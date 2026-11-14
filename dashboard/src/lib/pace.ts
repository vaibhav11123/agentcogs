/** Customers whose projected month ends under this margin are the alert. */
export const PACE_ALERT_PCT = 20;

/** Twin of backend/app/services/pace.py. Cost is paced; revenue stays monthly. */
export function projectMonth(costUsd: number, revenueUsd: number, now = new Date()) {
  const elapsed = now.getUTCDate();
  if (elapsed < 3 || costUsd < 0) return { cost: null as number | null, margin: null as number | null };
  const days = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 0)).getUTCDate();
  const cost = (costUsd * days) / elapsed;
  if (revenueUsd <= 0) return { cost, margin: null };
  return { cost, margin: ((revenueUsd - cost) / revenueUsd) * 100 };
}
