import pytest
from app.services.studios.craft_motion_cadence import cadence
from app.services.studios.craft_motion_validation import qualification_protocol


def test_detects_held_frames_and_incorrect_linear_trajectory():
    samples=[{'frame': i, 'x': x, 'sha256': str(x)} for i,x in enumerate([0,10,10,30])]
    r=cadence(samples,30,expected_velocity=300)
    assert r['adjacentIdenticalFrames']==[2]
    assert r['linearTrajectory']=='fail' and r['maxLinearResidualPixels']==10
    assert 'intentional' in r['limits']


def test_rejects_partial_coverage_and_accepts_quantized_positions():
    with pytest.raises(ValueError,match='contiguous'):
        cadence([{'frame':0,'x':0},{'frame':2,'x':20}],30)
    samples=[{'frame':i,'x':round(i*440/30)} for i in range(30)]
    assert cadence(samples,30,expected_velocity=440)['linearTrajectory']=='pass'
    assert cadence(samples,30)['linearTrajectory']=='inconclusive'
    with pytest.raises(ValueError):
        cadence([{'frame':0,'x':float('nan')}],30)


def test_mechanical_examples_do_not_qualify_other_engine_builds():
    current=qualification_protocol('clicko-effectcraft-1.0.6+67434e90.audio-levels')
    assert current['observedExamples'] and current['status']=='criteria_not_execution_evidence'
    assert qualification_protocol('new-unobserved-build')['observedExamples']==[]
    assert 'No professional finish' in current['exampleLimits']
