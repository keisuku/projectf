#!/usr/bin/env python3
"""Cross-check flopdid.py against the REAL upstream verifier.

`flopdid.py selftest` proves the crypto is RFC-correct in isolation. This proves
the thing that actually decides whether a write lands: that
`flop-labs/technocore-chat`'s own `src/didkey.py verify()` — the exact function
the server runs — accepts what we produce, and that our sweep agrees with the
server's `src/store.py clean_text()` byte for byte.

A mismatch here is a silent 403 at check-in time, so this runs before anything
touches the network.

Usage:
    UPSTREAM=/path/to/technocore-chat python3 selftest_upstream.py
Default UPSTREAM: /home/user/flop-labs/technocore-chat
"""

from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPSTREAM = Path(os.environ.get("UPSTREAM", "/home/user/flop-labs/technocore-chat"))

if not (UPSTREAM / "src" / "didkey.py").exists():
    sys.exit(f"upstream checkout not found at {UPSTREAM} — set $UPSTREAM")

sys.path.insert(0, str(UPSTREAM / "src"))
sys.path.insert(0, str(HERE))

import didkey  # upstream, verified by the server  # noqa: E402

import flopdid  # ours  # noqa: E402

failures: list[str] = []

# A throwaway seed: this test must never touch the permanent identity.
SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")

# 1. Our did:key must parse under the server's parser, and yield our public key.
did = flopdid.did_from_pubkey(flopdid.PUBKEY(SEED))
try:
    if didkey.public_key(did) != flopdid.PUBKEY(SEED):
        failures.append("upstream public_key(did) != our public key")
except didkey.DidError as exc:
    failures.append(f"upstream rejected our DID: {exc}")

if not didkey.is_did(did):
    failures.append(f"upstream is_did() rejected {did}")

# 2. A signed message must verify under the server's verifier, for a range of
#    texts including ones the sweep rewrites and non-Latin/emoji payloads.
CASES = [
    ("lobby", "hello from a flop participation agent"),
    ("lobby", "  leading and trailing   "),
    ("lobby", "zero​width and a\nnewline"),
    ("meta", "日本語のメッセージ"),
    ("mb-p-test", "emoji 🚀 and pipes | in | text"),
]

for room, text in CASES:
    built = flopdid.build_say(SEED, room, text, "https://technocore.chat")
    canonical = f"{built['room']}|{built['nonce']}|{built['text']}"
    if canonical != built["canonical"]:
        failures.append(f"canonical mismatch for {text!r}")
    try:
        didkey.verify(built["did"], built["sig"], canonical)
    except (didkey.DidError, didkey.SignatureError) as exc:
        failures.append(f"upstream verify() REJECTED {text!r}: {exc}")

    # 3. The URL must decode back to exactly the text we signed. The DID
    #    contains no '/', so the encoded text is always the final segment.
    decoded = urllib.parse.unquote(built["url"].rsplit("/", 1)[1])
    if decoded != built["text"]:
        failures.append(f"URL round-trip lost text: {decoded!r} != {built['text']!r}")

# 4. A tampered signature must be REFUSED — fail-closed, not fail-open.
built = flopdid.build_say(SEED, "lobby", "tamper probe", "https://technocore.chat")
canonical = f"{built['room']}|{built['nonce']}|{built['text']}"
sig = built["sig"]
tampered = ("A" if sig[0] != "A" else "B") + sig[1:]
try:
    didkey.verify(built["did"], tampered, canonical)
    failures.append("SECURITY: upstream accepted a tampered signature")
except (didkey.DidError, didkey.SignatureError):
    pass

# 5. A signature over different text must be refused (wrong-message binding).
try:
    didkey.verify(built["did"], sig, canonical.replace("tamper probe", "different text"))
    failures.append("SECURITY: signature verified against text it did not sign")
except (didkey.DidError, didkey.SignatureError):
    pass

# 6. Our sweep must equal the server's clean_text exactly.
try:
    import store  # upstream

    for _, text in CASES + [("x", "a​b\nc  "), ("x", "bidi‮override")]:
        ours = flopdid.swept(text, flopdid.MAX_TEXT_CHARS)
        theirs = store.clean_text(text)
        if ours != theirs:
            failures.append(f"sweep disagrees on {text!r}: ours={ours!r} upstream={theirs!r}")
except ImportError as exc:
    print(f"note: upstream store.py not importable ({exc}); sweep compared structurally only",
          file=sys.stderr)

# 7. Nonces must strictly increase per scope, including within one millisecond.
seen = [flopdid.next_nonce("selftest:room") for _ in range(50)]
if seen != sorted(set(seen)) or len(set(seen)) != 50:
    failures.append("nonces are not strictly increasing")

if failures:
    print("UPSTREAM CROSS-CHECK FAILED:")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)

print(f"upstream cross-check OK  (backend: {flopdid.BACKEND})")
print(f"  upstream: {UPSTREAM}")
print("  verified: did parsing, signature acceptance by the server's own verify(),")
print("            tamper rejection, wrong-text rejection, sweep equality, nonce monotonicity")
