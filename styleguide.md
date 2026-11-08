# Styleguide

- Code, comments, commits and docs in English. Small files, one responsibility each.
- Python 3.12, `trainer/` package, deps: numpy (+ pytest for tests). No torch/tensorflow.
  Managed with `uv` (`uv run pytest`). Type hints on public functions.
- TypeScript strict, Vite, plain Canvas 2D, no UI framework, no runtime deps beyond Vite.
  Tests with Vitest for pure logic (geometry, parsing). `npm run build` must pass with no errors.
- The replay format in `docs/replay-format.md` is a contract: both sides follow it exactly.
  If you think it must change, stop and report BLOCKED instead of changing it.
- Determinism: training takes a `--seed`; same seed -> same replay file.
- Units: track coordinates in metres-like units, angles in radians, y axis down (canvas style).
- Tests for logic, not for drawing. Every ticket ends with its checks run and listed.
- Commits: imperative, one logical change each (`Add ray sensors to car simulation`).
- Never: commit `node_modules`, `.venv`, or caches; add a backend server; hand-edit generated
  `web/public/replay.json`.
