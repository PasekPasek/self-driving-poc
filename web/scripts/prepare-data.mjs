// Copies the shared track and the sample replay into web/public/ so the viewer can fetch them.
// web/public/track.json and web/public/replay.json are generated: never edit them by hand.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoDir = resolve(webDir, "..");
const publicDir = resolve(webDir, "public");

mkdirSync(publicDir, { recursive: true });
copyFileSync(resolve(repoDir, "shared/track.json"), resolve(publicDir, "track.json"));
copyFileSync(resolve(repoDir, "fixtures/replay.sample.json"), resolve(publicDir, "replay.json"));
console.log("prepare-data: copied shared/track.json and fixtures/replay.sample.json to web/public/");
