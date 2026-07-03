export function parseApiError(raw: string): string {
  try {
    const parsed = JSON.parse(raw) as { detail?: string };
    if (parsed.detail) return parsed.detail;
  } catch {
    /* not JSON */
  }
  return raw;
}
