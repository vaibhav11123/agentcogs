import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { useAuth } from "@/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";
import { sdkSnippet } from "@/lib/install";

export function Settings() {
  const { ws, refresh } = useAuth();
  const [slack, setSlack] = useState("");
  const [alertEmail, setAlertEmail] = useState("");
  const [saved, setSaved] = useState(false);
  const [rotatedKey, setRotatedKey] = useState<string | null>(null);
  const [actionErr, setActionErr] = useState("");
  const [alertErr, setAlertErr] = useState("");
  const [rotating, setRotating] = useState(false);

  const snapshot = Boolean(ws?.sample);
  const setupKey = useQuery({
    queryKey: ["setup-key"],
    queryFn: api.setupKey,
    retry: false,
    enabled: !snapshot,
  });
  const billing = useQuery({ queryKey: ["billing"], queryFn: api.billingStatus, enabled: !snapshot });
  const stripe = useQuery({ queryKey: ["stripe"], queryFn: api.stripeStatus, enabled: !snapshot });
  const savedAlerts = useQuery({
    queryKey: ["alert-settings"],
    queryFn: api.alertSettings,
    enabled: !snapshot,
  });

  useEffect(() => {
    if (!savedAlerts.data) return;
    setSlack(savedAlerts.data.slack_webhook_url || "");
    setAlertEmail(savedAlerts.data.alert_email || "");
  }, [savedAlerts.data]);

  const saveAlerts = async () => {
    setAlertErr("");
    try {
      await api.updateAlerts({
        slack_webhook_url: slack || undefined,
        alert_email: alertEmail || undefined,
      });
      await savedAlerts.refetch();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: unknown) {
      setAlertErr(e instanceof Error ? e.message : "Could not save alerts");
    }
  };

  const testSlack = async () => {
    setAlertErr("");
    try {
      await api.updateAlerts({
        slack_webhook_url: slack || undefined,
        alert_email: alertEmail || undefined,
      });
      await api.testAlert();
      await savedAlerts.refetch();
      setSaved(true);
    } catch (e: unknown) {
      setAlertErr(e instanceof Error ? e.message : "Slack test failed");
    }
  };

  const rotateKey = async () => {
    setRotating(true);
    try {
      const { api_key } = await api.rotateKey();
      setRotatedKey(api_key);
      await refresh();
    } finally {
      setRotating(false);
    }
  };

  const upgrade = async (plan: string) => {
    setActionErr("");
    try {
      const { url } = await api.checkout(plan);
      window.location.href = url;
    } catch (e: unknown) {
      setActionErr(e instanceof Error ? e.message : "Billing is not available");
    }
  };

  const openPortal = async () => {
    setActionErr("");
    try {
      const { url } = await api.billingPortal();
      window.location.href = url;
    } catch (e: unknown) {
      setActionErr(e instanceof Error ? e.message : "Billing is not available");
    }
  };

  const connectStripe = async () => {
    setActionErr("");
    try {
      const { url } = await api.stripeOauthStart();
      window.location.href = url;
    } catch (e: unknown) {
      setActionErr(e instanceof Error ? e.message : "Stripe is not connected");
    }
  };

  if (!ws) return null;

  if (snapshot) {
    return (
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle className="text-base">Sample snapshot</CardTitle>
          <CardDescription>
            This company is a saved snapshot so the public link opens with no account.
            Keys, Stripe, and the cap apply on a workspace you run yourself.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const fullKey = rotatedKey || setupKey.data?.api_key || sessionStorage.getItem("acg_api_key") || "";
  const endpoint = import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
  const snippet = fullKey
    ? sdkSnippet({ apiKey: fullKey, workspaceId: ws.id, endpoint })
    : "";

  return (
    <FadeUpStagger className="space-y-6 max-w-2xl">
      <FadeUpItem>
        <div>
          <h1 className="text-2xl font-display tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">Workspace configuration and integrations.</p>
        </div>
      </FadeUpItem>

      <FadeUpItem>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">SDK API Key</CardTitle>
          <CardDescription>
            Pass this to <code className="text-xs bg-muted px-1 rounded">agentcogs.init(api_key=...)</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input value={fullKey || "Rotate the key to reveal it"} readOnly className="font-mono text-xs" />
            <Button variant="secondary" onClick={rotateKey} disabled={rotating}>
              {rotating ? "Rotating…" : fullKey ? "Rotate key" : "Show a new key"}
            </Button>
          </div>
          {rotatedKey && (
            <p className="text-xs text-muted-foreground">
              This key replaced the previous one. The snippet below uses it.
            </p>
          )}
          {snippet ? (
            <pre className="bg-primary text-primary-foreground text-sm p-4 rounded-md overflow-x-auto font-mono">
              {snippet}
            </pre>
          ) : (
            <p className="text-sm text-muted-foreground">
              The copy block appears after the key is on screen, so it is the key that authenticates.
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Env: AGENTCOGS_API_KEY, AGENTCOGS_WORKSPACE_ID, AGENTCOGS_ENDPOINT
          </p>
        </CardContent>
      </Card>
      </FadeUpItem>

      <FadeUpItem>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cost spike alerts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Slack webhook URL</label>
            <Input
              value={slack}
              onChange={(e) => setSlack(e.target.value)}
              placeholder="https://hooks.slack.com/services/…"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Alert email</label>
            <Input type="email" value={alertEmail} onChange={(e) => setAlertEmail(e.target.value)} />
          </div>
          {alertErr && <p className="text-sm text-destructive">{alertErr}</p>}
          <div className="flex items-center gap-3">
            <Button onClick={saveAlerts}>Save</Button>
            <Button variant="secondary" onClick={testSlack}>Send test to Slack</Button>
            {saved && <Badge variant="success">Saved</Badge>}
          </div>
        </CardContent>
      </Card>
      </FadeUpItem>

      <FadeUpItem>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Current: <strong className="uppercase text-foreground">{billing.data?.plan || ws.plan}</strong>
            {billing.data?.customer_cap != null && (
              <> · up to {billing.data.customer_cap} customers</>
            )}
          </p>
          {ws.plan === "free" ? (
            <>
            {actionErr && <p className="text-sm text-destructive">{actionErr}</p>}
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => upgrade("starter")}>Upgrade to Starter — $99/mo</Button>
              <Button variant="secondary" onClick={() => upgrade("growth")}>
                Growth — $249/mo
              </Button>
            </div>
            </>
          ) : (
            <Button variant="secondary" onClick={openPortal}>
              Manage billing
            </Button>
          )}
        </CardContent>
      </Card>
      </FadeUpItem>

      <FadeUpItem>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Stripe Meter export</CardTitle>
          <CardDescription>
            Connect Stripe to pull each customer's subscription revenue, and to
            push daily AI usage onto a metered subscription.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stripe.data?.connected ? (
            <div className="flex items-center gap-3">
              <Badge variant="success">Connected</Badge>
              <Button
                onClick={async () => {
                  await api.stripeSyncRevenue();
                  stripe.refetch();
                }}
              >
                Pull subscription revenue
              </Button>
              <Button
                variant="secondary"
                onClick={async () => {
                  await api.stripeDisconnect();
                  stripe.refetch();
                }}
              >
                Disconnect
              </Button>
            </div>
          ) : (
            <>
            {actionErr && <p className="mb-2 text-sm text-destructive">{actionErr}</p>}
            <Button onClick={connectStripe}>Connect Stripe</Button>
            </>
          )}
        </CardContent>
      </Card>
      </FadeUpItem>
    </FadeUpStagger>
  );
}
