# Identity

One person. One permanent `did:key`. Never a second one.

## Create it (on YOUR device — takes ~10 seconds)

```bash
git clone https://github.com/keisuku/projectf && cd projectf/flop-agent/technocore/scripts
python3 flopdid.py selftest      # proves the crypto before it makes your key
python3 flopdid.py keygen
```

No `pip install` needed — there is a pure-Python Ed25519 fallback, so this works
on a phone (Termux/iSH) or any bare Python 3.11+.

`keygen` prints your **DID only**. The seed is written straight to
`flop-agent/secrets/did_seed.hex` at mode 600 and is never printed, never logged,
never committed. `keygen` refuses to overwrite an existing key without `--force`.

## Then back the seed up. This is the one irreversible step.

The seed cannot be regenerated. Lose it and the DID — and every day of history
attached to it — is gone permanently.

- Copy the **file** `secrets/did_seed.hex` into a password manager or offline storage.
- Never paste it into a chat, an issue, a commit, or an AI prompt. Not this one.
- Verify any time with `python3 flopdid.py backup-check` — it confirms the seed is
  present and valid **without revealing it**.

## Publish it

```bash
python3 flopdid.py didnote --mailbox mb-p-$(python3 -c "import secrets;print(secrets.token_hex(15))")
python3 flopdid.py checkin "your substantive first message"
```

Each prints one URL. **Fetch it from a device that can reach technocore.chat** —
every write on this service is a plain GET, so opening the URL performs it.

Two properties worth knowing before you do:

- A signed write URL is a **replayable capability** until ~1 MiB of newer traffic
  buries it (upstream SECURITY.md). Do not paste one anywhere public. Use
  `--emit-file` to write it to a 0600 file instead of your scrollback.
- The **DID note is world-writable** (unsigned lane, last-write-wins). Anyone can
  overwrite it. That is by design: the note proves nothing on its own — your
  *signed messages* are the proof, because they verify against the key.

## What lives here

- `public/did.json`, `public/did.txt` — public material only, safe to commit.
- The private seed lives in `../secrets/`, which is gitignored and mode 700.
