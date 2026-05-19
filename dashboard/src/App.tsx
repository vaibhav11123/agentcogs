import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, RequireAuth } from "./auth";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Leaderboard } from "./pages/Leaderboard";
import { CustomerDetail } from "./pages/CustomerDetail";
import { Alerts } from "./pages/Alerts";
import { Settings } from "./pages/Settings";
import { DemoLanding } from "./pages/Demo";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/demo" element={<DemoLanding />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
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
