def test_direction_to_actual_render_with_supplied_audio(client, project, monkeypatch, tmp_path):
    from app.database import SessionLocal
    from app.domain.studios.contracts import AssetReferenceV1
    from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, StudioMediaIngest
    from app.providers.studios.contextual_motion_render import ContextualMotionRenderProvider
    from app.providers.studios.contextual_render import ContextualFFmpegProvider
    from app.providers.studios.gemini_editing import GeminiEditingProvider
    from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS, HyperFramesCliVideoRenderProvider
    from app.services.object_storage import get_object_storage
    from app.services.studios.compatibility import persist_contract, record_to_contract
    from app.services.studios.jobs import execute_job_once

    cli = os.getenv("RES_HYPERFRAMES_CLI")
    if not cli:
        pytest.skip("Pinned HyperFrames required")
    enable(monkeypatch)
    monkeypatch.setitem(
        VIDEO_RENDER_PROVIDERS,
        "hyperframes.contextual-v2",
        ContextualMotionRenderProvider(
            HyperFramesCliVideoRenderProvider("node", cli, 180), ContextualFFmpegProvider("ffmpeg", 180)
        ),
    )
    wav = tmp_path / "technical-audio.wav"
    # A technical fixture, deliberately not a qualification of narration or creative quality.
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1", wav)
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        stored = get_object_storage().put_file(wav, key=f"{project['workspace']}/test.wav", media_type="audio/wav")
        asset = LibraryAsset(
            workspace_id=record.workspace_id,
            title="Technical audio fixture",
            asset_type="audio",
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type="audio/wav",
            checksum_sha256=stored.checksum_sha256,
            size_bytes=stored.size_bytes,
        )
        db.add(asset)
        db.flush()
        db.add(
            StudioMediaIngest(
                workspace_id=record.workspace_id,
                asset_id=asset.id,
                status="ready",
                requested_by=record.created_by,
                idempotency_key="technical-voice-ingest",
            )
        )
        doc = record_to_contract(record)
        doc.composition.media_timeline = None
        doc.assets.append(
            AssetReferenceV1(
                id=asset.id, media_type="audio/wav", checksum=stored.checksum_sha256, rights_status="verified"
            )
        )
        voice_id = asset.id
        persist_contract(record, doc)
        db.commit()
    composition = direction(width=280, font_size=20, text="Distribuição")
    composition.scenes[0].id = "idea"
    composition.scenes[0].background = "#748494"
    composition.scenes[0].narration = "Distribuir não garante atenção."
    observed_contexts = []

    def plan(self, model, context, media):
        observed_contexts.append(context)
        if "findings" in context["outputSchema"]["properties"]:
            assert any(mime == "video/mp4" for _, mime in media)
            result = {
                "coverage": "partial",
                "summary": "Observação controlada do teste técnico.",
                "findings": [],
                "speechIntelligibility": "unknown",
                "soundEventAccuracy": "unknown",
            }
            return {"candidates": [{"content": {"parts": [{"text": json.dumps(result)}]}}]}
        result = (
            storyboard()
            if "concepts" in context["outputSchema"]["properties"]
            else composition.model_dump(mode="json", by_alias=True)
        )
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(result)}]}}]}

    monkeypatch.setattr(GeminiEditingProvider, "plan", plan)
    request = {**brief(), "narrationAssetId": voice_id}
    result = client.post(endpoint(project), headers=headers(project), json=request)
    assert result.status_code == 202, result.text
    run = result.json()
    url = endpoint(project) + f"/{run['id']}/resume"
    for stage in ("direction", "composition", "animatic", "render", "critique"):
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, run["jobs"][stage])
            assert execute_job_once(db, job) == "succeeded", job.error_message
        response = client.post(url, headers=headers(project))
        assert response.status_code == 200, response.text
        run = response.json()
        if stage != "critique":
            response = client.post(url, headers=headers(project))
            assert response.status_code == 200, response.text
            run = response.json()
            assert run["status"] == "running", (
                stage,
                run["blockers"],
                [
                    c
                    for c in run.get("artifacts", {}).get("animatic", {}).get("qualityEvaluation", {}).get("checks", [])
                    if c["status"] == "failed"
                ],
            )
    assert run["status"] == "awaiting_review"
    assert run["artifacts"]["video"]["artifact"]["audioCodec"]
    assert (
        run["artifacts"]["critique"]["renderBinding"]["checksum"]
        == run["artifacts"]["video"]["artifact"]["checksumSha256"]
    )
    assert run["humanReview"] == "pending"
    assert not run["autonomousProductionQualified"]
    assert observed_contexts[1]["measuredNarrationByBeat"]["idea"]["durationSeconds"] == 1
    revision = client.post(
        endpoint(project) + f"/{run['id']}/revise",
        headers=headers(project),
        json={
            "expectedRunRevision": run["revision"],
            "sceneIds": ["idea"],
            "instruction": "Deixe a explicação mais calma, preservando a conclusão.",
        },
    )
    assert revision.status_code == 202, revision.text
    revised = revision.json()
    assert revised["jobs"]["composition"] != run["jobs"]["composition"]
    assert revised["history"][0]["artifacts"]["video"] == run["artifacts"]["video"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, revised["jobs"]["composition"])
        assert execute_job_once(db, job) == "succeeded", job.error_message
    assert observed_contexts[3]["revision"]["sceneIds"] == ["idea"]
    assert (
        client.post(
            endpoint(project) + f"/{run['id']}/revise",
            headers=headers(project),
            json={
                "expectedRunRevision": run["revision"],
                "sceneIds": ["idea"],
                "instruction": "mais calmo",
            },
        ).status_code
        == 409
    )
