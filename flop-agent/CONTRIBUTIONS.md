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
- **Not yet done:** DID note publication and first signed check-in (the human
  performs those fetches; the agent container cannot reach technocore.chat).

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
