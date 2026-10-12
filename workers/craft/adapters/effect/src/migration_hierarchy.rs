//! Legacy groups use local top-left coordinates and inherited alpha. Craft
//! nulls provide the transform hierarchy; alpha is sampled separately.
use effectcraft_engine::Session;
use serde_json::{Value, json};
use std::collections::{HashMap, HashSet};

pub fn apply(
    session: &mut Session,
    page: &Value,
    graph: &Value,
    layers: &HashMap<String, u64>,
) -> (HashMap<String, String>, Vec<String>) {
    let mut warnings = Vec::new();
    let specs: HashMap<&str, &Value> = page["layers"].as_array().into_iter().flatten()
        .filter_map(|layer| Some((layer["id"].as_str()?, layer))).collect();
    let nodes: HashMap<&str, &Value> = graph["nodes"].as_array().into_iter().flatten()
        .filter_map(|node| Some((node["nodeId"].as_str()?, node))).collect();
    let by_layer: HashMap<&str, &Value> = nodes.values()
        .filter_map(|node| Some((node["targetLayerId"].as_str()?, *node))).collect();
    let mut parents = HashMap::new();
    // Set pivots before parenting/keyframes. Changing an anchor without the
    // matching position would move the original pixels.
    for (legacy, &id) in layers {
        let Some(spec) = specs.get(legacy.as_str()) else { continue };
        let node = by_layer.get(legacy.as_str()).copied().unwrap_or(&Value::Null);
        let w = spec["width"].as_f64().unwrap_or(100.0);
        let h = spec["height"].as_f64().unwrap_or(100.0);
        let ox = node["transformOriginX"].as_f64().unwrap_or(0.5);
        let oy = node["transformOriginY"].as_f64().unwrap_or(0.5);
        let result = (|| -> Result<(), String> {
            let anchor = session.execute("prop.get", json!({"layer":id,"path":"transform/anchor"}))
                .map_err(|e|e.to_string())?["value"].clone();
            let scale = session.execute("prop.get", json!({"layer":id,"path":"transform/scale"}))
                .map_err(|e|e.to_string())?["value"].clone();
            let sx = scale[0].as_f64().ok_or("missing scale")? / 100.0;
            let sy = scale[1].as_f64().ok_or("missing scale")? / 100.0;
            if sx == 0.0 || sy == 0.0 { return Err("zero scale".into()) }
            let a = if spec["kind"] == "group" {
                json!([ox*w,oy*h,0.0])
            } else {
                json!([anchor[0].as_f64().ok_or("missing anchor")?+(ox-0.5)*w/sx,
                    anchor[1].as_f64().ok_or("missing anchor")?+(oy-0.5)*h/sy,0.0])
            };
            session.execute("prop.set", json!({"layer":id,"path":"transform/anchor","value":a}))
                .map_err(|e|e.to_string())?;
            session.execute("prop.set", json!({"layer":id,"path":"transform/position","value":[
                spec["x"].as_f64().unwrap_or(0.0)+ox*w,
                spec["y"].as_f64().unwrap_or(0.0)+oy*h,0.0]})).map_err(|e|e.to_string())?;
            Ok(())
        })();
        if let Err(error) = result {
            warnings.push(format!("Pivot on `{legacy}`: {error}; original preserved"));
        }
        let parent = node["parentNodeId"].as_str().and_then(|name| nodes.get(name))
            .and_then(|parent| parent["targetLayerId"].as_str())
            .or_else(|| spec["properties"]["parentId"].as_str());
        if let Some(parent) = parent {
            if specs.get(parent).is_some_and(|p| p["kind"] == "group") && layers.contains_key(parent) {
                parents.insert(legacy.clone(), parent.to_owned());
            } else {
                warnings.push(format!("Parent `{parent}` on `{legacy}` requires manual conversion; original preserved"));
            }
        } else if node["parentNodeId"].as_str().is_some() {
            warnings.push(format!("Missing parent on `{legacy}`; original preserved"));
        }
    }
    // Validate the complete graph before any parent edits, independent of input order.
    let mut valid = HashMap::new();
    for (child, parent) in &parents {
        let mut seen = HashSet::from([child.as_str()]);
        let mut current = Some(parent.as_str());
        let mut cycle = false;
        while let Some(ancestor) = current {
            if !seen.insert(ancestor) || seen.len() > 64 { cycle = true; break }
            current = parents.get(ancestor).map(String::as_str);
        }
        if cycle {
            warnings.push(format!("Cyclic or excessive hierarchy on `{child}`; original preserved"));
            continue;
        }
        match session.execute("layer.setParent", json!({"layers":[layers[child]],"parent":layers[parent],"compensate":false})) {
            Ok(_) => { valid.insert(child.clone(), parent.clone()); }
            Err(error) => warnings.push(format!("Parent on `{child}`: {error}; original preserved")),
        }
    }
    for group in valid.values().collect::<HashSet<_>>() {
        let count = valid.values().filter(|parent| *parent == group).count();
        let opacity = specs[group.as_str()]["opacity"].as_f64().unwrap_or(1.0);
        let animated_alpha = graph["tracks"].as_array().into_iter().flatten().any(|track|
            track["targetLayerId"].as_str() == Some(group.as_str()) && track["property"] == "opacity");
        if count > 1 && (opacity != 1.0 || animated_alpha) {
            warnings.push(format!("Group `{group}` alpha on overlapping children requires compositing review; original preserved"));
        }
        if graph.is_null() && specs[group.as_str()]["properties"]["editorialTiming"].is_object() {
            warnings.push(format!("Group `{group}` timing without a motion graph requires manual review; original preserved"));
        }
    }
    (valid, warnings)
}
