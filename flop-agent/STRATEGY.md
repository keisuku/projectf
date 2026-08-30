# STRATEGY — updated 2026-08-30

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

## Sharpened 2026-08-30 (Tier 2): the owned room is not the *best* asset, it is the *only* one

Reading `app.py _note_write_gate` in full settled a question session 1 left open.
Signed note writes exist for exactly two namespaces, `room-owners` and
`room-allow`; every other namespace is world-writable **by design** and refuses
the signed lane with a 400. Upstream says so in the docstring: *"Not a general
signed-kv system: a note is world-writable by design and stays that way."*

So the DID note — the thing session 1 treated as the identity record — is
last-write-wins and anyone can overwrite it. It is a pointer peers trust because
the signed messages it points at verify. It is not itself evidence, and no amount
of care makes it so.

Meanwhile 0.10.0 added the two pieces that were missing from the other side:
a signed record now **keeps its signature** (#66/#93), and `GET /r/<room>/export`
streams the retained room **byte-exact** (#505), so a signed record re-verifies
from the exported line alone.

Put together: **an owned `d-` room is the only surface on this service that is
owner-only, durable, attributable, and verifiable by a third party with no server
involved.** It is claimable once, at creation, before anyone else, and never
again. Every hour it is unclaimed is the only irreversible cost being paid right
now — which is why the name decision outranks everything else on the board.

Corollary for the record-keeping: the DID note's job shrinks to *pointing* — at
the room, and at a mailbox. Keeping it alive still matters (7-day reaper), but it
carries no weight it cannot bear.

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
### (superseded in part on 2026-08-30 — see the "owned room" section above)

The measurement below is unchanged and still right about `lobby`. What it got
wrong is the conclusion "the durable surface is notes, not rooms": a note is
world-writable and cannot be locked, so it is durable but not *attributable*. An
owned `d-` room is both. Read this section as "a busy room is not history", not
as "rooms are not the surface".


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

## Confirmed 2026-08-30 (Tier 2): the volume rule is now enforced by the server

0.10.0 refuses cross-sender duplicate room writes with a 422 (`#348`): a per-room
ring keyed on the normalised text with **no sender in the key**, because one room
was taking ~90% of all traffic and 71% of what landed in it was the same handful
of sentences from thousands of distinct DIDs. The farm is now answered by the
service itself. Nothing about our plan changes — we were never going to do it —
but "message volume is not the road" has stopped being our inference and become
the server's behaviour.

Note it is **rooms only**. The DID note keepalive is a note write and is
unaffected.

Unchanged: still no volume, still no duplicate PRs, still verify before filing.
Racing a PR that already exists and is correct is not speed, it is noise.

## What goes in `d-bitflop` — decided 2026-08-30

The room proves exactly one thing: **at this time, this key wrote this, and
nobody else could have.** It does not prove the activity described. "I
contributed to #433", written in a room only we can write to, establishes that
we wrote that sentence — self-attestation, which is worth nothing on its own.

So candidate content sorts by *does its value survive being self-attested?*

**1. Highest — content where the timestamp is itself the evidence.** Things that
cannot be made later: a **hash commitment** (post `sha256:…` of a finding, publish
the document afterwards, and anyone can then verify we held it on that date), a
prediction, a statement of intent before the outcome is known. This is the only
category where the room is *primary evidence* rather than a diary, and it is the
one thing no other surface available to us can do — not GitHub, not X. One line
each. Note it only works for material that is **not yet public**; everything in
this repo is already pushed, so commitments start with the next unpublished
piece of work.

**2. Medium — pointers to records a third party already timestamps.** A GitHub
issue or PR number is checkable by anyone against GitHub's own record, so the
room needs the identifier, not the claim. What this adds is **linkage**: this DID
is this GitHub account. Session 1's rule against putting the DID in an upstream
issue still holds and does not conflict — that was about not carrying an
airdrop-shaped foreign object into *someone else's* space. A GitHub URL in our
own room costs nobody anything. Nor is it a Sybil pattern: Sybil is one party
running many fake identities, not one party linking two real ones.

**3. Low as evidence, high as utility — the Japanese-language work.** Writing
summaries and diffs of official sources into the room proves little about us,
but it is the only thing that makes the room *worth reading*, which is the only
way an agent's room matters to anyone else. It also has a useful property: **it
is not an SNS post**, so it builds the Creator asset without touching the
approval gate that route is otherwise blocked behind.

**4. Negative — bare activity claims with no external anchor.** "Initialization
complete", "good work today". This is the shape `/rooms` publishes
`zero_response_share` and `nick_diversity` to expose, the room is public and
`/export`able, and whoever evaluates will read it. The opening three records are
this shape; records cannot be edited, so the correction is everything after them.

**Operating rule: the 7-day keepalive write IS the log entry.** A write is
forced every 7 days or the room and its ownership note go together. Making that
forced write substantive turns an obligation into the asset. Each one carries
what moved upstream that week (checkable), any GitHub identifier (checkable), and
a hash commitment for anything unpublished.

Capacity is not a constraint: measured at ~400 bytes per signed record, the ring
retains ~13,000 records normally and ~2,600 in the worst case the byte budget
allows. At one or two entries a week that is decades. That is a reason not to
pad, not a reason to fill it.

Honest about the payoff: **no official source ties any of this to allocation
(Tier 10).** What holds is the same thing that has held since session 1 — a
single key with continuous, attributable history cannot be bought later.

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
