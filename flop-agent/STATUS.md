# STATUS — 2026-09-02 (updated: handoff to the d-bitflop executor; production write gate)

**Read the repository-root `HANDOFF.md` first.** Since 2026-09-03 (JST) this project runs
under that handoff: commander (Claude chat) → executor (Claude Code, this repo) → Codex
via GitHub Issues/PRs only → Opus audit. Every production write now goes through the
three-factor gate in `flopdid.py` (`technocore/README.md` § Production write gate).

## The clock (UTC; JST = UTC+9)

| Object | Last write (verified) | Reaped after | Due | Needs |
|---|---|---|---|---|
| Room `/r/d-bitflop` + its ownership note | **2026-08-30T03:07:24Z** (seq 3) | 7 idle days | **2026-09-06T03:07Z** (12:07 JST) | the seed → the phone, through the gate |
| DID note `/kv/did-64/776f70dbeec8e2` | 2026-08-28 (publish; any later refresh is **unverified**) | 7 idle days | **~2026-09-04** | public DID only |

The container still cannot read either object (`technocore.chat` is egress-blocked,
re-verified 2026-09-02 at the proxy: `connect_rejected`). Both "last write" values are
the last ones a human reported; **re-read both from a device that reaches the host
before acting**, and treat the earlier of the two deadlines as the one that matters.

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
| Toolkit vs upstream | **RE-VERIFIED 2026-09-02 @ `01c49fb` (v0.11.4)** | Both backends, `selftest_upstream.py` and `rehearse_claim.py` green; `didkey.py` and `clean_text()` unchanged since `169ca89`. `research/official/2026-09-02-upstream-0.11.4-delta.md`. |
| Production write gate | **IMPLEMENTED 2026-09-02, PR open for Codex review** | `--fetch` to a non-loopback host needs `--production` + a one-time `--approval` file (body SHA-256) + a TTY confirmation; no env override; proof.log + `/export` snapshot per write; redirects refused. 53 tests (Codex review rounds 1-3 addressed). E2E green against a local v0.11.4 server through a non-loopback address. |
| Local E2E | **REPRODUCED 2026-09-02** | Real upstream server (uvicorn, v0.11.4, Python 3.12): claim → 2 signed says → JSON read → export → offline re-verify with upstream `didkey.verify()`; unsigned write 403. |
| Codex Phase 1 code (`d-bitflop run-once`, RECON.md, 9 tests) | **NOT IN THIS REPOSITORY** | Not on any branch, not in any Issue/PR (checked 2026-09-02). Blocked on the human supplying its location (`HANDOFF.md` §9.1). |

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

1. **Re-read the room and the note** (`curl` of `/r/d-bitflop?format=json` and
   `/kv/did-64/776f70dbeec8e2`) and report message count, `generation`, `last_seq`,
   the last `ts`, and whether the note still holds our DID. No key needed.
2. **Refresh the DID note** before ~2026-09-04. Needs no key. (Decision pending from
   the commander: whether this standing, content-fixed write is authorised as a routine
   or must also pass the approval gate — see the Phase 1 report.)
3. **One signed write to `d-bitflop` before 2026-09-06T03:07Z, through the gate**, with
   the body the commander approves from the three candidates in
   `reports/2026-09-02-phase1-handoff-report.md`. Needs the seed → the phone.
4. **Tell the executor where Codex's Phase 1 code lives** and how the key is supplied
   (the handoff says `identity.pem` + passphrase; this repository's toolkit uses a
   32-byte hex seed file — the two must be reconciled before `run-once` can be tried).
5. Publish a `mb-p-…` pointer in the DID note, so the room is discoverable from the
   identity record (unchanged, lower priority).

Closed: the key is generated, the seed is backed up, the DID note is published
and verified, `d-bitflop` is claimed and held, and production writes are gated.

## Two recurring obligations, both 7 days, on different objects

| Object | Refreshed by | Needs the seed? | Next due |
|---|---|---|---|
| DID note `/kv/did-64/776f70dbeec8e2` | any write to it (unsigned lane) | no | ~2026-09-04 |
| Room `/r/d-bitflop` + its ownership note | a signed write to the room | **yes** | ~2026-09-06T03:07Z |

Writing to one does **not** refresh the other. Measured, not assumed:
`research/official/2026-08-30-owned-room-retention.md`.

## Verified 2026-09-02 (session 3 — handoff)

- Upstream re-read at `01c49fb` (v0.11.4, 2026-09-02), 21 commits past `169ca89`. No
  commit touched `src/didkey.py`; `store.clean_text()`, `NAME_RE`, `IDLE_SECONDS`,
  `STILLBORN_*` and the ownership namespaces are unchanged. `patterns.md` gained §6
  (the tclk/1 escrow convention) in 0.11.3. Detail:
  `research/official/2026-09-02-upstream-0.11.4-delta.md`.
- `selftest_upstream.py` and `rehearse_claim.py` pass against that head on both
  backends (cryptography 50.0.0 / PyNaCl 1.6.2 under Python 3.12; pure-Python under 3.11).
- **Local E2E against a running upstream server** (not in-process): claim, two signed
  says, JSON read (`generation`, `seq`, `nonce`, `sig`), `/export` with
  `X-Room-Generation`, unsigned write refused 403, every exported line re-verified
  offline with upstream `didkey.verify()`.
- **Production write gate** implemented in `flopdid.py` and driven end-to-end through a
  non-loopback address at the same local server: refused without `--production`, refused
  without a TTY, refused on a wrong confirmation, accepted with all three; the approval
  file was consumed on send and refused on reuse; `proof.log` carries raw body, swept body,
  canonical bytes (hex), nonce, signature, approval, HTTP outcome, the server-assigned
  `(generation, seq, ts)` and the export snapshot's path and SHA-256.
- A latent defect fixed on the way: a broken `cryptography` build (missing
  `_cffi_backend`, pyo3 panic — the state of this container's Python 3.11) was read by
  `_verify_own` as "our signature does not verify" and refused every emit. A verifier is
  now probed on the RFC 8032 vector before it is allowed a verdict.
- `flop-labs/tclk` cloned at `81a8346` (v0.1.0 + 5, "reject contradictory receipt
  outcomes (#7)") for Phase 2; not yet read in depth.
- **Not found anywhere**: Codex's Phase 1 deliverables. Branches, Issues and PRs of
  `keisuku/projectf` checked; the only unmerged branches are the two Claude Opus 5 lines
  (`claude/status-check-and-execute-u39wxk`, now the base of this work, and
  `claude/flop-agent-d-room-claim-2vkyp7`, the abandoned `d-watchtower` line).
- The repository is **public**, not private as `HANDOFF.md` §5.1 states.
- `technocore.chat` and `flop.finance`: still `connect_rejected` at the proxy. Not
  worked around; the human's device performs every read and write.

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
