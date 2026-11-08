import { describe, expect, it } from "vitest";
import sample from "../../../fixtures/replay.sample.json";
import { buildScene, frameIndexAt, frameSeconds, loopSeconds, rayColor, HOLD_SECONDS, lapCompleteAt, FADE_SECONDS, CRASHED_ALPHA } from "../scene";
import { parseReplay } from "../replay";

describe("playback timing", () => {
  it("picks the stored frame at or before a simulated time, clamped to the last frame", () => {
    expect(frameIndexAt(0, 0.2, 5)).toBe(0);
    expect(frameIndexAt(0.19, 0.2, 5)).toBe(0);
    expect(frameIndexAt(0.2, 0.2, 5)).toBe(1);
    expect(frameIndexAt(100, 0.2, 5)).toBe(4);
  });

  it("lets the longest car finish and then hold before looping", () => {
    const replay = parseReplay(sample);
    const generation = replay.generations[0];
    if (!generation) throw new Error("no generation");
    const longest = Math.max(...generation.cars.map((c) => c.frames.length));
    const secs = frameSeconds(replay);
    expect(loopSeconds(generation, secs)).toBeCloseTo((longest - 1) * secs + HOLD_SECONDS, 9);
  });
});

describe("rayColor", () => {
  it("is red when the sensor is near and green when it is far", () => {
    expect(rayColor(0)).toBe("rgb(255, 59, 59)");
    expect(rayColor(1)).toBe("rgb(59, 255, 106)");
  });

  it("clamps readings outside 0..1", () => {
    expect(rayColor(-3)).toBe(rayColor(0));
    expect(rayColor(7)).toBe(rayColor(1));
  });
});

describe("buildScene", () => {
  it("draws every car and six rays for the best car, each as long as its reading", () => {
    const replay = parseReplay(sample);
    const generation = replay.generations[0];
    if (!generation) throw new Error("no generation");
    const secs = frameSeconds(replay);
    const simTime = 0.5;
    const scene = buildScene(replay, generation, simTime, secs);

    expect(scene.cars).toHaveLength(generation.cars.length);
    expect(scene.cars.filter((c) => c.best)).toHaveLength(1);
    expect(scene.rays).toHaveLength(6);

    const best = generation.cars[generation.bestCarIndex];
    const index = frameIndexAt(simTime, secs, best?.frames.length ?? 0);
    const readings = best?.sensors?.[index] ?? [];
    scene.rays.forEach((ray, k) => {
      const length = Math.hypot(ray.to.x - ray.from.x, ray.to.y - ray.from.y);
      expect(length).toBeCloseTo((readings[k] ?? NaN) * replay.meta.sensorMaxRange, 6);
    });
  });
});

describe("buildScene extras", () => {
  const replay = parseReplay(sample);
  const secs = frameSeconds(replay);

  it("shows a crash mark only once the car has reached its crash frame, and fades the car", () => {
    const generation = replay.generations[0];
    if (!generation) throw new Error("no generation");
    const car = generation.cars.find((c) => c.crash && c.crash.frame > 0);
    if (!car?.crash) throw new Error("sample needs a crashed car");
    const before = buildScene(replay, generation, (car.crash.frame - 1) * secs, secs);
    const at = buildScene(replay, generation, car.crash.frame * secs, secs);
    const later = buildScene(replay, generation, car.crash.frame * secs + FADE_SECONDS * 3, secs);
    const marks = (s: typeof at) => s.crashes.filter((m) => m.x === car.crash?.x && m.y === car.crash?.y);
    expect(marks(before)).toHaveLength(0);
    expect(marks(at)).toHaveLength(1);
    expect(later.cars.filter((c) => c.crashed && !c.best).every((c) => c.alpha === CRASHED_ALPHA)).toBe(true);
    expect(at.cars.filter((c) => !c.crashed).every((c) => c.alpha === 1)).toBe(true);
  });

  it("limits the best-car trail to the frames reached so far", () => {
    const generation = replay.generations[0];
    if (!generation) throw new Error("no generation");
    expect(buildScene(replay, generation, 0, secs).trail.count).toBe(1);
    expect(buildScene(replay, generation, 3 * secs, secs).trail.count).toBe(4);
  });

  it("flags lap completion only after the finishing car reaches its last frame", () => {
    const done = replay.generations.find((g) => g.completedLap);
    const notDone = replay.generations.find((g) => !g.completedLap);
    if (!done || !notDone) throw new Error("sample needs both kinds of generation");
    const finisher = done.cars.find((c) => c.progress >= 1);
    const lastFrame = (finisher?.frames.length ?? 1) - 1;
    expect(lapCompleteAt(done, (lastFrame - 1) * secs, secs)).toBe(false);
    expect(lapCompleteAt(done, lastFrame * secs, secs)).toBe(true);
    expect(lapCompleteAt(notDone, 1e6, secs)).toBe(false);
  });
});
