"""Track geometry: boundaries, nearest-point projection and lap arc length."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TRACK_PATH = Path(__file__).resolve().parents[2] / "shared" / "track.json"
_WINDOW = 8  # segments searched either side of the previous nearest segment


@dataclass(frozen=True)
class Track:
    width: float
    start: tuple[float, float, float]
    centerline: np.ndarray  # (n, 2), closed implicitly
    seg_len: np.ndarray  # (n,) length of segment i -> i+1
    arc_start: np.ndarray  # (n,) arc length at centerline[i]
    lap_length: float
    # Boundary segments (2n, 2): origin and edge vector, for ray casting.
    wall_origin: np.ndarray
    wall_edge: np.ndarray
    # Centerline segments tiled 3x so a window slice never needs wrap-around.
    _seg_a: np.ndarray
    _seg_e: np.ndarray
    _seg_len2: np.ndarray

    @property
    def n(self) -> int:
        return len(self.centerline)

    def project(self, x: float, y: float, hint: int | None = None) -> tuple[int, float, float]:
        """Nearest point on the centerline: (segment index, arc length, distance).

        With ``hint`` only segments near it are searched (cheap, and immune to jumping
        to a neighbouring leg of the track); without it all segments are searched.
        """
        n = self.n
        if hint is None:
            lo, hi = n, 2 * n
        else:
            lo, hi = hint + n - _WINDOW, hint + n + _WINDOW + 1
        a = self._seg_a[lo:hi]
        e = self._seg_e[lo:hi]
        wx = x - a[:, 0]
        wy = y - a[:, 1]
        t = np.clip((wx * e[:, 0] + wy * e[:, 1]) / self._seg_len2[lo:hi], 0.0, 1.0)
        dx = wx - t * e[:, 0]
        dy = wy - t * e[:, 1]
        d2 = dx * dx + dy * dy
        k = int(np.argmin(d2))
        seg = (lo + k) % n
        return seg, float(self.arc_start[seg] + t[k] * self.seg_len[seg]), math.sqrt(float(d2[k]))


def load_track(path: Path = TRACK_PATH) -> Track:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    c = np.asarray(data["centerline"], dtype=float)
    width = float(data["width"])
    edge = np.roll(c, -1, axis=0) - c
    seg_len = np.hypot(edge[:, 0], edge[:, 1])
    arc_start = np.concatenate(([0.0], np.cumsum(seg_len)[:-1]))

    tangent = np.roll(c, -1, axis=0) - np.roll(c, 1, axis=0)
    tangent /= np.hypot(tangent[:, 0], tangent[:, 1])[:, None]
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    half = width / 2.0
    origins, edges = [], []
    for side in (half, -half):
        b = c + side * normal
        origins.append(b)
        edges.append(np.roll(b, -1, axis=0) - b)

    s = data["start"]
    return Track(
        width=width,
        start=(float(s["x"]), float(s["y"]), float(s["heading"])),
        centerline=c,
        seg_len=seg_len,
        arc_start=arc_start,
        lap_length=float(seg_len.sum()),
        wall_origin=np.concatenate(origins),
        wall_edge=np.concatenate(edges),
        _seg_a=np.tile(c, (3, 1)),
        _seg_e=np.tile(edge, (3, 1)),
        _seg_len2=np.tile(seg_len**2, 3),
    )
