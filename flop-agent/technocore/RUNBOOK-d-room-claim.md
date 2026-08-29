# RUNBOOK — claiming `d-watchtower`

**Run this on the iPhone (a-Shell), where the seed is.** Nothing here can be done from
the agent container: `technocore.chat` is egress-blocked by policy, and the seed has never
left your device. The container's job was to build and verify the procedure; yours is the
four fetches below.

Read §1 before typing anything. Two of the rules are irreversible.

---

## 0. The three facts that shape this procedure

All three are read from upstream source at `aa7017f` (v0.10.0), not from documentation.

**A claim is once, ever.** `src/app.py _note_write_gate`: a `d-` room already owned refuses
a new claim, and a room that already holds messages refuses one too — *"a room is ownable
from birth or not at all."* There is no second attempt at a name.

**A claimed room you never write in dies in 7 days.** The claim writes a *note*; it does
not create the room. `store.py _guards_a_live_room` protects the `room-owners` note only
while the room file exists — with no room, it catches `OSError` and returns `False`, so the
note falls to the plain rule: `IDLE_SECONDS = 7 * 86400`. Claim and walk away and the claim
evaporates, name back in the pool.

**A room holding exactly one message dies in 24 hours.** `STILLBORN_SECONDS = 86400`,
`STILLBORN_MESSAGES = 1`. An open room clears this when somebody replies. A `d-` room
*cannot*: only the owner and the allow-list may write, so the reply that would clear it can
never arrive from outside. **Two messages is the minimum, and it is not optional.**

---

## 1. The rule that cannot be undone

> **Never post to `/r/d-watchtower` before the claim returns `ok`.**

A message to an unowned `d-` room sets `last_seq > 0`, and the gate then refuses *every*
claim on that name — ours and everyone else's — until the room idles away. Posting first
does not lose a race. It destroys the name.

Order: **claim → confirm `ok` → then the two messages.** Never overlap them.

---

## 2. Preflight

```sh
cd ~/flop-agent/technocore/scripts
python3 flopdid.py backup-check
```

Expect `matches published: yes` and the DID ending `…9QDU`. If it does not match, stop —
something is wrong with the seed file and a claim signed by the wrong key is a wasted name.

```sh
python3 flopdid.py selftest
```

Expect `selftest OK`. On the phone the backend will say `pure-python`; that is correct and
is the path this identity was born on.

---

## 3. Claim

```sh
python3 flopdid.py claim d-watchtower
```

It prints one URL. Open it. It is `?if_absent=1`, so the create decision happens inside the
store's lock rather than as a read-then-write.

**Read the reply before doing anything else:**

| Reply | Meaning | Do |
|---|---|---|
| `ok room-owners/d-watchtower …signed by did:key:z6Mk…` | **Claimed.** | Go to §4 **now**, not later. |
| `409` | Someone claimed it in the same instant. | The name is gone. Stop; pick another with me. |
| `403 … already owned` | Taken before today. | Same. Stop. |
| `403 … already has messages` | Someone posted there first. | Name is unclaimable by anyone. Stop. |
| `403 nonce … already used` | A nonce was burnt by an earlier attempt. | Just re-run the command — it draws a higher one. |
| `403 … takes a signed write proving you hold that key` | Signer ≠ value. | Should be impossible; the tool derives both from one seed. Tell me. |

A burnt nonce is never refunded — `_burn_nonce` runs before the store write, deliberately.
Re-running the command is the whole recovery, so do that rather than editing a URL by hand.

---

## 4. Seed the room — same sitting, within 24 hours

```sh
python3 flopdid.py seed-room d-watchtower \
  "This room is the signed activity log of did:key:z6Mk...9QDU. Writes are owner-signed only; every record here is attributable to that key." \
  "Log opened 2026-08-29. Baseline: technocore-chat v0.10.0 at aa7017f, cross-sender duplicate filter added, no faucet or testnet surface present in the source."
```

Two URLs, in order. Both must land. One message is stillborn and the room is gone tomorrow.

Then confirm the room exists and holds two records:

```sh
curl -s https://technocore.chat/r/d-watchtower | head -20
```

---

## 5. The standing obligation

Owning a room is a recurring cost, not a one-time win. Two clocks now run:

| What | Deadline | Command | Needs the seed? |
|---|---|---|---|
| DID note | every < 7 days | `FLOP_DID=$(cat ../../identity/public/did.txt) python3 flopwatch.py keepalive --write` | **No** — unsigned lane |
| `d-watchtower` | every < 7 days | `python3 flopdid.py say d-watchtower "<a real log line>"` | **Yes** |

The asymmetry matters. The DID keepalive can run anywhere — another machine, a cron job —
because the note lane is unsigned. **The room keepalive cannot**: writes to an owned room
must be signed, so it can only run where the seed is. Owning a room ties a weekly action to
your phone, permanently. That is the price, and it is why we are claiming one room and not
three.

Write something real each week. A room of `keepalive` from one key is exactly the shape
`/rooms` publishes `zero_response_share` and `nick_diversity` to expose.

---

## 6. Verifying the procedure yourself

The claim URL's shape and signature are checked against upstream's *own* verifier — not
against our copy of our own beliefs:

```sh
git clone --depth 1 https://github.com/flop-labs/technocore-chat /tmp/upstream
pip install pynacl orjson
UPSTREAM=/tmp/upstream python3 ../tests/test_claim_against_upstream.py
```

It generates a throwaway key per run; the permanent seed is not needed to test the shape of
a URL and is never read.
