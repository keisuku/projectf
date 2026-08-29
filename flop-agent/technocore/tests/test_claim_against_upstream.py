#!/usr/bin/env python3
"""Prove the d- room claim URL is one the SERVER would accept — using the server's code.

Verifying our signature with our own verifier only proves we agree with ourselves. This
imports upstream `didkey.verify()` and `store.ownable()` — the exact functions technocore
runs — and routes a generated claim URL through them.

The claim is unrepeatable: a name, once written to /kv/room-owners, is never re-claimable
by us if the write is malformed and someone else takes it meanwhile. That asymmetry is why
this test exists and why it runs against upstream rather than a copy of our own beliefs.

Run:
    git clone --depth 1 https://github.com/flop-labs/technocore-chat /tmp/upstream
    UPSTREAM=/tmp/upstream python3 test_claim_against_upstream.py

Requires upstream's own deps (pynacl, orjson). Skips, loudly, without them — a skipped
test must never read as a passing one.

**No key material is involved.** A throwaway seed is generated per run; the permanent seed
stays on the device that made it and is not needed to test the shape of a URL.
"""

import os
import secrets
import sys
import tempfile
import urllib.parse
from pathlib import Path

UPSTREAM = Path(os.environ.get("UPSTREAM", "/home/user/upstream-technocore"))
HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"

if not (UPSTREAM / "src" / "didkey.py").exists():
    sys.exit(f"SKIPPED: no upstream checkout at {UPSTREAM}. Set $UPSTREAM. "
             "This test is worthless without it — it exists to check OUR code against "
             "THEIRS, and passing it against a stub would be a lie.")

sys.path.insert(0, str(UPSTREAM / "src"))
try:
    import didkey  # upstream
    import store  # upstream
except ImportError as exc:
    sys.exit(f"SKIPPED: upstream deps missing ({exc}). pip install pynacl orjson")

_tmp = tempfile.mkdtemp(prefix="flopclaim-")
os.environ["FLOP_AGENT_HOME"] = _tmp
_throwaway = secrets.token_bytes(32)
os.environ["FLOP_DID_SEED"] = _throwaway.hex()

sys.path.insert(0, str(SCRIPTS))
import flopdid  # noqa: E402

BASE = "https://technocore.chat"
ROOM = "d-watchtower"
failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def parse(url: str) -> tuple[dict, str]:
    """Split a signed-note URL the way Starlette's route does."""
    path, _, query = url.partition("?")
    segs = path[len(BASE):].strip("/").split("/")
    check(segs[0] == "kv", f"not a /kv route: {segs[0]}")
    ns, key, verb, did, sig, nonce, value = segs[1:8]
    return {"ns": ns, "key": key, "verb": verb, "did": did, "sig": sig,
            "nonce": nonce, "value": urllib.parse.unquote(value)}, query


def main() -> int:
    seed = _throwaway
    res = flopdid.build_claim(seed, ROOM, BASE)
    p, query = parse(res["url"])

    # --- route shape -------------------------------------------------------
    check(p["verb"] == "set-signed", f"verb is {p['verb']}, not set-signed")
    check(p["ns"] == store.OWNERS_NS, f"namespace is {p['ns']}")
    check(p["key"] == ROOM, f"key is {p['key']}")
    check(query == "if_absent=1",
          f"query is {query!r}: without if_absent the gate reads the owner note and then "
          "writes it, so two simultaneous claims can both believe they won")

    # --- the server rebuilds the signed string from the URL, so ours must match
    canonical = f"{p['ns']}|{p['key']}|{p['nonce']}|" \
                f"{store.clean_text(p['value'], store.MAX_VALUE_CHARS)}"
    check(canonical == res["canonical"],
          f"canonical drift:\n    ours {res['canonical']!r}\n    server {canonical!r}")
    try:
        didkey.verify(p["did"], p["sig"], canonical)
    except Exception as exc:  # noqa: BLE001 — any rejection is the failure
        failures.append(f"upstream didkey.verify() REJECTED the claim: {exc}")

    # --- _note_write_gate's first-claim rules, checked before spending a nonce
    check(store.ownable(p["key"]), "upstream store.ownable() refuses this name")
    check(didkey.is_did(p["value"]), "the stored value is not a did:key")
    check(p["did"] == p["value"],
          "signer != value: a FIRST claim must be signed by the key it stores")

    # --- the signature must bind every field, or a field can be swapped in flight
    for label, tampered in (
        ("room", f"{p['ns']}|d-watchtowe|{p['nonce']}|{p['value']}"),
        ("nonce", f"{p['ns']}|{p['key']}|{int(p['nonce']) + 1}|{p['value']}"),
        ("namespace", f"{store.ALLOW_NS}|{p['key']}|{p['nonce']}|{p['value']}"),
        ("value", f"{p['ns']}|{p['key']}|{p['nonce']}|{p['value'][:-1]}A"),
    ):
        try:
            didkey.verify(p["did"], p["sig"], tampered)
            failures.append(f"TAMPER ACCEPTED ({label}): the signature does not bind it")
        except Exception:  # noqa: BLE001,S110 — rejection is the pass
            pass

    # --- our mirrored name rules must not drift from upstream's -------------
    # Classes compose, so a body whose first segment is a marker changes what the room IS:
    # d-p-x is also unlisted, d-e-x also ephemeral. Getting this wrong claims a different
    # room than the one intended, once, permanently.
    for name in ("d-watchtower", "d-jobs", "lobby", "meta", "watchtower", "d", "d-",
                 "d-p-secret", "d-e-mail", "mb-p-x", "d-mb-x", "e-d-x", "dd-x", "d-d-x"):
        check(flopdid.ownable(name) == store.ownable(name),
              f"ownable({name!r}): ours={flopdid.ownable(name)} "
              f"upstream={store.ownable(name)}")
        check(flopdid.room_classes(name) == store.room_classes(name),
              f"room_classes({name!r}) disagrees with upstream")

    # --- room-owners and room-allow share ONE counter (/kv/room-nonce/<room>)
    probe = "d-nonce-probe"
    claim = flopdid.build_claim(seed, probe, BASE)
    allow = flopdid.build_set(seed, store.ALLOW_NS, probe,
                              flopdid.did_from_pubkey(flopdid.PUBKEY(seed)), BASE)
    check(int(allow["nonce"]) > int(claim["nonce"]),
          f"room-allow nonce {allow['nonce']} <= claim nonce {claim['nonce']}: the server "
          "burns one counter per room, so the allow-list write would be refused as a replay")

    # --- refuse locally rather than spend a round trip the human makes by hand
    for bad, why in (("lobby", "hardcoded unownable"), ("meta", "hardcoded unownable"),
                     ("watchtower", "no d- class"), ("D-Watchtower", "uppercase")):
        try:
            flopdid.build_claim(seed, bad, BASE)
            failures.append(f"build_claim({bad!r}) was allowed — {why}")
        except SystemExit:
            pass

    if failures:
        print("FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("PASS — checked against upstream didkey.verify() and store.ownable():")
    print("  route shape, canonical string, if_absent, signer==value, ownable,")
    print("  4 tamper rejections, 14 name-class agreements, shared room-nonce ordering,")
    print("  4 local refusals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
