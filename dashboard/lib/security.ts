const ALLOWED_PROTOCOLS = ["https:", "http:"];

export function sanitizeUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (!ALLOWED_PROTOCOLS.includes(parsed.protocol)) return null;
    return url;
  } catch {
    return null;
  }
}
