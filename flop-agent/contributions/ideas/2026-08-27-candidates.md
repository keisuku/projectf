# Contribution candidates — evaluated 2026-08-27

> **Duplicate check is mandatory before any of these is filed.** Run it every
> time; the repo moves fast enough that a candidate can be claimed overnight.
> Checked 2026-08-27:
>
> - The "capacity refusal should name the sharded path" idea was **already
>   filed as #165** (2026-08-25, `good first issue`) and already has **four PRs**
>   fighting over it (#167 closed, #283 closed, #267 open). Do not file it.
> - Candidates A and B below returned **zero** matching issues and PRs.
>
> Lesson recorded: the `good first issue` label is where the crowd goes, so a
> labelled easy issue is the *worst* odds in the repo, not the best.

Scored on the evaluation function. Nothing here has been filed; every public
action needs approval first.

---

## A. Dependency-free signer for the signed lane  ★ RECOMMENDED

**What.** Upstream `scripts/sign.py` needs `cryptography`, provisioned through a
PEP 723 header by `uv`. That assumes network access and a package manager at
signing time. Offer a stdlib-only Ed25519 signer (already written and verified
here) so the signed lane is reachable from a locked-down box or a phone.

**Why it fits their stated mission.** The repo exists for "agents whose sandbox
only allows webfetch". `docs/design.md` §5.2 makes the constraint explicit: a
webfetch-only agent cannot sign, so signing is for agents that "also have a
shell". A shell without `pip` is squarely inside that population, and today it is
excluded by a packaging detail rather than by anything essential.

**Evidence it is real, not theoretical.** In this very container `cryptography`
imports and then dies with a pyo3 `PanicException` (missing `_cffi_backend`) —
which does not derive from `Exception`, so a normal `try/except Exception` around
the import does not catch it. The pure-Python path is what made signing work here
at all.

| | |
|---|---|
| FLOP value 3 · Alignment 5 · Usefulness 5 · Verifiability 5 · Cost 4 · Risk **low** | |

**Caution.** `AGENTS.md` enforces hard core size caps (`sz-baseline.json`) and
says growth past a cap "needs a new primitive, or belongs in extra". This must be
proposed as `scripts/`- or `examples/`-level, explicitly **not** core, and framed
as a *verification-independent* addition — the server keeps verifying with
libsodium either way. **Open an issue first and ask; do not arrive with a PR.**

---

## B. Key-hygiene option for `scripts/sign.py`  ★ RECOMMENDED (smallest, cleanest)

**What.** `sign.py keygen` prints the seed to stdout. For a tool that mints
identities people intend to keep — and which may carry airdrop history — stdout
means terminal scrollback, shell history, CI logs, and any agent transcript that
wrapped the call. Propose `--out FILE` writing at mode 600, printing only the DID.

**Why it is in scope and not a security report.** This is a local developer
utility, not the service, so it is **not** a vulnerability under their threat
model and must **not** go to the private advisory channel. It is an ordinary
usability/hygiene issue. Their docstring already hedges — "weaker than
randomness, fine for a demo, not for an identity you care about" — so the
distinction between demo and durable identity is one they already recognise.

| | |
|---|---|
| FLOP value 3 · Alignment 5 · Usefulness 4 · Verifiability 5 · Cost 5 · Risk **low** | |

**Why this one first.** Tiny, obviously correct, easy to accept, and it reads as
someone who actually used the tool rather than someone farming a contribution
graph. Best possible first interaction with the maintainers.

---

## C. Japanese onboarding guide  ★ BUILD, DO NOT PUBLISH YET

**What.** A genuine Japanese-language guide to participating: what FLOP is, what
Technocore is *and is not*, how to make a permanent DID safely, the nonce and
sweep rules that cause silent 403s, and how to avoid the scams that will appear
before any token exists.

**Why it has real value.** The Japanese-language crypto audience is large and
currently has essentially no accurate FLOP material. The highest-value piece is
not a translation — it is the **scam-avoidance** section, because "no token
exists yet" is exactly the fact that stops people losing money in the window
before launch.

| | |
|---|---|
| FLOP value 2 · Alignment 3 · Usefulness 4 · Early edge 4 · Cost 3 · Risk **medium (public speech)** | |

**Why not upstream.** Translations carry ongoing maintenance cost for a fast
repo (v0.9.7, 313+ PRs in two weeks). Offering one unsolicited is more likely to
be a burden than a gift. Host it ourselves; propose a link only if they want one.

**Gate.** No SNS post, no publication, without explicit approval per §15/§21.

---

## Rejected outright

- **Bulk issue/PR filing.** 209 open issues already. Volume is negative signal.
- **Any "airdrop tool" from a third party.** Official implementation only.
- **Anything that raises message counts to look active.** The engagement
  aggregates in `/rooms` exist to catch exactly that.
