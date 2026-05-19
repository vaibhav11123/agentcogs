import { AreaChart, BarList, Card, Title } from "@tremor/react";
import { fmtUsd } from "@/lib/format";
import { useFirstChartAnimation, CHART_ANIMATION_DURATION } from "@/lib/useChartAnimation";
import type { DailyPoint, NodeCost } from "@/api";

interface CostRevenueChartProps {
  daily: DailyPoint[];
  monthlyRevenue: number | null;
}

export function CostRevenueChart({ daily, monthlyRevenue }: CostRevenueChartProps) {
  const dailyRevenue = (monthlyRevenue ?? 0) / 30;
  const chartData = daily.map((d) => ({
    day: d.day.slice(5),
    "AI Cost": d.usd,
    Revenue: dailyRevenue,
  }));

  const showAnimation = useFirstChartAnimation(chartData.length > 0);

  return (
    <Card className="p-4 ring-1 ring-border">
      <Title>30-day cost vs revenue</Title>
      <AreaChart
        className="mt-4 h-56"
        data={chartData}
        index="day"
        categories={["AI Cost", "Revenue"]}
        colors={["orange", "emerald"]}
        valueFormatter={(v) => fmtUsd(v, 2)}
        showAnimation={showAnimation}
        animationDuration={CHART_ANIMATION_DURATION}
        curveType="monotone"
      />
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
      {barData.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">No node breakdown yet.</p>
      ) : (
        <BarList
          data={barData}
          className="mt-4"
          valueFormatter={(v: number) => fmtUsd(v, 4)}
          color="orange"
        />
      )}
    </Card>
  );
}
