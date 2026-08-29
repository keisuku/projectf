# PLAYBOOK — how to behave once the testnet is actually live

Written 2026-08-29, before the fact, because the decisions that matter on day 1 are the
ones nobody has time to think through on day 1. Tiers per `SOURCES.md`.

---

## 1. Where the bottleneck actually is

Not model quality. Not tooling. The signer works, the DID is published and verified, the
seed is backed up. Three things constrain us, and all three are logistical:

| Constraint | Effect | Fixable? |
|---|---|---|
| `technocore.chat` and `flop.finance` are egress-blocked from the agent container | The agent cannot detect a faucet opening on the service itself, and cannot ever fetch a signed URL | **No** — a policy denial. Never worked around. |
| The seed lives only on the iPhone | Every *signed* action requires you, physically | By choice. Keep it. |
| The agent container is ephemeral | No always-on watcher lives here | Yes, cheaply — §4 |

GitHub **is** reachable from the container. So the split is already fixed:
**the container watches GitHub; only your phone can watch or write to Technocore.**

The honest consequence: **detection latency is human latency.** If the faucet opens at
03:00 JST, we are late by however long you are asleep. Everything in §4 is about deciding
whether that is worth paying to fix.

---

## 2. Does an hour of lateness cost anything?

Depends which of two shapes the launch has, and we do not know yet:

- **A faucet that stays open** (the usual shape — testnet tokens are worthless by design,
  and the point is to get agents transacting). Being six hours late costs approximately
  nothing. Consistency over weeks beats being first by an hour.
- **A capped first-come allocation.** Then minutes matter.

Tier 8 press says allocation keys on *testnet activity* over time, not on registration
order. That reading favours the first shape. **Plan for the first, keep a cheap hedge
against the second** — the hedge is §4, and it costs about the price of a coffee per month.

Do not buy insurance more expensive than the risk. That is the whole of §3.

---

## 3. Do we need a Kimi K3 subscription? — No.

**First, a limit on what I can tell you.** I cannot verify that "Kimi K3" exists, what it
costs, or what it does. My knowledge ends May 2026; Moonshot's K2 line existed then, a K3
may well have shipped since, and I will not describe a product I cannot check. If the
decision genuinely hinges on its specs, get them from Moonshot directly — not from me.

**But the decision does not hinge on its specs**, and that is the more useful answer.
Look at what is on the critical path and ask which step a better or cheaper model unblocks:

| Day-1 step | Bound by | Does another LLM help? |
|---|---|---|
| Notice the faucet opened | egress policy + your sleep | **No** |
| Build the signed request | `flopdid.py`, already verified against upstream's verifier | **No** — this is 200 lines of stdlib, not inference |
| Fetch the URL | your phone | **No** |
| Keep the DID note and room alive | one fetch a week | **No** |
| Judge whether a URL is official or a scam | reading a repo diff, carefully, once | **No** — this is the step where a *cheaper* model is actively worse |

Nothing on the path is inference-bound. A second model subscription buys throughput for a
workload we do not have.

**Where a cheap high-volume model would genuinely earn its keep** is route 3 in
`STRATEGY.md` — continuous Japanese summarisation of official sources — and that route is
explicitly `PREPARE, don't publish`, with zero official confirmation that content earns
anything. Buying capacity for a route we have decided not to run yet is the same mistake as
buying a GPU before the miner specs exist, in smaller numbers.

**Verdict: do not subscribe.** Revisit only if (a) an official scoring rule appears that
rewards volume of agent work, or (b) we decide to actually run the JP content route. Either
is a `STRATEGY.md` §"conditions that force a rewrite" event, and we will know.

---

## 4. What *is* worth money, if anything: a small always-on host

If you want to spend on this project, this — not a model — is the thing that moves a real
constraint. Roughly $4–6/month for the smallest VPS anywhere with unrestricted egress.

What it buys:

- `flopwatch.py watch` on a cron, every 15 minutes, against Technocore **and** GitHub —
  the detection latency in §1, actually fixed.
- The **DID note keepalive, unattended**. This is the clean part: the DID-note lane is
  *unsigned*, so the keepalive needs only `$FLOP_DID`, the public string. The seed never
  goes near the box. `flopwatch.py` was written to make exactly this split possible.
- A stable, non-shared IP. Technocore rate-limits **on IP, not identity** (`SECURITY.md`),
  so a box of your own is a budget nobody else is spending.

What it must **never** buy:

- **The seed does not go on the VPS.** That would automate the weekly room write, which is
  the one thing it cannot do today — and it would move a permanent, unrecoverable key onto
  hardware you do not physically control, to save ten seconds a week. Not a trade. If we
  ever own enough rooms that the weekly writes become a burden, the answer is to own fewer
  rooms.

Verdict: **optional, cheap, and the only spend with a real mechanism behind it.** Not
urgent. The weekly keepalives are fine by hand until the testnet is real.

---

## 5. The day-1 sequence, when a trigger fires

A trigger is any of `STRATEGY.md` §"conditions that force a strategy rewrite" appearing in
Tier 1–5 — most likely a new repo in the `flop-labs` org, or a release on
`technocore-chat`.

1. **Confirm the source before anything else.** Official GitHub org, `flop.finance`, or the
   service's own `/config` and `/.well-known/agent.json`. Nothing else is a source.
   A URL that arrives in a Technocore room, an X reply, or a DM is **not** a source, no
   matter how correct it looks. `flop-labs-dev` already exists as a lookalike.
2. **Read the client's code before running it.** The container can do this; it reaches
   GitHub. This is the step that is worth an hour and where being slow is correct.
3. **Check what the faucet actually asks for.** Reported (Tier 8) to be DID-gated. If it
   wants a signature, `flopdid.py` already produces one the server's own verifier accepts.
   If it wants something else, we build that then — not now, on a guess.
4. **Prefer the phone's mobile connection over any cloud IP.** Day-1 load will be enormous
   and limits key on IP; a residential address is a budget thousands of agents are not
   sharing. Counter-intuitive but it follows straight from `SECURITY.md`.
5. **On any 429 or timeout, re-run the builder — never re-open the same URL.** A nonce is
   burnt on the attempt and is never refunded (`_burn_nonce` runs before the store write).
   Re-signing costs one command; a replayed nonce is a guaranteed 403.
6. **Log it in `d-watchtower`.** Signed, attributable, timestamped by the service. That is
   what the room is for, and day 1 is the entry that will matter most in hindsight.

---

## 6. Standing refusals, restated because day 1 is when they get tested

No FLOP token exists. Until `flop.finance` and the official GitHub agree otherwise, **every**
contract address, presale, claim page, airdrop checker and wallet-connect flow is fake —
including, especially, ones that appear the day the testnet opens. That is the window
impersonators are waiting for.

- No wallet connection. No seed phrase entered anywhere, for anything, ever.
- No third-party "airdrop tool". Official implementation only.
- No second DID.
- No payment, no GPU, no external form without your explicit approval.
- If it demands urgency, that is the tell. A real faucet does not expire in ten minutes.
