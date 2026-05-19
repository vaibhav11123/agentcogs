import { Link } from "react-router-dom";
import { WarningCircle } from "@phosphor-icons/react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface AlertStripProps {
  overBudgetCount: number;
  warnBudgetCount: number;
  anomalyCount: number;
}

export function AlertStrip({ overBudgetCount, warnBudgetCount, anomalyCount }: AlertStripProps) {
  if (overBudgetCount === 0 && warnBudgetCount === 0 && anomalyCount === 0) {
    return (
      <Alert className="border-success/30 bg-success/5">
        <AlertTitle className="text-success">All customers within budget</AlertTitle>
        <AlertDescription className="text-success/90">
          No cost spikes detected in the last 7 days.
        </AlertDescription>
      </Alert>
    );
  }

  const parts: string[] = [];
  if (overBudgetCount > 0) {
    parts.push(`${overBudgetCount} customer${overBudgetCount > 1 ? "s" : ""} over budget`);
  }
  if (warnBudgetCount > 0) {
    parts.push(`${warnBudgetCount} approaching budget limit`);
  }
  if (anomalyCount > 0) {
    parts.push(`${anomalyCount} cost anomal${anomalyCount > 1 ? "ies" : "y"} this week`);
  }

  return (
    <Alert variant="warning" className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        <WarningCircle size={16} weight="bold" className="shrink-0" aria-hidden />
        <div>
          <AlertTitle>Attention needed</AlertTitle>
          <AlertDescription>{parts.join(" · ")}</AlertDescription>
        </div>
      </div>
      {(overBudgetCount > 0 || anomalyCount > 0) && (
        <Button variant="outline" size="sm" asChild className="shrink-0 bg-white/80">
          <Link to="/alerts">View alerts</Link>
        </Button>
      )}
    </Alert>
  );
}
