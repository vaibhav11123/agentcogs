export type MarginTone = "muted" | "destructive" | "warning" | "success";

export function fmtUsd(n: number, decimals = 2): string {
  // Live LLM runs can be sub-cent (e.g. Haiku hello ≈ $0.00004); don't show $0.0000.
  const places =
    n > 0 && n < 0.01 ? Math.max(decimals, 6) : decimals;
  return `$${n.toLocaleString(undefined, {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  })}`;
}

export function fmtPct(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`;
}

export function marginTone(marginPct: number, revenueUsd: number): MarginTone {
  if (revenueUsd <= 0) return "muted";
  if (marginPct < 30) return "destructive";
  if (marginPct < 60) return "warning";
  return "success";
}

export function marginTextClass(tone: MarginTone): string {
  return {
    muted: "text-muted-foreground",
    destructive: "text-destructive",
    warning: "text-warning",
    success: "text-success",
  }[tone];
}

export function marginProgressClass(tone: MarginTone): string {
  return {
    muted: "bg-muted",
    destructive: "bg-destructive",
    warning: "bg-warning",
    success: "bg-success",
  }[tone];
}
