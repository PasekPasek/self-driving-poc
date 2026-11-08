"""Ray sensors: distance from the car centre to the nearest track boundary."""

import numpy as np

from .constants import SENSOR_ANGLES, SENSOR_MAX_RANGE
from .track import Track

_ANGLES = np.asarray(SENSOR_ANGLES)
_WALL_WINDOW = 24  # boundary segments searched either side of the car (~250 units of arc)
_WINDOW_OFFSETS = np.arange(-_WALL_WINDOW, _WALL_WINDOW + 1)


def read_sensors(
    track: Track, x: float, y: float, heading: float, seg: int | None = None
) -> np.ndarray:
    """Six distances in 0..1 (1 = nothing within ``SENSOR_MAX_RANGE``), in ``SENSOR_ANGLES`` order.

    With ``seg`` (the car's nearest centerline segment) only the boundary segments within
    ``_WALL_WINDOW`` of it are tested. That matches the full test whenever the car is on the
    track, because the first wall a ray crosses lies within sensor range of the car.
    """
    ang = _ANGLES + heading
    dx = np.cos(ang)[:, None]
    dy = np.sin(ang)[:, None]
    origin, edge = track.wall_origin, track.wall_edge
    if seg is not None:
        n = track.n
        idx = (seg + _WINDOW_OFFSETS) % n
        idx = np.concatenate((idx, idx + n))  # both boundaries
        origin, edge = origin[idx], edge[idx]
    ox, oy = origin[:, 0], origin[:, 1]
    ex, ey = edge[:, 0], edge[:, 1]
    wx = ox - x
    wy = oy - y
    denom = dx * ey - dy * ex  # (6, 2n)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (wx * ey - wy * ex) / denom  # distance along the ray
        s = (wx * dy - wy * dx) / denom  # position along the wall segment
    hit = (t >= 0.0) & (s >= 0.0) & (s <= 1.0)  # parallel rays give nan -> False
    dist = np.where(hit, t, np.inf).min(axis=1)
    return np.minimum(dist / SENSOR_MAX_RANGE, 1.0)
