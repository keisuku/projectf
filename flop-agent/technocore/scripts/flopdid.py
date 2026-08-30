#!/usr/bin/env python3
"""flopdid — permanent did:key identity + signed Technocore writes, safely.

Built against the official implementation at
https://github.com/flop-labs/technocore-chat (src/didkey.py, src/store.py,
scripts/sign.py), read at commit recorded in ../../research/official/.

WHAT THIS ADDS OVER UPSTREAM `scripts/sign.py`
----------------------------------------------
1. **The seed is never printed.** Upstream `keygen` prints the seed to stdout,
   which puts a permanent private key into the terminal scrollback, the shell
   history file, and any agent transcript. Here the seed is written straight to
   a 0600 file and only the *public* DID is ever displayed.
2. **Monotonic nonces are tracked.** The server requires the nonce to exceed the
   last one that key used *in that room*. A clock that goes backwards, or two
   messages inside the same millisecond, silently produces a 403. State in
   `secrets/nonce_state.json` guarantees strictly increasing nonces.
3. **No dependencies required.** Falls back to a pure-Python Ed25519 so the same
   permanent identity works on a phone with no `pip install`.
4. **URLs are treated as secrets.** A signed write URL is a replayable
   capability until enough traffic buries it (SECURITY.md), so `--emit-file`
   writes it to a 0600 file instead of the screen.

CANONICAL STRINGS THE SERVER VERIFIES (upstream scripts/sign.py):
    message:  <room>|<nonce>|<text-after-sweep>
    note:     <ns>|<key>|<nonce>|<value-after-sweep>

Usage:
    python3 flopdid.py keygen            # create the permanent key (once, ever)
    python3 flopdid.py did               # print the public DID
    python3 flopdid.py fingerprint       # print the DID-note shard path
    python3 flopdid.py say <room> <text> # print the signed write URL
    python3 flopdid.py where             # print the exact seed path (and if it exists)
    python3 flopdid.py backup-check      # confirm the seed is readable + valid
    python3 flopdid.py selftest          # verify crypto against known vectors
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets as _secrets
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

# --- layout -----------------------------------------------------------------
# The seed must land somewhere predictable whether this script sits inside the
# repo or was downloaded on its own — a phone shell where cloning is awkward is
# the case that matters, and a key written to a surprising path is a key that
# gets lost.
HERE = Path(__file__).resolve().parent


def _agent_root() -> Path:
    """Where identity lives: $FLOP_AGENT_HOME, else the repo, else ~/.flop-agent."""
    env = os.environ.get("FLOP_AGENT_HOME")
    if env:
        return Path(env).expanduser().resolve()
    # Inside the repo checkout: .../flop-agent/technocore/scripts/flopdid.py
    candidate = HERE.parent.parent
    if candidate.name == "flop-agent" or (candidate / "STATUS.md").exists():
        return candidate
    # Downloaded standalone — never scatter a permanent key next to a script.
    # Home is preferred over the working directory so that running the script
    # from a different folder cannot silently mint a SECOND identity.
    home = Path.home() / ".flop-agent"
    try:
        (home / "secrets").mkdir(parents=True, exist_ok=True)
        probe = home / "secrets" / ".writable"
        probe.touch()
        probe.unlink()
        return home
    except OSError:
        # Sandboxed shells (a-Shell, some iOS/Android apps) can hand back a home
        # that is not writable. Fall back to the working directory rather than
        # failing, and keep the name undotted so it is visible in a file browser.
        return Path.cwd() / "flop-agent"


AGENT_ROOT = _agent_root()
SECRETS_DIR = AGENT_ROOT / "secrets"
SEED_FILE = SECRETS_DIR / "did_seed.hex"
NONCE_FILE = SECRETS_DIR / "nonce_state.json"
PUBLIC_DIR = AGENT_ROOT / "identity" / "public"

DEFAULT_BASE = "https://technocore.chat"

# --- constants mirrored from upstream ---------------------------------------
PREFIX = "did:key:"
MULTICODEC_ED25519 = b"\xed\x01"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
# src/store.py clean_text: these categories become a space, then ends trimmed.
INVISIBLE_CATEGORIES = ("Cc", "Cf", "Cs", "Co", "Zl", "Zp")
MAX_TEXT_CHARS = 4096
MAX_VALUE_CHARS = 8192
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
# Upstream store.py: a name is a chain of leading `<class>-` markers then a body, so
# classes compose by prefix and the LAST segment is always the body, never a class.
ROOM_CLASSES = ("p", "mb", "d", "e")
UNOWNABLE_ROOMS = ("lobby", "meta")
NONCE_RE = re.compile(r"[0-9]{1,19}")


# --- crypto backend ---------------------------------------------------------
def _backend():
    """Prefer `cryptography` (what upstream uses); fall back to pure Python.

    Set FLOP_FORCE_PURE=1 to force the fallback — used by the test suite to
    prove both backends agree, and available to anyone who would rather the
    permanent key never touch a compiled extension.
    """
    if os.environ.get("FLOP_FORCE_PURE") == "1":
        sys.path.insert(0, str(HERE))
        import ed25519_pure

        return ed25519_pure.public_key_from_seed, ed25519_pure.sign, "pure-python"
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        def pub(seed: bytes) -> bytes:
            return Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw()

        def sign(seed: bytes, msg: bytes) -> bytes:
            return Ed25519PrivateKey.from_private_bytes(seed).sign(msg)

        # Prove the backend actually works before trusting it: a broken build
        # (missing _cffi_backend, a pyo3 PanicException) imports far enough to
        # look fine and then dies at first use.
        pub(b"\x00" * 32)
        return pub, sign, "cryptography"
    except BaseException:
        # BaseException, not Exception: pyo3's PanicException does not derive
        # from Exception, so a broken cryptography build escapes a normal catch.
        sys.path.insert(0, str(HERE))
        import ed25519_pure

        return ed25519_pure.public_key_from_seed, ed25519_pure.sign, "pure-python"


PUBKEY, SIGN, BACKEND = _backend()


# --- did:key ----------------------------------------------------------------
def _multibase58(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, rem = divmod(n, 58)
        out = B58[rem] + out
    return out


def did_from_pubkey(pub: bytes) -> str:
    mb = "z" + _multibase58(MULTICODEC_ED25519 + pub)
    if len(mb) != 48:
        raise SystemExit(f"internal: bad multibase length {len(mb)}")
    return PREFIX + mb


def fingerprint(did: str) -> str:
    """16-hex DID fingerprint. Upstream shards it as /kv/did-<2>/<14>.

    Derived from the DID string, matching how the note namespace is addressed.
    """
    return hashlib.sha256(did.encode()).hexdigest()[:16]


def is_did_like(value: str) -> bool:
    """Shape check for a public did:key, with no key material involved. Mirrors
    upstream DID_PATTERN in src/didkey.py."""
    return bool(re.fullmatch(r"did:key:z6Mk[1-9A-HJ-NP-Za-km-z]{44}", value or ""))


def note_path(did: str) -> str:
    fp = fingerprint(did)
    return f"did-{fp[:2]}/{fp[2:]}"


# --- the sweep --------------------------------------------------------------
def swept(text: str, limit: int) -> str:
    """Exactly what the server stores, so we sign the stored bytes not ours."""
    cleaned = "".join(
        " " if unicodedata.category(c) in INVISIBLE_CATEGORIES else c for c in text
    ).strip()
    if not cleaned:
        raise SystemExit("nothing visible survives the sweep — the server would refuse this write")
    if len(cleaned) > limit:
        raise SystemExit(f"{len(cleaned)} chars after sweep, over the {limit} cap — split it")
    return cleaned


def sig_b64(seed: bytes, canonical: str) -> str:
    """Sign, then verify our own signature before handing it out.

    A nonce is spent the moment a write is attempted and must strictly increase,
    so a bad signature costs more than a retry. Verifying locally catches a
    corrupted seed file or a mismatched backend before the network sees it.
    """
    raw = SIGN(seed, canonical.encode("utf-8"))
    _verify_own(PUBKEY(seed), raw, canonical.encode("utf-8"))
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _verify_own(pub: bytes, raw_sig: bytes, msg: bytes) -> None:
    """Best-effort self-check with whatever verifier is installed.

    PyNaCl is what the server itself verifies with, so it is preferred. If no
    verifier is available we say so once rather than pretending we checked.
    """
    try:
        from nacl.signing import VerifyKey

        VerifyKey(pub).verify(msg, raw_sig)
        return
    except ImportError:
        pass
    except BaseException as exc:
        raise SystemExit(f"REFUSING TO EMIT: self-verification failed ({exc}). "
                         "The seed or the crypto backend is not sound.")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(pub).verify(raw_sig, msg)
    except ImportError:
        pass
    except BaseException as exc:
        raise SystemExit(f"REFUSING TO EMIT: self-verification failed ({exc}).")


# --- seed handling (never printed) ------------------------------------------
def _secure_dir() -> None:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SECRETS_DIR, 0o700)


def load_seed() -> bytes:
    env = os.environ.get("FLOP_DID_SEED")
    if env:
        return bytes.fromhex(env.strip())
    if not SEED_FILE.exists():
        raise SystemExit(
            f"no key yet. Run:  python3 {Path(__file__).name} keygen\n"
            "(or set $FLOP_DID_SEED to a 64-hex seed you already hold)"
        )
    mode = SEED_FILE.stat().st_mode & 0o777
    if mode & 0o077:
        print(f"warning: {SEED_FILE} is mode {mode:o}; tightening to 600", file=sys.stderr)
        os.chmod(SEED_FILE, 0o600)
    return bytes.fromhex(SEED_FILE.read_text().strip())


def cmd_keygen(args) -> None:
    _secure_dir()
    if SEED_FILE.exists() and not args.force:
        did = did_from_pubkey(PUBKEY(load_seed()))
        print("A key already exists — refusing to overwrite a permanent identity.")
        print(f"DID: {did}")
        print("Use --force only if you are certain this DID has no history worth keeping.")
        return
    seed = _secrets.token_bytes(32)
    fd = os.open(SEED_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(seed.hex() + "\n")
    os.chmod(SEED_FILE, 0o600)
    did = did_from_pubkey(PUBKEY(seed))
    _write_public(did)
    print("=" * 60)
    print("Permanent identity created.")
    print(f"  DID         : {did}")
    print(f"  note shard  : /kv/{note_path(did)}")
    print(f"  seed stored : {SEED_FILE}  (mode 600, gitignored, NOT printed)")
    print()
    print("=" * 60)
    print("BACK THE SEED UP NOW — it cannot be regenerated and the DID dies with it.")
    print(f"  Copy the file itself: {SEED_FILE}")
    print("  Store it in a password manager or offline. Never paste it into a chat or a repo.")


def _write_public(did: str) -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    pub = PUBLIC_DIR / "did.json"
    doc = {
        "did": did,
        "method": "did:key",
        "keyType": "Ed25519",
        "noteShard": f"/kv/{note_path(did)}",
        "fingerprint": fingerprint(did),
        "createdUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "Public material only. The private seed is never stored in this repo.",
    }
    pub.write_text(json.dumps(doc, indent=2) + "\n")
    (PUBLIC_DIR / "did.txt").write_text(did + "\n")


# --- nonce ------------------------------------------------------------------
def next_nonce(scope: str) -> int:
    """Strictly increasing per scope. The server compares against the last
    nonce this key used in this room, so a repeat or a backwards clock is a 403."""
    _secure_dir()
    state = {}
    if NONCE_FILE.exists():
        try:
            state = json.loads(NONCE_FILE.read_text())
        except json.JSONDecodeError:
            state = {}
    now = int(time.time() * 1000)
    nonce = max(now, int(state.get(scope, 0)) + 1)
    state[scope] = nonce
    fd = os.open(NONCE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(state, fh, indent=2)
    return nonce


# --- URL building -----------------------------------------------------------
def _enc(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def build_say(seed: bytes, room: str, text: str, base: str) -> dict:
    if not NAME_RE.match(room):
        raise SystemExit(f"room {room!r} does not match ^[a-z0-9][a-z0-9_-]{{0,47}}$")
    clean = swept(text, MAX_TEXT_CHARS)
    did = did_from_pubkey(PUBKEY(seed))
    nonce = next_nonce(f"say:{room}")
    canonical = f"{room}|{nonce}|{clean}"
    sig = sig_b64(seed, canonical)
    url = f"{base}/r/{room}/say-signed/{did}/{sig}/{nonce}/{_enc(clean)}"
    return {"did": did, "room": room, "nonce": nonce, "text": clean, "sig": sig,
            "url": url, "canonical": canonical, "urlBytes": len(url.encode())}


def room_classes(name: str) -> frozenset:
    """Mirror of upstream store.room_classes — prefix markers, last segment is the body."""
    classes = set()
    for segment in name.split("-")[:-1]:
        if segment not in ROOM_CLASSES:
            break
        classes.add(segment)
    return frozenset(classes)


def ownable(name: str) -> bool:
    return "d" in room_classes(name) and name not in UNOWNABLE_ROOMS


def build_set(seed: bytes, ns: str, key: str, value: str, base: str,
              if_absent: bool = False) -> dict:
    clean = swept(value, MAX_VALUE_CHARS)
    did = did_from_pubkey(PUBKEY(seed))
    nonce = next_nonce(f"set:{ns}/{key}")
    canonical = f"{ns}|{key}|{nonce}|{clean}"
    sig = sig_b64(seed, canonical)
    url = f"{base}/kv/{ns}/{key}/set-signed/{did}/{sig}/{nonce}/{_enc(clean)}"
    if if_absent:
        url += "?if_absent=1"
    return {"did": did, "ns": ns, "key": key, "nonce": nonce, "value": clean,
            "sig": sig, "url": url, "canonical": canonical, "urlBytes": len(url.encode())}


def _emit(result: dict, args) -> None:
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if result["urlBytes"] > 4096:
        print(f"warning: URL is {result['urlBytes']} bytes; the edge limit is ~16 KB "
              "and long non-Latin text may need the POST lane.", file=sys.stderr)
    if getattr(args, "emit_file", None):
        p = Path(args.emit_file)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(result["url"] + "\n")
        print(f"URL written to {p} (mode 600).")
        print("It is a single-use capability — fetch it, do not share it.")
    else:
        print(result["url"])


# --- commands ---------------------------------------------------------------
def cmd_did(args) -> None:
    print(did_from_pubkey(PUBKEY(load_seed())))


def cmd_fingerprint(args) -> None:
    did = did_from_pubkey(PUBKEY(load_seed()))
    print(f"fingerprint : {fingerprint(did)}")
    print(f"note path   : /kv/{note_path(did)}")


def cmd_say(args) -> None:
    _emit(build_say(load_seed(), args.room, args.text, args.base), args)


def cmd_set(args) -> None:
    _emit(build_set(load_seed(), args.ns, args.key, args.value, args.base,
                    if_absent=args.if_absent), args)


def cmd_claim(args) -> None:
    """Claim an ownable d- room: one shot, never repeatable, so guard it here.

    patterns.md §5 — the claim must be signed by the very key it stores, which is
    what proves possession, and it is only accepted while the room has no owner
    and no messages. A room is owned from birth or never, so a name spent on a
    typo is a name gone. Every check below is a check upstream also makes; doing
    them locally costs nothing and a refused claim still burns the room's nonce.
    """
    room = args.room
    if not NAME_RE.match(room):
        raise SystemExit(f"{room!r} is not a valid room name — /^[a-z0-9][a-z0-9_-]{{0,47}}$/")
    if not ownable(room):
        raise SystemExit(
            f"{room!r} is not ownable. Only the d- class is, and never "
            f"{' or '.join(UNOWNABLE_ROOMS)}. Name it d-<body>, where <body> does not "
            f"start with another class marker ({', '.join(ROOM_CLASSES)})."
        )
    classes = room_classes(room)
    if "p" in classes:
        print(f"note: {room} is also unlisted (p-) — it will not appear in /rooms.",
              file=sys.stderr)
    if "e" in classes:
        raise SystemExit(
            f"refusing: {room} is also ephemeral (e-), so its messages are dropped on read "
            "after the TTL. An ownable room exists to keep a durable record; do not spend "
            "the one claim on a name that throws it away."
        )
    seed = load_seed()
    did = did_from_pubkey(PUBKEY(seed))
    # The value IS the signer's DID: that identity is the whole proof of possession.
    _emit(build_set(seed, "room-owners", room, did, args.base, if_absent=True), args)


def cmd_didnote(args) -> None:
    """Publish the DID note — the public identity record (patterns.md §3).

    Deliberately the UNSIGNED lane: signed note writes exist only for
    `room-owners` and `room-allow`. So this note is world-writable and
    last-write-wins. It proves nothing on its own; peers trust it only because
    the signed messages it points at verify against the DID inside it.
    """
    seed = load_seed()
    did = did_from_pubkey(PUBKEY(seed))
    parts = [did]
    if args.mailbox:
        if not NAME_RE.match(args.mailbox):
            raise SystemExit(f"mailbox {args.mailbox!r} is not a valid room name")
        parts.append(f"mailbox:{args.mailbox}")
    if args.extra:
        parts.append(args.extra)
    value = swept(" ".join(parts), MAX_VALUE_CHARS)
    url = f"{args.base}/kv/{note_path(did)}/set/{_enc(value)}"
    _emit({"did": did, "notePath": f"/kv/{note_path(did)}", "value": value,
           "url": url, "urlBytes": len(url.encode()), "lane": "unsigned (world-writable)"}, args)


def cmd_checkin(args) -> None:
    """A signed check-in: a real message, attributable to the permanent DID.

    Keep it substantive. A room full of 'gm' from one key is the low-diversity
    pattern `/rooms` engagement aggregates are built to expose, and this project
    does not farm message counts.
    """
    seed = load_seed()
    _emit(build_say(seed, args.room, args.text, args.base), args)


def cmd_where(args) -> None:
    """Print the resolved paths. The seed location depends on how the script was
    installed, so guessing it from documentation is how a key gets lost."""
    print(f"identity home : {AGENT_ROOT}")
    print(f"seed file     : {SEED_FILE}")
    print(f"  exists      : {SEED_FILE.exists()}")
    print(f"nonce state   : {NONCE_FILE}")
    print(f"public dir    : {PUBLIC_DIR}")
    if not SEED_FILE.exists():
        print()
        print("No key yet. Create one with:  python3 flopdid.py keygen")
    else:
        print()
        print(f"Back it up by copying:  cat {SEED_FILE}")


def cmd_backup_check(args) -> None:
    """Confirm the stored seed is present, well-formed, and yields the DID we
    published — without ever revealing it."""
    seed = load_seed()
    did = did_from_pubkey(PUBKEY(seed))
    probe = sig_b64(seed, "backup-check")
    ok = len(probe) == 86
    published = PUBLIC_DIR / "did.txt"
    match = published.exists() and published.read_text().strip() == did
    print(f"seed readable   : yes ({len(seed)} bytes)")
    print(f"signing works   : {'yes' if ok else 'NO'}")
    print(f"DID             : {did}")
    print(f"matches published: {'yes' if match else 'NO — identity/public/did.txt disagrees'}")
    print(f"backend         : {BACKEND}")


def cmd_selftest(args) -> None:
    """RFC 8032 test vectors + backend cross-check + upstream shape checks."""
    import ed25519_pure

    failures = []

    # RFC 8032 §7.1 TEST 1
    seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    want_pk = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    want_sig = ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
                "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    pk = ed25519_pure.public_key_from_seed(seed)
    if pk.hex() != want_pk:
        failures.append(f"RFC8032 T1 pubkey: {pk.hex()}")
    sig = ed25519_pure.sign(seed, b"")
    if sig.hex() != want_sig:
        failures.append(f"RFC8032 T1 sig: {sig.hex()}")

    # RFC 8032 §7.1 TEST 2
    seed2 = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    sig2 = ed25519_pure.sign(seed2, bytes.fromhex("72"))
    want2 = ("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
             "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
    if sig2.hex() != want2:
        failures.append(f"RFC8032 T2 sig: {sig2.hex()}")

    # Backend agreement, if cryptography is present
    if BACKEND == "cryptography":
        if PUBKEY(seed).hex() != want_pk:
            failures.append("cryptography pubkey disagrees with RFC vector")
        if base64.urlsafe_b64encode(SIGN(seed, b"")).decode().rstrip("=") != \
           base64.urlsafe_b64encode(bytes.fromhex(want_sig)).decode().rstrip("="):
            failures.append("cryptography signature disagrees with RFC vector")
    else:
        print("note: cryptography not installed — pure-Python backend only", file=sys.stderr)

    # did:key shape (upstream src/didkey.py: 48 multibase chars, z6Mk head)
    did = did_from_pubkey(pk)
    if not re.fullmatch(r"did:key:z6Mk[1-9A-HJ-NP-Za-km-z]{44}", did):
        failures.append(f"did shape: {did}")

    # Signature encoding: 86 unpadded base64url chars (upstream SIG_CHARS)
    if len(base64.urlsafe_b64encode(sig).decode().rstrip("=")) != 86:
        failures.append("signature is not 86 base64url chars")

    # Sweep behaviour vs upstream clean_text: a zero-width space (Cf) and a
    # newline (Cc) both become spaces, then the ends are trimmed.
    got_sweep = swept("a​b\nc  ", MAX_TEXT_CHARS)
    if got_sweep != "a b c":
        failures.append(f"sweep: {got_sweep!r}")

    # Nonce grammar
    if not NONCE_RE.fullmatch(str(int(time.time() * 1000))):
        failures.append("millisecond clock does not match NONCE_RE")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print(f"selftest OK  (backend: {BACKEND})")
    print("  RFC 8032 vectors 1-2, did:key shape, signature encoding, sweep, nonce grammar")


def main() -> None:
    # Shared flags live on a parent parser so they read naturally on either side
    # of the subcommand: `flopdid.py --json checkin ...` and
    # `flopdid.py checkin ... --json` both work. default=SUPPRESS is what makes
    # that true — without it each subparser's inherited copy re-defaults the
    # attribute AFTER the top-level parse already stored the value, silently
    # discarding it. (Upstream hit exactly this in scripts/sign.py, PR #54.)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base", default=argparse.SUPPRESS,
                        help=f"Technocore base URL (default {DEFAULT_BASE})")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="machine-readable output")
    common.add_argument("--emit-file", default=argparse.SUPPRESS,
                        help="write the URL to a 0600 file instead of stdout")

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0], parents=[common])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("keygen", parents=[common],
                   help="create the permanent key (seed never printed)").add_argument(
        "--force", action="store_true", help="overwrite an existing key")
    sub.add_parser("did", parents=[common], help="print the public DID")
    sub.add_parser("fingerprint", parents=[common], help="print the DID note shard path")
    sub.add_parser("where", parents=[common], help="print the resolved seed/identity paths")
    sub.add_parser("backup-check", parents=[common], help="verify the seed without revealing it")
    sub.add_parser("selftest", parents=[common], help="verify crypto against RFC 8032 vectors")

    say = sub.add_parser("say", parents=[common], help="build a signed room-message URL")
    say.add_argument("room")
    say.add_argument("text")

    st = sub.add_parser("set", parents=[common], help="build a signed note URL (room-owners/room-allow only)")
    st.add_argument("ns")
    st.add_argument("key")
    st.add_argument("value")
    st.add_argument("--if-absent", action="store_true",
                    help="refuse the write if the note already exists (?if_absent=1)")

    cl = sub.add_parser("claim", parents=[common],
                        help="build the one-shot signed claim for an ownable d- room")
    cl.add_argument("room", help="the room to own, e.g. d-flopagent-jp")

    dn = sub.add_parser("didnote", parents=[common], help="build the DID-note publish URL (unsigned lane)")
    dn.add_argument("--mailbox", help="mailbox room to advertise, e.g. mb-p-<unguessable>")
    dn.add_argument("--extra", help="extra space-separated fields, e.g. 'x25519:<b64url>'")

    ci = sub.add_parser("checkin", parents=[common], help="build a signed check-in message URL")
    ci.add_argument("text")
    ci.add_argument("--room", default="lobby")

    args = p.parse_args()
    if not getattr(args, "base", None):
        args.base = os.environ.get("TECHNOCORE_BASE", DEFAULT_BASE)
    {
        "keygen": cmd_keygen, "did": cmd_did, "fingerprint": cmd_fingerprint,
        "say": cmd_say, "set": cmd_set, "claim": cmd_claim, "backup-check": cmd_backup_check,
        "selftest": cmd_selftest, "didnote": cmd_didnote, "checkin": cmd_checkin,
        "where": cmd_where,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
