const KEY = "acg_sample";

export function isSample(): boolean {
  return sessionStorage.getItem(KEY) === "1";
}

export function enterSample(): void {
  sessionStorage.setItem(KEY, "1");
}

export function leaveSample(): void {
  sessionStorage.removeItem(KEY);
}

export const SAMPLE_WORKSPACE = {
  id: "sample",
  name: "Patternstack",
  email: "demo@agentcogs.dev",
  plan: "sample",
  sample: true,
};
