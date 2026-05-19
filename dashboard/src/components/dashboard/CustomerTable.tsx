import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  SortingState,
} from "@tanstack/react-table";
import { useNavigate } from "react-router-dom";
import { LeaderboardRow } from "@/api";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BudgetPill } from "@/components/BudgetPill";
import { EditableRevenue } from "@/components/EditableRevenue";
import { MarginBar } from "@/components/dashboard/MarginBar";
import { fmtUsd } from "@/lib/format";

const col = createColumnHelper<LeaderboardRow>();

interface CustomerTableProps {
  data: LeaderboardRow[];
  sorting: SortingState;
  onSortingChange: (sorting: SortingState) => void;
  loading?: boolean;
}

export function CustomerTable({ data, sorting, onSortingChange, loading }: CustomerTableProps) {
  const nav = useNavigate();

  const columns = [
    col.accessor("display_name", {
      header: "Customer",
      cell: (i) => (
        <div>
          <div className="font-medium">{i.getValue()}</div>
          <div className="text-xs text-muted-foreground">{i.row.original.external_id}</div>
        </div>
      ),
    }),
    col.accessor("runs", {
      header: "Runs",
      cell: (i) => <span className="tabular-nums">{i.getValue().toLocaleString()}</span>,
    }),
    col.accessor("cost_usd", {
      header: "AI Cost",
      cell: (i) => <span className="tabular-nums font-medium">{fmtUsd(i.getValue())}</span>,
    }),
    col.accessor("revenue_usd", {
      header: "Revenue",
      cell: (i) => (
        <EditableRevenue customerId={i.row.original.customer_id} value={i.getValue()} />
      ),
    }),
    col.accessor("margin_pct", {
      header: "Margin",
      cell: (i) => (
        <MarginBar marginPct={i.getValue()} revenueUsd={i.row.original.revenue_usd} />
      ),
    }),
    col.accessor("budget_status", {
      header: "Budget",
      cell: (i) => <BudgetPill status={i.getValue()} />,
    }),
  ];

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      onSortingChange(next);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <Card className="overflow-hidden">
      {loading ? (
        <div className="space-y-3 p-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : data.length === 0 ? (
        <div className="p-10 text-center">
          <p className="text-muted-foreground mb-2">No cost events yet.</p>
          <p className="text-sm text-muted-foreground">
            Install the SDK:{" "}
            <Badge variant="secondary" className="font-mono">
              pip install agentcogs
            </Badge>
          </p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id} className="bg-muted/40 hover:bg-muted/40">
                {hg.headers.map((h) => (
                  <TableHead
                    key={h.id}
                    onClick={h.column.getToggleSortingHandler()}
                    className="cursor-pointer select-none"
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: " ↑", desc: " ↓" }[h.column.getIsSorted() as string] ?? ""}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                className="cursor-pointer"
                onClick={() => nav(`/customers/${row.original.customer_id}`)}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Card>
  );
}
