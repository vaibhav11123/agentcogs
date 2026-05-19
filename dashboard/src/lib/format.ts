export type MarginTone = "muted" | "destructive" | "warning" | "success";

export function fmtUsd(n: number, decimals = 2): string {
  return `$${n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
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
