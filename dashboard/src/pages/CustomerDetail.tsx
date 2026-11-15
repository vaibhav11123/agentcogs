import { useEffect } from "react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ArrowLeft } from "@phosphor-icons/react";
import { api } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FeeField } from "@/components/EditableRevenue";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CostRevenueChart, NodeBreakdown } from "@/components/dashboard/CostRevenueChart";
import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";
import { fmtPct, fmtUsd } from "@/lib/format";
import { projectMonth } from "@/lib/pace";
import { SAMPLE_AS_OF } from "@/sample/patternstack";

function statusVariant(status: string): "success" | "warning" | "destructive" | "secondary" {
  if (status === "completed") return "success";
  if (status === "error") return "destructive";
  return "warning";
}

export function CustomerDetail() {
  const { id = "" } = useParams();
  const [search] = useSearchParams();
  const eventId = search.get("event");
  const { ws } = useAuth();
  const sample = ws?.email === "demo@agentcogs.dev";
  const snapshot = Boolean(ws?.sample);
  const qc = useQueryClient();

  const customer = useQuery({ queryKey: ["cust", id], queryFn: () => api.customer(id) });
  const daily = useQuery({ queryKey: ["daily", id], queryFn: () => api.daily(id) });
  const events = useQuery({ queryKey: ["events", id], queryFn: () => api.events(id) });
  const nodes = useQuery({ queryKey: ["nodes", id], queryFn: () => api.nodes(id) });
  const cap = useMutation({
    mutationFn: (budget: number) => api.updateCustomer(id, { monthly_budget_usd: budget }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cust", id] });
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
    },
  });

  useEffect(() => {
    if (!eventId) return;
    document.getElementById(`run-${eventId}`)?.scrollIntoView({ block: "center" });
  }, [eventId, events.data]);

  if (customer.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  const c = customer.data!;
  const asOf = snapshot ? new Date(SAMPLE_AS_OF) : new Date();
  const monthKey = asOf.toISOString().slice(0, 7);
  const monthCost = (daily.data || [])
    .filter((d) => d.day.startsWith(monthKey))
    .reduce((s, d) => s + d.usd, 0);
  const pace = projectMonth(monthCost, Number(c.monthly_revenue_usd || 0), asOf);
  const alreadyCapped = c.monthly_budget_usd != null && monthCost >= Number(c.monthly_budget_usd);

  return (
    <FadeUpStagger className="space-y-6">
      <FadeUpItem>
        <div>
          <Link
            to="/"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors duration-[120ms]"
          >
            <ArrowLeft size={16} aria-hidden />
            All customers
          </Link>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="text-baseline-2xl font-display tracking-tight">
              {c.display_name || c.external_id}
            </h1>
            <Badge variant="secondary" className="font-mono">
              {c.external_id}
            </Badge>
            {c.monthly_budget_usd != null && (
              <Badge variant="outline">Budget {fmtUsd(c.monthly_budget_usd)}/mo</Badge>
            )}
          </div>
          {pace.margin != null && (
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted-foreground max-w-xl">
                {fmtPct(pace.margin)} if this month's spend continues.
                Month to date uses the full monthly revenue against cost so far.
              </p>
              <Button
                disabled={cap.isPending || alreadyCapped || monthCost <= 0 || snapshot}
                onClick={() => cap.mutate(Number(monthCost.toFixed(2)))}
              >
                {snapshot
                  ? "Cap applies on your own workspace"
                  : alreadyCapped
                    ? "Capped at today's spend"
                    : `Stop at ${fmtUsd(monthCost)}`}
              </Button>
            </div>
          )}
        </div>
      </FadeUpItem>

      {!snapshot && Number(c.monthly_revenue_usd || 0) <= 0 && (
        <FadeUpItem>
          <Card className="p-5">
            <p className="text-sm font-medium">Monthly fee</p>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">
              This account has cost and no fee, so margin stays blank. Type what they pay you per month.
            </p>
            <FeeField customerId={c.id} />
          </Card>
        </FadeUpItem>
      )}

      <FadeUpItem>
        <Card className="p-5">
          <p className="text-sm font-medium">Where this number comes from</p>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            One agent call is one event. The SDK names the customer, wraps the call, and posts the cost.
            The month on this page is every call added up. The fee is the monthly amount on the account.
          </p>
          <pre className="mt-4 overflow-x-auto rounded-baseline-md bg-surface-sunken p-4 font-mono text-sm leading-relaxed">{`agentcogs.set_customer("${c.external_id}")
with agentcogs.run(workflow_id="${(events.data || [])[0]?.workflow_id || "research_agent"}"):
    result = agent.invoke(state)`}</pre>
          {(events.data || [])[0] && (
            <p className="mt-3 text-sm">
              Latest call{" "}
              <span className="font-mono">{(events.data || [])[0].workflow_id}</span>
              {" · "}
              {fmtUsd(Number((events.data || [])[0].total_usd), 4)}
              {" · "}
              {format(new Date((events.data || [])[0].ts), "MMM d HH:mm")}
            </p>
          )}
        </Card>
      </FadeUpItem>

      <FadeUpItem>
        <CostRevenueChart
          daily={daily.data || []}
          monthlyRevenue={c.monthly_revenue_usd}
          loading={daily.isLoading}
          revenueHint={
            sample ? "Sample revenue for this company" : "Typed in. Pull Stripe to replace it."
          }
        />
      </FadeUpItem>

      {(nodes.data || []).length > 0 && (
        <FadeUpItem>
          <NodeBreakdown nodes={nodes.data || []} />
        </FadeUpItem>
      )}

      <FadeUpItem>
        <Card className="overflow-hidden">
          <div className="border-b px-4 py-3 font-medium">Recent runs</div>
          <Table>
            <TableHeader>
              <TableRow className="bg-surface-sunken hover:bg-surface-sunken">
                <TableHead>Time</TableHead>
                <TableHead>Workflow</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Cost</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(events.data || []).map((e) => (
                <TableRow
                  key={e.id}
                  id={`run-${e.id}`}
                  className={e.id === eventId ? "bg-amber-100" : undefined}
                >
                  <TableCell>{format(new Date(e.ts), "MMM d HH:mm")}</TableCell>
                  <TableCell>
                    <code className="text-xs rounded bg-muted px-1.5 py-0.5 font-mono">{e.workflow_id}</code>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(e.status)}>{e.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums font-medium">
                    {fmtUsd(Number(e.total_usd), 4)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </FadeUpItem>
    </FadeUpStagger>
  );
}
