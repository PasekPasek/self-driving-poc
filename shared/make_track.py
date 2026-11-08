"""Generate shared/track.json: the "Smocza Petla" track.

Usage: python shared/make_track.py [--preview docs/track.png]

numpy only; matplotlib is an optional dev dependency used for --preview.
The centerline is a closed Catmull-Rom spline through hand-placed waypoints,
resampled to equally spaced points. Coordinates: 1000 x 650 box, y axis down.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

WIDTH = 40.0
N_POINTS = 240
BOX = (1000.0, 650.0)

# (section name, waypoints that belong to it), in driving order. The first
# waypoint of the first section is the start of the main straight.
SECTIONS: list[tuple[str, list[tuple[float, float]]]] = [
    ("start straight", [(170, 590), (340, 590), (540, 590), (740, 590)]),
    ("hairpin", [(850, 588), (925, 555), (940, 505), (905, 462), (840, 452)]),
    ("chicane", [(769, 470), (688, 435), (608, 437), (568, 402)]),
    ("s-bends", [(576, 343), (618, 260), (592, 212), (514, 205),
                 (413, 194), (372, 156)]),
    ("sweeping curve", [(330, 130), (230, 105), (130, 150), (75, 250),
                        (60, 380), (68, 500), (95, 560), (135, 586)]),
]


def catmull_rom_closed(points: np.ndarray, samples_per_seg: int = 40) -> np.ndarray:
    """Uniform Catmull-Rom spline through points, closed. Returns dense curve."""
    n = len(points)
    t = np.linspace(0.0, 1.0, samples_per_seg, endpoint=False)[:, None]
    out = []
    for i in range(n):
        p0, p1, p2, p3 = (points[(i + k) % n] for k in (-1, 0, 1, 2))
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t
                          + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t**2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3))
    return np.vstack(out)


def resample_closed(curve: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Resample a closed dense curve to n equally spaced points.

    Returns the points and the arc-length position (0..1) of each dense input
    sample, so callers can map dense indices to resampled indices.
    """
    closed = np.vstack([curve, curve[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = s[-1]
    targets = np.arange(n) * total / n
    x = np.interp(targets, s, closed[:, 0])
    y = np.interp(targets, s, closed[:, 1])
    return np.column_stack([x, y]), s[:-1] / total


def build() -> dict:
    waypoints: list[tuple[float, float]] = []
    section_first_wp: list[int] = []
    for _, pts in SECTIONS:
        section_first_wp.append(len(waypoints))
        waypoints.extend(pts)
    wp = np.array(waypoints, dtype=float)

    per_seg = 40
    dense = catmull_rom_closed(wp, per_seg)
    centerline, dense_pos = resample_closed(dense, N_POINTS)

    # Section boundaries: dense index of each section's first waypoint -> resampled index.
    starts = []
    for first in section_first_wp:
        pos = dense_pos[first * per_seg]
        starts.append(int(round(pos * N_POINTS)) % N_POINTS)
    starts[0] = 0
    sections = []
    for i, (name, _) in enumerate(SECTIONS):
        to = starts[i + 1] - 1 if i + 1 < len(SECTIONS) else N_POINTS - 1
        sections.append({"name": name, "fromIndex": starts[i], "toIndex": to})

    d = centerline[1] - centerline[0]
    start = {"x": round(float(centerline[0][0]), 2),
             "y": round(float(centerline[0][1]), 2),
             "heading": round(float(np.arctan2(d[1], d[0])), 4)}
    return {
        "name": "Smocza Pętla",
        "width": WIDTH,
        "box": {"width": BOX[0], "height": BOX[1]},
        "start": start,
        "centerline": [[round(float(x), 2), round(float(y), 2)] for x, y in centerline],
        "sections": sections,
    }


def preview(track: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    c = np.array(track["centerline"])
    tan = np.roll(c, -1, axis=0) - np.roll(c, 1, axis=0)
    nrm = np.column_stack([-tan[:, 1], tan[:, 0]])
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    h = track["width"] / 2
    fig, ax = plt.subplots(figsize=(10, 6.5))
    for edge in (c + nrm * h, c - nrm * h):
        e = np.vstack([edge, edge[:1]])
        ax.plot(e[:, 0], e[:, 1], color="black", lw=1.5)
    colors = ["#4c78a8", "#e45756", "#f58518", "#54a24b", "#b279a2"]
    for sec, col in zip(track["sections"], colors):
        seg = c[sec["fromIndex"]: sec["toIndex"] + 1]
        ax.plot(seg[:, 0], seg[:, 1], color=col, lw=3, label=sec["name"])
    s = track["start"]
    ax.annotate("start", (s["x"], s["y"]), xytext=(s["x"], s["y"] + 35), ha="center",
                arrowprops={"arrowstyle": "->"})
    ax.set_xlim(0, track["box"]["width"])
    ax.set_ylim(track["box"]["height"], 0)
    ax.set_aspect("equal")
    ax.set_title(track["name"])
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=100)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="also write a PNG preview (needs matplotlib)")
    args = parser.parse_args()
    track = build()
    out = Path(__file__).with_name("track.json")
    out.write_text(json.dumps(track, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.preview:
        preview(track, args.preview)


if __name__ == "__main__":
    main()
