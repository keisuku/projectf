# DRAFT — correction comment for #417, then the PR
# STATUS: the correction is URGENT — a wrong claim of mine is already posted.

## 1. Correction to post on #417

Correction to my last comment: **point 2 was wrong.** `_new_key()` in
`scripts/sign.py` already wraps `from_private_bytes` in a `BaseException` guard
and falls back to the stdlib backend, so the import-then-fail case is covered. I
missed that function when I read the diff. I wrote the guard and a test for it,
and the test passed against unmodified #433 — which is how I found out. Sorry for
the noise.

Point 1 stands and is now written: `tests/unit/test_signer_backends.py`, 200
randomised key/message pairs signed with both backends and asserted
byte-identical, plus the seed-rejection and all-zero/all-0xff edges compared
against the same oracle. Ed25519 signing is deterministic, so this is exact
equality rather than "both verify" — an assertion two backends drifting apart
could still satisfy.

Full CI green on top of `pull/433/head`: `ruff check`, `ruff format --check`,
`ty check`, `pytest tests` (464 passed), and `sz.py --check` unchanged since
tests are not core.

@Aphelios01-sdk — happy to send this as a patch onto your branch so #433 stays
one PR, or as a follow-up after it lands. Your call; tell me which and I will
open it.

## 2. What the PR contains

One new file, `tests/unit/test_signer_backends.py`. No production code changes.

Rationale for the reviewer: `tests/unit/test_didkey_backends.py` established that
when this repo gains a second implementation of a crypto primitive, `cryptography`
is kept as an oracle and the two are asked the same question — explicitly rather
than "asserting ... matches a table of expectations written by hand". #433 adds a
second *signing* backend with two hand-written RFC vectors. This applies the
existing standard to the new lane.
