import { Badge } from "@/components/ui/badge";

export function BudgetPill({ status }: { status: "ok" | "warn" | "exceeded" }) {
  const config = {
    ok: { variant: "success" as const, label: "OK" },
    warn: { variant: "warning" as const, label: "Warn" },
    exceeded: { variant: "destructive" as const, label: "Over" },
  }[status];

  return <Badge variant={config.variant}>{config.label}</Badge>;
}
