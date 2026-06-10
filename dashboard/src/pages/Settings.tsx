import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { useAuth } from "@/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";

export function Settings() {
  const { ws, refresh } = useAuth();
  const [slack, setSlack] = useState("");
  const [alertEmail, setAlertEmail] = useState("");
  const [saved, setSaved] = useState(false);
  const [rotatedKey, setRotatedKey] = useState<string | null>(null);
  const [rotating, setRotating] = useState(false);

  const billing = useQuery({ queryKey: ["billing"], queryFn: api.billingStatus });
  const stripe = useQuery({ queryKey: ["stripe"], queryFn: api.stripeStatus });

  useEffect(() => {
    if (ws) setAlertEmail(ws.email);
  }, [ws]);

  const saveAlerts = async () => {
    await api.updateAlerts({
      slack_webhook_url: slack || undefined,
      alert_email: alertEmail || undefined,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
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
    const { url } = await api.checkout(plan);
    window.location.href = url;
  };

  const openPortal = async () => {
    const { url } = await api.billingPortal();
    window.location.href = url;
  };

  const connectStripe = async () => {
    const { url } = await api.stripeOauthStart();
    window.location.href = url;
  };

  if (!ws) return null;

  const maskedKey = ws.key_last4 ? `acg_live_••••${ws.key_last4}` : "acg_live_••••••••";

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
            <Input value={maskedKey} readOnly className="font-mono text-xs" />
            <Button variant="secondary" onClick={rotateKey} disabled={rotating}>
              {rotating ? "Rotating…" : "Rotate key"}
            </Button>
          </div>
          {rotatedKey && (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 space-y-2">
              <p className="text-xs font-medium text-amber-900 dark:text-amber-100">
                Copy your new key now — you won&apos;t see the full key again.
              </p>
              <div className="flex gap-2">
                <Input value={rotatedKey} readOnly className="font-mono text-xs" />
                <Button variant="secondary" onClick={() => navigator.clipboard.writeText(rotatedKey)}>
                  Copy
                </Button>
              </div>
              {ws.key_created_at && (
                <p className="text-xs text-muted-foreground">
                  Active key created {new Date(ws.key_created_at).toLocaleString()}
                </p>
              )}
            </div>
          )}
          <pre className="bg-primary text-primary-foreground text-xs p-3 rounded-md overflow-x-auto">
{`pip install agentcogs

import agentcogs

agentcogs.init(
    api_key="${maskedKey}",
    workspace_id="${ws.id}",
)

agentcogs.set_customer("your_tenant_id")  # once per request
with agentcogs.run(workflow_id="support_bot"):
    # any LLM call here`}
          </pre>
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
          <div className="flex items-center gap-3">
            <Button onClick={saveAlerts}>Save</Button>
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
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => upgrade("starter")}>Upgrade to Starter — $99/mo</Button>
              <Button variant="secondary" onClick={() => upgrade("growth")}>
                Growth — $249/mo
              </Button>
            </div>
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
            Connect Stripe to auto-push daily AI usage to a metered subscription.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stripe.data?.connected ? (
            <div className="flex items-center gap-3">
              <Badge variant="success">Connected</Badge>
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
            <Button onClick={connectStripe}>Connect Stripe</Button>
          )}
        </CardContent>
      </Card>
      </FadeUpItem>
    </FadeUpStagger>
  );
}
