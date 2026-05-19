import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api, Workspace } from "./api";

type Ctx = {
  ws: Workspace | null;
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};
const AuthCtx = createContext<Ctx>({} as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ws, setWs] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      setWs(await api.me());
    } catch {
      setWs(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const signOut = async () => {
    await api.logout();
    setWs(null);
  };

  return (
    <AuthCtx.Provider value={{ ws, loading, refresh, signOut }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { ws, loading } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!loading && !ws) navigate("/login");
  }, [ws, loading, navigate]);
  if (loading) return <div className="p-8 text-slate-500">Loading…</div>;
  if (!ws) return null;
  return <>{children}</>;
}
