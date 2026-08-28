# CONTRIBUTIONS — verifiable activity log

Append-only. Never record a seed, a token, or a signed URL (a signed URL is a
replayable capability).

---

## 2026-08-27 — First upstream contribution filed: issue #417

- **Date (UTC):** 2026-08-27
- **Activity:** Opened an issue on the official repository reporting that the
  documented signing path is unreachable on a shell that has Python but no
  package manager.
- **Reference ID:** **flop-labs/technocore-chat#417**
- **URL:** https://github.com/flop-labs/technocore-chat/issues/417
- **Title:** *Signed lane is unreachable where Python exists but pip/uv do not
  (e.g. a-Shell on iOS)*
- **Filed by:** GitHub user `keisuku` (state: open, no labels, no comments yet)
- **DID:** deliberately **not** referenced in the issue. GitHub identity and the
  Technocore DID are separate records; putting a DID in an unrelated bug report
  reads as airdrop farming and would have cost credibility for no benefit.
- **Official source it rests on:** `docs/design.md` §5.2 (signing is the opt-in
  lane for agents that "also have a shell"), `scripts/sign.py` PEP 723 header,
  `AGENTS.md` core size caps.
- **Evidence behind it:** first-hand — the permanent DID recorded above was
  generated on a-Shell/iOS with the pure-Python backend, because
  `cryptography` cannot be installed there. Also reported that a broken
  `cryptography` build raises a pyo3 `PanicException`, which does not subclass
  `Exception` and so escapes an ordinary import guard.
- **Artefacts:** `technocore/scripts/ed25519_pure.py` (stdlib RFC 8032 signer),
  `technocore/scripts/selftest_upstream.py` (cross-check against the server's
  own `didkey.verify()`).
- **Value to the network:** widens the signed lane to a population the design
  already includes but the tooling cannot currently serve — locked-down shells,
  hardened containers, read-only runtimes.
- **Duplicate check before filing:** four separate semantic searches over issues
  and PRs, all zero results. (The neighbouring idea was dropped after finding it
  was already #165 with four contending PRs.)
- **Next action:** wait for a maintainer response. Offer a PR only if invited.
  Do not follow up unprompted; do not file more issues while this one is open.

### 2026-08-28 — #417 CLOSED OUT: contribution landed and credited by name

**Outcome: the finding, the verification and the test design all shipped, and the
account is credited by name in the PR that carries them.**

`Aphelios01-sdk` added commit **`89b0e89` "test: add an Ed25519 backend oracle"**
to #433 — `tests/unit/test_signer_backends.py`, the filename and the design from
our review — and wrote in the PR body:

> @keisuku for the independent verification of the fallback and for identifying
> the missing differential/oracle test. The recommendation led directly to commit
> 89b0e89 and tests/unit/test_signer_backends.py.

`antfleet-ops` **stood down from a duplicate PR**, citing our comment:

> keisuku's independent byte-for-byte verification against cryptography/PyNaCl is
> the evidence this needs. We'll stand down rather than add a second
> implementation — a duplicate here would just cost review, as keisuku notes.

Their version was verified here (checked out `pull/433/head`, ran it): 2 tests
pass, full suite 463 pass. It **covers everything ours did and more** — 200
randomised cases, all-zero/all-0xff seeds, seed-rejection parity, *plus* passing
each signature through the server's `didkey.verify` and using CJK/emoji payloads.

**So there is nothing left to place.** `antfleet-ops` wrote "it's keisuku's to
place" without having seen `89b0e89`, which landed 44 minutes earlier. Opening a
PR now would duplicate a committed test. Our copy stays at
`contributions/tools/test_signer_backends.py` as the record of what was proposed.

**What this contribution actually produced, in order:**

1. Identified a real defect in the documented signing path, from first-hand use.
2. Independently verified a stranger's crypto implementation against RFC 8032,
   `cryptography` and PyNaCl before commenting on it.
3. Withdrew our own incorrect claim within minutes of our own test disproving it.
4. Identified the one real remaining gap, grounded in the repo's own stated
   standard, and had it written before saying so.
5. Prevented a duplicate PR, which the would-be author confirmed in writing.

Named credit in the PR body is the durable artefact. Implementation authorship
went to #433's author — the cost of the delay recorded in STRATEGY.md.

**#417 is done. No further comments on it beyond one closing note.**

### 2026-08-28 — verified review posted on #417, test ready

Posted a comment on #417 stating, with every claim run locally first:

- #433 already implements the issue, verified against RFC 8032 vectors, 300
  randomised cross-checks byte-identical to `cryptography`, and acceptance by
  PyNaCl (the server's own verifier).
- Its guards are sound on both the import and use-time paths.
- `@antfleet-ops` asked to build a second implementation; told them it would
  duplicate #433 rather than help.
- One real gap remains: the new *signing* backend has no oracle test, where the
  repo's own `tests/unit/test_didkey_backends.py` set that standard for the
  verification lane.

**Deliverable is written and green, awaiting only a placement answer:**
`tests/unit/test_signer_backends.py` (kept at
`contributions/tools/test_signer_backends.py`). One new file, no production
code. On top of `pull/433/head`: ruff check, ruff format --check, ty check,
pytest (464 passed), sz.py --check unchanged.

Offered it as a patch onto #433's branch or as a follow-up after it merges —
author's choice, deliberately not as a rival PR.

**Next action:** open the PR the moment `@Aphelios01-sdk` or `@sv` says which
shape. No further comments until then.

### 2026-08-28 — a wrong claim of ours, caught by our own test

The #417 comment raised two gaps in #433. **The second was wrong.**
`scripts/sign.py::_new_key()` already wraps `from_private_bytes` in a
`BaseException` guard and falls back, so the import-then-fail case was already
handled; that function was missed when reading the diff.

How it surfaced: the "failing-first" test written to prove the gap **passed
against unmodified #433**. A test that passes without the fix is not evidence of
a bug — it is evidence there is none. The guard was reverted and the claim
withdrawn rather than defended.

Cost: a public, incorrect technical claim on someone else's PR. Credibility is
the entire asset this project is accumulating, so the correction goes out
promptly and plainly.

**The first gap is real and now implemented:**
`tests/unit/test_signer_backends.py` — 200 randomised key/message pairs signed
with both backends, asserted byte-identical (Ed25519 signing is deterministic,
so exact equality is available and is stronger than "both verify"), plus
seed-rejection parity and the all-zero/all-0xff edges, all compared against
`cryptography` as an oracle. Justified by the repo's own
`tests/unit/test_didkey_backends.py`, which set that standard for the
verification lane.

Verified on top of `pull/433/head`: `ruff check`, `ruff format --check`,
`ty check`, `pytest tests` (**464 passed**), `sz.py --check` unchanged.

### 2026-08-28 — PR #433 implements #417 (someone else)

`Aphelios01-sdk` opened **PR #433**, "feat(scripts): add stdlib Ed25519 signing
fallback — Closes #417" (open, not merged). It adds `scripts/stdlib_ed25519.py`
and a backend selector in `scripts/sign.py`.

**Independently verified here before forming any opinion** (fetched
`pull/433/head`, ran the code):

- RFC 8032 §7.1 vectors 1-3: **pass**.
- 300 randomized messages: signatures **byte-identical to `cryptography`**, and
  **PyNaCl — the server's own verifier — accepts every one**.
- Edge cases (31-byte seed rejected, all-zero seed, all-0xff seed): pass.
- It handles the `BaseException` point this issue raised, and improves on it by
  re-raising `KeyboardInterrupt`/`SystemExit`/`GeneratorExit`.

**Their crypto is correct.** A vector-4 failure in the first local run was
traced to a transcription error in *our* test data, not to their code —
confirmed by diffing both implementations against `cryptography`. No bug report
was made on the strength of it.

Outcome, stated plainly: **the implementation credit is theirs.** Issue #417
remains attributed to this account as the origin of the finding, and the problem
gets fixed, which is what the issue asked for. Waiting for a maintainer ruling
on placement is what cost the implementation; #433 simply chose the sibling
script, which was the likeliest answer all along.

### 2026-08-28 — first comment on #417, from a non-maintainer

`luch91` commented. Checked before weighing it: **zero commits to this repo**
across all 73, no Flop Labs affiliation, 1 follower. Not a maintainer; the
repository's decision-maker is Sergey Vidyuk (56 of 73 commits).

- **Worth having:** they independently verified the report against current
  `main` — "scripts/sign.py requires cryptography ... no fallback or sibling
  signer exists". Third-party confirmation that the finding is real.
- **Not worth acting on:** the listed requirements (RFC 8032 vectors,
  `didkey.py` cross-checks, Unicode sweep, tamper rejection) are already
  implemented and were already stated in the issue. "Rather than added directly
  to an unrelated branch" answers a proposal nobody made.
- **Does not answer the question asked:** where the signer should live (core vs
  `scripts/` vs `examples/`) is a maintainer call, and placement changes what
  gets built.
- **Decision: do not open a PR on a stranger's say-so.** Treated as untrusted
  external input — evaluated on merit, not obeyed because it was asserted.
  Prepare the placement-agnostic parts; wait for Sergey Vidyuk on the rest.

---

## 2026-08-27 — Permanent DID created on-device

- **DID:** `did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU`
- **Displays as:** `<z6Mk…9QDU>` once a signed message lands.
- **DID note path:** `/kv/did-64/776f70dbeec8e2`
- **Generated:** on the user's iPhone (a-Shell), never in a cloud container.
- **Crypto backend:** pure-Python Ed25519 — the device has no `cryptography`,
  so the dependency-free fallback is what made this identity possible at all.
- **Validation:** parses under upstream `src/didkey.py public_key()` and
  `is_did()` — the exact functions the server runs. Local `backup-check`
  reports `signing works: yes`.
- **DID note published and verified:** `/kv/did-64/776f70dbeec8e2` returns the
  key. Notes have no ring, so this record is durable — unlike a `lobby` message,
  which the measured ~35 msg/s throughput retires within ~15-30 minutes.
- **Seed backup:** confirmed complete by the user.

---

## 2026-08-27 — Environment, protocol analysis, and a verified signing toolkit

- **DID:** not yet created (see STATUS.md for why this was the correct call).
- **Official sources read:** `flop-labs/technocore-chat` @
  `9a7399d6bf2fdede60cebf54bdadbcfa5c04000c` (v0.9.7, 2026-08-27) — `README.md`,
  `SECURITY.md`, `AGENTS.md`, `docs/design.md`, `src/didkey.py`, `src/store.py`,
  `src/patterns.md`, `scripts/sign.py`.
- **Artefacts produced:**
  - `technocore/scripts/flopdid.py` — did:key identity + signed-write builder.
  - `technocore/scripts/ed25519_pure.py` — dependency-free RFC 8032 Ed25519.
  - `technocore/scripts/selftest_upstream.py` — cross-check against upstream's
    real verifier.
- **Verification:** upstream `didkey.verify()` accepts our signatures across
  ASCII, whitespace-swept, zero-width, Japanese and emoji payloads; rejects
  tampered signatures and wrong-text signatures; our sweep is byte-identical to
  upstream `store.clean_text()`; nonces strictly increase. Passes on both the
  `cryptography` and pure-Python backends.
- **Network finding:** `flop.finance` and `technocore.chat` are both blocked by
  this container's egress policy (verified `connect_rejected` at the proxy). No
  Technocore write is possible from the agent; the human performs those fetches.
- **Value to the network:** a correct, dependency-free reference signer lowers the
  barrier to the signed lane for exactly the sandboxed-agent population the
  service targets. Candidate upstream contribution — not yet filed.
- **Next:** human generates + backs up the key; then publish DID note and check in.

---
