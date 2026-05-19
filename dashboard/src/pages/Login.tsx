import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api";
import { useAuth } from "@/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const IS_DEV = import.meta.env.DEV;

export function Login() {
  const [email, setEmail] = useState("test@example.com");
  const [code, setCode] = useState("");
  const [stage, setStage] = useState<"email" | "code">("email");
  const [err, setErr] = useState("");
  const [apiKey, setApiKey] = useState("");
  const nav = useNavigate();
  const { refresh } = useAuth();

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
      const res = await api.devLogin(email);
      setApiKey(res.api_key);
      await refresh();
      nav("/");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Dev login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl font-display">AgentCOGS</CardTitle>
          <CardDescription>Per-customer LLM cost attribution</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {stage === "email" ? (
            <>
              <label className="block text-sm font-medium">Work email</label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              <div className="flex flex-col gap-2">
                <Button onClick={request}>Send code</Button>
                {IS_DEV && (
                  <Button variant="secondary" onClick={devLogin}>
                    Dev login (no email)
                  </Button>
                )}
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                Check {email} for a 6-digit code (or backend logs in dev).
              </p>
              <Input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
              <div className="flex gap-2">
                <Button onClick={verify}>Verify</Button>
                <Button variant="secondary" onClick={() => setStage("email")}>
                  Back
                </Button>
              </div>
            </>
          )}
          {apiKey && (
            <p className="text-xs text-muted-foreground break-all">API key: {apiKey}</p>
          )}
          {err && <p className="text-sm text-destructive">{err}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
