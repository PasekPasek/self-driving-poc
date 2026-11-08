"""Validate a replay file against docs/replay-format.md.

Usage: python shared/validate_replay.py <replay.json> [--track shared/track.json]

numpy and stdlib only. Prints every violation found and exits with status 1,
or prints "OK" and exits 0.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DEFAULT_TRACK = Path(__file__).with_name("track.json")
MAX_BYTES = 8_000_000
MAX_FRAMES = 400
PROGRESS_TOLERANCE = 0.02  # frames are strided; progress is measured on every simulation step
META_KEYS = {"seed", "populationSize", "generations", "dt", "frameStride", "track",
             "sensorAngles", "sensorMaxRange"}
GEN_KEYS = {"index", "bestProgress", "completedLap", "bestCarIndex", "cars"}
CAR_KEYS = {"frames", "progress", "crashed", "crash"}
BEST_EXTRA_KEYS = {"sensors", "outputs"}


class Projector:
    """Nearest-point projection onto the closed centerline, as a lap fraction in [0, 1)."""

    def __init__(self, centerline: np.ndarray) -> None:
        self.a = centerline
        self.d = np.roll(centerline, -1, axis=0) - centerline
        self.len2 = (self.d ** 2).sum(axis=1)
        seg = np.sqrt(self.len2)
        self.cum = np.concatenate([[0.0], np.cumsum(seg)[:-1]])
        self.total = float(seg.sum())

    def fraction(self, x: float, y: float) -> float:
        p = np.array([x, y])
        t = np.clip(((p - self.a) * self.d).sum(axis=1) / self.len2, 0.0, 1.0)
        near = self.a + t[:, None] * self.d
        i = int(np.argmin(((near - p) ** 2).sum(axis=1)))
        return float((self.cum[i] + t[i] * math.sqrt(self.len2[i])) / self.total) % 1.0


def frame_progress(proj: Projector, frames: list) -> float:
    """Running maximum of the unwrapped projection over frames (backwards seam crossing never counts)."""
    prev, unwrapped, best = 0.0, 0.0, 0.0
    for x, y, _ in frames:
        cur = proj.fraction(x, y)
        delta = (cur - prev + 0.5) % 1.0 - 0.5
        unwrapped += delta
        best = max(best, unwrapped)
        prev = cur
    return min(best, 1.0)


def is_num(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def rounded(v: float, digits: int) -> bool:
    return round(v, digits) == v


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-finite number {name}")


def validate(path: Path, track_path: Path = DEFAULT_TRACK) -> list[str]:
    errors: list[str] = []

    def err(where: str, msg: str) -> None:
        errors.append(f"{where}: {msg}")

    raw = path.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) >= MAX_BYTES:
        err("file", f"size must be < {MAX_BYTES} bytes")
    try:
        data = json.loads(raw, parse_constant=_reject_constant)
    except ValueError as exc:
        return [f"file: not valid JSON ({exc})"]
    if raw.rstrip("\n") != json.dumps(data, separators=(",", ":"), ensure_ascii=False):
        err("file", 'not written as json.dumps(..., separators=(",", ":")) on one line')

    track = json.loads(track_path.read_text(encoding="utf-8"))
    centerline = np.array(track["centerline"], dtype=float)
    proj = Projector(centerline)
    start = track["start"]

    if not isinstance(data, dict) or set(data) != {"meta", "generations"}:
        return errors + ["root: keys must be exactly meta, generations"]
    meta = data["meta"]
    if not isinstance(meta, dict) or set(meta) != META_KEYS:
        return errors + [f"meta: keys must be exactly {sorted(META_KEYS)}"]
    for key in ("seed", "populationSize", "generations", "frameStride"):
        if not is_int(meta[key]):
            err("meta", f"{key} must be an integer")
    if is_int(meta["populationSize"]) and meta["populationSize"] < 1:
        err("meta", "populationSize must be >= 1")
    if is_int(meta["frameStride"]) and meta["frameStride"] < 1:
        err("meta", "frameStride must be >= 1")
    if not (is_num(meta["dt"]) and meta["dt"] > 0):
        err("meta", "dt must be a positive number")
    if not (is_num(meta["sensorMaxRange"]) and meta["sensorMaxRange"] > 0):
        err("meta", "sensorMaxRange must be a positive number")
    if not isinstance(meta["track"], str):
        err("meta", "track must be a string")
    angles = meta["sensorAngles"]
    if not (isinstance(angles, list) and len(angles) == 6 and all(is_num(a) for a in angles)):
        err("meta", "sensorAngles must be 6 numbers")
    elif not all(-3.1416 <= a <= 3.1416 for a in angles):
        err("meta", "sensorAngles must lie in [-3.1416, 3.1416]")

    gens = data["generations"]
    if not isinstance(gens, list):
        return errors + ["generations: must be an array"]
    if meta["generations"] != len(gens):
        err("meta", f"generations={meta['generations']} but file has {len(gens)}")
    pop = meta["populationSize"]

    for gi, gen in enumerate(gens):
        g = f"generations[{gi}]"
        if not isinstance(gen, dict) or set(gen) != GEN_KEYS:
            err(g, f"keys must be exactly {sorted(GEN_KEYS)}")
            continue
        if gen["index"] != gi or not is_int(gen["index"]):
            err(g, "index must equal the array position")
        cars = gen["cars"]
        if not isinstance(cars, list) or len(cars) != pop:
            err(g, f"cars must be an array of populationSize={pop} cars")
            continue
        progresses: list[float] = []
        for ci, car in enumerate(cars):
            progresses.append(_check_car(f"{g}.cars[{ci}]", car, gen.get("bestCarIndex") == ci,
                                         proj, start, err))
        best = max(range(len(cars)), key=lambda i: (progresses[i], -i))
        if gen["bestCarIndex"] != best or not is_int(gen["bestCarIndex"]):
            err(g, f"bestCarIndex must be {best} (highest progress, lowest index on ties)")
        if gen["bestProgress"] != max(progresses):
            err(g, f"bestProgress must equal the max car progress {max(progresses)}")
        if gen["completedLap"] is not any(p >= 1.0 for p in progresses):
            err(g, "completedLap must be true iff some car has progress 1.0")
    return errors


def _check_car(where: str, car: object, is_best: bool, proj: Projector, start: dict, err) -> float:
    if not isinstance(car, dict):
        err(where, "must be an object")
        return -1.0
    expected = CAR_KEYS | (BEST_EXTRA_KEYS if is_best else set())
    if set(car) != expected:
        err(where, f"keys must be exactly {sorted(expected)}")
        return -1.0
    frames = car["frames"]
    ok = isinstance(frames, list) and 1 <= len(frames) <= MAX_FRAMES
    ok = ok and all(isinstance(f, list) and len(f) == 3 and all(is_num(v) for v in f) for f in frames)
    if not ok:
        err(where, f"frames must be 1..{MAX_FRAMES} arrays of [x, y, heading]")
        return -1.0
    for i, (x, y, h) in enumerate(frames):
        if not (rounded(x, 1) and rounded(y, 1) and rounded(h, 3)):
            err(where, f"frame {i}: x, y need 1 decimal and heading 3 decimals")
            break
        if not -3.142 <= h <= 3.142:
            err(where, f"frame {i}: heading {h} outside [-pi, pi) (before rounding)")
            break
    x0, y0, h0 = frames[0]
    if abs(x0 - start["x"]) > 0.06 or abs(y0 - start["y"]) > 0.06 or abs(h0 - start["heading"]) > 0.002:
        err(where, "frame 0 must be the track start pose")
    progress = car["progress"]
    if not (is_num(progress) and 0.0 <= progress <= 1.0 and rounded(progress, 4)):
        err(where, "progress must be a number in 0..1 with 4 decimals")
        return -1.0
    crashed, crash = car["crashed"], car["crash"]
    if not isinstance(crashed, bool):
        err(where, "crashed must be a boolean")
    elif crashed:
        last = len(frames) - 1
        if not (isinstance(crash, dict) and set(crash) == {"x", "y", "frame"}):
            err(where, "crash must be {x, y, frame} when crashed")
        elif crash["frame"] != last or [crash["x"], crash["y"]] != frames[last][:2]:
            err(where, "crash must repeat the last frame's x, y and its index")
        if progress >= 1.0:
            err(where, "a crashed car cannot have progress 1.0")
    else:
        if crash is not None:
            err(where, "crash must be null when not crashed")
    if progress >= 1.0 and progress != 1.0:
        err(where, "completed progress must be exactly 1.0")
    measured = frame_progress(proj, frames)
    if progress == 1.0:
        if measured < 1.0 - PROGRESS_TOLERANCE:
            err(where, f"progress 1.0 but frames only reach {measured:.4f}")
        if crashed is True:
            err(where, "a completed car must have crashed=false")
    elif abs(measured - progress) > PROGRESS_TOLERANCE:
        err(where, f"progress {progress} disagrees with frames (projection gives {measured:.4f})")
    if is_best:
        _check_best_extras(where, car, len(frames), err)
    return progress


def _check_best_extras(where: str, car: dict, n: int, err) -> None:
    for key, width, lo, hi in (("sensors", 6, 0.0, 1.0), ("outputs", 2, -1.0, 1.0)):
        rows = car[key]
        if not (isinstance(rows, list) and len(rows) == n):
            err(where, f"{key} must have one row per frame ({n})")
            continue
        for i, row in enumerate(rows):
            good = isinstance(row, list) and len(row) == width and all(is_num(v) for v in row)
            if not good or not all(lo <= v <= hi and rounded(v, 2) for v in row):
                err(where, f"{key}[{i}] must be {width} numbers in {lo}..{hi} with 2 decimals")
                break


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--track", type=Path, default=DEFAULT_TRACK)
    args = parser.parse_args()
    errors = validate(args.file, args.track)
    if errors:
        for line in errors:
            print(f"INVALID {line}", file=sys.stderr)
        return 1
    print(f"OK {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
