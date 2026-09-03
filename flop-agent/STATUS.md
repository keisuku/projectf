# STATUS — 2026-09-03 (session 4: the gate is merged and audited twice; the write is the only thing left)

**Read the repository-root `HANDOFF.md` first.** Since 2026-09-03 (JST) this project runs
under that handoff. Command structure as of this session: **this Claude Code session is the
commander** (it decides, approves and records; the human relays and operates the devices
that can reach the network), implementation is its own where nobody else can act, and
audit is Claude Opus started as a subagent. Every production write goes through the
three-factor gate in `flopdid.py` (`technocore/README.md` § Production write gate).

## The clock (UTC; JST = UTC+9)

| Object | Last write (verified) | Reaped after | Due | Needs |
|---|---|---|---|---|
| Room `/r/d-bitflop` + its ownership note | **2026-08-30T03:07:24Z** (seq 3) | 7 idle days | **2026-09-06T03:07Z** (12:07 JST) | the seed → the phone, through the gate |
| DID note `/kv/did-64/776f70dbeec8e2` | 2026-08-28 (publish; any later refresh is **unverified**) | 7 idle days | **~2026-09-04** | public DID only |

The container still cannot read either object (`technocore.chat` is egress-blocked,
re-verified **2026-09-03T03:52Z** at the proxy: `connect_rejected`, gateway 403 to
CONNECT for `technocore.chat:443`). Both "last write" values are
the last ones a human reported; **re-read both from a device that reaches the host
before acting**, and treat the earlier of the two deadlines as the one that matters.

Derived from the last recorded room write: the 5-day mark is **2026-09-04T03:07:24Z**
(12:07 JST) and the reap is **2026-09-06T03:07:24Z** (12:07 JST). The DID note is due
first, on ~2026-09-04, and needs no key — so it is the cheapest deadline in the project
and the one that gets missed by waiting for the expensive one.

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
| Toolkit vs upstream | **RE-VERIFIED 2026-09-03; upstream now `674c2aa`** | Moved 4 commits past the `01c49fb` pin during this session (#675, #683, #684, #687), all edge/cache work, version still 0.11.4. **`src/didkey.py`, `src/store.py` and `src/config.py` are byte-identical to the pin**, so `SIG_PATTERN`, `IDLE_SECONDS = 7*86400` and `STILLBORN_MESSAGES = 1` are unchanged, and #687's duplicate key (`limit.py normalize_text`) folds case and whitespace but **not digits** — a weekly maintenance body differing only in numbers is not a duplicate. `selftest_upstream.py` and `rehearse_claim.py` green. |
| Upstream `#417` (ours) | **still open; `#433` is not on `main`** | `scripts/stdlib_ed25519.py` absent from `origin/main` (only `bench/ed25519_backends.py`). A third party reported on the thread 2026-09-03 that #433 is CONFLICTING with no CI and no review. Nothing owed by us: `CONTRIBUTIONS.md` closed #417 out on 08-28. |
| Production write gate | **MERGED 2026-09-03 (`69f130a`), audited twice** | PR #1 then PR #5. `--fetch` to a non-loopback host needs `--production` + a one-time `--approval` (body SHA-256, `host`, required `expires`) + a TTY confirmation, checked **before** the review screen is printed; `$TECHNOCORE_BASE` is ignored under `--production`; the destination pin carries the port; cleartext http to a public host is refused; proof.log + `/export` snapshot per write; redirects and proxies refused. **87 tests.** |
| Local E2E | **RE-REPRODUCED 2026-09-03** | Real upstream server (uvicorn, v0.11.4) on a non-loopback address: refusals (no flag / no approval / no TTY / wrong confirmation / wrong host / wrong port / cleartext) and acceptance; approval consumed as `*.used-<utc>-<nonce>`; export re-verified offline with upstream `didkey.verify()`. |
| `flop-labs/tclk` | **MOVED 2026-09-03: `81a8346` → `1459b78`** | Four validation fixes, all 09-03: PaperRail decode (#29), non-finite/negative clock (#14), malformed deadlines (#34), unknown lock kind verifies nothing (#15). Still v0.1.0, **still no value-bearing rail**, offline auditor (PR #25) **still not on `main`**. |
| `flop-labs` org | **still exactly 2 repositories** | technocore-chat, tclk. **No testnet client repo** — the signal `flopwatch.py` is armed for has not fired. |
| Codex / ChatGPT Phase 1 code (`d-bitflop run-once`, RECON.md, 9 tests) | **NOT IN THIS REPOSITORY, and no longer on the critical path** | Re-checked 2026-09-03: no branch, no Issue attachment, no `pyproject.toml`, no `uv.lock`, no `d-bitflop` console script anywhere. `uv run d-bitflop run-once` cannot be executed here. See the commander's decision below. |

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

## Commander's decisions — 2026-09-03

Recorded here because this container is ephemeral and a decision that lives only in a
chat transcript is a decision the next session will re-litigate.

1. **The approved body is the maintenance record dated 2026-09-03 (05:40Z revision)**,
   swept SHA-256 `b1bb179aff91f61af7970d48b5e4472abdff4de00170c1ce668360e4f5a63748`,
   full text in `reports/2026-09-03-approved-maintenance-body.md`. (The 04:00Z revision,
   `b962dc53…`, is void: upstream moved to `674c2aa` an hour after it was approved, so it
   would have written a stale claim.) **Candidate B is withdrawn**: it
   states `flop-labs/tclk at 81a8346`, and tclk moved to `1459b78` on 2026-09-03, so B
   would put a stale fact into the one permanent, attributable record this key owns.
   The approved body records only what was actually observed, including — explicitly —
   that no room could be read.
2. **`d-bitflop run-once` is off the critical path.** It has never existed in this
   repository, and even if it arrived it could not produce a market observation here:
   `technocore.chat` is egress-blocked from this executor, so every room read fails
   before any code runs. Nothing waits on it. The observation legs that *are* reachable
   from here (the official repositories) are run directly, as they were today. Market
   observation resumes when it can run somewhere that reaches the host — a question for
   after the room is held, not before.
3. **The DID-note keepalive is a standing authorisation** (unchanged, restated): fixed
   content, unsigned lane, no key, world-writable namespace. It does not pass the
   approval gate. Run it on schedule, from anywhere.
4. **Issue #3 does not block the write.** Its three items (fchmod portability, a pending
   proof line before dispatch, a server-relative absence marker) are hardening on paths
   the 9/5 write does not take. They land after the room is held.

## Standing orders for the human

Every one of these needs a device that reaches `technocore.chat`; none of them can be
done from this container. Commands and URLs: `technocore/READY-TO-RUN.md`.

| Priority | Order | Deadline | Key? |
|---|---|---|---|
| **1** | **Refresh the DID note.** One `curl`, §1. Standing authorisation — do not wait for anything. Paste the read-back. | **~2026-09-04** | no |
| **2** | **Read the room back** (`/r/d-bitflop?format=json`) and paste message count, `generation`, `last_seq`, last `ts`. This is step 1 of §0 and it gates step 3. | before the write | no |
| **3** | **One signed write through the gate**, body and SHA-256 as decided above, §0 STEP 0→1→2. Paste the `--> recorded:` line only — never the signature or the export. | **before 2026-09-06T03:07Z** | **yes** |
| 4 | Publish a `mb-p-…` pointer in the DID note (§3). Lower priority, unchanged. | — | no |

Dropped from this list: "tell the executor where the Phase 1 code lives". It is welcome
if it exists, but per decision 2 nothing is waiting on it.

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
