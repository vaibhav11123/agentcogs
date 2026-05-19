import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { fmtUsd } from "@/lib/format";

export function EditableRevenue({
  customerId,
  value,
}: {
  customerId: string;
  value: number;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value || ""));

  const mut = useMutation({
    mutationFn: (v: number) =>
      api.updateCustomer(customerId, { monthly_revenue_usd: v }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
    },
  });

  if (!editing) {
    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setDraft(String(value || ""));
          setEditing(true);
        }}
        className={cn(
          "text-left w-full rounded px-2 py-1 tabular-nums hover:bg-muted transition-colors",
          value <= 0 && "text-muted-foreground"
        )}
      >
        {value > 0 ? fmtUsd(value) : "Add revenue"}
      </button>
    );
  }

  return (
    <Input
      autoFocus
      type="number"
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onClick={(e) => e.stopPropagation()}
      onBlur={() => {
        mut.mutate(Number(draft) || 0);
        setEditing(false);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          mut.mutate(Number(draft) || 0);
          setEditing(false);
        }
        if (e.key === "Escape") setEditing(false);
      }}
      className="h-8 w-28"
    />
  );
}
