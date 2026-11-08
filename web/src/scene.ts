// Pure playback logic: which frame each car shows at a given simulated time, and where its sensor rays point.
import { rayEnd } from "./geometry";
import type { Car, FramePose, Generation, Replay } from "./replay";
import type { Point, Pose } from "./track";

/** Simulated seconds that pass per real second. */
export const PLAYBACK_SPEED = 2;
/** Simulated seconds the finished replay holds before it starts again. */
export const HOLD_SECONDS = 2;

/** Simulated seconds a crashed car takes to fade down to its resting opacity. */
export const FADE_SECONDS = 1.2;
export const CRASHED_ALPHA = 0.15;

export interface CarView {
  pose: Pose;
  best: boolean;
  crashed: boolean;
  alpha: number;
}

export interface RayView {
  from: Point;
  to: Point;
  color: string;
}

/** Best car's readings at the current frame; arrays are references into the replay, not copies. */
export interface Readout {
  sensors: readonly number[];
  steer: number;
  throttle: number;
}

export interface SceneView {
  cars: CarView[];
  rays: RayView[];
  /** Crash points of this generation that have already happened. */
  crashes: { x: number; y: number }[];
  /** Best car's path so far: the first `count` entries of `frames`. */
  trail: { frames: readonly FramePose[]; count: number };
  readout: Readout | null;
  lapComplete: boolean;
}

/** Seconds of simulated time between two stored frames. */
export function frameSeconds(replay: Replay): number {
  return replay.meta.frameStride * replay.meta.dt;
}

/** Simulated seconds for one full loop: the longest car, then a hold. */
export function loopSeconds(generation: Generation, frameSecs: number): number {
  const longest = Math.max(...generation.cars.map((car) => car.frames.length));
  return (longest - 1) * frameSecs + HOLD_SECONDS;
}

/** Index of the stored frame shown at simulated time `simTime`; a finished car keeps its last frame. */
export function frameIndexAt(simTime: number, frameSecs: number, frameCount: number): number {
  const index = Math.floor(simTime / frameSecs + 1e-9);
  return Math.max(0, Math.min(index, frameCount - 1));
}

/** Colour of a sensor ray: green when the reading is far (1), red when it is near (0). */
export function rayColor(reading: number): string {
  const t = Math.max(0, Math.min(1, reading));
  const red = [255, 59, 59];
  const green = [59, 255, 106];
  const channel = (i: number) => Math.round((red[i] ?? 0) + ((green[i] ?? 0) - (red[i] ?? 0)) * t);
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`;
}

function poseAt(car: Car, frameIndex: number): Pose {
  const frame = car.frames[frameIndex];
  if (!frame) throw new Error(`frame ${frameIndex} missing`);
  return { x: frame[0], y: frame[1], heading: frame[2] };
}

/** True once a car of a lap-completing generation has crossed the line by `simTime`. */
export function lapCompleteAt(generation: Generation, simTime: number, frameSecs: number): boolean {
  if (!generation.completedLap) return false;
  const finished = generation.cars.find((car) => car.progress >= 1);
  return finished !== undefined && frameIndexAt(simTime, frameSecs, finished.frames.length) >= finished.frames.length - 1;
}

/** Everything the renderer needs for one moment of generation `generation`. */
export function buildScene(replay: Replay, generation: Generation, simTime: number, frameSecs: number): SceneView {
  const crashes: { x: number; y: number }[] = [];
  const cars: CarView[] = generation.cars.map((car, carIndex) => {
    const index = frameIndexAt(simTime, frameSecs, car.frames.length);
    const best = carIndex === generation.bestCarIndex;
    const crashed = car.crash !== null && index >= car.crash.frame;
    if (crashed && car.crash) crashes.push({ x: car.crash.x, y: car.crash.y });
    const sinceCrash = crashed && car.crash ? simTime - car.crash.frame * frameSecs : 0;
    const alpha = crashed && !best ? Math.max(CRASHED_ALPHA, 1 - sinceCrash / FADE_SECONDS) : 1;
    return { pose: poseAt(car, index), best, crashed, alpha };
  });

  const rays: RayView[] = [];
  const best = generation.cars[generation.bestCarIndex];
  const bestView = cars.find((c) => c.best);
  let readout: Readout | null = null;
  let trailCount = 0;
  if (best && bestView) {
    const index = frameIndexAt(simTime, frameSecs, best.frames.length);
    trailCount = index + 1;
    const readings = best.sensors?.[index];
    const output = best.outputs?.[index];
    if (readings) {
      readings.forEach((reading, k) => {
        const angle = replay.meta.sensorAngles[k];
        if (angle === undefined) throw new Error(`sensor angle ${k} missing`);
        rays.push({
          from: { x: bestView.pose.x, y: bestView.pose.y },
          to: rayEnd(bestView.pose, angle, reading, replay.meta.sensorMaxRange),
          color: rayColor(reading),
        });
      });
      readout = { sensors: readings, steer: output?.[0] ?? 0, throttle: output?.[1] ?? 0 };
    }
  }
  return {
    cars,
    rays,
    crashes,
    trail: { frames: best?.frames ?? [], count: trailCount },
    readout,
    lapComplete: lapCompleteAt(generation, simTime, frameSecs),
  };
}
