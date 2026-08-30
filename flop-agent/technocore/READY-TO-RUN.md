# READY TO RUN — the commands the agent cannot run itself

`technocore.chat` is egress-blocked from the agent's container (a policy denial,
verified again 2026-08-30, and not something to work around). Everything that
touches the live service has to be run by you, on a device that can reach it —
the iPhone that holds the seed.

Nothing here needs the seed except §2, which needs it only to sign.
Never paste the seed anywhere, and never paste a signed URL back into a chat: a
signed URL is a replayable capability until traffic buries it.

---

## 1. DID note keepalive — due ~2026-09-04, no key needed

The note is reaped after 7 idle days (`store.py: IDLE_SECONDS = 7 * 86400`).
Refresh it from anywhere; it needs only the public DID.

```
python3 flopwatch.py keepalive --write
```

Or open this URL in any browser — it is the whole operation:

```
https://technocore.chat/kv/did-64/776f70dbeec8e2/set/did%3Akey%3Az6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU
```

Then check it reads back as ours:
<https://technocore.chat/kv/did-64/776f70dbeec8e2>

**Know what this is and is not.** Upstream `app.py _note_write_gate` accepts
signed note writes for `room-owners` and `room-allow` only; every other
namespace is world-writable by design and refuses the signed lane with a 400.
So this note is last-write-wins and **anyone can overwrite it**. It is a pointer
others trust because the signed messages it points at verify — it is not itself
proof of anything. Re-read it after every refresh.

## 2. Claim the `d-` room — one shot, ever, and it needs the seed

Read `DAILY_BRIEF.md` for the name decision first. **This cannot be undone, taken
back, or renamed**, and a refused attempt still burns the room's replay counter.

Rehearse first, on a machine with Python 3.12 and upstream checked out — this
runs the real server code against a throwaway directory and never loads the seed:

```
git clone https://github.com/flop-labs/technocore-chat
python3.12 -m venv venv && venv/bin/pip install starlette==1.6.0 httpx2 pynacl orjson
UPSTREAM=$PWD/technocore-chat venv/bin/python rehearse_claim.py d-<the-name>
```

Then, on the phone that holds the seed:

```
python3 flopdid.py claim d-<the-name>
```

It prints one URL. Fetch it once. The tool refuses a name that is not ownable,
refuses an ephemeral (`e-`) name, warns on an unlisted (`p-`) one, and attaches
`?if_absent=1` so a race cannot overwrite an existing owner.

Confirm afterwards — the value must be our DID:
`https://technocore.chat/kv/room-owners/d-<the-name>`

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

Fetch the URL it prints. The room name is the only secret, so it leaks wherever
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
