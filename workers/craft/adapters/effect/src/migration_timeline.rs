//! Native composition layers for the media timeline; keep unsupported data visible.
use super::Adapter;
use serde_json::{Value, json};
use std::collections::HashMap;

pub fn apply(adapter: &mut Adapter, params: &Value) -> HashMap<String, u64> {
    let mut ids = HashMap::new();
    let Some(timeline) = params
        .pointer("/legacyDocument/composition/mediaTimeline")
        .filter(|v| v.is_object())
    else {
        return ids;
    };
    let fps = adapter
        .session
        .active_comp()
        .map(|comp| comp.frame_rate.as_f64())
        .unwrap_or(30.0);
    for track in timeline
        .get("tracks")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
    {
        let kind = track["kind"].as_str().unwrap_or("");
        if !matches!(kind, "video" | "audio" | "overlay" | "caption") {
            adapter.warnings.push(format!(
                "Timeline track `{kind}` requires manual conversion; original preserved"
            ));
            continue;
        }
        let entries = track
            .get(if kind == "caption" { "cues" } else { "clips" })
            .and_then(Value::as_array);
        for clip in entries.into_iter().flatten() {
            let legacy_id = clip["id"].as_str().unwrap_or("unknown");
            let result = (|| -> Result<u64, String> {
                let start = clip
                    .pointer("/timeline/startFrame")
                    .and_then(Value::as_f64)
                    .unwrap_or(0.0)
                    / fps;
                let duration = clip
                    .pointer("/timeline/durationFrames")
                    .and_then(Value::as_f64)
                    .unwrap_or(1.0)
                    / fps;
                let speed = clip
                    .get("playbackRate")
                    .and_then(Value::as_f64)
                    .unwrap_or(1.0);
                let source = clip
                    .pointer("/source/startMicroseconds")
                    .and_then(Value::as_f64)
                    .unwrap_or(0.0)
                    / 1_000_000.0;
                let imported = if kind == "caption" {
                    let comp = adapter.session.active_comp().ok_or("no composition")?;
                    let (width, height) = (f64::from(comp.width), f64::from(comp.height));
                    adapter.session.execute("layer.newText", json!({"name":legacy_id,"text":clip.get("text"),"box":[width*0.05,height*0.75,width*0.9,height*0.2],"fill":clip.pointer("/style/color").and_then(Value::as_str).unwrap_or("#ffffff"),"size":clip.pointer("/style/fontSize").and_then(Value::as_f64).unwrap_or(56.0)})).map_err(|e|e.to_string())?
                } else {
                    adapter.execute(
                        "asset.import",
                        &json!({"assetId":clip.get("assetId"),"addToComp":true}),
                        params,
                    )?
                };
                let id = imported
                    .get("layer")
                    .and_then(Value::as_u64)
                    .or_else(|| adapter.session.state.selected_layers.first().map(|id| id.0))
                    .ok_or("import did not create a layer")?;
                if speed != 1.0 {
                    adapter
                        .session
                        .execute(
                            "layer.timeStretch",
                            json!({"layers":[id],"percent":100.0/speed,"hold":"in"}),
                        )
                        .map_err(|e| e.to_string())?;
                }
                // The source starts at (start - source/speed), while visible in/out
                // boundaries are on the timeline's exact frame grid.
                adapter.session.execute("layer.timing", json!({"layers":[id],"start":start-source/speed,"in":start,"out":start+duration})).map_err(|e|e.to_string())?;
                let enabled = clip.get("enabled").and_then(Value::as_bool).unwrap_or(true)
                    && !track.get("muted").and_then(Value::as_bool).unwrap_or(false);
                let original_audio = clip
                    .pointer("/transform/originalAudioEnabled")
                    .and_then(Value::as_bool)
                    .unwrap_or(false);
                adapter
                    .session
                    .execute(
                        "layer.setSwitch",
                        json!({"layers":[id],"switch":"video","value":enabled && kind!="audio"}),
                    )
                    .map_err(|e| e.to_string())?;
                adapter
                    .session
                    .execute(
                        "layer.setSwitch",
                        json!({"layers":[id],"switch":"audio","value":enabled && (kind=="audio" || original_audio)}),
                    )
                    .map_err(|e| e.to_string())?;
                if kind == "audio" {
                    let gain = clip.get("gainDb").and_then(Value::as_f64).unwrap_or(0.0);
                    adapter
                        .session
                        .execute(
                            "prop.set",
                            json!({"layer":id,"path":"audio/levels","value":[gain,gain]}),
                        )
                        .map_err(|e| e.to_string())?;
                    if clip.get("pan").and_then(Value::as_f64).unwrap_or(0.0) != 0.0
                        || ["fadeInFrames", "fadeOutFrames"]
                            .iter()
                            .any(|key| clip.get(key).and_then(Value::as_u64).unwrap_or(0) > 0)
                    {
                        adapter.warnings.push(format!("Audio pan/fades on `{legacy_id}` require manual conversion; original preserved"));
                    }
                }
                if clip
                    .get("transform")
                    .and_then(Value::as_object)
                    .is_some_and(|v| !v.is_empty())
                    || ["effects", "keyframes"].iter().any(|key| {
                        clip.get(key)
                            .and_then(Value::as_array)
                            .is_some_and(|v| !v.is_empty())
                    })
                {
                    adapter.warnings.push(format!("Timeline transforms/effects on `{legacy_id}` require manual review; original preserved"));
                }
                if kind == "caption" {
                    adapter.warnings.push(format!("Caption `{legacy_id}` was converted to editable native text; typography/outline placement requires review; original cue preserved"));
                }
                let locked = clip.get("locked").and_then(Value::as_bool).unwrap_or(false)
                    || track
                        .get("locked")
                        .and_then(Value::as_bool)
                        .unwrap_or(false);
                adapter
                    .session
                    .execute(
                        "layer.setSwitch",
                        json!({"layers":[id],"switch":"lock","value":locked}),
                    )
                    .map_err(|e| e.to_string())?;
                Ok(id)
            })();
            match result {
                Ok(id) => {
                    ids.insert(legacy_id.to_owned(), id);
                }
                Err(error) => adapter.warnings.push(format!(
                    "Timeline clip `{legacy_id}`: {error}; original preserved"
                )),
            }
        }
    }
    ids
}
