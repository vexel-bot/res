"""Versioned final-font layout policy is part of the canonical recipe binding."""

import copy

import pytest
from test_remotion_native import native_document
from test_typography_units import typography_direction

from app.domain.studios.typography import layout_policy


@pytest.fixture(autouse=True)
def clean_database():
    yield






def test_oversized_layout_fails_before_render_or_dom_allocation():
    with pytest.raises(ValueError, match="layout_unit_limit"):
        native_document(typography_direction("A" * 2001, duration=30, stagger=0, hold=20))
