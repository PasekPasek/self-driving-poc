import { describe, expect, it } from "vitest";
import trackJson from "../../../shared/track.json";
import { boundaries, rayEnd, rightNormal, startLine } from "../geometry";
import { parseTrack, type Track } from "../track";

const EPS = 1e-9;

/** A circle of radius 100 centred on the origin, 360 points, driven with increasing angle. */
function circleTrack(): Track {
  const centerline = Array.from({ length: 360 }, (_, i) => {
    const t = (i / 360) * 2 * Math.PI;
    return { x: 100 * Math.cos(t), y: 100 * Math.sin(t) };
  });
  return {
    name: "circle",
    width: 20,
    box: { width: 1000, height: 650 },
    start: { x: 100, y: 0, heading: Math.PI / 2 },
    centerline,
    sections: [{ name: "all", fromIndex: 0, toIndex: 359 }],
  };
}

describe("track boundaries", () => {
  it("sit exactly width/2 from the centerline on the real track", () => {
    const track = parseTrack(trackJson);
    const { left, right } = boundaries(track);
    track.centerline.forEach((c, i) => {
      const dl = Math.hypot((left[i]?.x ?? 0) - c.x, (left[i]?.y ?? 0) - c.y);
      const dr = Math.hypot((right[i]?.x ?? 0) - c.x, (right[i]?.y ?? 0) - c.y);
      expect(dl).toBeCloseTo(track.width / 2, 9);
      expect(dr).toBeCloseTo(track.width / 2, 9);
    });
  });

  it("puts the right edge on the car's right-hand side (clockwise on screen is the inside of a circle)", () => {
    const { left, right } = boundaries(circleTrack());
    expect(Math.hypot(right[0]?.x ?? 0, right[0]?.y ?? 0)).toBeCloseTo(90, 9);
    expect(Math.hypot(left[0]?.x ?? 0, left[0]?.y ?? 0)).toBeCloseTo(110, 9);
  });

  it("gives unit normals perpendicular to the local tangent", () => {
    const track = circleTrack();
    const n = rightNormal(track.centerline, 10);
    expect(Math.hypot(n.x, n.y)).toBeCloseTo(1, 9);
    // The normal uses the neighbours on both sides, so check against the central difference.
    const prev = track.centerline[9];
    const next = track.centerline[11];
    if (!prev || !next) throw new Error("bad fixture");
    expect((next.x - prev.x) * n.x + (next.y - prev.y) * n.y).toBeCloseTo(0, 9);
  });

  it("places the start line across the track at centerline[0]", () => {
    const track = parseTrack(trackJson);
    const [a, b] = startLine(track);
    const c = track.centerline[0];
    if (!c) throw new Error("no centerline");
    expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeCloseTo(track.width, 9);
    expect((a.x + b.x) / 2).toBeCloseTo(c.x, 9);
    expect((a.y + b.y) / 2).toBeCloseTo(c.y, 9);
  });
});

describe("rayEnd", () => {
  const pose = { x: 100, y: 200, heading: 0 };

  it("points along heading when the sensor angle is zero", () => {
    const end = rayEnd(pose, 0, 0.5, 150);
    expect(end.x).toBeCloseTo(175, EPS);
    expect(end.y).toBeCloseTo(200, EPS);
  });

  it("has length reading x maxRange", () => {
    const end = rayEnd(pose, 0.6, 0.2, 150);
    expect(Math.hypot(end.x - pose.x, end.y - pose.y)).toBeCloseTo(0.2 * 150, 9);
  });

  it("adds sensor angle to heading, positive clockwise on screen", () => {
    // Heading straight down the screen (+y); a sensor at -pi/2 points along +x.
    const end = rayEnd({ x: 0, y: 0, heading: Math.PI / 2 }, -Math.PI / 2, 1, 100);
    expect(end.x).toBeCloseTo(100, 9);
    expect(end.y).toBeCloseTo(0, 9);
    // A sensor at +pi/2 from the same heading points along -x (the car's left as it drives down).
    const other = rayEnd({ x: 0, y: 0, heading: Math.PI / 2 }, Math.PI / 2, 1, 100);
    expect(other.x).toBeCloseTo(-100, 9);
    expect(other.y).toBeCloseTo(0, 9);
  });

  it("reads zero length when the sensor touches the car", () => {
    const end = rayEnd(pose, 1.2, 0, 150);
    expect(end).toEqual({ x: pose.x, y: pose.y });
  });
});
