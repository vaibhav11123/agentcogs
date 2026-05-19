import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChartLineUp } from "@phosphor-icons/react";
import { api } from "@/api";
import { useAuth } from "@/auth";
import { Card } from "@/components/ui/card";
import { FadeUp } from "@/components/motion/FadeUp";

export function DemoLanding() {
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const tick = setInterval(() => {
      setProgress((p) => Math.min(p + 8, 92));
    }, 120);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    api
      .demoSession()
      .then(() => refresh())
      .then(() => {
        setProgress(100);
        setTimeout(() => nav("/", { replace: true }), 400);
      })
      .catch((e: Error) => setError(e.message));
  }, [nav, refresh]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-background">
        <Card className="max-w-md p-8 text-center">
          <p className="text-destructive font-medium">Demo unavailable</p>
          <p className="text-muted-foreground text-sm mt-2">{error}</p>
          <p className="text-muted-foreground text-sm mt-4">
            Run <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono">./tools/start_demo.sh</code> or{" "}
            <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono">./tools/seed_demo.sh</code> first.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <FadeUp>
        <Card className="w-full max-w-md p-10 text-center shadow-sm">
          <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-baseline-lg bg-primary text-primary-foreground">
            <ChartLineUp size={28} weight="fill" aria-hidden />
          </div>
          <h1 className="text-baseline-2xl font-display tracking-tight">AgentCOGS</h1>
          <p className="mt-2 text-muted-foreground">See which customers are profitable</p>
          <div className="mt-8 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out-studio"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">Loading demo workspace…</p>
        </Card>
      </FadeUp>
    </div>
  );
}
