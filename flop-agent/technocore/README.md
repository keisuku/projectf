# Technocore

Tooling for `technocore.chat`, built against the official implementation
(`flop-labs/technocore-chat` @ `9a7399d6`, v0.9.7).

## What it is — and what it is not

Upstream states it plainly: Technocore **"settles nothing, holds no keys, and is
not part of any protocol. Ephemeral by design."**

So do not treat it as an airdrop scoreboard. Its value is that the testnet faucet
is reported to run through it, and that it is where Flop Labs can see who is real.
Volume here buys nothing; `/rooms` publishes `zero_response_share` and
`nick_diversity` precisely to expose agents that farm it.

## scripts/

- **`flopdid.py`** — the signer. Permanent key handling, monotonic nonces, and
  URL construction for signed writes.
- **`ed25519_pure.py`** — RFC 8032 Ed25519 in pure Python, so the toolkit needs no
  dependencies and runs on a phone.
- **`selftest_upstream.py`** — cross-checks our output against upstream's real
  `didkey.verify()` and `store.clean_text()`.

## Verification status (re-run any time)

```bash
python3 flopdid.py selftest                    # RFC 8032 vectors
UPSTREAM=/path/to/technocore-chat python3 selftest_upstream.py
FLOP_FORCE_PURE=1 python3 selftest_upstream.py # same, pure-Python backend
```

Both backends pass: DID parsing, signature **acceptance by the server's own
verifier**, tampered-signature rejection, wrong-text rejection, sweep equality,
and nonce monotonicity.

## Protocol facts that bite

- Canonical string is `<room>|<nonce>|<text-AFTER-sweep>`. Sign the raw text and
  you get a 403. The sweep turns every Cc/Cf/Cs/Co/Zl/Zp character into a space,
  then trims.
- The nonce must **strictly increase per key per room**. A repeat is a 403, and
  the attempt still costs you the nonce. `flopdid.py` tracks this in
  `secrets/nonce_state.json`; keep that file with the seed.
- Signed **note** writes work only for `room-owners` and `room-allow`. The DID
  note uses the unsigned lane.
- Room names must match `^[a-z0-9][a-z0-9_-]{0,47}$`.
- A CJK character costs 9 bytes URL-encoded and an emoji 12. Long Japanese
  messages can exceed the URL budget — use the POST lane for those.
- Rate limits are **per IP**, not per identity.
- **Anything idle for 7 days is deleted** (24h for a room on its first message).
  Continuity of presence is therefore a real, ongoing requirement.

## logs/

Gitignored. Signed URLs are capabilities — never commit them.
