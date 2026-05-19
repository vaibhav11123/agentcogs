import { Link } from "react-router-dom";
import { format } from "date-fns";
import { Lightning } from "@phosphor-icons/react";
import { Anomaly } from "@/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";
import { fmtUsd } from "@/lib/format";
import { cn } from "@/lib/utils";

interface AnomalyCardProps {
  alert: Anomaly;
  featured?: boolean;
}

export function AnomalyCard({ alert, featured }: AnomalyCardProps) {
  return (
    <Card
      className={cn(
        "overflow-hidden border-l-4 transition-colors duration-[120ms] ease-out-studio hover:bg-secondary/40",
        featured ? "border-l-destructive" : "border-l-warning"
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Lightning
              size={16}
              weight="bold"
              className={cn(featured ? "text-destructive" : "text-warning")}
              aria-hidden
            />
            <CardTitle className="text-base font-display">{alert.display_name || alert.external_id}</CardTitle>
          </div>
          <Badge variant={featured ? "destructive" : "warning"}>
            {Number(alert.multiplier).toFixed(1)}× normal
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Run cost</p>
          <p className="text-2xl font-bold font-mono tabular-nums text-destructive">
            {fmtUsd(Number(alert.total_usd), 4)}
          </p>
        </div>
        <div className="flex items-center justify-between text-sm">
          <code className="rounded bg-muted px-2 py-1 text-xs font-mono">{alert.workflow_id}</code>
          <span className="text-muted-foreground">
            {format(new Date(alert.created_at), "MMM d, h:mm a")}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export function AnomalyCardGrid({ alerts }: { alerts: Anomaly[] }) {
  if (alerts.length === 0) {
    return (
      <Card className="p-10 text-center">
        <p className="text-muted-foreground">
          No cost spikes detected. Alerts appear when a run costs &gt;2.5σ or &gt;3× a
          customer&apos;s typical spend.
        </p>
      </Card>
    );
  }

  return (
    <FadeUpStagger className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {alerts.map((a, idx) => (
        <FadeUpItem key={a.id}>
          <Link to={`/customers/${a.customer_id}`} className="block">
            <AnomalyCard alert={a} featured={idx === 0} />
          </Link>
        </FadeUpItem>
      ))}
    </FadeUpStagger>
  );
}
