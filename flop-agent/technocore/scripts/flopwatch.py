#!/usr/bin/env python3
"""flopwatch — keep the identity alive, and catch the testnet the hour it lands.

Two jobs, because they share a schedule and forgetting either is expensive:

1. **KEEPALIVE.** Upstream reaps anything untouched for 7 days —
   `store.py: IDLE_SECONDS = 7 * 86400  # untouched rooms/notes are reaped`.
   Notes have no ring, so volume never retires them, but idleness does. The DID
   note is the durable identity record and it *will* be deleted a week after its
   last write. This re-publishes it.

2. **WATCH.** The testnet client and faucet have to be announced somewhere, and
   the plausible channels are few: the official repo's releases, a new repo in
   the org, the service's own manifest, or a new room on the discovery lane.
   This snapshots those and reports only what changed.

Zero dependencies — stdlib only.

**This tool never needs the private key.** The DID note lane is unsigned
(signed note writes exist only for `room-owners` and `room-allow`), so a
keepalive needs the *public* DID and nothing else. That is deliberate: the
weekly refresh can therefore run anywhere — another machine, a cron job, a
different agent — without the seed ever leaving the device that made it.

Identity is resolved in this order:
    $FLOP_DID  ->  --did  ->  identity/public/did.txt  ->  derived from the seed
The seed is the last resort and is only ever used to compute the public DID.

Usage:
    python3 flopwatch.py status              # days until the DID note is reaped
    FLOP_DID=did:key:z6Mk... python3 flopwatch.py keepalive --write   # no seed needed
    python3 flopwatch.py keepalive           # print the refresh URL
    python3 flopwatch.py keepalive --write   # perform the refresh
    python3 flopwatch.py watch               # report changes since last run
    python3 flopwatch.py watch --write-keepalive   # both, in one command
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import flopdid  # reuse the identity resolution, never the seed  # noqa: E402

STATE_FILE = flopdid.AGENT_ROOT / "secrets" / "watch_state.json"
BASE = os.environ.get("TECHNOCORE_BASE", "https://technocore.chat")
REPO = "flop-labs/technocore-chat"
IDLE_DAYS = 7  # store.py IDLE_SECONDS

# Anything whose appearance would change what we should be doing today.
#
# Matched at a word boundary, and only ever reported when a target CHANGES and
# the word is NEW there. Both rules matter: the plain substring "token" hits
# CHAT_STATS_TOKEN on every page of the manual, and "register" hits "/humans
# registers the read/post lanes". A watcher that cries wolf on the baseline is
# one you stop reading, which costs exactly the alert it was built for.
SIGNALS = (
    "testnet", "faucet", "genesis", "mainnet", "airdrop", "snapshot",
    "eligib", "miner", "validator", "epoch", "leaderboard", "reward",
    "registration", "claim", "stake", "tokenomics", "allocation",
)

# Cheap, public, and each one is a plausible announcement channel.
TARGETS = [
    ("technocore/agent.json", f"{BASE}/.well-known/agent.json"),
    ("technocore/config", f"{BASE}/config"),
    ("technocore/llms.txt", f"{BASE}/llms.txt"),
    ("technocore/rooms", f"{BASE}/rooms?limit=40"),
    # Server-written and NOT world-writable: the one discovery surface a
    # stranger cannot forge an entry into (README: "/r/events is the one
    # non-world-writable surface").
    ("technocore/events", f"{BASE}/r/events"),
    # Raw file reads need no API budget and survive an unauthenticated 403 on
    # api.github.com, so the doc surface is watched even where the API is not.
    ("github/README", f"https://raw.githubusercontent.com/{REPO}/main/README.md"),
    ("github/CHANGELOG", f"https://raw.githubusercontent.com/{REPO}/main/CHANGELOG.md"),
    ("github/releases", f"https://api.github.com/repos/{REPO}/releases?per_page=5"),
    ("github/tags", f"https://api.github.com/repos/{REPO}/tags?per_page=5"),
    # A testnet client would most likely arrive as a NEW repository, not a
    # commit to this one.
    ("github/org-repos", "https://api.github.com/orgs/flop-labs/repos?per_page=100&sort=created"),
]


def _load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _save(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_FILE.parent, 0o700)
    fd = os.open(STATE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(state, fh, indent=2)


def _fetch(url: str, timeout: int = 25) -> tuple[str | None, str]:
    """Return (body, note). Never raises — an unreachable target is data, not a
    crash, because half these hosts are blocked from some environments."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "flopwatch (participation agent; contact via github.com/keisuku)",
        "Accept": "application/json, text/plain, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace"), f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # DNS, TLS, egress policy, timeout
        return None, f"unreachable ({type(e).__name__})"


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def _signals_in(body: str) -> list[str]:
    low = body.lower()
    return [s for s in SIGNALS if re.search(rf"\b{re.escape(s)}", low)]


# --- identity ---------------------------------------------------------------
def resolve_did(explicit: str | None = None) -> str:
    """The public DID, preferring every source that is not the private key.

    Reaching for the seed to learn a *public* value is a needless handling of
    key material, and it is what would otherwise chain the weekly keepalive to
    the one device holding it.
    """
    for candidate in (explicit, os.environ.get("FLOP_DID")):
        if candidate:
            did = candidate.strip()
            if not flopdid.is_did_like(did):
                raise SystemExit(f"not a valid did:key: {did!r}")
            return did
    published = flopdid.PUBLIC_DIR / "did.txt"
    if published.exists():
        did = published.read_text().strip()
        if flopdid.is_did_like(did):
            return did
    return flopdid.did_from_pubkey(flopdid.PUBKEY(flopdid.load_seed()))


# --- keepalive --------------------------------------------------------------
def _did_note_url(explicit: str | None = None) -> tuple[str, str, str]:
    did = resolve_did(explicit)
    path = flopdid.note_path(did)
    return did, path, f"{BASE}/kv/{path}/set/{urllib.parse.quote(did, safe='')}"


def cmd_status(args) -> None:
    state = _load()
    last = state.get("keepalive_utc")
    did = resolve_did(getattr(args, "did", None))
    print(f"DID        : {did}")
    print(f"DID note   : /kv/{flopdid.note_path(did)}")
    if not last:
        print("last refresh: never recorded by this tool")
        print(f"ACTION      : refresh within {IDLE_DAYS} days of your last write, or it is reaped.")
        return
    days = (time.time() - last) / 86400
    left = IDLE_DAYS - days
    print(f"last refresh: {days:.1f} days ago")
    if left <= 0:
        print("STATUS      : *** OVERDUE — the note may already be deleted. Re-publish now. ***")
    elif left <= 2:
        print(f"STATUS      : *** {left:.1f} days left — refresh now. ***")
    else:
        print(f"STATUS      : ok, {left:.1f} days of margin")


def cmd_keepalive(args) -> None:
    did, path, url = _did_note_url(getattr(args, "did", None))
    if not args.write:
        print(f"DID note path : /kv/{path}")
        print("Fetch this to refresh it (resets the 7-day idle clock):")
        print(url)
        print("\nOr run:  python3 flopwatch.py keepalive --write")
        return
    body, note = _fetch(url)
    state = _load()
    if body is None:
        print(f"refresh FAILED: {note}")
        print("The note was NOT refreshed. Retry from a network that reaches technocore.chat.")
        raise SystemExit(1)
    state["keepalive_utc"] = time.time()
    _save(state)
    print(f"DID note refreshed ({note}). Idle clock reset for {IDLE_DAYS} days.")
    # Confirm it reads back as ours rather than trusting the write.
    check, cnote = _fetch(f"{BASE}/kv/{path}")
    if check is None:
        print(f"  note: could not read back ({cnote})")
    elif did in check:
        print("  verified: the note reads back with our DID.")
    else:
        print("  WARNING: the note does NOT contain our DID — it is world-writable and")
        print("  someone may have overwritten it. Re-publish and check again.")


# --- watch ------------------------------------------------------------------
def cmd_watch(args) -> None:
    state = _load()
    seen = state.setdefault("targets", {})
    changes, unreachable = [], []

    for name, url in TARGETS:
        body, note = _fetch(url)
        if body is None:
            unreachable.append(f"{name}: {note}")
            continue
        digest = _digest(body)
        prev = seen.get(name, {}).get("digest")
        hits = _signals_in(body)
        if prev is None:
            seen[name] = {"digest": digest, "signals": hits}
            changes.append((name, "FIRST SNAPSHOT", [], body))  # baseline: never alarms
        elif prev != digest:
            new_hits = [h for h in hits if h not in seen[name].get("signals", [])]
            seen[name] = {"digest": digest, "signals": hits}
            changes.append((name, "CHANGED", new_hits, body))

    _save(state)

    print(f"=== flopwatch {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())} ===")
    if unreachable:
        print("\nUnreachable (not a failure — some hosts are blocked from some networks):")
        for u in unreachable:
            print(f"  - {u}")

    if not changes:
        print("\nNo changes since last run.")
    for name, kind, hits, body in changes:
        print(f"\n[{kind}] {name}")
        if hits:
            print(f"  !! SIGNAL WORDS: {', '.join(hits)}")
            for line in body.splitlines():
                if any(h in line.lower() for h in hits):
                    print(f"     | {line.strip()[:200]}")
                    break
        elif kind == "CHANGED":
            print("  (changed, no new signal words — likely routine)")
        else:
            print("  baseline recorded; future runs report only what changes here")

    if any(h for _, _, h, _ in changes):
        print("\n>>> A signal word appeared. Read the official source before acting,")
        print(">>> and treat anything asking for a wallet or a payment as hostile")
        print(">>> until flop.finance and the official GitHub agree on it.")

    if args.write_keepalive:
        print()
        cmd_keepalive(argparse.Namespace(write=True, did=getattr(args, "did", None)))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ident = argparse.ArgumentParser(add_help=False)
    ident.add_argument("--did", default=None,
                       help="public did:key to keep alive (or set $FLOP_DID). No seed needed.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", parents=[ident], help="days until the DID note is reaped")
    k = sub.add_parser("keepalive", parents=[ident], help="refresh the DID note")
    k.add_argument("--write", action="store_true", help="perform the fetch, not just print it")
    w = sub.add_parser("watch", parents=[ident], help="report changes on the announcement channels")
    w.add_argument("--write-keepalive", action="store_true", help="also refresh the DID note")
    args = p.parse_args()
    {"status": cmd_status, "keepalive": cmd_keepalive, "watch": cmd_watch}[args.cmd](args)


if __name__ == "__main__":
    main()
