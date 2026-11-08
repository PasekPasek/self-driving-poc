import json
import math
import time

import numpy as np
import pytest

from trainer.constants import DT, MAX_SPEED, SENSOR_ANGLES, SENSOR_MAX_RANGE
from trainer.sensors import read_sensors
from trainer.simulation import simulate
from trainer.track import TRACK_PATH, load_track

REPO = TRACK_PATH.parents[1]


@pytest.fixture(scope="module")
def track():
    return load_track()


def full_throttle_straight(_sensors):
    return 0.0, 1.0


def centerline_follower(track, lookahead=3, speed=20.0):
    """Cheating controller: reads the track geometry to steer at a point ahead on the centerline."""
    from trainer.constants import ACCELERATION, MAX_TURN_RATE, TURN_SPEED_REF

    x, y, heading = track.start
    v = 0.0
    seg = None

    def control(_sensors):
        nonlocal x, y, heading, v, seg
        seg, _, _ = track.project(x, y, seg)
        tx, ty = track.centerline[(seg + lookahead) % track.n]
        err = math.atan2(ty - y, tx - x) - heading
        err = (err + math.pi) % (2 * math.pi) - math.pi
        steer = max(-1.0, min(1.0, err * 2.0))
        throttle = max(-1.0, min(1.0, (speed - v) * 0.5))
        # Mirror the simulator's integration so the next call sees the new pose.
        v = max(-8.0, min(MAX_SPEED, v + throttle * ACCELERATION * DT))
        heading += steer * MAX_TURN_RATE * DT * min(1.0, abs(v) / TURN_SPEED_REF)
        x += math.cos(heading) * v * DT
        y += math.sin(heading) * v * DT
        return steer, throttle

    return control


def mid_straight_pose(track, index=30):
    """Centerline point on the start straight with the local track direction as heading."""
    (x, y), (nx, ny) = track.centerline[index], track.centerline[index + 1]
    return x, y, math.atan2(ny - y, nx - x)


def test_sensor_angles_match_replay_contract():
    sample = json.loads((REPO / "fixtures" / "replay.sample.json").read_text())
    assert list(SENSOR_ANGLES) == sample["meta"]["sensorAngles"]
    assert SENSOR_MAX_RANGE == sample["meta"]["sensorMaxRange"]
    assert DT == sample["meta"]["dt"]


def test_standing_car_sensors_match_hand_computed_distances(track):
    # Mid-straight pose: both walls are parallel to the heading at +-half-width, so a ray at
    # relative angle a hits a wall at half / sin(|a|). Nothing else lies within 150 units.
    x, y, heading = mid_straight_pose(track)
    reading = read_sensors(track, x, y, heading) * SENSOR_MAX_RANGE
    half = track.width / 2
    side = half / math.sin(0.6)
    rear_side = half / math.sin(math.pi - 2.54)
    assert reading[0] == pytest.approx(side, rel=0.01)  # front-left
    assert reading[1] == pytest.approx(SENSOR_MAX_RANGE)  # front-centre: far straight ahead
    assert reading[2] == pytest.approx(side, rel=0.01)  # front-right
    assert reading[3] == pytest.approx(rear_side, rel=0.01)  # rear-right
    assert reading[4] == pytest.approx(SENSOR_MAX_RANGE)  # rear-centre: straight behind
    assert reading[5] == pytest.approx(rear_side, rel=0.01)  # rear-left


def test_start_pose_front_sensors(track):
    reading = read_sensors(track, *track.start) * SENSOR_MAX_RANGE
    side = track.width / 2 / math.sin(0.6)
    assert reading[0] == pytest.approx(side, rel=0.01)
    assert reading[1] == pytest.approx(SENSOR_MAX_RANGE)
    assert reading[2] == pytest.approx(side, rel=0.01)


def test_sensors_facing_walls_directly(track):
    # Car across the straight: front-centre and rear-centre rays hit the walls at half-width.
    x, y, heading = mid_straight_pose(track)
    reading = read_sensors(track, x, y, heading + math.pi / 2)
    assert reading[1] * SENSOR_MAX_RANGE == pytest.approx(track.width / 2, rel=0.01)
    assert reading[4] * SENSOR_MAX_RANGE == pytest.approx(track.width / 2, rel=0.01)


def test_zero_steer_crashes_at_first_corner(track):
    ep = simulate(track, full_throttle_straight)
    assert ep.crashed and not ep.completed_lap
    cx, cy, frame = ep.crash
    assert frame == len(ep.frames) - 1
    assert (cx, cy) == (ep.frames[-1][0], ep.frames[-1][1])
    _, arc, dist = track.project(cx, cy)
    assert track.width / 2 < dist <= track.width / 2 + MAX_SPEED * DT  # just past the boundary
    # The first corner (hairpin) starts at the end of the start straight (index 66).
    assert track.arc_start[60] < arc < track.arc_start[75]
    assert 0.0 < ep.final_progress < 0.3


def test_centerline_follower_completes_a_lap(track):
    ep = simulate(track, centerline_follower(track), max_frames=3000)
    assert ep.completed_lap and not ep.crashed
    assert ep.crash is None
    assert ep.final_progress == 1.0
    assert np.all(np.diff(ep.progress) >= 0)


def test_reverse_driving_does_not_add_progress(track):
    ep = simulate(track, lambda s: (0.0, -1.0), max_frames=60)
    assert not ep.crashed
    assert ep.final_progress == 0.0


def test_timeout_is_not_a_crash(track):
    ep = simulate(track, lambda s: (0.0, 0.0), max_frames=50)
    assert not ep.crashed and not ep.completed_lap and ep.crash is None
    assert len(ep.frames) == 51 and len(ep.outputs) == 50


def test_deterministic(track):
    a = simulate(track, centerline_follower(track), max_frames=3000)
    b = simulate(track, centerline_follower(track), max_frames=3000)
    for name in ("frames", "sensors", "outputs", "progress"):
        assert np.array_equal(getattr(a, name), getattr(b, name))
    assert a.crash == b.crash


def test_episode_of_2000_frames_under_100ms(track):
    simulate(track, lambda s: (0.0, 0.0), max_frames=50)  # warm up numpy
    best = float("inf")
    for _ in range(5):
        t0 = time.perf_counter()
        ep = simulate(track, lambda s: (0.0, 0.0), max_frames=2000)
        best = min(best, time.perf_counter() - t0)
    assert len(ep.frames) == 2001
    print(f"\n2000-frame episode: {best * 1000:.1f} ms")
    assert best < 0.1
