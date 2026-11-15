import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { fmtUsd } from "@/lib/format";
import { Button } from "@/components/ui/button";

export function EditableRevenue({
  customerId,
  value,
  locked = false,
}: {
  customerId: string;
  value: number;
  locked?: boolean;
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

  if (locked) {
    return <span className="tabular-nums">{value > 0 ? fmtUsd(value) : "—"}</span>;
  }

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

export function FeeField({ customerId }: { customerId: string }) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState("");
  const mut = useMutation({
    mutationFn: (v: number) => api.updateCustomer(customerId, { monthly_revenue_usd: v }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["leaderboard"] });
      await qc.invalidateQueries({ queryKey: ["summary"] });
      await qc.invalidateQueries({ queryKey: ["cust", customerId] });
    },
  });

  return (
    <form
      className="mt-3 flex flex-wrap items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const value = Number(draft);
        if (!Number.isFinite(value) || value < 0) return;
        mut.mutate(value);
      }}
    >
      <Input
        type="number"
        min="0"
        step="1"
        value={draft}
        placeholder="8200"
        onChange={(e) => setDraft(e.target.value)}
        className="h-9 w-32"
        aria-label="Monthly fee in dollars"
      />
      <Button type="submit" disabled={mut.isPending || draft === ""}>
        Save fee
      </Button>
    </form>
  );
}
