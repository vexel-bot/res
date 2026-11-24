"""Shared editorial brief for studio and independent motion productions."""

from pathlib import Path


def first_view_direction():
    return Path(__file__).with_name("motion_first_view.md").read_text(encoding="utf-8-sig")


def motion_brief(brief):
    return brief.rstrip() + "\n\n" + first_view_direction()
