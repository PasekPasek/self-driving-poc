"""Evaluate a population: one deterministic episode per genome, optionally in worker processes."""

import math
import multiprocessing as mp
from dataclasses import dataclass

import numpy as np

from .network import NetController
from .simulation import simulate
from .track import Track, load_track

MAX_FRAMES = 3000  # simulation steps per episode (a lap needs ~2000)
STALL_FRAMES = 120  # steps without progress before a car is stopped (timeout)
SPEED_BONUS = 0.5  # extra fitness for a completed lap, scaled by how early it finished


@dataclass(frozen=True)
class CarRecord:
    """Stride-sampled episode (the last frame is always the final pose)."""

    frames: np.ndarray  # (K, 3), heading wrapped to [-pi, pi)
    sensors: np.ndarray  # (K, 6)
    outputs: np.ndarray  # (K, 2), last row repeated so there is one per frame
    progress: float
    crashed: bool
    crash: tuple[float, float] | None
    completed: bool
    fitness: float


def run_car(track: Track, genome: np.ndarray, stride: int) -> CarRecord:
    ep = simulate(track, NetController(genome), MAX_FRAMES, stall_frames=STALL_FRAMES)
    count = len(ep.frames)
    keep = list(range(0, count, stride))
    if keep[-1] != count - 1:
        keep.append(count - 1)
    frames = ep.frames[keep].copy()
    frames[:, 2] = (frames[:, 2] + math.pi) % (2 * math.pi) - math.pi  # wrap before rounding
    outputs = ep.outputs[[min(i, len(ep.outputs) - 1) for i in keep]] if len(ep.outputs) else np.zeros((len(keep), 2))
    progress = ep.final_progress
    fitness = progress
    if ep.completed_lap:
        fitness += SPEED_BONUS * (1.0 - (count - 1) / MAX_FRAMES)
    return CarRecord(
        frames=frames,
        sensors=ep.sensors[keep],
        outputs=outputs,
        progress=progress,
        crashed=ep.crashed,
        crash=None if ep.crash is None else (ep.crash[0], ep.crash[1]),
        completed=ep.completed_lap,
        fitness=fitness,
    )


_worker_track: Track | None = None


def _init_worker() -> None:
    global _worker_track
    _worker_track = load_track()


def _run_job(job: tuple[np.ndarray, int]) -> CarRecord:
    assert _worker_track is not None
    return run_car(_worker_track, job[0], job[1])


class Evaluator:
    """Evaluates genomes in input order, so results do not depend on the worker count."""

    def __init__(self, stride: int, workers: int = 1) -> None:
        self._stride = stride
        self._pool = None
        self._track = load_track()
        if workers > 1:
            self._pool = mp.get_context("fork").Pool(workers, initializer=_init_worker)

    def evaluate(self, population: np.ndarray) -> list[CarRecord]:
        if self._pool is None:
            return [run_car(self._track, g, self._stride) for g in population]
        return self._pool.map(_run_job, [(g, self._stride) for g in population], chunksize=1)

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
