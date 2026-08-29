# HANDOFF — read this first, then STATUS.md and STRATEGY.md

Written 2026-08-28 at the end of session 1. This is the briefing a fresh session
needs to continue without re-deriving anything.

---

## 1. The decision that reframes everything

**GitHub contribution is a side road. The DID is the main road.**

Session 1 spent most of its effort on a GitHub issue. It succeeded — see the
record below — but the evidence says that is not where the value is:

- The airdrop is reported to be decided by **testnet activity**, not by repo
  contributions and not by chat volume.
- **The faucet is DID-gated**: "only agents with decentralized identity (DID)
  keys will be able to access the faucet."
- The repo is crowded: 14 external contributors ever, ~313 PRs in two weeks, and
  every finding gets absorbed by a competing implementation within a day.

So from now on: **maximise what the key does, not what the GitHub account does.**
GitHub is opportunistic only — and when it is done, the issue and the PR ship
together (see §6).

---

## 2. State of play — what exists right now

| Asset | State |
|---|---|
| Permanent DID | `did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU` |
| Private seed | On the user's iPhone (a-Shell) **only**, backed up offline. Never in this repo, never in any transcript. |
| DID note | `/kv/did-64/776f70dbeec8e2` — published and verified |
| Signed writes | Working, verified against upstream `didkey.verify()` |
| Toolkit | `technocore/scripts/` — `flopdid.py`, `ed25519_pure.py`, `flopwatch.py` |
| Testnet | **Not started.** Watch is automated in `flopwatch.py` |
| GitHub | Issue #417 closed out, credited by name in PR #433. Nothing outstanding. |

**The one recurring obligation:** the DID note is deleted after **7 idle days**
(`store.py: IDLE_SECONDS = 7 * 86400 — untouched rooms/notes are reaped`). Run
`flopwatch.py watch --write-keepalive` weekly or the identity record vanishes.
It needs only the **public** DID (`$FLOP_DID`), so it can run anywhere.

---

## 3. The royal road: what the DID should actually be doing

Ranked by "cannot be bought later", which is the only edge that survives.

### 3.1 Claim an owned `d-` room — the single most scarce thing available

`src/patterns.md` §5: only `d-` rooms are ownable, the claim happens **at
creation, before anyone else**, and the claim itself must be **signed by the key
being stored** — so the claim is cryptographic proof of possession, recorded
durably.

    GET /kv/room-owners/d-<name>/set-signed/<did>/<sig>/<nonce>/<the same did:key>?if_absent=1
        signature covers:  room-owners|d-<name>|<nonce>|<the same did:key>

Once claimed, `/r/d-<name>` accepts signed writes **from the owner's key only**.
That yields the thing nothing else on this service gives:

- an **append-only, attributable, unforgeable record** owned by the DID,
- immune to the spam that makes `lobby` worthless,
- with an ownership note that survives the idle reaper as long as the room lives
  (`store.py: ROOM_GUARD_NS`, `_guards_a_live_room`).

**A good room name is first-come and can never be re-claimed.** This is the
clearest "get there early or never" asset found so far. It is also the natural
home for the agent's own verifiable activity log.

**Updated 2026-08-29.** Name decided: **`d-watchtower`**. Chosen over a generic
one-word name (`d-jobs`, `d-faucet`) deliberately: an owned room takes writes
from the owner's key only, so claiming a communal name does not acquire an asset,
it removes one from the commons and reads as squatting to the party publishing
`zero_response_share`. Chosen over `d-flopwatch` because a leading `flop` invites
exactly the confusion with official channels that `STRATEGY.md` flags as the top
risk (`flop-labs-dev`).

The claim is built and verified against upstream's own verifier
(`technocore/tests/test_claim_against_upstream.py`) but **cannot be sent from
here** — signing needs the seed, which is on the phone, and technocore.chat is
egress-blocked. The whole procedure is
**`technocore/RUNBOOK-d-room-claim.md`**. Read §0 and §1 of it before touching
anything: posting to the room *before* the claim lands destroys the name
permanently, for everyone, and a claimed room with fewer than two messages is
reaped within 24 hours.

**Own one room, not three.** Each owned room needs a *signed* write every 7 days
forever, and signed means the phone. The recurring cost is the reason to stop at
one.

### 3.2 A `mb-` mailbox so other agents can reach the DID attributably

`mb-` rooms refuse the unsigned lane, so every message in one is bound to a
`did:key`. `mb-p-<unguessable>` is attributable *and* unlisted. Advertise it in
the DID note (`flopdid.py didnote --mailbox mb-p-...`). Being reachable is a
precondition for any agent-to-agent workload later.

### 3.3 Day-1 faucet readiness

The faucet is DID-gated and reported to run through Technocore. The signer works,
the key exists, the watch is armed. What remains is to not miss the moment —
`flopwatch.py watch` covers `/r/events`, `/rooms`, `/config`,
`/.well-known/agent.json`, the repo docs and **the org's repo list** (a testnet
client most likely arrives as a *new repo*).

### 3.4 Real workload, when there is a network to do it on

The long-term goal from the user's brief: this becomes an agent that actually
uses the network — watching official sources, diffing, summarising in Japanese,
logging verifiable activity. Until the testnet exists there is nothing to spend
on, so this stays a design, not a build.

---

## 4. What is explicitly NOT the road

- **Volume in `lobby`.** Measured at ~35 msg/s: a message is gone in 15–30
  minutes (`research/official/2026-08-27-lobby-throughput.md`). `/rooms`
  publishes `zero_response_share` and `nick_diversity` to expose exactly the
  agents that farm it.
- **Posting the DID on X.** No official basis found. A signed write already
  proves key possession; a tweet proves nothing, and mass DID posting is the
  cleanest possible training set for a Sybil filter
  (`research/official/2026-08-28-x-posting-and-faucet-gate.md`).
- **A second DID, ever.**
- **GPU spend** before miner specs exist.
- **Chasing GitHub issues** now that the repo has shown how fast findings get
  absorbed.

---

## 5. Immediate next actions for the new session

1. **Confirm the keepalive is running.** `flopwatch.py status`. Due ~2026-09-03.
2. **Claim `d-watchtower`** — name decided, URL builder written and verified.
   Follow `technocore/RUNBOOK-d-room-claim.md` on the phone. Claim, confirm `ok`,
   then immediately post the two seeding messages. All three in one sitting.
2b. **Close the linkage gap in the same sitting** (RUNBOOK §4b, §4c). The GitHub
   contribution is permanently timestamped but is not reachable from the DID —
   nothing associates a `did:key` with anything until we sign a write saying so.
   Message 2 of the room seeding IS that record; the DID note then points at the
   room; lobby gets one announcement. Identity and activity stopped being two
   separate projects on 2026-08-29.

3. **Publish a mailbox** in the DID note (§3.2).
4. **Keep the watch running** and treat any signal word as a stop-everything event.
   `PLAYBOOK-testnet-day1.md` is the pre-thought version of what to do when one
   fires — including the two spending questions, both answered *no* for now
   (no Kimi/second-model subscription; a $5 VPS is optional and is the only spend
   with a real mechanism behind it).

Everything in 2–3 requires the human to fetch a URL: `technocore.chat` and
`flop.finance` are **blocked by this container's egress policy** (verified
`connect_rejected` at the proxy). That is a policy denial and must not be worked
around. Build the URL, hand it over.

---

## 6. Hard-won lessons — do not relearn these

1. **Ship the implementation with the issue.** #417 was filed without a PR to
   respect "discuss substantial changes first". Someone else implemented it in
   under a day. In a repo at this velocity, restraint costs the work.
2. **Run other people's code before commenting on it.** One claim about #433 was
   wrong; it was caught only because the "failing-first" test written to prove it
   **passed against the unmodified PR**. A test that passes without the fix is
   evidence there is no bug. Withdraw immediately when that happens.
3. **Search before filing.** The first idea was already issue #165 — with four
   PRs contending it. `good first issue` is the *worst*-odds label in the repo.
4. **Verify test data before accusing.** A "vector 4 failure" in #433's crypto
   was our own transcription error. Both implementations agreed with
   `cryptography`; the report was never made.
5. **The seed is never needed for public work.** Keepalive, watching and DID
   derivation all run from the public DID. Reach for the key only to sign.

---

## 6b. Added 2026-08-29 — the lesson from the X guide

**A confidently-relayed community guide is Tier 9, and helpfulness is the delivery
mechanism.** One circulating "onboarding checklist" was 80% harmless-and-roughly-right and
carried, in step 1, a link to `floppysol.xyz/onboard` offering to *generate your DID key*.
That domain is in no official source. A key generated in someone else's browser has no
revocation path — `did:key` has no registry — so it is lost at birth, silently.

Two habits follow. **Check the claim against the source tree before acting**, which took
one grep. And **separate the guide's tier from its usefulness**: the same document's
linkage step was architecturally sound and exposed a real gap in our plan. Dismissing the
whole thing for its worst item would have cost as much as swallowing it whole.

## 7. Non-negotiables

- The seed is never displayed, printed, committed, logged, or sent anywhere —
  including to the assistant. `secrets/` is 700, the seed file 600, gitignored.
- Approval required before: any SNS post, any public issue/PR, any payment, any
  wallet action, any GPU contract, any external form.
- No FLOP token exists. Every contract, presale, claim page and wallet-connect
  flow is fake until flop.finance and the official GitHub agree otherwise.
- Tag every claim with its source tier (`SOURCES.md`). Never present unreachable
  sources as current.
