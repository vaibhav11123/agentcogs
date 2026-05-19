import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  ChartLineUp,
  Gear,
  SignOut,
  Users,
  Warning,
} from "@phosphor-icons/react";
import { useAuth } from "@/auth";
import { NavIcon } from "@/components/icons";
import { LiveModeToggle } from "@/components/LiveModeToggle";
import { PageTransition } from "@/components/motion/FadeUp";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const DEMO_EMAIL = "demo@agentcogs.dev";
const DEMO_WORKSPACE_NAME = "Patternstack";

const navItems = [
  { to: "/", label: "Customers", icon: Users, end: true },
  { to: "/alerts", label: "Alerts", icon: Warning },
  { to: "/settings", label: "Settings", icon: Gear },
];

export function Layout() {
  const { ws, signOut } = useAuth();
  const isDemo = ws?.email === DEMO_EMAIL;
  const location = useLocation();

  return (
    <div className="min-h-screen flex bg-background">
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r bg-card">
        <div className="flex h-16 items-center gap-2 px-5 border-b">
          <div className="flex h-8 w-8 items-center justify-center rounded-baseline-md bg-primary text-primary-foreground">
            <ChartLineUp size={16} weight="fill" aria-hidden />
          </div>
          <div>
            <Link to="/" className="font-display text-baseline-sm tracking-tight">
              AgentCOGS
            </Link>
            <p className="text-baseline-xs text-muted-foreground leading-tight">
              {isDemo ? DEMO_WORKSPACE_NAME : "Per-customer LLM economics"}
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {navItems.map(({ to, label, icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-baseline-md px-3 py-2 text-baseline-sm font-medium transition-colors duration-[120ms] ease-out-studio active:scale-[0.97]",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <NavIcon icon={icon} active={isActive} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t p-4 space-y-3">
          {isDemo && (
            <Badge variant="secondary" className="w-full justify-center">
              Demo workspace
            </Badge>
          )}
          <div className="text-baseline-xs text-muted-foreground truncate">{ws?.email}</div>
          <Badge variant="outline" className="uppercase text-baseline-xs">
            {ws?.plan}
          </Badge>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b bg-background/95 backdrop-blur px-4 md:px-6">
          <div className="flex items-center gap-4">
            <div className="md:hidden font-display font-bold">AgentCOGS</div>
            <nav className="flex md:hidden gap-1">
              {navItems.map(({ to, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      "rounded-baseline-md px-2.5 py-1.5 text-baseline-xs font-medium transition-colors duration-[120ms]",
                      isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                    )
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="hidden md:block text-baseline-sm text-muted-foreground">
            Customer profitability dashboard
          </div>
          <div className="flex items-center gap-2">
            <LiveModeToggle />
            <Separator orientation="vertical" className="h-6 hidden sm:block" />
            <Button variant="ghost" size="sm" onClick={signOut} className="hidden sm:flex gap-2">
              <SignOut size={16} aria-hidden />
              Sign out
            </Button>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6 lg:p-8">
          <PageTransition key={location.pathname}>
            <Outlet />
          </PageTransition>
        </main>
      </div>
    </div>
  );
}
