export function nowIso(): string {
  return new Date().toISOString();
}

export function startOfTodayIso(): string {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now.toISOString();
}

export function secondsBetween(startIso?: string, endIso = nowIso()): number | undefined {
  if (!startIso) {
    return undefined;
  }
  return Math.max(0, Math.floor((Date.parse(endIso) - Date.parse(startIso)) / 1000));
}
