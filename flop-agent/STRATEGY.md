# STRATEGY — updated 2026-08-27

## Pivot 2026-08-28: the key is the road, the repo is a detour

Session 1 proved the GitHub route works — issue #417 landed with named credit —
and in doing so proved it is not where the value is. Findings get absorbed by a
competing implementation within a day, 14 external contributors exist in total,
and none of it is confirmed to map to allocation. Meanwhile the one thing that
*is* reported to gate the faucet is the DID.

**Standing rule: maximise the DID's durable, attributable record. Treat GitHub as
opportunistic, and only ever with the implementation attached.**

The most scarce asset identified so far is an **owned `d-` room**
(`HANDOFF.md` §3.1): claimable once, at creation, by a signed claim that proves
key possession, after which only the owner's key can write to it. That is an
unforgeable activity log that cannot be bought later. Nothing else on this
service offers it.

## Current route ranking

| # | Route | Verdict | Why |
|---|---|---|---|
| 1 | **Agent** (DID + testnet readiness) | **ACTIVE** | Cheapest, earliest, and the only route whose main asset — a DID with continuous history — cannot be bought later. Reported faucet path runs through Technocore. |
| 2 | **Builder** (GitHub contributions) | **ACTIVE, selective** | The repo is the only public artefact Flop Labs maintains. Contributions are timestamped, verifiable, and attributable forever. Crowded (313+ PRs), so quality is the whole game. |
| 3 | **Creator** (Japanese-language) | **PREPARE, don't publish** | Genuinely uncontested niche. But zero official confirmation that content earns anything. Build the asset; publish only on the user's approval. |
| 4 | **Miner** | **DEFER — do not spend** | No client, no hardware spec, no scoring formula, no reward curve. Buying a GPU now is a bet on unpublished parameters. |
| 5 | **Validator** | **DEFER — do not spend** | Same, plus likely stake/permission requirements that do not exist yet. |

## Scoring the top candidates (0–5 per the evaluation function)

| | DID + readiness | GitHub contribution | JP content | GPU now |
|---|---|---|---|---|
| FLOP expected value | 4 | 3 | 2 | 1 |
| Official alignment | 5 | 5 | 3 | 1 |
| Early-participant edge | 5 | 4 | 4 | 1 |
| Hard to catch up later | 5 | 4 | 3 | 0 |
| Usefulness to network | 3 | 5 | 3 | 2 |
| Verifiability | 5 | 5 | 3 | 2 |
| Sybil resistance | 5 | 5 | 3 | 3 |
| Cost efficiency | 5 | 4 | 3 | 0 |
| Testnet connectivity | 5 | 3 | 2 | 2 |
| **Money cost** | none | none | none | **high** |
| **Risk** | low | low | low-med (SNS) | **high** |

## Measured correction — 2026-08-27: rooms vs notes

`lobby` runs at **~35 messages/second**, which puts its ring retention at roughly
**15–30 minutes** (`research/official/2026-08-27-lobby-throughput.md`). A message
posted there is not history; it is gone before anyone reads it.

So the durable surface is **notes, not rooms**:

- **DID note** (`/kv/did-64/776f70dbeec8e2`) — no ring, survives. This is the
  identity record that matters, and keeping it correct is the ongoing job.
- **A quiet room** retains far longer than `lobby`, but still dies after 7 idle
  days — continuity needs a periodic write, not a busy room.
- **`lobby` is for announcement, once.** Not for accumulating anything.

This removes the last reason to post frequently. It also means the anti-replay
window in `lobby` is ~1–3 minutes, so a signed URL for it is burned on use.

## Biggest opportunity right now

**Day-1 faucet readiness.** The faucet is reported to run through Technocore.
Almost everyone will meet it without a working signer, without a backed-up key,
and without knowing the nonce rule. We already have a tested signer that the
server's own verifier accepts. That advantage is real and it expires the moment
the testnet is a week old.

## Biggest risk right now

**Scams, by a wide margin.** No FLOP token exists. No contract, no presale, no
claim page, no wallet-connect flow is legitimate today — there is nothing to
connect to. A named launch date plus an absent token is the exact window
impersonators exploit, and a lookalike GitHub org already exists
(`flop-labs-dev`). Second risk: losing the DID seed, which is unrecoverable.

## Confirmed 2026-08-28 (Tier 8): the faucet is DID-gated

Press reports that **only agents with DID keys can access the testnet faucet**.
If that holds, the identity built here is the entry ticket to the one route that
is reported to decide allocation — and it is already published and verified.

Also reported: **the only stated qualification requirement so far is to follow
@flop_labs on X.** Five seconds, no downside; do it. Neither claim is Tier 1-2.

## Lesson taken 2026-08-28: file the implementation WITH the issue

#417 was reported without a PR, on the reasoning that CONTRIBUTING says to
discuss substantial changes first and that arriving with unsolicited crypto code
reads badly. In a repo taking ~313 PRs in two weeks that reasoning was wrong:
within a day someone else implemented it (#433), correctly, and a second party
(`antfleet-ops`) announced they would "carry in" the reporter's implementation.

The placement question that was held as blocking — core vs `scripts/` vs
`examples/` — was answerable by judgement. #433 chose the sibling script, which
was the obvious answer.

**New rule: when a finding already has a working, tested implementation, open
the issue and the PR together**, and say in the PR that it can be moved or
dropped if the maintainer prefers another shape. Restraint is not free here; it
costs the implementation. Politeness is not the currency — being first with
something correct is.

Unchanged: still no volume, still no duplicate PRs, still verify before filing.
Racing a PR that already exists and is correct is not speed, it is noise.

## What we deliberately are NOT doing

- No second DID, ever. One identity, continuous history.
- No message-count farming. `/rooms` publishes `zero_response_share` and
  `nick_diversity` specifically to expose it.
- No GPU spend before miner specs are published.
- No PR volume. Reproduce → root-cause → minimal fix → test, or don't file.
- No SNS posting, no public issue, no PR without explicit approval.
- **No posting the DID on X.** A signed Technocore write already proves key
  possession cryptographically; a tweet proves nothing, since anyone can paste
  any DID. It also permanently links the X account to the DID and places us
  inside the exact cluster a Sybil filter would train on. See
  `research/official/2026-08-28-x-posting-and-faucet-gate.md`.
- No third-party "airdrop tool" — official implementation only.

## Conditions that force a strategy rewrite

Re-rank immediately if any of these appear in Tier 1–5:

1. Testnet start date, client release, or faucet opening → **TESTNET DAY-1 MODE**.
2. Any published scoring / points / epoch / eligibility rule.
3. Confirmation that Technocore activity does or does not count toward the airdrop.
4. Miner or validator hardware and reward specs → run the ROI model, then advise.
5. Whitepaper, tokenomics, or the base chain being named.
6. Any official statement on Sybil rules or per-identity caps.
7. An official token contract address (until then: every one is fake).
