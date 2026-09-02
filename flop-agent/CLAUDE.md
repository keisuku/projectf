# CLAUDE.md — operating rules for this project

This directory is the **single source of truth** for FLOP participation.

## Startup routine (every session, in order)

-1. **Read the repository-root `../HANDOFF.md` first** — the d-bitflop handoff
   (2026-09-03). It defines the current roles (commander / executor / Codex via
   GitHub only / Opus audit), the absolute prohibitions, the production-write
   approval gate, and the task order. Where it and the documents below disagree,
   it wins.
0. **Read `HANDOFF.md` (this directory) next.** It carries the reframing that matters: the DID is
   the main road, GitHub is a side road, and the lessons that were expensive to
   learn. Do not re-derive them.
1. Read `STATUS.md`, `STRATEGY.md`, `CONTRIBUTIONS.md`, latest `DAILY_BRIEF.md`.
2. Re-check official sources by tier (`SOURCES.md`). State plainly which were
   reachable and which were not. **Never present stale data as current.**
3. Diff against the last recorded baseline in `research/official/`. Prioritise
   anything that changes expected FLOP value.
4. Re-evaluate all routes, but with the standing ranking from `HANDOFF.md` §1:
   **what the key does** outranks what the GitHub account does. Ask first what
   would make the DID's record more durable, more attributable, or more ready for
   the faucet — and only then whether anything else is worth the hours.
5. Lead with the `FLOP DAILY` block. Detail after, not before.

Do not continue a previous plan on momentum. If the facts moved, the plan moves.

## Hard rules

**Secrets.** The Ed25519 seed is never displayed, never printed to stdout, never
committed, never logged, never sent to any external service or model — including
me. `secrets/` is mode 700, the seed file 600, and both are gitignored. If a task
appears to require revealing the seed, stop and explain instead.

**Approval required** before any of: posting to SNS, opening a public issue or
PR, submitting an external form, any payment, any wallet action, any GPU
contract, or sending anything to an external service.

**Autonomous** without asking: reading official repos and docs, local analysis,
writing code and tests, structuring this repo, diffing upstream, drafting
proposals, updating these documents.

**Never**: create a second DID, farm message counts, spam, fake engagement, evade
a rate limit or CAPTCHA, use an unofficial airdrop tool, or work around a network
policy denial.

## Evidence discipline

Tag every claim with its tier. Keep official fact and inference visibly separate —
in this repo, inference is labelled Tier 10 and says so in the text. If a source
could not be reached, record that it could not be reached.

## Environment note

The agent may run in an **ephemeral cloud container**, not on the user's device.
It is reclaimed after inactivity, and `flop.finance` / `technocore.chat` are
egress-blocked from it. Anything that must persist goes into git. Anything that
must touch Technocore is handed to the human as a ready-to-fetch URL.

## Output format

Open with:

```
FLOP DAILY
現在の状態：
DID：OK / NG
Technocore：OK / NG
Testnet：未開始 / 開始
重要変更：あり / なし
今日の最適行動
S+： ...
S：  ...
A：  ...
今日はやらない： ...
理由： ...
```

Then detail. Short first, depth after.
