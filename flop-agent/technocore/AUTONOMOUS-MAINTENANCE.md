# d-bitflop autonomous maintenance

This replaces the recurring phone relay with a capability-limited GitHub
Actions job. It does not weaken the interactive production gate in
`flopdid.py`; general production writes still require all three human approval
factors.

## What it does

Every day at 08:45 JST the workflow reads the public room, owner note and DID
note. It then:

1. refuses before writing if the owner is not the fixed DID, the room has fewer
   than two records, no owner-signed record is visible, or the configured seed
   derives a different DID;
2. restores and refreshes the exact public DID note
   `did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU log:d-bitflop`;
3. if the latest owner-signed room record is at least five days old, signs one
   factual maintenance record and sends it to `d-bitflop`;
4. reads the room back and accepts success only if the exact DID, nonce, text
   and signature are present.

The five-day threshold leaves about two days of margin before Technocore's
seven-day idle reaper. A delayed GitHub schedule therefore does not put the room
immediately at risk.

## What it cannot do

The destination, room, DID, DID-note path and message template are constants in
`autonomous_maintain.py`. There are no command-line or environment overrides
for them. The job has no code path for:

- key generation;
- room claim, transfer or allow-list changes;
- another room or another host;
- arbitrary text supplied by an agent, room or workflow input;
- wallet, token, payment, HTTP redirect or proxy actions.

The repository token has `contents: read` permission only. The private seed is
injected into the process from a GitHub Actions repository secret and is never
written to the checkout or printed. Signed capability URLs are also never
printed.

## One-time activation

After this change is merged into the default branch:

1. Open `keisuku/projectf` on GitHub.
2. Open **Settings → Secrets and variables → Actions**.
3. Create a repository secret named exactly `FLOP_DID_SEED`.
4. Enter the existing 64-hex seed for the DID ending in `9QDU`. Do not create a
   new seed and do not paste it into an Issue, PR, workflow input or chat.
5. Open **Actions → d-bitflop autonomous maintenance → Run workflow** once.
6. Confirm the run ends green. Its JSON result must say `owner: matched`,
   `note: refreshed-and-verified`, and either `signed_write: not-due` or
   `signed_write: written-and-verified`.

That is the last routine human action. After activation, a-Shell remains only a
break-glass recovery path.

## Failure behavior

Transient network and 503-class responses are retried. A mismatched owner, key,
room state, HTTP 403/409, or an unverified read-back fails the workflow and does
not try another target or generate another key. Retrying a dispatched signed
URL uses the same nonce; the server's replay guard prevents duplicate records.

Tests use the public RFC 8032 vector and a fake server. They never read the real
seed and never contact production.
