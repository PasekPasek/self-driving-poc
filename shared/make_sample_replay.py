"""Generate fixtures/replay.sample.json: a tiny hand-made replay (not a real simulation).

Usage: python shared/make_sample_replay.py

2 generations x 3 cars along the track centerline. Generation 1's best car completes the lap.
numpy only. The output must pass shared/validate_replay.py.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from validate_replay import Projector, frame_progress

ROOT = Path(__file__).resolve().parent.parent
ANGLES = [-0.6, 0.0, 0.6, 2.54, 3.1416, -2.54]
MAX_RANGE = 150.0
STRIDE, DT = 4, 0.05
STEP = 22.0  # arc length per stored frame


def wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


class Course:
    def __init__(self, track: dict) -> None:
        c = np.array(track["centerline"], dtype=float)
        self.c, self.proj = c, Projector(c)
        self.nxt = np.roll(c, -1, axis=0)
        seg = np.linalg.norm(self.nxt - c, axis=1)
        self.cum = np.concatenate([[0.0], np.cumsum(seg)])
        self.total = self.cum[-1]
        self.half = track["width"] / 2

    def pose(self, s: float, offset: float) -> tuple[float, float, float]:
        s %= self.total
        i = int(np.searchsorted(self.cum, s, side="right") - 1)
        t = (s - self.cum[i]) / (self.cum[i + 1] - self.cum[i])
        d = self.nxt[i] - self.c[i]
        heading = math.atan2(d[1], d[0])
        p = self.c[i] + t * d
        nx, ny = -d[1] / np.linalg.norm(d), d[0] / np.linalg.norm(d)  # left of travel
        return float(p[0] - nx * offset), float(p[1] - ny * offset), heading  # +offset = right

    def ray(self, x: float, y: float, angle: float) -> float:
        """Distance to the nearest track edge along a ray (edges = centerline +- half width)."""
        d = np.array([math.cos(angle), math.sin(angle)])
        tan = self.nxt - self.c
        nrm = np.column_stack([-tan[:, 1], tan[:, 0]]) / np.linalg.norm(tan, axis=1)[:, None]
        best = MAX_RANGE
        for sign in (1.0, -1.0):
            a, b = self.c + sign * self.half * nrm, self.nxt + sign * self.half * nrm
            e = b - a
            den = d[0] * e[:, 1] - d[1] * e[:, 0]
            with np.errstate(divide="ignore", invalid="ignore"):
                w = a - np.array([x, y])
                t = (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / den
                u = (w[:, 0] * d[1] - w[:, 1] * d[0]) / den
            hit = (den != 0) & (t > 0) & (u >= 0) & (u <= 1)
            if hit.any():
                best = min(best, float(t[hit].min()))
        return best


def make_car(course: Course, target: float, crash: bool, extras: bool, wobble: float) -> dict:
    """Drive along the centerline until `target` lap fraction; then crash off the outside edge or stop."""
    frames: list[list[float]] = []
    k, finished = 0, False
    while not finished:
        s = k * STEP
        frac = s / course.total
        last = frac >= target
        offset = wobble * math.sin(k * 0.45)
        if last and crash:
            offset = course.half + 2.0  # just outside the track
        x, y, h = course.pose(s, offset)
        frames.append([round(x, 1), round(y, 1), round(wrap(h), 3)])
        if last:
            finished = True
        k += 1
    car: dict = {"frames": frames}
    progress = frame_progress(course.proj, frames)
    completed = progress >= 1.0
    car["progress"] = 1.0 if completed else round(progress, 4)
    car["crashed"] = crash
    car["crash"] = {"x": frames[-1][0], "y": frames[-1][1], "frame": len(frames) - 1} if crash else None
    if extras:
        car["sensors"] = [[round(course.ray(x, y, h + a) / MAX_RANGE, 2) for a in ANGLES]
                          for x, y, h in frames]
        car["outputs"] = [[round(0.6 * math.cos(k * 0.45), 2), round(min(1.0, 0.5 + 0.05 * k), 2)]
                          for k in range(len(frames))]
    return car


def build() -> dict:
    track = json.loads((ROOT / "shared" / "track.json").read_text(encoding="utf-8"))
    course = Course(track)
    # (target lap fraction, crashes, wobble) per car; generation 1 car 0 completes the lap.
    plan = [
        [(0.05, True, 3.0), (0.30, True, 4.0), (0.02, True, 2.0)],
        [(1.02, False, 3.0), (0.45, True, 4.0), (0.10, True, 2.0)],
    ]
    generations = []
    for gi, specs in enumerate(plan):
        cars = []
        best = max(range(len(specs)), key=lambda i: (specs[i][0], -i))
        for ci, (target, crash, wobble) in enumerate(specs):
            cars.append(make_car(course, target, crash, ci == best, wobble))
        progresses = [c["progress"] for c in cars]
        generations.append({
            "index": gi,
            "bestProgress": max(progresses),
            "completedLap": any(p >= 1.0 for p in progresses),
            "bestCarIndex": max(range(len(cars)), key=lambda i: (progresses[i], -i)),
            "cars": cars,
        })
    meta = {"seed": 1, "populationSize": 3, "generations": 2, "dt": DT, "frameStride": STRIDE,
            "track": "shared/track.json", "sensorAngles": ANGLES, "sensorMaxRange": MAX_RANGE}
    return {"meta": meta, "generations": generations}


def main() -> None:
    out = ROOT / "fixtures" / "replay.sample.json"
    out.write_text(json.dumps(build(), separators=(",", ":"), ensure_ascii=False) + "\n",
                   encoding="utf-8")


if __name__ == "__main__":
    main()
