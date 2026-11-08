// Pure counters for the side panel.
import type { Replay } from "./replay";

export interface Stats {
  /** 1-based generation number shown to the viewer. */
  generationNumber: number;
  totalGenerations: number;
  /** Cars run so far, including every car of the current generation (they all start together). */
  attempts: number;
  bestThisGeneration: number;
  bestOverall: number;
  /** Best progress of generations 0..generation, for the chart. */
  series: number[];
}

export function statsAt(replay: Replay, generation: number): Stats {
  const upTo = replay.generations.slice(0, generation + 1);
  const series = upTo.map((g) => g.bestProgress);
  return {
    generationNumber: generation + 1,
    totalGenerations: replay.generations.length,
    attempts: upTo.reduce((sum, g) => sum + g.cars.length, 0),
    bestThisGeneration: series[generation] ?? 0,
    bestOverall: Math.max(0, ...series),
    series,
  };
}
