import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import { AnomalyCardGrid } from "@/components/dashboard/AnomalyCard";
import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";
import { PACE_ALERT_PCT } from "@/lib/pace";
import { fmtPct } from "@/lib/format";

export function Alerts() {
  const alerts = useQuery({
    queryKey: ["alerts"],
    queryFn: api.recentAlerts,
  });
  const board = useQuery({
    queryKey: ["leaderboard"],
    queryFn: api.leaderboard,
  });
  const ending = (board.data ?? [])
    .filter((row) => row.pace_margin_pct != null && row.pace_margin_pct < PACE_ALERT_PCT)
    .sort((a, b) => (a.pace_margin_pct ?? 0) - (b.pace_margin_pct ?? 0));

  return (
    <FadeUpStagger className="space-y-6">
      <FadeUpItem>
        <div>
          <h1 className="text-2xl font-display tracking-tight">Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Customers projected to end the month under {PACE_ALERT_PCT}%, then cost spikes of 2.5σ or 3× a typical run.
          </p>
        </div>
      </FadeUpItem>

      <FadeUpItem>
        {board.isLoading ? (
          <Skeleton className="h-24" />
        ) : ending.length === 0 ? (
          <Card className="p-5 text-sm text-muted-foreground">
            No customer is projected under {PACE_ALERT_PCT}%.
          </Card>
        ) : (
          <Card className="divide-y">
            {ending.map((row) => (
              <Link
                key={row.customer_id}
                to={`/customers/${row.customer_id}`}
                className="flex items-center justify-between gap-4 px-5 py-3 text-sm hover:bg-secondary"
              >
                <span className="font-medium">{row.display_name}</span>
                <span className="tabular-nums text-destructive">
                  ends near {fmtPct(row.pace_margin_pct ?? 0)}
                </span>
              </Link>
            ))}
          </Card>
        )}
      </FadeUpItem>

      <FadeUpItem>
        <h2 className="text-sm font-medium">Cost spikes</h2>
      </FadeUpItem>

      <FadeUpItem>
        {alerts.isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-44" />
            ))}
          </div>
        ) : (
          <AnomalyCardGrid alerts={alerts.data ?? []} />
        )}
      </FadeUpItem>
    </FadeUpStagger>
  );
}
