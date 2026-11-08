"""Ray sensors: distance from the car centre to the nearest track boundary."""

import numpy as np

from .constants import SENSOR_ANGLES, SENSOR_MAX_RANGE
from .track import Track

_ANGLES = np.asarray(SENSOR_ANGLES)


def read_sensors(track: Track, x: float, y: float, heading: float) -> np.ndarray:
    """Six distances in 0..1 (1 = nothing within ``SENSOR_MAX_RANGE``), in ``SENSOR_ANGLES`` order."""
    ang = _ANGLES + heading
    dx = np.cos(ang)[:, None]
    dy = np.sin(ang)[:, None]
    ox, oy = track.wall_origin[:, 0], track.wall_origin[:, 1]
    ex, ey = track.wall_edge[:, 0], track.wall_edge[:, 1]
    wx = ox - x
    wy = oy - y
    denom = dx * ey - dy * ex  # (6, 2n)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (wx * ey - wy * ex) / denom  # distance along the ray
        s = (wx * dy - wy * dx) / denom  # position along the wall segment
    hit = (t >= 0.0) & (s >= 0.0) & (s <= 1.0)  # parallel rays give nan -> False
    dist = np.where(hit, t, np.inf).min(axis=1)
    return np.minimum(dist / SENSOR_MAX_RANGE, 1.0)
