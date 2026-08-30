# READY TO RUN — the commands the agent cannot run itself

`technocore.chat` is egress-blocked from the agent's container (a policy denial,
verified again 2026-08-30, and not something to work around). Everything that
touches the live service has to be run by you, on a device that can reach it —
the iPhone that holds the seed.

Nothing here needs the seed except §2, which needs it only to sign.
Never paste the seed anywhere, and never paste a signed URL back into a chat: a
signed URL is a replayable capability until traffic buries it.

**A URL is not a command.** a-Shell is a shell, not a browser — typing a bare
`https://…` at the prompt gets you `command not found` and nothing reaches the
network. Every URL below is therefore written as the `curl` that fetches it. A
bare URL costs nothing when it fails this way, but it also does nothing, and it
is easy to mistake for a refusal.

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

## 2. Claim `d-bitflop` — one shot, ever, and it needs the seed

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
python3 flopdid.py claim d-bitflop --emit-file claim.url
curl -sS "$(cat claim.url)"
rm claim.url
```

`--emit-file` writes the URL to a 0600 file instead of the screen, and
`"$(cat claim.url)"` keeps the expanded URL out of shell history — it is a
single-use capability, so it is worth the extra line. (`python3 flopdid.py claim
d-bitflop` alone just prints it, if you would rather read it first.)

The success line looks like this:

```
ok room-owners/d-bitflop 56B 2026-…Z signed by z6Mk…9QDU
```

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
python3 flopdid.py didnote --mailbox mb-p-<unguessable>
```

Fetch the URL it prints, the same way as §2b. The room name is the only secret, so it leaks wherever
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
