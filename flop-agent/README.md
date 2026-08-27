# flop-agent

Single source of truth for participation in **Flop Network / Flop Labs /
Technocore**, as a long-lived agent with one permanent identity.

Not an airdrop bot. The goal is one durable DID, continuous useful activity, a
verifiable record of it, and readiness for testnet day 1.

## Start here

| File | What it holds |
|---|---|
| `STATUS.md` | Where participation actually stands right now |
| `STRATEGY.md` | Route ranking, opportunity, risk, and what triggers a rewrite |
| `SOURCES.md` | Evidence tiers, and what this container can and cannot reach |
| `CONTRIBUTIONS.md` | Append-only log of verifiable activity |
| `CLAUDE.md` | Operating rules for the agent |
| `identity/README.md` | **How to create and back up the permanent DID** |
| `technocore/README.md` | The signing toolkit and the protocol rules that bite |
| `testnet/README.md` | Day-1 readiness checklist and trigger conditions |

## The one thing to do first

```bash
git clone -b claude/flop-participation-agent-bx8e7z https://github.com/keisuku/projectf
cd projectf/flop-agent/technocore/scripts
python3 flopdid.py selftest    # verify the crypto before it makes your key
python3 flopdid.py keygen      # prints your DID; the seed is never printed
```

Then **back up the seed file** at the path `keygen` reports. It cannot be
regenerated.

Runs on stock Python 3.11+ with no packages installed — **a phone shell is
enough**. See `identity/README.md` for the git-free two-file install.

## Security posture

- The private seed never leaves the machine that generated it, and is never
  printed, committed, or sent to any model or service.
- `.gitignore` denies key material by default; verified with `git check-ignore`.
- Signed write URLs are treated as capabilities, not as text — upstream
  `SECURITY.md` documents that a captured one becomes replayable.
- Only the official implementation (`flop-labs/technocore-chat`) is used as a
  reference. No third-party airdrop tooling.

## Where this is heading

A FLOP ecosystem intelligence agent: watch official sources and the upstream
repo, diff them, surface what changes expected value, summarise in Japanese, and
keep a verifiable contribution record. The intent is that this becomes genuine
recurring workload on the network rather than activity performed to look active.

## Reality check

There is **no FLOP token today** — no contract, no presale, no claim page. Every
offer of one is a scam. See `STRATEGY.md` § Risk.
