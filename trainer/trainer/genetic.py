"""Genetic algorithm over flat genomes. All randomness comes from the caller's Generator."""

import numpy as np

ELITE = 3
TOURNAMENT = 3
MUTATION_RATE = 0.05  # probability that a gene mutates
MUTATION_SIGMA = 0.1
INIT_SIGMA = 0.5  # std of the initial genes: small weights, so gen-0 cars wobble instead of spinning
INIT_THROTTLE_BIAS = 1.0  # added to the throttle output bias at init: gen-0 cars drive, then crash


def initial_population(rng: np.random.Generator, size: int, genome_size: int) -> np.ndarray:
    population = rng.normal(0.0, INIT_SIGMA, (size, genome_size))
    population[:, -1] += INIT_THROTTLE_BIAS  # last gene = throttle output bias (see network.unpack)
    return population


def next_population(
    rng: np.random.Generator, population: np.ndarray, fitness: np.ndarray
) -> np.ndarray:
    """Elitism + tournament selection + uniform crossover + gaussian mutation."""
    size, genes = population.shape
    order = np.argsort(-fitness, kind="stable")  # best first, lowest index wins ties
    children = [population[i].copy() for i in order[:ELITE]]
    while len(children) < size:
        a = _tournament(rng, fitness)
        b = _tournament(rng, fitness)
        mask = rng.random(genes) < 0.5
        child = np.where(mask, population[a], population[b])
        mutate = rng.random(genes) < MUTATION_RATE
        child = child + mutate * rng.normal(0.0, MUTATION_SIGMA, genes)
        children.append(child)
    return np.asarray(children)


def _tournament(rng: np.random.Generator, fitness: np.ndarray) -> int:
    picks = rng.integers(0, len(fitness), TOURNAMENT)
    return int(picks[np.argmax(fitness[picks])])
