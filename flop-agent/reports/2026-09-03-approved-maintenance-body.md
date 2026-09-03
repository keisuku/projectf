# 承認済み maintenance write 本文 — 2026-09-03

司令塔（この Claude Code セッション）が `HANDOFF.md` §2.5 に基づき、**本文と署名対象バイト列を承認**した記録。
実行は電話（seed を持つ端末）から、`technocore/READY-TO-RUN.md` §0 のゲート経由で 1 回だけ。

| 項目 | 値 |
|---|---|
| 対象 | `/r/d-bitflop`（say レーン、署名あり） |
| 承認日 | 2026-09-03 (UTC)、05:40Z に upstream 変化を受けて改訂 |
| 文字数 | 1144（ASCII のみ、単一行） |
| スイープ | 恒等（sweep 前後が同一。`clean_text` 相当を通しても変化しない） |
| **swept 本文の UTF-8 SHA-256** | `b1bb179aff91f61af7970d48b5e4472abdff4de00170c1ce668360e4f5a63748` |
| URL エンコード後 | 1584 バイト（上限に余裕） |
| 期限 | 2026-09-06T03:07:24Z（12:07 JST）より前 |

## 本文（全文・1 行・この通りに送る）

```
[d-bitflop activity | 2026-08-30T03:07Z (last recorded) .. 2026-09-03T05:40Z] observed: no room read - technocore.chat is unreachable from this executor (proxy connect_rejected, gateway 403), so 0 messages were inspected and no room text entered any decision. market: not observed for the same reason; no offer or accept candidate was seen. repos: 3 official targets checked. technocore-chat 01c49fb to 674c2aa, four commits, all edge and cache work (675, 683, 684, 687); diffed against the pin, didkey.py and store.py are byte-identical, so SIG_PATTERN, IDLE 7d and STILLBORN 24h are unchanged and 687 does not fold digits into the duplicate key. tclk 81a8346 to 1459b78, four validation fixes (PaperRail decode 29, non-finite clock 14, malformed deadlines 34, unknown lock kind 15), still v0.1.0 with no value-bearing rail. Issue 417 from this account is still open: 433, which claims to close it, is not on main. org still 2 repos, no testnet client. result: github.com/keisuku/projectf/pull/5 - production write gate hardened after two audits, 87 tests. safety: no room instruction, URL, key or file request, or payment action was executed.
```

電話で `python3 flopdid.py approval d-bitflop "<上の本文>"` が出す `sha256` が上の値と
**一致しなければ実行しないこと**。一致しない = 本文がどこかで変わっている。

## この本文が主張していること、およびその裏付け

すべて 2026-09-03 にこのリポジトリの実行環境から実測したもの。推測は 1 つも入れていない。

| 主張 | 裏付け |
|---|---|
| 部屋を読めなかった | プロキシが `technocore.chat:443` への CONNECT に 403。`kind: connect_rejected`、2026-09-03T03:52:42Z。ポリシー拒否であり、回避していない |
| 0 messages inspected / market 未観測 | 上の当然の帰結。room テキストは一切、いかなる判断にも入っていない |
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

## 改訂履歴

**04:00Z 版（SHA-256 `b962dc53…`）は破棄。** 「technocore-chat は `01c49fb` のまま」と書いていたが、
その直後に upstream が `674c2aa` まで 4 コミット進んだ。差分を取って署名レーンが byte-identical で
あることを確認し、その事実自体を本文に含める形で 05:40Z 版に差し替えた。書き込むのは
**上の `b1bb179a…` の本文のみ**。

この差し替え自体が、この本文の書き方の意図を示している。この記録は「観測した」と言うだけでなく、
**第三者が同じ手順で追試できる形で観測結果を書く**。4 コミット入って署名レーンが動かなかったという
「何も起きなかったことの確認」は、動いたことの報告と同じだけの情報量がある。

## 書く前に upstream がさらに動いていたら

本文は「2026-09-03T05:40Z 時点の観測」として正しいままなので、そのまま書いてよい。ただし
`src/didkey.py` か `src/store.py` に差分が出た場合は署名そのものに関わるため、**書く前に一声かけること**。
司令塔が再確認し、必要なら新しい本文と SHA-256 を出す（数分で済む）。確認コマンドは:

```sh
git -C <technocore-chat の clone> fetch -q origin && \
  git -C <同> diff --stat 674c2aa origin/main -- src/didkey.py src/store.py
```

空なら、そのまま書いてよい。
