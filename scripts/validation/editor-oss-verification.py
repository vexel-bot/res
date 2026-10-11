"""Consolidate existing research receipts. No render, provider call or deletion."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'docs/studios/research/editor-oss-20261002'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

sources = load(REPORT / 'sources.json')
cleanup = load(REPORT / 'cleanup.json')
cleanup['logicalCloneBytes'] = int(sum(r['logicalFileBytes'] for r in cleanup['repositories']))
cleanup['removed'] = all(not Path(p).exists() for p in cleanup['rootsValidated'])
cleanup['status'] = 'removed' if cleanup['removed'] else 'blocked_by_automatic_approval_review'
cleanup['reviewReason'] = 'blocked by policy; no more specific reason supplied'
cleanup['rejectedActions'] = ['Recursive removal of the two verified temporary roots', 'Recursive removal of the exact literal editor-oss-study root']
(REPORT / 'cleanup.json').write_text(json.dumps(cleanup, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
sources['retention'] = 'Original analysis, hashes and immutable links retained; temporary-clone removal is pending because automatic approval review rejected deletion.'
sources['cleanupReceipt'] = 'cleanup.json'
(REPORT / 'sources.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

diagnostic = REPORT / 'diagnostic'
original_manifest_hash = digest(diagnostic / 'manifest.json')
reproduction = {
    'schemaVersion': 'res.editor-oss-render-diagnostic.v1', 'date': '2026-10-02',
    'worker': 'workers/remotion-benchmark/render-hybrid.mjs',
    'workerSha256': digest(ROOT / 'workers/remotion-benchmark/render-hybrid.mjs'),
    'runtimeSha256': digest(ROOT / 'workers/remotion-benchmark/src/hybrid.tsx'),
    'hashSnapshotMeaning': 'Worker/runtime hashes collected after the failed run; another session was editing shared files, so these alone do not attest every byte executed in that run.',
    'originalManifestSha256': original_manifest_hash,
    'retainedSyntheticMedia': {'path': 'diagnostic/source24.mp4', 'sha256': digest(diagnostic / 'source24.mp4'), 'bytes': (diagnostic / 'source24.mp4').stat().st_size},
    'retainedLog': {'path': 'diagnostic/worker.log', 'sha256': digest(diagnostic / 'worker.log')},
    'workerExitCode': 1, 'error': 'Compositor error: No frame found at position 23757',
    'compositionFrame': 14, 'observedSourceTimeSeconds': 1.9333333333333333,
    'underlyingCause': 'unconfirmed', 'approvedOutput': False,
    'apiRegression': 'heavy_media_execution_in_progress; job retrying',
    'observedLease': {'operation': 'video_render', 'pid': 9420, 'processExistsViaWin32Process': True, 'removedOrInterrupted': False},
    'rerunRequirement': 'Wait for the current heavy-media owner to finish; use the existing lease boundary. Do not bypass the lease or terminate its owner.',
    'manifestPortability': 'The original manifest deliberately retains its original pytest media path; for a rerun rebind assetFiles.footage.path to diagnostic/source24.mp4, verify its checksum and save the new manifest hash.',
}
(diagnostic / 'reproduction.json').write_text(json.dumps(reproduction, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

suites = []
for filename in ['backend-tests.xml', 'render-tests.xml']:
    xml = ET.parse(REPORT / filename).getroot()
    suite = xml.find('testsuite')
    suite_result = {'receipt': filename, 'tests': int(suite.attrib['tests']), 'failures': int(suite.attrib['failures']), 'errors': int(suite.attrib['errors']), 'skipped': int(suite.attrib['skipped']), 'elapsedSeconds': float(suite.attrib['time']), 'failureCases': []}
    for case in suite.findall('testcase'):
        if case.find('failure') is not None:
            suite_result['failureCases'].append(case.attrib['name'])
    suite_result['passed'] = suite_result['tests'] - suite_result['failures'] - suite_result['errors'] - suite_result['skipped']
    suites.append(suite_result)

files_to_bind = [
    'backend/app/domain/studios/motion.py', 'backend/app/domain/studios/motion_recipes.py',
    'backend/app/services/studios/native_motion_recipes.py', 'backend/app/providers/studios/remotion_projection.py',
    'backend/app/providers/studios/remotion_render.py', 'workers/remotion-benchmark/src/hybrid.tsx',
    'workers/remotion-benchmark/render-hybrid.mjs', 'backend/tests/test_native_motion_recipes.py',
    'backend/tests/test_studio_motion_graph.py', 'backend/tests/test_editorial_motion_v2.py',
    'backend/tests/test_remotion_native.py', 'backend/tests/test_remotion_native_api.py',
]
verification = {
    'schemaVersion': 'res.editor-oss-verification.v1', 'date': '2026-10-02',
    'research': {'repositories': len(sources['repositories']), 'selectedFiles': sum(len(r['files']) for r in sources['repositories']), 'externalCodeCopiedIntoApplication': False},
    'numericalRuntime': load(REPORT / 'runtime-study.json')['summary'],
    'recipes': load(REPORT / 'contract-study.json')['recipeFixtures'],
    'pythonTestSuites': suites,
    'lint': {'pythonResearchScripts': 'passed', 'runtimeStudyNodeSyntax': 'passed'},
    'sourceHashes': [{'path': p, 'sha256': digest(ROOT / p)} for p in files_to_bind],
    'sourceHashSnapshotMeaning': 'Collected after test runs; local changes from another session were observed. Numeric probes bind their own execution-source hashes; pytest receipts describe those executions and do not qualify later edits.',
    'cleanup': {'status': cleanup['status'], 'logicalCloneBytes': cleanup['logicalCloneBytes'], 'removed': cleanup['removed']},
    'technicalRenderQualifiedByThisStudy': False, 'humanVisualReview': 'not_performed', 'autonomyQualified': False,
    'sharedContractsChanged': False, 'applicationSourceChangedByThisStudy': False,
    'pending': ['Temporary clone removal rejected by automatic approval review', 'Investigate worker extraction failure after media owner finishes', 'Complete implementation handoff and real human review'],
}
(REPORT / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'repositories': verification['research']['repositories'], 'selectedFiles': verification['research']['selectedFiles'], 'suites': [{k:v for k,v in s.items() if k != 'failureCases'} for s in suites], 'cleanup': verification['cleanup']}, ensure_ascii=False))
