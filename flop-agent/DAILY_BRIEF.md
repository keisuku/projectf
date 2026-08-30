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
  所有する d- ルーム名を1つ決める。決まり次第、iPhone で claim を1回だけ実行する。
  （鍵の所持証明つきの署名で、作成時に一度きり。取り直しは永久に効かない）
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

## The one decision that is blocking, and only you can make it

**The `d-` room name.** It is claimed at creation, by whoever gets there first,
and it can never be re-claimed or renamed. Constraints from upstream:
`^[a-z0-9][a-z0-9_-]{0,47}$`, must start `d-`, and the body must not begin with
another class marker (`p-`, `mb-`, `e-`) or it silently inherits that class.

Candidates, all rehearsed as valid and ownable:

| Name | What it says |
|---|---|
| `d-flop-jp` | short, obvious, the Japanese-language niche the strategy already owns |
| `d-flopagent-jp` | names the agent, not just the language |
| `d-keisuku` | personal; unambiguous, and nobody contests it |
| `d-flop-watch` | describes the function (official-source watching and diffing) |

My recommendation is **`d-flop-jp`**: short names are the scarce ones, it is
descriptive without dating itself, and it reads as a place rather than a handle.

## Watch list — unchanged, still empty

Testnet start date · client release · faucet · agent registration · scoring or
points rules · Sybil rules · miner/validator specs · whitepaper or tokenomics ·
any official token contract (until then, all are fake).
