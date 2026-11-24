"""Observable motion execution, independent of editorial approval."""
import math
import re
import json
from pathlib import Path


def qualification_protocol(build):
    protocol = json.loads(Path(__file__).with_name('craft_motion_quality.v1.json').read_text(encoding='utf-8'))
    examples = json.loads(Path(__file__).with_name('craft_motion_examples.v1.json').read_text(encoding='utf-8'))
    return {**protocol, 'buildId': build, 'status': 'criteria_not_execution_evidence',
            'observedExamples': examples['examples'] if build == examples['buildId'] else [],
            'exampleLimits': examples['limits'],
            'instruction': 'Use probe_motion_script and verify_motion_execution, then inspect rendered behaviour. '
                           'Neither command availability nor a single successful example qualifies every use. '
                           'Capabilities without identified observed proof remain unqualified for quality claims.'}


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def equal(left, right, tolerance):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isfinite(left) and math.isfinite(right) and abs(left-right) <= tolerance
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal(a, b, tolerance) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal(left[k], right[k], tolerance) for k in left)
    return type(left) is type(right) and left == right


def verify(project, checks):
    """Selectors are exact native layer IDs and property UIDs, never fuzzy matches."""
    if not isinstance(checks, list) or not 1 <= len(checks) <= 48:
        raise ValueError('craft_motion_checks_required')
    results = []
    for check in checks:
        if not isinstance(check, dict) or not all(k in check for k in ('layer', 'prop', 'expected')):
            raise ValueError('craft_motion_check_selector_required')
        layer = next((l for l in project.get('layers', []) if str(l['id']) == str(check['layer'])), None)
        prop = next((p for p in nodes(layer) if str(p.get('uid')) == str(check['prop'])), None) if layer else None
        field = check.get('field', 'value')
        if field not in {'value', 'keys', 'enabled', 'type'}:
            raise ValueError('craft_motion_check_field_invalid')
        tolerance = check.get('tolerance', 0)
        if type(tolerance) not in {int, float} or not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError('craft_motion_check_tolerance_invalid')
        available = prop is not None and field in prop
        actual = prop[field] if available else None
        results.append({**check, 'actual': actual, 'status': ('pass' if equal(actual, check['expected'], tolerance)
                       else 'fail') if available else 'inconclusive'})
    return {'schemaVersion': 'craft.execution-check.v1', 'checks': results,
            'status': 'fail' if any(c['status']=='fail' for c in results) else
                      'inconclusive' if any(c['status']=='inconclusive' for c in results) else 'pass',
            'scope': 'Persisted configuration only; visual behaviour and aesthetic quality require observed render evidence.'}


def receipt(commands, project):
    checks, risks = [], []
    for command in commands:
        params = command.get('params', {})
        if command['id'] == 'prop.set' and all(k in params for k in ('layer', 'prop', 'value')):
            checks.append({'layer': params['layer'], 'prop': params['prop'], 'expected': params['value']})
        if command['id'] == 'script.run':
            if re.search(r'catch\s*\([^)]*\)\s*{\s*}', params.get('code','')):
                risks.append('Empty exception handler: configuration may have failed silently; inspect critical properties.')
            risks.append('Script success does not establish application of every requested setting. Use verify_motion_execution.')
    return {'schemaVersion': 'craft.execution.v1', 'commandExecution': 'succeeded',
            'configuration': verify(project, checks[:48]) if checks else {'status': 'inconclusive', 'checks': []},
            'uncheckedPropertyCommands': max(0, len(checks)-48),
            'risks': list(dict.fromkeys(risks)), 'visualBehaviour': 'unobserved', 'aestheticQuality': 'inconclusive'}


def cost_breakdown(state):
    stages = {}
    for turn in state.get('turns', []):
        stage = turn.get('cycleStageAtSubmission') or turn.get('decisionStage', 'unknown')
        item = stages.setdefault(stage, {'responses': 0, 'usageEstimatedUsd': 0, 'thinkingTokens': 0})
        item['responses'] += 1
        item['usageEstimatedUsd'] = round(item['usageEstimatedUsd'] + (turn.get('costUsd') or 0), 8)
        item['thinkingTokens'] += turn.get('usage', {}).get('output_tokens_details', {}).get('thinking_tokens', 0)
    failures = [t for t in state.get('tools', []) if not t.get('ok')]
    return {'stages': stages, 'failedTools': len(failures), 'directorUsageEstimatedUsd': state.get('measuredCostUsd', 0),
            'evaluatorUsageEstimatedUsd': state.get('directorOperations', {}).get('measuredCostUsd', 0),
            'uncertainExposureUsd': state.get('uncertainCostUpperBoundUsd', 0),
            'limits': 'Reported usage priced at pinned tariff, not invoice. Legacy stages may be inaccurate. Tool counts are not causal cost allocation.'}
