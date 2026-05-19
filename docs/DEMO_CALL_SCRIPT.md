# AgentCOGS Validation Call — 30-Minute Script

## Goal of this call

The goal is **not** to sell the product. The goal is to confirm: *does this prospect have the per-customer attribution problem badly enough to install the SDK right now?*

If they install during the call → success.  
If they say "let me think about it" → failure (politely).

## 5 minutes before the call

```bash
./tools/seed_demo.sh
cd dashboard && npm run dev

# Terminal 3 — live drift (use WS_ID and DEMO_KEY printed by seed_demo.sh)
python3 tools/live_drift.py \
  --workspace-id "$DEMO_WORKSPACE_ID" \
  --api-key "$DEMO_API_KEY" \
  --interactive
```

- Code editor open with `prototype/demo.py`
- Clean venv ready: `pip install agentcogs` (or editable install)
- Their GitHub repo URL ready
- Notifications off

---

## Minute 0:00 — Opening (60 seconds)

> "Hey [name], thanks for hopping on. Quick agenda: I want to ask you one question about how you handle costs today, then if it's relevant I'll show you what we built in about 5 minutes, and we can install it together in your repo if it makes sense. Cool?"

[Wait for yes]

> "Great. So — how do you currently know what each customer costs you to serve?"

**Then shut up.** Count to 10 if needed.

---

## Minute 0:30 — Listen (3–5 minutes)

| Phrase | Meaning | Action |
|--------|---------|--------|
| "spreadsheet" / "manual" | confirmed pain | proceed to demo |
| "we just averaged it out" | confirmed pain | proceed |
| "LangSmith traces and a calculation" | partial pain | proceed |
| "we built custom middleware" | strong pain | proceed |
| "we don't really know" | strong pain | proceed |
| "OpenAI dashboard is fine" | no pain | end gracefully |
| "Helicone / Langfuse" | traces not margin | proceed |

**Probing follow-ups (pick 1–2):**

> "How often are you updating that spreadsheet?"

> "Does that number feed into billing or which customers to drop?"

> "Have you ever found out months later a customer was unprofitable?"

---

## Minute 4:00 — The Bridge (30 seconds)

> "That tracks with what I've heard from other LangGraph founders. Want me to show what we built in about 90 seconds?"

[Wait for yes]

> "Cool, I'll share my screen."

---

## Minute 4:30 — The Dashboard (90 seconds)

Open `http://localhost:5173` (after `/demo` or dev login).

> "Each row is one of your customers. Three columns matter: AI cost this month, revenue, gross margin."

Point at **TechFlow** vs **Acme**:

> "TechFlow is around 29% margin. Acme is around 75%. With 40 customers you'll usually find 2–3 you didn't realize were burning you."

Click **TechFlow** → per-node breakdown.

---

## Minute 6:00 — Live anomaly (60 seconds)

Terminal 3: press **`a`** (Initech retry loop).

> "I'm simulating a retry loop for Initech. Watch Alerts / the dashboard with LIVE on."

Toggle **LIVE** in the header. Show the new anomaly within a few seconds.

---

## Minute 7:00 — The SDK (90 seconds)

Run `python prototype/demo.py` — walk through the two-line integration and printed cost event.

> "If they're over budget, we raise **before** the LLM call — not just after."

---

## Minute 8:30 — The install ask

> "Would you be open to installing this in your repo right now? About 5 minutes. Free design partner access."

**Stop talking.**

### If YES

1. `pip install agentcogs`
2. Issue API key (from your DB or their new workspace)
3. Wrap their `.invoke()` with `agentcogs.run(customer_id=...)`
4. One real request → show their event in the dashboard

### If MAYBE

> "What would have to be true for you to want this?"

### If NO

> "What would solve this problem if you could wave a magic wand?"

---

## Minute 15:00 — Close

> "Three quick questions: (1) how many customers on the platform? (2) rough monthly AI spend? (3) who else has this problem — would you intro one person?"

**Always ask for an intro.**

---

## After the call (within 10 minutes)

Send recap email with dashboard link, workspace ID, API key, and Friday check-in.

Log in CRM: attribution method (their words), pain 1–5, installed Y/N, objection, intros, next step.

---

## Failure mode antidotes

| If they… | Then you… |
|----------|-----------|
| Compare to LangSmith | "LangSmith logs traces; we aggregate per-customer margin." |
| Ask pricing | "Free for design partners; paid tier later around $99/mo." |
| Ask security | "Token counts and costs only — no prompts. SDK is auditable." |
| Go silent | Don't fill it — they're deciding. |

---

## What success looks like

- SDK installed + first real event in dashboard
- 1+ peer intro committed
- Specific follow-up date

Two or more "great" calls out of five Week-0 DMs → strong PMF signal.
