import { Progress } from "@/components/ui/progress";
import { fmtPct, marginProgressClass, marginTextClass, marginTone } from "@/lib/format";
import { cn } from "@/lib/utils";

interface MarginBarProps {
  marginPct: number;
  revenueUsd: number;
}

export function MarginBar({ marginPct, revenueUsd }: MarginBarProps) {
  const tone = marginTone(marginPct, revenueUsd);

  if (revenueUsd <= 0) {
    return <span className="text-muted-foreground text-sm">—</span>;
  }

  const barValue = Math.min(100, Math.max(0, marginPct));

  return (
    <div className="flex min-w-[140px] items-center gap-3">
      <Progress
        value={barValue}
        className="h-2 w-20"
        indicatorClassName={marginProgressClass(tone)}
      />
      <span className={cn("font-semibold tabular-nums text-sm w-12 text-right", marginTextClass(tone))}>
        {fmtPct(marginPct)}
      </span>
    </div>
  );
}
