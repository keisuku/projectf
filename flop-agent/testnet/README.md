# Testnet

**Status: NOT STARTED.** No official start date. (Press reports airdrop targeted
Q4 2026, genesis Q1 2027 — neither confirmed by a Tier 1–2 source, neither final.)

## Why this is the main event

Airdrop allocation is reported to be based on **testnet activity** — not on
Technocore chat activity. If that holds, the hours after the faucet opens matter
more than every day before it combined.

## Day-1 readiness checklist

| | Item | State |
|---|---|---|
| ☑ | Permanent DID exists | `did:key:z6Mk…9QDU` |
| ☑ | Seed backed up | user-confirmed |
| ☑ | Signer works, verified against upstream | done |
| ☑ | Runs with no dependencies (phone-capable) | done |
| ☑ | Nonce monotonicity handled | done |
| ☑ | DID note published | `/kv/did-64/776f70dbeec8e2`, verified |
| ☐ | **Weekly keepalive** — the note is reaped after 7 idle days | `flopwatch.py watch --write-keepalive` |
| ☑ | Watch established for faucet/testnet announcements | `technocore/scripts/flopwatch.py` |

## Trigger conditions for TESTNET DAY-1 MODE

Any of: a start date, a client release, a faucet endpoint, agent registration
opening, or published scoring/points/epoch rules — from Tier 1–5.

On trigger: stop routine work, re-read the official rules **before acting**, and
produce a priority-ordered plan for the first 24 hours.

## Standing rule for testnet participation

Read what is actually being scored before generating any load. If rewards track
useful work — genuine workload, quality, diversity, uptime, verified compute —
then generating junk inference is both against the rules and a waste of the
budget. The plan is to run the real agent workload described in the root README
and let that be the activity.
