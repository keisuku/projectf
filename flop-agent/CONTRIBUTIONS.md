# CONTRIBUTIONS — verifiable activity log

Append-only. Never record a seed, a token, or a signed URL (a signed URL is a
replayable capability).

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
