"""A director can accept a verified existing cut without fabricating an edit."""
import os
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from conftest import register
from app.database import SessionLocal
from app.models import CreativeDocument, StudioGenerationJob
from app.services.studios import llm_connections
from app.services.studios.compatibility import record_to_contract


@pytest.mark.skipif(os.environ.get('CLICKO_TEST_REAL_CRAFT') != '1', reason='requires real native runtime')
def test_review_only_can_export_unchanged_project_after_actual_temporal_review(client, monkeypatch):
    token, workspace = register(client, 'review-only@example.com')
    headers = {'Authorization': 'Bearer '+token}
    root = '/api/v1/studios/v1'
    created = client.post(root+'/documents', headers=headers, json={
        'workspaceId': workspace, 'title': 'Unchanged cut acceptance', 'contentType': 'video',
        'brief': {'objective':'Review the existing cut', 'audience':'QA'},
        'composition': {'pages':[{'id':'main','width':320,'height':320,'durationMs':1000,'layers':[]}],
                        'mediaTimeline':{'frameRate':{'numerator':12,'denominator':1},'durationFrames':12,'tracks':[]}},
    })
    assert created.status_code == 201, created.text
    document = created.json()
    base = root+'/documents/'+document['documentId']+'/craft'
    migrated = client.post(base+'/migrate', headers={**headers,'Idempotency-Key':'migrate-review-only'},
                           json={'engine':'effectcraft','expectedRevision':document['revision']})
    assert migrated.status_code == 200, migrated.text
    with SessionLocal() as db:
        original = record_to_contract(db.get(CreativeDocument,document['documentId'])).native_editor_state.checksum_sha256
    connection = SimpleNamespace(id='review-only',workspace_id=workspace,revision=1,provider='anthropic',config={
        'enabled':True,'protocol':'anthropic_messages','billingMode':'local_free','budgetUsd':0,
        'baseUrl':'https://api.anthropic.com/v1','models':['offline'],'maxOutputTokens':4000,
        'inputUsdPerMillion':0,'outputUsdPerMillion':0})
    real_refresh = SessionLocal.class_.refresh
    monkeypatch.setattr(SessionLocal.class_, 'refresh', lambda db, item, *a, **kw:
                        None if item is connection else real_refresh(db,item,*a,**kw))
    turns = []
    def turn(_model,_system,messages,_tools,_tokens,_seconds,**_options):
        turns.append(messages)
        if len(turns)==1:
            assert 'inspect_effectcraft_controls' in {item['name'] for item in _tools}
            name,args='inspect_effectcraft_controls',{'query':'frear'}
        elif len(turns)==2:
            name,args='review_clip',{'sampling':'overview','startSeconds':0,'durationSeconds':1}
        elif len(turns)==3:
            name,args='review_clip',{'sampling':'native','startSeconds':0,'durationSeconds':.4}
        else:
            name,args='finish_project',{'rationale':'Reviewed and accepted without edits.','deliveryStatus':'reviewed'}
        return {'stop_reason':'tool_use','model':'offline','usage':{},'content':[
            {'type':'tool_use','id':f'review-{len(turns)}','name':name,'input':args}]}
    monkeypatch.setattr(llm_connections,'planner',lambda *_:(connection,SimpleNamespace(craft_turn=turn),'offline','offline'))
    result = client.post(base+'/ai-commands',headers={**headers,'Idempotency-Key':'review-only'},json={
        'expectedRevision':migrated.json()['revision'],'instruction':'Review and export if this cut already meets the brief.',
        'connectionId':'review-only','directionEffort':'open_ended','unlimitedBudget':True,'requireExport':True})
    assert result.status_code==200,result.text
    assert result.json()['exportStatus']=='succeeded'
    assert result.json()['deliveryReview']['status']=='reviewed'
    with SessionLocal() as db:
        job = db.scalar(select(StudioGenerationJob).where(StudioGenerationJob.idempotency_key=='review-only'))
        assert job.result_payload['aiTrace']['reviewOnly'] is True
        assert not any(t['name'] in {'edit_project','run_motion_script'} for t in job.result_payload['tools'])
        assert job.result_payload['nativeToolObservation']['result']['controls'][0]['id']=='interpolation'
        assert job.result_payload['measuredCostUsd']==0
        assert record_to_contract(db.get(CreativeDocument,document['documentId'])).native_editor_state.checksum_sha256==original
