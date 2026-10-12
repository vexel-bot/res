//! The shared transport only. Document editing and pixels belong to the Craft engines.
#![forbid(unsafe_code)]
use serde::Deserialize;
use serde_json::{Value, json};
use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};

pub type Result<T> = std::result::Result<T, String>;

pub fn requires_isolation(command: &str) -> bool {
    let command = command.to_ascii_lowercase();
    command.contains("script") || command.contains("plugin")
}
pub fn isolated_context() -> bool {
    #[cfg(target_arch = "wasm32")]
    {
        true
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        std::env::var("CLICKO_CRAFT_ISOLATED").is_ok_and(|value| value == "1")
    }
}
pub fn capability_isolation(commands: &mut [Value]) {
    for command in commands {
        let required = command
            .get("id")
            .and_then(Value::as_str)
            .is_some_and(requires_isolation);
        command["requiresIsolation"] = json!(required);
        if required && !isolated_context() {
            command["available"] = json!(false);
            command["disabledReason"] =
                json!("script and plugin execution requires an isolated worker or browser engine");
        }
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Request {
    pub protocol_version: u32,
    pub request_id: Value,
    pub engine: String,
    pub method: String,
    #[serde(default = "empty_object")]
    pub params: Value,
}
fn empty_object() -> Value {
    json!({})
}

pub fn respond(
    raw: &str,
    engine: &str,
    mut dispatch: impl FnMut(&str, &Value) -> Result<Value>,
) -> Value {
    let request: Request = match serde_json::from_str(raw) {
        Ok(request) => request,
        Err(e) => {
            return json!({"protocolVersion":1,"requestId":null,"error":{"code":"INVALID_REQUEST","message":e.to_string()}});
        }
    };
    let result = if request.protocol_version != 1 || request.engine != engine {
        Err("unsupported protocol version or incorrect engine".into())
    } else {
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| dispatch(&request.method, &request.params)))
            .unwrap_or_else(|_| Err("engine rejected the request after an internal failure; the saved input remains unchanged".into()))
    };
    match result {
        Ok(result) => json!({"protocolVersion":1,"requestId":request.request_id,"result":result}),
        Err(message) => {
            json!({"protocolVersion":1,"requestId":request.request_id,"error":{"code":"ENGINE_ERROR","message":message}})
        }
    }
}

pub fn stdio(
    engine: &str,
    mut dispatch: impl FnMut(&str, &Value) -> Result<Value>,
) -> std::io::Result<()> {
    let input = std::io::stdin();
    let mut output = std::io::stdout().lock();
    for line in input.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let response = respond(&line, engine, &mut dispatch);
        serde_json::to_writer(&mut output, &response)?;
        writeln!(output)?;
        output.flush()?;
    }
    Ok(())
}

pub fn text<'a>(params: &'a Value, name: &str) -> Result<&'a str> {
    params
        .get(name)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("missing string `{name}`"))
}

/// A launch-time root materialized by the authenticated host, never a client-selected path.
pub struct Workspace {
    root: PathBuf,
}
impl Workspace {
    pub fn from_params(params: &Value) -> Result<Self> {
        let root = Path::new(text(params, "mediaRoot")?)
            .canonicalize()
            .map_err(|e| format!("mediaRoot: {e}"))?;
        if !root.is_dir() {
            return Err("mediaRoot is not a directory".into());
        }
        Ok(Self { root })
    }
    pub fn read_path(&self, path: &str) -> Result<PathBuf> {
        let requested = Path::new(path);
        let resolved = if requested.is_absolute() {
            requested.to_path_buf()
        } else {
            self.root.join(requested)
        };
        let resolved = resolved
            .canonicalize()
            .map_err(|e| format!("input path: {e}"))?;
        if !resolved.starts_with(&self.root) {
            return Err("input path leaves the job workspace".into());
        }
        Ok(resolved)
    }
    pub fn write_path(&self, path: &str) -> Result<PathBuf> {
        let requested = Path::new(path);
        let joined = if requested.is_absolute() {
            requested.to_path_buf()
        } else {
            self.root.join(requested)
        };
        let name = joined.file_name().ok_or("output path needs a filename")?;
        let parent = joined
            .parent()
            .ok_or("output path needs a parent")?
            .canonicalize()
            .map_err(|e| format!("output parent: {e}"))?;
        if !parent.starts_with(&self.root) {
            return Err("output path leaves the job workspace".into());
        }
        let out = parent.join(name);
        if out.exists()
            && !out
                .canonicalize()
                .map_err(|e| e.to_string())?
                .starts_with(&self.root)
        {
            return Err("output symlink leaves the job workspace".into());
        }
        Ok(out)
    }
    pub fn read(&self, path: &str) -> std::io::Result<Vec<u8>> {
        std::fs::read(self.read_path(path).map_err(std::io::Error::other)?)
    }
    pub fn check_command(&self, id: &str, params: &Value) -> Result<()> {
        // These capabilities require an independently sandboxed host rather than tenant media access.
        if requires_isolation(id) && !isolated_context() {
            return Err(format!("`{id}` requires an isolated script/plugin host"));
        }
        let property_path = id.starts_with("prop.")
            || id.starts_with("keys.")
            || id.starts_with("effects.")
            || id.starts_with("effect.")
            || id.starts_with("layer.setTransform");
        fn check(
            ws: &Workspace,
            value: &Value,
            key: &str,
            depth: usize,
            property_path: bool,
        ) -> Result<()> {
            if depth > 32 {
                return Err("command nesting exceeds 32".into());
            }
            match value {
                Value::Object(o) => {
                    for (key, value) in o {
                        check(ws, value, key, depth + 1, property_path)?;
                    }
                }
                Value::Array(a) => {
                    for value in a {
                        check(ws, value, key, depth + 1, property_path)?;
                    }
                }
                Value::String(path)
                    if [
                        "path",
                        "paths",
                        "folder",
                        "directory",
                        "filename",
                        "filePath",
                        "sourcePath",
                        "output",
                        "out",
                        "uri",
                        "url",
                    ]
                    .iter()
                    .any(|field| field.eq_ignore_ascii_case(key))
                        && !(property_path && key == "path") =>
                {
                    if path.contains("://") {
                        return Err("remote URLs must be ingested by the authenticated host".into());
                    }
                    if Path::new(path).exists() {
                        ws.read_path(path)?;
                    } else {
                        ws.write_path(path)?;
                    }
                }
                _ => (),
            }
            Ok(())
        }
        check(self, params, "", 0, property_path)
    }
}

pub fn commands(params: &Value) -> Result<Vec<(String, Value)>> {
    if let Some(list) = params.get("commands").and_then(Value::as_array) {
        if list.len() > 1000 {
            return Err("at most 1000 commands per transaction".into());
        }
        list.iter()
            .map(|command| {
                Ok((
                    text(command, "id")?.to_owned(),
                    command.get("params").cloned().unwrap_or_else(empty_object),
                ))
            })
            .collect()
    } else {
        let id = params
            .get("command")
            .or_else(|| params.get("id"))
            .and_then(Value::as_str)
            .ok_or("missing command or commands")?;
        Ok(vec![(
            id.to_owned(),
            params.get("params").cloned().unwrap_or_else(empty_object),
        )])
    }
}

pub fn dimensions(params: &Value) -> Result<(u32, u32)> {
    let w = params.get("width").and_then(Value::as_u64).unwrap_or(1080);
    let h = params.get("height").and_then(Value::as_u64).unwrap_or(1080);
    if w == 0 || h == 0 || w > 16384 || h > 16384 || w.saturating_mul(h) > 67_108_864 {
        return Err("invalid dimensions (maximum 16384 per side, 64 megapixels)".into());
    }
    Ok((w as u32, h as u32))
}
pub fn seconds(params: &Value) -> Result<f64> {
    let seconds = params
        .get("timeSeconds")
        .or_else(|| params.get("seconds"))
        .or_else(|| params.get("time"))
        .and_then(Value::as_f64)
        .unwrap_or(0.0);
    if !seconds.is_finite() || !(0.0..=86_400.0).contains(&seconds) {
        return Err("invalid time".into());
    }
    Ok(seconds)
}

pub fn frame_seconds(params: &Value, fps: f64) -> Result<f64> {
    if ["timeSeconds", "seconds", "time"]
        .iter()
        .any(|key| params.get(key).is_some())
    {
        return seconds(params);
    }
    let frame = params.get("frame").and_then(Value::as_u64).unwrap_or(0);
    let value = frame as f64 / fps;
    if !fps.is_finite() || fps <= 0.0 || !value.is_finite() || value > 86_400.0 {
        return Err("invalid frame time".into());
    }
    Ok(value)
}
pub fn legacy_pages(params: &Value) -> &[Value] {
    params
        .pointer("/legacyDocument/composition/pages")
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or(&[])
}
pub fn media_path<'a>(params: &'a Value, asset_id: &str) -> Option<&'a str> {
    params
        .get("media")
        .and_then(Value::as_array)?
        .iter()
        .find(|m| m.get("assetId").and_then(Value::as_str) == Some(asset_id))?
        .get("path")?
        .as_str()
}

/// Upstream Photo/Film registries publish compact parameter descriptions. The exact,
/// commonly edited commands below get a concrete schema; other commands retain their
/// authoritative description and optional fields discovered from the registry.
pub fn command_schema(engine: &str, id: &str, description: &str) -> Value {
    let num = || json!({"type":"number"});
    let int = || json!({"type":"integer"});
    let string = || json!({"type":"string"});
    let boolean = || json!({"type":"boolean"});
    let vec = |length| json!({"type":"array","items":{"type":"number"},"minItems":length,"maxItems":length});
    let mut properties = serde_json::Map::new();
    let mut required = Vec::<&str>::new();
    match (engine, id) {
        ("photocraft", "type.create") => {
            properties.extend([
                ("text".into(), string()),
                ("name".into(), string()),
                ("x".into(), num()),
                ("y".into(), num()),
                ("box".into(), vec(4)),
                ("size".into(), num()),
                ("font".into(), string()),
                ("color".into(), json!({"type":"string","format":"color"})),
                (
                    "align".into(),
                    json!({"type":"string","enum":["left","center","right","justify"]}),
                ),
            ]);
            required.push("text");
        }
        ("photocraft", "shape.create") => {
            properties.extend([("kind".into(),json!({"type":"string","enum":["rect","roundedRect","ellipse","polygon","star","line"]})),("rect".into(),vec(4)),("fill".into(),json!({"type":"string","format":"color"})),("name".into(),string()),("radii".into(),num()),("sides".into(),int())]);
            required.extend(["kind", "rect"]);
        }
        ("photocraft", "layer.setProps") => {
            properties.extend([("layer".into(),int()),("name".into(),string()),("visible".into(),boolean()),("opacity".into(),json!({"type":"number","minimum":0,"maximum":1})),("fill".into(),json!({"type":"number","minimum":0,"maximum":1})),("locked".into(),boolean()),("blend".into(),json!({"type":"string","enum":["Normal","Multiply","Screen","Overlay","Soft Light","Hard Light","Difference"]}))]);
        }
        ("photocraft", "layer.translate") => {
            properties.extend([
                ("layer".into(), int()),
                ("dx".into(), int()),
                ("dy".into(), int()),
            ]);
            required.extend(["dx", "dy"]);
        }
        ("photocraft", "layer.select") => {
            properties.extend([
                ("layer".into(), int()),
                (
                    "layers".into(),
                    json!({"type":"array","items":{"type":"integer"}}),
                ),
            ]);
        }
        ("photocraft", "edit.transform") => {
            properties.extend([
                ("layer".into(), int()),
                ("matrix".into(), vec(6)),
                ("rect".into(), vec(4)),
            ]);
        }
        ("photocraft", "type.setText") => {
            properties.extend([("layer".into(), int()), ("text".into(), string())]);
            required.push("text");
        }
        ("photocraft", "type.setStyle") => {
            properties.extend([
                ("layer".into(), int()),
                ("size".into(), num()),
                ("font".into(), string()),
                ("color".into(), json!({"type":"string","format":"color"})),
                ("fauxBold".into(), boolean()),
                ("fauxItalic".into(), boolean()),
            ]);
        }
        ("photocraft", "layer.newFillLayer.solidColor") => {
            properties.extend([
                ("color".into(), json!({"type":"string","format":"color"})),
                ("name".into(), string()),
            ]);
        }
        ("filmcraft", "timeline.place") => {
            properties.extend([
                ("item".into(), int()),
                ("track".into(), string()),
                ("audioTrack".into(), string()),
                ("seconds".into(), num()),
                ("sourceIn".into(), int()),
                ("duration".into(), int()),
                ("insert".into(), boolean()),
                ("video".into(), boolean()),
                ("audio".into(), boolean()),
            ]);
            required.extend(["item", "seconds"]);
        }
        ("filmcraft", "timeline.trim") => {
            properties.extend([
                ("clip".into(), int()),
                ("edge".into(), json!({"type":"string","enum":["in","out"]})),
                (
                    "mode".into(),
                    json!({"type":"string","enum":["regular","ripple"]}),
                ),
                ("deltaFrames".into(), int()),
            ]);
            required.extend(["clip", "edge", "deltaFrames"]);
        }
        ("filmcraft", "captions.add") => {
            properties.extend([
                ("text".into(), string()),
                ("seconds".into(), num()),
                ("durationSeconds".into(), num()),
                ("track".into(), string()),
            ]);
            required.push("text");
        }
        ("filmcraft", "file.newColorMatte") => {
            properties.extend([
                ("color".into(), json!({"type":"string","format":"color"})),
                ("seconds".into(), num()),
            ]);
            required.extend(["color", "seconds"]);
        }
        ("filmcraft", "clip.audioGain") => {
            properties.extend([
                (
                    "clips".into(),
                    json!({"type":"array","items":{"type":"integer"}}),
                ),
                ("db".into(), num()),
                (
                    "mode".into(),
                    json!({"type":"string","enum":["set","adjust","normalizeMax","normalizeAll"]}),
                ),
            ]);
            required.extend(["clips", "db"]);
        }
        ("filmcraft", "effects.setParam") => {
            properties.extend([
                ("clip".into(), int()),
                ("effect".into(), string()),
                ("param".into(), string()),
                ("value".into(), num()),
                ("keyframe".into(), boolean()),
                ("time".into(), int()),
            ]);
            required.extend(["clip", "effect", "param", "value"]);
        }
        ("filmcraft", "timeline.select") => {
            properties.extend([
                (
                    "clips".into(),
                    json!({"type":"array","items":{"type":"integer"}}),
                ),
                ("add".into(), boolean()),
                ("toggle".into(), boolean()),
            ]);
            required.push("clips");
        }
        ("effectcraft", "layer.newSolid") => {
            properties.extend([
                ("name".into(), string()),
                ("color".into(), json!({"type":"string","format":"color"})),
                ("width".into(), int()),
                ("height".into(), int()),
            ]);
        }
        ("effectcraft", "layer.newText") => {
            properties.extend([
                ("text".into(), string()),
                ("name".into(), string()),
                ("size".into(), num()),
                ("font".into(), string()),
                ("fill".into(), json!({"type":"string","format":"color"})),
                ("box".into(), vec(4)),
                ("position".into(), vec(2)),
            ]);
        }
        ("effectcraft", "layer.newShape") => {
            properties.extend([
                ("name".into(), string()),
                (
                    "kind".into(),
                    json!({"type":"string","enum":["rect","rounded","ellipse","star","polygon"]}),
                ),
                ("position".into(), vec(2)),
                ("size".into(), vec(2)),
                ("fill".into(), json!({"type":"string","format":"color"})),
                ("strokeWidth".into(), num()),
            ]);
        }
        ("effectcraft", "prop.set") => {
            properties.extend([
                ("layer".into(), int()),
                ("path".into(), string()),
                (
                    "value".into(),
                    json!({"type":["number","array","string","boolean","object"]}),
                ),
            ]);
            required.extend(["path", "value"]);
        }
        ("effectcraft", "layer.select") => {
            properties.insert(
                "layers".into(),
                json!({"type":"array","items":{"type":"integer"}}),
            );
            required.push("layers");
        }
        (
            "effectcraft",
            "edit.clear" | "edit.duplicate" | "edit.cut" | "edit.copy" | "layer.setSwitch",
        ) => {
            properties.insert(
                "layers".into(),
                json!({"type":"array","items":{"type":"integer"}}),
            );
            if id == "layer.setSwitch" {
                properties.extend([
                    ("switch".into(), string()),
                    ("value".into(), boolean()),
                    ("merge".into(), boolean()),
                ]);
                required.push("switch");
            }
        }
        ("effectcraft", "layer.setTransform") => {
            properties.extend([
                ("layer".into(), int()),
                (
                    "prop".into(),
                    json!({"type":"string","enum":["position","scale","rotation","opacity"]}),
                ),
                ("value".into(), num()),
            ]);
            required.extend(["prop", "value"]);
        }
        ("effectcraft", "effect.add") => {
            properties.extend([("layer".into(), int()), ("effect".into(), string())]);
            required.push("effect");
        }
        ("effectcraft", "effect.setParam") => {
            properties.extend([
                ("layer".into(), int()),
                ("effect".into(), int()),
                ("param".into(), string()),
                ("value".into(), num()),
            ]);
            required.extend(["effect", "param", "value"]);
        }
        _ => {
            // Descriptions use {"name":type}. Only top-level quoted names are collected;
            // a description isn't interpreted as executable code or JSON Schema.
            let bytes = description.as_bytes();
            let mut index = 0usize;
            while let Some(start) = description
                .get(index..)
                .and_then(|s| s.find('"'))
                .map(|n| n + index)
            {
                let Some(end) = description
                    .get(start + 1..)
                    .and_then(|s| s.find('"'))
                    .map(|n| n + start + 1)
                else {
                    break;
                };
                index = end + 1;
                if bytes.get(index) != Some(&b':') {
                    continue;
                }
                let key = &description[start + 1..end];
                if key.is_empty() || !key.chars().all(|c| c.is_ascii_alphanumeric() || c == '_') {
                    continue;
                }
                let tail = description.get(index + 1..).unwrap_or("");
                let token = tail.split([',', '}']).next().unwrap_or("");
                let schema = if token.starts_with('[') {
                    json!({"type":"array","items":{"type":"number"}})
                } else if token.starts_with("bool") {
                    boolean()
                } else if token.starts_with("str") {
                    string()
                } else if token.starts_with("id")
                    || token.starts_with('n')
                    || token.starts_with('i')
                    || token.starts_with('u')
                {
                    int()
                } else if token.starts_with('f')
                    || token.starts_with("px")
                    || token.starts_with("0..")
                    || token.starts_with("percent")
                {
                    num()
                } else {
                    string()
                };
                properties.entry(key.to_owned()).or_insert(schema);
            }
        }
    }
    json!({"type":"object","properties":properties,"required":required,"additionalProperties":true,"description":description})
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn frame_preview_respects_project_rate_and_explicit_time() {
        assert_eq!(frame_seconds(&json!({"frame":9}), 10.0).unwrap(), 0.9);
        assert_eq!(
            frame_seconds(&json!({"frame":9,"timeSeconds":0.2}), 10.0).unwrap(),
            0.2
        );
        assert!(frame_seconds(&json!({"frame":1}), 0.0).is_err());
    }
    #[test]
    fn wrong_engine_does_not_dispatch() {
        let response = respond(
            r#"{"protocolVersion":1,"requestId":"a","engine":"wrong","method":"project.new"}"#,
            "photocraft",
            |_, _| Err("should never run".into()),
        );
        assert_eq!(response["requestId"], "a");
        assert!(
            response["error"]["message"]
                .as_str()
                .unwrap()
                .contains("incorrect engine")
        );
    }
    #[test]
    fn rejects_absurd_allocation_and_command_count() {
        assert!(dimensions(&json!({"width":0})).is_err());
        assert!(dimensions(&json!({"width":16384,"height":16384})).is_err());
        assert!(commands(&json!({"commands":vec![json!({"id":"layer.new"});1001]})).is_err());
    }
    #[test]
    fn catches_upstream_panic() {
        let response = respond(
            r#"{"protocolVersion":1,"requestId":4,"engine":"photocraft","method":"project.new"}"#,
            "photocraft",
            |_, _| panic!("test failure"),
        );
        assert_eq!(response["error"]["code"], "ENGINE_ERROR");
    }
    #[test]
    fn property_paths_are_not_filesystem_paths() {
        let root = std::env::temp_dir().canonicalize().unwrap();
        let workspace = Workspace { root };
        assert!(
            workspace
                .check_command("prop.set", &json!({"path":"transform/rotation","value":20}))
                .is_ok()
        );
        assert!(
            workspace
                .check_command(
                    "file.import",
                    &json!({"paths":["https://outside.invalid/asset.png"]})
                )
                .is_err()
        );
        if !isolated_context() {
            assert!(workspace.check_command("script.run", &json!({})).is_err());
        }
    }
    #[test]
    fn editable_controls_have_numeric_and_vector_schemas() {
        let image = command_schema("photocraft", "shape.create", "ignored");
        assert_eq!(image["properties"]["rect"]["maxItems"], 4);
        let trim = command_schema("filmcraft", "timeline.trim", "ignored");
        assert_eq!(trim["properties"]["deltaFrames"]["type"], "integer");
        let clear = command_schema("effectcraft", "edit.clear", "{layers?}");
        assert_eq!(clear["properties"]["layers"]["items"]["type"], "integer");
        let prop = command_schema("effectcraft", "prop.set", "{path,value}");
        assert!(
            prop["properties"]["value"]["type"]
                .as_array()
                .unwrap()
                .contains(&json!("array"))
        );
    }
}
