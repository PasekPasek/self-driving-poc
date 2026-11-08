// Pure data for what earlier generations leave on the track: crash marks and best-car trails, older = fainter.
import type { FramePose, Replay } from "./replay";

export interface CrashMark {
  x: number;
  y: number;
  alpha: number;
}

export interface TrailLine {
  frames: FramePose[];
  alpha: number;
}

export interface History {
  generation: number;
  crashes: CrashMark[];
  trails: TrailLine[];
}

/** Opacity of a mark `age` generations old (age 1 = the previous generation): decays geometrically down to a floor. */
export function fadeAlpha(age: number, start: number, decay: number, floor: number): number {
  return Math.max(floor, start * decay ** (age - 1));
}

export const crashAlpha = (age: number): number => fadeAlpha(age, 0.75, 0.93, 0.15);
export const trailAlpha = (age: number): number => fadeAlpha(age, 0.5, 0.9, 0.07);

/** Crash marks and best trails of every generation before `generation`. */
export function buildHistory(replay: Replay, generation: number): History {
  const crashes: CrashMark[] = [];
  const trails: TrailLine[] = [];
  for (const past of replay.generations.slice(0, generation)) {
    const age = generation - past.index;
    for (const car of past.cars) {
      if (car.crash) crashes.push({ x: car.crash.x, y: car.crash.y, alpha: crashAlpha(age) });
    }
    const best = past.cars[past.bestCarIndex];
    if (best) trails.push({ frames: best.frames, alpha: trailAlpha(age) });
  }
  return { generation, crashes, trails };
}
