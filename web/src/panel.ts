// DOM side panel: counters, sensor bars, gauges, chart. Reads a SceneView/Stats, holds no playback logic.
import type { SceneView } from "./scene";
import type { Stats } from "./stats";

function el<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`missing #${id}`);
  return found as T;
}

const pct = (v: number): string => `${Math.round(v * 100)}%`;

export class Panel {
  private readonly bars: HTMLElement[] = [];
  private readonly chart = el<HTMLCanvasElement>("chart");
  private readonly text = new Map<string, string>();

  constructor() {
    const sensors = el("sensors");
    for (let i = 0; i < 6; i++) {
      const bar = document.createElement("div");
      bar.className = "bar";
      const fill = document.createElement("i");
      bar.append(fill);
      sensors.append(bar);
      this.bars.push(fill);
    }
  }

  /** Sets text only when it changed, so per-frame updates do not touch the DOM needlessly. */
  private setText(id: string, value: string): void {
    if (this.text.get(id) === value) return;
    this.text.set(id, value);
    el(id).textContent = value;
  }

  updateStats(stats: Stats): void {
    this.setText("gen-title", `Generation ${stats.generationNumber} / ${stats.totalGenerations}`);
    this.setText("attempts", String(stats.attempts));
    this.setText("best-gen", pct(stats.bestThisGeneration));
    this.setText("best-all", pct(stats.bestOverall));
    this.drawChart(stats);
  }

  updateScene(scene: SceneView): void {
    const readout = scene.readout;
    this.bars.forEach((fill, i) => {
      const reading = readout?.sensors[i] ?? 0;
      fill.style.height = `${Math.round(reading * 100)}%`;
    });
    this.setGauge("steer-fill", readout?.steer ?? 0);
    this.setGauge("throttle-fill", readout?.throttle ?? 0);
  }

  /** Centered gauge: value -1..1 fills left or right of the middle. */
  private setGauge(id: string, value: number): void {
    const fill = el(id);
    const v = Math.max(-1, Math.min(1, value));
    fill.style.left = v < 0 ? `${50 + v * 50}%` : "50%";
    fill.style.width = `${Math.abs(v) * 50}%`;
  }

  private drawChart(stats: Stats): void {
    const ctx = this.chart.getContext("2d");
    if (!ctx) return;
    const { width, height } = this.chart;
    const pad = 8;
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = "#262b36";
    ctx.lineWidth = 1;
    ctx.strokeRect(pad, pad, width - 2 * pad, height - 2 * pad);
    const n = stats.totalGenerations;
    const x = (i: number): number => pad + (n <= 1 ? 0 : (i / (n - 1)) * (width - 2 * pad));
    const y = (v: number): number => height - pad - Math.max(0, Math.min(1, v)) * (height - 2 * pad);
    ctx.strokeStyle = "#ffd166";
    ctx.lineWidth = 2;
    ctx.beginPath();
    stats.series.forEach((v, i) => (i === 0 ? ctx.moveTo(x(i), y(v)) : ctx.lineTo(x(i), y(v))));
    ctx.stroke();
    const last = stats.series.length - 1;
    ctx.fillStyle = "#ffd166";
    ctx.beginPath();
    ctx.arc(x(last), y(stats.series[last] ?? 0), 3.5, 0, Math.PI * 2);
    ctx.fill();
  }
}
