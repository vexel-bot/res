from __future__ import annotations

import numpy as np
import pytest

from scripts.audit_ugc_sound_asset import (
    FRAME_BYTES,
    MUSIC_CLASS_INDICES,
    VOICE_CLASS_INDICES,
    _family_summary,
    analyze_speech,
    waveform_to_yamnet_patches,
)


def test_silent_pcm_passes_only_the_speech_preflight() -> None:
    result = analyze_speech(bytes(FRAME_BYTES * 4))

    assert result["framesAnalyzed"] == 4
    assert result["speechFrames"] == 0
    assert result["speechDetectionStatus"] == "pass"


def test_audio_shorter_than_one_frame_is_rejected() -> None:
    with pytest.raises(ValueError, match="ugc_sound_too_short_for_speech_preflight"):
        analyze_speech(bytes(FRAME_BYTES - 1))


def test_yamnet_frontend_pads_silence_to_one_complete_patch() -> None:
    patches = waveform_to_yamnet_patches(bytes(FRAME_BYTES * 4))

    assert patches.shape == (1, 96, 64)
    assert patches.dtype == np.float32
    assert np.isfinite(patches).all()


def test_family_summary_is_fail_closed_above_threshold() -> None:
    scores = np.zeros((2, 521), dtype=np.float32)
    scores[1, 0] = 0.8
    labels = [f"class-{index}" for index in range(521)]

    voice = _family_summary(scores, labels, VOICE_CLASS_INDICES)
    music = _family_summary(scores, labels, MUSIC_CLASS_INDICES)

    assert voice == {
        "maximumScore": 0.80000001,
        "maximumClassIndex": 0,
        "maximumClassName": "class-0",
        "maximumPatchIndex": 1,
        "status": "inconclusive",
    }
    assert music["status"] == "pass"
