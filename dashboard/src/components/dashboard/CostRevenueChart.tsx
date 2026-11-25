import { AreaChart, BarList, Card, Title } from "@tremor/react";
import { fmtUsd, fmtPct, marginTextClass, marginTone } from "@/lib/format";
import { useFirstChartAnimation, CHART_ANIMATION_DURATION } from "@/lib/useChartAnimation";
import { cn } from "@/lib/utils";
import type { DailyPoint, NodeCost } from "@/api";

interface CostRevenueChartProps {
  daily: DailyPoint[];
  monthlyRevenue: number | null;
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
  value: string;
  hint: string;
  valueClass?: string;
}) {
  return (
    <div className="p-5">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <p className={cn("mt-2 text-3xl font-semibold font-mono tabular-nums", valueClass)}>{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

export function CostRevenueChart({
  daily,
  monthlyRevenue,
  loading,
  revenueHint = "Monthly figure, not a daily charge",
}: CostRevenueChartProps) {
  const month = new Date().toISOString().slice(0, 7);
  const thisMonth = daily.filter((d) => d.day.startsWith(month));
  const cost = thisMonth.reduce((sum, d) => sum + d.usd, 0);
  const runs = thisMonth.reduce((sum, d) => sum + d.runs, 0);
  const revenue = monthlyRevenue ?? 0;
  const profit = revenue - cost;
  const hasRevenue = revenue > 0;
  const margin = hasRevenue ? ((revenue - cost) / revenue) * 100 : 0;
  const tone = marginTone(margin, revenue);
  const showTrend = daily.length >= 2;
  const chartData = daily.map((d) => ({
    day: d.day.slice(5),
    "AI Cost": d.usd,
  }));
  const showAnimation = useFirstChartAnimation(showTrend);

  if (loading) {
    return <Card className="h-28 animate-skeleton bg-muted ring-1 ring-border" />;
  }

  return (
    <Card className="overflow-hidden p-0 ring-1 ring-border">
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border">
        <Stat
          label="AI margin"
          value={hasRevenue ? fmtPct(margin) : "—"}
          hint={hasRevenue ? "This month" : "Add monthly revenue"}
          valueClass={hasRevenue ? marginTextClass(tone) : "text-muted-foreground"}
        />
        <Stat
          label="Fee minus AI cost"
          value={fmtUsd(profit)}
          hint="Monthly fee minus attributed AI cost"
          valueClass={profit < 0 ? "text-destructive" : undefined}
        />
        <Stat
          label="AI cost"
          value={fmtUsd(cost)}
          hint={runs === 1 ? "1 run this month" : `${runs} runs this month`}
        />
        <Stat
          label="Fee"
          value={hasRevenue ? fmtUsd(revenue) : "—"}
          hint={revenueHint}
          valueClass={hasRevenue ? undefined : "text-muted-foreground"}
        />
      </div>
      {showTrend ? (
        <div className="border-t border-border px-5 pb-2 pt-4">
          <p className="text-xs font-medium text-muted-foreground">
            AI cost by day · last 30 days. The figures above are this month.
          </p>
          <AreaChart
            className="mt-2 h-36"
            data={chartData}
            index="day"
            categories={["AI Cost"]}
            colors={["orange"]}
            showLegend={false}
            showYAxis={true}
            yAxisWidth={84}
            startEndOnly
            curveType="monotone"
            showAnimation={showAnimation}
            animationDuration={CHART_ANIMATION_DURATION}
            valueFormatter={(v) => fmtUsd(v)}
          />
        </div>
      ) : (
        <p className="border-t border-border px-5 py-3 text-sm text-muted-foreground">
          A daily chart starts on the second day with spend. Revenue stays the monthly number you entered, so it is not drawn as a daily line.
        </p>
      )}
    </Card>
  );
}

interface NodeBreakdownProps {
  nodes: NodeCost[];
}

export function NodeBreakdown({ nodes }: NodeBreakdownProps) {
  const barData = nodes.map((n) => ({
    name: n.node,
    value: n.usd,
  }));

  return (
    <Card className="p-4 ring-1 ring-border">
      <Title>Cost by workflow node</Title>
      <p className="mt-1 text-xs text-muted-foreground">
        This month. The largest bar is the first place to cut.
      </p>
      <BarList
        data={barData}
        className="mt-4"
        valueFormatter={(v: number) => fmtUsd(v)}
        color="orange"
      />
    </Card>
  );
}
