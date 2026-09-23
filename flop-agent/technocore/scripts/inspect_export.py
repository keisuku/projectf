#!/usr/bin/env python3
"""Read a saved `/export` and print only what concerns one DID — never a signature.

Why this exists: the gate saves a byte-exact `/export` snapshot beside every
production write, so the device that made the write is already holding evidence
about what the room said at that moment. For a busy `mb-` room that snapshot is
thousands of other agents' records, and pasting it into a chat would be both
enormous and careless — a stored `sig` is replay material while the record is
inside the server's anti-replay window, and most of those signatures are not
ours to move around.

So this reads the file locally and prints two things: a shape summary of the
whole export (how many records, which sequences, which payload types), and the
full detail of **only** the records that mention the DID you name. `sig` is
never printed, for any record, ours or anyone's. The output is safe to paste;
the export is not.

Untrusted input by definition: a record's `text` is written by whoever signed
it. Fields are tabulated as data, never followed as instructions, and `type` is
a claim by its author — only `from` says who actually signed.

Needs no key, no network, and no packages. It only reads the file you name.

With no `--did`, it looks for `identity/public/did.txt` beside the export's own
directory — the layout the gate already writes, where exports land in
`<identity home>/logs/`. That keeps the command short enough to type on a phone,
which is the only device this ever runs on. `--summary` skips the lookup.

Usage:
    python3 inspect_export.py <export.jsonl>             # uses identity/public/did.txt
    python3 inspect_export.py <export.jsonl> --did did:key:z6Mk...
    python3 inspect_export.py <export.jsonl> --summary   # shape only

Exit codes: 0 the DID was found (or no `--did` was given and the file parsed),
1 the DID appears nowhere in the export, 2 the file could not be read.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

VALUE_CAP = 240  # one field of someone else's prose is context, not a payload dump


def short(did: object) -> str:
    if not isinstance(did, str) or not did.startswith("did:key:"):
        return str(did)
    body = did[len("did:key:"):]
    return f"{body[:8]}…{body[-4:]}"


def payload(text: object) -> dict | None:
    """The record's JSON object, or None when the text is not protocol JSON."""
    if not isinstance(text, str):
        return None
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def describe(rec: dict, doc: dict | None) -> str:
    """One record, with every field except the signature."""
    head = (f"  seq {rec.get('seq')}  {str(rec.get('ts', ''))[:19]}  "
            f"from {short(rec.get('from'))}")
    if doc is None:
        text = str(rec.get("text", ""))
        body = text if len(text) <= VALUE_CAP else text[:VALUE_CAP] + " …(truncated)"
        return f"{head}\n      (not protocol JSON) {body!r}"
    lines = [head]
    for key in sorted(doc):
        if key == "sig":  # never, from any record
            continue
        value = doc[key]
        rendered = value if isinstance(value, (int, float, bool, type(None))) else str(value)
        if isinstance(rendered, str) and len(rendered) > VALUE_CAP:
            rendered = rendered[:VALUE_CAP] + " …(truncated)"
        lines.append(f"      {key} = {rendered!r}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("export", help="a saved export-<room>-<utc>-<nonce>.jsonl")
    ap.add_argument("--did", help="print full detail for records mentioning this DID")
    ap.add_argument("--summary", action="store_true",
                    help="shape only; do not look up or use a DID")
    args = ap.parse_args()

    path = Path(args.export)
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2

    # The gate writes exports to <identity home>/logs/, and the DID is published
    # at <identity home>/identity/public/did.txt. Reading it is what lets the
    # command stay short; it is public material and never the seed.
    if not args.did and not args.summary:
        published = path.resolve().parent.parent / "identity" / "public" / "did.txt"
        if published.is_file():
            found = published.read_text(encoding="utf-8", errors="replace").strip()
            if found.startswith("did:key:"):
                args.did = found.split()[0]
                print(f"did (from {published.name}): {args.did}")
            else:
                print(f"{published} does not hold a did:key — pass --did", file=sys.stderr)

    records: list[dict] = []
    malformed = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if isinstance(rec, dict):
            records.append(rec)

    if not records:
        print(f"{path.name}: no records could be parsed ({malformed} malformed lines)",
              file=sys.stderr)
        return 2

    seqs = [r["seq"] for r in records if isinstance(r.get("seq"), int)]
    types = Counter()
    signed = 0
    for rec in records:
        doc = payload(rec.get("text"))
        types[(doc or {}).get("type", "(not protocol JSON)")] += 1
        if isinstance(rec.get("sig"), str) and rec["sig"]:
            signed += 1

    print(f"export     : {path.name}")
    print(f"records    : {len(records)}   malformed lines {malformed}")
    if seqs:
        print(f"seq range  : {min(seqs)} .. {max(seqs)}")
    print(f"first ts   : {str(records[0].get('ts',''))[:19]}")
    print(f"last ts    : {str(records[-1].get('ts',''))[:19]}")
    print(f"carry a sig: {signed} of {len(records)}  (signatures are never printed)")
    print("payload types:")
    for kind, n in types.most_common(12):
        print(f"   {n:>6}  {kind}")

    if not args.did:
        print("\nPass --did did:key:... to see the records that mention one identity.")
        return 0

    print("\n" + "=" * 68)
    print(f"RECORDS MENTIONING {short(args.did)}")
    print("=" * 68)
    hits = 0
    for rec in records:
        # Match anywhere: the signer, or a payload naming it (a receipt addressed
        # to this DID is the interesting case and does not come *from* it).
        blob = json.dumps({k: v for k, v in rec.items() if k != "sig"}, ensure_ascii=False)
        if args.did not in blob:
            continue
        hits += 1
        doc = payload(rec.get("text"))
        who = "SELF   " if rec.get("from") == args.did else "other  "
        print(f"[{who}]")
        print(describe(rec, doc))
        print()
    if not hits:
        print("   none — this DID appears nowhere in this export.")
        print("   That is a fact about this snapshot only: an export holds the room's")
        print("   RETAINED ring at the moment it was taken, so a record written after")
        print("   the snapshot, or already rotated out of the ring before it, is absent")
        print("   without being absent from history.")
        return 1
    print(f"   {hits} record(s) mention this DID.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
