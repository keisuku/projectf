# DRAFT — comment for flop-labs/technocore-chat#417
# STATUS: awaiting the user's approval. Post as a comment on the issue page.
# Fact-checked 2026-08-28 against pull/433/head, run locally.

---

Heads-up before anyone writes more code: **#433 already implements this**, and I
ran it before commenting.

I fetched `pull/433/head` and exercised `scripts/stdlib_ed25519.py` directly:

- RFC 8032 §7.1 vectors 1–3: pass.
- 300 randomised messages (0–300 bytes): signatures **byte-identical to
  `cryptography`**, and PyNaCl — the library `src/didkey.py` verifies with —
  accepts every one.
- A 31-byte seed is rejected; all-zero and all-0xff seeds sign and verify.
- Its guard catches `BaseException` and re-raises
  `KeyboardInterrupt`/`SystemExit`/`GeneratorExit`, which is better than what I
  described, and its tests simulate a wheel that raises outside `Exception` —
  the exact failure I hit.

@antfleet-ops — thanks for offering, but I don't think a second implementation
helps here; #433 covers what I asked for, and it would be better reviewed than
duplicated.

Two things I would add to #433 rather than compete with it:

**1. The new signing backend has no oracle test.**
`tests/unit/test_didkey_backends.py` sets the house standard for exactly this
situation — its docstring says a backend swap that quietly moves the
accept/reject boundary is "a security change wearing a performance change's
clothes", and that `cryptography` stays available "as an oracle... rather than
asserting libsodium matches a table of expectations written by hand".

#433 adds a second *signing* backend and tests it against two hand-written RFC
vectors, which is the table this repo already decided was not enough. The same
differential shape would apply: sign the same randomised inputs with both
backends and assert the bytes match. That is the run I did above (300 cases,
byte-identical), so it is a small test to contribute.

**2. The guard covers import failure, but not import-then-fail.**
A `cryptography` build can import cleanly and raise at first use — a wheel whose
extension loads while its backend is missing. Deriving a public key from a fixed
seed once, before trusting the native path, closes that case for a couple of
lines.

@sv — from my side #417 is answered by #433 plus those two. Happy to send them as
a small follow-up once #433 lands, or as a patch onto that branch if its author
prefers.
