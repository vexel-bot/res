import copy
import json
from pathlib import Path

import pytest

from app.services.studios.craft_motion_validation import receipt, verify, cost_breakdown
from app.services.studios.craft_agent import Draft
from app.services.studios import craft_director as director, craft_project_context
from app.services.studios.craft_history import compact_messages
from test_craft_direction_v2 import native as _native, invoke, plan


@pytest.fixture
def native(client, tmp_path):
    yield from _native.__wrapped__(client, tmp_path)


def project():
    return {'layers': [{'id': 1, 'properties': {'children': [{'uid': 9, 'value': [1, 2],
        'keys': [{'time': 1, 'in': 'Bezier', 'out': 'Linear', 'value': [1, 2]}]}]}}]}


def test_readback_distinguishes_mismatch_missing_and_tolerance():
    checks = [{'layer': 1, 'prop': 9, 'expected': [1, 2.01], 'tolerance': .02},
              {'layer': 1, 'prop': 9, 'expected': [2, 2]}, {'layer': 2, 'prop': 9, 'expected': [1, 2]}]
    result = verify(project(), checks)
    assert [c['status'] for c in result['checks']] == ['pass', 'fail', 'inconclusive']
    assert verify(project(), [{'layer': 1, 'prop': 9, 'field': 'keys', 'expected': []}])['status'] == 'fail'
    assert verify(project(), [{'layer': 1, 'prop': 9, 'expected': [True, 2]}])['status'] == 'fail'
    with pytest.raises(ValueError):
        verify(project(), [{'layer': 1, 'prop': 9, 'expected': [], 'tolerance': float('nan')}])


def test_successful_script_cannot_claim_settings_or_finish_from_empty_catch():
    r = receipt([{'id': 'script.run', 'params': {'code': 'try{apply()}catch(e){}'}}], project())
    assert r['commandExecution'] == 'succeeded' and r['configuration']['status'] == 'inconclusive'
    assert len(r['risks']) == 2 and r['visualBehaviour'] == 'unobserved'
    assert receipt([{'id': 'prop.set', 'params': {'layer': 1, 'prop': 9, 'value': [1, 2]}}], project())['configuration']['status'] == 'pass'


def test_probe_discards_edits_without_changing_project_or_batch(tmp_path):
    source = tmp_path/'original.ecproj'; source.write_bytes(b'original')
    d = object.__new__(Draft); d.engine='effectcraft'; d.directory=tmp_path; d.params={'nativePath': str(source)}
    d.project=project(); before=copy.deepcopy(d.project); d.batches=4
    def call(method, **args):
        Path(args['outputPath']).write_bytes(b'mutated disposable project')
        return {'results': [{'ok': True, 'result': 'probe'}]}
    d.call=call
    assert d.run('probe_motion_script', {'code': 'probe()'})['discardedEdits']
    assert source.read_bytes() == b'original' and d.project == before and d.batches == 4
    assert not (tmp_path/'disposable-probe.ecproj').exists()


def test_motion_plan_requires_observed_reference_and_executable_finish_criteria(native):
    _, _, job, _ = native
    job.request_payload={'motionQualityProfile': 'reference-led-v1'}
    original = copy.deepcopy(job.result_payload)
    job.result_payload={'referenceInspections': []}
    with pytest.raises(ValueError, match='reference_observation_required'):
        invoke(native, 'record_direction_plan', {'plan': plan()})
    job.result_payload=original
    with pytest.raises(ValueError, match='observable_plan_required'):
        invoke(native, 'record_direction_plan', {'plan': plan()})
    p=plan();p['referenceObservations']=[{'referenceId': p['referenceIds'][0], 'observed': 'scale contrast', 'limits': 'stills only'}]
    p['scenes'][0].update(productionChecks=['Inspect camera position keys'], aestheticCriteria=['Occlusion remains coherent'])
    assert invoke(native,'record_direction_plan',{'plan':p})['item']['plan']['scenes'][0]['aestheticCriteria']


def test_compaction_keeps_verification_identifiers_and_recovery_path():
    s={'tools': [{'toolUseId': 'check', 'draftBatch': 4, 'name': 'verify_motion_execution', 'ok': True,
                   'verification': {'status': 'fail', 'checks': ['large detail']*2000}}]}
    m=compact_messages({}, {}, 4, s)
    checkpoint=json.loads(m[0]['content'][1]['text'])
    assert checkpoint['executionCheckIndex'][0]['status']=='fail'
    assert checkpoint['executionDetailsAvailableVia']['payload']['kind']=='execution'
    assert 'large detail' not in json.dumps(m)


def test_cost_report_preserves_uncertainty_and_stage_without_inventing_causality():
    s={'turns':[{'cycleStageAtSubmission':'experiment','costUsd':.2,'usage':{}}],
       'uncertainCostUpperBoundUsd':1.4,'directorOperations':{'measuredCostUsd':.3}}
    r=cost_breakdown(s)
    assert r['stages']['experiment']['usageEstimatedUsd']==.2 and r['uncertainExposureUsd']==1.4
    assert r['evaluatorUsageEstimatedUsd']==.3


def test_intent_pass_cannot_replace_craft_or_approve_a_different_revision(native):
    invoke(native,'record_direction_plan',{'plan':plan()})
    db, record, job, draft = native
    job.request_payload={'motionQualityProfile':'reference-led-v1'}
    _,state=craft_project_context.state(db,record)
    state['cycle']={'requireVisualEvaluation':True}
    bound=director.binding(record,job,draft)
    assessment={'modality':'visual','interval':{'startSeconds':0,'durationSeconds':2},
                'findings':[{'dimension':'intent','status':'pass','sceneIds':['reveal']} ]}
    state['evidence']=[{'id':'proof','binding':bound,'planId':state['plans'][-1]['id'],'assessment':assessment}]
    with pytest.raises(ValueError,match='experiment_finish_required'):
        director.require_cycle_evaluation(state,record,job,draft,experiment=True)
    assessment['findings'].append({'dimension':'craft','status':'pass','sceneIds':['reveal']})
    director.require_cycle_evaluation(state,record,job,draft,experiment=True)
    Path(draft.params['nativePath']).write_bytes(b'a genuinely different project')
    with pytest.raises(ValueError,match='experiment_visual_evidence_required'):
        director.require_cycle_evaluation(state,record,job,draft,experiment=True)
