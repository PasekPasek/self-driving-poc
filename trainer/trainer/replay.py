"""Serialise training history in the replay contract (docs/replay-format.md)."""

import json
from pathlib import Path

from .constants import DT, SENSOR_ANGLES, SENSOR_MAX_RANGE
from .evaluate import CarRecord


def _round_list(values, digits: int) -> list[float]:
    return [round(float(v), digits) for v in values]


def car_json(rec: CarRecord, with_extras: bool) -> dict:
    progress = 1.0 if rec.completed else min(round(rec.progress, 4), 0.9999)
    last = len(rec.frames) - 1
    car: dict = {
        "frames": [
            [round(float(x), 1), round(float(y), 1), round(float(h), 3)] for x, y, h in rec.frames
        ],
        "progress": progress,
        "crashed": rec.crashed,
        "crash": None
        if rec.crash is None
        else {"x": round(rec.crash[0], 1), "y": round(rec.crash[1], 1), "frame": last},
    }
    if with_extras:
        car["sensors"] = [_round_list(row, 2) for row in rec.sensors]
        car["outputs"] = [_round_list(row, 2) for row in rec.outputs]
    return car


def generation_json(index: int, records: list[CarRecord]) -> dict:
    cars = [car_json(r, False) for r in records]
    best = max(range(len(cars)), key=lambda i: (cars[i]["progress"], -i))
    cars[best] = car_json(records[best], True)
    return {
        "index": index,
        "bestProgress": cars[best]["progress"],
        "completedLap": any(c["progress"] == 1.0 for c in cars),
        "bestCarIndex": best,
        "cars": cars,
    }


def write_replay(path: Path, seed: int, population: int, stride: int, generations: list[dict]) -> None:
    replay = {
        "meta": {
            "seed": seed,
            "populationSize": population,
            "generations": len(generations),
            "dt": DT,
            "frameStride": stride,
            "track": "shared/track.json",
            "sensorAngles": list(SENSOR_ANGLES),
            "sensorMaxRange": SENSOR_MAX_RANGE,
        },
        "generations": generations,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(replay, separators=(",", ":")), encoding="utf-8")
