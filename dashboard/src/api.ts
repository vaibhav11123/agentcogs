const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const FETCH_TIMEOUT_MS = 8000;

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(`${BASE}${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      signal: controller.signal,
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }
    if (res.headers.get("content-type")?.includes("application/json")) {
      return res.json();
    }
    return (await res.text()) as unknown as T;
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error(
        `API unreachable at ${BASE} (timeout ${FETCH_TIMEOUT_MS / 1000}s). Run ./tools/start_demo.sh`
      );
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  me: () => req<Workspace>("/v1/auth/me"),
  requestLogin: (email: string) =>
    req("/v1/auth/request", { method: "POST", body: JSON.stringify({ email }) }),
  verifyLogin: (email: string, code: string) =>
    req("/v1/auth/verify", { method: "POST", body: JSON.stringify({ email, code }) }),
  devLogin: (email: string) =>
    req<{ api_key: string }>("/v1/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ email, name: "Dev Workspace" }),
    }),
  demoSession: () => req<{ ok: boolean }>("/v1/demo/session", { method: "POST" }),
  logout: () => req("/v1/auth/logout", { method: "POST" }),

  leaderboard: () => req<LeaderboardRow[]>("/v1/leaderboard"),
  customer: (id: string) => req<Customer>(`/v1/customers/${id}`),
  updateCustomer: (id: string, body: Partial<Customer>) =>
    req<Customer>(`/v1/customers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  events: (id: string) => req<CostEvent[]>(`/v1/customers/${id}/events`),
  daily: (id: string) => req<DailyPoint[]>(`/v1/customers/${id}/daily`),
  nodes: (id: string) => req<NodeCost[]>(`/v1/customers/${id}/nodes`),

  recentAlerts: () => req<Anomaly[]>("/v1/alerts/recent"),
  summary: () => req<Summary>("/v1/summary"),
  updateAlerts: (body: { slack_webhook_url?: string; alert_email?: string }) =>
    req("/v1/alerts/settings", { method: "PATCH", body: JSON.stringify(body) }),

  billingStatus: () => req<{ plan: string; customer_cap: number | null }>("/v1/billing/status"),
  checkout: (plan: string) =>
    req<{ url: string }>("/v1/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),
  billingPortal: () => req<{ url: string }>("/v1/billing/portal", { method: "POST" }),

  stripeStatus: () => req<{ connected: boolean }>("/v1/stripe/status"),
  stripeOauthStart: () => req<{ url: string }>("/v1/stripe/oauth/start"),
  stripeDisconnect: () => req("/v1/stripe/disconnect", { method: "POST" }),

  exportUrl: (year: number, month: number) =>
    `${BASE}/v1/export/monthly.csv?year=${year}&month=${month}`,
};

export type Workspace = {
  id: string;
  name: string;
  email: string;
  api_key: string;
  plan: string;
};
export type LeaderboardRow = {
  customer_id: string;
  external_id: string;
  display_name: string;
  runs: number;
  cost_usd: number;
  revenue_usd: number;
  margin_pct: number;
  budget_usd: number | null;
  budget_status: "ok" | "warn" | "exceeded";
};
export type Customer = {
  id: string;
  external_id: string;
  display_name: string;
  monthly_budget_usd: number | null;
  monthly_revenue_usd: number | null;
  stripe_customer_id: string | null;
};
export type CostEvent = {
  id: string;
  workflow_id: string;
  ts: string;
  status: string;
  total_usd: number;
  model_breakdown: Record<string, unknown>;
  node_breakdown: Record<string, number>;
  error: string | null;
};
export type DailyPoint = { day: string; usd: number; runs: number };
export type NodeCost = { node: string; usd: number };
export type Anomaly = {
  id: string;
  customer_id: string;
  display_name: string;
  external_id: string;
  workflow_id: string;
  total_usd: number;
  multiplier: number;
  z_score: number | null;
  created_at: string;
  event_id: string;
};
export type SummaryDailyPoint = { day: string; cost_usd: number; runs: number };
export type Summary = {
  total_cost_usd: number;
  total_revenue_usd: number;
  blended_margin_pct: number;
  over_budget_count: number;
  warn_budget_count: number;
  anomaly_count_7d: number;
  customer_count: number;
  daily_trend: SummaryDailyPoint[];
  month_start: string;
};
