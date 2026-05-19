import type { ReactNode } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AuthProvider, RequireAuth, useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Leaderboard } from "./pages/Leaderboard";
import { CustomerDetail } from "./pages/CustomerDetail";
import { Alerts } from "./pages/Alerts";
import { Settings } from "./pages/Settings";
import { DemoLanding } from "./pages/Demo";
import { Onboarding } from "./pages/Onboarding";
import { api } from "./api";

function OnboardingGate({ children }: { children: ReactNode }) {
  const { ws } = useAuth();
  const loc = useLocation();
  const { data } = useQuery({
    queryKey: ["onboarding"],
    queryFn: api.onboardingStatus,
    enabled: !!ws && loc.pathname !== "/onboarding",
  });
  if (loc.pathname === "/onboarding") return <>{children}</>;
  if (data && !data.first_event && loc.pathname === "/") {
    return <Navigate to="/onboarding" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/demo" element={<DemoLanding />} />
        <Route
          element={
            <RequireAuth>
              <OnboardingGate>
                <Layout />
              </OnboardingGate>
            </RequireAuth>
          }
        >
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/" element={<Leaderboard />} />
          <Route path="/customers/:id" element={<CustomerDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AuthProvider>
  );
}
