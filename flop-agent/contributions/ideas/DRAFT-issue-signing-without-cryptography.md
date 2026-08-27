# DRAFT — GitHub issue for flop-labs/technocore-chat
# STATUS: APPROVED by the user 2026-08-27. Posted manually from their GitHub
# account (this session has read-only access to flop-labs and cannot post).
#
# Deliberately absent, and it must stay that way: the DID, any wallet, and any
# mention of FLOP or the airdrop. Identity linkage belongs in the DID note
# (`didnote --extra "github:<user>"`), never in an unrelated bug report.
# Duplicate check run 2026-08-27: 0 matching issues, 0 matching PRs.

---

**Title:** Signed lane is unreachable where Python exists but pip/uv do not (e.g. a-Shell on iOS)

**Body:**

## What I hit

I set up a `did:key` identity for the signed lane from a phone shell (a-Shell on
iOS). Python 3.11 is there, but `pip`/`uv` are not usable, so `cryptography`
cannot be installed — and `scripts/sign.py` provisions it from its PEP 723
header. The documented signing path could not run at all on that device.

The failure is not always a clean `ImportError`, either. On another box here the
`cryptography` wheel was present but its `_cffi_backend` was missing, and the
import raised a pyo3 `PanicException`, which does **not** subclass `Exception` —
so an ordinary `try: import ... except Exception:` guard around it does not
catch it.

## Why I think it is in scope

`docs/design.md` §5.2 draws the line at "an agent that also has a shell": a
webfetch-only agent cannot sign, so signing is the opt-in upgrade for agents with
code execution. My case *has* code execution — it just has no package manager.
That population sits inside the line the design draws, but outside what the
tooling can currently serve, and the gap is a packaging detail rather than
anything essential: Ed25519 signing needs only `hashlib` and integer arithmetic.

This is not one phone, either: the same holds for hardened containers with no
network at build time, read-only runtimes, and any environment where the Python
is fixed and the package set is not the caller's to change.

Verification is unaffected — the server keeps verifying with libsodium either
way. This is only about the client-side signer.

## Reproduction

```
$ python3 -c "import cryptography"   # a-Shell, iOS
ModuleNotFoundError: No module named 'cryptography'
$ uv run scripts/sign.py keygen
uv: command not found
```

## What I have already

I wrote a stdlib-only RFC 8032 signer for my own use and cross-checked it
against this repo's `src/didkey.py verify()` — the same function the server
runs — over ASCII, whitespace-swept, zero-width, CJK and emoji payloads, plus
tampered-signature and wrong-text cases, and confirmed its sweep matches
`src/store.py clean_text()` byte for byte. It passes RFC 8032 §7.1 vectors 1–2
and agrees with `cryptography` where that is installed. The identity I actually
use was generated with it on the phone.

## What I am asking

Would you want this in the repo, and if so, where? I do not want to grow core —
`AGENTS.md` is clear that core has size caps and that growth past one "needs a
new primitive, or belongs in extra". My assumption is this belongs beside
`scripts/sign.py` (a fallback import, or a sibling script), explicitly not core,
and `cryptography` stays the default path when it is importable.

Happy to open a PR in whatever shape you prefer, or to drop it if you would
rather keep the signer single-implementation. Also happy to just contribute the
`BaseException` note as a comment if that is the only part worth having.
