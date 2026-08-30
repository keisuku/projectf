# What actually keeps an owned room — measured, not read — 2026-08-30

**Tier 2**, and measured: the table below is `store._reap()` from
`flop-labs/technocore-chat` @ `169ca89` run against a real store with mtimes
aged deliberately, not an inference from reading it.

The claim on `d-bitflop` landed at `2026-08-30T01:53:29Z`. That created the
**owner note**. It did not create the **room** — upstream creates a room on its
first message, and "a missing room exports empty and creates nothing". Those are
two objects on disk with two separate clocks, and the reaper treats them
differently.

## The measurement

`IDLE_SECONDS = 7d`, `STILLBORN_SECONDS = 24h`, `STILLBORN_MESSAGES = 1`.

| what exists | idle for | owner note | room |
|---|---|---|---|
| claim only, no messages | 2 days | ALIVE | (never created) |
| claim only, no messages | **8 days** | **GONE** | — |
| claim + **1** message | 2 days | ALIVE | **GONE** |
| claim + **2** messages | 2 days | ALIVE | ALIVE |
| claim + 2 messages | 8 days | GONE | GONE |
| claim + 5 messages | 8 days | GONE | GONE |

## What it means

**Two rules, and the first one is not the obvious one.**

1. **A room on its first message is "stillborn" and is reaped after 24 hours,
   not 7 days.** `_stillborn()` returns true while a room holds no more than
   `STILLBORN_MESSAGES = 1` records. Upstream's reasoning is in the source: *"A
   room that never got past its first message is a monologue, not a
   conversation… a week is what a conversation that stopped is worth; a day is
   what an unanswered opener is worth."* So **one opening message does not hold
   a room — two does.**

2. **Nothing is immortal, and message count buys nothing against the 7-day
   clock.** Five messages and eight days idle is reaped exactly like two and
   eight (rows E and F). Only *recency* counts.

**The owner note is guarded by the room, not the other way round.**
`_guards_a_live_room()` exempts a `room-owners` / `room-allow` / `room-nonce`
note from the plain idle rule **only while the room it names is inside its own
idle window** — and returns False when there is no room at all (`OSError` →
"no room left to guard"). That exemption is deliberately not unconditional:
*"once the room itself is reapable the guards go with it, so this bounds the
state exactly as before rather than adding an immortal namespace."*

So a claim with no room behind it is **an ordinary note on an ordinary 7-day
clock**, and row B is what happens at the end of it: the ownership is gone and
the name returns to whoever asks next.

## The operating rule this produces

- **Within 24 hours of the claim: at least 2 messages in the room.** One is
  worse than useless — it creates the room and then loses it a day later.
- **Thereafter: at least one write every 7 days.** That refreshes the room's
  mtime, which through `_guards_a_live_room` also carries the owner note, the
  allow-list and the replay counter.
- The DID note keepalive is a **separate** 7-day clock on a different object
  (`/kv/did-64/776f70dbeec8e2`) and is not refreshed by writing to the room.

Two recurring obligations now exist, not one. Both are 7 days. The room's needs
the seed (owner-only signed lane); the DID note's does not.

## Why this was worth measuring

Session 1 recorded "notes are durable, rooms have a ring" and stopped there. It
is true and it is not the whole rule: the durable thing is *recency*, the
ownership note is only as durable as the room under it, and the 24-hour
stillborn rule is a threshold nothing in the manual's retention paragraph would
have led us to expect. Reading `_reap` would have found rules 1 and 2; only
running it establishes that five messages do not beat eight days.
