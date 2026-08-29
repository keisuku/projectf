# X / community intel, 2026-08-29 — and the one item in it that is dangerous

Relayed by the user from a Grok summary of X posts in the preceding 24 hours. Recorded
because the *linkage* question it raises is real and was a genuine gap in our plan. Tiered
carefully, because the summary blends three very different kinds of claim into one voice.

---

## 0. The dangerous item, first

> "Technocore DIDを作成 `https://floppysol.xyz/onboard` などでキーを生成"

**Do not use this. Do not visit it to "check".** Treat it as hostile until Flop Labs
publishes it themselves.

Verified 2026-08-29 against the full official source tree (`flop-labs/technocore-chat`,
fetched today):

- `floppysol.xyz` appears **nowhere** — not in the README, the manual, `SKILL.md`,
  `patterns.md`, `SECURITY.md`, or any source file.
- The only domains the official code names are **`technocore.chat`** (the service) and
  **`flop.finance`** (`CHAT_SECURITY_CONTACT` / `security@flop.finance`).
- The official onboarding path needs no site at all. `SKILL.md` — served verbatim at
  `technocore.chat/skill.md` — is the onboarding document, and DID creation is
  **local key generation**, described in `patterns.md`. There is nothing to visit.

A third-party page offering to *generate your DID key* is the highest-value phishing
target this ecosystem has. A key generated in someone else's browser is a key you cannot
prove they did not keep, and there is no revocation: a `did:key` **is** its keypair, with
no registry and no resolver (`src/didkey.py`). Losing it is not "getting hacked later", it
is handing over the identity permanently, silently, at the moment of creation.

This does not apply to us in the narrow sense — our key was generated locally on-device on
2026-08-27 and the standing rule is **never a second DID**. It is recorded because the same
link will be circulated again, harder, the day the faucet opens, and because a *lookalike
domain in a helpful onboarding guide* is precisely the shape `STRATEGY.md` §Risk predicted.

`floppysol` also reads as **flop + Solana**. No official source names a base chain at all
(`STRATEGY.md` §"conditions that force a rewrite" item 5 is still unmet). A domain
asserting one is asserting something the project has not.

---

## 1. Tiering the rest

The summary is one voice, but the claims come from three different places:

**Tier 8 — press/official-account statements, consistent with what we already hold:**
- Airdrop share **20.4%** of supply, split across miners, validators, agents, early
  community. (We had "~20% proposed over 10 years" from press. Consistent, more precise,
  still not Tier 1–2.)
- No VC allocation, no presale, 100% fair launch; Hayes self-funding.
- Direction of qualification: follow `@flop_labs`, hold a Technocore DID, be useful.
- **No allocation numbers, no snapshot date, no formula.** The summary says so itself, and
  flags that anyone quoting a specific `$FLOP` figure is fabricating. That warning is
  correct and worth keeping.

**Tier 9–10 — a community member's guide, not an official procedure:**
- The 5-step "onboarding checklist" (signed hello → DID note → lobby intro → create a room
  → link contributions).
- "Apply as Miner / Validator / KOL via the official form."
- The `floppysol.xyz` link above.

**What the *actual* official onboarding says** (`SKILL.md`, read today, byte-identical to
what `/skill.md` serves):

> **Your first action:** Pick a nick and post a short greeting in `/r/lobby` […] **Say it
> in your own words**, not this sentence: a room refuses further copies of a text several
> senders have already posted […] Keeping it under 16 characters also puts it under the
> length floor, where nothing is ever refused.

That is the whole official checklist. Read the manual; use the signed lane if you can run
code. There is **no** official gate listing "DID note, lobby intro, room creation" as
required steps, and **no** mention anywhere in the source of a KOL programme, an
application form, or a reward for spreading the word.

The community checklist is not *wrong* — it happens to describe roughly what we are doing
anyway, and steps 1–4 are all cheap and harmless. It is simply not evidence of a rule.
**Never act on Tier 8+ alone** (`SOURCES.md`); acting on Tier 9 because it was relayed
confidently is the same error one tier further down.

---

## 2. The item that is a real gap: linkage

> "貢献をDIDに紐づける — 投稿の公開リンクをコピーし、Technocoreの部屋でSigned modeで貼り付ける"

**This one deserves to be taken seriously even though its tier is low**, because it does not
depend on the rumour being true. It follows from the architecture:

A `did:key` has no registry and no resolver. Nothing anywhere associates our DID with our
GitHub account, our contribution, or anything else. Whoever eventually evaluates
participation sees a key with a published note and no history attached to it — the work
exists (upstream #417 → #433, credited by name, permanently timestamped) but is
**not reachable from the identity**.

That is a real defect in our own plan, and it is ours, not the rumour's: `STRATEGY.md`
already said *"lobby is for announcement, once"* and the announcement was never made. We
built the identity infrastructure and never connected it to the work.

**It is not, however, a catastrophe, and the panic reading is wrong:**

- Linking later does not move the contribution's timestamp. #417 was filed 2026-08-27 and
  #433 credits the account by name; that record is public, permanent, and independent of
  anything on Technocore.
- **The testnet still does not exist.** Verified today: the `flop-labs` org contains
  **exactly one repository**, `technocore-chat`, last pushed 2026-08-29T17:06Z. No client,
  no faucet, no registration, no points, nothing in the source tree mentioning any of them.
  The route reported to decide allocation has not started. There is no scoreboard to be
  behind on.
- The linkage costs **one signed write**. A gap that closes in one fetch is a to-do, not a
  crisis.

Correct response: close it today, in the same device session as the room claim, and stop
treating identity and activity as two separate projects.

---

## 3. What changed in the plan

Not the direction — the DID is still the road, and `d-watchtower` is still today's task.
What changed is that the room now has a **job on day one** instead of being an empty
asset waiting for the testnet:

    DID note  ──points to──▶  d-watchtower  ──contains──▶  signed contribution records
    (durable, unsigned lane)   (durable, owner-signed)      (links to #417 / #433)

The two seeding messages the reaper forces us to post are no longer filler. Message 2 is
the contribution linkage. The anti-stillborn requirement and the linkage requirement are
satisfied by the same write.

Lobby gets **one** announcement, in original wording (the dupe filter refuses the 6th copy
of any canned text in 60s, and `zero_response_share` is published to expose farming). It
retains 15–30 minutes and is not a record — the record is the room and the note.

## 4. Still unverified, do not act on

- Whether any Miner / Validator / KOL application form exists. If one does, it will be
  linked from `@flop_labs` or `flop.finance` and from nowhere else. A form requesting a
  seed phrase, a private key, or a wallet connection is a scam by construction, regardless
  of where it is linked from.
- Whether Technocore activity counts toward allocation at all. Unchanged since
  2026-08-27: Technocore's own README says it "settles nothing, holds no keys, and is not
  part of any protocol." The on-ramp, not the scoreboard.
