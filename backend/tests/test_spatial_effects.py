"""Persisted spatial parameters keep their typed semantics and digest binding."""
import copy

import pytest
from test_remotion_native import native_document
from test_spatial_effects_render import spatial_direction

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2


@pytest.fixture(autouse=True)
def clean_database():
    yield


def spatial_document():
    doc, projection = native_document(ContextualPlanRequestV2.model_validate(spatial_direction("spatial")))
    return doc, projection, next(layer for layer in doc.composition.pages[0].layers if layer.name == "hard")
