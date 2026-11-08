"""Simulation constants. Sensor and timing values follow docs/replay-format.md."""

DT = 0.05  # seconds per simulation step (meta.dt)
SENSOR_ANGLES = (-0.6, 0.0, 0.6, 2.54, 3.1416, -2.54)  # rad, 3 front then 3 rear
SENSOR_MAX_RANGE = 150.0  # track units; sensors saturate here

MAX_SPEED = 30.0  # units / s
MIN_SPEED = -8.0  # reversing is allowed but slow
ACCELERATION = 20.0  # units / s^2 at full throttle
MAX_TURN_RATE = 2.0  # rad / s at full steer, once speed >= TURN_SPEED_REF
TURN_SPEED_REF = 5.0  # below this speed the turn rate scales down (no spinning on the spot)

DEFAULT_MAX_FRAMES = 2000  # simulation steps per episode
