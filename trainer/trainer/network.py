"""Tiny MLP controller: 6 sensors + speed -> 8 tanh hidden -> (steer, throttle) tanh."""

import numpy as np

from .constants import ACCELERATION, DT, MAX_SPEED, MIN_SPEED

N_IN, N_HIDDEN, N_OUT = 7, 8, 2
GENOME_SIZE = N_IN * N_HIDDEN + N_HIDDEN + N_HIDDEN * N_OUT + N_OUT  # 82


def unpack(genome: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split a flat genome into (w1, b1, w2, b2)."""
    i = N_IN * N_HIDDEN
    j = i + N_HIDDEN
    k = j + N_HIDDEN * N_OUT
    return (
        genome[:i].reshape(N_IN, N_HIDDEN),
        genome[i:j],
        genome[j:k].reshape(N_HIDDEN, N_OUT),
        genome[k:],
    )


class NetController:
    """Stateful controller for ``simulate``: tracks the car's speed itself (it is a pure
    function of the throttle history), because the simulator only passes sensor readings."""

    def __init__(self, genome: np.ndarray) -> None:
        self._w1, self._b1, self._w2, self._b2 = unpack(genome)
        self._speed = 0.0

    def __call__(self, sensors: np.ndarray) -> tuple[float, float]:
        x = np.empty(N_IN)
        x[:6] = sensors
        x[6] = self._speed / MAX_SPEED
        hidden = np.tanh(x @ self._w1 + self._b1)
        steer, throttle = np.tanh(hidden @ self._w2 + self._b2)
        self._speed = min(MAX_SPEED, max(MIN_SPEED, self._speed + throttle * ACCELERATION * DT))
        return float(steer), float(throttle)
