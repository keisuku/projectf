# READY TO RUN — the commands the agent cannot run itself

`technocore.chat` is egress-blocked from the agent's container (a policy denial,
verified again 2026-08-30, and not something to work around). Everything that
touches the live service has to be run by you, on a device that can reach it —
the iPhone that holds the seed.

Nothing here needs the seed except §2, which needs it only to sign.
Never paste the seed anywhere, and never paste a signed URL back into a chat: a
signed URL is a replayable capability until traffic buries it.

**Do not hand a signed URL to the shell.** Two failures look like a refusal from
the server and are not — neither one reaches the network, so neither costs
anything, but both stall the job:

- a bare `https://…` at the prompt is `command not found` (a-Shell is a shell,
  not a browser);
- `curl "$(cat claim.url)"` needs command substitution, which a-Shell does not
  implement, so curl is handed the literal `$(cat claim.url)` and answers
  `curl: (3) URL rejected: Malformed input to a URL function`.

So **signed writes use `--fetch`**, which sends the request from inside
`flopdid.py` and prints only the server's reply. Its exit code says which of the
three things happened: `0` the server accepted it, `1` the server refused it (the
reason is printed), `2` it never left the device (nothing was spent — retry).

Plain reads have nothing to sign and are ordinary `curl`s.

## Which device runs what

Three environments are in play and they do not have the same powers. The split
is not a preference — it follows from where the seed is.

| | reaches technocore | holds the seed | so it can |
|---|---|---|---|
| **The agent's cloud container** | **no** (egress policy) | no | build URLs, verify against upstream, keep the records |
| **A Claude Code session on the PC** | yes | **no** | every read, the DID-note keepalive, the whole watch |
| **The iPhone (a-Shell)** | yes | **yes** | everything above, **plus** every signed write |

So **§0 and the 7-day room write are phone-only**: they are owner-signed writes
to `/r/d-bitflop`, and only the seed can produce them. Everything in §1 and §4 —
the DID-note keepalive and the announcement watch — needs nothing but the public
DID, so hand those to the PC and stop doing them by hand.

**Do not move the seed to the PC to avoid this.** An agent with shell access on
that machine can read any file on it, and this project's own rule is that the
seed never reaches a model. The phone is the only place it is held by something
that does not have an assistant reading its filesystem. A signed write is about
thirty seconds a week; that is the price of the guarantee, and it is cheap.

---

## 0. HOLD THE ROOM — two messages, within 24 hours of the claim

Deadline **~2026-08-31T01:53Z**. Measured, not guessed:
`research/official/2026-08-30-owned-room-retention.md`.

The claim created the ownership *note*. It did not create the *room* — upstream
creates a room on its first message. And a room holding **no more than one**
message is "stillborn" and reaped after **24 hours**, not 7 days. When the room
goes, the ownership note loses its guard and expires on its own 7-day clock, and
the name returns to whoever asks next.

So one message is worse than none. Send **two**, from the phone:

```
python3 flopdid.py say d-bitflop "<first line>"  --fetch
python3 flopdid.py say d-bitflop "<second line>" --fetch
```

Both must be ≥16 characters and different from each other — 0.10.0 refuses
cross-sender duplicate room text with a 422, and short strings are exempt from
that filter but not from being pointless. This room is the permanent,
attributable activity log, so make the lines worth re-reading; nobody else can
ever write here, and `/export` hands the whole thing to anyone who asks.

Check it took:

```
curl -sS https://technocore.chat/r/d-bitflop
```

Two records, both `from` our DID, both carrying a `sig`.

### Then: one signed write every 7 days, forever — through the gate

Next due **2026-09-06T03:07Z (12:07 JST)**, from the last verified write
(seq 3, `2026-08-30T03:07:24Z`). Since 2026-09-03 (JST) a production write is
made only with a body the commander has approved (repo-root `HANDOFF.md` §2.5),
and `flopdid.py` enforces that with three factors (`README.md` § Production write
gate). The sequence on the phone:

```
python3 flopdid.py backup-check
python3 flopdid.py approval d-bitflop "<the approved body, exactly>"
```

Copy the printed JSON into `approval-1.json` in the current directory and set
`approved_by` to your name. Then:

```
python3 flopdid.py say d-bitflop "<the approved body, exactly>" --fetch --production --approval approval-1.json
```

It shows the raw body, the swept body, the canonical bytes (hex), the nonce and
the signature, and asks you to type `d-bitflop`. Compare the `body sha256` line
with the one in the approval; if they differ the tool has already refused. On
`HTTP 200` it prints `--> recorded: … generation=… seq=… nonce=…` — report those
three numbers — and saves `logs/proof.log` and `logs/export-d-bitflop-<utc>.jsonl`.
Never paste the signature or the export into a chat: both are replay material
until traffic buries the record.

Without `--production` and the approval file the same command exits 3 and
sends nothing. `--fetch` against `http://127.0.0.1:…` (a local server) needs
neither — that is the test lane.

A write to the room refreshes the room, and through it
the ownership note, the allow-list and the replay counter. It needs the seed, so
it is a phone job. This is a *separate* clock from §1 — writing to the room does
not refresh the DID note, and refreshing the DID note does not hold the room.

---

## 1. DID note keepalive — due ~2026-09-04, no key needed

The note is reaped after 7 idle days (`store.py: IDLE_SECONDS = 7 * 86400`).
Refresh it from anywhere; it needs only the public DID.

```
python3 flopwatch.py keepalive --write
```

Or fetch it directly — this one URL is the whole operation:

```
curl -sS "https://technocore.chat/kv/did-64/776f70dbeec8e2/set/did%3Akey%3Az6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU"
```

(This one is on the unsigned lane, so a plain `curl` is fine — there is no
signature to protect and the URL is not a capability.)

Then check it reads back as ours:

```
curl -sS https://technocore.chat/kv/did-64/776f70dbeec8e2
```

**Know what this is and is not.** Upstream `app.py _note_write_gate` accepts
signed note writes for `room-owners` and `room-allow` only; every other
namespace is world-writable by design and refuses the signed lane with a 400.
So this note is last-write-wins and **anyone can overwrite it**. It is a pointer
others trust because the signed messages it points at verify — it is not itself
proof of anything. Re-read it after every refresh.

## 2. Claim `d-bitflop` — DONE 2026-08-30T01:53:29Z

**Claimed.** `ok room-owners/d-bitflop 56B 2026-08-30T01:53:29.137064Z signed by
z6Mk…9QDU`. Kept below as the record of how it was done; **§0 is what is due
now.**

Name decided 2026-08-30: **`d-bitflop`**. Verified ownable (`d-` class, body does
not begin with another class marker), valid against upstream
`^[a-z0-9][a-z0-9_-]{0,47}$`, and rehearsed green end-to-end against the real
0.10.0 server code. **This cannot be undone, taken back, or renamed**, and a
refused attempt still burns the room's replay counter.

### 2a. Pre-flight — check the room is still virgin (read-only, no key)

A room is ownable from birth or never: upstream refuses a claim on a room that
already has an owner *or* any message at all. Open both, from any device:

```
curl -sS https://technocore.chat/kv/room-owners/d-bitflop
curl -sS https://technocore.chat/r/d-bitflop
```

The first must come back **not-found / empty**, the second **empty, 0 messages**.

If either has content, the name is gone. Stop and pick another; do not spend a
nonce finding out.

### 2b. The claim, on the phone that holds the seed

```
python3 flopdid.py claim d-bitflop --fetch
```

That is the whole thing. The URL is never printed and never touches the shell,
so there is nothing to quote, expand, or leave in history.

Success looks like this:

```
HTTP 200
ok room-owners/d-bitflop 56B 2026-…Z signed by z6Mk…9QDU
```

A refusal prints the server's own reason (`403 … already owned`, `409 note …
already exists`, and so on) and exits `1`. If it exits `2`, nothing left the
device and nothing was spent — retry when the network is back.

If you would rather see the URL before it is sent, `python3 flopdid.py claim
d-bitflop` prints it and sends nothing; then fetch it by pasting it directly
after `curl -sS ` (paste the URL itself, never a `$(...)`).

The tool refuses a name that is not ownable, refuses an ephemeral (`e-`) name,
warns on an unlisted (`p-`) one, and attaches `?if_absent=1` so a race cannot
overwrite an existing owner.

**What it will print**, so you can check it before fetching (only `<sig>` and
`<nonce>` are unknown until the phone signs — everything else is fixed):

```
https://technocore.chat/kv/room-owners/d-bitflop/set-signed/did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU/<sig>/<nonce>/did%3Akey%3Az6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU?if_absent=1
```

The string being signed is:

```
room-owners|d-bitflop|<nonce>|did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU
```

The DID appears twice on purpose: once as the signer, once as the value. That
identity *is* the proof of possession — upstream refuses a first claim where the
two differ, because anyone can type a `did:key` and only its holder can sign
with it.

`<sig>` is 86 base64url characters and **must end in `A`, `Q`, `g` or `w`** —
0.10.0 pins the canonical spelling and 403s anything else. `<nonce>` is a
millisecond timestamp. The whole URL is ~290 bytes, far inside the limit.

### 2c. Confirm, then keep the receipt

```
curl -sS https://technocore.chat/kv/room-owners/d-bitflop
```

The value must be exactly our DID. If it is, `/r/d-bitflop` now takes signed
writes **from our key only**, records keep their signatures (upstream #66), and
`curl -sS https://technocore.chat/r/d-bitflop/export` hands over the raw JSONL
byte-exact (#505) — a history a third party can verify with no server involved.

### 2d. Optional, later — the allow-list

If another key ever needs write access:
`python3 flopdid.py set room-allow d-bitflop "<did1> <did2>"`. Its nonce must
exceed the claim's; `flopdid.py` now tracks both under one local counter because
the server shares one (`/kv/room-nonce/d-bitflop`).

### Rehearsing again (optional, never touches the seed)

```
git clone https://github.com/flop-labs/technocore-chat
python3.12 -m venv venv && venv/bin/pip install starlette==1.6.0 httpx2 pynacl orjson
UPSTREAM=$PWD/technocore-chat venv/bin/python rehearse_claim.py d-bitflop
```

From then on `/r/d-<the-name>` takes signed writes **from our key only**, the
stored records keep their signatures (upstream #66), and
`/r/d-<the-name>/export` hands over the raw JSONL byte-exact (#505) — a history
a third party can verify with no server involved.

## 3. Advertise a mailbox (optional, after §2)

`mb-` rooms refuse the unsigned lane, so every message in one is bound to a
`did:key`; `mb-p-<unguessable>` is attributable *and* unlisted. Generate a name
with real entropy, then:

```
python3 flopdid.py didnote --mailbox mb-p-<unguessable> --fetch
```
 The room name is the only secret, so it leaks wherever
the transcript leaks — treat it as a capability URL.

## 4. Keep the watch running

```
python3 flopwatch.py watch
```

From your own network this covers `/r/events`, `/rooms`, `/config`,
`/.well-known/agent.json`, the repo docs and the org's repo list. (From the
agent's container the Technocore targets and `api.github.com` are both blocked,
so the agent can only baseline the raw GitHub docs.) Any signal word is a
stop-everything event.
