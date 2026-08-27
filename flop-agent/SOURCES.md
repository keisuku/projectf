# SOURCES — evidence tiers

Every claim in this repo carries a tier. **Never act on Tier 8+ alone.**

| Tier | Source | Reachable from the agent container? |
|---|---|---|
| 1 | flop.finance | **NO — egress-blocked** |
| 2 | github.com/flop-labs (`technocore-chat`) | YES (git clone + web) |
| 3 | @flop_labs (X) | NO (X needs a human) |
| 4 | Arthur Hayes / @CryptoHayes | NO (X needs a human) |
| 5 | technocore.chat (live service) | **NO — egress-blocked** |
| 6 | Flop Labs member statements | indirect |
| 7 | Official AMA / Spaces / YouTube | indirect |
| 8 | Reputable third-party press | YES (web search) |
| 9 | Community repos, Discord, forums | YES |
| 10 | Inference / our own guesses | n/a |

## Container network reality (verified 2026-08-27)

`flop.finance` and `technocore.chat` both return **403 at the egress proxy** —
an organisation network policy, not an outage. Verified via
`$HTTPS_PROXY/__agentproxy/status` (`connect_rejected`, `technocore.chat:443`).

Consequences, which shape the whole plan:

- Tier 1 and Tier 5 — the two most authoritative live sources — **cannot be read
  by the agent.** Anything sourced from press about them is Tier 8.
- **No write to Technocore can be performed from here.** Check-ins must be
  fetched by the human, from a device that can reach the host.
- This is a policy denial. It must not be worked around.

## Verified primary artefacts

- `flop-labs/technocore-chat` @ `9a7399d6bf2fdede60cebf54bdadbcfa5c04000c`
  (2026-08-27), v0.9.7. Read in full: `README.md`, `SECURITY.md`, `AGENTS.md`,
  `docs/design.md`, `src/didkey.py`, `src/store.py`, `src/patterns.md`,
  `scripts/sign.py`.
- Repo created **2026-08-13**; project announced **2026-08-18**. Today is day
  ~9 of public existence.

## Impersonation watch

`flop-labs-dev/technocore-chat` (created 2026-08-25, 0 stars) is a byte-identical
description clone of the official repo. **The official org is `flop-labs`.**
Treat every other org name as unverified.
