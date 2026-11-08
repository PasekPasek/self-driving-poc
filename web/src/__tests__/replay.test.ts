import { describe, expect, it } from "vitest";
import sample from "../../../fixtures/replay.sample.json";
import { parseReplay } from "../replay";
import { ReplayFormatError } from "../validate";

describe("parseReplay", () => {
  it("accepts the sample replay", () => {
    const replay = parseReplay(sample);
    expect(replay.meta.populationSize).toBe(3);
    expect(replay.generations).toHaveLength(2);
    expect(replay.generations[0]?.cars).toHaveLength(3);
    expect(replay.generations[0]?.cars[1]?.sensors?.[0]).toHaveLength(6);
  });

  it("rejects a file without generations", () => {
    const { generations: _omitted, ...withoutGenerations } = sample;
    expect(() => parseReplay(withoutGenerations)).toThrow(ReplayFormatError);
    expect(() => parseReplay(withoutGenerations)).toThrow(/replay\.generations must be/);
  });

  it("rejects a car whose crash and crashed flag disagree", () => {
    const broken = structuredClone(sample);
    const car = broken.generations[0]?.cars[0];
    if (!car) throw new Error("sample has no car");
    car.crash = null;
    expect(() => parseReplay(broken)).toThrow(/crash must be null exactly when crashed is false/);
  });
});
