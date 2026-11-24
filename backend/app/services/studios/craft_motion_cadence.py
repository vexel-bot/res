"""Temporal measurements; motion samples never establish perceptual quality."""
import math


def cadence(samples, fps, *, expected_velocity=None, tolerance=1.5):
    if not samples or not math.isfinite(fps) or fps <= 0:
        raise ValueError('motion_cadence_invalid_input')
    frames = [s['frame'] for s in samples]
    if frames != list(range(len(samples))):
        raise ValueError('motion_cadence_requires_contiguous_frames_from_zero')
    if any(not math.isfinite(s['x']) for s in samples):
        raise ValueError('motion_cadence_nonfinite_position')
    deltas = [b['x']-a['x'] for a, b in zip(samples, samples[1:])]
    duplicates = [b['frame'] for a, b in zip(samples, samples[1:]) if a.get('sha256') and a['sha256']==b.get('sha256')]
    residual = ([abs(s['x']-(samples[0]['x']+expected_velocity*s['frame']/fps)) for s in samples]
                if expected_velocity is not None else [])
    return {'frameCount': len(samples), 'fps': fps, 'durationSeconds': len(samples)/fps,
            'adjacentIdenticalFrames': duplicates, 'positionDeltas': deltas,
            'maxLinearResidualPixels': max(residual) if residual else None,
            'linearTrajectory': ('pass' if max(residual)<=tolerance else 'fail') if residual else 'inconclusive',
            'limits': 'Identical frames may be intentional holds. File cadence and trajectory do not measure playback performance or aesthetic quality.'}
