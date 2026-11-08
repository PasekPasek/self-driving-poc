// Pure playback logic: which frame each car shows at a given simulated time, and where its sensor rays point.
import { rayEnd } from "./geometry";
import type { Car, Generation, Replay } from "./replay";
import type { Point, Pose } from "./track";

/** Simulated seconds that pass per real second. */
export const PLAYBACK_SPEED = 2;
/** Simulated seconds the finished replay holds before it starts again. */
export const HOLD_SECONDS = 2;

export interface CarView {
  pose: Pose;
  best: boolean;
}

export interface RayView {
  from: Point;
  to: Point;
  color: string;
}

export interface SceneView {
  cars: CarView[];
  rays: RayView[];
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

/** Simulated time reached after `wallSeconds` of real time, wrapped into one loop. */
export function simTimeAt(wallSeconds: number, loopSecs: number): number {
  return (wallSeconds * PLAYBACK_SPEED) % loopSecs;
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

/** Everything the renderer needs for one moment of generation `generation`. */
export function buildScene(replay: Replay, generation: Generation, simTime: number, frameSecs: number): SceneView {
  const cars: CarView[] = generation.cars.map((car, carIndex) => {
    const index = frameIndexAt(simTime, frameSecs, car.frames.length);
    return { pose: poseAt(car, index), best: carIndex === generation.bestCarIndex };
  });

  const rays: RayView[] = [];
  const best = generation.cars[generation.bestCarIndex];
  const bestView = cars.find((c) => c.best);
  if (best?.sensors && bestView) {
    const index = frameIndexAt(simTime, frameSecs, best.frames.length);
    const readings = best.sensors[index];
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
    }
  }
  return { cars, rays };
}
