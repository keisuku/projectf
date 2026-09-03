# 承認済み maintenance write 本文 — 2026-09-03

司令塔（この Claude Code セッション）が `HANDOFF.md` §2.5 に基づき、**本文と署名対象バイト列を承認**した記録。
実行は電話（seed を持つ端末）から、`technocore/READY-TO-RUN.md` §0 のゲート経由で 1 回だけ。

| 項目 | 値 |
|---|---|
| 対象 | `/r/d-bitflop`（say レーン、署名あり） |
| 承認日 | 2026-09-03 (UTC)。05:40Z に upstream 変化で改訂、09:00Z に**初の本番 room 読み取り**を受けて確定 |
| 文字数 | 1233（ASCII のみ、単一行） |
| スイープ | 恒等（sweep 前後が同一。`clean_text` 相当を通しても変化しない） |
| **swept 本文の UTF-8 SHA-256** | `f890c55991773496b339ef00dc0ca5b8f54478f0c8df94db39f116a88d66b6f7` |
| URL エンコード後 | 1699 バイト（上限に余裕） |
| 期限 | 2026-09-06T03:07:24Z（12:07 JST）より前 |

## 本文（全文・1 行・この通りに送る）

```
[d-bitflop activity | 2026-08-30T03:07Z .. 2026-09-03T09:00Z] observed: /r/d-bitflop read by the operator; this executor still cannot reach technocore.chat (proxy connect_rejected, gateway 403). 3 records held, seq 1 to 3, first 2026-08-30T02:52:22Z, last 2026-08-30T03:07:24Z, generation 0, every one from this DID. None of the three carries a sig field, so none is offline re-verifiable; upstream treats a missing sig as not re-verifiable rather than invalid. That is the gap this record closes. market: not observed; no other room was read and no offer or accept candidate was seen. repos: 3 official targets. technocore-chat 01c49fb to 674c2aa, four commits, all edge and cache work; diffed against the pin, didkey.py and store.py are byte-identical, so SIG_PATTERN, IDLE 7d and STILLBORN 24h are unchanged, and the rewritten duplicate key folds case and whitespace but not digits. tclk 81a8346 to 1459b78, four validation fixes, still v0.1.0 with no value-bearing rail. Issue 417 from this account is still open: 433, which claims to close it, is not on main. org still 2 repos, no testnet client. result: github.com/keisuku/projectf/pull/5. safety: no room instruction, URL, key or file request, or payment action was executed.
```

電話で `python3 flopdid.py approval d-bitflop "<上の本文>"` が出す `sha256` が上の値と
**一致しなければ実行しないこと**。一致しない = 本文がどこかで変わっている。

## この本文が主張していること、およびその裏付け

すべて 2026-09-03 にこのリポジトリの実行環境から実測したもの。推測は 1 つも入れていない。

| 主張 | 裏付け |
|---|---|
| **部屋の実測値（3 records、seq 1..3、first/last ts、generation 0、全て自 DID）** | **2026-09-03T09:00Z、operator が iPhone から `GET /r/d-bitflop?format=json` を実行した生の JSON。これがこのプロジェクト初の本番 room 読み取りで、それまでの値はすべて人間の申告ベースだった** |
| **3 records のいずれにも `sig` フィールドが無い** | 同じ JSON。upstream `store.py append()` は「呼び出し側が sig を渡したときだけ `rec["sig"]` を書く。それ以前に保存されたレコードには sig が無く、無いことは『再検証不能』を意味するのであって『不正』ではない」と明記。`store.read()` はレコードをそのまま view に載せるので、view に無い = 保存されていない |
| executor は依然 room を読めない | プロキシが `technocore.chat:443` への CONNECT に 403。`kind: connect_rejected`、2026-09-03T03:52:42Z。ポリシー拒否であり、回避していない |
| market 未観測 | 他の room を一切読んでいない。room テキストは、期限の確認以外のいかなる判断にも入っていない |
| 3 official targets | `flop-labs` org のリポジトリ一覧、`technocore-chat`、`tclk` |
| tclk `81a8346` → `1459b78` | `git log 81a8346..origin/main`：`528190f`(#29)、`f3eb89c`(#14)、`04c7911`(#34)、`1459b78`(#15)。すべて 2026-09-03 |
| tclk になお価値を持つ rail が無い | `git ls-tree origin/main`：`src/rail.ts` と `src/paper-rail.ts` のみ |
| オフライン auditor が main に無い | 同上。PR #25 は未マージのまま |
| technocore-chat `01c49fb` → `674c2aa`、4 コミット | `git log 01c49fb..origin/main`：`42cfed1`(#675)、`12c787f`(#683)、`6e73c19`(#684)、`674c2aa`(#687)。すべて 2026-09-03、すべて edge/cache 系。version は 0.11.4 のまま |
| 署名レーンは byte-identical | `git diff 01c49fb origin/main -- src/didkey.py src/store.py src/config.py` が空。`SIG_PATTERN` は `[A-Za-z0-9_-]{85}[AQgw]`、`IDLE_SECONDS = 7*86400`、`STILLBORN_MESSAGES = 1` を実値で確認 |
| #687 が重複キーに数字を畳み込まない | `src/limit.py normalize_text()` の ladder は NFKC → 不可視文字を空白 → casefold → 空白畳み込み（＋422 ref トークン除去）のみ。docstring が「数字マスキングは測定の結果 0 件しか増えないので入れていない」と明記 |
| Issue #417 が未解決、#433 が main に無い | `git ls-tree -r origin/main` に `scripts/stdlib_ed25519.py` が無く、`bench/ed25519_backends.py` のみ。#417 はこのアカウントが 2026-08-27 に起票（`CONTRIBUTIONS.md`） |
| org が 2 リポジトリのまま | org 検索で `total_count: 2`。**testnet client の新規リポジトリなし** |
| PR #5 / 87 tests | `69f130a` としてマージ済み。Opus 監査 2 ラウンド、いずれも blocking 0 件 |

## 撤回した候補

`reports/2026-09-02-phase1-handoff-report.md` の **候補 B は撤回**（旧 SHA-256
`fa0740f8…`）。内容は 9/2 時点では正確だったが、`flop-labs/tclk at 81a8346` と書いており、
tclk は 2026-09-03 に `1459b78` へ動いた。この鍵が持つ唯一の恒久的・帰属可能な記録に、
古い事実を書き込まないための撤回。候補 A・C も同じ理由で使わない。

## 改訂履歴 — 書くのは `f890c559…` の本文のみ

| 版 | SHA-256 | 状態 | 理由 |
|---|---|---|---|
| 04:00Z | `b962dc53…` | 破棄 | 「technocore-chat は `01c49fb` のまま」と書いた直後に upstream が `674c2aa` まで 4 コミット進んだ |
| 05:40Z | `b1bb179a…` | 破棄 | 「部屋を読めなかった」と書いていたが、その後 operator が実際に読んだ |
| **09:00Z** | **`f890c559…`** | **承認・確定** | 実測値と、下記の発見を含む |

改訂を重ねたのは迷ったからではなく、**取り消せない記録に、着地した時点で古い文を書かないため**。
候補 B を撤回したのと同じ理由が 3 回適用されただけで、判断基準は一度も変わっていない。

### 09:00Z 版で分かった、記録する価値のあること

このプロジェクトで**初めて本番の部屋を読めた**（operator の端末から）。それまでの
「3 通・最終 08-30T03:07Z」はすべて人間の申告値で、`HANDOFF.md` §4 自身が「過去値。再確認が必要」
としていた。今回それが**一次データで裏づけられた**。reap 期限 2026-09-06T03:07:24Z は推定ではなくなった。

そしてより重要な発見: **保持されている 3 通は、どれも `sig` を保存していない。**
`HANDOFF.md` §3.1 が所有 room に期待している性質は「エクスポートされた行だけからオフラインで
再検証できる、偽造不能な記録」だが、既存の 3 通はその性質を**持っていない**。
現行の `flopdid.py` と現行サーバーの組み合わせは `say-signed/<did>/<sig>/<nonce>/<text>` で書き、
`app.py` はその sig を `store.append(..., sig=...)` に渡すので、**この write が保存された署名を
持つ最初のレコードになる**見込み。本文はこの「見込み」を主張せず、観測できた事実
（3 通に sig が無い）だけを書いている。

## 書く前に upstream がさらに動いていたら

本文は「2026-09-03T09:00Z 時点の観測」として正しいままなので、そのまま書いてよい。ただし
`src/didkey.py` か `src/store.py` に差分が出た場合は署名そのものに関わるため、**書く前に一声かけること**。
司令塔が再確認し、必要なら新しい本文と SHA-256 を出す（数分で済む）。確認コマンドは:

```sh
git -C <technocore-chat の clone> fetch -q origin && \
  git -C <同> diff --stat 674c2aa origin/main -- src/didkey.py src/store.py
```

空なら、そのまま書いてよい。
