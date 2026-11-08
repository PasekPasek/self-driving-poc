import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { prepareData } from "./prepare-data.mjs";

function fakeRepo() {
  const repo = mkdtempSync(join(tmpdir(), "prepare-data-"));
  mkdirSync(join(repo, "shared"));
  mkdirSync(join(repo, "fixtures"));
  writeFileSync(join(repo, "shared/track.json"), '{"track":"new"}');
  writeFileSync(join(repo, "fixtures/replay.sample.json"), '{"sample":true}');
  return { repo, publicDir: join(repo, "web-public") };
}

describe("prepareData", () => {
  it("seeds replay.json from the sample when there is none", () => {
    const { repo, publicDir } = fakeRepo();
    expect(prepareData({ repoDir: repo, publicDir })).toBe("sample");
    expect(readFileSync(join(publicDir, "replay.json"), "utf8")).toBe('{"sample":true}');
    expect(readFileSync(join(publicDir, "track.json"), "utf8")).toBe('{"track":"new"}');
  });

  it("never overwrites an existing real replay, but still refreshes track.json", () => {
    const { repo, publicDir } = fakeRepo();
    mkdirSync(publicDir);
    writeFileSync(join(publicDir, "replay.json"), '{"real":"training run"}');
    writeFileSync(join(publicDir, "track.json"), '{"track":"old"}');
    expect(prepareData({ repoDir: repo, publicDir })).toBe("kept");
    expect(readFileSync(join(publicDir, "replay.json"), "utf8")).toBe('{"real":"training run"}');
    expect(readFileSync(join(publicDir, "track.json"), "utf8")).toBe('{"track":"new"}');
  });
});
