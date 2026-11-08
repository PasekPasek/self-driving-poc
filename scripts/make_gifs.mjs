// Records docs/media/lap.gif and docs/media/learning.gif from the real replay in web/public/replay.json.
// It serves the built viewer (web/dist) on a free port, drives it in headless Chrome with a virtual clock
// (requestAnimationFrame is replaced, so every run captures the same frames), and hands the PNG frames to
// scripts/make_gif.py. Run it through `make media`; it needs web/node_modules, a built web/dist,
// google-chrome (or CHROME_PATH) and Python 3 with Pillow.
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, existsSync, rmSync } from "node:fs";
import { createServer } from "node:http";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = resolve(root, "web/dist");
const outDir = resolve(root, "docs/media");
const { chromium } = createRequire(resolve(root, "web/package.json"))("playwright-core");

const FPS = 12;
const STEP_MS = 1000 / FPS; // virtual wall time per captured frame
const VIEWPORT = { width: 1280, height: 680 };
const LAP_GENERATION = 15; // 0-based: generation 16 in the viewer, the first lap of the committed run
const LEARNING = [0, 3, 7, 11, 15]; // viewer generations 1, 4, 8, 12, 16
const LEARNING_SPEED = 8;
const LEARNING_CLIP_FRAMES = 36; // 3 s of GIF per generation
const LAP_SPEED = 4;
const BANNER_HOLD_FRAMES = 24;
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };

if (!existsSync(join(dist, "index.html"))) throw new Error("web/dist is missing: run `npm run build` in web/ first");

const server = createServer((req, res) => {
  const path = new URL(req.url, "http://x").pathname;
  const file = resolve(dist, "." + (path === "/" ? "/index.html" : path));
  if (!file.startsWith(dist) || !existsSync(file)) {
    res.writeHead(404).end();
    return;
  }
  res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" }).end(readFileSync(file));
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const url = `http://127.0.0.1:${server.address().port}/`;

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH ?? "/usr/bin/google-chrome",
  args: ["--no-sandbox"],
});
const page = await browser.newPage({ viewport: VIEWPORT });
await page.addInitScript(() => {
  let queue = [];
  let now = 0;
  window.requestAnimationFrame = (callback) => (queue.push(callback), queue.length);
  window.__step = (ms) => {
    now += ms;
    const run = queue;
    queue = [];
    run.forEach((callback) => callback(now));
  };
});

const step = () => page.evaluate((ms) => window.__step(ms), STEP_MS);
const bannerShown = () => page.$eval("#banner", (el) => !el.hidden);

/** Opens the viewer at the start of `generation` (0-based), paused-free, at the given speed. */
async function open(generation, speed) {
  await page.goto(url);
  await page.waitForFunction(() => document.querySelectorAll("#speeds button").length > 0);
  await page.click(`#speeds button:text-is("x${speed}")`);
  await page.$eval("#slider", (el, value) => {
    el.value = String(value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }, generation);
  await step();
  await step(); // first tick has dt 0; this one draws generation `generation` at time 0
}

async function shot(dir, index) {
  await page.screenshot({ path: join(dir, `${String(index).padStart(4, "0")}.png`) });
}

function assemble(frames, out, extra = []) {
  execFileSync("python3", [resolve(root, "scripts/make_gif.py"), frames, out, "--fps", String(FPS), ...extra], { stdio: "inherit" });
}

mkdirSync(outDir, { recursive: true });
const work = mkdtempSync(join(tmpdir(), "make-gifs-"));
try {
  // lap.gif: the lap-complete generation, from the start line to the LAP COMPLETE banner.
  const lapDir = join(work, "lap");
  mkdirSync(lapDir);
  await open(LAP_GENERATION, LAP_SPEED);
  let n = 0;
  for (let guard = 0; guard < 600 && !(await bannerShown()); guard++) {
    await shot(lapDir, n++);
    await step();
  }
  if (!(await bannerShown())) throw new Error("the banner never appeared");
  await page.click("#play"); // pause on the banner, so the hold does not roll into the next generation
  for (let i = 0; i < BANNER_HOLD_FRAMES; i++) {
    await shot(lapDir, n++);
    await step();
  }
  assemble(lapDir, join(outDir, "lap.gif"), ["--hold-last", "1500"]);

  // learning.gif: the first seconds of a few generations, one after another.
  const learnDir = join(work, "learning");
  mkdirSync(learnDir);
  n = 0;
  for (const generation of LEARNING) {
    await open(generation, LEARNING_SPEED);
    for (let i = 0; i < LEARNING_CLIP_FRAMES; i++) {
      await shot(learnDir, n++);
      await step();
    }
  }
  assemble(learnDir, join(outDir, "learning.gif"), ["--hold-last", "1000"]);
} finally {
  rmSync(work, { recursive: true, force: true });
  await browser.close();
  server.close();
}
