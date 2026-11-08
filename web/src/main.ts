import { buildHistory, type History } from "./history";
import { fetchJson } from "./load";
import { Panel } from "./panel";
import {
  advance,
  buildTimeline,
  createPlayback,
  SPEEDS,
  setGeneration,
  setSpeed,
  stepGeneration,
  togglePause,
  type Playback,
  type Timeline,
} from "./playback";
import { parseReplay, type Replay } from "./replay";
import { Stage } from "./render";
import { buildScene, frameSeconds } from "./scene";
import { statsAt } from "./stats";
import { parseTrack } from "./track";

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`missing #${id}`);
  return found as T;
}

function setStatus(text: string): void {
  el("status").textContent = text;
}

/** Wires the controls; returns a function that syncs their look with the playback state (writes only on change). */
function bindControls(replay: Replay, timeline: Timeline, get: () => Playback, set: (p: Playback) => void): () => void {
  const speeds = el("speeds");
  const speedButtons = SPEEDS.map((speed) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `x${speed}`;
    button.addEventListener("click", () => set(setSpeed(get(), speed)));
    speeds.append(button);
    return { speed, button };
  });
  const slider = el<HTMLInputElement>("slider");
  slider.max = String(replay.generations.length - 1);

  el("prev").addEventListener("click", () => set(stepGeneration(get(), -1, timeline)));
  el("next").addEventListener("click", () => set(stepGeneration(get(), 1, timeline)));
  el("play").addEventListener("click", () => set(togglePause(get(), timeline)));
  slider.addEventListener("input", () => set(setGeneration(get(), Number(slider.value), timeline)));

  window.addEventListener("keydown", (event) => {
    const target = event.target instanceof HTMLElement ? event.target.tagName : "";
    if (target === "INPUT") return; // the slider handles its own arrows
    if (event.key === " " && target !== "BUTTON") {
      event.preventDefault();
      set(togglePause(get(), timeline));
    } else if (event.key === "ArrowLeft") set(stepGeneration(get(), -1, timeline));
    else if (event.key === "ArrowRight") set(stepGeneration(get(), 1, timeline));
  });

  let shown = "";
  return () => {
    const state = get();
    const key = `${state.speed}|${state.paused}|${state.generation}`;
    if (key === shown) return;
    shown = key;
    speedButtons.forEach(({ speed, button }) => button.setAttribute("aria-pressed", String(speed === state.speed)));
    const play = el("play");
    play.textContent = state.paused ? "▶" : "⏸";
    play.setAttribute("aria-label", state.paused ? "Play" : "Pause");
    slider.value = String(state.generation);
  };
}

async function main(): Promise<void> {
  const canvas = el<HTMLCanvasElement>("stage");
  try {
    const track = parseTrack(await fetchJson("track.json"));
    const replay = parseReplay(await fetchJson("replay.json"));
    const frameSecs = frameSeconds(replay);
    const timeline = buildTimeline(replay, frameSecs);
    const stage = new Stage(canvas, track);
    const panel = new Panel();
    const banner = el("banner");
    window.addEventListener("resize", () => stage.resize());

    let state = createPlayback();
    const syncControls = bindControls(replay, timeline, () => state, (next) => (state = next));

    let history: History = buildHistory(replay, state.generation);
    let shownStats = -1;
    let last: number | null = null;

    const tick = (now: number): void => {
      const dt = last === null ? 0 : Math.min((now - last) / 1000, 0.1);
      last = now;
      state = advance(state, dt, timeline);
      const generation = replay.generations[state.generation];
      if (!generation) throw new Error(`generation ${state.generation} missing`);
      if (history.generation !== state.generation) history = buildHistory(replay, state.generation);
      if (shownStats !== state.generation) {
        shownStats = state.generation;
        panel.updateStats(statsAt(replay, state.generation));
        setStatus(`${track.name} · generation ${generation.index + 1} of ${replay.generations.length}`);
      }
      const scene = buildScene(replay, generation, state.time, frameSecs);
      stage.draw(scene, history);
      panel.updateScene(scene);
      banner.hidden = !scene.lapComplete;
      if (scene.lapComplete) banner.textContent = `LAP COMPLETE — generation ${generation.index + 1}`;
      syncControls();
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error));
  }
}

void main();
