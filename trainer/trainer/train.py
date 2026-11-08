"""Neuroevolution trainer: ``python -m trainer.train --seed 42 --out ../web/public/replay.json``."""

import argparse
import os
import time
from pathlib import Path

import numpy as np

from .evaluate import Evaluator
from .genetic import initial_population, next_population
from .network import GENOME_SIZE
from .replay import generation_json, write_replay

EXTRA_GENERATIONS = 2  # generations run after the first completed lap


def train(
    seed: int,
    population_size: int = 30,
    max_generations: int = 80,
    stride: int = 8,
    workers: int = 1,
    log=print,
) -> list[dict]:
    """Evolve until a car completes the lap (plus two more generations); return replay generations."""
    rng = np.random.default_rng(seed)
    population = initial_population(rng, population_size, GENOME_SIZE)
    evaluator = Evaluator(stride, workers)
    generations: list[dict] = []
    extra_left = None
    try:
        for index in range(max_generations):
            records = evaluator.evaluate(population)
            gen = generation_json(index, records)
            generations.append(gen)
            crashes = sum(c["crashed"] for c in gen["cars"])
            log(f"gen {index:3d}  best {gen['bestProgress'] * 100:5.1f}%  crashes {crashes}/{population_size}")
            if gen["completedLap"] and extra_left is None:
                extra_left = EXTRA_GENERATIONS
            elif extra_left is not None:
                extra_left -= 1
            if extra_left == 0:
                break
            fitness = np.array([r.fitness for r in records])
            population = next_population(rng, population, fitness)
    finally:
        evaluator.close()
    return generations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("../web/public/replay.json"))
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--max-generations", type=int, default=80)
    parser.add_argument("--frame-stride", type=int, default=8)
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()

    start = time.time()
    generations = train(
        args.seed, args.population, args.max_generations, args.frame_stride, args.workers
    )
    write_replay(args.out, args.seed, args.population, args.frame_stride, generations)
    done = generations[-1]["completedLap"] or any(g["completedLap"] for g in generations)
    print(
        f"wrote {args.out} ({args.out.stat().st_size / 1e6:.2f} MB): {len(generations)} generations, "
        f"lap completed: {done}, {time.time() - start:.1f}s"
    )


if __name__ == "__main__":
    main()
