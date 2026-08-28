# DRAFT — replacement comment for flop-labs/technocore-chat#417
# The earlier comment was deleted by the author after one claim in it proved wrong.
# Every claim below was run locally against pull/433/head before writing.
# STATUS: awaiting approval.

---

*(Re-posting: an earlier version of this had a wrong second point, which I removed
once my own test disproved it. Everything below is what I actually ran.)*

**#433 already implements this.** I fetched `pull/433/head` and exercised
`scripts/stdlib_ed25519.py` directly before saying so:

- RFC 8032 §7.1 vectors 1–3: pass.
- 300 randomised messages (0–300 bytes): signatures **byte-identical to
  `cryptography`**, and PyNaCl — the library `src/didkey.py` verifies with —
  accepts every one.
- A 31-byte seed is rejected; all-zero and all-0xff seeds sign and verify.
- The import guard catches `BaseException` and re-raises
  `KeyboardInterrupt`/`SystemExit`/`GeneratorExit`, which is better than what I
  described in the issue, and the tests simulate a wheel that raises outside
  `Exception` — the exact failure I hit.
- `_new_key()` also guards the *use-time* path, so a wheel that imports cleanly
  and fails on first call falls back too. I went looking for that as a gap and
  it is already closed.

@antfleet-ops — thanks for offering to pick this up, but I don't think a second
implementation helps; #433 covers what I asked for, and it would be better
reviewed than duplicated.

**One thing I would add to #433 rather than compete with it: the new signing
backend has no oracle test.**

`tests/unit/test_didkey_backends.py` set the house standard for exactly this
situation. Its docstring says a backend swap that quietly moves the
accept/reject boundary is "a security change wearing a performance change's
clothes", and that `cryptography` stays available "as an oracle ... rather than
asserting libsodium matches a table of expectations written by hand".

#433 adds a second *signing* backend and pins it with two hand-written RFC
vectors — the table that reasoning already rejected for the verification lane.
The same differential shape applies, and signing is the easier case: Ed25519 is
deterministic, so the two backends can be asserted **byte-identical** rather
than merely both-verifying, which is an assertion two backends drifting in
opposite directions could still satisfy.

I have it written — `tests/unit/test_signer_backends.py`, 200 randomised
key/message pairs plus seed-rejection parity and the all-zero/all-0xff edges,
all compared against the oracle. One new file, no production code touched. Green
on top of `pull/433/head`: `ruff check`, `ruff format --check`, `ty check`,
`pytest tests` (464 passed), and `sz.py --check` unchanged, since tests are not
core.

@Aphelios01-sdk — I'd rather this landed as part of your work than as a rival
PR. Happy to send it as a patch onto your branch, or as a follow-up once #433
merges. Whichever you prefer — say which and I'll open it.
