import { Link } from "react-router-dom";
import { WarningCircle } from "@phosphor-icons/react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { PACE_ALERT_PCT } from "@/lib/pace";
import { fmtPct } from "@/lib/format";

interface AlertStripProps {
  overBudgetCount: number;
  warnBudgetCount: number;
  anomalyCount: number;
  paceCount?: number;
  paceName?: string | null;
  paceMargin?: number | null;
}

export function AlertStrip({
  overBudgetCount,
  warnBudgetCount,
  anomalyCount,
  paceCount = 0,
  paceName,
  paceMargin,
}: AlertStripProps) {
  const quiet = paceCount === 0 && overBudgetCount === 0 && warnBudgetCount === 0 && anomalyCount === 0;
  if (quiet) {
    return (
      <Alert className="border-success/30 bg-success/5">
        <AlertTitle className="text-success">No customer ends the month under {PACE_ALERT_PCT}%</AlertTitle>
        <AlertDescription className="text-success/90">
          No cost spikes detected in the last 7 days.
        </AlertDescription>
      </Alert>
    );
  }

  const title =
    paceCount > 0
      ? `${paceCount} end the month under ${PACE_ALERT_PCT}%`
      : "Attention needed";
  const lead =
    paceName && paceMargin != null
      ? `${paceName} ends near ${fmtPct(paceMargin)} if spend continues.`
      : "";
  const rest: string[] = [];
  if (overBudgetCount > 0) rest.push(`${overBudgetCount} past a cap you set`);
  if (warnBudgetCount > 0) rest.push(`${warnBudgetCount} near a cap`);
  if (anomalyCount > 0) rest.push(`${anomalyCount} cost spike${anomalyCount > 1 ? "s" : ""} this week`);

  return (
    <Alert variant="warning" className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        <WarningCircle size={16} weight="bold" className="shrink-0" aria-hidden />
        <div>
          <AlertTitle>{title}</AlertTitle>
          <AlertDescription>
            {[lead, rest.join(" · ")].filter(Boolean).join(" ")}
          </AlertDescription>
        </div>
      </div>
      <Button variant="outline" size="sm" asChild className="shrink-0 bg-white/80">
        <Link to="/alerts">View alerts</Link>
      </Button>
    </Alert>
  );
}
