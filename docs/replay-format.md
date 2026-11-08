# Replay format

The replay file is the only link between the Python trainer (writer) and the TypeScript viewer
(reader). It is a single JSON file. Both sides follow this document exactly; change it only via a ticket.

Units: track coordinates in metres-like units (the track fits a 1000 x 650 box), angles in radians,
y axis down (canvas style), `heading` 0 = +x, positive turns toward +y (clockwise on screen).
Same seed -> byte-identical file.

## Track (`shared/track.json`)

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Track name ("Smocza Pętla") |
| `width` | number | Constant track width; boundaries are centerline ± width/2 along the normal |
| `box` | `{width, height}` | Bounding box, 1000 x 650 |
| `start` | `{x, y, heading}` | Start pose, on the centerline at the start of the main straight (`centerline[0]`) |
| `centerline` | `[x, y][]` | Closed loop, 240 points, equally spaced, driving order. The loop closes implicitly: the last point connects to the first (the first point is not repeated) |
| `sections` | `{name, fromIndex, toIndex}[]` | Named sections in driving order; inclusive centerline indices; together they cover `0..n-1` |

Lap progress is the fraction (0..1) of centerline arc length covered from `start`, in driving
direction. `1` means a full lap.

## Replay file

### `meta`

| Field | Type | Unit | Meaning |
|---|---|---|---|
| `seed` | integer | | Training seed |
| `populationSize` | integer | cars | Cars per generation (length of every `cars[]`) |
| `generations` | integer | | Number of generations (length of `generations[]`) |
| `dt` | number | s | Simulation time step |
| `frameStride` | integer | steps | One stored frame every `frameStride` simulation steps; frame `i` is at time `i * frameStride * dt` |
| `track` | string | | Track file reference, relative to the replay file's repository root: `shared/track.json` |
| `sensorAngles` | number[6] | rad | Sensor directions relative to car heading: 3 front first, then 3 rear |
| `sensorMaxRange` | number | track units | Distance at which a sensor saturates |

### `generations[]` item

| Field | Type | Unit | Meaning |
|---|---|---|---|
| `index` | integer | | 0-based generation number, equals the array position |
| `bestProgress` | number | lap fraction 0..1 | Max `progress` over `cars` |
| `completedLap` | boolean | | True if any car completed the lap |
| `bestCarIndex` | integer | | Index into `cars` of the best car (highest `progress`, lowest index on ties) |
| `cars` | Car[] | | `populationSize` cars |

### `Car`

| Field | Type | Unit | Meaning |
|---|---|---|---|
| `frames` | `[x, y, heading][]` | x, y: track units, 1 decimal; heading: rad, 3 decimals | Pose per stored frame; frame 0 is the start pose. A crashed car's last frame is its crash pose |
| `progress` | number | lap fraction 0..1 | Furthest lap progress reached |
| `crashed` | boolean | | True if the car left the track |
| `crash` | `{x, y, frame} \| null` | | Crash point (1 decimal) and its index into `frames` (always the last frame); `null` iff `crashed` is false |

### Best car extras

Only `cars[bestCarIndex]` additionally carries (same length as its `frames`; other cars omit both keys):

| Field | Type | Unit | Meaning |
|---|---|---|---|
| `sensors` | `number[6][]` | 0..1, 2 decimals | Per frame, distance to the track edge along each ray in `sensorAngles` order, divided by `sensorMaxRange` (1 = nothing within range) |
| `outputs` | `[steer, throttle][]` | -1..1, 2 decimals | Per frame, network outputs: `steer` -1 (full left, heading decreases) .. 1 (full right, heading increases); `throttle` -1 (brake) .. 1 (full) |

### Size budget

Whole file < 8 MB for 30 cars x 60 generations. A frame is about 23 bytes, so the trainer must keep
the average at or below ~150 frames per car and at most 400 frames per car (choose `frameStride`
accordingly); crashed cars are short, which keeps the average low. The best car's sensors and outputs
add about 60 bytes per frame, once per generation (~1.5 MB worst case). Write compact JSON (no
indentation).

## Example

```json
{
  "meta": {
    "seed": 42, "populationSize": 30, "generations": 60, "dt": 0.05, "frameStride": 4,
    "track": "shared/track.json",
    "sensorAngles": [-0.6, 0, 0.6, 2.54, 3.1416, -2.54],
    "sensorMaxRange": 150
  },
  "generations": [
    {
      "index": 0, "bestProgress": 0.012, "completedLap": false, "bestCarIndex": 1,
      "cars": [
        {"frames": [[170.0, 590.0, 0.015], [171.2, 590.0, 0.015]], "progress": 0.004,
         "crashed": true, "crash": {"x": 171.2, "y": 590.0, "frame": 1}},
        {"frames": [[170.0, 590.0, 0.015], [172.0, 590.0, 0.015]], "progress": 0.012,
         "crashed": true, "crash": {"x": 172.0, "y": 590.0, "frame": 1},
         "sensors": [[1, 1, 1, 0.1, 0.1, 0.1], [1, 1, 1, 0.1, 0.1, 0.1]],
         "outputs": [[0.0, 0.5], [0.0, 0.5]]}
      ]
    }
  ]
}
```

(The example is abbreviated: real files have `populationSize` cars per generation and `meta.generations`
generations. A full valid sample is `fixtures/replay.sample.json`.)
