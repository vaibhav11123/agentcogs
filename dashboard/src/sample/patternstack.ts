import snapshot from "./patternstack.json";
import type {
  Anomaly,
  CostEvent,
  Customer,
  DailyPoint,
  LeaderboardRow,
  NodeCost,
  OnboardingStatus,
  Summary,
} from "@/api";

type CustomerSnap = {
  customer: Customer;
  daily: DailyPoint[];
  nodes: NodeCost[];
  events: CostEvent[];
};

type Snapshot = {
  as_of: string;
  summary: Summary;
  leaderboard: LeaderboardRow[];
  customers: Record<string, CustomerSnap>;
  alerts: Anomaly[];
  onboarding: OnboardingStatus;
};

const data = snapshot as unknown as Snapshot;

export const SAMPLE_AS_OF = data.as_of;

function customerSnap(id: string): CustomerSnap {
  const row = data.customers[id];
  if (!row) throw new Error("That customer is not in the sample snapshot.");
  return row;
}

export const sampleData = {
  summary: () => data.summary,
  leaderboard: () => data.leaderboard,
  customer: (id: string) => customerSnap(id).customer,
  daily: (id: string) => customerSnap(id).daily,
  nodes: (id: string) => customerSnap(id).nodes,
  events: (id: string) => customerSnap(id).events,
  alerts: () => data.alerts,
  onboarding: () => data.onboarding,
};
