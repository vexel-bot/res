"""Brief-only, uncapped Claude editing through the normal Clicko native service."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
KEY = 'orbita-autonomous-cinematic-20261114-v3'
SOURCE = '79d559cc-0c47-4e46-bd79-5cae48ab29b0'
CONNECTION = '9947192f-7acf-466c-b46b-a3eab369f618'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    temp.replace(path)


def main(args):
    runtime, output = args.runtime.resolve(), args.output.resolve()
    os.environ.update(ENVIRONMENT='development', DATABASE_URL='sqlite:///' + (runtime/'studios/records.sqlite').as_posix(),
                      STORAGE_PATH=str(runtime/'studios/uploads'))
    os.environ['STUDIO_LLM_CREDENTIAL_KEY'] = (runtime/'llm-credential-key').read_text().strip()
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, str(ROOT/'backend'))
    if args.phase not in {'collect', 'resume', 'recover-export'}:
        spec = importlib.util.spec_from_file_location('original_preflight', Path(__file__).with_name('clicko-system-claude-test.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not module.preflight(runtime, output, expected_build=getattr(args, 'expected_build', 'clicko-effectcraft-1.0.4+67434e90')):
            return 2
    if args.phase == 'preflight':
        return 0

    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftAICommandRequestV1, CraftRenderRequestV1
    from app.models import CreativeDocument, StudioGenerationJob, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, craft_ai, craft_agent, craft_drafts
    from app.services.studios.craft_artifact_copy import copy_verified
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.kernel import create_document

    receipt_file = output/'receipt.json'
    receipt = json.loads(receipt_file.read_text(encoding='utf-8')) if receipt_file.exists() else {}
    with SessionLocal() as db:
        key = receipt.get('taskKey', args.task_key)
        if receipt.get('jobId'):
            previous_job = db.get(StudioGenerationJob, receipt['jobId'])
            if previous_job:
                key = previous_job.idempotency_key
        origin = db.get(CreativeDocument, receipt.get('sourceDocumentId', args.source_document))
        source = record_to_contract(origin)
        user = db.get(User, source.actor_id)
        if args.phase == 'prepare':
            if receipt:
                raise ValueError('autonomous_review_already_prepared')
            branch = create_document(db, CreateStudioDocumentRequest.model_validate({
                'workspaceId': origin.workspace_id, 'contentType': 'video', 'brandRevision': source.brand_memory_ref.revision,
                'title': getattr(args, 'title', 'ÓRBITA · direção cinematográfica autônoma do Claude'),
                'sourceDocumentId': origin.id, 'sourceRevision': source.revision,
                'branchReason': 'Autonomous cinematic revision preserving source and editorial ancestry',
                'brief': {**source.brief.model_dump(mode='json', by_alias=True),
                    'objective': getattr(args, 'objective', 'Criar a melhor peça cinematográfica de ÓRBITA como um todo, com autonomia criativa total do Claude.'),
                    'audience': getattr(args, 'audience', 'Pessoas interessadas em cinema e ficção científica, assistindo principalmente no celular.'),
                    'restrictions': []},
                'composition': source.composition.model_dump(mode='json', by_alias=True),
                'assets': [item.model_dump(mode='json', by_alias=True) for item in source.assets],
            }), user, creation_key=key)
            native = source.native_editor_state
            with craft.workspace_files(db, origin, native) as (_, params, _):
                craft.save_native(db, branch, user, Path(params['nativePath']), engine='effectcraft', expected_revision=1,
                    key=key+'-clone', asset_manifest=native.asset_manifest, font_manifest=native.font_manifest)
            db.commit()
            receipt = {'stage': 'prepared', 'taskKey': key, 'documentId': branch.id, 'revision': branch.revision,
                'sourceDocumentId': origin.id, 'sourceRevision': source.revision, 'sourceSha256': native.checksum_sha256,
                'generationBudgetUsd': None, 'editingDeadlineSeconds': None, 'unlimitedBudget': True,
                'editor': 'Claude via Clicko; creative input is only the user-approved brief', 'apiSpendUsd': 0}
            write(receipt_file, receipt)
            print(json.dumps(receipt, ensure_ascii=False), flush=True)
            return 0
        if not receipt:
            raise ValueError('prepare_autonomous_review_first')
        branch = db.get(CreativeDocument, receipt['documentId'])
        if args.phase == 'qualify-export':
            from app.services.studios.jobs import execute_job_once
            render, _ = craft.create_render_job(db, branch,
                CraftRenderRequestV1(expectedRevision=branch.revision, format='mp4', quality='high'),
                user, key+'-runtime-qualification')
            if render.status in {'queued', 'retrying'}:
                execute_job_once(db, render)
                db.refresh(render)
            result = {'purpose': 'technical qualification of the unchanged Claude-authored native project',
                'apiSpendUsd': 0, 'jobId': render.id, 'status': render.status, 'error': render.error_code,
                'nativeChecksumSha256': record_to_contract(branch).native_editor_state.checksum_sha256,
                'result': render.result_payload}
            if render.status == 'succeeded':
                artifact = render.result_payload['artifact']
                asset = craft.scoped_asset(db, branch.workspace_id, artifact['assetId'], artifact['checksumSha256'])
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                    shutil.copyfile(path, output/'runtime-qualification.mp4')
            write(output/'runtime-full-scene-qualification.json', result)
            print(json.dumps({k:result[k] for k in ['purpose','apiSpendUsd','status','error']}), flush=True)
            return 0 if render.status == 'succeeded' else 1
        existing = craft_drafts.session_job(db, branch, key)
        if args.phase == 'recover-export':
            if not existing or not (existing.result_payload or {}).get('exportRequested'):
                raise ValueError('no_director_requested_export_to_recover')
            answer = craft.receipt(db, branch, key, existing.payload_hash)
            if not answer:
                raise ValueError('committed_director_receipt_required')
            started = time.monotonic()
            craft_agent.save_export(db, existing, branch, user, key, answer)
            receipt['renderRecoverySeconds'] = round(receipt.get('renderRecoverySeconds', 0) + time.monotonic()-started, 3)
        if args.phase in {'generate', 'resume'}:
            if args.phase == 'generate' and existing:
                raise ValueError('existing_task_collect_or_resume_same_key')
            if args.phase == 'resume':
                if not existing or not craft_agent.can_resume(existing):
                    raise ValueError('same_task_not_resumable_collect_its_result')
                request = CraftAICommandRequestV1.model_validate(json.loads((output/'request.json').read_text(encoding='utf-8')))
            else:
                brief = (output/'briefing.txt').read_text(encoding='utf-8')
                request = CraftAICommandRequestV1(expectedRevision=receipt['revision'], instruction=brief,
                    connectionId=CONNECTION, model='claude-opus-5-5', directionEffort='open_ended',
                    unlimitedBudget=True, requireExport=True, directionContract=args.direction_contract)
                write(output/'request.json', request.model_dump(mode='json', by_alias=True))
            started = time.monotonic()
            try:
                craft_ai.ai_commands(db, branch, request, user, key)
            except Exception as error:
                db.rollback()
                receipt['error'] = str(error).split(':', 1)[0]
                write(output/'last-error.json', {'type': type(error).__name__, 'message': str(error)[:1000]})
            receipt['executionSeconds'] = round(receipt.get('executionSeconds', 0) + time.monotonic()-started, 3)
        job = craft_drafts.session_job(db, branch, key)
        if not job:
            write(receipt_file, receipt)
            return 1
        state = job.result_payload or {}
        if job.status == 'succeeded':
            receipt.pop('error', None)
        receipt.update(stage=job.status, jobId=job.id, apiSpendUsd=state.get('measuredCostUsd', 0),
            uncertainUsd=round(state.get('uncertainCostUpperBoundUsd', 0) + craft_agent.pending_exposure(job), 8),
            paidResponses=len(state.get('turns', [])), savedBatches=state.get('draft', {}).get('batches', 0),
            deliveryReview=state.get('deliveryReview'), exportRequested=state.get('exportRequested'),
            exportJobId=state.get('exportJobId'))
        receipt['evaluationSpendUsd'] = state.get('directorOperations', {}).get('measuredCostUsd', 0)
        receipt['totalRecordedAndEstimatedUsd'] = round(receipt['apiSpendUsd'] + receipt['evaluationSpendUsd'], 8)
        write(output/'job-evidence.json', {'request': job.request_payload, 'result': state})
        if state.get('exportJobId'):
            render = db.get(StudioGenerationJob, state['exportJobId'])
            receipt['exportStatus'] = render.status
            if render.status == 'succeeded':
                artifact = render.result_payload['artifact']
                asset = craft.scoped_asset(db, branch.workspace_id, artifact['assetId'], artifact['checksumSha256'])
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                    copy_verified(path, output/'orbita-claude-autonomo.mp4', artifact['checksumSha256'])
                native = record_to_contract(branch).native_editor_state
                with craft.native_bundle(db, branch, native) as bundle:
                    copy_verified(bundle, output/'orbita-claude-autonomo-editavel.zip')
                receipt.update(artifact=artifact, finalRevision=branch.revision)
        db.refresh(origin)
        receipt['sourcePreserved'] = (origin.revision == receipt['sourceRevision']
            and record_to_contract(origin).native_editor_state.checksum_sha256 == receipt['sourceSha256'])
        assert receipt['sourcePreserved']
        write(receipt_file, receipt)
        print(json.dumps({k:receipt.get(k) for k in ['stage','apiSpendUsd','uncertainUsd','paidResponses','savedBatches','exportStatus']}, ensure_ascii=False), flush=True)
        return 0 if receipt.get('exportStatus') == 'succeeded' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['preflight','prepare','generate','collect','resume','recover-export','qualify-export'])
    parser.add_argument('--runtime', type=Path, default=ROOT/'.codex-runtime/clicko-dev')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-document', default=SOURCE)
    parser.add_argument('--task-key', default=KEY)
    parser.add_argument('--direction-contract', choices=['v1', 'v2'], default='v1')
    raise SystemExit(main(parser.parse_args()))
