import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ArrowLeft } from "@phosphor-icons/react";
import { api } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
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
import { fmtUsd } from "@/lib/format";

function statusVariant(status: string): "success" | "warning" | "destructive" | "secondary" {
  if (status === "completed") return "success";
  if (status === "error") return "destructive";
  return "warning";
}

export function CustomerDetail() {
  const { id = "" } = useParams();

  const customer = useQuery({ queryKey: ["cust", id], queryFn: () => api.customer(id) });
  const daily = useQuery({ queryKey: ["daily", id], queryFn: () => api.daily(id) });
  const events = useQuery({ queryKey: ["events", id], queryFn: () => api.events(id) });
  const nodes = useQuery({ queryKey: ["nodes", id], queryFn: () => api.nodes(id) });

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
        </div>
      </FadeUpItem>

      <FadeUpItem>
        <div className="grid gap-6 lg:grid-cols-2">
          <CostRevenueChart daily={daily.data || []} monthlyRevenue={c.monthly_revenue_usd} />
          <NodeBreakdown nodes={nodes.data || []} />
        </div>
      </FadeUpItem>

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
                <TableRow key={e.id}>
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
