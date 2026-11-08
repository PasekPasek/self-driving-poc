import { describe, expect, it } from "vitest";
import sample from "../../../fixtures/replay.sample.json";
import { buildScene, frameIndexAt, frameSeconds, loopSeconds, rayColor, simTimeAt, HOLD_SECONDS, PLAYBACK_SPEED } from "../scene";
import { parseReplay } from "../replay";

describe("playback timing", () => {
  it("picks the stored frame at or before a simulated time, clamped to the last frame", () => {
    expect(frameIndexAt(0, 0.2, 5)).toBe(0);
    expect(frameIndexAt(0.19, 0.2, 5)).toBe(0);
    expect(frameIndexAt(0.2, 0.2, 5)).toBe(1);
    expect(frameIndexAt(100, 0.2, 5)).toBe(4);
  });

  it("wraps wall time into one loop at the playback speed", () => {
    const loop = 10;
    expect(simTimeAt(0, loop)).toBe(0);
    expect(simTimeAt(1, loop)).toBe(PLAYBACK_SPEED);
    expect(simTimeAt(5.5, loop)).toBeCloseTo((5.5 * PLAYBACK_SPEED) % loop, 9);
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
