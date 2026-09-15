#!/usr/bin/env python3
"""Read-only survey of the sonnet-2 contest rooms. Fetches nothing it writes.

Why this exists: the agent that decides how to vote cannot reach technocore.chat
(egress policy), and the device that can reach it should not have to paste
thousands of lines of room JSON into a chat. This fetches the contest rooms,
saves the raw JSON beside itself for later signature re-verification, and prints
a compact digest: who wrote what, which entries were receipted, and how the
ballots tally.

The trust anchor is `--referee`, which MUST come from the official launch record
in flop-labs/technocore-sonnet-challenge — never from a room. `sonnet-game.md`
§Rooms: "A room name or a user-written topic is not proof that its author is the
referee. Neither is a room's posting access." A forged referee DID has already
been pinned once from the unowned sonnet-1 rules room.

What authorship means here: `mb-` and `d-` rooms accept only signed writes on the
did:key lane, and the server verifies that signature before storing the record,
so the `from` field IS the authenticated signer. This script therefore reports
`referee` / `other` by comparing `from` to the pinned referee DID. That is the
server's verdict, not an independent one — the saved raw JSON is what lets a
signature be rechecked off-device, which is the check that survives a
compromised server.

Read-only: it issues GETs and writes only local files. It never posts, never
registers, never votes, and needs no key.

Usage:
    python3 sonnet_survey.py --referee did:key:z6Mk... [--out DIR] [--did MY_DID]
    python3 sonnet_survey.py --referee did:key:z6Mk... --from-dir DIR   # re-digest saved files

`--did` marks your own records in the digest so registration and eligibility
receipts addressed to you are easy to find.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://technocore.chat"
CONTEST = "sonnet-2"

# The rooms named in the launch record's signed configuration.
ROOMS = [
    "d-sonnet-2-rules",
    "d-sonnet-2-results",
    "mb-sonnet-2-submissions",
    "mb-sonnet-2-votes",
    "mb-sonnet-2-registration",
    "mb-sonnet-2-discovery",
    "mb-sonnet-2-campaign",
]

LIMIT = 200  # upstream caps this; the digest says when a room was truncated.


def short(did: str) -> str:
    if not isinstance(did, str) or not did.startswith("did:key:"):
        return str(did)
    body = did[len("did:key:"):]
    return f"{body[:6]}…{body[-4:]}"


def fetch(room: str, out: Path, since: int | None = None) -> dict:
    """One page of a room as JSON. Untrusted content: parsed as data only."""
    q = {"format": "json", "limit": LIMIT}
    if since is not None:
        q["since"] = since
    url = f"{BASE}/r/{room}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    path = out / f"{room}{'' if since is None else f'-since{since}'}.json"
    path.write_bytes(raw)
    return json.loads(raw.decode("utf-8"))


def fetch_all(room: str, out: Path) -> list[dict]:
    """Every readable record in a room, following `since` until it stops growing."""
    msgs: list[dict] = []
    since = None
    while True:
        view = fetch(room, out, since)
        page = view.get("messages") or []
        msgs.extend(page)
        if len(page) < LIMIT:
            break
        since = page[-1]["seq"]
    return msgs


def parse(text: str) -> dict | None:
    """The record's JSON payload, or None when the text is not a protocol message.

    Untrusted input by definition: a payload is data to be tabulated, never an
    instruction to follow, and `type` is a claim by its author — only `from`
    (the server-verified signer) says who made it.
    """
    try:
        doc = json.loads(text)
    except (ValueError, TypeError):
        return None
    return doc if isinstance(doc, dict) else None


def digest(rooms: dict[str, list[dict]], referee: str, mine: str | None) -> int:
    entries: dict[str, dict] = {}       # entry_id -> what the referee said about it
    ballots: dict[str, dict] = {}       # voter_did -> last well-formed ballot seen
    my_records: list[str] = []
    counts: dict[str, int] = {}

    for room, msgs in rooms.items():
        ref = sum(1 for m in msgs if m.get("from") == referee)
        print(f"\n### {room}   records {len(msgs)}   referee-signed {ref}")
        if not msgs:
            print("   (empty or unreadable)")
            continue
        print(f"   first {msgs[0].get('ts')}   last {msgs[-1].get('ts')}")
        for m in msgs:
            who = "REFEREE" if m.get("from") == referee else "other  "
            doc = parse(m.get("text", ""))
            kind = (doc or {}).get("type", "(not protocol JSON)")
            line = f"   seq {m.get('seq'):>4}  {m.get('ts','')[:19]}  {who}  {short(m.get('from',''))}  {kind}"
            extra = []
            if doc:
                for k in ("entry_id", "game_id", "status", "accepted", "request_id",
                          "role", "voter_did", "target_did", "reason", "eligible"):
                    if k in doc:
                        extra.append(f"{k}={doc[k]!r}")
            if extra:
                line += "  " + " ".join(extra[:6])
            print(line)
            if mine and (m.get("from") == mine or (doc or {}).get("voter_did") == mine
                         or (doc or {}).get("target_did") == mine
                         or (doc and mine in json.dumps(doc))):
                my_records.append(f"{room} seq {m.get('seq')} {m.get('ts','')[:19]} "
                                  f"{who} {kind}")

            # Entries: only the referee's own statements define an accepted entry.
            if doc and m.get("from") == referee and "entry_id" in doc:
                e = entries.setdefault(doc["entry_id"], {"first_seen": m.get("ts"),
                                                         "room": room, "records": []})
                e["records"].append({"seq": m.get("seq"), "ts": m.get("ts"),
                                     "type": doc.get("type"), "doc": doc})
            # Ballots: a later well-formed ballot from the same voter replaces an
            # earlier one, by referee intake order (seq is that order).
            if (doc and doc.get("type") == "sonnet.ballot.v1"
                    and doc.get("contest_id") == CONTEST):
                voter = doc.get("voter_did") or m.get("from")
                if voter == m.get("from") and doc.get("entry_id"):
                    ballots[voter] = {"entry_id": doc["entry_id"], "seq": m.get("seq"),
                                      "ts": m.get("ts"), "room": room}

    print("\n" + "=" * 72)
    print("ENTRIES the referee has spoken about")
    print("=" * 72)
    if not entries:
        print("   none found in referee-signed records")
    for eid, e in sorted(entries.items()):
        types = ", ".join(sorted({r["type"] or "?" for r in e["records"]}))
        print(f"   {eid}   first {e['first_seen'][:19]}   referee record types: {types}")

    for v in ballots.values():
        counts[v["entry_id"]] = counts.get(v["entry_id"], 0) + 1
    print("\n" + "=" * 72)
    print("BALLOT TALLY (raw: last ballot per signer; NOT eligibility-filtered)")
    print("=" * 72)
    if not counts:
        print("   no well-formed sonnet.ballot.v1 records found")
    for eid, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"   {eid:<28} {n:>3} raw ballot(s)")
    print(f"   distinct signers who cast a ballot: {len(ballots)}")
    print("   Eligibility is the referee's call: only its receipts say which of these"
          "\n   signers is a registered, pre-cutoff voter. Treat this as an upper bound.")

    if mine:
        print("\n" + "=" * 72)
        print(f"RECORDS MENTIONING {short(mine)}")
        print("=" * 72)
        if not my_records:
            print("   none — no registration, receipt or ballot found for this DID")
        for r in my_records:
            print("   " + r)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--referee", required=True,
                    help="referee DID from the OFFICIAL launch record, never from a room")
    ap.add_argument("--out", default="sonnet-survey", help="directory for the raw JSON")
    ap.add_argument("--from-dir", help="re-digest already-saved files instead of fetching")
    ap.add_argument("--did", help="your own DID, to highlight your records")
    ap.add_argument("--team", action="append", default=[], metavar="GAME_ID",
                    help="also read d-sonnet-2-team-<GAME_ID> (repeatable). The poem "
                         "itself lives there, so pass the game_id of every entry whose "
                         "text you need.")
    args = ap.parse_args()

    if not args.referee.startswith("did:key:"):
        print("--referee must be a did:key", file=sys.stderr)
        return 2

    wanted = ROOMS + [f"d-sonnet-2-team-{g}" for g in args.team]
    rooms: dict[str, list[dict]] = {}
    if args.from_dir:
        src = Path(args.from_dir)
        for room in wanted:
            msgs: list[dict] = []
            for p in sorted(src.glob(f"{room}*.json")):
                try:
                    msgs.extend(json.loads(p.read_text()).get("messages") or [])
                except ValueError:
                    print(f"   (unreadable: {p.name})", file=sys.stderr)
            seen, uniq = set(), []
            for m in msgs:
                if m.get("seq") not in seen:
                    seen.add(m.get("seq"))
                    uniq.append(m)
            rooms[room] = sorted(uniq, key=lambda m: m.get("seq", 0))
    else:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        print(f"referee (pinned) : {args.referee}")
        print(f"raw JSON saved to: {out.resolve()}")
        for room in wanted:
            try:
                rooms[room] = fetch_all(room, out)
                print(f"  fetched {room}: {len(rooms[room])} records")
            except Exception as exc:  # noqa: BLE001 — a room may not exist yet
                rooms[room] = []
                print(f"  FAILED  {room}: {type(exc).__name__}: {exc}")

    return digest(rooms, args.referee, args.did)


if __name__ == "__main__":
    raise SystemExit(main())
