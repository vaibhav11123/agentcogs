import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api";
import { useAuth } from "@/auth";
import { customerApiUrl } from "@/customerApi";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FadeUpItem, FadeUpStagger } from "@/components/motion/FadeUp";
import { sdkSnippet } from "@/lib/install";

export function Onboarding() {
  const { ws } = useAuth();
  const navigate = useNavigate();
  const [pollKey, setPollKey] = useState(0);

  const status = useQuery({
    queryKey: ["onboarding", pollKey],
    queryFn: api.onboardingStatus,
    refetchInterval: (q) => (q.state.data?.first_event ? false : 2000),
  });

  const storedKey = sessionStorage.getItem("acg_api_key");
  const keyQuery = useQuery({
    queryKey: ["setup-key"],
    queryFn: api.setupKey,
    retry: false,
    enabled: Boolean(ws) && !storedKey,
  });

  useEffect(() => {
    if (status.data?.first_event) {
      const t = setTimeout(() => navigate("/"), 1500);
      return () => clearTimeout(t);
    }
  }, [status.data?.first_event, navigate]);

  if (!ws) return null;

  const endpoint = customerApiUrl(import.meta.env.VITE_API_URL) || "http://localhost:8000";
  const apiKey = storedKey || keyQuery.data?.api_key || "";

  const snippet = apiKey
    ? sdkSnippet({ apiKey, workspaceId: ws.id, endpoint })
    : "";

  return (
    <FadeUpStagger className="space-y-6 max-w-2xl mx-auto py-8 px-4">
      <FadeUpItem>
        <div>
          <h1 className="text-2xl font-display tracking-tight">Connect the SDK</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Send your first cost event — usually under 10 minutes.
          </p>
        </div>
      </FadeUpItem>

      <FadeUpItem>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">1. Install & configure</CardTitle>
            <CardDescription>Copy into your app or run the hello script.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {snippet ? (
              <>
                <pre className="bg-muted text-sm p-4 rounded-md overflow-x-auto font-mono">{snippet}</pre>
                <Button variant="secondary" onClick={() => navigator.clipboard.writeText(snippet)}>
                  Copy snippet
                </Button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Rotate the key in Settings. The snippet appears with that key, so the copy is the one that works.
              </p>
            )}
          </CardContent>
        </Card>
      </FadeUpItem>

      <FadeUpItem>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">2. Run the hello script</CardTitle>
            <CardDescription>
              From the repo: <code className="text-xs bg-muted px-1 rounded">examples/hello_agentcogs.py</code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              The key in the block above is the one that authenticates. Optional: OPENAI_API_KEY or ANTHROPIC_API_KEY.
            </p>
            {apiKey && (
            <pre className="bg-muted text-xs p-2 rounded">
              {`export AGENTCOGS_API_KEY='${apiKey}'
export AGENTCOGS_WORKSPACE_ID='${ws.id}'
export AGENTCOGS_ENDPOINT='${endpoint}'
python3 examples/hello_agentcogs.py`}
            </pre>
            )}
          </CardContent>
        </Card>
      </FadeUpItem>

      <FadeUpItem>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">3. Waiting for first event</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-3">
            {status.data?.first_event ? (
              <>
                <Badge variant="success">Received</Badge>
                <span className="text-sm">Redirecting to dashboard…</span>
              </>
            ) : (
              <>
                <Badge variant="secondary">Listening</Badge>
                <span className="text-sm text-muted-foreground">
                  Polling every 2s — run your instrumented agent once.
                </span>
                <Button variant="ghost" size="sm" onClick={() => setPollKey((k) => k + 1)}>
                  Refresh
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </FadeUpItem>

      <FadeUpItem>
        <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
          Skip to dashboard →
        </Link>
      </FadeUpItem>
    </FadeUpStagger>
  );
}
