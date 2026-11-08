import json
import sys

import numpy as np
import pytest

from trainer.network import GENOME_SIZE, NetController
from trainer.replay import write_replay
from trainer.sensors import read_sensors
from trainer.simulation import simulate
from trainer.track import TRACK_PATH, load_track
from trainer.train import train

SHARED = TRACK_PATH.parent
sys.path.insert(0, str(SHARED))
from validate_replay import validate  # noqa: E402


@pytest.fixture(scope="module")
def track():
    return load_track()


def tiny_run(tmp_path, name, seed=7, workers=1):
    gens = train(seed, population_size=6, max_generations=3, workers=workers, log=lambda _: None)
    out = tmp_path / name
    write_replay(out, seed, 6, 8, gens)
    return out, gens


def test_windowed_ray_cast_agrees_with_full(track):
    rng = np.random.default_rng(0)
    checked = 0
    for _ in range(3000):
        i = int(rng.integers(0, track.n))
        # Random pose on the track: centerline point, lateral offset inside the width, any heading.
        x, y = track.centerline[i]
        nx, ny = track.centerline[(i + 1) % track.n] - track.centerline[i]
        norm = np.hypot(nx, ny)
        off = rng.uniform(-0.55, 0.55) * track.width  # includes just-off-track poses
        x, y = x - ny / norm * off, y + nx / norm * off
        heading = rng.uniform(-np.pi, np.pi)
        seg, _, dist = track.project(x, y)
        full = read_sensors(track, x, y, heading)
        windowed = read_sensors(track, x, y, heading, seg, dist)
        assert np.array_equal(full, windowed)
        checked += 1
    assert checked == 3000


def test_windowed_ray_cast_exact_in_the_known_thin_strip(track):
    # Poses 19.5-20.5 from the centerline (half width 20) near the hairpin/chicane used to mismatch.
    rng = np.random.default_rng(1)
    for _ in range(3000):
        i = int(rng.integers(95, 120))
        x, y = track.centerline[i]
        nx, ny = track.centerline[(i + 1) % track.n] - track.centerline[i]
        norm = np.hypot(nx, ny)
        off = rng.choice([-1, 1]) * rng.uniform(19.5, 20.5)
        x, y = x - ny / norm * off, y + nx / norm * off
        heading = rng.uniform(-np.pi, np.pi)
        seg, _, dist = track.project(x, y)
        assert np.array_equal(read_sensors(track, x, y, heading), read_sensors(track, x, y, heading, seg, dist))


def test_stall_stops_a_standing_car_as_timeout(track):
    ep = simulate(track, lambda _s: (0.0, 0.0), 3000, stall_frames=100)
    assert len(ep.frames) < 300 and not ep.crashed and not ep.completed_lap


def test_net_controller_is_deterministic_and_bounded():
    genome = np.random.default_rng(1).normal(size=GENOME_SIZE)
    a, b = NetController(genome), NetController(genome)
    sensors = np.linspace(0, 1, 6)
    for _ in range(20):
        out = a(sensors)
        assert out == b(sensors)
        assert all(-1.0 <= v <= 1.0 for v in out)


def test_short_run_validates_against_replay_format(tmp_path):
    out, _ = tiny_run(tmp_path, "r.json")
    assert validate(out) == []
    data = json.loads(out.read_text())
    assert data["meta"]["generations"] == len(data["generations"]) == 3
    assert all(len(g["cars"]) == 6 for g in data["generations"])


def test_same_seed_gives_identical_bytes_across_worker_counts(tmp_path):
    a, _ = tiny_run(tmp_path, "a.json", workers=1)
    b, _ = tiny_run(tmp_path, "b.json", workers=1)
    c, _ = tiny_run(tmp_path, "c.json", workers=2)
    assert a.read_bytes() == b.read_bytes() == c.read_bytes()


def test_different_seed_differs(tmp_path):
    a, _ = tiny_run(tmp_path, "a.json", seed=7)
    b, _ = tiny_run(tmp_path, "b.json", seed=8)
    assert a.read_bytes() != b.read_bytes()


def test_default_seed_shows_learning_curve_and_completes_lap():
    gens = train(42, log=lambda _: None)
    assert gens[0]["bestProgress"] < 0.25
    assert gens[-1]["completedLap"] and len(gens) <= 80
    assert sum(g["completedLap"] for g in gens) >= 1
