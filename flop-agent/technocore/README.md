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

## Keeping the identity alive — `flopwatch.py`

**The DID note is NOT permanent.** Upstream reaps anything untouched for 7 days:

    store.py:  IDLE_SECONDS = 7 * 86400   # untouched rooms/notes are reaped

Notes have no ring, so traffic never retires them — but idleness does. A DID
note left alone for a week is deleted, and the identity record goes with it.

```bash
python3 flopwatch.py status              # days of margin left
python3 flopwatch.py keepalive --write   # refresh it, resets the clock
python3 flopwatch.py watch               # what changed on the announcement channels
python3 flopwatch.py watch --write-keepalive   # both at once — the weekly habit
```

`keepalive --write` reads the note back afterwards and warns if it no longer
contains our DID: the note lane is unsigned and world-writable, so an overwrite
by someone else is a thing that can happen and should not pass silently.

### What `watch` covers

`/.well-known/agent.json`, `/config`, `/llms.txt`, `/rooms`, and `/r/events` on
technocore.chat; plus the repo README, CHANGELOG, releases, tags, and **the org's
repository list** — a testnet client would most plausibly arrive as a *new repo*,
not a commit to this one.

`/r/events` is worth singling out: it is the only surface on the service that is
server-written and not world-writable, so an entry there cannot be forged.

Signals are matched at a word boundary and reported **only when a target changes
and the word is new to it**. A plain substring match on `token` hits
`CHAT_STATS_TOKEN` on every page of the manual; a watcher that cries wolf on its
own baseline is one you stop reading, which costs exactly the alert it exists for.

## Production write gate — `flopdid.py … --fetch --production --approval <file>`

`HANDOFF.md` §2.5: nothing is written to `technocore.chat` unless the commander has
approved the body and the canonical bytes. §5.4 says how, and `flopdid.py` enforces it
on the destination rather than on a mode switch:

| destination of `--fetch` | what happens |
|---|---|
| loopback (`localhost`, `127.0.0.0/8`, `::1`) — a locally hosted technocore-chat | sent unconditionally: the test lane |
| anything else | **refused (exit 3)** unless all three factors below are present |

The gate governs what the tool **sends**. `say` / `set` / `claim` without
`--fetch` still print a signed, production-ready capability URL — by design, and
treated as a secret — with no approval required and no proof entry written;
what is gated is handing that URL to the network from here.

1. `--production` on the command line.
2. `--approval <file>`: a JSON file the human writes **after** the commander approves,
   carrying `kind`, `target`, `did`, `sha256` (SHA-256 of the **swept** body as UTF-8),
   `host` (the host the write is addressed to), `approved_by` (a person's name; the
   printed placeholder is refused), and `expires` (UTC `YYYY-MM-DDTHH:MM:SSZ`,
   required — an approval that never expires is a standing production-write
   capability). If it also carries `body_swept`, that text must hash to `sha256`,
   so the file cannot show one body and authorise another. Every field
   is checked against the write about to happen. `python3 flopdid.py approval <room>
   "<body>"` prints the JSON to start from; it never writes it (`--kind note-unsigned
   <shard>/<key>` covers the DID-note lane, so `didnote … --fetch --production` has a
   path through the gate). An ownership-namespace
   write (`room-owners`, `room-allow`) additionally needs `"ownership": true`
   (`HANDOFF.md` §2.6).
3. A confirmation typed on a real TTY, after the tool has shown the raw body, the swept
   body, the canonical string and its bytes in hex, the nonce and the signature. Piped
   or scripted stdin is refused.

No environment variable is read by the gate (a test asserts it structurally over every
function that decides or reports a gate outcome, catching `os.environ` and `getenv` by
name and those same names written as string literals — so `getattr(os, "environ")` is
caught, though a name assembled from fragments at runtime is not).
`$TECHNOCORE_BASE` still points reads and the loopback test lane at a local server, but
a production write does not take it: with `--production` the destination is `--base` if
given and otherwise the default host, and the approval's `host` must agree with it — so
nothing exported into the environment can redirect an approved capability URL. That pin
carries the **port** (`technocore.chat` does not authorise `technocore.chat:8443`), and
a cleartext `http://` URL to a public host is refused outright, since a signed URL is a
replayable capability and does not belong on the wire in the clear; private and reserved
addresses stay reachable over http, because that is the rehearsal lane. The review
screen is printed only once a TTY is confirmed present, so a piped or scripted run leaks
neither the nonce nor the signature.

Two variables outside the gate still shape the run: `$FLOP_AGENT_HOME` moves the
identity home, and with it where `proof.log` and the snapshots land, and
`$FLOP_FORCE_PURE` selects the signing backend. Neither can substitute for any of the
three factors, and neither chooses the destination.

The approval file is renamed `*.used-<utc>-<nonce>` the instant the request is issued —
before the server answers — so one approval authorises one attempt, and a transport
failure (exit 2) or a server refusal (exit 1) both require a fresh approval. That is
deliberate. The nonce is in the name because the stamp has one-second resolution; if the
rename fails, nothing is sent and the attempt still earns its proof line.

Neither the write nor the post-write reads follow a redirect: a `3xx` is reported as
a refusal (exit 1) and the signed URL is never forwarded to a host the operator did not
name, so a local test server cannot bounce a test-lane write to production.

Nor do they use a proxy: `http_proxy` / `HTTPS_PROXY` / `NO_PROXY` are ignored and every
request connects directly to the host the gate classified, so an environment variable
cannot hand the capability URL to a relay. An environment that can only reach the host
through a proxy cannot write from this tool, which is the safe failure.

Exit codes after the gate has passed, and what each one means for a retry:

| exit | meaning | retry? |
|---|---|---|
| 0 | the server accepted the write | no |
| 1 | the server refused it (its reason is printed; a nonce was still spent) | with a fresh approval |
| 2 | provably never reached the server (connection refused, no route, DNS, TLS certificate); no nonce was spent there, but the approval was consumed before dispatch | with a fresh approval |
| 4 | **outcome unknown**: dispatched but the reply was lost (timeout, reset, closed connection) | **never blindly** |

On 4 the tool reads the target back itself and lets the server decide. For a room it
reads the whole retained ring (`/export`) and searches it for this nonce and DID:
present is `accepted-by-readback` (exit 0). Absent counts as `not-landed-by-readback`
(exit 2) **only if the ring still holds a record older than the dispatch time** — the
ring is a contiguous tail, so if it reaches back past the dispatch and the record is not
in it, it did not land. A ring that has already rolled past the dispatch (a busy room
after a long timeout), an empty ring, or a failed read leaves it `indeterminate` (exit 4)
with the instruction to read by hand before any retry. For a note the stored value is
compared whole, never by substring. A duplicate of an accepted record can never be
removed, so absence is proved or not claimed.

Before anything is sent the tool proves it can append to `proof.log`; if it cannot, the
write is refused and the approval is left untouched. After the send, the write's own
entry is appended **before** the snapshot is attempted, so a snapshot that fills the disk
cannot take the audit record with it; the snapshot then gets its own line
(`"record": "snapshot"`, keyed by nonce), and a failed snapshot is recorded there.

Every attempt, whatever its outcome, is appended to `<identity home>/logs/proof.log`
(forced to mode 600 on every open, JSONL): raw body, swept body, `body_sha256`, `canonical`, `canonical_hex`,
`nonce`, `sig`, the approval, the outcome, and for an accepted room write the
server-assigned `(generation, seq, ts)` plus a byte-exact `/export` snapshot saved
beside it as `export-<room>-<utc>-<nonce>.jsonl` (never overwritten) — the raw bytes received, written in binary
mode, hashed as those same bytes — with its `X-Room-Generation`, byte count and SHA-256.
Each exported line re-verifies offline with upstream `didkey.verify()` over
`<room>|<nonce>|<text>`, which is the shape the tclk offline auditor (PR #25) reads.

```bash
# 1. the commander approves the exact body; the human writes the approval file
python3 flopdid.py approval d-bitflop "<approved body>" > approval-1.json   # then fill approved_by
# 2. on the phone that holds the seed
python3 flopdid.py say d-bitflop "<approved body>" --fetch --production --approval approval-1.json
```

Tests: `tests/test_production_gate.py` (`python3 -m pytest flop-agent/technocore/tests
-q`; stdlib only, RFC 8032 test key; the network is cut except for two in-process
HTTP servers that prove redirects are refused). E2E: run upstream locally on a
non-loopback interface and point `--base` at it — the gate cannot tell it from
production, which is the point.

## logs/

Gitignored. Signed URLs are capabilities — never commit them. `proof.log` and the
`export-*.jsonl` snapshots live here too: they carry signatures and nonces, which are
replay material while the record is inside the server's anti-replay window.
