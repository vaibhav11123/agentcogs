import type { ReactNode } from "react";
import { AreaChart, Card } from "@tremor/react";
import { NumberTicker } from "./NumberTicker";
import { fmtUsd, fmtPct, marginTextClass, marginTone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useFirstChartAnimation, CHART_ANIMATION_DURATION } from "@/lib/useChartAnimation";
import type { SummaryDailyPoint } from "@/api";

interface KpiHeroProps {
  marginPct: number;
  totalCost: number;
  totalRevenue: number;
  trend: SummaryDailyPoint[];
  loading?: boolean;
  revenueHint?: string;
}

function Stat({
  label,
  value,
  hint,
  valueClass,
}: {
  label: string;
  value: ReactNode;
  hint: string;
  valueClass?: string;
}) {
  return (
    <div className="p-5">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <div className={cn("mt-2 text-3xl font-semibold font-mono tabular-nums", valueClass)}>{value}</div>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

export function KpiHero({
  marginPct,
  totalCost,
  totalRevenue,
  trend,
  loading,
  revenueHint = "Monthly fee you entered",
  marginHint,
}: KpiHeroProps & { marginHint?: string }) {
  const profit = totalRevenue - totalCost;
  const hasRevenue = totalRevenue > 0;
  const tone = marginTone(marginPct, totalRevenue);
  const chartData = trend.map((d) => ({
    day: d.day.slice(5),
    "AI Cost": d.cost_usd,
  }));
  const showTrend = chartData.length >= 2;
  const showAnimation = useFirstChartAnimation(showTrend);

  return (
    <Card className="overflow-hidden p-0 ring-1 ring-border">
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border">
        <Stat
          label="AI margin"
          hint={
            marginHint ??
            (hasRevenue
              ? "Fee minus attributed AI cost, divided by the fee"
              : "Add a monthly fee to compute margin")
          }
          valueClass={hasRevenue ? marginTextClass(tone) : "text-muted-foreground"}
          value={
            loading ? (
              <div className="h-9 w-24 animate-skeleton rounded bg-muted" />
            ) : hasRevenue ? (
              <NumberTicker value={marginPct} decimalPlaces={1} suffix="%" />
            ) : (
              "—"
            )
          }
        />
        <Stat
          label="Fee minus AI cost"
          hint="Monthly fee minus attributed AI cost"
          valueClass={profit < 0 ? "text-destructive" : undefined}
          value={loading ? <div className="h-9 w-28 animate-skeleton rounded bg-muted" /> : fmtUsd(profit)}
        />
        <Stat
          label="AI cost"
          hint="LLM spend this month"
          value={loading ? <div className="h-9 w-24 animate-skeleton rounded bg-muted" /> : fmtUsd(totalCost)}
        />
        <Stat
          label="Fees"
          hint={revenueHint}
          value={
            loading ? (
              <div className="h-9 w-24 animate-skeleton rounded bg-muted" />
            ) : hasRevenue ? (
              fmtUsd(totalRevenue)
            ) : (
              "—"
            )
          }
          valueClass={hasRevenue ? undefined : "text-muted-foreground"}
        />
      </div>
      {showTrend && (
        <div className="border-t border-border px-5 pb-2 pt-4">
          <p className="text-xs font-medium text-muted-foreground">AI cost by day</p>
          <AreaChart
            className="mt-2 h-24"
            data={chartData}
            index="day"
            categories={["AI Cost"]}
            colors={["orange"]}
            showLegend={false}
            showYAxis={true}
            showGridLines={false}
            yAxisWidth={84}
            startEndOnly
            curveType="monotone"
            showAnimation={showAnimation}
            animationDuration={CHART_ANIMATION_DURATION}
            valueFormatter={(v) => fmtUsd(v)}
          />
        </div>
      )}
    </Card>
  );
}

export function KpiHeroFallback({
  marginPct,
  totalCost,
  totalRevenue,
}: {
  marginPct: number;
  totalCost: number;
  totalRevenue: number;
}) {
  return (
    <KpiHero
      marginPct={marginPct}
      totalCost={totalCost}
      totalRevenue={totalRevenue}
      trend={[]}
    />
  );
}
