# STATUS — 2026-08-27

## Participation state

| Item | State | Note |
|---|---|---|
| Permanent DID | **NOT YET CREATED — deliberate** | See decision below. One command, on your device. |
| Seed backup | n/a | Nothing to back up yet. |
| DID note published | NO | Blocked: Technocore unreachable from the agent. |
| Signed check-in | NO | Blocked: same. URLs can be pre-built here. |
| Signing toolkit | **DONE and verified** | Accepted by upstream's own verifier, both backends. |
| Testnet | **NOT STARTED** | No official start date. |
| Miner / validator | Deferred | No specs published. |
| GitHub contribution | Candidates identified, none filed | Approval required before filing. |

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

## Verified this session

- Official repo identified and read at `9a7399d6` (v0.9.7).
- Protocol implemented and cross-checked against upstream `didkey.verify()` —
  the exact function the server runs — including tamper and wrong-text rejection.
- Sweep verified byte-identical to upstream `store.clean_text()`.
- `.gitignore` verified to exclude every secret path by actual `git check-ignore`.
- No key material exists anywhere in this repo.
