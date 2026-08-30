#!/usr/bin/env python3
"""Rehearse the one-shot d- room claim against the REAL upstream server, offline.

`selftest_upstream.py` proves the crypto and the sweep agree with upstream. This
proves the thing that decides whether the *claim* lands: that the exact URL
`flopdid.py claim` emits is accepted by `flop-labs/technocore-chat`'s own app,
that ownership then refuses everyone else, and that the record it stores
re-verifies offline.

Why it exists: a d- room is claimable exactly once, at creation, and a name spent
on a refused claim is a name gone (upstream `_note_write_gate`: a room with any
message can never be claimed, and a refused claim still burns
/kv/room-nonce/<room>). Rehearsing against the real code costs nothing.

Requires Python >= 3.12 (upstream's floor) and upstream's runtime deps:
    python3.12 -m venv venv && venv/bin/pip install starlette==1.6.0 httpx2 pynacl orjson
    UPSTREAM=/path/to/technocore-chat venv/bin/python rehearse_claim.py [room]

The seed used here is an RFC 8032 test vector. The permanent identity is never
loaded, never touched, and never needed: this rehearses the shape, not the key.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPSTREAM = Path(os.environ.get("UPSTREAM", "/home/user/flop-labs/technocore-chat"))
ROOM = sys.argv[1] if len(sys.argv) > 1 else "d-rehearsal-only"

if not (UPSTREAM / "src" / "app.py").exists():
    sys.exit(f"upstream checkout not found at {UPSTREAM} — set $UPSTREAM")
if sys.version_info < (3, 12):
    sys.exit(f"upstream requires Python >= 3.12; this is {sys.version.split()[0]}")

# A throwaway root, and limits raised so the rehearsal is not rate-limited.
os.environ["CHAT_ROOT"] = tempfile.mkdtemp(prefix="rehearse-chatroot-")
os.environ.setdefault("CHAT_RATE_WRITE", "100000")
os.environ.setdefault("CHAT_RATE_READ", "100000")
os.environ.setdefault("CHAT_RATE_ROOMS_PER_DAY", "100000")

sys.path.insert(0, str(UPSTREAM / "src"))
sys.path.insert(0, str(HERE))
os.chdir(UPSTREAM)  # app.py reads pyproject.toml relative to the checkout

import app as upstream_app  # noqa: E402
import didkey  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

import flopdid  # ours  # noqa: E402

# RFC 8032 test vectors — never the permanent identity.
OWNER = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fa")
STRANGER = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
OWNER_DID = flopdid.did_from_pubkey(flopdid.PUBKEY(OWNER))

client = TestClient(upstream_app.app)
failures: list[str] = []


def check(label: str, response, want: int = 200):
    ok = response.status_code == want
    print(f"[{'OK  ' if ok else 'FAIL'}] {label}: {response.status_code}")
    if not ok:
        failures.append(f"{label}: got {response.status_code}, wanted {want} — {response.text[:200]}")
    return response


# 1. The name must be one flopdid agrees is ownable, before anything is spent.
if not flopdid.ownable(ROOM):
    sys.exit(f"{ROOM!r} is not ownable by our own rule — fix the name, not the test")

# 2. The claim URL our tool builds must be accepted by the server's own gate.
claim = flopdid.build_set(OWNER, "room-owners", ROOM, OWNER_DID, "", if_absent=True)
check("claim the room (the URL `flopdid.py claim` emits)", client.get(claim["url"]))

# 3. The owner note must read back as the claiming key.
owner_note = check("read /kv/room-owners/<room>", client.get(f"/kv/room-owners/{ROOM}"))
if OWNER_DID not in owner_note.text:
    failures.append("the owner note does not name the claiming DID")

# 4. The owner's signed write must land.
say = flopdid.build_say(OWNER, ROOM, "rehearsal: the activity log opens here", "")
check("owner's signed write lands", client.get(say["url"]))

# 5. Everyone else must be refused — this is the whole value of the claim.
check("unsigned write refused", client.get(f"/r/{ROOM}/say/intruder/hello%20there"), want=403)
stranger = flopdid.build_say(STRANGER, ROOM, "a write from a key that is not the owner", "")
check("stranger's signed write refused", client.get(stranger["url"]), want=403)
reclaim = flopdid.build_set(
    STRANGER, "room-owners", ROOM,
    flopdid.did_from_pubkey(flopdid.PUBKEY(STRANGER)), "", if_absent=True,
)
check("stranger's re-claim refused", client.get(reclaim["url"]), want=403)

# 6. The stored record must carry its signature and re-verify with no server
#    involved (upstream #66/#93) — that is what makes the room evidence.
served = client.get(f"/r/{ROOM}?format=json")
try:
    record = json.loads(served.text)["messages"][-1]
    if not record.get("sig"):
        failures.append("the stored record carries no sig field — it cannot be re-verified")
    else:
        didkey.verify(record["from"], record["sig"], f"{ROOM}|{record['nonce']}|{record['text']}")
        print("[OK  ] the stored record re-verifies OFFLINE from the served fields")
except Exception as exc:  # noqa: BLE001 — any failure here is a real finding
    failures.append(f"offline re-verification failed: {exc}")

# 7. The room must export byte-exact (upstream #505), so the log is portable.
export = check("GET /r/<room>/export streams the room", client.get(f"/r/{ROOM}/export"))
if export.status_code == 200 and not export.headers.get("X-Room-Generation"):
    failures.append("export carries no X-Room-Generation header")

print()
if failures:
    print("CLAIM REHEARSAL FAILED — do not spend the real claim:")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)
print(f"claim rehearsal OK for {ROOM!r}  (backend: {flopdid.BACKEND})")
print(f"  upstream: {UPSTREAM}")
print("  verified: the claim URL is accepted, ownership refuses unsigned writes,")
print("            stranger writes and stranger re-claims, the stored record")
print("            re-verifies offline, and the room exports.")
