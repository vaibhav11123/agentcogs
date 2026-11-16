import { useEffect, useRef } from "react";
import { useAuth } from "@/auth";
import { isSample } from "@/sample/session";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const DEMO_EMAIL = "demo@agentcogs.dev";

export const SCREEN_NAMES = [
  "login",
  "demo",
  "onboarding",
  "customers",
  "customer",
  "alerts",
  "settings",
] as const;

export type ScreenName = (typeof SCREEN_NAMES)[number];

type SettledQuery = {
  isSuccess: boolean;
  isError: boolean;
  isFetching: boolean;
};

const recent = new Map<string, number>();

function canReport(ws: { sample?: boolean; email?: string } | null): boolean {
  if (isSample()) return false;
  if (ws?.sample) return false;
  if (ws?.email === DEMO_EMAIL) return false;
  return true;
}

export function reportScreen(screen: ScreenName, success: boolean): void {
  if (isSample()) return;
  if (!SCREEN_NAMES.includes(screen)) return;
  const now = Date.now();
  const signature = `${screen}:${success}`;
  const prev = recent.get(signature);
  if (prev !== undefined && now - prev < 200) return;
  recent.set(signature, now);
  void fetch(`${BASE}/v1/usage`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ screen, success }),
    keepalive: true,
  }).catch(() => {});
}

// visitKey resets the report when the route changes. It is not sent.
export function useScreenUsage(
  screen: ScreenName,
  query: SettledQuery,
  visitKey: string = screen,
): void {
  const { ws, loading } = useAuth();
  const sent = useRef<string | null>(null);
  useEffect(() => {
    if (loading || query.isFetching) return;
    if (!query.isSuccess && !query.isError) return;
    if (sent.current === visitKey) return;
    sent.current = visitKey;
    if (!canReport(ws)) return;
    reportScreen(screen, query.isSuccess);
  }, [screen, visitKey, query.isSuccess, query.isError, query.isFetching, ws, loading]);
}
