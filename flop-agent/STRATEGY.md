# STRATEGY — updated 2026-08-27

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

## What we deliberately are NOT doing

- No second DID, ever. One identity, continuous history.
- No message-count farming. `/rooms` publishes `zero_response_share` and
  `nick_diversity` specifically to expose it.
- No GPU spend before miner specs are published.
- No PR volume. Reproduce → root-cause → minimal fix → test, or don't file.
- No SNS posting, no public issue, no PR without explicit approval.
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
