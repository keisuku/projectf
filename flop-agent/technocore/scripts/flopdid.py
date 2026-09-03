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

PRODUCTION WRITE GATE (HANDOFF.md §2.5, §5.4)
--------------------------------------------
`--fetch` sends the request from inside this tool. Against a loopback base
(127.0.0.1 / localhost / ::1 — a locally hosted technocore-chat) it sends
unconditionally: that is the test lane. Against any other host it is REFUSED
unless three independent things are all present:

    1. the `--production` flag on the command line,
    2. `--approval <file>` — a one-time approval file the human writes, carrying
       the SHA-256 of the exact body being sent (see `approval` below), and
    3. an interactive confirmation on a TTY, typed after the tool has shown the
       raw body, the swept body, the canonical bytes (hex), the nonce and the
       signature.

No environment variable is consulted by the gate, so none can relax any of the
three factors, and none can choose the destination: with `--production`,
`$TECHNOCORE_BASE` is ignored. (Two variables still shape the run around it:
`$FLOP_AGENT_HOME` moves the identity home, and with it where proof.log and the
snapshots are written, and `$FLOP_FORCE_PURE` selects the signing backend.
Neither can substitute for a factor.) The
approval file is consumed (renamed) the moment the request is issued, so it can
authorise at most one attempt. Every attempt — accepted, refused, or never sent —
is appended to `<identity home>/logs/proof.log`, and an accepted room write is
followed by an `/export` snapshot saved beside it.

    python3 flopdid.py approval d-bitflop "<body>"      # print the approval JSON to write
    python3 flopdid.py say d-bitflop "<body>" --fetch --production --approval approval-1.json
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


# RFC 8032 §7.1 TEST 1: the public key and the signature over the empty message.
# Used to probe a verifier before trusting its verdict on our own signature.
_RFC_PK = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
_RFC_SIG = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
    "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
)


def _verifiers() -> list:
    """The installed verifiers that demonstrably work, PyNaCl first (it is what
    the server verifies with). Each is probed on the RFC 8032 vector before it
    is allowed a verdict: a broken build — `cryptography` without its
    `_cffi_backend`, which dies in a pyo3 panic that is not even an `Exception`
    — used to read as "our signature failed to verify" and refused every write
    from a perfectly good key. A verifier that cannot pass a known-good vector
    is absent, not a judge."""
    found = []
    try:
        from nacl.exceptions import BadSignatureError
        from nacl.signing import VerifyKey

        VerifyKey(_RFC_PK).verify(b"", _RFC_SIG)
        found.append(("pynacl", lambda pub, sig, msg: VerifyKey(pub).verify(msg, sig),
                      BadSignatureError))
    except BaseException:  # noqa: BLE001 — ImportError, a broken build, a pyo3 panic
        pass
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(_RFC_PK).verify(_RFC_SIG, b"")
        found.append(("cryptography",
                      lambda pub, sig, msg: Ed25519PublicKey.from_public_bytes(pub).verify(sig, msg),
                      InvalidSignature))
    except BaseException:  # noqa: BLE001
        pass
    return found


def _verify_own(pub: bytes, raw_sig: bytes, msg: bytes) -> None:
    """Self-check with the first verifier that is known to work.

    Only a verifier's own bad-signature verdict refuses the emit. Anything else
    it raises mid-verify is unexpected after a passed probe and refuses too, but
    says which verifier and why, so the failure is diagnosable rather than being
    read as a bad key. If no verifier works, say so once and carry on: the
    server is the final verifier either way.
    """
    for name, verify, bad_signature in _verifiers():
        try:
            verify(pub, raw_sig, msg)
        except bad_signature:
            raise SystemExit(f"REFUSING TO EMIT: {name} rejected our own signature. "
                             "The seed or the signing backend is not sound.") from None
        except BaseException as exc:  # noqa: BLE001
            raise SystemExit(f"REFUSING TO EMIT: {name} failed while verifying our own "
                             f"signature ({type(exc).__name__}: {exc}).") from None
        return
    if not getattr(_verify_own, "_warned", False):
        _verify_own._warned = True  # type: ignore[attr-defined]
        print("note: no working Ed25519 verifier installed (PyNaCl or cryptography); "
              "the signature was not self-checked before emitting.", file=sys.stderr)


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
    # room-owners and room-allow share ONE server-side replay counter per room
    # (/kv/room-nonce/<room>, upstream store.NONCE_NS), so they must share one
    # local scope too. Tracking them separately would let an allow-list write
    # reuse a nonce the claim already burned — the server answers that with a
    # 403 and the room's counter has still moved.
    scope = f"room-nonce:{key}" if ns in ("room-owners", "room-allow") else f"set:{ns}/{key}"
    nonce = next_nonce(scope)
    canonical = f"{ns}|{key}|{nonce}|{clean}"
    sig = sig_b64(seed, canonical)
    url = f"{base}/kv/{ns}/{key}/set-signed/{did}/{sig}/{nonce}/{_enc(clean)}"
    if if_absent:
        url += "?if_absent=1"
    return {"did": did, "ns": ns, "key": key, "nonce": nonce, "value": clean,
            "sig": sig, "url": url, "canonical": canonical, "urlBytes": len(url.encode())}


def _request(url: str, accept: str):
    import urllib.request

    return urllib.request.Request(url, headers={
        "User-Agent": "flopdid (participation agent; contact via github.com/keisuku)",
        "Accept": accept,
    })


def _opener():
    """An opener that uses no proxy and refuses every redirect, for both
    writes and the post-write reads.

    No proxy: urllib would otherwise honour `http_proxy` / `HTTPS_PROXY` from
    the environment, and a proxy is handed the complete signed URL — a
    capability. With `NO_PROXY` not covering loopback, an environment variable
    alone could route an ungated test-lane write through a relay that can
    replay it at technocore.chat. An empty ProxyHandler makes every request
    connect directly to the host the gate classified. (Direct is also what the
    phone and the PC do; an environment that can only reach the host through a
    proxy simply cannot write from this tool, which is the safe failure.)

    No redirect: `redirect_request` returning None makes urllib raise the 3xx
    as an HTTPError instead of following it, so the only host any request from
    this tool reaches is the one in the URL that was built and gated."""
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)


EXIT_INDETERMINATE = 4  # the request may have reached the server; the reply was lost


def _never_reached(exc: BaseException) -> bool:
    """True only when the failure provably happened before any byte of the
    request left this machine: connection refused, no route, DNS failure, or a
    TLS certificate rejected during the handshake. Everything else — a timeout,
    a reset, a connection closed without a reply, a truncated body — may have
    happened after the server stored the write, and is not "not sent"."""
    import errno
    import socket
    import ssl

    reason = getattr(exc, "reason", exc)
    if isinstance(reason, (ConnectionRefusedError, socket.gaierror,
                           ssl.SSLCertVerificationError)):
        return True
    if isinstance(reason, OSError) and reason.errno in (
        errno.ECONNREFUSED, errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EADDRNOTAVAIL,
    ):
        return True
    return False


def _send(url: str) -> int:
    """GET the signed URL from here, and print what the server said.

    This exists because handing a signed URL to a shell is where it goes wrong.
    A bare `https://…` at a prompt is `command not found`; `curl "$(cat f)"`
    needs command substitution, which restricted shells (a-Shell on iOS among
    them) do not implement, and curl is then handed the literal `$(cat f)` and
    answers `URL rejected: Malformed input to a URL function`. Neither failure
    reaches the network, and both read like a refusal from the server.

    The URL is never printed here — only the response. Every write on this
    service is a plain GET, so this is the whole operation.

    Redirects are never followed. A signed URL is a capability, and following
    a 3xx would hand it to whatever host the answering server names — a local
    test server answering `302 https://technocore.chat/…` would turn a gated
    test-lane write into an ungated production one. The gate decides on the
    host the operator typed, so that is the only host this request may reach.
    """
    import urllib.error

    req = _request(url, "text/plain, application/json, */*")
    try:
        with _opener().open(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
            print(f"HTTP {resp.status}")
            print(body.rstrip())
            return 0 if 200 <= resp.status < 300 else 1
    except urllib.error.HTTPError as exc:
        # The server's refusals carry the reason in the body and are the most
        # useful thing on the screen — print them rather than a status alone.
        body = exc.read().decode("utf-8", "replace")
        print(f"HTTP {exc.code}", file=sys.stderr)
        if 300 <= exc.code < 400:
            print(f"REFUSED: the server answered with a redirect to "
                  f"{exc.headers.get('Location', '?')!r}; a signed write is never "
                  "forwarded to a host the operator did not name.", file=sys.stderr)
        print(body.rstrip(), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — every transport failure is classified below
        if _never_reached(exc):
            print(f"NOT SENT: {type(exc).__name__}: {exc}", file=sys.stderr)
            print("Nothing reached the server, so no nonce was spent there. Retry from a "
                  "network that reaches this host — a production retry needs a FRESH "
                  "approval: the one used here was consumed on dispatch.", file=sys.stderr)
            return 2
        # A timeout, a reset, a connection closed before the reply, a truncated
        # body: the request may have been stored. Saying "not sent" here would
        # invite a resend, and a resend of an accepted write is a duplicate
        # record that can never be removed.
        print(f"OUTCOME UNKNOWN: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("The request was dispatched (or may have been) and the reply was lost. "
              "The server may have stored it. Do NOT resend: read the room back "
              "first and look for this nonce.", file=sys.stderr)
        return EXIT_INDETERMINATE


# --- production write gate --------------------------------------------------
#
# HANDOFF.md §2.5: a write to technocore.chat happens only when the commander has
# approved the body and the canonical bytes. §5.4 says how: a CLI flag, an
# interactive confirmation, and a one-time approval file carrying the body's
# hash, all three, and nothing in the environment can stand in for any of them.
#
# The gate keys on the destination, not on a mode switch: loopback is the test
# lane and is never gated, everything else is production and always is. That
# keeps the local technocore-chat E2E runnable without ceremony while making it
# impossible to reach the live service by forgetting a flag.

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
APPROVER_PLACEHOLDER = "<name of the approver>"
LOGS_DIR = AGENT_ROOT / "logs"
PROOF_LOG = LOGS_DIR / "proof.log"
EXIT_GATE_REFUSED = 3  # distinct from 1 (server refused) and 2 (never sent)


def is_loopback(base: str) -> bool:
    """True only for a base URL whose host is the local machine itself.

    The host must be the literal name `localhost` or a literal loopback IP
    (127.0.0.0/8 or ::1). A hostname that merely *looks* local —
    `127.0.0.1.nip.io`, `localhost.example` — resolves wherever its owner says,
    so it is production, and the DNS answer is never consulted here.
    """
    import ipaddress

    host = (urllib.parse.urlsplit(base).hostname or "").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def body_sha256(clean: str) -> str:
    """The hash an approval file carries: SHA-256 of the swept body as UTF-8.

    It is the swept body, not the raw argument, because the swept form is what
    gets signed and stored; approving the raw text would let a zero-width
    character change what lands without changing the hash.
    """
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def _write_kind(result: dict) -> str:
    if "room" in result:
        return "say"
    if "ns" in result:
        return "set"
    return "note-unsigned"


def _write_target(result: dict) -> str:
    """The target as the approval names it and as the readers address it.

    For the unsigned note lane that is the note path **without** the `/kv/`
    prefix: `cmd_didnote` carries `notePath` as `/kv/<shard>/<key>` for display,
    and every reader here builds `{base}/kv/{target}`, so returning the display
    form produced `/kv//kv/…` and read back a note that cannot exist."""
    kind = _write_kind(result)
    if kind == "say":
        return result["room"]
    if kind == "set":
        return f"{result['ns']}/{result['key']}"
    return result["notePath"].removeprefix("/kv/").lstrip("/")


def _write_body(result: dict) -> str:
    return result["text"] if "text" in result else result["value"]


def _destination(base: str) -> str:
    """The destination an approval pins: `host` or `host:port`, lowercased.

    The *hostname* alone is not the destination. `https://technocore.chat:8443`
    and `http://technocore.chat` share it, and the second puts a signed
    capability URL on the wire in cleartext — so the port travels with the host,
    and `_cleartext_refusal` handles the scheme."""
    parts = urllib.parse.urlsplit(base)
    host = (parts.hostname or "").lower()
    if not host:
        return base.lower()
    if ":" in host:  # an IPv6 literal: keep the brackets, or `[::1]:443` and
        host = f"[{host}]"  # `[::1:443]` would render the same destination
    try:
        port = parts.port
    except ValueError:
        # A malformed port. Keep it visible rather than dropping it — but strip
        # any userinfo first: this string is printed on the review screen and
        # written to proof.log, and a password in a URL must not be persisted.
        return parts.netloc.rpartition("@")[2].lower()
    return f"{host}:{port}" if port is not None else host


def _cleartext_refusal(base: str) -> str | None:
    """Refuse `http://` to a public host under --production.

    A signed URL is a replayable capability for as long as the record sits in
    the server's anti-replay window, so handing one to a cleartext connection
    gives it to every hop on the path. Private and reserved addresses stay
    reachable over http: that is where a local upstream server is rehearsed
    against, and no such address can be technocore.chat."""
    parts = urllib.parse.urlsplit(base)
    if parts.scheme == "https":
        return None
    host = parts.hostname or ""
    try:
        import ipaddress

        addr = ipaddress.ip_address(host)
        # 6to4 (2002::/16) embeds a public IPv4 address, and `is_private` says
        # True for it. `2002:0808:0808::1` is 8.8.8.8 wearing a private label, so
        # it is treated as the public address it carries.
        six_to_four = addr.version == 6 and addr in ipaddress.ip_network("2002::/16")
        if addr.is_private and not six_to_four:
            return None
    except ValueError:
        pass
    return (f"{base} is a cleartext {parts.scheme or 'http'} URL to a public host; a signed "
            "URL is a replayable capability and does not go over cleartext. Use https.")


def _refuse(reason: str) -> int:
    print("PRODUCTION WRITE REFUSED: " + reason, file=sys.stderr)
    print("Nothing was sent and no nonce reached the server. See HANDOFF.md §2.5 / §5.4.",
          file=sys.stderr)
    return EXIT_GATE_REFUSED


def _load_approval(path: str, result: dict, did: str, host: str) -> dict | str:
    """Read and check the one-time approval file. Returns the approval, or the
    reason it is not acceptable.

    Every field is checked against what is about to be sent, so an approval for
    one body, one target or one key cannot be reused for another. The file is
    the human's artefact: this tool never writes one for production use, it only
    prints what one should contain (`approval` command).
    """
    p = Path(path)
    if not p.is_file():
        return f"approval file {path!r} does not exist (a consumed one is renamed *.used-<utc>)"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"approval file {path!r} is not readable JSON: {exc}"
    if not isinstance(doc, dict):
        return "approval file must hold a JSON object"
    kind, target, body = _write_kind(result), _write_target(result), _write_body(result)
    # `host` is part of the approval because the approval authorises a write to a
    # named service, not merely a body: the destination is as much a part of what
    # a commander approves as the text, and pinning it here means no environment,
    # alias or typo can point an approved signed URL — a replayable capability —
    # at a host nobody approved. It carries the port when there is one, so
    # `technocore.chat` does not authorise `technocore.chat:8443`.
    want = {"kind": kind, "target": target, "did": did, "sha256": body_sha256(body),
            "host": host}
    for field, expected in want.items():
        got = doc.get(field)
        if not isinstance(got, str) or got.strip() != expected:
            return (f"approval field {field!r} is {got!r}, but this write needs {expected!r}"
                    + (" (SHA-256 of the swept body)" if field == "sha256" else "")
                    + (" (the host this write is addressed to)" if field == "host" else ""))
    # `body_swept` is written for the human to read; if it is present it must
    # describe the same body the hash commits to, or the file shows one text and
    # authorises another.
    swept_body = doc.get("body_swept")
    if swept_body is not None:
        if not isinstance(swept_body, str):
            return f"approval field 'body_swept' must be a string, not {type(swept_body).__name__}"
        if body_sha256(swept_body) != doc["sha256"].strip():
            return ("approval field 'body_swept' does not hash to the approved 'sha256' "
                    f"({body_sha256(swept_body)} vs {doc['sha256'].strip()}); the file shows "
                    "one body and authorises another")
    approver = doc.get("approved_by")
    if not isinstance(approver, str) or not approver.strip():
        return "approval field 'approved_by' must name who approved this body"
    if approver.strip() == APPROVER_PLACEHOLDER or re.fullmatch(r"<.*>", approver.strip()):
        # The `approval` command prints this placeholder on purpose: the file it
        # prints must be edited by a person before it can authorise anything.
        return ("approval field 'approved_by' is still the placeholder "
                f"{approver.strip()!r}; a person must write their name there")
    # Required, not optional: an approval without an expiry is a standing
    # authorisation for a body someone approved once, and a file left on a device
    # would still open the production lane weeks later. The `approval` command
    # emits 48 hours.
    expires = doc.get("expires")
    if expires is None:
        return ("approval field 'expires' is required (UTC YYYY-MM-DDTHH:MM:SSZ); an "
                "approval that never expires is a standing production-write capability")
    import calendar

    try:
        exp = calendar.timegm(time.strptime(str(expires), "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return f"approval field 'expires' {expires!r} is not YYYY-MM-DDTHH:MM:SSZ (UTC)"
    if time.time() > exp:
        return f"approval expired at {expires}"
    if kind == "set" and result["ns"] in ("room-owners", "room-allow", "room-nonce"):
        # HANDOFF.md §2.6: ownership notes are not touched until Phase 2 needs them.
        if doc.get("ownership") is not True:
            return (f"{result['ns']} is an ownership namespace (HANDOFF.md §2.6); the approval "
                    "must carry \"ownership\": true to permit it")
    return doc


def _consume_approval(path: str, nonce: object = None) -> str:
    """Rename the approval so it cannot authorise a second attempt. Done before
    the request leaves, so an interrupted send cannot be replayed on retry.

    The nonce is in the name because the UTC stamp has one-second resolution:
    two consumptions inside the same second would otherwise write the same name
    and the first record would be silently replaced. The nonce is unique per
    room by construction; the unsigned note lane has none, so it falls back to
    a distinguishing suffix rather than a colliding one."""
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    tag = str(nonce) if nonce is not None else f"unsigned-{os.getpid()}"
    used = f"{path}.used-{stamp}-{tag}"
    os.replace(path, used)
    return used


def _show_before_send(result: dict, host: str, raw_body: str, approval_path: str) -> None:
    kind = _write_kind(result)
    print("=" * 72)
    print("PRODUCTION WRITE — review before confirming")
    print(f"  host           : {host}")
    print(f"  lane           : {kind}")
    print(f"  target         : {_write_target(result)}")
    print(f"  signer DID     : {result['did']}")
    print(f"  body (as given): {raw_body!r}")
    print(f"  body (swept)   : {_write_body(result)!r}")
    print(f"  body sha256    : {body_sha256(_write_body(result))}")
    if "canonical" in result:
        canonical = result["canonical"].encode("utf-8")
        print(f"  canonical      : {result['canonical']!r}")
        print(f"  canonical hex  : {canonical.hex()}")
        print(f"  nonce          : {result['nonce']}")
        print(f"  signature      : {result['sig']}")
    else:
        print("  canonical      : (unsigned lane — no signature, world-writable note)")
    print(f"  approval file  : {approval_path}  (will be consumed on send)")
    print(f"  proof log      : {PROOF_LOG}")
    print("=" * 72)


def _open_private(path: Path, flags: int) -> int:
    """Open (creating if needed) and force mode 600 on the descriptor. The mode
    argument to os.open applies only to a file it creates; a proof log or
    snapshot that already exists with a wider mode — restored from a backup,
    created by hand — keeps it. These files carry nonces and signatures, which
    are a live write capability until the record is buried, so the mode is
    enforced on every open, the way the seed file's is."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
    except OSError:
        os.close(fd)
        raise
    return fd


def _proof_append(entry: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fd = _open_private(PROOF_LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def _get(url: str, timeout: int = 30) -> tuple[int, dict, bytes]:
    """Plain GET for the post-write snapshot. Returns (status, headers, body)
    with the body as the raw bytes received — an /export is promised byte-exact
    and is hashed and stored as such; decoding is the caller's business. A
    transport failure is (0, {}, reason-as-bytes): the snapshot is evidence,
    not a step that may abort the record of a write that already happened.
    Redirects are refused, as in `_send`."""
    import urllib.error

    req = _request(url, "application/json, application/x-ndjson, text/plain, */*")
    try:
        with _opener().open(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()
    except Exception as exc:  # noqa: BLE001 — any transport failure is data here
        return 0, {}, f"{type(exc).__name__}: {exc}".encode("utf-8")


def _snapshot_after_send(result: dict, base: str, stamp: str) -> dict:
    """After an accepted room write: save the byte-exact /export beside the proof
    log and locate our record (by nonce) in the JSON read, so the proof carries
    the server-assigned (generation, seq, ts) the commander asks for."""
    out: dict = {}
    if _write_kind(result) != "say":
        status, _, body = _get(f"{base}/kv/{_write_target(result)}")
        out["readback"] = {"status": status, "body": body[:400].decode("utf-8", "replace")}
        return out
    room = result["room"]
    status, headers, body = _get(f"{base}/r/{room}/export")
    if status == 200:
        # Raw bytes, binary mode, and the hash over those same bytes: the file
        # on disk IS the export, with no newline translation and no decoding.
        # The nonce is in the name because it is unique per room by
        # construction (strictly increasing), where a one-second stamp is not;
        # O_EXCL then makes overwriting an earlier snapshot impossible rather
        # than merely unlikely, since a proof entry points at it by hash.
        path = LOGS_DIR / f"export-{room}-{stamp}-{result['nonce']}.jsonl"
        fd = _open_private(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, "wb") as fh:
            fh.write(body)
        out["export"] = {"file": str(path), "generation": headers.get("x-room-generation"),
                         "lines": body.count(b"\n"), "bytes": len(body),
                         "sha256": hashlib.sha256(body).hexdigest()}
    else:
        out["export"] = {"status": status, "error": body[:300].decode("utf-8", "replace")}
    status, _, body = _get(f"{base}/r/{room}?format=json&limit=50")
    if status == 200:
        try:
            view = json.loads(body.decode("utf-8"))
            out["room"] = {"generation": view.get("generation"), "last_seq": view.get("last_seq"),
                           "count": view.get("count")}
            for msg in view.get("messages", []):
                if msg.get("nonce") == result["nonce"] and msg.get("from") == result["did"]:
                    out["record"] = {k: msg.get(k) for k in ("seq", "ts", "nonce", "sig")}
                    out["record"]["generation"] = view.get("generation")
        except ValueError:
            out["room"] = {"error": "read returned non-JSON"}
    else:
        out["room"] = {"status": status, "error": body[:300].decode("utf-8", "replace")}
    return out


def _ts_epoch(ts: str) -> float | None:
    """A server `ts` ("2026-09-02T22:10:23.323177Z") as an epoch, or None."""
    from datetime import datetime

    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError, TypeError):
        return None


def _readback(result: dict, base: str, dispatched_at: float) -> tuple[int, str, dict]:
    """Settle an indeterminate send by reading the target back.

    Returns (exit code, outcome, evidence). Nothing here can resend; the only
    question is whether a retry (with a fresh approval) would duplicate a
    record, so absence has to be PROVED, never inferred from a window that
    may simply have rolled past the write.

    For a room write the whole retained ring is read (`/export`) and searched
    for our nonce and DID. Presence is acceptance. Absence counts only if the
    ring still holds a record from before the request was dispatched: the
    ring is a contiguous tail, so if it reaches back past our dispatch and our
    record is not in it, our record did not land. A ring that has already
    rolled past the dispatch time — a busy room after a 30-second timeout —
    proves nothing, and stays indeterminate.

    For a note the stored value is compared exactly, whole line to whole
    line, never by substring: a proposed value that is a substring of the old one would
    otherwise read as landed.
    """
    if _write_kind(result) == "say":
        room = result["room"]
        status, headers, body = _get(f"{base}/r/{room}/export")
        if status != 200:
            return EXIT_INDETERMINATE, "indeterminate", {
                "status": status, "error": body[:300].decode("utf-8", "replace")}
        generation = headers.get("x-room-generation")
        oldest: float | None = None
        for line in body.splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("nonce") == result["nonce"] and rec.get("from") == result["did"]:
                return 0, "accepted-by-readback", {
                    k: rec.get(k) for k in ("seq", "ts", "nonce", "sig")
                } | {"generation": generation}
            when = _ts_epoch(rec.get("ts"))
            if when is not None and (oldest is None or when < oldest):
                oldest = when
        if oldest is not None and oldest <= dispatched_at:
            return 2, "not-landed-by-readback", {
                "generation": generation, "ring_reaches_back_to": oldest,
                "dispatched_at": dispatched_at}
        return EXIT_INDETERMINATE, "indeterminate", {
            "generation": generation, "reason": "the retained ring does not reach back to "
            "the dispatch time, so absence cannot be proved",
            "ring_reaches_back_to": oldest, "dispatched_at": dispatched_at}
    status, _, body = _get(f"{base}/kv/{_write_target(result)}")
    if status != 200:
        return EXIT_INDETERMINATE, "indeterminate", {
            "status": status, "error": body[:300].decode("utf-8", "replace")}
    stored = _note_value(body.decode("utf-8", "replace"))
    if stored == _write_body(result):
        return 0, "accepted-by-readback", {"value": stored[:400]}
    return 2, "not-landed-by-readback", {"value": stored[:400]}


def _note_value(text: str) -> str:
    """The exact stored value out of a note read. Upstream `note_read` answers
    `<banner>\n\n<value>` plus an optional `\n\n# budget: …` footer (there is
    no JSON form for a single note), and a value is one swept line, so the
    value is the first line after the banner's blank line — whole, never a
    substring test against the page."""
    lines = text.split("\n")
    if lines and lines[0].startswith("!!"):
        return lines[2] if len(lines) > 2 else ""
    return lines[0] if lines else ""


def _proof_preflight() -> str | None:
    """Prove the proof log can be written BEFORE anything is sent. A write
    whose record cannot be kept must not happen; finding that out after the
    server has stored it is too late. Returns the reason on failure."""
    try:
        os.close(_open_private(PROOF_LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND))
    except OSError as exc:
        return f"proof log {PROOF_LOG} is not writable ({exc})"
    return None


def production_fetch(result: dict, args, raw_body: str) -> int:
    """The only path by which `--fetch` reaches a non-loopback host."""
    base = args.base
    host = _destination(base)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    entry = {
        "ts": stamp, "host": host, "kind": _write_kind(result), "target": _write_target(result),
        "did": result["did"], "body_raw": raw_body, "body_clean": _write_body(result),
        "body_sha256": body_sha256(_write_body(result)),
        "canonical": result.get("canonical"),
        "canonical_hex": result["canonical"].encode("utf-8").hex() if "canonical" in result else None,
        "nonce": result.get("nonce"), "sig": result.get("sig"), "backend": BACKEND,
    }

    def refused(reason: str) -> int:
        entry.update({"outcome": "gate-refused", "reason": reason})
        try:
            _proof_append(entry)
        except OSError as exc:
            print(f"warning: could not record the refusal in {PROOF_LOG}: {exc}",
                  file=sys.stderr)
        return _refuse(reason)

    problem = _proof_preflight()
    if problem:
        return refused(problem)
    if not getattr(args, "production", False):
        return refused(f"{host} is not loopback and --production was not given")
    cleartext = _cleartext_refusal(base)
    if cleartext:
        return refused(cleartext)
    approval_path = getattr(args, "approval", None)
    if not approval_path:
        return refused("--approval <file> is required for a production write")
    approval = _load_approval(approval_path, result, result["did"], host)
    if isinstance(approval, str):
        return refused(approval)
    entry["approval"] = {"file": approval_path, "sha256": approval["sha256"],
                         "approved_by": approval["approved_by"],
                         "created": approval.get("created"), "note": approval.get("note")}
    # The TTY check comes BEFORE the review screen, not after. The screen exists
    # to be read by a person about to type a confirmation; with no terminal there
    # is nobody to read it, and printing it anyway writes the nonce and the
    # signature — together a replayable capability — into whatever pipe, log or
    # cron mail captured the run.
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return refused("interactive confirmation needs a TTY on stdin and stdout; "
                       "a production write cannot be scripted or piped")
    _show_before_send(result, host, raw_body, approval_path)
    expected = _write_target(result)
    try:
        typed = input(f"Type the target exactly ({expected}) to send, anything else aborts: ")
    except (EOFError, KeyboardInterrupt):
        typed = ""
    if typed.strip() != expected:
        return refused("confirmation did not match; aborted by operator")
    try:
        entry["approval"]["consumed_as"] = _consume_approval(approval_path, result.get("nonce"))
    except OSError as exc:
        # The approval could not be made single-use (read-only directory, a name
        # that already exists). Nothing is sent — but the attempt still earns its
        # proof line, which is what `refused` guarantees.
        return refused(f"the approval file could not be consumed ({exc}); nothing was sent "
                       "because an approval that survives a send is not single-use")
    dispatched_at = time.time()
    entry["dispatched_at"] = dispatched_at
    code = _send(result["url"])
    entry["http_exit"] = code
    entry["outcome"] = {0: "accepted", 1: "server-refused", 2: "not-sent",
                        EXIT_INDETERMINATE: "indeterminate"}[code]
    if code == EXIT_INDETERMINATE:
        # The reply was lost after dispatch. Read the target back and let what
        # the server holds decide, never the exception.
        code, entry["outcome"], entry["readback"] = _readback(result, base, dispatched_at)
        print(f"--> read back: {entry['outcome']}")
        if code == EXIT_INDETERMINATE:
            print("--> STILL UNKNOWN: read the room back by hand before any retry; a retry "
                  "needs a fresh approval and may duplicate an accepted record.")
        elif code == 2:
            print("--> the write did not land; a retry needs a fresh approval.")
    # The write's own record goes to disk NOW, before the snapshot is even
    # attempted: the snapshot can be large and can be the thing that fills the
    # disk, and an audit entry that waits for it is an audit entry that can be
    # lost. The snapshot gets its own line afterwards, keyed by nonce.
    _proof_append(entry)
    print(f"--> proof: {PROOF_LOG} ({entry['outcome']})")
    if code == 0:
        snapshot = {"ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), "record": "snapshot",
                    "target": entry["target"], "nonce": entry["nonce"], "did": entry["did"]}
        try:
            snapshot["after"] = _snapshot_after_send(result, base, stamp)
        except Exception as exc:  # noqa: BLE001 — recorded, never fatal
            snapshot["after"] = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"--> snapshot FAILED ({snapshot['after']['error']}); the write stands and "
                  "is already recorded. Fetch /export by hand.", file=sys.stderr)
        rec = snapshot["after"].get("record") or entry.get("readback")
        if rec and "seq" in rec:
            print(f"--> recorded: room={result.get('room')} generation={rec.get('generation')} "
                  f"seq={rec.get('seq')} nonce={rec.get('nonce')} ts={rec.get('ts')}")
        exp = snapshot["after"].get("export", {})
        if exp.get("file"):
            print(f"--> export snapshot: {exp['file']} (generation {exp.get('generation')}, "
                  f"{exp.get('lines')} lines)")
        try:
            _proof_append(snapshot)
        except OSError as exc:
            print(f"warning: the snapshot line could not be appended ({exc}); the accepted "
                  "entry above is already on disk.", file=sys.stderr)
    return code


def _emit(result: dict, args, raw_body: str | None = None) -> None:
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if result["urlBytes"] > 4096:
        print(f"warning: URL is {result['urlBytes']} bytes; the edge limit is ~16 KB "
              "and long non-Latin text may need the POST lane.", file=sys.stderr)
    if getattr(args, "fetch", False):
        if is_loopback(args.base):
            raise SystemExit(_send(result["url"]))
        raise SystemExit(production_fetch(result, args, raw_body if raw_body is not None
                                          else _write_body(result)))
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
    _emit(build_say(load_seed(), args.room, args.text, args.base), args, raw_body=args.text)


def cmd_set(args) -> None:
    _emit(build_set(load_seed(), args.ns, args.key, args.value, args.base,
                    if_absent=args.if_absent), args, raw_body=args.value)


def cmd_approval(args) -> None:
    """Print the approval JSON a production write of this exact body would need.

    Deliberately prints rather than writes: the approval is the human's act, made
    after the commander has approved the body, and writing it here would let one
    command both propose and approve. The hash is over the swept body, which is
    what will be signed and stored.
    """
    if args.kind == "say":
        if not NAME_RE.fullmatch(args.target):
            raise SystemExit(f"{args.target!r} is not a valid room name")
        clean = swept(args.body, MAX_TEXT_CHARS)
    else:
        if "/" not in args.target:
            raise SystemExit(f"for kind={args.kind} the target is "
                             + ("<ns>/<key>" if args.kind == "set" else "<shard>/<key>, the "
                                "note path without the /kv/ prefix (see `fingerprint`)"))
        if args.target.startswith("/kv/") or args.target.startswith("kv/"):
            raise SystemExit(f"target {args.target!r} must not carry the /kv/ prefix; the "
                             "readers add it")
        clean = swept(args.body, MAX_VALUE_CHARS)
    did = args.did
    if not did and (PUBLIC_DIR / "did.txt").exists():
        did = (PUBLIC_DIR / "did.txt").read_text().strip()
    if not did:
        # Last resort, and only for the public value: the seed is read to derive the DID.
        did = did_from_pubkey(PUBKEY(load_seed()))
    if not is_did_like(did):
        raise SystemExit(f"not a valid did:key: {did!r}")
    # The destination this approval will be checked against: `--host` if given,
    # otherwise the one `--base` names — so an approval prepared for a rehearsal
    # server matches that server, and the phone's default stays technocore.chat.
    host = getattr(args, "host", None) or _destination(getattr(args, "base", None)
                                                       or DEFAULT_BASE)
    doc = {
        "kind": args.kind, "target": args.target, "did": did, "sha256": body_sha256(clean),
        "host": host, "body_swept": clean, "approved_by": "<name of the approver>",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "expires": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 48 * 3600)),
        "note": "one-time; consumed on send; the tool checks kind/target/did/sha256/host",
    }
    if args.kind == "set" and args.target.split("/", 1)[0] in ("room-owners", "room-allow"):
        doc["ownership"] = False
    print(json.dumps(doc, indent=2, ensure_ascii=False))


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
    _emit(build_set(seed, "room-owners", room, did, args.base, if_absent=True), args,
          raw_body=did)


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
    raw_value = " ".join(parts)
    value = swept(raw_value, MAX_VALUE_CHARS)
    url = f"{args.base}/kv/{note_path(did)}/set/{_enc(value)}"
    _emit({"did": did, "notePath": f"/kv/{note_path(did)}", "value": value,
           "url": url, "urlBytes": len(url.encode()), "lane": "unsigned (world-writable)"},
          args, raw_body=raw_value)


def cmd_checkin(args) -> None:
    """A signed check-in: a real message, attributable to the permanent DID.

    Keep it substantive. A room full of 'gm' from one key is the low-diversity
    pattern `/rooms` engagement aggregates are built to expose, and this project
    does not farm message counts.
    """
    seed = load_seed()
    _emit(build_say(seed, args.room, args.text, args.base), args, raw_body=args.text)


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
    common.add_argument("--fetch", action="store_true", default=argparse.SUPPRESS,
                        help="send the request from here and print the server's reply "
                             "(the URL is never printed; needs a network that reaches the host)")
    common.add_argument("--production", action="store_true", default=argparse.SUPPRESS,
                        help="with --fetch: allow a non-loopback host, subject to --approval "
                             "and an interactive confirmation (HANDOFF.md §5.4)")
    common.add_argument("--approval", default=argparse.SUPPRESS,
                        help="with --fetch --production: the one-time approval file carrying "
                             "the SHA-256 of the swept body (see the `approval` command)")

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

    ap = sub.add_parser("approval", parents=[common],
                        help="print the one-time approval JSON a production write would need")
    ap.add_argument("target", help="room name for kind=say, <ns>/<key> for kind=set, or the "
                                   "note path without /kv/ for kind=note-unsigned")
    ap.add_argument("body", help="the exact body that will be sent")
    ap.add_argument("--kind", choices=("say", "set", "note-unsigned"), default="say")
    ap.add_argument("--did", help="signer DID (default: identity/public/did.txt)")
    ap.add_argument("--host", help="destination the write is addressed to, host or host:port "
                                   "(default: the one --base names, else "
                                   f"{urllib.parse.urlsplit(DEFAULT_BASE).hostname})")

    args = p.parse_args()
    if not getattr(args, "base", None):
        # $TECHNOCORE_BASE is a convenience for pointing reads and the loopback
        # test lane at a local server. A production write does not take it: the
        # destination of a signed capability URL is named on the command line or
        # it is the default host, so no exported variable — set by a profile, a
        # forgotten `export`, or another process — can redirect an approved write.
        # The approval's `host` field then has to agree with it as well, so
        # `approval` refuses the variable too: otherwise a stray export in the
        # phone's profile prints an approval for a host the write will not use,
        # and the operator, told to leave `host` as printed, is handed a refusal
        # at the one moment the clock is running.
        if getattr(args, "production", False) or args.cmd == "approval":
            args.base = DEFAULT_BASE
        else:
            args.base = os.environ.get("TECHNOCORE_BASE", DEFAULT_BASE)
    {
        "keygen": cmd_keygen, "did": cmd_did, "fingerprint": cmd_fingerprint,
        "say": cmd_say, "set": cmd_set, "claim": cmd_claim, "backup-check": cmd_backup_check,
        "selftest": cmd_selftest, "didnote": cmd_didnote, "checkin": cmd_checkin,
        "where": cmd_where, "approval": cmd_approval,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
