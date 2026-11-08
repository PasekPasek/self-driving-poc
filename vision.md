# Vision

A toy proof-of-concept: a small car learns to drive a race track by itself, and the browser shows
how the model got there. Generation 1 crashes in the first corner; after N generations a car
completes the whole lap. The repo is also a showcase of claude-crew: it was planned, split into
tickets and built by role-routed agents talking through files.

Audience: developers watching a demo. It must be fun to watch and readable in 30 seconds.

## How it works
- Python trains offline: a tiny neural net (6 sensor inputs -> steer, throttle) evolved with a
  genetic algorithm (neuroevolution, numpy only). Training writes one replay file.
- TypeScript replays that file in the browser: the track, the car, its 6 sensor rays
  (3 front, 3 rear), trajectories of past generations, generation / attempt counters, best-progress chart.
- No server, no ML in the browser. The replay file is the only link between the two halves.

## Main modules
- `shared/track.json` — the track ("Smocza Pętla"): centerline + width. Single source of truth.
- `docs/replay-format.md` — the replay contract between Python and TS. Change it only via a ticket.
- `trainer/` — Python: simulation (physics, ray sensors, collisions, lap progress) and training.
- `web/` — Vite + TypeScript + Canvas 2D: replay viewer.
- `web/public/replay.json` — generated training run shipped with the demo.
