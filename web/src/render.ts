// Canvas 2D drawing of the track and the scene. Drawing is not unit-tested; the logic it draws is.
import { boundaries, rightNormal, startLine, type Boundaries } from "./geometry";
import type { SceneView } from "./scene";
import type { Point, Track } from "./track";

const COLORS = {
  background: "#0b0d12",
  asphalt: "#2b2f38",
  edge: "rgba(230, 233, 240, 0.85)",
  startLine: "#f5f5f5",
  label: "rgba(216, 220, 230, 0.35)",
  car: "rgba(120, 170, 255, 0.55)",
  bestCar: "#ffd166",
};

const CAR_LENGTH = 14;
const CAR_WIDTH = 7;
const LABEL_OFFSET = 26;
const MARGIN = 0.94;

export class Stage {
  private readonly ctx: CanvasRenderingContext2D;
  private readonly edges: Boundaries;
  private readonly asphalt: Path2D;
  private readonly edgePath: Path2D;
  private readonly start: [Point, Point];
  private dpr = 1;
  private scale = 1;
  private offsetX = 0;
  private offsetY = 0;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly track: Track,
  ) {
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas 2D is not available in this browser");
    this.ctx = ctx;
    this.edges = boundaries(track);
    this.asphalt = loopsPath(this.edges.left, this.edges.right);
    this.edgePath = new Path2D();
    addLoop(this.edgePath, this.edges.left);
    addLoop(this.edgePath, this.edges.right);
    this.start = startLine(track);
    this.resize();
  }

  /** Matches the backing store to the window and recomputes the track fit (aspect ratio kept). */
  resize(): void {
    const cssWidth = this.canvas.clientWidth;
    const cssHeight = this.canvas.clientHeight;
    this.dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(cssWidth * this.dpr);
    this.canvas.height = Math.round(cssHeight * this.dpr);
    const { width, height } = this.track.box;
    this.scale = Math.min(cssWidth / width, cssHeight / height) * MARGIN;
    this.offsetX = (cssWidth - width * this.scale) / 2;
    this.offsetY = (cssHeight - height * this.scale) / 2;
  }

  draw(scene: SceneView): void {
    const ctx = this.ctx;
    const dpr = this.dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(dpr * this.scale, 0, 0, dpr * this.scale, dpr * this.offsetX, dpr * this.offsetY);

    ctx.fillStyle = COLORS.asphalt;
    ctx.fill(this.asphalt, "evenodd");
    ctx.strokeStyle = COLORS.edge;
    ctx.lineWidth = 2.5;
    ctx.stroke(this.edgePath);

    this.drawLabels();
    this.drawStartLine();
    this.drawRays(scene);
    this.drawCars(scene);
  }

  private drawLabels(): void {
    const ctx = this.ctx;
    const { centerline, sections, width } = this.track;
    ctx.fillStyle = COLORS.label;
    ctx.font = "13px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const section of sections) {
      const mid = Math.floor((section.fromIndex + section.toIndex) / 2);
      const c = centerline[mid];
      if (!c) continue;
      const n = rightNormal(centerline, mid);
      const d = width / 2 + LABEL_OFFSET;
      ctx.fillText(section.name, c.x + n.x * d, c.y + n.y * d);
    }
  }

  private drawStartLine(): void {
    const ctx = this.ctx;
    const [a, b] = this.start;
    ctx.strokeStyle = COLORS.startLine;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  private drawRays(scene: SceneView): void {
    const ctx = this.ctx;
    ctx.lineWidth = 1.5;
    for (const ray of scene.rays) {
      ctx.strokeStyle = ray.color;
      ctx.beginPath();
      ctx.moveTo(ray.from.x, ray.from.y);
      ctx.lineTo(ray.to.x, ray.to.y);
      ctx.stroke();
      ctx.fillStyle = ray.color;
      ctx.beginPath();
      ctx.arc(ray.to.x, ray.to.y, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  private drawCars(scene: SceneView): void {
    const ctx = this.ctx;
    // Draw the best car last so it sits on top of the others.
    const ordered = [...scene.cars].sort((a, b) => Number(a.best) - Number(b.best));
    for (const car of ordered) {
      ctx.save();
      ctx.translate(car.pose.x, car.pose.y);
      ctx.rotate(car.pose.heading);
      ctx.fillStyle = car.best ? COLORS.bestCar : COLORS.car;
      if (car.best) {
        ctx.shadowColor = COLORS.bestCar;
        ctx.shadowBlur = 8 * this.dpr;
      }
      ctx.fillRect(-CAR_LENGTH / 2, -CAR_WIDTH / 2, CAR_LENGTH, CAR_WIDTH);
      ctx.restore();
    }
  }
}

function addLoop(path: Path2D, points: readonly Point[]): void {
  points.forEach((p, i) => (i === 0 ? path.moveTo(p.x, p.y) : path.lineTo(p.x, p.y)));
  path.closePath();
}

function loopsPath(a: readonly Point[], b: readonly Point[]): Path2D {
  const path = new Path2D();
  addLoop(path, a);
  addLoop(path, b);
  return path;
}
