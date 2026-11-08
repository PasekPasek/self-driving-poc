"""Deterministic episode: one car, a controller function, a track."""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .constants import (
    ACCELERATION,
    DEFAULT_MAX_FRAMES,
    DT,
    MAX_SPEED,
    MAX_TURN_RATE,
    MIN_SPEED,
    TURN_SPEED_REF,
)
from .sensors import read_sensors
from .track import Track

# Controller: sensors (6 floats in 0..1) -> (steer, throttle), each in [-1, 1].
Controller = Callable[[np.ndarray], tuple[float, float]]


@dataclass(frozen=True)
class Episode:
    """Result of one episode. Frame 0 is the start pose; arrays share the frame index.

    ``outputs`` has one row per simulation step (``len(frames) - 1``): the controller's
    (clamped) output that produced the step from frame i to frame i + 1.
    """

    frames: np.ndarray  # (F, 3) x, y, heading (heading unwrapped, radians)
    sensors: np.ndarray  # (F, 6) readings at each frame
    outputs: np.ndarray  # (F - 1, 2) steer, throttle
    progress: np.ndarray  # (F,) running-max lap fraction, 1.0 on completion
    crashed: bool
    crash: tuple[float, float, int] | None  # x, y, frame index (always the last frame)
    completed_lap: bool

    @property
    def final_progress(self) -> float:
        return float(self.progress[-1])


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def simulate(
    track: Track, controller: Controller, max_frames: int = DEFAULT_MAX_FRAMES
) -> Episode:
    """Run until crash, full lap or ``max_frames`` steps (timeout is not a crash)."""
    x, y, heading = track.start
    speed = 0.0
    half_width = track.width / 2.0
    lap = track.lap_length

    seg, arc, _ = track.project(x, y)
    prev_frac = arc / lap
    unwrapped = 0.0
    best = 0.0

    frames = [(x, y, heading)]
    sensors = [read_sensors(track, x, y, heading)]
    outputs: list[tuple[float, float]] = []
    progress = [0.0]
    crash = None
    completed = False

    for step in range(max_frames):
        steer, throttle = controller(sensors[-1])
        steer = _clamp(float(steer), -1.0, 1.0)
        throttle = _clamp(float(throttle), -1.0, 1.0)
        outputs.append((steer, throttle))

        speed = _clamp(speed + throttle * ACCELERATION * DT, MIN_SPEED, MAX_SPEED)
        heading += steer * MAX_TURN_RATE * DT * _clamp(abs(speed) / TURN_SPEED_REF, 0.0, 1.0) * (
            1.0 if speed >= 0.0 else -1.0
        )
        x += math.cos(heading) * speed * DT
        y += math.sin(heading) * speed * DT

        seg, arc, dist = track.project(x, y, seg)
        frac = arc / lap
        delta = frac - prev_frac
        delta -= round(delta)  # wrap to [-0.5, 0.5]
        if delta == -0.5:
            delta = 0.5
        prev_frac = frac
        unwrapped += delta
        best = max(best, unwrapped)

        frames.append((x, y, heading))
        sensors.append(read_sensors(track, x, y, heading))
        if dist > half_width:
            progress.append(best)
            crash = (x, y, step + 1)
            break
        if best >= 1.0:
            best = 1.0
            progress.append(best)
            completed = True
            break
        progress.append(best)

    return Episode(
        frames=np.asarray(frames),
        sensors=np.asarray(sensors),
        outputs=np.asarray(outputs).reshape(-1, 2),
        progress=np.asarray(progress),
        crashed=crash is not None,
        crash=crash,
        completed_lap=completed,
    )
