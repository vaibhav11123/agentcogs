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
}

export function KpiHero({ marginPct, totalCost, totalRevenue, trend, loading }: KpiHeroProps) {
  const tone = marginTone(marginPct, totalRevenue);
  const chartData = trend.map((d) => ({
    day: d.day.slice(5),
    "AI Cost": d.cost_usd,
  }));

  const showAnimation = useFirstChartAnimation(chartData.length > 0);

  return (
    <Card className="overflow-hidden p-0 ring-1 ring-border">
      <div className="grid lg:grid-cols-[1.4fr_1fr_1fr] divide-y lg:divide-y-0 lg:divide-x divide-border">
        <div className="p-6">
          <p className="text-sm font-medium text-muted-foreground">Blended gross margin</p>
          <div className="mt-2 flex items-end gap-3">
            {loading ? (
              <div className="h-10 w-32 animate-skeleton rounded bg-muted" />
            ) : (
              <NumberTicker
                value={totalRevenue > 0 ? marginPct : 0}
                decimalPlaces={1}
                suffix="%"
                className={cn("text-4xl font-bold", marginTextClass(tone))}
              />
            )}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {totalRevenue > 0 ? "Month-to-date across all customers" : "Add revenue to compute margin"}
          </p>
          {chartData.length > 0 && (
            <AreaChart
              className="mt-4 h-28"
              data={chartData}
              index="day"
              categories={["AI Cost"]}
              colors={["orange"]}
              showLegend={false}
              showYAxis={false}
              showGridLines={false}
              showXAxis={true}
              curveType="monotone"
              showAnimation={showAnimation}
              animationDuration={CHART_ANIMATION_DURATION}
            />
          )}
        </div>

        <div className="p-6">
          <p className="text-sm font-medium text-muted-foreground">Total AI cost</p>
          <p className="mt-2 text-3xl font-bold font-mono tabular-nums">{fmtUsd(totalCost)}</p>
          <p className="mt-1 text-xs text-muted-foreground">LLM spend this month</p>
        </div>

        <div className="p-6">
          <p className="text-sm font-medium text-muted-foreground">Total revenue</p>
          <p className="mt-2 text-3xl font-bold font-mono tabular-nums">{fmtUsd(totalRevenue)}</p>
          <p className="mt-1 text-xs text-muted-foreground">Monthly recurring revenue</p>
        </div>
      </div>
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
  const tone = marginTone(marginPct, totalRevenue);
  return (
    <Card className="overflow-hidden p-0 ring-1 ring-border">
      <div className="grid lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-border">
        <div className="p-6">
          <p className="text-sm font-medium text-muted-foreground">Blended gross margin</p>
          <p className={cn("mt-2 text-4xl font-bold font-mono tabular-nums", marginTextClass(tone))}>
            {totalRevenue > 0 ? fmtPct(marginPct) : "—"}
          </p>
        </div>
        <div className="p-6">
          <p className="text-sm font-medium text-muted-foreground">Total AI cost</p>
          <p className="mt-2 text-3xl font-bold font-mono tabular-nums">{fmtUsd(totalCost)}</p>
        </div>
        <div className="p-6">
          <p className="text-sm font-medium text-muted-foreground">Total revenue</p>
          <p className="mt-2 text-3xl font-bold font-mono tabular-nums">{fmtUsd(totalRevenue)}</p>
        </div>
      </div>
    </Card>
  );
}
