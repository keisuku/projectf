# How far ahead is "the top"? — measured 2026-08-27

Question: what is the actual gap between the leading participants and someone
starting today? Measured from primary sources, not vibes.

## Route 1 — Testnet activity (the one reported to decide the airdrop)

**Gap: exactly zero.** The testnet does not exist. No faucet, no client, no
registration, no points. Every participant on earth has the same score: none.

This is the route that is reported to determine allocation. Nobody is ahead.

## Route 2 — GitHub contribution to `flop-labs/technocore-chat`

Full history fetched and counted (`git rev-list`, `git log`):

| Metric | Value |
|---|---|
| Repo age | **14 days** (2026-08-13 → 2026-08-27) |
| Total commits on `main` | 73 |
| PR numbers referenced (PRs opened) | **~313** |
| Merged commits referencing a PR | 63 |
| Commits by the maintainer (Sergey Vidyuk) | 56 |
| **Commits by everyone else, ever** | **17** |
| **Distinct external contributors, ever** | **14** |
| **Most commits by any external contributor** | **2** |
| First external contribution | **2026-08-20 — 7 days ago** |
| Newest external contributors | 2026-08-26 — *yesterday* |

Read those last rows again. **The top outside contributor to this project has
two merged commits.** The distance from "nobody" to "top external contributor"
is two commits, and the first outsider only got in a week ago.

Implied acceptance rate: ~313 PRs opened, 17 external commits landed — on the
order of **5%**. The bar is quality, not timing. Volume is what fails.

## Route 3 — Technocore DID presence

No public leaderboard exists, so this is bounded rather than counted. From
upstream `src/config.py` (a maintainer's note on real production data):

> on technocore.chat the `did` namespace sat at 10,240 of 10,240 while the whole
> store was 6.7% full, refusing **3,068 of 3,417 identity writes in a 15-minute
> window from 1,585 distinct fingerprints**.

Three things follow:

1. **Population is large** — ~1,585 distinct DIDs in a single 15-minute window.
   Thousands to tens of thousands exist. Being "early by DID" is not a moat.
2. **~90% of those identity writes FAILED.** The legacy namespace was full and
   refusing. Most of that crowd does not have a published DID note at all.
3. The decisive line, same note, on the sharded path that fixes it:

   > it saw **2 writes out of those 3,417**, because the clients with the legacy
   > path baked in are not the ones re-reading the manual.

   **Two out of 3,417 — about 0.06% — used the correct sharded path.**

Our tooling writes `/kv/did-<2hex>/<14hex>` because it was built from
`src/patterns.md` §3 rather than copied from another agent. That is not an
advantage of timing; it is an advantage of having read the source.

Caveat: that measurement is from when the knob landed, not from today. Sharding
is now what the manual documents, so adoption has likely improved. The direction
holds; treat the exact ratio as historical.

## Honest summary

| Route | Where "the top" is | Distance from us |
|---|---|---|
| Testnet (pays the airdrop) | nowhere — does not exist | **0** |
| GitHub | 2 merged commits | **2 commits** |
| Technocore DID | thousands exist, ~90% failed to publish | days, and correctness beats age |
| Miner / Validator | no specs published | n/a — cannot be ahead |

**Nobody has a meaningful lead, because the scoreboard has not been switched on.**
The measurable races are small enough to enter in days.

## What this does NOT establish

None of these routes is confirmed to map to airdrop allocation. Only "testnet
activity" has been reported as the basis (Tier 8 press, not Tier 1–2), and it
does not exist yet. Everything above is positioning, not scoring.
