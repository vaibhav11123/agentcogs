import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "@/api";
import { useAuth } from "@/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const IS_DEV = import.meta.env.DEV;

export function Login() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [stage, setStage] = useState<"email" | "code">("email");
  const [err, setErr] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [own, setOwn] = useState(false);
  const nav = useNavigate();
  const { refresh } = useAuth();
  const setup = useQuery({
    queryKey: ["setup-status"],
    queryFn: api.setupStatus,
    retry: false,
  });
  const selfhost = setup.data?.selfhost === true;

  const request = async () => {
    setErr("");
    try {
      await api.requestLogin(email);
      setStage("code");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Request failed");
    }
  };

  const verify = async () => {
    setErr("");
    try {
      await api.verifyLogin(email, code);
      await refresh();
      nav("/");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Verify failed");
    }
  };

  const devLogin = async () => {
    setErr("");
    try {
      const res = await api.devLogin(email || "test@example.com");
      setApiKey(res.api_key);
      await refresh();
      nav("/");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Dev login failed");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-16">
        <p className="text-sm font-medium text-muted-foreground">AgentCOGS</p>
        <h1 className="mt-3 font-display text-baseline-3xl tracking-tight">
          Which customer stops making money this month
        </h1>
        <p className="mt-4 text-muted-foreground">
          In the sample company, Vellum Research is 29% profitable so far. If that spend continues, the month ends near -52%. One click shows the cap.
        </p>
        {selfhost ? (
          <>
            <Button
              className="mt-8 w-fit"
              onClick={async () => {
                setErr("");
                try {
                  const res = await api.setupClaim();
                  sessionStorage.setItem("acg_api_key", res.api_key);
                  await refresh();
                  nav("/onboarding");
                } catch (e: unknown) {
                  setErr(e instanceof Error ? e.message : "Could not open the workspace");
                }
              }}
            >
              {setup.data?.needs_setup ? "Create my workspace" : "Open my workspace"}
            </Button>
            <p className="mt-3 text-xs text-muted-foreground">
              This machine. No email. The next screen has the install command and your API key.
            </p>
            <button
              type="button"
              className="mt-4 text-sm text-muted-foreground underline-offset-4 hover:underline"
              onClick={() => nav("/demo")}
            >
              Look at the sample company
            </button>
          </>
        ) : (
          <>
            <Button className="mt-8 w-fit" onClick={() => nav("/demo")}>
              Open Patternstack
            </Button>
            <p className="mt-3 text-xs text-muted-foreground">
              Opens the sample company. Nothing to type. A self-hosted API on this machine opens your own workspace instead.
            </p>
          </>
        )}
        {err && <p className="mt-3 text-sm text-destructive">{err}</p>}

        {!selfhost && (
        <div className="mt-12">
          {!own ? (
            <button
              type="button"
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
              onClick={() => setOwn(true)}
            >
              Use your own workspace
            </button>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Your workspace</CardTitle>
                <CardDescription>A code is sent to the work email.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {stage === "email" ? (
                  <>
                    <Input
                      type="email"
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                    <div className="flex flex-col gap-2">
                      <Button variant="secondary" onClick={request} disabled={!email}>
                        Send code
                      </Button>
                      {IS_DEV && (
                        <Button variant="ghost" onClick={devLogin}>
                          Dev login (no email)
                        </Button>
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-muted-foreground">Check {email} for a 6-digit code.</p>
                    <Input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
                    <div className="flex gap-2">
                      <Button onClick={verify}>Verify</Button>
                      <Button variant="secondary" onClick={() => setStage("email")}>
                        Back
                      </Button>
                    </div>
                  </>
                )}
                {apiKey && <p className="text-xs text-muted-foreground break-all">API key: {apiKey}</p>}
                {err && <p className="text-sm text-destructive">{err}</p>}
              </CardContent>
            </Card>
          )}
        </div>
        )}
      </div>
    </div>
  );
}
