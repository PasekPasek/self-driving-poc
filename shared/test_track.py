"""Geometry checks for shared/track.json. Run: pytest shared/test_track.py"""

import json
from pathlib import Path

import numpy as np
import pytest

TRACK_PATH = Path(__file__).with_name("track.json")


@pytest.fixture(scope="module")
def track() -> dict:
    return json.loads(TRACK_PATH.read_text(encoding="utf-8"))


def boundaries(track: dict) -> tuple[np.ndarray, np.ndarray]:
    c = np.array(track["centerline"])
    tan = np.roll(c, -1, axis=0) - np.roll(c, 1, axis=0)
    nrm = np.column_stack([-tan[:, 1], tan[:, 0]])
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    h = track["width"] / 2
    return c + nrm * h, c - nrm * h


def _cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def crossing_pairs(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Boolean matrix [i, j]: closed polyline a's segment i properly crosses b's segment j."""
    a0, a1 = a, np.roll(a, -1, axis=0)
    b0, b1 = b, np.roll(b, -1, axis=0)
    da = (a1 - a0)[:, None, :]
    db = (b1 - b0)[None, :, :]
    diff = b0[None, :, :] - a0[:, None, :]
    denom = _cross(da, db)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = _cross(diff, db) / denom
        u = _cross(diff, da) / denom
    return (denom != 0) & (t > 0) & (t < 1) & (u > 0) & (u < 1)


def self_intersections(poly: np.ndarray) -> int:
    hits = crossing_pairs(poly, poly)
    n = len(poly)
    idx = np.arange(n)
    gap = np.abs(idx[:, None] - idx[None, :])
    non_adjacent = (gap > 1) & (gap < n - 1)
    return int(np.count_nonzero(hits & non_adjacent) // 2)


def test_shape(track):
    assert track["width"] > 0
    assert 150 <= len(track["centerline"]) <= 300
    assert all(len(p) == 2 for p in track["centerline"])
    assert set(track["start"]) == {"x", "y", "heading"}


def test_loop_is_closed(track):
    c = np.array(track["centerline"])
    steps = np.linalg.norm(np.diff(np.vstack([c, c[:1]]), axis=0), axis=1)
    # The closing step (last -> first) is an ordinary step: no gap, no duplicate point.
    assert steps[-1] == pytest.approx(np.median(steps), rel=0.1)
    assert steps.min() > 0
    assert steps.max() < 1.2 * np.median(steps)


def test_start_on_centerline_with_heading(track):
    c = np.array(track["centerline"])
    s = track["start"]
    assert np.allclose(c[0], [s["x"], s["y"]], atol=0.01)
    d = c[1] - c[0]
    assert np.arctan2(d[1], d[0]) == pytest.approx(s["heading"], abs=0.01)


def test_boundaries_do_not_self_intersect(track):
    outer, inner = boundaries(track)
    assert self_intersections(outer) == 0
    assert self_intersections(inner) == 0


def test_boundaries_do_not_intersect_each_other(track):
    outer, inner = boundaries(track)
    assert not crossing_pairs(outer, inner).any()


def test_everything_inside_box(track):
    w, h = track["box"]["width"], track["box"]["height"]
    assert (w, h) == (1000, 650)
    outer, inner = boundaries(track)
    for pts in (np.array(track["centerline"]), outer, inner):
        assert pts[:, 0].min() >= 0 and pts[:, 0].max() <= w
        assert pts[:, 1].min() >= 0 and pts[:, 1].max() <= h


def test_sections_cover_loop_in_order(track):
    n = len(track["centerline"])
    secs = track["sections"]
    assert secs[0]["fromIndex"] == 0
    assert secs[-1]["toIndex"] == n - 1
    for sec in secs:
        assert sec["fromIndex"] <= sec["toIndex"]
    for prev, nxt in zip(secs, secs[1:]):
        assert nxt["fromIndex"] == prev["toIndex"] + 1
    assert [s["name"] for s in secs][0] == "start straight"


def test_min_radius_of_curvature(track):
    """Radius >= 1.25 x half-width everywhere, so neither boundary forms a cusp."""
    c = np.array(track["centerline"])
    a, b, d = np.roll(c, 1, axis=0), c, np.roll(c, -1, axis=0)
    cross = np.abs((b - a)[:, 0] * (d - a)[:, 1] - (b - a)[:, 1] * (d - a)[:, 0])
    lengths = (np.linalg.norm(b - a, axis=1) * np.linalg.norm(d - b, axis=1)
               * np.linalg.norm(d - a, axis=1))
    with np.errstate(divide="ignore"):
        radius = lengths / (2 * cross)  # circumradius of three consecutive points; inf on a straight
    assert radius.min() >= 1.25 * track["width"] / 2
