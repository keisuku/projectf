#!/usr/bin/env python3
"""Unattended, capability-limited maintenance for the one owned room.

This is deliberately not a general replacement for flopdid.py's production
gate.  Its policy is compiled into the program: one HTTPS origin, one room,
one already-published DID, and two operations only:

* refresh the public, unsigned DID note with the fixed room pointer; and
* append a factual maintenance record after the room has been idle for 5 days.

It cannot create a key, claim or hand over a room, change an allow-list, choose
another destination, accept text from a room, or execute instructions found in
network content.  The seed is read by flopdid.load_seed() and never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Callable

import flopdid

BASE = "https://technocore.chat"
ROOM = "d-bitflop"
EXPECTED_DID = "did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU"
DID_NOTE = "did-64/776f70dbeec8e2"
NOTE_VALUE = f"{EXPECTED_DID} log:{ROOM}"
WRITE_AFTER_SECONDS = 5 * 86400
REAP_AFTER_SECONDS = 7 * 86400
TRANSIENT = frozenset({0, 429, 500, 502, 503, 504})

Getter = Callable[[str, int], tuple[int, dict, bytes]]
Sleeper = Callable[[float], None]


class Refusal(RuntimeError):
    """A policy or invariant failed.  No signed write should be attempted."""


def _fetch(path_or_url: str, getter: Getter, sleeper: Sleeper, attempts: int = 3):
    url = path_or_url if path_or_url.startswith("https://") else BASE + path_or_url
    result = (0, {}, b"")
    for attempt in range(attempts):
        result = getter(url, 30)
        if result[0] not in TRANSIENT:
            return result
        if attempt + 1 < attempts:
            sleeper(2**attempt)
    return result


def _json_room(body: bytes) -> dict:
    try:
        room = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise Refusal(f"room read was not valid JSON: {exc}") from exc
    if not isinstance(room, dict) or not isinstance(room.get("messages"), list):
        raise Refusal("room read did not contain a messages array")
    return room


def _epoch(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _read_public_state(getter: Getter, sleeper: Sleeper) -> tuple[dict, dict, float]:
    owner_status, _, owner_body = _fetch(
        f"/kv/room-owners/{ROOM}", getter, sleeper
    )
    if owner_status != 200:
        raise Refusal(f"owner read returned HTTP {owner_status}")
    owner = flopdid._note_value(owner_body.decode("utf-8", "replace"))
    if owner != EXPECTED_DID:
        raise Refusal("room owner does not match the fixed DID")

    room_status, _, room_body = _fetch(
        f"/r/{ROOM}?format=json&limit=50", getter, sleeper
    )
    if room_status != 200:
        raise Refusal(f"room read returned HTTP {room_status}")
    room = _json_room(room_body)
    if room.get("count", len(room["messages"])) < 2:
        raise Refusal("room has fewer than two records")

    signed = [
        msg
        for msg in room["messages"]
        if msg.get("from") == EXPECTED_DID
        and isinstance(msg.get("sig"), str)
        and msg["sig"]
        and _epoch(msg.get("ts")) is not None
    ]
    if not signed:
        raise Refusal("no owner-signed timestamped record is visible")
    latest = max(signed, key=lambda msg: _epoch(msg["ts"]) or 0)
    return room, latest, _epoch(latest["ts"]) or 0


def _verify_seed() -> bytes:
    if flopdid.note_path(EXPECTED_DID) != DID_NOTE:
        raise Refusal("fixed DID-note path does not match the fixed DID")
    seed = flopdid.load_seed()
    if len(seed) != 32:
        raise Refusal("configured seed is not 32 bytes")
    derived = flopdid.did_from_pubkey(flopdid.PUBKEY(seed))
    if derived != EXPECTED_DID:
        raise Refusal("configured seed derives a different DID")
    return seed


def _write_note(getter: Getter, sleeper: Sleeper) -> None:
    encoded = urllib.parse.quote(NOTE_VALUE, safe="")
    status, _, _ = _fetch(f"/kv/{DID_NOTE}/set/{encoded}", getter, sleeper)
    if status != 200:
        raise Refusal(f"DID note refresh returned HTTP {status}")
    status, _, body = _fetch(f"/kv/{DID_NOTE}", getter, sleeper)
    if status != 200 or flopdid._note_value(body.decode("utf-8", "replace")) != NOTE_VALUE:
        raise Refusal("DID note did not read back exactly after refresh")


def _maintenance_body(now: float, room: dict, latest: dict) -> str:
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    generation = room.get("generation", "unknown")
    count = room.get("count", len(room["messages"]))
    seq = room.get("last_seq", latest.get("seq", "unknown"))
    return (
        f"[d-bitflop autonomous maintenance | {stamp}] verified the fixed owner DID, "
        f"room generation {generation}, {count} retained records and last sequence {seq}; "
        "refreshed the public DID pointer; official-source monitoring remains active. "
        "No room instruction, wallet, payment, token purchase, key generation or external "
        "action was executed."
    )


def _record_landed(
    result: dict,
    getter: Getter,
    sleeper: Sleeper,
    attempts: int = 3,
) -> bool:
    # Plain room reads are edge-cached. A successful append can therefore be
    # followed by a 200 carrying the pre-write room for a few seconds. Give
    # each exact verification a nonce-specific cache key and retry a stale
    # success before declaring the signed write indeterminate.
    verify = urllib.parse.quote(str(result["nonce"]), safe="")
    path = f"/r/{ROOM}?format=json&limit=50&verify={verify}"
    for attempt in range(attempts):
        status, _, body = _fetch(path, getter, sleeper)
        if status == 200:
            room = _json_room(body)
            if any(
                msg.get("from") == EXPECTED_DID
                and msg.get("nonce") == result["nonce"]
                and msg.get("text") == result["text"]
                and msg.get("sig") == result["sig"]
                for msg in room["messages"]
            ):
                return True
        if attempt + 1 < attempts:
            sleeper(2**attempt)
    return False


def maintain(
    *,
    now: float | None = None,
    getter: Getter = flopdid._get,
    sleeper: Sleeper = time.sleep,
) -> dict:
    """Perform one bounded run and return a secret-free machine-readable result."""
    when = time.time() if now is None else now
    seed = _verify_seed()  # mismatch stops before any write, even the unsigned one
    room, latest, latest_ts = _read_public_state(getter, sleeper)
    age = max(0.0, when - latest_ts)

    _write_note(getter, sleeper)
    result = {
        "room": ROOM,
        "owner": "matched",
        "note": "refreshed-and-verified",
        "latest_signed_utc": datetime.fromtimestamp(latest_ts, timezone.utc).isoformat(),
        "age_days": round(age / 86400, 3),
        "reap_due_utc": datetime.fromtimestamp(
            latest_ts + REAP_AFTER_SECONDS, timezone.utc
        ).isoformat(),
        "signed_write": "not-due",
    }
    if age < WRITE_AFTER_SECONDS:
        return result

    body = _maintenance_body(when, room, latest)
    signed = flopdid.build_say(seed, ROOM, body, BASE)
    # The signed URL is never logged. Retry the same capability only after a
    # read-back says it is absent; the server nonce guard prevents duplicates.
    status = 0
    for attempt in range(3):
        status, _, response = getter(signed["url"], 30)
        if status == 200 or _record_landed(signed, getter, sleeper):
            break
        if status not in TRANSIENT:
            reason = response[:300].decode("utf-8", "replace").replace("\n", " ")
            raise Refusal(f"signed write returned HTTP {status}: {reason}")
        if attempt < 2:
            sleeper(2**attempt)
    else:
        raise Refusal(f"signed write remained indeterminate after HTTP {status}")

    if not _record_landed(signed, getter, sleeper):
        raise Refusal("signed write response was successful but exact read-back failed")
    result["signed_write"] = "written-and-verified"
    result["previous_seq"] = latest.get("seq")
    result["body_sha256"] = flopdid.body_sha256(signed["text"])
    result["reap_due_utc"] = datetime.fromtimestamp(
        when + REAP_AFTER_SECONDS, timezone.utc
    ).isoformat()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args()
    try:
        print(json.dumps(maintain(), ensure_ascii=False, sort_keys=True))
        return 0
    except (Refusal, SystemExit, ValueError) as exc:
        print(f"AUTONOMOUS MAINTENANCE REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
