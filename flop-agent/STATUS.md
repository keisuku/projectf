# STATUS — 2026-08-30 (updated: d-bitflop claimed and held)

## Participation state

| Item | State | Note |
|---|---|---|
| Permanent DID | **CREATED** `did:key:z6Mk…9QDU` | Generated on the user's iPhone. Validated by upstream `didkey.public_key()`. |
| Seed backup | **DONE** (user-confirmed) | The one irreversible step, closed. |
| DID note published | **YES** `/kv/did-64/776f70dbeec8e2` | Durable (notes have no ring). Verified by fetch. |
| Signed check-in | NO | Blocked: same. URLs can be pre-built here. |
| Signing toolkit | **DONE, and proven on-device** | The phone has no `cryptography`; the pure-Python fallback is what actually runs there. |
| Testnet | **NOT STARTED** | No official start date. |
| Miner / validator | Deferred | No specs published. |
| GitHub contribution | **#417 landed in #433, credited by name** | Finding, verification and test design all shipped. Nothing outstanding. |
| DID note keepalive | **DUE ~2026-09-04** | Reaped after 7 idle days from the 2026-08-28 publish. `flopwatch.py keepalive --write`, or the ready URL in `technocore/READY-TO-RUN.md` §1. Needs no key. |
| Owned `d-` room | **CLAIMED `d-bitflop`** 2026-08-30T01:53:29Z | `signed by z6Mk…9QDU`. `/r/d-bitflop` now takes signed writes from our key only. |
| Room contents | **HELD — 3 messages, seq 1..3** | Past `STILLBORN_MESSAGES = 1`, so the 24-hour rule can never apply again. Only the 7-day idle clock remains. |
| Room keepalive | **DUE ~2026-09-06T03:07Z** | Then one signed write every 7 days, or the room *and* the ownership note go together. Needs the seed. |
| Mailbox (`mb-p-…`) | NOT PUBLISHED | After the room claim. `READY-TO-RUN.md` §3. |
| Toolkit vs upstream | **RE-VERIFIED 2026-08-30 @ `169ca89` (0.10.0)** | Both backends. Sweep proven identical over all 1,114,112 code points. Signatures accepted by the tightened `SIG_PATTERN`. |

## Why the DID was not generated in this container

Three facts together make generating it here strictly worse than generating it
on your own device:

1. **This agent runs in an ephemeral cloud container**, not on your phone. It is
   reclaimed after a period of inactivity. A seed written here dies with it
   unless exported — and exporting a permanent private key through a chat
   transcript is exactly what your own rules forbid.
2. **technocore.chat is egress-blocked from here.** The DID cannot be published
   and the check-in cannot be sent from this container. So a DID generated here
   would gain **zero** history today — there is no early-age advantage to lose.
3. Therefore deferring costs nothing and avoids your permanent identity ever
   existing on hardware you do not control.

The toolkit is committed to git, so it survives this container. You run one
command locally and the identity is yours from birth.

## Blocked on the human

Every remaining item needs a device that can reach `technocore.chat`. The exact
commands and URLs are in `technocore/READY-TO-RUN.md`.

1. **Refresh the DID note** before ~2026-09-04. Needs no key — give it to the PC.
2. **One substantive signed write to `d-bitflop`** before ~2026-09-06T03:07Z,
   and every 7 days after. Needs the seed. Content policy: `STRATEGY.md`.
3. Publish a `mb-p-d-bitflop` pointer in the DID note, so the room is
   discoverable from the identity record.

Closed: the key is generated, the seed is backed up, the DID note is published
and verified, and `d-bitflop` is claimed.

## Two recurring obligations, both 7 days, on different objects

| Object | Refreshed by | Needs the seed? | Next due |
|---|---|---|---|
| DID note `/kv/did-64/776f70dbeec8e2` | any write to it (unsigned lane) | no | ~2026-09-04 |
| Room `/r/d-bitflop` + its ownership note | a signed write to the room | **yes** | ~2026-09-06T03:07Z |

Writing to one does **not** refresh the other. Measured, not assumed:
`research/official/2026-08-30-owned-room-retention.md`.

## Verified 2026-08-30 (session 2)

- Upstream re-read at `169ca89`, version `0.10.0` — ten commits past the baseline.
  Full delta: `research/official/2026-08-30-upstream-0.10.0-delta.md`.
- **0.10.0 tightened the signature encoding** (`SIG_PATTERN` now ends `[AQgw]`), so a
  non-canonical signer 403s. Ours was already canonical: 3000/3000 accepted, all four
  canonical tails observed.
- **The sweep is identical, proven not sampled**: every Unicode code point
  (1,114,112), 20,000 random strings, and the 4095/4096/4097 cap boundary, all compared
  against upstream `store.clean_text()`. Zero mismatches.
- **The full `d-` claim was rehearsed against the real upstream app** in-process, on a
  throwaway store and an RFC 8032 test key: the claim lands, unsigned writes are
  refused, a stranger's signed write is refused, a stranger's re-claim is refused, the
  stored record re-verifies offline, and the room exports.
  (`technocore/scripts/rehearse_claim.py` — committed, re-runnable.)
- **The DID note cannot be protected.** `app.py _note_write_gate` accepts signed note
  writes for `room-owners` and `room-allow` only; every other namespace is
  world-writable by design and 400s on the signed lane. The DID note is a pointer, not
  evidence — which is what makes the owned room the only durable, attributable surface.
- **No testnet signal.** The `flop-labs` org still has exactly one repository; every
  watch word in the repo's docs is an incidental hit. Latest tag `v0.9.7`.
- `technocore.chat` and `flop.finance` re-tested: still `connect_rejected` (403) at the
  proxy. A policy denial, not worked around.

## Verified 2026-08-27 (session 1)

- Official repo identified and read at `9a7399d6` (v0.9.7).
- Protocol implemented and cross-checked against upstream `didkey.verify()` —
  the exact function the server runs — including tamper and wrong-text rejection.
- Sweep verified byte-identical to upstream `store.clean_text()`.
- `.gitignore` verified to exclude every secret path by actual `git check-ignore`.
- No key material exists anywhere in this repo.
