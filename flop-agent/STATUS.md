# STATUS — 2026-08-29 (updated: d- room claim prepared, awaiting the device)

## Participation state

| Item | State | Note |
|---|---|---|
| Permanent DID | **CREATED** `did:key:z6Mk…9QDU` | Generated on the user's iPhone. Validated by upstream `didkey.public_key()`. |
| Seed backup | **DONE** (user-confirmed) | The one irreversible step, closed. |
| DID note published | **YES** `/kv/did-64/776f70dbeec8e2` | Durable (notes have no ring). Verified by fetch. |
| Signed check-in | NO | Blocked: same. URLs can be pre-built here. |
| Signing toolkit | **DONE, and proven on-device** | The phone has no `cryptography`; the pure-Python fallback is what actually runs there. |
| Testnet | **NOT STARTED** | No official start date. |
| Miner / validator | Deferred | No specs published. |
| GitHub contribution | **#417 landed in #433, credited by name** | Finding, verification and test design all shipped. Nothing outstanding. |
| DID note keepalive | **DUE ~2026-09-03** | Reaped after 7 idle days. `flopwatch.py watch --write-keepalive`. |
| `d-watchtower` claim | **BUILT, NOT SENT** | Name decided 2026-08-29. `flopdid.py claim d-watchtower` on the phone. Blocked only by egress. |
| Claim verification | **DONE** | `technocore/tests/test_claim_against_upstream.py` checks the URL against upstream's own `didkey.verify()` and `store.ownable()`. |
| `mb-` mailbox | Deferred | Name is unguessable, so nobody can take it first. No urgency. |
| **DID ↔ contribution linkage** | **NOT DONE — closes today** | Nothing associates the DID with upstream #417/#433. A `did:key` has no registry; the link has to be a signed write we make. RUNBOOK §4/§4b. |
| Lobby announcement | **NOT DONE — closes today** | `SKILL.md`'s stated first action. Never made. One post, original wording. |
| `floppysol.xyz` | **HOSTILE — do not visit** | Circulating in an X onboarding guide as a place to "generate your DID key". Absent from the entire official source tree. See `research/official/2026-08-29-…`. |

## Why the DID was not generated in this container

Three facts together make generating it here strictly worse than generating it
on your own device:

1. **This agent runs in an ephemeral cloud container**, not on your phone. It is
   reclaimed after a period of inactivity. A seed written here dies with it
   unless exported — and exporting a permanent private key through a chat
   transcript is exactly what your own rules forbid.
2. **technocore.chat is egress-blocked from here.** The DID cannot be published
   and the check-in cannot be sent from this container. So a DID generated here
   would gain **zero** history today — there is no early-age advantage to lose.
3. Therefore deferring costs nothing and avoids your permanent identity ever
   existing on hardware you do not control.

The toolkit is committed to git, so it survives this container. You run one
command locally and the identity is yours from birth.

## Blocked on the human

1. Generate the permanent key locally (one command — see `identity/README.md`).
2. Back the seed up.
3. Fetch the two onboarding URLs the tool prints.

## Verified 2026-08-29, second pass (X intel check)

- **The `flop-labs` org still contains exactly one repository** (`technocore-chat`, pushed
  2026-08-29T17:06Z). No testnet client, no faucet, no onboarding site, no registration.
  The route reported to decide allocation has not started; there is no scoreboard to be
  behind on.
- **`floppysol.xyz` appears nowhere in the official source.** The only domains the code
  names are `technocore.chat` and `flop.finance`. A page offering to generate a DID key is
  the highest-value phishing target here: a `did:key` **is** its keypair, with no registry
  and no revocation, so a key made in someone else's browser is lost at the moment of
  creation.
- **The real official onboarding is `SKILL.md`** (served at `/skill.md`): post a short,
  original greeting in `/r/lobby`, read the manual, use the signed lane if you can run
  code. That is all of it. No KOL programme, no application form, no reward for spreading
  the word appears anywhere in the source.
- The community "5-step checklist" is Tier 9–10, not an official gate — but its linkage
  step is architecturally correct and exposed a real gap in our own plan. Closing today.

## Verified 2026-08-29 (session 2)

Read from upstream source at `aa7017f` (v0.10.0), not from documentation:

- **The claim protocol**, confirmed against `src/patterns.md` §5 and `src/app.py
  _note_write_gate`. Canonical string `room-owners|d-<name>|<nonce>|<the same did:key>`;
  our builder's output is accepted by upstream's own verifier and rejects all four
  single-field tampers.
- **Two reaper rules bite a fresh claim, and neither was in our notes.** A claim writes a
  note, not a room; with no room file `_guards_a_live_room` returns `False`, so the
  `room-owners` note falls to the plain 7-day idle rule and the claim evaporates. And a room
  holding one message is *stillborn* — reaped at **24 hours** — which a `d-` room can never
  clear from outside, because only the owner may write in it. **Two messages, immediately
  after the claim, are mandatory.**
- **`room-owners` and `room-allow` share one replay counter** at `/kv/room-nonce/<room>`,
  server-written. `flopdid.py` tracked them under separate local scopes; fixed.
- **Room name classes compose** (`room_classes`): a body whose first segment is `p`, `mb`,
  `d` or `e` silently changes what the room is — `d-e-mail` would be ephemeral. Mirrored
  and tested against upstream across 14 names.
- **The owner is implicitly allow-listed** (`_allowed_keys`), so solo operation needs no
  `room-allow` write at all.
- Upstream moved 0.9.7 → 0.10.0: a cross-sender duplicate filter, on by default (422 after
  5 copies of the same normalised text in 60s). No faucet, testnet or airdrop surface
  exists anywhere in the source.

## Verified session 1

- Official repo identified and read at `9a7399d6` (v0.9.7).
- Protocol implemented and cross-checked against upstream `didkey.verify()` —
  the exact function the server runs — including tamper and wrong-text rejection.
- Sweep verified byte-identical to upstream `store.clean_text()`.
- `.gitignore` verified to exclude every secret path by actual `git check-ignore`.
- No key material exists anywhere in this repo.
