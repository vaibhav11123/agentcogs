import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { Skeleton } from "@/components/ui/skeleton";
import { AnomalyCardGrid } from "@/components/dashboard/AnomalyCard";
import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";

export function Alerts() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: api.recentAlerts,
  });

  return (
    <FadeUpStagger className="space-y-6">
      <FadeUpItem>
        <div>
          <h1 className="text-2xl font-display tracking-tight">Recent anomalies</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Cost spikes detected when a run exceeds 2.5σ or 3× typical spend.
          </p>
        </div>
      </FadeUpItem>

      <FadeUpItem>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-44" />
            ))}
          </div>
        ) : (
          <AnomalyCardGrid alerts={data} />
        )}
      </FadeUpItem>
    </FadeUpStagger>
  );
}
