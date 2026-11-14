import { Link } from "react-router-dom";
import { useAuth } from "@/auth";
import { useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { DownloadSimple } from "@phosphor-icons/react";
import { api } from "@/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { KpiHero, KpiHeroFallback } from "@/components/dashboard/KpiHero";
import { AlertStrip } from "@/components/dashboard/AlertStrip";
import { CustomerTable } from "@/components/dashboard/CustomerTable";
import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";
import { fmtPct, fmtUsd } from "@/lib/format";

export function Leaderboard() {
  const { ws } = useAuth();
  const sample = ws?.email === "demo@agentcogs.dev";
  const [sorting, setSorting] = useState<SortingState>([{ id: "margin_pct", desc: false }]);
  const [capped, setCapped] = useState(false);
  const qc = useQueryClient();

  const { data = [], isLoading } = useQuery({
    queryKey: ["leaderboard"],
    queryFn: api.leaderboard,
  });

  const summary = useQuery({
    queryKey: ["summary"],
    queryFn: api.summary,
  });

  const onboarding = useQuery({
    queryKey: ["onboarding"],
    queryFn: api.onboardingStatus,
  });

  const totalCost = summary.data?.total_cost_usd ?? data.reduce((s, r) => s + r.cost_usd, 0);
  const totalRev = summary.data?.total_revenue_usd ?? data.reduce((s, r) => s + r.revenue_usd, 0);
  const blended =
    summary.data?.blended_margin_pct ??
    (totalRev > 0 ? ((totalRev - totalCost) / totalRev) * 100 : 0);

  const now = new Date();
  const exportUrl = api.exportUrl(now.getFullYear(), now.getMonth() + 1);
  const profit = totalRev - totalCost;
  const priced = data.filter((row) => row.revenue_usd > 0);
  const thinnest = priced.reduce<(typeof data)[number] | null>(
    (worst, row) =>
      worst == null || (row.margin_pct ?? 0) < (worst.margin_pct ?? 0) ? row : worst,
    null
  );
  const pace = thinnest?.pace_margin_pct;
  const alreadyCapped =
    thinnest != null && thinnest.budget_usd != null && thinnest.cost_usd >= thinnest.budget_usd;
  const cap = useMutation({
    mutationFn: () =>
      api.updateCustomer(thinnest!.customer_id, {
        monthly_budget_usd: Number(thinnest!.cost_usd.toFixed(2)),
      }),
    onSuccess: async () => {
      setCapped(true);
      await qc.invalidateQueries({ queryKey: ["leaderboard"] });
      await qc.invalidateQueries({ queryKey: ["summary"] });
    },
  });
  const read =
    data.length === 0
      ? "Connect the SDK to see which customers cost more than they pay."
      : thinnest == null
        ? `AI cost this month is ${fmtUsd(totalCost)}. Add revenue on a row to see margin.`
        : pace != null
          ? `${thinnest.display_name} is ${fmtPct(thinnest.margin_pct ?? 0)} so far. If this spend continues, the month ends near ${fmtPct(pace)}.`
          : `${thinnest.display_name} has the lowest margin, ${fmtPct(thinnest.margin_pct ?? 0)}. Gross profit this month is ${fmtUsd(profit)}.`;

  return (
    <FadeUpStagger className="space-y-6">
      <FadeUpItem>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-baseline-2xl font-display tracking-tight">Customers</h1>
            <p className="text-baseline-sm text-muted-foreground mt-1 max-w-2xl">{read}</p>
          </div>
          <a href={exportUrl} download>
            <Button variant="outline" className="gap-2">
              <DownloadSimple size={16} aria-hidden />
              Export CSV
            </Button>
          </a>
        </div>
      </FadeUpItem>

      <FadeUpItem>
        {summary.isError ? (
          <KpiHeroFallback marginPct={blended} totalCost={totalCost} totalRevenue={totalRev} />
        ) : (
          <KpiHero
            marginPct={blended}
            totalCost={totalCost}
            totalRevenue={totalRev}
            trend={summary.data?.daily_trend ?? []}
            loading={summary.isLoading && !summary.data}
            revenueHint={
              sample ? "Sample revenue for this company" : "Typed in. Pull Stripe to replace it."
            }
            marginHint={
              summary.data?.pace_margin_pct != null
                ? `Month to date. On pace for ${fmtPct(summary.data.pace_margin_pct)} if spend continues.`
                : undefined
            }
          />
        )}
      </FadeUpItem>

      {thinnest && pace != null && (
        <FadeUpItem>
          <Card className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">
                {thinnest.display_name} ends near {fmtPct(pace)} if nothing changes
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Month to date is {fmtPct(thinnest.margin_pct ?? 0)} on {fmtUsd(thinnest.cost_usd)} of
                spend. Capping here stops the next run that would go past today's cost.
              </p>
            </div>
            <Button
              className="shrink-0"
              disabled={cap.isPending || alreadyCapped || capped}
              onClick={() => cap.mutate()}
            >
              {alreadyCapped || capped
                ? "Capped at today's spend"
                : `Stop ${thinnest.display_name} at ${fmtUsd(thinnest.cost_usd)}`}
            </Button>
          </Card>
        </FadeUpItem>
      )}

      <FadeUpItem>
        <AlertStrip
          overBudgetCount={
            summary.data?.over_budget_count ?? data.filter((r) => r.budget_status === "exceeded").length
          }
          warnBudgetCount={
            summary.data?.warn_budget_count ?? data.filter((r) => r.budget_status === "warn").length
          }
          anomalyCount={summary.data?.anomaly_count_7d ?? 0}
        />
      </FadeUpItem>

      <FadeUpItem>
        {data.length > 0 && (
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-medium">By customer</h2>
            <p className="text-xs text-muted-foreground">Lowest margin first</p>
          </div>
        )}
        {!isLoading && data.length === 0 && !onboarding.data?.first_event ? (
          <Card className="p-8 text-center space-y-3">
            <p className="text-sm text-muted-foreground">
              No customers yet. Connect the SDK and send your first cost event.
            </p>
            <Link to="/onboarding">
              <Button>Open setup guide</Button>
            </Link>
          </Card>
        ) : (
          <CustomerTable
            data={data}
            sorting={sorting}
            onSortingChange={setSorting}
            loading={isLoading}
          />
        )}
      </FadeUpItem>
    </FadeUpStagger>
  );
}
