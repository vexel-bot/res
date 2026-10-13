#![forbid(unsafe_code)]
mod migration_motion;
mod migration_hierarchy;
mod migration_timeline;
use clicko_craft_protocol::{
    Result, Workspace, command_schema, commands, dimensions, legacy_pages, text,
};
use effectcraft_engine::project::render_queue::{
    Channels, OutputFormat, OutputModule, RenderSettings, TimeSpan,
};
use effectcraft_engine::{
    Importer, Services, Session,
    project::{Footage, ItemId, Project},
    render::FootageSource,
    time::Tick,
};
use image::ImageEncoder;
use serde_json::{Value, json};
use std::{
    collections::HashMap,
    sync::{Arc, RwLock},
};
#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

pub const REVISION: &str = "67434e90388b6dca4417555346fa6850b6f96033";
pub const BUILD: &str = "clicko-effectcraft-1.0.2+67434e90";

#[derive(Default)]
struct Store {
    files: RwLock<HashMap<String, Vec<u8>>>,
    workspace: RwLock<Option<Arc<Workspace>>>,
}
impl Store {
    fn put(&self, path: &str, bytes: Vec<u8>) {
        self.files
            .write()
            .unwrap_or_else(|e| e.into_inner())
            .insert(path.to_owned(), bytes);
    }
    fn resolved_footage(&self, footage: &Footage) -> Option<Footage> {
        if self
            .files
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .contains_key(&footage.path)
        {
            return Some(footage.clone());
        }
        let workspace = self
            .workspace
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .clone()?;
        let path = workspace.read_path(&footage.path).ok()?;
        let mut resolved = footage.clone();
        resolved.path = path.to_string_lossy().into_owned();
        Some(resolved)
    }
}
impl Services for Store {
    fn read_file(&self, path: &str) -> std::io::Result<Vec<u8>> {
        if let Some(bytes) = self
            .files
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .get(path)
        {
            return Ok(bytes.clone());
        }
        self.workspace
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .as_ref()
            .ok_or_else(|| std::io::Error::other("file is not registered in this session"))?
            .read(path)
    }
    fn write_file(&self, path: &str, data: &[u8]) -> std::io::Result<()> {
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(workspace) = self
            .workspace
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .as_ref()
        {
            return effectcraft_engine::config::atomic_write(
                &workspace.write_path(path).map_err(std::io::Error::other)?,
                data,
            );
        }
        self.put(path, data.to_vec());
        Ok(())
    }
    fn exists(&self, path: &str) -> bool {
        self.files
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .contains_key(path)
            || self
                .workspace
                .read()
                .unwrap_or_else(|e| e.into_inner())
                .as_ref()
                .is_some_and(|w| w.read_path(path).is_ok())
    }
    fn list_dir(&self, _: &str) -> Vec<String> {
        vec![]
    }
    fn is_dir(&self, _: &str) -> bool {
        false
    }
    fn store_file(&self, path: &str, data: &[u8]) -> std::io::Result<()> {
        self.write_file(path, data)
    }
}
struct Media {
    pool: Arc<effectcraft_media::MediaPool>,
    store: Arc<Store>,
}
impl Importer for Media {
    fn probe(&self, path: &str) -> std::result::Result<Footage, String> {
        if let Some(bytes) = self
            .store
            .files
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .get(path)
        {
            return effectcraft_media::probe_bytes(path, bytes.clone().into())
                .map_err(|e| e.to_string());
        }
        let workspace = self
            .store
            .workspace
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .clone()
            .ok_or("no workspace for media probing")?;
        let mut footage =
            effectcraft_media::probe(workspace.read_path(path)?).map_err(|e| e.to_string())?;
        footage.path = path.to_owned();
        Ok(footage)
    }
    fn register(&self, path: &str, bytes: &[u8]) {
        self.store.put(path, bytes.to_vec());
        self.pool.add_bytes(path, bytes.into());
    }
}
impl FootageSource for Media {
    fn frame(
        &self,
        item: ItemId,
        footage: &Footage,
        t: Tick,
    ) -> Option<Arc<effectcraft_engine::raster::Image>> {
        self.pool
            .frame(item, &self.store.resolved_footage(footage)?, t)
    }
    fn frame_at_size(
        &self,
        item: ItemId,
        footage: &Footage,
        t: Tick,
        w: u32,
        h: u32,
    ) -> Option<Arc<effectcraft_engine::raster::Image>> {
        self.pool
            .frame_at_size(item, &self.store.resolved_footage(footage)?, t, w, h)
    }
    fn audio(
        &self,
        item: ItemId,
        footage: &Footage,
        t: Tick,
        frames: usize,
        rate: u32,
    ) -> Option<Vec<f32>> {
        self.pool.audio(
            item,
            &self.store.resolved_footage(footage)?,
            t,
            frames,
            rate,
        )
    }
    fn aux(
        &self,
        item: ItemId,
        footage: &Footage,
        t: Tick,
    ) -> Option<Arc<effectcraft_engine::raster::AuxChannels>> {
        self.pool
            .aux(item, &self.store.resolved_footage(footage)?, t)
    }
    fn model(&self, item: ItemId, footage: &Footage) -> Option<Arc<effectcraft_model::Model>> {
        self.pool
            .model(item, &self.store.resolved_footage(footage)?)
    }
    fn vector_frame(
        &self,
        item: ItemId,
        footage: &Footage,
        scale: f64,
    ) -> Option<Arc<effectcraft_engine::raster::Image>> {
        self.pool
            .vector_frame(item, &self.store.resolved_footage(footage)?, scale)
    }
    fn set_cache_budget(&self, bytes: usize) {
        self.pool.set_budget(bytes);
    }
    fn cache_budget(&self) -> Option<usize> {
        Some(self.pool.budget())
    }
    fn purge(&self) {
        self.pool.clear();
    }
}

#[cfg_attr(target_arch = "wasm32", wasm_bindgen)]
pub struct Adapter {
    session: Session,
    store: Arc<Store>,
    media: Arc<Media>,
    warnings: Vec<String>,
}
impl Default for Adapter {
    fn default() -> Self {
        let store = Arc::new(Store::default());
        let media = Arc::new(Media {
            pool: Arc::new(effectcraft_media::MediaPool::new()),
            store: store.clone(),
        });
        let mut session = effectcraft_host::session();
        session.services = store.clone();
        session.footage = media.clone();
        session.importer = Some(media.clone());
        session.models_dir = None;
        Self {
            session,
            store,
            media,
            warnings: vec![],
        }
    }
}
impl Adapter {
    pub fn open_bytes(&mut self, bytes: &[u8]) -> Result<()> {
        let text = std::str::from_utf8(bytes).map_err(|e| e.to_string())?;
        let project = Project::from_json(text).map_err(|e| e.to_string())?;
        self.session.project = Arc::new(project);
        self.session.history = Default::default();
        self.session.state = Default::default();
        let first_comp = self.session.project.comps().next().map(|(id, _)| *id);
        if let Some(id) = first_comp {
            self.session.open_comp(id);
        }
        self.session.mark_saved();
        Ok(())
    }
    pub fn native_bytes(&self) -> Result<Vec<u8>> {
        self.session
            .project
            .to_file_json()
            .map(String::into_bytes)
            .map_err(|e| e.to_string())
    }
    pub fn preview_png(&self, time: f64, max_side: u32) -> Result<Vec<u8>> {
        let comp = self
            .session
            .active_comp_id()
            .ok_or("no active composition")?;
        let (w, h, rgba) = self
            .session
            .render_rgba8_alpha(comp, Tick::from_seconds_f64(time), max_side.min(4096), true)
            .map_err(|e| e.to_string())?;
        let mut bytes = Vec::new();
        image::codecs::png::PngEncoder::new(&mut bytes)
            .write_image(&rgba, w, h, image::ExtendedColorType::Rgba8)
            .map_err(|e| e.to_string())?;
        Ok(bytes)
    }
    pub fn inspect(&mut self) -> Result<Value> {
        let project = self
            .session
            .execute("project.summary", json!({}))
            .map_err(|e| e.to_string())?;
        let comp = self
            .session
            .execute("comp.info", json!({}))
            .map_err(|e| e.to_string())?;
        let mut layers = Vec::new();
        let mut timeline = Vec::new();
        for layer in comp
            .get("layers")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            let properties = self
                .session
                .execute("layer.tree", json!({"layer":layer["id"],"depth":12}))
                .map_err(|e| e.to_string())?;
            layers.push(json!({"id":layer["id"].to_string(),"name":layer["name"],"kind":layer["type"],"properties":properties}));
            timeline.push(json!({"id":layer["id"].to_string(),"trackId":layer["id"].to_string(),"name":layer["name"],"kind":layer["type"],"startMs":layer["in"].as_f64().unwrap_or(0.0)*1000.0,"durationMs":(layer["out"].as_f64().unwrap_or(0.0)-layer["in"].as_f64().unwrap_or(0.0))*1000.0,"properties":layer}));
        }
        Ok(
            json!({"engine":"effectcraft","buildId":BUILD,"name":comp["name"],"width":comp["width"],"height":comp["height"],"fps":comp["frameRate"],"durationMs":comp["duration"].as_f64().unwrap_or(0.0)*1000.0,"layers":layers,"timeline":timeline,"warnings":self.warnings,"raw":{"project":project,"composition":comp}}),
        )
    }
    fn execute(&mut self, id: &str, params: &Value, context: &Value) -> Result<Value> {
        if id == "inspector.transform" {
            let layer = params
                .get("layer")
                .and_then(Value::as_u64)
                .ok_or("missing layer")?;
            let fields = [
                ("rotation", "transform/rotation"),
                ("opacity", "transform/opacity"),
            ];
            let mut results = Vec::new();
            for (field, path) in fields {
                if let Some(value) = params.get(field) {
                    results.push(
                        self.session
                            .execute_checked(
                                "prop.set",
                                json!({"layer":layer,"path":path,"value":value}),
                            )
                            .map_err(|e| e.to_string())?,
                    );
                }
            }
            if let Some(position) = params.get("position") {
                results.push(
                    self.session
                        .execute_checked(
                            "prop.set",
                            json!({"layer":layer,"path":"transform/position","value":position}),
                        )
                        .map_err(|e| e.to_string())?,
                );
            }
            if let Some(scale) = params.get("scale") {
                results.push(
                    self.session
                        .execute_checked(
                            "prop.set",
                            json!({"layer":layer,"path":"transform/scale","value":scale}),
                        )
                        .map_err(|e| e.to_string())?,
                );
            }
            return Ok(json!({"results":results}));
        }
        if id == "asset.import" {
            let asset = text(params, "assetId")?;
            let media = context
                .get("media")
                .and_then(Value::as_array)
                .and_then(|list| list.iter().find(|m| m["assetId"] == asset))
                .ok_or_else(|| format!("asset `{asset}` was not materialized"))?;
            let path = media
                .get("relativePath")
                .or_else(|| media.get("path"))
                .and_then(Value::as_str)
                .ok_or("missing asset path")?;
            return self.session.execute("file.import", json!({"paths":[path],"sequence":false,"addToComp":params.get("addToComp").and_then(Value::as_bool).unwrap_or(true)})).map_err(|e| e.to_string());
        }
        if context.get("mediaRoot").is_some() {
            Workspace::from_params(context)?.check_command(id, params)?;
        }
        self.session
            .execute_checked(id, params.clone())
            .map_err(|e| e.to_string())
    }
    pub fn dispatch(&mut self, method: &str, params: &Value) -> Result<Value> {
        if method == "engine.capabilities" {
            return Ok(capabilities());
        }
        if method == "engine.commands" {
            return Ok(capabilities()["commands"].clone());
        }
        if params.get("mediaRoot").is_some() {
            *self
                .store
                .workspace
                .write()
                .unwrap_or_else(|e| e.into_inner()) =
                Some(Arc::new(Workspace::from_params(params)?));
        }
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(path) = params.get("nativePath").and_then(Value::as_str) {
            self.open_bytes(
                &Workspace::from_params(params)?
                    .read(path)
                    .map_err(|e| e.to_string())?,
            )?;
        }
        let mut results = Vec::new();
        match method {
            "project.new" => {
                let (width, height) = dimensions(params)?;
                self.warnings.clear();
                self.session
                    .execute("file.newProject", json!({}))
                    .map_err(|e| e.to_string())?;
                let mut duration = params
                    .get("durationMs")
                    .and_then(Value::as_f64)
                    .unwrap_or(5000.0)
                    / 1000.0;
                let mut fps = params.get("fps").and_then(Value::as_f64).unwrap_or(30.0);
                if let Some(timeline) = params
                    .pointer("/legacyDocument/composition/mediaTimeline")
                    .filter(|v| v.is_object())
                {
                    let n = timeline
                        .pointer("/frameRate/numerator")
                        .and_then(Value::as_f64)
                        .unwrap_or(30.0);
                    let d = timeline
                        .pointer("/frameRate/denominator")
                        .and_then(Value::as_f64)
                        .unwrap_or(1.0);
                    if n > 0.0 && d > 0.0 {
                        fps = n / d;
                        duration = timeline
                            .get("durationFrames")
                            .and_then(Value::as_f64)
                            .unwrap_or(duration * fps)
                            / fps;
                    }
                }
                if let Some(graph) = params.get("legacyMotionGraph").filter(|g| g.is_object()) {
                    let n = graph
                        .pointer("/frameRate/numerator")
                        .and_then(Value::as_f64)
                        .unwrap_or(30.0);
                    let d = graph
                        .pointer("/frameRate/denominator")
                        .and_then(Value::as_f64)
                        .unwrap_or(1.0);
                    if n.is_finite() && d.is_finite() && n > 0.0 && d > 0.0 {
                        fps = n / d;
                        if let Some(frames) = graph
                            .get("durationFrames")
                            .and_then(Value::as_f64)
                            .filter(|f| f.is_finite() && *f > 0.0)
                        {
                            duration = frames / fps;
                        }
                    }
                }
                self.session.execute("comp.new", json!({"name":params.get("title").and_then(Value::as_str).unwrap_or("Composição"),"width":width,"height":height,"duration":duration,"fps":fps})).map_err(|e| e.to_string())?;
                self.migrate(params)?;
            }
            "project.open" | "project.inspect" | "project.save" => (),
            "engine.execute" | "project.execute" => {
                for (id, args) in commands(params)? {
                    results.push(self.execute(&id, &args, params)?);
                }
            }
            "undo" => {
                if !self.session.undo() {
                    return Err("nothing to undo".into());
                }
            }
            "redo" => {
                if !self.session.redo() {
                    return Err("nothing to redo".into());
                }
            }
            "render.frame" => {
                #[cfg(not(target_arch = "wasm32"))]
                {
                    let path =
                        Workspace::from_params(params)?.write_path(text(params, "outputPath")?)?;
                    let bytes = self.preview_png(
                        clicko_craft_protocol::frame_seconds(
                            params,
                            self.session
                                .active_comp()
                                .ok_or("no active composition")?
                                .frame_rate
                                .as_f64(),
                        )?,
                        params.get("maxSide").and_then(Value::as_u64).unwrap_or(0) as u32,
                    )?;
                    effectcraft_engine::config::atomic_write(&path, &bytes)
                        .map_err(|e| e.to_string())?;
                    return Ok(
                        json!({"path":path,"artifact":{"path":path,"mediaType":"image/png"},"warnings":self.warnings}),
                    );
                }
                #[cfg(target_arch = "wasm32")]
                return Err("use previewPng() for browser pixels".into());
            }
            "render.export" => {
                #[cfg(not(target_arch = "wasm32"))]
                {
                    let path =
                        Workspace::from_params(params)?.write_path(text(params, "outputPath")?)?;
                    let path_text = path.to_string_lossy().into_owned();
                    let fmt = params
                        .get("format")
                        .and_then(Value::as_str)
                        .unwrap_or("mp4");
                    if fmt == "png" {
                        let time = clicko_craft_protocol::frame_seconds(
                            params,
                            self.session
                                .active_comp()
                                .ok_or("no composition")?
                                .frame_rate
                                .as_f64(),
                        )?;
                        let bytes = self.preview_png(time, 0)?;
                        effectcraft_engine::config::atomic_write(&path, &bytes)
                            .map_err(|e| e.to_string())?;
                        return Ok(
                            json!({"path":path,"frames":1,"artifact":{"path":path,"mediaType":"image/png"},"warnings":self.warnings}),
                        );
                    }
                    let format = match fmt {
                        "mp4" | "h264" => OutputFormat::H264,
                        "mov" | "prores" => OutputFormat::ProRes,
                        "webm" => OutputFormat::WebM,
                        "gif" => OutputFormat::Gif,
                        "png" => OutputFormat::PngSequence,
                        "wav" => OutputFormat::Wav,
                        _ => return Err(format!("unknown export format `{fmt}`")),
                    };
                    let settings = RenderSettings {
                        time_span: TimeSpan::LengthOfComp,
                        storage_overflow: false,
                        ..Default::default()
                    };
                    let output = OutputModule {
                        format,
                        channels: if params
                            .get("alpha")
                            .and_then(Value::as_bool)
                            .unwrap_or(false)
                        {
                            Channels::Rgba
                        } else {
                            Channels::Rgb
                        },
                        ..Default::default()
                    };
                    let job = effectcraft_export::Job {
                        project: &self.session.project,
                        footage: self.session.footage.as_ref(),
                        expr: self.session.expr.as_deref(),
                        accel: None,
                        comp: self.session.active_comp_id().ok_or("no active comp")?,
                        settings: &settings,
                        output: &output,
                        path: &path_text,
                        sink: None,
                        nested_switches: true,
                        options: Default::default(),
                    };
                    let report = effectcraft_export::export(&job, &mut |_| true)
                        .map_err(|e| e.to_string())?;
                    let media_type = match fmt {
                        "mov" | "prores" => "video/quicktime",
                        "webm" => "video/webm",
                        "gif" => "image/gif",
                        "wav" => "audio/wav",
                        "png" => "image/png",
                        _ => "video/mp4",
                    };
                    return Ok(
                        json!({"path":report.path,"artifact":{"path":report.path,"mediaType":media_type,"width":report.width,"height":report.height},"frames":report.frames,"bytes":report.bytes,"warnings":self.warnings}),
                    );
                }
                #[cfg(target_arch = "wasm32")]
                return Err("final video export runs on a server worker".into());
            }
            _ => return Err(format!("unknown adapter method `{method}`")),
        }
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(output) = params.get("outputPath").and_then(Value::as_str) {
            effectcraft_engine::config::atomic_write(
                &Workspace::from_params(params)?.write_path(output)?,
                &self.native_bytes()?,
            )
            .map_err(|e| e.to_string())?;
        }
        Ok(
            json!({"inspection":self.inspect()?,"nativePath":params.get("outputPath"),"warnings":self.warnings,"results":results}),
        )
    }
    fn migrate(&mut self, params: &Value) -> Result<()> {
        for (index, page) in legacy_pages(params).iter().enumerate() {
            let mut native_layers = HashMap::new();
            if index > 0 {
                self.session.execute("comp.new", json!({"name":format!("Página {}", index+1),"width":page.get("width"),"height":page.get("height"),"duration":page.get("durationMs").and_then(Value::as_f64).unwrap_or(5000.0)/1000.0})).map_err(|e| e.to_string())?;
            }
            if let Some(background) = page.get("background") {
                // Craft solids store RGB separately from transform opacity.
                // Translating RGBA as an RGB string makes transparent overlays opaque.
                let (rgb, alpha) = match background.as_str() {
                    Some(hex) if hex.len() == 9 && hex.starts_with('#') => (
                        json!(&hex[..7]),
                        f64::from(u8::from_str_radix(&hex[7..], 16).map_err(|e| e.to_string())?) / 255.0,
                    ),
                    _ => (background.clone(), 1.0),
                };
                self.session
                    .execute("comp.settings", json!({"background":rgb}))
                    .map_err(|e| e.to_string())?;
                if alpha > 0.0 {
                    let created = self.session
                        .execute("layer.newSolid", json!({"name":"Fundo","color":rgb}))
                        .map_err(|e| e.to_string())?;
                    let id = created["layer"].as_u64().ok_or("background layer missing")?;
                    self.session.execute("prop.set", json!({"layer":id,"path":"transform/opacity","value":alpha * 100.0})).map_err(|e|e.to_string())?;
                }
            }
            if index == 0 {
                native_layers.extend(migration_timeline::apply(self, params));
            }
            for layer in page
                .get("layers")
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
            {
                let p = layer
                    .get("properties")
                    .cloned()
                    .unwrap_or_else(|| json!({}));
                let x = layer.get("x").and_then(Value::as_f64).unwrap_or(0.0);
                let y = layer.get("y").and_then(Value::as_f64).unwrap_or(0.0);
                let w = layer.get("width").and_then(Value::as_f64).unwrap_or(100.0);
                let h = layer.get("height").and_then(Value::as_f64).unwrap_or(100.0);
                let name = layer
                    .get("name")
                    .and_then(Value::as_str)
                    .unwrap_or("Camada");
                let result = match layer.get("kind").and_then(Value::as_str).unwrap_or("") {
                    "text" => self.session.execute("layer.newText", json!({"name":name,"text":p.get("text"),"box":[x,y,w,h],"fill":p.get("color").and_then(Value::as_str).unwrap_or("#ffffff"),"size":p.get("fontSize").and_then(Value::as_f64).unwrap_or(48.0)})).map_err(|e| e.to_string()),
                    "shape" => self.session.execute("layer.newShape", json!({"name":name,"kind":"rect","position":[x+w/2.0,y+h/2.0],"size":[w,h],"fill":p.get("fill").and_then(Value::as_str).unwrap_or("#6c5ce7")})).map_err(|e| e.to_string()),
                    "group" => self.session.execute("layer.newNull", json!({"name":name})).map_err(|e|e.to_string()),
                    "image"|"video"|"audio" => self.execute("asset.import", &json!({"assetId":p.get("assetId").or_else(|| p.get("asset_id")),"addToComp":true}), params),
                    _ => Err("unsupported composition layer type".into()),
                };
                match result {
                    Err(e) => self
                        .warnings
                        .push(format!("layer `{name}`: {e}; original preserved")),
                    Ok(result) => {
                        let id = result
                            .get("layer")
                            .and_then(Value::as_u64)
                            .or_else(|| self.session.state.selected_layers.first().map(|id| id.0));
                        if let Some(id) = id {
                            if let Some(legacy_id) = layer.get("id").and_then(Value::as_str) {
                                native_layers.insert(legacy_id.to_owned(), id);
                            }
                            if let Some(timing) = p.get("editorialTiming") {
                                let fps = timing.get("fps").and_then(Value::as_f64).unwrap_or(0.0);
                                let start = timing
                                    .get("startFrame")
                                    .and_then(Value::as_f64)
                                    .unwrap_or(0.0);
                                let duration = timing
                                    .get("durationFrames")
                                    .and_then(Value::as_f64)
                                    .unwrap_or(0.0);
                                if fps > 0.0 && duration > 0.0 {
                                    if let Err(error) = self.session.execute("layer.timing", json!({"layers":[id],"start":start/fps,"in":start/fps,"out":(start+duration)/fps})) {
                                        self.warnings.push(format!("layer `{name}` timing: {error}; original preserved"));
                                    }
                                } else {
                                    self.warnings.push(format!(
                                        "layer `{name}` has invalid timing; original preserved"
                                    ));
                                }
                            }
                            self.session.execute("prop.set",json!({"layer":id,"path":"transform/opacity","value":layer.get("opacity").and_then(Value::as_f64).unwrap_or(1.0)*100.0})).map_err(|e|e.to_string())?;
                            self.session.execute("prop.set",json!({"layer":id,"path":"transform/rotation","value":layer.get("rotation").and_then(Value::as_f64).unwrap_or(0.0)})).map_err(|e|e.to_string())?;
                            if matches!(
                                layer.get("kind").and_then(Value::as_str),
                                Some("image" | "video" | "audio")
                            ) {
                                self.session.execute("prop.set",json!({"layer":id,"path":"transform/position","value":[x+w/2.0,y+h/2.0,0.0]})).map_err(|e|e.to_string())?;
                                let dimensions = self
                                    .session
                                    .active_comp()
                                    .and_then(|c| c.layer(effectcraft_engine::project::LayerId(id)))
                                    .and_then(|l| l.source.item())
                                    .and_then(|item| self.session.project.item(item))
                                    .and_then(|item| item.dimensions());
                                if let Some((sw, sh)) =
                                    dimensions.filter(|(sw, sh)| *sw > 0 && *sh > 0)
                                {
                                    self.session.execute("prop.set",json!({"layer":id,"path":"transform/scale","value":[w/f64::from(sw)*100.0,h/f64::from(sh)*100.0,100.0]})).map_err(|e|e.to_string())?;
                                }
                            }
                            self.session.execute("layer.setSwitch",json!({"layers":[id],"switch":"video","value":layer.get("visible").and_then(Value::as_bool).unwrap_or(true)})).map_err(|e|e.to_string())?;
                            self.session.execute("layer.setSwitch",json!({"layers":[id],"switch":"lock","value":layer.get("locked").and_then(Value::as_bool).unwrap_or(false)})).map_err(|e|e.to_string())?;
                        }
                    }
                }
            }
            let graph = params.get("legacyMotionGraph").filter(|value|value.is_object()).unwrap_or(&Value::Null);
            let (parents, warnings) = migration_hierarchy::apply(&mut self.session, page, graph, &native_layers);
            self.warnings.extend(warnings);
            {
                self.warnings.extend(migration_motion::apply(
                    &mut self.session,
                    graph,
                    &native_layers,
                    page,
                    &parents,
                ));
            }
        }
        Ok(())
    }
}

pub fn capabilities() -> Value {
    let mut commands = effectcraft_engine::command_specs().iter().map(|command| {
        let known = command_schema("effectcraft", command.id, command.params);
        let mut schema = effectcraft_engine::commands::params_schema(command);
        if let Some(fields) = schema.get_mut("properties").and_then(Value::as_object_mut) {
            for (key, spec) in fields.iter_mut() {
                if let Some(typed) = known.get("properties").and_then(|p| p.get(key)) { *spec = typed.clone(); }
                else if ["layer","comp","index","width","height","depth"].contains(&key.as_str()) { spec["type"] = json!("integer"); }
                else if ["size","time","duration","delta","opacity","rotation"].contains(&key.as_str()) { spec["type"] = json!("number"); }
                else if ["visible","enabled","add","toggle","edit","vertical","merge","selected","offset"].contains(&key.as_str()) { spec["type"] = json!("boolean"); }
                // The registry description is authoritative. Unspecified parameter
                // types must remain open; strings were incorrectly rejecting native
                // arrays, vector properties, IDs by name and structured effects.
            }
        }
        json!({"id":command.id,"label":command.label,"menu":command.menu,"params":command.params,"inputSchema":schema})
    }).collect::<Vec<_>>();
    commands.push(json!({"id":"asset.import","label":"Importar material","inputSchema":{"type":"object","properties":{"assetId":{"type":"string"},"addToComp":{"type":"boolean"}},"required":["assetId"],"additionalProperties":true}}));
    commands.push(json!({"id":"inspector.transform","label":"Transformar elemento","inputSchema":{"type":"object","properties":{"layer":{"type":"integer"},"position":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"scale":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"rotation":{"type":"number"},"opacity":{"type":"number","minimum":0,"maximum":100}},"required":["layer"],"additionalProperties":false}}));
    clicko_craft_protocol::capability_isolation(&mut commands);
    json!({"engine":"effectcraft","buildId":BUILD,"upstreamRevision":REVISION,"formatVersion":effectcraft_engine::project::SCHEMA_VERSION,"commands":commands,"formats":["ecproj","mp4","mov","webm","gif","png","wav"]})
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
        clicko_craft_protocol::respond(request, "effectcraft", |method, params| {
            self.dispatch(method, params)
        })
        .to_string()
    }
    #[wasm_bindgen(js_name = openNative)]
    pub fn browser_open(&mut self, bytes: &[u8]) -> std::result::Result<(), JsValue> {
        self.open_bytes(bytes).map_err(|e| JsValue::from_str(&e))
    }
    #[wasm_bindgen(js_name = saveNative)]
    pub fn browser_save(&self) -> std::result::Result<Vec<u8>, JsValue> {
        self.native_bytes().map_err(|e| JsValue::from_str(&e))
    }
    #[wasm_bindgen(js_name = previewPng)]
    pub fn browser_preview(
        &self,
        time: f64,
        max_side: u32,
    ) -> std::result::Result<Vec<u8>, JsValue> {
        self.preview_png(time, max_side)
            .map_err(|e| JsValue::from_str(&e))
    }
    #[wasm_bindgen(js_name = registerAsset)]
    pub fn browser_register(&mut self, path: &str, bytes: &[u8]) {
        self.store.put(path, bytes.to_vec());
        self.media.pool.add_bytes(path, bytes.into());
    }
    #[wasm_bindgen(js_name = importAsset)]
    pub fn browser_import(
        &mut self,
        name: &str,
        bytes: &[u8],
    ) -> std::result::Result<String, JsValue> {
        self.browser_register(name, bytes);
        self.session
            .execute(
                "file.import",
                json!({"paths":[name],"sequence":false,"addToComp":true}),
            )
            .map(|v| v.to_string())
            .map_err(|e| JsValue::from_str(&e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rgba_background_alpha_survives_native_reopening() {
        for (color, expected_alpha) in [("#ff000000", 0u8), ("#ff000080", 128), ("#ff0000", 255)] {
            let mut adapter = Adapter::default();
            adapter.dispatch("project.new", &json!({"width":16,"height":16,
                "legacyDocument":{"composition":{"pages":[{"width":16,"height":16,"background":color,"layers":[]}]}}
            })).unwrap();
            let png = adapter.preview_png(0.0, 0).unwrap();
            let image = image::load_from_memory(&png).unwrap().to_rgba8();
            assert_eq!(image.get_pixel(8, 8).0[3], expected_alpha, "{color}");
            let bytes = adapter.native_bytes().unwrap();
            adapter.open_bytes(&bytes).unwrap();
            assert_eq!(png, adapter.preview_png(0.0, 0).unwrap());
        }
    }
    #[test]
    fn media_timeline_trim_survives_native_reopening() {
        let root =
            std::env::temp_dir().join(format!("clicko-effect-timeline-{}", std::process::id()));
        std::fs::create_dir_all(&root).unwrap();
        let mut png = Vec::new();
        let pixels: Vec<u8> = (0..16 * 16).flat_map(|_| [255, 0, 0, 255]).collect();
        image::codecs::png::PngEncoder::new(&mut png)
            .write_image(&pixels, 16, 16, image::ExtendedColorType::Rgba8)
            .unwrap();
        std::fs::write(root.join("source.png"), png).unwrap();
        let mut adapter = Adapter::default();
        adapter.dispatch("project.new", &json!({"mediaRoot":root,"width":16,"height":16,
            "media":[{"assetId":"fixture-image","relativePath":"source.png"}],
            "legacyDocument":{"composition":{"pages":[{"width":16,"height":16,"layers":[]}],"mediaTimeline":{"frameRate":{"numerator":10,"denominator":1},"durationFrames":10,"tracks":[{"id":"video","kind":"video","clips":[{"id":"trimmed-image","assetId":"fixture-image","timeline":{"startFrame":2,"durationFrames":4}}]}]}}}
        })).unwrap();
        assert!(adapter.warnings.is_empty(), "{:?}", adapter.warnings);
        let absent = adapter.preview_png(0.0, 0).unwrap();
        let visible = adapter.preview_png(0.2, 0).unwrap();
        assert_ne!(absent, visible);
        assert_eq!(absent, adapter.preview_png(0.6, 0).unwrap());
        let bytes = adapter.native_bytes().unwrap();
        adapter.open_bytes(&bytes).unwrap();
        assert_eq!(visible, adapter.preview_png(0.2, 0).unwrap());
        let output = root.join("frame.png");
        adapter
            .dispatch(
                "render.frame",
                &json!({"mediaRoot":root,"outputPath":output,"frame":2}),
            )
            .unwrap();
        assert_eq!(visible, std::fs::read(&output).unwrap());
        std::fs::remove_file(output).unwrap();
        std::fs::remove_file(root.join("source.png")).unwrap();
        std::fs::remove_dir(root).unwrap();
    }
    #[test]
    fn authored_graphics_timing_survives_native_reopening() {
        let mut adapter = Adapter::default();
        adapter.dispatch("project.new", &json!({"width":16,"height":16,"fps":10,"durationMs":1000,
            "legacyDocument":{"composition":{"pages":[{"width":16,"height":16,"layers":[{"id":"square","kind":"shape","name":"Square","x":0,"y":0,"width":8,"height":8,"properties":{"fill":"#ff0000","editorialTiming":{"fps":10,"startFrame":2,"durationFrames":4}}}]}]}}
        })).unwrap();
        assert!(adapter.warnings.is_empty(), "{:?}", adapter.warnings);
        let absent = adapter.preview_png(0.0, 0).unwrap();
        let visible = adapter.preview_png(0.2, 0).unwrap();
        assert_ne!(absent, visible);
        assert_eq!(absent, adapter.preview_png(0.6, 0).unwrap());
        let bytes = adapter.native_bytes().unwrap();
        adapter.open_bytes(&bytes).unwrap();
        assert_eq!(visible, adapter.preview_png(0.2, 0).unwrap());
    }
    #[test]
    fn migrated_cycles_and_group_compositing_are_explicit_review_items() {
        let mut adapter=Adapter::default();
        adapter.dispatch("project.new", &json!({"width":24,"height":24,"legacyDocument":{"composition":{"pages":[{
            "width":24,"height":24,"layers":[
                {"id":"a","kind":"group","properties":{"parentId":"b"}},
                {"id":"b","kind":"group","properties":{"parentId":"a"}},
                {"id":"c","kind":"group","opacity":0.5,"properties":{}},
                {"id":"s1","kind":"shape","properties":{"parentId":"c"}},
                {"id":"s2","kind":"shape","properties":{"parentId":"c"}}
            ]}]}}
        })).unwrap();
        assert_eq!(adapter.warnings.iter().filter(|warning|warning.contains("Cyclic")).count(),2);
        assert!(adapter.warnings.iter().any(|warning|warning.contains("compositing review")));
        assert!(adapter.preview_png(0.0,0).is_ok());
    }
    #[test]
    fn migrated_group_pivot_animation_and_inherited_alpha_survive_reopening() {
        let mut adapter = Adapter::default();
        adapter.dispatch("project.new", &json!({"width":48,"height":48,"fps":10,"durationMs":200,
            "legacyDocument":{"composition":{"pages":[{"width":48,"height":48,"background":"#00000000","layers":[
                {"id":"child","kind":"shape","x":4,"y":0,"width":4,"height":4,"opacity":0.5,"properties":{"fill":"#ff0000"}},
                {"id":"group","kind":"group","x":20,"y":20,"width":16,"height":16,"rotation":90,"opacity":0.5,"properties":{}}
            ]}]}},
            "legacyMotionGraph":{"frameRate":{"numerator":10,"denominator":1},"durationFrames":2,
                "nodes":[{"nodeId":"g","targetLayerId":"group","transformOriginX":0,"transformOriginY":0},
                    {"nodeId":"c","targetLayerId":"child","parentNodeId":"g"}],
                "tracks":[{"targetLayerId":"group","property":"position_x","keyframes":[{"frame":0,"value":0},{"frame":1,"value":8}]},
                    {"targetLayerId":"group","property":"opacity","keyframes":[{"frame":0,"value":0.5},{"frame":1,"value":1.0}]}]}
        })).unwrap();
        assert!(adapter.warnings.is_empty(), "{:?}",adapter.warnings);
        let first=adapter.preview_png(0.0,0).unwrap();
        let last=adapter.preview_png(0.1,0).unwrap();
        let a=image::load_from_memory(&first).unwrap().to_rgba8();
        let b=image::load_from_memory(&last).unwrap().to_rgba8();
        assert_eq!(a.get_pixel(17,25).0,[255,0,0,64]);
        assert_eq!(a.get_pixel(25,25).0,[0,0,0,0]);
        assert_eq!(b.get_pixel(25,25).0,[255,0,0,128]);
        assert_eq!(b.get_pixel(17,25).0,[0,0,0,0]);
        let bytes=adapter.native_bytes().unwrap();
        adapter.open_bytes(&bytes).unwrap();
        assert_eq!(first,adapter.preview_png(0.0,0).unwrap());
        assert_eq!(last,adapter.preview_png(0.1,0).unwrap());
        let comp=adapter.session.active_comp().unwrap();
        assert!(comp.layers.iter().any(|layer|layer.parent.is_some()));
    }
    #[test]
    fn migrated_leaf_pivot_and_hidden_static_group_preserve_pixels() {
        let mut adapter=Adapter::default();
        adapter.dispatch("project.new", &json!({"width":24,"height":24,"legacyDocument":{"composition":{"pages":[{
            "width":24,"height":24,"background":"#00000000","layers":[
                {"id":"leaf","kind":"shape","x":8,"y":8,"width":4,"height":8,"rotation":90,"properties":{"fill":"#ff0000"}},
                {"id":"hidden","kind":"group","x":0,"y":0,"width":24,"height":24,"visible":false,"properties":{}},
                {"id":"hidden-child","kind":"shape","x":12,"y":12,"width":8,"height":8,"properties":{"fill":"#0000ff","parentId":"hidden"}}
            ]}]}},"legacyMotionGraph":{"frameRate":{"numerator":30,"denominator":1},"durationFrames":1,
                "nodes":[{"nodeId":"n","targetLayerId":"leaf","transformOriginX":0,"transformOriginY":0}],"tracks":[]}
        })).unwrap();
        assert!(adapter.warnings.is_empty(),"{:?}",adapter.warnings);
        let png=adapter.preview_png(0.0,0).unwrap();
        let image=image::load_from_memory(&png).unwrap().to_rgba8();
        assert_eq!(image.get_pixel(2,10).0,[255,0,0,255]);
        assert_eq!(image.get_pixel(15,15).0,[0,0,0,0]);
        let bytes=adapter.native_bytes().unwrap();
        adapter.open_bytes(&bytes).unwrap();
        assert_eq!(png,adapter.preview_png(0.0,0).unwrap());
    }
    #[test]
    fn migrated_motion_changes_native_pixels_and_survives_reopening() {
        let mut adapter = Adapter::default();
        adapter.dispatch("project.new", &json!({"width":16,"height":16,"fps":10,"durationMs":1000,
            "legacyDocument":{"composition":{"pages":[{"width":16,"height":16,"layers":[{"id":"square","kind":"shape","name":"Square","x":0,"y":0,"width":8,"height":8,"properties":{"fill":"#ff0000"}}]}]}},
            "legacyMotionGraph":{"frameRate":{"numerator":10,"denominator":1},"durationFrames":10,"tracks":[{"targetLayerId":"square","property":"opacity","keyframes":[{"frame":0,"value":0.0,"easing":"ease_in"},{"frame":9,"value":1.0}]}]}
        })).unwrap();
        assert!(adapter.warnings.is_empty(), "{:?}", adapter.warnings);
        let first = adapter.preview_png(0.0, 0).unwrap();
        let last = adapter.preview_png(0.9, 0).unwrap();
        assert_ne!(first, last);
        let bytes = adapter.native_bytes().unwrap();
        adapter.open_bytes(&bytes).unwrap();
        assert_eq!(first, adapter.preview_png(0.0, 0).unwrap());
        assert_eq!(last, adapter.preview_png(0.9, 0).unwrap());
    }
    #[test]
    fn large_motion_import_preserves_all_frames_in_one_native_history_step() {
        let mut adapter=Adapter::default();
        adapter.dispatch("project.new", &json!({"width":16,"height":16,"fps":10,"durationMs":1_200_000,
            "legacyDocument":{"composition":{"pages":[{"width":16,"height":16,"background":"#00000000","layers":[
                {"id":"square","kind":"shape","x":0,"y":0,"width":8,"height":8,"properties":{"fill":"#ff0000"}}
            ]}]}},"legacyMotionGraph":{"frameRate":{"numerator":10,"denominator":1},"durationFrames":12_000,
                "tracks":[{"targetLayerId":"square","property":"opacity","keyframes":[
                    {"frame":0,"value":0.0,"easing":"linear"},{"frame":11_999,"value":1.0}]}]}
        })).unwrap();
        assert!(adapter.warnings.is_empty(),"{:?}",adapter.warnings);
        let comp=adapter.session.active_comp().unwrap();
        let layer=comp.layers.iter().find(|layer|layer.name=="Camada").unwrap();
        let opacity=layer.props.prop("transform/opacity").unwrap();
        assert_eq!(opacity.keys.len(),12_000);
        assert_eq!(adapter.session.history.undo.last().unwrap().0,"Import legacy animation");
        let at=|adapter:&mut Adapter, seconds:f64|image::load_from_memory(&adapter.preview_png(seconds,0).unwrap()).unwrap().to_rgba8().get_pixel(4,4).0;
        assert_eq!(at(&mut adapter,0.0),[0,0,0,0]);
        assert_eq!(at(&mut adapter,600.0),[255,0,0,128]);
        assert_eq!(at(&mut adapter,1199.9),[255,0,0,255]);
        let bytes=adapter.native_bytes().unwrap();
        adapter.open_bytes(&bytes).unwrap();
        assert_eq!(at(&mut adapter,600.0),[255,0,0,128]);
    }
    #[test]
    fn invalid_motion_property_does_not_leave_partial_native_keys() {
        let mut adapter=Adapter::default();
        adapter.dispatch("project.new", &json!({"width":16,"height":16,"fps":10,"durationMs":300,
            "legacyDocument":{"composition":{"pages":[{"width":16,"height":16,"layers":[
                {"id":"square","kind":"shape","width":8,"height":8,"properties":{"fill":"#ff0000"}}
            ]}]}},"legacyMotionGraph":{"frameRate":{"numerator":10,"denominator":1},"durationFrames":3,
                "tracks":[{"targetLayerId":"square","property":"opacity","keyframes":[
                    {"frame":0,"value":0.0,"easing":"unsupported"},{"frame":2,"value":1.0}]}]}
        })).unwrap();
        assert!(adapter.warnings.iter().any(|warning|warning.contains("invalid motion keys")));
        let comp=adapter.session.active_comp().unwrap();
        let layer=comp.layers.iter().find(|layer|layer.name=="Camada").unwrap();
        assert!(layer.props.prop("transform/opacity").unwrap().keys.is_empty());
    }
    #[test]
    fn composition_native_roundtrip_and_pixels() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch(
                "project.new",
                &json!({"width":16,"height":12,"fps":30,"durationMs":1000}),
            )
            .unwrap();
        adapter.dispatch("engine.execute", &json!({"command":"layer.newSolid","params":{"color":"#ff0000","width":16,"height":12}})).unwrap();
        let png = adapter.preview_png(0.0, 0).unwrap();
        assert_eq!(&png[..8], b"\x89PNG\r\n\x1a\n");
        let bytes = adapter.native_bytes().unwrap();
        adapter.open_bytes(&bytes).unwrap();
        assert_eq!(png, adapter.preview_png(0.0, 0).unwrap());
    }
    #[test]
    fn undo_redo_use_real_engine_history() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch("project.new", &json!({"width":16,"height":12}))
            .unwrap();
        let before = adapter.preview_png(0.0, 0).unwrap();
        adapter
            .dispatch(
                "engine.execute",
                &json!({"command":"layer.newSolid","params":{"color":"#ff0000"}}),
            )
            .unwrap();
        adapter.dispatch("undo", &json!({})).unwrap();
        assert_eq!(before, adapter.preview_png(0.0, 0).unwrap());
        adapter.dispatch("redo", &json!({})).unwrap();
        assert_ne!(before, adapter.preview_png(0.0, 0).unwrap());
    }
    #[test]
    fn actual_native_command_changes_pixels_through_scoped_worker() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch("project.new", &json!({"width":16,"height":16}))
            .unwrap();
        let result = adapter.dispatch("engine.execute",&json!({"command":"layer.newSolid","params":{"color":"#ff0000","width":8,"height":8}})).unwrap();
        let layer = result
            .pointer("/results/0/layer")
            .and_then(Value::as_u64)
            .unwrap();
        let before = adapter.preview_png(0.0, 0).unwrap();
        let root = std::env::temp_dir();
        adapter.dispatch("engine.execute",&json!({"mediaRoot":root,"command":"inspector.transform","params":{"layer":layer,"position":[2.0,2.0,0.0]}})).unwrap();
        assert_ne!(before, adapter.preview_png(0.0, 0).unwrap());
    }
    #[test]
    fn actual_h264_export_has_container_and_frames() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch(
                "project.new",
                &json!({"width":16,"height":16,"fps":30,"durationMs":100}),
            )
            .unwrap();
        adapter
            .dispatch(
                "engine.execute",
                &json!({"command":"layer.newSolid","params":{"color":"#ff0000"}}),
            )
            .unwrap();
        let path =
            std::env::temp_dir().join(format!("clicko-effect-export-{}.mp4", std::process::id()));
        let path_text = path.to_string_lossy().into_owned();
        let settings = RenderSettings {
            time_span: TimeSpan::LengthOfComp,
            ..Default::default()
        };
        let output = OutputModule {
            format: OutputFormat::H264,
            ..Default::default()
        };
        let job = effectcraft_export::Job {
            project: &adapter.session.project,
            footage: adapter.session.footage.as_ref(),
            expr: adapter.session.expr.as_deref(),
            accel: None,
            comp: adapter.session.active_comp_id().unwrap(),
            settings: &settings,
            output: &output,
            path: &path_text,
            sink: None,
            nested_switches: true,
            options: Default::default(),
        };
        let report = effectcraft_export::export(&job, &mut |_| true).unwrap();
        assert_eq!(report.frames, 3);
        let bytes = std::fs::read(&path).unwrap();
        assert_eq!(&bytes[4..8], b"ftyp");
        std::fs::remove_file(path).unwrap();
    }
}
