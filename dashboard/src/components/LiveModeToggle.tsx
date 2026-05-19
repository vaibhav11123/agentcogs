import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Broadcast } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function LiveModeToggle() {
  const qc = useQueryClient();
  const [live, setLive] = useState(false);
  const prevCost = useRef<number | null>(null);

  useEffect(() => {
    if (!live) return;
    const id = setInterval(async () => {
      await qc.invalidateQueries({ queryKey: ["leaderboard"] });
      await qc.invalidateQueries({ queryKey: ["summary"] });
      await qc.invalidateQueries({ queryKey: ["alerts"] });
      await qc.invalidateQueries({ queryKey: ["daily"] });
      await qc.invalidateQueries({ queryKey: ["events"] });

      const summary = qc.getQueryData<{ total_cost_usd: number }>(["summary"]);
      if (summary && prevCost.current != null && summary.total_cost_usd > prevCost.current) {
        const delta = summary.total_cost_usd - prevCost.current;
        toast.info(`New activity detected (+$${delta.toFixed(2)} AI cost)`);
      }
      if (summary) prevCost.current = summary.total_cost_usd;
    }, 3000);
    return () => clearInterval(id);
  }, [live, qc]);

  useEffect(() => {
    if (live) {
      toast.success("Live mode enabled — refreshing every 3s");
      prevCost.current = null;
    }
  }, [live]);

  return (
    <Button
      type="button"
      variant={live ? "default" : "outline"}
      size="sm"
      onClick={() => setLive(!live)}
      className="gap-2"
    >
      <span className="relative flex h-3.5 w-3.5 items-center justify-center">
        <Broadcast size={14} aria-hidden />
        {live && (
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary-foreground ring-2 ring-primary" />
        )}
      </span>
      {live ? "LIVE" : "Static"}
    </Button>
  );
}
