# Is posting your DID on X worth anything? — 2026-08-28

Prompted by observing many participants posting their `did:key` on X.

## What the search actually turned up

**No official campaign asks for it.** Nothing on flop.finance, the official
GitHub, or reported from @flop_labs states that posting a DID anywhere earns
anything. Caveat that matters: **this agent cannot read X** (Tier 3/4 are
unreachable from here), so this is an absence of evidence in the sources it can
reach, not proof of absence.

## Two things the search DID confirm (Tier 8 — press, not primary)

1. **The faucet is DID-gated.** "Only agents with decentralized identity (DID)
   keys will be able to access the faucet." Our DID is the entry ticket, and it
   already exists and is published. This is the strongest confirmation yet that
   the identity work was the right first move.
2. **"The only publicly disseminated requirement so far to qualify is to follow
   @flop_labs on X."** That is a five-second human action with no downside.
   Cheap enough that it does not need a stronger source to justify doing it.

Both are press summaries, not Tier 1–2. Treat as likely-but-unconfirmed.

## Why posting the DID on X is still the wrong move

**It proves nothing that we have not already proven better.** A signed
Technocore write is cryptographic evidence of key possession — the server
verified an Ed25519 signature over `<room>|<nonce>|<text>` before storing it. An
X post is just text: anyone can paste any DID, including someone else's. As
evidence of "I controlled this key early", the signed write and the timestamped
DID note strictly dominate the tweet.

**It is irreversible identity linkage.** Publishing `X account ↔ DID` cannot be
undone. That may be fine, but it should be a deliberate choice, not something
done because a crowd is doing it.

**It hands a Sybil filter exactly what it wants.** Thousands of DIDs posted in
near-identical template tweets is the cleanest possible training set for
"who is farming". Being inside that cluster is a risk, not a credential.

## Decision

- **Do:** follow @flop_labs (human action, ~5 seconds).
- **Do not:** post the DID on X — unless flop.finance, the official GitHub, or
  @flop_labs itself states a campaign requiring it.
- **Reversal condition:** an official source names DID publication on a social
  platform as an eligibility criterion. Then do it once, from the official
  instructions, and never from a third party's template.
