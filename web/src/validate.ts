// Small runtime checks for JSON read from disk or the network. Each helper throws a
// ReplayFormatError naming the offending path, so a bad file fails with a readable message.

export class ReplayFormatError extends Error {
  constructor(message: string) {
    super(`Invalid file: ${message}`);
    this.name = "ReplayFormatError";
  }
}

export function fail(path: string, expected: string): never {
  throw new ReplayFormatError(`${path} must be ${expected}`);
}

export function asRecord(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    fail(path, "an object");
  }
  return value as Record<string, unknown>;
}

export function asArray(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) fail(path, "an array");
  return value as unknown[];
}

export function asNumber(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) fail(path, "a finite number");
  return value as number;
}

export function asInteger(value: unknown, path: string): number {
  const n = asNumber(value, path);
  if (!Number.isInteger(n)) fail(path, "an integer");
  return n;
}

export function asBoolean(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") fail(path, "a boolean");
  return value as boolean;
}

export function asString(value: unknown, path: string): string {
  if (typeof value !== "string") fail(path, "a string");
  return value as string;
}

export function asNumberArray(value: unknown, path: string, length?: number): number[] {
  const items = asArray(value, path);
  if (length !== undefined && items.length !== length) {
    fail(path, `an array of ${length} numbers`);
  }
  return items.map((item, i) => asNumber(item, `${path}[${i}]`));
}
