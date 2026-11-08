import type { Point, Pose, Track } from "./track";

/**
 * Unit normal at centerline point i, pointing to the car's right-hand side on screen
 * (y axis down, so for a track driven towards +x the normal is +y).
 * Uses the neighbouring points, wrapping around the closed loop.
 */
export function rightNormal(centerline: readonly Point[], i: number): Point {
  const n = centerline.length;
  const prev = centerline[(i - 1 + n) % n];
  const next = centerline[(i + 1) % n];
  if (!prev || !next) throw new Error(`centerline index ${i} out of range`);
  const tx = next.x - prev.x;
  const ty = next.y - prev.y;
  const len = Math.hypot(tx, ty);
  if (len === 0) throw new Error(`degenerate centerline at index ${i}`);
  return { x: -ty / len, y: tx / len };
}

export interface Boundaries {
  left: Point[];
  right: Point[];
}

/** Track edges: centerline offset by ±width/2 along the normal. Both lists follow the centerline order. */
export function boundaries(track: Track): Boundaries {
  const half = track.width / 2;
  const left: Point[] = [];
  const right: Point[] = [];
  track.centerline.forEach((c, i) => {
    const normal = rightNormal(track.centerline, i);
    right.push({ x: c.x + normal.x * half, y: c.y + normal.y * half });
    left.push({ x: c.x - normal.x * half, y: c.y - normal.y * half });
  });
  return { left, right };
}

/** The start/finish line: a segment across the track at centerline[0]. */
export function startLine(track: Track): [Point, Point] {
  const c = track.centerline[0];
  if (!c) throw new Error("track has no centerline");
  const normal = rightNormal(track.centerline, 0);
  const half = track.width / 2;
  return [
    { x: c.x - normal.x * half, y: c.y - normal.y * half },
    { x: c.x + normal.x * half, y: c.y + normal.y * half },
  ];
}

/**
 * End point of a sensor ray. The ray leaves the car at `heading + angle` (radians, clockwise
 * positive on screen) and its length is `reading * maxRange` (reading 1 = nothing within range).
 */
export function rayEnd(pose: Pose, angle: number, reading: number, maxRange: number): Point {
  const length = reading * maxRange;
  const direction = pose.heading + angle;
  return { x: pose.x + Math.cos(direction) * length, y: pose.y + Math.sin(direction) * length };
}
