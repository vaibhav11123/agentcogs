import { Badge } from "@/components/ui/badge";
import { fmtUsd } from "@/lib/format";

export function BudgetPill({
  status,
  capUsd,
}: {
  status: "ok" | "warn" | "exceeded";
  capUsd?: number | null;
}) {
  const config = {
    ok: { variant: "success" as const, label: "OK" },
    warn: { variant: "warning" as const, label: "Warn" },
    exceeded: { variant: "destructive" as const, label: "Over" },
  }[status];

  return (
    <div className="flex flex-col items-end gap-1">
      <Badge variant={config.variant}>{config.label}</Badge>
      {capUsd != null && capUsd > 0 ? (
        <span className="text-[10px] leading-none text-muted-foreground tabular-nums">
          cap {fmtUsd(capUsd)}
        </span>
      ) : null}
    </div>
  );
}
