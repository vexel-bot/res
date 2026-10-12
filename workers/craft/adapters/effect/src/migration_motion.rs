//! Convert legacy transform tracks through native keyframe commands. Sampling at
//! the graph's frame grid preserves rendered easing, including custom Beziers.
use effectcraft_engine::Session;
use serde_json::{Value, json};
use std::collections::{BTreeMap, HashMap};

fn value_at(keys: &[Value], frame: u64) -> Option<f64> {
    let first = keys.first()?;
    let last = keys.last()?;
    if frame <= first.get("frame")?.as_u64()? {
        return first.get("value")?.as_f64();
    }
    if frame >= last.get("frame")?.as_u64()? {
        return last.get("value")?.as_f64();
    }
    for pair in keys.windows(2) {
        let (a, b) = (&pair[0], &pair[1]);
        let (start, end) = (a.get("frame")?.as_u64()?, b.get("frame")?.as_u64()?);
        if frame < start || frame > end {
            continue;
        }
        if start == end {
            return None;
        }
        let p = (frame - start) as f64 / (end - start) as f64;
        let eased = match a.get("easing").and_then(Value::as_str).unwrap_or("linear") {
            "hold" => 0.0,
            "ease_in" => p * p,
            "ease_out" => 1.0 - (1.0 - p).powi(2),
            "ease_in_out" => {
                if p < 0.5 {
                    2.0 * p * p
                } else {
                    1.0 - (-2.0 * p + 2.0).powi(2) / 2.0
                }
            }
            "cubic_bezier" => {
                let c = a.get("cubicBezier")?.as_array()?;
                if c.len() != 4 {
                    return None;
                }
                let coords: Vec<f64> = c.iter().map(Value::as_f64).collect::<Option<_>>()?;
                let cubic = |t: f64, x: f64, y: f64| {
                    3.0 * (1.0 - t).powi(2) * t * x + 3.0 * (1.0 - t) * t * t * y + t.powi(3)
                };
                let (mut lo, mut hi, mut t) = (0.0, 1.0, p);
                for _ in 0..16 {
                    if cubic(t, coords[0], coords[2]) < p {
                        lo = t;
                    } else {
                        hi = t;
                    }
                    t = (lo + hi) / 2.0;
                }
                cubic(t, coords[1], coords[3])
            }
            "linear" => p,
            _ => return None,
        };
        return Some(
            a.get("value")?.as_f64()?
                + (b.get("value")?.as_f64()? - a.get("value")?.as_f64()?) * eased,
        );
    }
    None
}

pub fn apply(session: &mut Session, graph: &Value, layers: &HashMap<String, u64>, page: &Value, parents: &HashMap<String, String>) -> Vec<String> {
    let mut warnings = Vec::new();
    let rate = graph.get("frameRate").unwrap_or(&Value::Null);
    let fps = rate
        .get("numerator")
        .and_then(Value::as_f64)
        .unwrap_or(30.0)
        / rate
            .get("denominator")
            .and_then(Value::as_f64)
            .unwrap_or(1.0);
    let frames = graph
        .get("durationFrames")
        .and_then(Value::as_u64)
        .unwrap_or(if graph.is_null() {1} else {0});
    if !fps.is_finite() || fps <= 0.0 || frames == 0 {
        return vec!["Motion graph has invalid timing; original preserved".into()];
    }
    let mut groups: BTreeMap<(u64, &str), Vec<&Value>> = BTreeMap::new();
    let mut opacity_tracks = HashMap::new();
    for track in graph
        .get("tracks")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        let target = track
            .get("targetLayerId")
            .and_then(Value::as_str)
            .unwrap_or("");
        let Some(&layer) = layers.get(target) else {
            warnings.push(format!(
                "Motion target `{target}` was not converted; original preserved"
            ));
            continue;
        };
        let property = track.get("property").and_then(Value::as_str).unwrap_or("");
        if property == "opacity" { opacity_tracks.insert(target, track); }
        let path = match property {
            "position_x" | "position_y" => "transform/position",
            "scale_x" | "scale_y" => "transform/scale",
            "rotation_degrees" => "transform/rotation",
            "opacity" => "transform/opacity",
            _ => {
                warnings.push(format!("Motion property `{property}` on `{target}` requires manual conversion; original preserved"));
                continue;
            }
        };
        groups.entry((layer, path)).or_default().push(track);
    }
    for child in parents.keys() {
        groups.entry((layers[child], "transform/opacity")).or_default();
    }
    // Bound validation as well as native key creation before sampling any frames.
    if frames.saturating_mul(groups.len().max(1) as u64) > 10_000 {
        return vec!["Motion graph exceeds the automatic keyframe conversion budget; original preserved for manual conversion".into()];
    }
    let specs: HashMap<&str, &Value> = page["layers"].as_array().into_iter().flatten()
        .filter_map(|spec| Some((spec["id"].as_str()?,spec))).collect();
    for (&target, spec) in &specs {
        let tracks: Vec<&Value> = graph["tracks"].as_array().into_iter().flatten()
            .filter(|track|track["targetLayerId"].as_str()==Some(target)).collect();
        let rotation = spec["rotation"].as_f64().unwrap_or(0.0) != 0.0 || tracks.iter().any(|track|
            track["property"] == "rotation_degrees" && track["keyframes"].as_array().into_iter().flatten()
                .any(|key|key["value"].as_f64().unwrap_or(0.0)!=0.0));
        let x = tracks.iter().find(|track|track["property"]=="scale_x");
        let y = tracks.iter().find(|track|track["property"]=="scale_y");
        if rotation && (x.is_some() || y.is_some()) && (0..frames).any(|frame| {
            let scalar = |track: Option<&&Value>| track.and_then(|track|track["keyframes"].as_array())
                .and_then(|keys|value_at(keys,frame)).unwrap_or(1.0);
            (scalar(x)-scalar(y)).abs()>1e-9
        }) {
            warnings.push(format!("Rotated nonuniform scaling on `{target}` has a different transform order; original preserved for review"));
        }
    }
    // Engine edits retain undo snapshots. Bound conversion work explicitly,
    // rather than truncate a long animation or exhaust a worker's memory.
    for ((layer, path), tracks) in groups {
        let result = (|| -> Result<(), String> {
            let base = session
                .execute("prop.get", json!({"layer":layer,"path":path}))
                .map_err(|e| e.to_string())?["value"]
                .clone();
            for frame in 0..frames {
                let mut value = base.clone();
                for track in &tracks {
                    let keys = track
                        .get("keyframes")
                        .and_then(Value::as_array)
                        .ok_or("missing motion keys")?;
                    let scalar = value_at(keys, frame)
                        .filter(|v| v.is_finite())
                        .ok_or("invalid motion keys")?;
                    match track["property"].as_str().unwrap_or("") {
                        "position_x" => {
                            value[0] = json!(base[0].as_f64().ok_or("position dimension")? + scalar)
                        }
                        "position_y" => {
                            value[1] = json!(base[1].as_f64().ok_or("position dimension")? + scalar)
                        }
                        "scale_x" => {
                            value[0] = json!(base[0].as_f64().ok_or("scale dimension")? * scalar)
                        }
                        "scale_y" => {
                            value[1] = json!(base[1].as_f64().ok_or("scale dimension")? * scalar)
                        }
                        "opacity" => value = json!(scalar * 100.0),
                        "rotation_degrees" => value = json!(scalar),
                        _ => return Err("unsupported motion property".into()),
                    }
                }
                if path == "transform/opacity" {
                    let legacy = layers.iter().find(|(_, id)| **id == layer).map(|(legacy,_)|legacy.as_str()).ok_or("missing layer mapping")?;
                    let mut parent = parents.get(legacy);
                    let mut alpha = value.as_f64().ok_or("opacity value")?;
                    while let Some(ancestor) = parent {
                        let spec = specs.get(ancestor.as_str()).ok_or("missing parent specification")?;
                        let parent_alpha = if let Some(track) = opacity_tracks.get(ancestor.as_str()) {
                            value_at(track["keyframes"].as_array().ok_or("missing parent keys")?,frame).ok_or("invalid parent keys")?
                        } else { spec["opacity"].as_f64().unwrap_or(1.0) };
                        let timing = &spec["properties"]["editorialTiming"];
                        let active = if let (Some(start),Some(duration),Some(rate)) = (timing["startFrame"].as_f64(),timing["durationFrames"].as_f64(),timing["fps"].as_f64()) {
                            let seconds=frame as f64/fps;
                            rate > 0.0 && seconds >= start/rate && seconds < (start+duration)/rate
                        } else {true};
                        alpha *= if spec["visible"].as_bool().unwrap_or(true) && active {parent_alpha} else {0.0};
                        parent = parents.get(ancestor);
                    }
                    value=json!(alpha);
                }
                if graph.is_null() {
                    session.execute("prop.set",json!({"layer":layer,"path":path,"value":value})).map_err(|e|e.to_string())?;
                } else {
                    session.execute("prop.addKey", json!({"layer":layer,"path":path,"time":frame as f64/fps,"timeBase":"comp","value":value})).map_err(|e| e.to_string())?;
                }
            }
            Ok(())
        })();
        if let Err(error) = result {
            warnings.push(format!(
                "Motion `{path}` on native layer {layer}: {error}; original preserved"
            ));
        }
    }
    for field in ["transitions", "audioEvents", "constraints"] {
        if graph
            .get(field)
            .and_then(Value::as_array)
            .is_some_and(|v| !v.is_empty())
        {
            warnings.push(format!(
                "Motion `{field}` requires manual conversion; original preserved"
            ));
        }
    }
    warnings
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn legacy_easing_is_sampled_on_frame_grid() {
        let keys = vec![
            json!({"frame":0,"value":0.0,"easing":"ease_in"}),
            json!({"frame":10,"value":20.0}),
        ];
        assert_eq!(value_at(&keys, 5), Some(5.0));
        assert_eq!(value_at(&keys, 10), Some(20.0));
        let hold = vec![
            json!({"frame":0,"value":0.0,"easing":"hold"}),
            json!({"frame":10,"value":20.0}),
        ];
        assert_eq!(value_at(&hold, 9), Some(0.0));
        assert_eq!(value_at(&hold, 10), Some(20.0));
    }
}
