import { Progress } from "@/components/ui/progress";
import { fmtPct, marginProgressClass, marginTextClass, marginTone } from "@/lib/format";
import { cn } from "@/lib/utils";

interface MarginBarProps {
  marginPct: number | null;
  revenueUsd: number;
}

export function MarginBar({ marginPct, revenueUsd }: MarginBarProps) {
  if (revenueUsd <= 0 || marginPct == null) {
    return <span className="text-muted-foreground text-sm">—</span>;
  }

  const tone = marginTone(marginPct, revenueUsd);

  const barValue = Math.min(100, Math.max(0, marginPct));

  return (
    <div className="flex min-w-[140px] items-center gap-3">
      <Progress
        value={barValue}
        aria-label={`AI margin ${fmtPct(marginPct)}`}
        className="h-2 w-20"
        indicatorClassName={marginProgressClass(tone)}
      />
      <span className={cn("font-semibold tabular-nums text-sm w-12 text-right", marginTextClass(tone))}>
        {fmtPct(marginPct)}
      </span>
    </div>
  );
}
