"""Run many seeds and report how watchable each training run is.

    uv run python scripts/pick_seed.py --seeds 0-63

Per seed: generation of the first lap, gen-0 crashes / stalls / best progress, the largest
single-generation jump in best progress before the lap (and the final jump onto the lap), and the track sections where the
best-progress car of some generation crashed (the "frontier") before the lap.
"""

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trainer.track import TRACK_PATH, load_track
from trainer.train import train


def parse_seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for part in text.split(","):
        lo, _, hi = part.partition("-")
        seeds.extend(range(int(lo), int(hi or lo) + 1))
    return seeds


def analyse(seed: int) -> dict:
    track = load_track()
    sections = json.loads(TRACK_PATH.read_text(encoding="utf-8"))["sections"]
    t0 = time.time()
    gens = train(seed, workers=1, log=None)
    lap = next((g["index"] for g in gens if g["completedLap"]), None)
    gen0 = gens[0]["cars"]
    crashed = sum(c["crashed"] for c in gen0)
    frontier: set[str] = set()
    best_series = [g["bestProgress"] for g in gens]
    for g in gens:
        if lap is not None and g["index"] >= lap:
            break
        car = g["cars"][g["bestCarIndex"]]
        if car["crashed"]:
            seg, _, _ = track.project(car["crash"]["x"], car["crash"]["y"])
            frontier.update(s["name"] for s in sections if s["fromIndex"] <= seg <= s["toIndex"])
    end = lap if lap is not None else len(gens)
    series = best_series[:end]  # generations before the lap
    jump = max((b - a for a, b in zip(series, series[1:])), default=0.0)
    to_lap = (best_series[end] - series[-1]) if lap is not None and series else 0.0
    return {
        "seed": seed, "lap": lap, "crashes": crashed, "stalls": len(gen0) - crashed,
        "gen0_best": best_series[0], "frontier": sorted(frontier, key=lambda n: [s["name"] for s in sections].index(n)),
        "jump": jump, "to_lap": to_lap, "seconds": time.time() - t0, "series": best_series,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="0-31", help="e.g. 0-31 or 1,5,9-12")
    parser.add_argument("--workers", type=int, default=mp.cpu_count())
    parser.add_argument("--series", action="store_true", help="print the best-progress list per seed")
    args = parser.parse_args()

    with mp.get_context("fork").Pool(args.workers) as pool:
        rows = pool.map(analyse, parse_seeds(args.seeds), chunksize=1)
    print("seed  lap  gen0:crash stall best   jump  tolap  frontier sections")
    for r in rows:
        lap = "-" if r["lap"] is None else str(r["lap"])
        print(
            f"{r['seed']:4d}  {lap:>3}  {r['crashes']:6d} {r['stalls']:5d} {r['gen0_best']:5.3f}  "
            f"{r['jump']:5.3f} {r['to_lap']:5.3f}   {len(r['frontier'])}/5 {', '.join(r['frontier'])}"
        )
        if args.series:
            print("      " + " ".join(f"{b:.2f}" for b in r["series"]))


if __name__ == "__main__":
    main()
