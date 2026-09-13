#!/usr/bin/env python3
"""Check a room `/export` against this key, without printing any signature.

Why re-signing rather than verifying: the device that holds the seed is the one
that needs this answer, and that device (a-Shell) has no Ed25519 verifier — no
PyNaCl, no `cryptography`. Ed25519 signatures are deterministic, so re-signing
`<room>|<nonce>|<text>` with our own seed and comparing byte-for-byte proves the
stored record is exactly what this key signed. It answers the same question a
verifier would, using only the signing primitive the device actually has.

What it prints: one line per record with `seq`, whether it carries a signature,
and MATCH / MISMATCH. **Never a signature, never the seed.** A signature is
replay material while the record is inside the server's anti-replay window, so
the output of this script is safe to paste into a chat and the export is not.

Records from another DID are reported as `other-did` and not checked — this key
cannot re-sign someone else's record, and in an owned room there should be none.
Records with no `sig` are reported as `no-sig`: upstream stores one only when
the caller supplies it, so a missing signature means "not re-verifiable", never
"invalid" (`store.py append()`).

Usage:
    python3 verify_export.py <export.jsonl> [room]

`room` defaults to the name in the export's filename when it follows the
`export-<room>-<utc>-<nonce>.jsonl` convention, else it must be given.

Exit codes: 0 every signed record matched; 1 at least one MISMATCH; 2 the file
could not be read or the room could not be determined.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import flopdid  # noqa: E402  — the signer, and its seed loading


def room_from_name(path: Path) -> str | None:
    m = re.fullmatch(r"export-(.+)-\d{8}T\d{6}Z-\d+\.jsonl", path.name)
    return m.group(1) if m else None


def main() -> int:
    if not 2 <= len(sys.argv) <= 3:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("usage: python3 verify_export.py <export.jsonl> [room]", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    room = sys.argv[2] if len(sys.argv) == 3 else room_from_name(path)
    if not room:
        print(f"cannot tell the room from {path.name!r} — pass it as the second argument",
              file=sys.stderr)
        return 2

    seed = flopdid.load_seed()
    did = flopdid.did_from_pubkey(flopdid.PUBKEY(seed))
    print(f"export : {path.name}")
    print(f"room   : {room}")
    print(f"key    : {flopdid.short(did) if hasattr(flopdid, 'short') else did[:12] + '…'}")
    print()

    matched = mismatched = unsigned = other = malformed = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            malformed += 1
            print("  (a line that is not JSON)")
            continue
        seq = rec.get("seq")
        if rec.get("from") != did:
            other += 1
            print(f"  seq {seq}: other-did   (not this key's record; not checked)")
            continue
        if "sig" not in rec:
            unsigned += 1
            print(f"  seq {seq}: no-sig      not re-verifiable (stored before the signature "
                  "was retained)")
            continue
        # Deterministic: the same key over the same message yields the same signature.
        ours = flopdid.sig_b64(seed, f"{room}|{rec['nonce']}|{rec['text']}")
        if ours == rec["sig"]:
            matched += 1
            print(f"  seq {seq}: signed      MATCH")
        else:
            mismatched += 1
            print(f"  seq {seq}: signed      MISMATCH — the stored record is not what this "
                  "key signed over room|nonce|text")

    print()
    print(f"MATCH {matched}   MISMATCH {mismatched}   no-sig {unsigned}   "
          f"other-did {other}   malformed {malformed}")
    if mismatched:
        print("A MISMATCH is worth reporting verbatim: either the stored text/nonce differs "
              "from what was signed, or the room name passed here is wrong.")
    return 1 if mismatched else 0


if __name__ == "__main__":
    raise SystemExit(main())
