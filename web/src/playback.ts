// Pure playback state: which generation is shown, how far into it, how fast. Controls drive it, the loop advances it.
import { loopSeconds, PLAYBACK_SPEED } from "./scene";
import type { Replay } from "./replay";

export const SPEEDS = [1, 2, 4, 8] as const;

export interface Playback {
  generation: number;
  /** Simulated seconds since the generation started. */
  time: number;
  speed: number;
  paused: boolean;
}

/** Per-replay constants the playback needs; built once. */
export interface Timeline {
  frameSecs: number;
  /** Simulated seconds each generation plays for, including the final hold. */
  loops: number[];
}

export function buildTimeline(replay: Replay, frameSecs: number): Timeline {
  return { frameSecs, loops: replay.generations.map((g) => loopSeconds(g, frameSecs)) };
}

export function createPlayback(): Playback {
  return { generation: 0, time: 0, speed: 1, paused: false };
}

function lastGeneration(timeline: Timeline): number {
  return timeline.loops.length - 1;
}

function loopOf(timeline: Timeline, generation: number): number {
  const loop = timeline.loops[generation];
  if (loop === undefined) throw new Error(`generation ${generation} missing`);
  return loop;
}

/** True when the last generation has played to its end. */
export function isFinished(state: Playback, timeline: Timeline): boolean {
  return state.generation === lastGeneration(timeline) && state.time >= loopOf(timeline, state.generation);
}

/** Moves time forward by `wallSeconds` of real time; rolls into the next generation, stops after the last. */
export function advance(state: Playback, wallSeconds: number, timeline: Timeline): Playback {
  if (state.paused || isFinished(state, timeline)) return state;
  const time = state.time + wallSeconds * state.speed * PLAYBACK_SPEED;
  const loop = loopOf(timeline, state.generation);
  if (time < loop) return { ...state, time };
  if (state.generation < lastGeneration(timeline)) return { ...state, generation: state.generation + 1, time: 0 };
  return { ...state, time: loop, paused: true };
}

/** Jumps to the start of generation `generation` (clamped into range). */
export function setGeneration(state: Playback, generation: number, timeline: Timeline): Playback {
  const clamped = Math.max(0, Math.min(Math.round(generation), lastGeneration(timeline)));
  return { ...state, generation: clamped, time: 0 };
}

export function stepGeneration(state: Playback, delta: number, timeline: Timeline): Playback {
  return setGeneration(state, state.generation + delta, timeline);
}

/** Play/pause; pressing play on a finished run restarts it from generation 0. */
export function togglePause(state: Playback, timeline: Timeline): Playback {
  if (state.paused && isFinished(state, timeline)) return { ...state, generation: 0, time: 0, paused: false };
  return { ...state, paused: !state.paused };
}

export function setSpeed(state: Playback, speed: number): Playback {
  return { ...state, speed };
}
