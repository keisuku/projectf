# DAILY BRIEF — 2026-08-30 (day 3)

```
FLOP DAILY
現在の状態：
DID：OK（did:key:z6Mk…9QDU / note 公開済み・検証済み）
Technocore：NG（このコンテナから egress ブロック — 2026-08-30 再確認）
Testnet：未開始（公式リポジトリに兆候ゼロ、org のリポジトリは依然1つ）
重要変更：あり（upstream 0.10.0 — 署名の綴りが1つに固定／署名レコードが sig を保持／
　　　　　　room export 追加。そして DID note は仕様上ロック不可能と判明）

今日の最適行動
S+：
  d-bitflop を iPhone で claim する（`python3 flopdid.py claim d-bitflop` 1回だけ）
  実行前に §2a の2つのURLで「まだ誰も持っていない・1件も投稿がない」ことを確認する
S：
  DID note の keepalive を iPhone から実行する（期限 ~2026-09-04）
A：
  mb-p-<推測不能> のメールボックスを DID note に載せる

今日はやらない：
  GPU購入・miner準備／SNS投稿／DIDのX投稿／PR量産／2つ目のDID作成／
  Technocoreでのメッセージ数稼ぎ（0.10.0 で重複投稿は 422 で弾かれるようになった）

理由：
  upstream を読み直した結果、この サービスで「所有者の鍵だけが書ける」面は
  d- ルームただ1つだと確定した。DID note は設計上 world-writable で、署名lane は
  room-owners / room-allow の2名前空間にしか存在しない（それ以外は 400）。
  同時に 0.10.0 で「署名レコードが署名を保持」「ルームを byte-exact に export できる」
  が入ったため、所有ルームは “第三者がサーバ抜きで検証できる履歴” になった。
  買い直せない資産はこれだけで、しかも先着1回。名前を決めることが今日の律速。
```

## Executed this session (no network needed, all local and verified)

The container still cannot reach `technocore.chat`, so this session spent its
time on the one thing that can be done without it: making sure that when the
human *does* run the one-shot claim, it lands.

1. **Re-verified the toolkit against upstream `0.10.0`** — both crypto backends,
   the server's own `didkey.verify()`, tamper rejection, wrong-text rejection,
   nonce monotonicity. All green.
2. **Proved the sweep identical, not sampled.** Every code point in Unicode
   (1,114,112) plus 20,000 random strings plus the length boundary, compared
   against upstream `store.clean_text()`. Zero mismatches.
3. **Checked the tightened signature rule.** 0.10.0 pins `SIG_PATTERN` to a
   canonical last character (`[AQgw]`); a non-canonical signer now 403s. Ours was
   already canonical — 3000/3000 accepted, all four tails seen.
4. **Rehearsed the whole claim against the real server code**, in-process, on a
   throwaway root and a test-vector key: the claim URL our tool builds is
   accepted, unsigned writes are refused, a stranger's signed write is refused, a
   stranger's re-claim is refused, the stored record re-verifies offline, and the
   room exports. Committed as `technocore/scripts/rehearse_claim.py`.
5. **Added `flopdid.py claim`** — the one-shot claim with the guards that a
   one-shot deserves: name shape, ownability, a refusal on an ephemeral (`e-`)
   name, a warning on an unlisted (`p-`) one, and `?if_absent=1` by construction.

Detail: `research/official/2026-08-30-upstream-0.10.0-delta.md`.

## Name decided: `d-bitflop`

Chosen by the user. Checked against every upstream rule and rehearsed green
end-to-end: valid under `^[a-z0-9][a-z0-9_-]{0,47}$`, `d-` class so ownable, and
the body `bitflop` does not begin with another class marker, so it does not
silently inherit `p-`, `mb-` or `e-`.

The claim URL is a *signed* URL and the seed is on the phone only — by design,
and the reason it was never generated in this container. So the URL cannot be
finished here; what can be, has been. Every fixed part is written out in
`technocore/READY-TO-RUN.md` §2, so the phone's output can be checked character
by character before it is fetched. Only `<sig>` and `<nonce>` come from the key.

**Before running it**, open the two pre-flight URLs in §2a. A room is ownable
from birth or never: upstream refuses a claim on a room that already has an owner
or even one message, and a refused attempt still burns the room's replay
counter.

## Watch list — unchanged, still empty

Testnet start date · client release · faucet · agent registration · scoring or
points rules · Sybil rules · miner/validator specs · whitepaper or tokenomics ·
any official token contract (until then, all are fake).
