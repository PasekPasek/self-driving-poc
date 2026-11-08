import { parseReplay, type Generation, type Replay } from "./replay";
import { fetchJson } from "./load";
import { Stage } from "./render";
import { buildScene, frameSeconds, loopSeconds, simTimeAt } from "./scene";
import { parseTrack, type Track } from "./track";

const SHOWN_GENERATION = 0;

function setStatus(text: string): void {
  const status = document.getElementById("status");
  if (status) status.textContent = text;
}

function pickGeneration(replay: Replay): Generation {
  const generation = replay.generations[SHOWN_GENERATION];
  if (!generation) throw new Error(`replay has no generation ${SHOWN_GENERATION}`);
  return generation;
}

function startLoop(stage: Stage, replay: Replay, generation: Generation, track: Track): void {
  const frameSecs = frameSeconds(replay);
  const loop = loopSeconds(generation, frameSecs);
  let startedAt: number | null = null;

  const tick = (now: number): void => {
    if (startedAt === null) startedAt = now;
    const simTime = simTimeAt((now - startedAt) / 1000, loop);
    stage.draw(buildScene(replay, generation, simTime, frameSecs));
    setStatus(
      `${track.name} · generation ${generation.index} · best progress ${Math.round(generation.bestProgress * 100)}%` +
        (generation.completedLap ? " · lap completed" : ""),
    );
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

async function main(): Promise<void> {
  const canvas = document.getElementById("stage");
  if (!(canvas instanceof HTMLCanvasElement)) throw new Error("missing #stage canvas");
  try {
    const track = parseTrack(await fetchJson("track.json"));
    const replay = parseReplay(await fetchJson("replay.json"));
    const generation = pickGeneration(replay);
    const stage = new Stage(canvas, track);
    window.addEventListener("resize", () => stage.resize());
    startLoop(stage, replay, generation, track);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error));
  }
}

void main();
