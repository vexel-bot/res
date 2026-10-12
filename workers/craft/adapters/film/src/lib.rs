#![forbid(unsafe_code)]
use clicko_craft_protocol::{Result, Workspace, command_schema, commands, dimensions, text};
use filmcraft_engine::{Services, Session, export, time::Tick};
use serde_json::{Value, json};
use std::{
    collections::HashMap,
    sync::{Arc, RwLock},
};
#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

pub const REVISION: &str = "0800a8b0aa4a703ba42172f415b45a61f8d8a5e1";
pub const BUILD: &str = "clicko-filmcraft-1.0.0+0800a8b0";

#[derive(Default)]
struct Store {
    files: RwLock<HashMap<String, Vec<u8>>>,
    workspace: RwLock<Option<Arc<Workspace>>>,
}
impl Store {
    fn put(&self, name: &str, bytes: Vec<u8>) {
        self.files
            .write()
            .unwrap_or_else(|e| e.into_inner())
            .insert(name.to_owned(), bytes);
    }
}
impl Services for Store {
    fn read_file(&self, path: &str) -> std::io::Result<Vec<u8>> {
        if let Some(data) = self
            .files
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .get(path)
        {
            return Ok(data.clone());
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
            return filmcraft_format::atomic_write(
                &workspace.write_path(path).map_err(std::io::Error::other)?,
                data,
            );
        }
        self.put(path, data.to_vec());
        Ok(())
    }
    fn export_in_memory(&self) -> bool {
        cfg!(target_arch = "wasm32")
    }
    #[cfg(not(target_arch = "wasm32"))]
    fn reader(&self, path: &str) -> Option<std::io::Result<filmcraft_media::SharedReader>> {
        let workspace = self
            .workspace
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .clone()?;
        Some(
            workspace
                .read_path(path)
                .map_err(std::io::Error::other)
                .and_then(|path| {
                    filmcraft_media::reader::FileReader::open(&path)
                        .map(|reader| Arc::new(reader) as filmcraft_media::SharedReader)
                }),
        )
    }
    fn file_loader(&self) -> Option<filmcraft_media::sequence::FrameLoader> {
        let workspace = self
            .workspace
            .read()
            .unwrap_or_else(|e| e.into_inner())
            .clone()?;
        Some(Arc::new(move |path| workspace.read(path)))
    }
}

#[cfg_attr(target_arch = "wasm32", wasm_bindgen)]
pub struct Adapter {
    session: Session,
    store: Arc<Store>,
    warnings: Vec<String>,
}
impl Default for Adapter {
    fn default() -> Self {
        let store = Arc::new(Store::default());
        let mut session = Session::default();
        session.services = store.clone();
        Self {
            session,
            store,
            warnings: vec![],
        }
    }
}
impl Adapter {
    pub fn open_bytes(&mut self, bytes: &[u8]) -> Result<()> {
        let loaded = filmcraft_format::decode(bytes).map_err(|e| e.to_string())?;
        self.session = Session::default();
        self.session.services = self.store.clone();
        self.session.project = Arc::new(loaded.project);
        self.session.state.active_sequence =
            self.session.project.sequences().next().map(|item| item.id);
        if let Some(view) = loaded.view {
            self.session.restore_project_view(view);
        }
        Ok(())
    }
    pub fn native_bytes(&self) -> Vec<u8> {
        filmcraft_format::encode_with_view(
            &self.session.project,
            Some(&self.session.project_view()),
            false,
        )
    }
    pub fn preview_png(&self, time: f64, max_side: u32) -> Result<Vec<u8>> {
        let sequence = self.session.active_sequence().ok_or("no active sequence")?;
        let side = sequence.settings.width.max(sequence.settings.height);
        let scale = if max_side == 0 {
            1.0
        } else {
            (max_side.min(4096) as f32 / side.max(1) as f32).min(1.0)
        };
        let image = self
            .session
            .render_program_at(scale, Tick::from_seconds_f64(time))
            .ok_or("sequence frame could not be rendered")?;
        export::encode_png(image.to_rgba8(), image.w as u32, image.h as u32)
            .map_err(|e| e.to_string())
    }
    pub fn inspect(&mut self) -> Result<Value> {
        let project = self
            .session
            .execute("project.inspect", json!({}))
            .map_err(|e| e.to_string())?;
        let sequence = self
            .session
            .execute("sequence.inspect", json!({}))
            .map_err(|e| e.to_string())?;
        let q = self.session.active_sequence().ok_or("no active sequence")?;
        let mut timeline = Vec::new();
        let mut layers = Vec::new();
        for (kind, key) in [("video", "video"), ("audio", "audio")] {
            for track in sequence
                .get(key)
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
            {
                let track_id = track["id"].to_string();
                layers.push(
                    json!({"id":track_id,"name":track["name"],"kind":kind,"properties":track}),
                );
                for clip in track
                    .get("items")
                    .and_then(Value::as_array)
                    .into_iter()
                    .flatten()
                {
                    timeline.push(json!({"id":clip["clip"].to_string(),"trackId":track_id,"kind":kind,"name":clip["name"],"startMs":clip["start"].as_f64().unwrap_or(0.0)/254_016_000.0,"durationMs":clip["duration"].as_f64().unwrap_or(0.0)/254_016_000.0,"properties":clip}));
                }
            }
        }
        Ok(
            json!({"engine":"filmcraft","buildId":BUILD,"name":self.session.project.name,"width":q.settings.width,"height":q.settings.height,"durationMs":q.duration().seconds()*1000.0,"fps":q.settings.frame_rate.as_f64(),"layers":layers,"timeline":timeline,"warnings":self.warnings,"raw":{"project":project,"sequence":sequence}}),
        )
    }
    fn execute(&mut self, id: &str, params: &Value, context: &Value) -> Result<Value> {
        if id == "composition.link" {
            let asset_id = text(params, "assetId")?;
            let assets = context
                .get("media")
                .and_then(Value::as_array)
                .ok_or("materialized media manifest missing")?;
            let path_for = |asset: &str| {
                assets
                    .iter()
                    .find(|m| m["assetId"] == asset)
                    .and_then(|m| m.get("relativePath").or_else(|| m.get("path")))
                    .and_then(Value::as_str)
                    .ok_or_else(|| format!("asset `{asset}` is missing"))
            };
            let new_path = path_for(asset_id)?;
            if let Some(old_asset) = params.get("replaceAssetId").and_then(Value::as_str) {
                let old_path = path_for(old_asset)?;
                let old_item = self.session.project.items.values().find(|item| item.as_media().is_some_and(|m| matches!(&m.media,filmcraft_engine::project::MediaRef::File{path} if path == old_path))).map(|item| item.id).ok_or("linked composition media does not exist in the native project")?;
                return self.session.execute("media.relink",json!({"item":old_item.0,"path":new_path,"force":true,"relinkOthers":false})).map_err(|e|e.to_string());
            }
            let imported = self.execute(
                "asset.import",
                &json!({"assetId":asset_id,"addToTimeline":false}),
                context,
            )?;
            let item = imported
                .pointer("/items/0")
                .and_then(Value::as_u64)
                .ok_or("composition import returned no media")?;
            let placed = self.session.execute("timeline.place",json!({"item":item,"track":"new","seconds":params.get("seconds").and_then(Value::as_f64).unwrap_or(0.0),"insert":false,"video":true,"audio":false})).map_err(|e|e.to_string())?;
            return Ok(
                json!({"item":item,"clips":placed["clips"],"sourceDocumentId":params.get("sourceDocumentId")}),
            );
        }
        if id == "asset.import" {
            let asset_id = text(params, "assetId")?;
            let media = context
                .get("media")
                .and_then(Value::as_array)
                .and_then(|list| list.iter().find(|m| m["assetId"] == asset_id))
                .ok_or_else(|| format!("asset `{asset_id}` was not materialized"))?;
            let path = media
                .get("relativePath")
                .or_else(|| media.get("path"))
                .and_then(Value::as_str)
                .ok_or("asset path is missing")?;
            let mut imported = self
                .session
                .execute("file.import", json!({"paths":[path],"imageSequence":false}))
                .map_err(|e| e.to_string())?;
            if params
                .get("addToTimeline")
                .and_then(Value::as_bool)
                .unwrap_or(true)
            {
                let item = imported
                    .pointer("/items/0")
                    .and_then(Value::as_u64)
                    .ok_or("import returned no media item")?;
                let has_video = self
                    .session
                    .project
                    .item(filmcraft_engine::project::ItemId(item))
                    .is_some_and(|item| item.has_video());
                let mut placement = json!({"item":item,"audioTrack":"new","seconds":params.get("seconds").and_then(Value::as_f64).unwrap_or(self.session.playhead().seconds()),"insert":false,"video":has_video,"audio":true});
                if has_video {
                    placement["track"] = json!("new");
                }
                let placed = self
                    .session
                    .execute("timeline.place", placement)
                    .map_err(|e| e.to_string())?;
                imported["clips"] = placed["clips"].clone();
            }
            return Ok(imported);
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
                self.session.execute("file.newProject", json!({"name":params.get("title").and_then(Value::as_str).unwrap_or("Vídeo")})).map_err(|e| e.to_string())?;
                let fps = match (
                    params
                        .pointer("/legacyDocument/composition/mediaTimeline/frameRate/numerator")
                        .and_then(Value::as_f64),
                    params
                        .pointer("/legacyDocument/composition/mediaTimeline/frameRate/denominator")
                        .and_then(Value::as_f64),
                ) {
                    (Some(n), Some(d)) if n > 0.0 && d > 0.0 => n / d,
                    _ => params.get("fps").and_then(Value::as_f64).unwrap_or(30.0),
                };
                let legacy_tracks = params
                    .pointer("/legacyDocument/composition/mediaTimeline/tracks")
                    .and_then(Value::as_array);
                let video_count = legacy_tracks
                    .map(|t| {
                        t.iter()
                            .filter(|t| t["kind"] == "video" || t["kind"] == "overlay")
                            .count()
                    })
                    .unwrap_or(3)
                    .max(1);
                let audio_count = legacy_tracks
                    .map(|t| t.iter().filter(|t| t["kind"] == "audio").count())
                    .unwrap_or(3)
                    .max(1);
                self.session.execute("file.newSequence", json!({"name":"Montagem","width":width,"height":height,"fps":fps,"video":video_count,"audio":audio_count})).map_err(|e| e.to_string())?;
                self.migrate(params)?;
            }
            "project.open" | "project.inspect" | "project.save" => (),
            "engine.execute" | "project.execute" => {
                for (id, args) in commands(params)? {
                    results.push(self.execute(&id, &args, params)?);
                }
            }
            "undo" => {
                self.session.undo().ok_or("nothing to undo")?;
            }
            "redo" => {
                self.session.redo().ok_or("nothing to redo")?;
            }
            "render.frame" => {
                #[cfg(not(target_arch = "wasm32"))]
                {
                    let path =
                        Workspace::from_params(params)?.write_path(text(params, "outputPath")?)?;
                    let png = self.preview_png(
                        clicko_craft_protocol::frame_seconds(
                            params,
                            self.session
                                .active_sequence()
                                .ok_or("no active sequence")?
                                .settings
                                .frame_rate
                                .as_f64(),
                        )?,
                        params.get("maxSide").and_then(Value::as_u64).unwrap_or(0) as u32,
                    )?;
                    filmcraft_format::atomic_write(&path, &png).map_err(|e| e.to_string())?;
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
                    let mut settings: export::ExportSettings = serde_json::from_value(
                        params.get("settings").cloned().unwrap_or_else(|| json!({})),
                    )
                    .map_err(|e| e.to_string())?;
                    settings.path = path.to_string_lossy().into_owned();
                    let fmt = params
                        .get("format")
                        .and_then(Value::as_str)
                        .unwrap_or("h264");
                    settings.format = serde_json::from_value(json!(match fmt {
                        "mp4" => "h264",
                        "mov" => "prores",
                        "mxf_op1a" => "mxf-op1a",
                        "mxf_opatom" => "mxf-opatom",
                        "jpeg" => "jpg",
                        other => other,
                    }))
                    .map_err(|e| e.to_string())?;
                    if matches!(
                        fmt,
                        "png" | "tiff" | "bmp" | "jpg" | "jpeg" | "tga" | "dpx" | "exr"
                    ) {
                        let time = clicko_craft_protocol::frame_seconds(
                            params,
                            self.session
                                .active_sequence()
                                .ok_or("no active sequence")?
                                .settings
                                .frame_rate
                                .as_f64(),
                        )?;
                        let image = self
                            .session
                            .render_program_at(1.0, Tick::from_seconds_f64(time))
                            .ok_or("sequence frame could not be rendered")?;
                        let bytes = export::encode_still(
                            settings.format,
                            image.to_rgba8(),
                            image.w as u32,
                            image.h as u32,
                            true,
                        )
                        .map_err(|e| e.to_string())?;
                        filmcraft_format::atomic_write(&path, &bytes).map_err(|e| e.to_string())?;
                        return Ok(
                            json!({"path":path,"frames":1,"artifact":{"path":path,"width":image.w,"height":image.h},"warnings":self.warnings}),
                        );
                    }
                    settings.burn_captions = true;
                    let seq = self
                        .session
                        .state
                        .active_sequence
                        .ok_or("no active sequence")?;
                    let provider = self
                        .session
                        .media
                        .provider(self.session.project.clone(), self.session.services.clone());
                    let report = export::export(
                        &self.session.project,
                        seq,
                        &settings,
                        &provider,
                        &export::Progress::default(),
                    )
                    .map_err(|e| e.to_string())?;
                    let media_type = match fmt {
                        "wav" => "audio/wav",
                        "mov" | "prores" => "video/quicktime",
                        "gif" => "image/gif",
                        _ => "video/mp4",
                    };
                    return Ok(
                        json!({"path":report.path,"artifact":{"path":report.path,"mediaType":media_type},"frames":report.frames,"bytes":report.bytes,"warnings":self.warnings}),
                    );
                }
                #[cfg(target_arch = "wasm32")]
                return Err("final video export runs on a server worker".into());
            }
            _ => return Err(format!("unknown adapter method `{method}`")),
        }
        #[cfg(not(target_arch = "wasm32"))]
        if let Some(path) = params.get("outputPath").and_then(Value::as_str) {
            filmcraft_format::atomic_write(
                &Workspace::from_params(params)?.write_path(path)?,
                &self.native_bytes(),
            )
            .map_err(|e| e.to_string())?;
        }
        Ok(
            json!({"inspection":self.inspect()?,"nativePath":params.get("outputPath"),"warnings":self.warnings,"results":results}),
        )
    }
    fn migrate(&mut self, params: &Value) -> Result<()> {
        for page in clicko_craft_protocol::legacy_pages(params) {
            for layer in page
                .get("layers")
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
            {
                self.warnings.push(format!("Visual page layer `{}` requires composition in EffectCraft or an editable PhotoCraft asset; complete layer retained in the original archive", layer.get("name").or_else(|| layer.get("id")).and_then(Value::as_str).unwrap_or("unknown")));
            }
        }
        let Some(timeline) = params.pointer("/legacyDocument/composition/mediaTimeline") else {
            if params.get("legacyDocument").is_some() {
                self.warnings.push("legacy video has no media timeline; visual pages remain in the archived original and can be opened in PhotoCraft".into());
            }
            return Ok(());
        };
        let fps = self
            .session
            .active_sequence()
            .ok_or("no active sequence")?
            .settings
            .frame_rate;
        let mut imported = HashMap::new();
        let mut video_index = 0;
        let mut audio_index = 0;
        for track in timeline
            .get("tracks")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
        {
            let kind = track.get("kind").and_then(Value::as_str).unwrap_or("");
            if kind == "caption" {
                let caption = self
                    .session
                    .execute("captions.newTrack", json!({"name":track.get("name")}))
                    .map_err(|e| e.to_string())?;
                for cue in track
                    .get("cues")
                    .and_then(Value::as_array)
                    .into_iter()
                    .flatten()
                {
                    let start = cue
                        .pointer("/timeline/startFrame")
                        .and_then(Value::as_i64)
                        .unwrap_or(0);
                    let duration = cue
                        .pointer("/timeline/durationFrames")
                        .and_then(Value::as_i64)
                        .unwrap_or(1);
                    self.session.execute("captions.add", json!({"track":caption.get("track"),"text":cue.get("text"),"time":fps.tick_of(start).0,"durationSeconds":fps.tick_of(duration).seconds()})).map_err(|e| e.to_string())?;
                    if cue.get("style").is_some() {
                        self.warnings.push(format!("Caption styling on `{}` requires review in FilmCraft; text/timing converted and original style preserved", cue.get("id").and_then(Value::as_str).unwrap_or("unknown")));
                    }
                }
                continue;
            }
            if kind != "video" && kind != "audio" && kind != "overlay" {
                self.warnings.push(format!(
                    "track {} ({kind}) remains in the archived original",
                    track.get("name").and_then(Value::as_str).unwrap_or("")
                ));
                continue;
            }
            let destination = if kind == "audio" {
                audio_index += 1;
                format!("A{audio_index}")
            } else {
                video_index += 1;
                format!("V{video_index}")
            };
            for clip in track
                .get("clips")
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
            {
                let asset = clip.get("assetId").and_then(Value::as_str).unwrap_or("");
                let result: Result<()> = (|| {
                    let item = if let Some(item) = imported.get(asset) {
                        *item
                    } else {
                        let r = self.execute(
                            "asset.import",
                            &json!({"assetId":asset,"addToTimeline":false}),
                            params,
                        )?;
                        let item = r
                            .pointer("/items/0")
                            .and_then(Value::as_u64)
                            .ok_or("media import returned no item")?;
                        imported.insert(asset.to_owned(), item);
                        item
                    };
                    let start = clip
                        .pointer("/timeline/startFrame")
                        .and_then(Value::as_i64)
                        .unwrap_or(0);
                    let duration = clip
                        .pointer("/timeline/durationFrames")
                        .and_then(Value::as_i64)
                        .unwrap_or(1);
                    let source_in = clip
                        .pointer("/source/startMicroseconds")
                        .and_then(Value::as_f64)
                        .unwrap_or(0.0)
                        / 1_000_000.0;
                    let original_audio = clip
                        .pointer("/transform/originalAudioEnabled")
                        .and_then(Value::as_bool)
                        .unwrap_or(false);
                    let placed = self.session.execute("timeline.place", json!({"item":item,"track":destination,"time":fps.tick_of(start).0,"duration":fps.tick_of(duration).0,"sourceIn":Tick::from_seconds_f64(source_in).0,"insert":false,"audio":kind=="audio" || original_audio,"video":kind!="audio"})).map_err(|e| e.to_string())?;
                    if original_audio {
                        self.warnings.push(format!("Original audio on `{asset}` was imported as a linked track; source audio mix/fades require review; original preserved"));
                    }
                    let ids = placed
                        .get("clips")
                        .and_then(Value::as_array)
                        .cloned()
                        .unwrap_or_default();
                    if let Some(id) = ids.first().and_then(Value::as_u64) {
                        let sequence_id = self
                            .session
                            .state
                            .active_sequence
                            .ok_or("missing sequence")?;
                        self.session
                            .edit("Import Clip Properties", |project, _| {
                                let clip_native = project
                                    .sequence_mut(sequence_id)
                                    .and_then(|sequence| {
                                        sequence
                                            .find_item_mut(filmcraft_engine::project::ClipId(id))
                                    })
                                    .map(|(_, c)| c)
                                    .ok_or_else(|| {
                                        filmcraft_engine::EngineError::Other(
                                            "imported clip disappeared".into(),
                                        )
                                    })?;
                                clip_native.enabled =
                                    clip.get("enabled").and_then(Value::as_bool).unwrap_or(true);
                                clip_native.speed = clip
                                    .get("playbackRate")
                                    .and_then(Value::as_f64)
                                    .unwrap_or(1.0);
                                clip_native.gain_db =
                                    clip.get("gainDb").and_then(Value::as_f64).unwrap_or(0.0);
                                if let Some(name) = clip
                                    .get("label")
                                    .and_then(Value::as_str)
                                    .filter(|s| !s.is_empty())
                                {
                                    clip_native.name = name.to_owned();
                                }
                                Ok(())
                            })
                            .map_err(|e| e.to_string())?;
                        if let Some(transform) = clip.get("transform").and_then(Value::as_object) {
                            for (key, value) in transform {
                                let (effect, param) = match key.as_str() {
                                    "rotation" => ("motion", "rotation"),
                                    "scale" => ("motion", "scale"),
                                    "opacity" => ("opacity", "opacity"),
                                    "position" => ("motion", "position"),
                                    _ => {
                                        self.warnings.push(format!("transform `{key}` on clip {id} requires review; original preserved"));
                                        continue;
                                    }
                                };
                                self.session.execute("effects.setParam", json!({"clip":id,"effect":effect,"param":param,"value":value})).map_err(|e| e.to_string())?;
                            }
                        }
                    }
                    for field in ["effects", "keyframes"] {
                        if clip
                            .get(field)
                            .is_some_and(|v| v.as_array().is_some_and(|v| !v.is_empty()))
                        {
                            self.warnings.push(format!(
                                "{field} on clip {} require review; original preserved",
                                clip.get("id").and_then(Value::as_str).unwrap_or("")
                            ));
                        }
                    }
                    Ok(())
                })();
                if let Err(error) = result {
                    self.warnings
                        .push(format!("clip `{asset}`: {error}; original preserved"));
                }
            }
            let sequence_id = self
                .session
                .state
                .active_sequence
                .ok_or("missing sequence")?;
            let native_index = if kind == "audio" {
                audio_index - 1
            } else {
                video_index - 1
            };
            self.session
                .edit("Import Track Properties", |project, _| {
                    let sequence = project
                        .sequence_mut(sequence_id)
                        .ok_or(filmcraft_engine::EngineError::NoSequence)?;
                    let native = if kind == "audio" {
                        sequence.audio_tracks.get_mut(native_index)
                    } else {
                        sequence.video_tracks.get_mut(native_index)
                    }
                    .ok_or_else(|| {
                        filmcraft_engine::EngineError::Other("imported track disappeared".into())
                    })?;
                    if let Some(name) = track.get("name").and_then(Value::as_str) {
                        native.name = name.to_owned();
                    }
                    native.muted = track.get("muted").and_then(Value::as_bool).unwrap_or(false);
                    native.locked = track
                        .get("locked")
                        .and_then(Value::as_bool)
                        .unwrap_or(false);
                    Ok(())
                })
                .map_err(|e| e.to_string())?;
        }
        Ok(())
    }
}

pub fn capabilities() -> Value {
    let mut commands = filmcraft_engine::command_specs().iter().map(|command| json!({"id":command.id,"label":command.label,"menu":command.menu,"params":command.params,"inputSchema":command_schema("filmcraft",command.id,command.params)})).collect::<Vec<_>>();
    commands.push(json!({"id":"asset.import","label":"Importar material","inputSchema":{"type":"object","properties":{"assetId":{"type":"string"},"addToTimeline":{"type":"boolean","default":true},"seconds":{"type":"number","minimum":0}},"required":["assetId"],"additionalProperties":true}}));
    commands.push(json!({"id":"composition.link","label":"Vincular composição","inputSchema":{"type":"object","properties":{"assetId":{"type":"string"},"sourceDocumentId":{"type":"string"},"replaceAssetId":{"type":"string"},"seconds":{"type":"number","minimum":0}},"required":["assetId","sourceDocumentId"],"additionalProperties":false}}));
    clicko_craft_protocol::capability_isolation(&mut commands);
    let formats = export::Format::ALL
        .into_iter()
        .filter(|format| export::available(*format))
        .filter_map(|format| serde_json::to_value(format).ok())
        .collect::<Vec<_>>();
    json!({"engine":"filmcraft","buildId":BUILD,"upstreamRevision":REVISION,"formatVersion":filmcraft_format::SCHEMA_VERSION,"commands":commands,"formats":formats})
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
        clicko_craft_protocol::respond(request, "filmcraft", |method, params| {
            self.dispatch(method, params)
        })
        .to_string()
    }
    #[wasm_bindgen(js_name = openNative)]
    pub fn browser_open(&mut self, bytes: &[u8]) -> std::result::Result<(), JsValue> {
        self.open_bytes(bytes).map_err(|e| JsValue::from_str(&e))
    }
    #[wasm_bindgen(js_name = saveNative)]
    pub fn browser_save(&self) -> Vec<u8> {
        self.native_bytes()
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
    }
    #[wasm_bindgen(js_name = importAsset)]
    pub fn browser_import(
        &mut self,
        name: &str,
        bytes: &[u8],
    ) -> std::result::Result<String, JsValue> {
        self.store.put(name, bytes.to_vec());
        self.execute(
            "asset.import",
            &json!({"assetId":name}),
            &json!({"media":[{"assetId":name,"relativePath":name}]}),
        )
        .map(|v| v.to_string())
        .map_err(|e| JsValue::from_str(&e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn native_roundtrip_and_sequence_pixels() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch("project.new", &json!({"width":16,"height":12,"fps":30}))
            .unwrap();
        let item = adapter
            .session
            .execute("file.newColorMatte", json!({"color":"#ff0000","seconds":1}))
            .unwrap()["item"]
            .clone();
        adapter
            .session
            .execute(
                "timeline.place",
                json!({"item":item,"seconds":0,"video":true,"audio":false,"insert":false}),
            )
            .unwrap();
        let before = adapter.preview_png(0.0, 0).unwrap();
        assert_eq!(&before[..8], b"\x89PNG\r\n\x1a\n");
        adapter.open_bytes(&adapter.native_bytes()).unwrap();
        assert_eq!(adapter.preview_png(0.0, 0).unwrap(), before);
        assert!(
            adapter.inspect().unwrap()["timeline"]
                .as_array()
                .unwrap()
                .len()
                > 0
        );
    }
    #[test]
    fn unknown_command_does_not_change_native() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch("project.new", &json!({"width":16,"height":12}))
            .unwrap();
        let before = adapter.native_bytes();
        assert!(
            adapter
                .dispatch("engine.execute", &json!({"command":"does.not.exist"}))
                .is_err()
        );
        assert_eq!(before, adapter.native_bytes());
    }
    #[test]
    fn actual_h264_export_has_container_and_frames() {
        let mut adapter = Adapter::default();
        adapter
            .dispatch("project.new", &json!({"width":16,"height":16,"fps":30}))
            .unwrap();
        let item = adapter
            .session
            .execute(
                "file.newColorMatte",
                json!({"color":"#ff0000","seconds":0.1}),
            )
            .unwrap()["item"]
            .clone();
        adapter
            .session
            .execute(
                "timeline.place",
                json!({"item":item,"seconds":0,"video":true,"audio":false,"insert":false}),
            )
            .unwrap();
        let path =
            std::env::temp_dir().join(format!("clicko-film-export-{}.mp4", std::process::id()));
        let settings = export::ExportSettings {
            path: path.to_string_lossy().into_owned(),
            include_audio: false,
            ..Default::default()
        };
        let provider = adapter.session.media.provider(
            adapter.session.project.clone(),
            adapter.session.services.clone(),
        );
        let report = export::export(
            &adapter.session.project,
            adapter.session.state.active_sequence.unwrap(),
            &settings,
            &provider,
            &export::Progress::default(),
        )
        .unwrap();
        assert_eq!(report.frames, 3);
        let bytes = std::fs::read(&path).unwrap();
        assert_eq!(&bytes[4..8], b"ftyp");
        std::fs::remove_file(path).unwrap();
    }
}
