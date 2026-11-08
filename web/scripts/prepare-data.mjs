// Copies the shared track into web/public/ so the viewer can fetch it, and seeds web/public/replay.json
// with the sample replay only when there is none yet. A real training run (committed, or written by
// `make train`) is never overwritten. web/public/track.json and replay.json are generated: never edit them by hand.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");

/** Returns "kept" when web/public/replay.json already exists, otherwise "sample". */
export function prepareData({ repoDir = resolve(webDir, ".."), publicDir = resolve(webDir, "public") } = {}) {
  mkdirSync(publicDir, { recursive: true });
  copyFileSync(resolve(repoDir, "shared/track.json"), resolve(publicDir, "track.json"));
  const replay = resolve(publicDir, "replay.json");
  if (existsSync(replay)) return "kept";
  copyFileSync(resolve(repoDir, "fixtures/replay.sample.json"), replay);
  return "sample";
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const replay = prepareData();
  console.log(
    replay === "kept"
      ? "prepare-data: copied shared/track.json to web/public/; kept existing web/public/replay.json"
      : "prepare-data: copied shared/track.json and fixtures/replay.sample.json to web/public/",
  );
}
