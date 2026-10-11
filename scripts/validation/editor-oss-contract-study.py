"""Original research probes against existing res contracts; does not edit projects or run providers."""
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from app.domain.studios.motion import MotionTrackV1, _track_acceleration, _track_velocity  # noqa: E402
from app.domain.studios.motion_recipes import MotionRecipeV1  # noqa: E402

fixture_path = ROOT / 'docs/studios/research/editor-oss-20261002/recipes.v1.json'
fixtures = json.loads(fixture_path.read_text(encoding='utf-8'))
validated_recipes = [MotionRecipeV1.model_validate(item) for item in fixtures]

track = MotionTrackV1.model_validate({
    'trackId': 'research-velocity', 'targetLayerId': 'research-title',
    'property': 'position_x', 'unit': 'pixels',
    'keyframes': [{'frame': 0, 'value': 0, 'easing': 'ease_in'}, {'frame': 30, 'value': 100}],
})
dt = 1 / 10000
sampled_peak = (100 - 100 * (1 - dt) ** 2) / dt
velocity_probe = {
    'fps': 30, 'durationFrames': 30, 'displacementPx': 100, 'easing': 'ease_in',
    'thresholdPxPerSecond': 150, 'currentCheckerPxPerSecond': _track_velocity(track, 30),
    'curvePeakLimitPxPerSecond': 200, 'sampledPeakPxPerSecond': sampled_peak,
    'currentCheckerWouldPass': _track_velocity(track, 30) <= 150,
    'curvePeakWouldPass': sampled_peak <= 150,
    'currentAccelerationEstimate': _track_acceleration(track, 30),
    'analyticAccelerationPxPerSecondSquared': 200,
    'finding': 'Eased peak repaired: two keys yield velocity 200 and acceleration 200; threshold 150 now rejects the curve. See contract-study.initial.json for the original false pass.',
}

def exact_map(frame, source_rate, output_rate):
    return Fraction(frame) * Fraction(output_rate) / Fraction(source_rate)

time_vectors = []
for source_frame, source_fps, output_fps in [(24, 24, 60), (1, 24, 60), (60, 60, 24), (1, 60, 24), (24000, Fraction(24000, 1001), 30)]:
    mapped = exact_map(source_frame, source_fps, output_fps)
    time_vectors.append({'sourceFrame': source_frame, 'sourceRate': str(source_fps), 'outputRate': str(output_fps), 'exactOutputFrame': str(mapped), 'needsExplicitRoundingPolicy': mapped.denominator != 1})

report = {
    'schemaVersion': 'res.editor-oss-contract-study.v1', 'date': '2026-10-02',
    'source': {'path': 'backend/app/domain/studios/motion.py', 'sha256': hashlib.sha256((ROOT / 'backend/app/domain/studios/motion.py').read_bytes()).hexdigest()},
    'derivativeSource': {'path': 'backend/app/domain/studios/motion_derivatives.py', 'sha256': hashlib.sha256((ROOT / 'backend/app/domain/studios/motion_derivatives.py').read_bytes()).hexdigest()},
    'velocityProbe': velocity_probe, 'timeConversionOracleVectors': time_vectors,
    'recipeFixtures': {'path': fixture_path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(), 'validatedAgainst': 'app.domain.studios.motion_recipes.MotionRecipeV1', 'count': len(validated_recipes), 'ids': [r.id for r in validated_recipes], 'qualification': 'contract_validated_only'},
    'evidenceLevel': 'Existing Python contract/helper execution and original rational arithmetic oracle; no new renderer capability or aesthetic qualification.',
    'externalCodeCopied': False,
}
destination = ROOT / 'docs/studios/research/editor-oss-20261002/contract-study.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(velocity_probe, ensure_ascii=False))
