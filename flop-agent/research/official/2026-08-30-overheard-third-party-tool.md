# Overheard (@Crypto_Pranjal) — assessment, 2026-08-30

**Tier 9** (community). Not a Flop Labs product; the author says so. Everything
below about the tool comes from a user-supplied summary of an X thread —
**`overheard-five.vercel.app` is egress-blocked from this container (403 at the
proxy), so none of it has been verified first-hand and its code has not been
read.** Treat every capability claim as reported, not established.

## Verdict in one line

**Read-only features: harmless to look at. Anything that signs or creates a key:
never.** The tool changes nothing about our plan; the *signal* around it changes
two things about our pacing.

## The security line, and why it is absolute

Two of the reported features require a private key in a browser tab:

- **Create** — generates a DID in-browser, "seed never leaves the device".
- **Rooms / Play** — posts and issues cards "signed with your key".

Our rules already settle both, and they settle them the strict way:

1. **No second DID, ever.** `Create` is off-limits by the standing rule, not by a
   new judgement. One identity, continuous history — a second one halves the
   history and doubles the Sybil surface.
2. **The seed never enters a browser.** Not this one, not any. Even granting the
   author's good faith and correct code today, a Vercel deployment is re-served
   on every visit and can be changed at any moment by anyone with push access to
   it. A permanent, unrecoverable key pasted into a page that reloads from a CDN
   is the exact shape of the thing `STRATEGY.md` already refuses under "no
   third-party airdrop tool — official implementation only".

   Note the asymmetry that makes this cheap to obey: `flopdid.py --fetch` already
   does every signed operation from the phone in one command. There is nothing
   Overheard's signing features would let us do that we cannot already do.

**Card / Verify / Agent City** consume public data only. Our DID, the DID note
and `/r/d-bitflop` are all world-readable already, so pasting the DID into a
viewer discloses nothing. Fine to use, worth nothing to us either — we can read
the same endpoints with `curl`.

**Play** is explicitly stated to award points with no token or airdrop meaning.
Zero upside, and it is in the "signs with your key" family. Skip.

## What the tool tells us that the tool itself does not

**1. The community's own rubric matches what we built.** `Card` reportedly grades
an identity NOT SET UP / HALF SET UP / SET UP CORRECTLY by checking for a
persistent profile note plus signature history. That is a community invention
with no official standing — but it is evidence of what participants believe
counts, and by it we are already complete: the DID note is published and the
signature history is real and owner-only. **No new work follows from this.** It
is confirmation, and confirmation is not a task.

**2. The network's public surface is becoming legible, and that raises the value
of the room's contents.** A browsable visualisation means `/r/d-bitflop` is no
longer only our private log; it is a storefront that people and tools will
enumerate and compare. That does not change the content policy in `STRATEGY.md`
— it raises the payoff of following it, and raises the cost of a room full of
"initialization complete".

## The reported timeline, and what it changes

Reported (Tier 8-9, **unconfirmed**): airdrop Q4 2026, mainnet genesis target
Q1 2027, 100% fair launch, no presale, no VC.

If those dates hold, the runway to the airdrop is roughly **fourteen months**.
That is the single most consequential item in the whole summary, and it changes
pacing rather than direction:

- **The risk stops being competition and becomes attrition.** Fourteen months of
  a 7-day keepalive is sixty-plus cycles. The realistic way to lose this
  identity is not being out-competed — it is missing two consecutive weeks in
  month nine. **Automating the DID-note keepalive is now the highest-value
  unglamorous task available**, and it needs no key, so the PC can hold it
  (cron/launchd). The room write needs the seed and stays manual; a calendar
  repeat is the control there.
- **Patience becomes free.** There is no reason to rush a contribution, buy
  hardware, or post anything. Fourteen months is long enough that quality
  compounds and haste does not.
- **The asymmetry is favourable either way.** If the timeline is long we are
  positioned and merely have to persist; if it is short we are already done with
  setup. Nothing we would do differently under one is harmful under the other,
  which is why this is safe to act on despite being Tier 8.

**Do not treat the dates as fact.** They enter `SOURCES.md` as reported, and the
`STRATEGY.md` rewrite triggers still require Tier 1-5 confirmation.

## What we are NOT doing about it

- Not creating a key in it. Not importing the seed into it. Not playing the quiz.
- **Not replying on X.** Sending the author a bug report would be an SNS post,
  which needs the user's approval, and we have no verified finding to send: the
  page cannot be reached from here, so anything we said about it would be
  guesswork about software we have not run. If the user wants this pursued, the
  honest first step is for them to open the page and describe what it shows.
- Not filing anything upstream about retention. The obvious candidate — that a
  claimed room with no messages silently loses its claim — **is already
  documented** in `src/manual.md` ("open a room when you have someone to talk to,
  not to reserve the name"). See the correction in
  `2026-08-30-owned-room-retention.md`.
