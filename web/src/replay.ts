// Typed model of the replay file, following docs/replay-format.md. The viewer only reads this file.
import {
  asArray,
  asBoolean,
  asInteger,
  asNumber,
  asNumberArray,
  asRecord,
  asString,
  fail,
} from "./validate";

export type FramePose = [x: number, y: number, heading: number];

export interface Crash {
  x: number;
  y: number;
  frame: number;
}

export interface Car {
  frames: FramePose[];
  progress: number;
  crashed: boolean;
  crash: Crash | null;
  /** Best car only: per frame, 6 readings in 0..1 (1 = nothing within range), in sensorAngles order. */
  sensors?: number[][];
  /** Best car only: per frame, [steer, throttle]. */
  outputs?: number[][];
}

export interface Generation {
  index: number;
  bestProgress: number;
  completedLap: boolean;
  bestCarIndex: number;
  cars: Car[];
}

export interface ReplayMeta {
  seed: number;
  populationSize: number;
  generations: number;
  dt: number;
  frameStride: number;
  track: string;
  sensorAngles: number[];
  sensorMaxRange: number;
}

export interface Replay {
  meta: ReplayMeta;
  generations: Generation[];
}

const SENSOR_COUNT = 6;

function parseMeta(value: unknown): ReplayMeta {
  const m = asRecord(value, "meta");
  const sensorAngles = asNumberArray(m.sensorAngles, "meta.sensorAngles", SENSOR_COUNT);
  return {
    seed: asInteger(m.seed, "meta.seed"),
    populationSize: asInteger(m.populationSize, "meta.populationSize"),
    generations: asInteger(m.generations, "meta.generations"),
    dt: asNumber(m.dt, "meta.dt"),
    frameStride: asInteger(m.frameStride, "meta.frameStride"),
    track: asString(m.track, "meta.track"),
    sensorAngles,
    sensorMaxRange: asNumber(m.sensorMaxRange, "meta.sensorMaxRange"),
  };
}

function parseFrames(value: unknown, path: string): FramePose[] {
  return asArray(value, path).map((item, i) => {
    const [x, y, heading] = asNumberArray(item, `${path}[${i}]`, 3);
    return [x as number, y as number, heading as number];
  });
}

function parseCrash(value: unknown, path: string): Crash | null {
  if (value === null) return null;
  const c = asRecord(value, path);
  return {
    x: asNumber(c.x, `${path}.x`),
    y: asNumber(c.y, `${path}.y`),
    frame: asInteger(c.frame, `${path}.frame`),
  };
}

function parseCar(value: unknown, path: string): Car {
  const c = asRecord(value, path);
  const frames = parseFrames(c.frames, `${path}.frames`);
  if (frames.length === 0) fail(`${path}.frames`, "a non-empty array");
  const car: Car = {
    frames,
    progress: asNumber(c.progress, `${path}.progress`),
    crashed: asBoolean(c.crashed, `${path}.crashed`),
    crash: parseCrash(c.crash, `${path}.crash`),
  };
  if (car.crashed !== (car.crash !== null)) fail(`${path}.crash`, "null exactly when crashed is false");
  if (c.sensors !== undefined) {
    car.sensors = asArray(c.sensors, `${path}.sensors`).map((row, i) =>
      asNumberArray(row, `${path}.sensors[${i}]`, SENSOR_COUNT),
    );
    if (car.sensors.length !== frames.length) fail(`${path}.sensors`, "one row per frame");
  }
  if (c.outputs !== undefined) {
    car.outputs = asArray(c.outputs, `${path}.outputs`).map((row, i) =>
      asNumberArray(row, `${path}.outputs[${i}]`, 2),
    );
    if (car.outputs.length !== frames.length) fail(`${path}.outputs`, "one row per frame");
  }
  return car;
}

function parseGeneration(value: unknown, path: string, populationSize: number): Generation {
  const g = asRecord(value, path);
  const cars = asArray(g.cars, `${path}.cars`).map((car, i) =>
    parseCar(car, `${path}.cars[${i}]`),
  );
  if (cars.length !== populationSize) fail(`${path}.cars`, `${populationSize} cars (meta.populationSize)`);
  const bestCarIndex = asInteger(g.bestCarIndex, `${path}.bestCarIndex`);
  if (bestCarIndex < 0 || bestCarIndex >= cars.length) fail(`${path}.bestCarIndex`, "an index into cars");
  return {
    index: asInteger(g.index, `${path}.index`),
    bestProgress: asNumber(g.bestProgress, `${path}.bestProgress`),
    completedLap: asBoolean(g.completedLap, `${path}.completedLap`),
    bestCarIndex,
    cars,
  };
}

/**
 * Checks a parsed replay.json and returns it typed. Throws ReplayFormatError with the path of the
 * first problem, e.g. "Invalid file: replay.generations must be an array".
 */
export function parseReplay(value: unknown): Replay {
  const r = asRecord(value, "replay");
  const meta = parseMeta(r.meta);
  const generations = asArray(r.generations, "replay.generations");
  if (generations.length === 0) fail("replay.generations", "a non-empty array");
  return {
    meta,
    generations: generations.map((g, i) => parseGeneration(g, `replay.generations[${i}]`, meta.populationSize)),
  };
}
