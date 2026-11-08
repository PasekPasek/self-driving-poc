import { asArray, asNumber, asRecord, asString, fail } from "./validate";

export interface Point {
  x: number;
  y: number;
}

export interface Pose extends Point {
  heading: number;
}

export interface Section {
  name: string;
  fromIndex: number;
  toIndex: number;
}

/** Shape of shared/track.json. The centerline is a closed loop; the last point connects to the first. */
export interface Track {
  name: string;
  width: number;
  box: { width: number; height: number };
  start: Pose;
  centerline: Point[];
  sections: Section[];
}

function parsePose(value: unknown, path: string): Pose {
  const r = asRecord(value, path);
  return {
    x: asNumber(r.x, `${path}.x`),
    y: asNumber(r.y, `${path}.y`),
    heading: asNumber(r.heading, `${path}.heading`),
  };
}

/** Checks the shape of a parsed track.json and returns it typed. Throws ReplayFormatError otherwise. */
export function parseTrack(value: unknown): Track {
  const r = asRecord(value, "track");
  const box = asRecord(r.box, "track.box");
  const centerline = asArray(r.centerline, "track.centerline").map((point, i) => {
    const pair = asArray(point, `track.centerline[${i}]`);
    if (pair.length !== 2) fail(`track.centerline[${i}]`, "an [x, y] pair");
    return { x: asNumber(pair[0], `track.centerline[${i}][0]`), y: asNumber(pair[1], `track.centerline[${i}][1]`) };
  });
  if (centerline.length < 3) fail("track.centerline", "a loop of at least 3 points");
  const sections = asArray(r.sections, "track.sections").map((item, i) => {
    const s = asRecord(item, `track.sections[${i}]`);
    return {
      name: asString(s.name, `track.sections[${i}].name`),
      fromIndex: asNumber(s.fromIndex, `track.sections[${i}].fromIndex`),
      toIndex: asNumber(s.toIndex, `track.sections[${i}].toIndex`),
    };
  });
  return {
    name: asString(r.name, "track.name"),
    width: asNumber(r.width, "track.width"),
    box: { width: asNumber(box.width, "track.box.width"), height: asNumber(box.height, "track.box.height") },
    start: parsePose(r.start, "track.start"),
    centerline,
    sections,
  };
}
