import { describe, expect, it } from "vitest";
import sample from "../../../fixtures/replay.sample.json";
import { buildHistory, crashAlpha, trailAlpha } from "../history";
import { advance, buildTimeline, createPlayback, isFinished, setGeneration, setSpeed, stepGeneration, togglePause } from "../playback";
import { parseReplay } from "../replay";
import { frameSeconds, PLAYBACK_SPEED } from "../scene";
import { statsAt } from "../stats";

const replay = parseReplay(sample);
const timeline = buildTimeline(replay, frameSeconds(replay));

describe("playback state", () => {
  it("advances time by wall time x speed x base rate", () => {
    const s = advance(setSpeed(createPlayback(), 4), 0.1, timeline);
    expect(s.time).toBeCloseTo(0.1 * 4 * PLAYBACK_SPEED, 9);
    expect(s.generation).toBe(0);
  });

  it("does not move while paused", () => {
    const paused = togglePause(createPlayback(), timeline);
    expect(paused.paused).toBe(true);
    expect(advance(paused, 5, timeline)).toBe(paused);
  });

  it("rolls into the next generation at the end of a loop and stops after the last", () => {
    const first = timeline.loops[0] ?? 0;
    const next = advance(createPlayback(), first / PLAYBACK_SPEED + 0.01, timeline);
    expect(next.generation).toBe(1);
    expect(next.time).toBe(0);

    const last = setGeneration(createPlayback(), 99, timeline);
    expect(last.generation).toBe(replay.generations.length - 1);
    const end = advance(last, 1000, timeline);
    expect(isFinished(end, timeline)).toBe(true);
    expect(end.paused).toBe(true);
    expect(togglePause(end, timeline)).toMatchObject({ generation: 0, time: 0, paused: false });
  });

  it("switches generation from the start of that generation and clamps", () => {
    const mid = advance(createPlayback(), 0.3, timeline);
    expect(setGeneration(mid, 1, timeline)).toMatchObject({ generation: 1, time: 0 });
    expect(stepGeneration(createPlayback(), -1, timeline).generation).toBe(0);
    expect(stepGeneration(createPlayback(), 1, timeline).generation).toBe(1);
    expect(stepGeneration(setGeneration(createPlayback(), 1, timeline), 1, timeline).generation).toBe(1);
  });
});

describe("attempts counter", () => {
  it("counts every car of the shown generation and all earlier ones", () => {
    const pop = replay.meta.populationSize;
    expect(statsAt(replay, 0).attempts).toBe(pop);
    expect(statsAt(replay, 1).attempts).toBe(2 * pop);
  });

  it("tracks best progress this generation, overall, and the chart series", () => {
    const s = statsAt(replay, 1);
    expect(s.generationNumber).toBe(2);
    expect(s.bestThisGeneration).toBe(replay.generations[1]?.bestProgress);
    expect(s.bestOverall).toBe(Math.max(...replay.generations.map((g) => g.bestProgress)));
    expect(s.series).toHaveLength(2);
    expect(statsAt(replay, 0).series).toHaveLength(1);
  });
});

describe("history: what earlier generations leave on the track", () => {
  it("has nothing at generation 0", () => {
    const h = buildHistory(replay, 0);
    expect(h.crashes).toHaveLength(0);
    expect(h.trails).toHaveLength(0);
  });

  it("shows exactly the crashes and best trails of generations before N, older fainter", () => {
    const h = buildHistory(replay, 1);
    const crashed = replay.generations[0]?.cars.filter((c) => c.crashed).length;
    expect(h.crashes).toHaveLength(crashed ?? -1);
    expect(h.trails).toHaveLength(1);
    expect(h.trails[0]?.alpha).toBe(trailAlpha(1));
  });

  it("fades with age but never disappears", () => {
    expect(crashAlpha(2)).toBeLessThan(crashAlpha(1));
    expect(trailAlpha(5)).toBeLessThan(trailAlpha(2));
    expect(crashAlpha(1000)).toBeGreaterThan(0);
    expect(trailAlpha(1000)).toBeGreaterThan(0);
  });
});
