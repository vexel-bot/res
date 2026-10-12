#![forbid(unsafe_code)]
use clicko_craft_protocol::{
    Result, Workspace, command_schema, commands, dimensions, legacy_pages, media_path, text,
};
use photocraft_engine::Session;
use serde_json::{Value, json};
#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

pub const REVISION: &str = "a7f26522ff84cd427c8a5d54b0e8ded7b56fb296";
pub const BUILD: &str = "clicko-photocraft-1.0.0+a7f26522";

#[cfg_attr(target_arch = "wasm32", wasm_bindgen)]
#[derive(Default)]
pub struct Adapter {
    session: Session,
    warnings: Vec<String>,
}

impl Adapter {
    pub fn open_bytes(&mut self, name: &str, bytes: &[u8]) -> Result<()> {
        let doc = if name.ends_with(".pcraft") {
            photocraft_format::load_from_bytes(bytes).map_err(|e| e.to_string())?
        } else {
            let imported = photocraft_io::import(name, bytes).map_err(|e| e.to_string())?;
            self.warnings.extend(imported.warnings);
            imported.document
        };
        self.session = Session::new();
        self.session.add_document(doc, None);
        Ok(())
    }
    pub fn native_bytes(&self) -> Result<Vec<u8>> {
        let document = &self.session.active().ok_or("no active image project")?.doc;
        photocraft_format::save_to_bytes(document, &Default::default()).map_err(|e| e.to_string())
    }
    pub fn preview_png(&self, max_side: u32) -> Result<Vec<u8>> {
        let doc = &self.session.active().ok_or("no active image project")?.doc;
        let side = if max_side == 0 {
            doc.size.width.max(doc.size.height)
        } else {
            max_side.min(4096)
        };
        let rgba = photocraft_compose::thumbnail(doc, side.max(1));
        let image = photocraft_codecs::Image::from_u8(
            rgba.width,
            rgba.height,
            photocraft_codecs::ChannelLayout::Rgba,
            rgba.pixels,
        )
        .map_err(|e| e.to_string())?;
        photocraft_codecs::encode(&image, photocraft_codecs::Format::Png, &Default::default())
            .map_err(|e| e.to_string())
    }
    pub fn inspect(&self) -> Result<Value> {
        let state = self.session.active().ok_or("no active image project")?;
        let raw = photocraft_engine::inspect::document(state);
        let layers = raw
            .get("layers")
            .and_then(Value::as_array)
            .map(|layers| layers.iter().map(normalize_layer).collect::<Vec<_>>())
            .unwrap_or_default();
        Ok(
            json!({"engine":"photocraft","buildId":BUILD,"width":state.doc.size.width,"height":state.doc.size.height,
            "name":state.doc.name,"durationMs":0,"fps":0,"layers":layers,"timeline":[],"warnings":self.warnings,"raw":raw}),
        )
    }
    fn new_project(&mut self, params: &Value) -> Result<()> {
        let (width, height) = dimensions(params)?;
        self.session = Session::new();
        self.warnings.clear();
        self.session.execute("file.new", json!({"name":params.get("title").and_then(Value::as_str).unwrap_or("Imagem"),"width":width,"height":height,"background":"transparent"})).map_err(|e| e.to_string())?;
        Ok(())
    }
    fn execute(&mut self, id: &str, params: &Value, context: &Value) -> Result<Value> {
        if id == "asset.import" {
            let asset_id = text(params, "assetId")?;
            let path = media_path(context, asset_id)
                .ok_or_else(|| format!("asset `{asset_id}` was not materialized"))?;
            let workspace = Workspace::from_params(context)?;
            let path = workspace.read_path(path)?;
            let bytes = std::fs::read(&path).map_err(|e| e.to_string())?;
            return photocraft_engine::file_cmds::place_bytes(
                &mut self.session,
                path.file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("asset.png"),
                bytes,
                None,
                params,
            )
            .map_err(|e| e.to_string());
        }
        if context.get("mediaRoot").is_some() {
            Workspace::from_params(context)?.check_command(id, params)?;
        }
        self.session
            .execute(id, params.clone())
            .map_err(|e| e.to_string())
    }
    pub fn dispatch(&mut self, method: &str, params: &Value) -> Result<Value> {
        if method == "engine.capabilities" {
            return Ok(capabilities());
        }
        if method == "engine.commands" {
            return Ok(capabilities()["commands"].clone());
        }
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(path) = params.get("nativePath").and_then(Value::as_str) {
            let ws = Workspace::from_params(params)?;
            let path = ws.read_path(path)?;
            self.open_bytes(
                "project.pcraft",
                &std::fs::read(path).map_err(|e| e.to_string())?,
            )?;
        }
        let mut results = Vec::new();
        match method {
            "project.new" => {
                self.new_project(params)?;
                self.migrate(params)?;
            }
            "project.open" | "project.inspect" | "project.save" => (),
            "engine.execute" | "project.execute" => {
                for (id, args) in commands(params)? {
                    results.push(self.execute(&id, &args, params)?);
                }
            }
            "undo" => {
                results.push(self.execute("edit.undo", &json!({}), params)?);
            }
            "redo" => {
                results.push(self.execute("edit.redo", &json!({}), params)?);
            }
            "render.frame" | "render.export" => {
                #[cfg(not(target_arch = "wasm32"))]
                {
                    let ws = Workspace::from_params(params)?;
                    let path = ws.write_path(text(params, "outputPath")?)?;
                    let format = params
                        .get("format")
                        .and_then(Value::as_str)
                        .unwrap_or("png");
                    let bytes = if method == "render.frame" || format == "png" {
                        self.preview_png(
                            params.get("maxSide").and_then(Value::as_u64).unwrap_or(0) as u32,
                        )?
                    } else {
                        let doc = &self.session.active().ok_or("no active project")?.doc;
                        let exported = photocraft_io::export(doc, format, &Default::default())
                            .map_err(|e| e.to_string())?;
                        self.warnings.extend(exported.warnings);
                        exported.bytes
                    };
                    photocraft_format::atomic_write(&path, &bytes).map_err(|e| e.to_string())?;
                    let inspection = self.inspect()?;
                    return Ok(
                        json!({"artifact":{"path":path,"mediaType":format!("image/{format}"),"width":inspection["width"],"height":inspection["height"]},"path":path,"width":inspection["width"],"height":inspection["height"],"warnings":self.warnings}),
                    );
                }
                #[cfg(target_arch = "wasm32")]
                return Err(
                    "use previewPng() for browser pixels; final export runs on a server worker"
                        .into(),
                );
            }
            _ => return Err(format!("unknown adapter method `{method}`")),
        }
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(output) = params.get("outputPath").and_then(Value::as_str) {
            let path = Workspace::from_params(params)?.write_path(output)?;
            photocraft_format::atomic_write(&path, &self.native_bytes()?)
                .map_err(|e| e.to_string())?;
        }
        Ok(
            json!({"inspection":self.inspect()?,"warnings":self.warnings,"nativePath":params.get("outputPath"),"results":results}),
        )
    }
    fn migrate(&mut self, params: &Value) -> Result<()> {
        if legacy_pages(params).len() > 1 {
            return Err("the host must create one native image project per carousel page".into());
        }
        for (index, page) in legacy_pages(params).iter().enumerate() {
            if index > 0 {
                self.warnings.push(format!("page {} remains in the archived original; import it as a separate native image project", index + 1));
                continue;
            }
            if let Some(background) = page.get("background") {
                self.session
                    .execute(
                        "layer.newFillLayer.solidColor",
                        json!({"name":"Fundo","color":background}),
                    )
                    .map_err(|e| e.to_string())?;
            }
            let mut layers = page
                .get("layers")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            layers.sort_by_key(|l| l.get("zIndex").and_then(Value::as_i64).unwrap_or(0));
            for layer in layers {
                let props = layer
                    .get("properties")
                    .cloned()
                    .unwrap_or_else(|| json!({}));
                let name = layer
                    .get("name")
                    .and_then(Value::as_str)
                    .unwrap_or("Camada");
                let x = layer.get("x").and_then(Value::as_f64).unwrap_or(0.0);
                let y = layer.get("y").and_then(Value::as_f64).unwrap_or(0.0);
                let w = layer.get("width").and_then(Value::as_f64).unwrap_or(100.0);
                let h = layer.get("height").and_then(Value::as_f64).unwrap_or(100.0);
                let result = match layer.get("kind").and_then(Value::as_str).unwrap_or("") {
                    "text" => {
                        let family = props.get("fontFamily").or_else(||props.get("font_family")).and_then(Value::as_str).unwrap_or("Liberation Sans");
                        let fonts = self.session.execute("type.fonts",json!({})).map_err(|e|e.to_string())?;
                        if !fonts["families"].as_array().is_some_and(|families|families.iter().any(|item|item.as_str().is_some_and(|f|f.eq_ignore_ascii_case(family)))) {
                            self.warnings.push(format!("Font `{family}` on `{name}` is unavailable; provide the font and review typography; original preserved"));
                        }
                        let size = props.get("fontSize").or_else(||props.get("font_size")).and_then(Value::as_f64).unwrap_or(48.0);
                        let weight = props.get("fontWeight").and_then(|value|value.as_u64().or_else(||value.as_str().and_then(|s|s.parse().ok()))).unwrap_or(if props.get("fontWeight").and_then(Value::as_str)==Some("bold") {700} else {400});
                        let mut parameters = json!({"name":name,"box":[x,y,w,h],"text":props.get("text").and_then(Value::as_str).unwrap_or(""),"size":size,"font":family,"weight":weight,"color":props.get("color").and_then(Value::as_str).unwrap_or("#ffffff"),"align":props.get("align").and_then(Value::as_str).unwrap_or("left")});
                        if let Some(spacing) = props.get("letterSpacing").or_else(||props.get("letterSpacingPx")).and_then(Value::as_f64) { parameters["tracking"]=json!(spacing/size.max(0.001)*1000.0); }
                        if let Some(leading) = props.get("lineHeight").and_then(Value::as_f64) { parameters["leading"]=json!(size*leading); }
                        if props.get("autoFit").and_then(Value::as_bool).unwrap_or(false) { self.warnings.push(format!("Automatic text fitting on `{name}` requires review in PhotoCraft; original preserved")); }
                        self.session.execute("type.create",parameters).map_err(|e|e.to_string())
                    },
                    "shape" => self.session.execute("shape.create", json!({"name":name,"kind":if props.get("shape").and_then(Value::as_str)==Some("ellipse") {"ellipse"} else if props.get("radius").and_then(Value::as_f64).unwrap_or(0.0)>0.0 {"roundedRect"} else {"rect"},"radii":props.get("radius").and_then(Value::as_f64).unwrap_or(0.0),"rect":[x,y,w,h],"fill":props.get("fill").and_then(Value::as_str).unwrap_or("#6c5ce7")})).map_err(|e| e.to_string()),
                    "image" => {
                        let asset_id = props.get("assetId").or_else(|| props.get("asset_id")).and_then(Value::as_str).unwrap_or("");
                        self.execute("asset.import", &json!({"assetId":asset_id,"center":[x+w/2.0,y+h/2.0],"fit":false}), params)
                    },
                    "group" => self.session.execute("layer.new.group", json!({"name":name})).map_err(|e| e.to_string()),
                    _ => Err("unsupported image layer type".into()),
                };
                match result {
                    Ok(r) => {
                        let id = r.get("layer").or_else(|| r.get("id")).cloned();
                        if let Some(id) = id {
                            if layer.get("kind").and_then(Value::as_str) == Some("image") {
                                let bounds = id.as_u64().and_then(|id| {
                                    self.session
                                        .active()
                                        .and_then(|state| {
                                            state.doc.layer(photocraft_engine::doc::LayerId(id))
                                        })
                                        .and_then(|layer| layer.surface())
                                        .map(|surface| surface.content_bounds())
                                });
                                if let Some(bounds) = bounds
                                    .filter(|bounds| bounds.width() > 0 && bounds.height() > 0)
                                {
                                    let sx = w / f64::from(bounds.width());
                                    let sy = h / f64::from(bounds.height());
                                    self.session.execute("edit.transform",json!({"layer":id,"matrix":[sx,0.0,0.0,sy,x-sx*f64::from(bounds.x0),y-sy*f64::from(bounds.y0)]})).map_err(|e|e.to_string())?;
                                }
                            }
                            let rotation = layer
                                .get("rotation")
                                .and_then(Value::as_f64)
                                .unwrap_or(0.0)
                                .to_radians();
                            if rotation != 0.0 {
                                let (a, b) = (rotation.cos(), rotation.sin());
                                let (cx, cy) = (x + w / 2.0, y + h / 2.0);
                                self.session.execute("edit.transform", json!({"layer":id,"matrix":[a,b,-b,a,cx-a*cx+b*cy,cy-b*cx-a*cy]})).map_err(|e| e.to_string())?;
                            }
                            self.session.execute("layer.setProps", json!({"layer":id,"opacity":layer.get("opacity").and_then(Value::as_f64).unwrap_or(1.0),"visible":layer.get("visible").and_then(Value::as_bool).unwrap_or(true),"locked":layer.get("locked").and_then(Value::as_bool).unwrap_or(false)})).map_err(|e| e.to_string())?;
                        }
                    }
                    Err(e) => self
                        .warnings
                        .push(format!("layer `{name}`: {e}; original preserved")),
                }
            }
        }
        Ok(())
    }
}
fn normalize_layer(raw: &Value) -> Value {
    json!({"id":raw["id"].to_string(),"name":raw["name"],"kind":raw["kind"],"visible":raw["visible"],"opacity":raw["opacity"],"properties":raw,"children":raw.get("children").and_then(Value::as_array).map(|v| v.iter().map(normalize_layer).collect::<Vec<_>>()).unwrap_or_default()})
}
pub fn capabilities() -> Value {
    let mut commands = photocraft_engine::command_specs().iter().map(|command| json!({"id":command.id,"label":command.label,"menu":command.menu,"params":command.params,"inputSchema":command_schema("photocraft",command.id,command.params)})).collect::<Vec<_>>();
    commands.push(json!({"id":"asset.import","label":"Importar material","inputSchema":{"type":"object","properties":{"assetId":{"type":"string"}},"required":["assetId"],"additionalProperties":true}}));
    clicko_craft_protocol::capability_isolation(&mut commands);
    json!({"engine":"photocraft","buildId":BUILD,"upstreamRevision":REVISION,"formatVersion":photocraft_format::FORMAT_VERSION,"commands":commands,"formats":["pcraft","png","jpg","webp","psd","tiff","exr"]})
}

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
impl Adapter {
    #[wasm_bindgen(constructor)]
    pub fn browser_new() -> Self {
        Self::default()
    }
    #[wasm_bindgen(js_name = request)]
    pub fn browser_request(&mut self, request: &str) -> String {
        clicko_craft_protocol::respond(request, "photocraft", |method, params| {
            self.dispatch(method, params)
        })
        .to_string()
    }
    #[wasm_bindgen(js_name = openNative)]
    pub fn browser_open(&mut self, bytes: &[u8]) -> std::result::Result<(), JsValue> {
        self.open_bytes("project.pcraft", bytes)
            .map_err(|e| JsValue::from_str(&e))
    }
    #[wasm_bindgen(js_name = saveNative)]
    pub fn browser_save(&self) -> std::result::Result<Vec<u8>, JsValue> {
        self.native_bytes().map_err(|e| JsValue::from_str(&e))
    }
    #[wasm_bindgen(js_name = previewPng)]
    pub fn browser_preview(&self, max_side: u32) -> std::result::Result<Vec<u8>, JsValue> {
        self.preview_png(max_side)
            .map_err(|e| JsValue::from_str(&e))
    }
    #[wasm_bindgen(js_name = importAsset)]
    pub fn browser_import(
        &mut self,
        name: &str,
        bytes: &[u8],
    ) -> std::result::Result<String, JsValue> {
        photocraft_engine::file_cmds::place_bytes(
            &mut self.session,
            name,
            bytes.to_vec(),
            None,
            &json!({}),
        )
        .map(|v| v.to_string())
        .map_err(|e| JsValue::from_str(&e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn native_roundtrip_and_actual_pixels() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch("project.new", &json!({"width":16,"height":12}))
            .unwrap();
        adapter.dispatch("engine.execute", &json!({"commands":[{"id":"shape.create","params":{"kind":"rect","rect":[0,0,16,12],"fill":"#ff0000"}}]})).unwrap();
        let png = adapter.preview_png(0).unwrap();
        assert_eq!(&png[..8], b"\x89PNG\r\n\x1a\n");
        let bytes = adapter.native_bytes().unwrap();
        let before = adapter.inspect().unwrap()["layers"].clone();
        adapter.open_bytes("test.pcraft", &bytes).unwrap();
        assert_eq!(adapter.inspect().unwrap()["layers"], before);
        assert_eq!(adapter.preview_png(0).unwrap(), png);
    }
    #[test]
    fn manual_and_agent_command_share_history() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch("project.new", &json!({"width":16,"height":12}))
            .unwrap();
        let initial = adapter.preview_png(0).unwrap();
        adapter.dispatch("engine.execute", &json!({"command":"shape.create","params":{"kind":"rect","rect":[0,0,16,12],"fill":"#ff0000"}})).unwrap();
        assert_ne!(adapter.preview_png(0).unwrap(), initial);
        adapter.dispatch("undo", &json!({})).unwrap();
        assert_eq!(adapter.preview_png(0).unwrap(), initial);
        adapter.dispatch("redo", &json!({})).unwrap();
        assert_ne!(adapter.preview_png(0).unwrap(), initial);
    }
}
