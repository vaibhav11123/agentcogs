const MAINTAINER_HOSTS = new Set([
  "agentcogs-api-production.up.railway.app",
  "api.agentcogs.dev",
]);

// A customer's own API origin. The public sample stays static when a build
// is pointed at the maintainer's hosts.
export function customerApiUrl(raw: string | undefined | null): string {
  const trimmed = (raw ?? "").trim().replace(/\/$/, "");
  if (!trimmed) return "";
  try {
    if (MAINTAINER_HOSTS.has(new URL(trimmed).host)) return "";
  } catch {
    return "";
  }
  return trimmed;
}
