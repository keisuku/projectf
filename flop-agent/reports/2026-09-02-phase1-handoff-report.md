# Phase 1 引き継ぎ報告 — 2026-09-02 (UTC) / 09-03 (JST)

報告者: 実行者（Claude Code）。宛先: 司令塔（人間経由）。形式は `HANDOFF.md` §8。

## 1. 確認済み / 推測 / 未確認

### 確認済み（一次情報で検証したもの）

- **リポジトリの実体**: `keisuku/projectf` には Codex の Phase 1 コード（`d-bitflop run-once`、`RECON.md`、9 tests）は**存在しない**。全ブランチ（`main`、`claude/status-check-and-execute-u39wxk`、`claude/flop-agent-d-room-claim-2vkyp7`）、Issue（0 件）、PR（0 件）を確認。
- 代わりに、前セッション（Claude Opus 5、2026-08-27〜30）の成果が未マージブランチ `claude/status-check-and-execute-u39wxk` にあり、**d-bitflop の claim（2026-08-30T01:53:29Z）と署名付き 3 通（seq 1..3、最終 2026-08-30T03:07:24Z = 12:07 JST）はこのブランチの `flopdid.py` で行われたもの**。引き継ぎ書 §4 の「最後に確認された状態」と一致する。この作業ブランチはそこから fast-forward した。
- **鍵の形式**: このリポジトリの署名ツールは 32 byte の hex seed ファイル（`secrets/did_seed.hex`、iPhone の a-Shell 上のみ）を読む。引き継ぎ書の「identity.pem + パスフレーズ」とは形式が異なる。Codex が PEM に変換した可能性はあるが未確認（下記）。
- **リポジトリは public**（引き継ぎ書 §5.1 は private と記載）。`data/`、export、`.env`、`*.pem`、`proof.log`、`approval*.json` は `.gitignore` 済みで `git check-ignore` で検証。
- **upstream**: `flop-labs/technocore-chat` を `01c49fb`（v0.11.4、2026-09-02）で取得。`src/didkey.py` は 0.10.0 以降変更なし、`clean_text`・`NAME_RE`・`IDLE_SECONDS`・`STILLBORN_*`・所有権名前空間も変更なし。`patterns.md` §6 に tclk/1 が追加（0.11.3）。`flop-labs/tclk` を `81a8346`（v0.1.0+5）で取得。詳細: `research/official/2026-09-02-upstream-0.11.4-delta.md`。
- **検証**: `selftest_upstream.py` と `rehearse_claim.py d-bitflop` が現行 upstream に対して両バックエンドで合格。
- **ローカル E2E（実サーバー）**: upstream を uvicorn で起動し、使い捨て鍵で claim → 署名 say ×2 → JSON 読み取り（generation/seq/nonce/sig）→ `/export`（`x-room-generation` ヘッダ）→ 未署名 write 403 → export 全行を upstream の `didkey.verify()` でオフライン再検証。
- **本番 write ゲート**（§5.4）: `flopdid.py` に実装。非 loopback 宛の `--fetch` は `--production` + 一回限り承認ファイル（スイープ後本文の SHA-256、kind/target/did/approved_by/expires を照合）+ TTY での対話確認、の 3 点が揃わなければ exit 3 で拒否。環境変数は一切読まない（構造テストで保証）。送信直前に本文・スイープ後本文・署名対象文字列とその hex・nonce・署名を表示。承認ファイルは送信の瞬間に `*.used-<utc>` へリネーム。全試行を `logs/proof.log` に JSONL で記録し、成功時は `/export` スナップショットと server 付与の `(generation, seq, ts)` を保存。テスト 29 件合格（Python 3.12 / 3.11 の 2 系統）。ローカルサーバーをコンテナの非 loopback IP で公開してゲートを実通し（拒否 3 経路・受理 1 経路・承認ファイル再利用の拒否）。
- **副次的に修正した実バグ**: 壊れた `cryptography`（`_cffi_backend` 欠落 → pyo3 panic）を `_verify_own` が「自分の署名が検証できない」と誤認し全 write を拒否していた。検証器を RFC 8032 ベクトルで先に試してから判定に使うよう修正（テストあり）。
- **ネットワーク**: このコンテナから `technocore.chat` / `flop.finance` は egress ブロック（2026-09-02 再確認、proxy で `connect_rejected`）。回避していない。`github.com` / `api.github.com` は到達可。

### 推測

- d-bitflop の最終書き込みは 2026-08-30T03:07:24Z のまま（人間がその後に書いていなければ）。よって reap 期限 **2026-09-06T03:07Z（12:07 JST）** は妥当。
- Codex の「非 loopback origin 固定ガード」と本実装のゲートは同じ概念で、Codex コードが来たら統合可能（Codex 側のガードを残し、その上に本実装の 3 要素経路を載せる）。

### 未確認

- **本番の d-bitflop の現在値**（メッセージ数・generation・seq・最終 ts）。コンテナから読めない。
- **DID note**（`/kv/did-64/776f70dbeec8e2`）が 2026-08-28 以降に refresh されたか。されていなければ **~2026-09-04 に reap 対象**。引き継ぎ書はこの義務に触れていない。
- Codex の Phase 1 コードの所在、`identity.pem` の実在と seed との対応、パスフレーズの環境変数名（§9.1）。

## 2. 行った操作

- 本番（technocore.chat）への**書き込みなし**。読み取りもコンテナからは不可能で行っていない。
- ローカル: upstream サーバー起動（使い捨て store、使い捨て RFC テスト鍵）。永続 seed には一切触れていない（このコンテナに存在しない）。
- リポジトリ: `HANDOFF.md` を直下に配置し `CLAUDE.md`（直下・`flop-agent/`）から参照。`flopdid.py` にゲートを実装、`tests/test_production_gate.py` 追加、`STATUS.md`・`technocore/README.md`・`READY-TO-RUN.md`・調査記録を更新。ブランチ `claude/d-bitflop-handoff-7z2nfp` に push し、`security` ラベル付き PR を作成して Codex レビューを依頼（Issue も作成）。

## 3. 生存 write の本文案（3 パターン）

前提: 全て実観測データのみ。挨拶なし。16 文字超で相互に異なる（422 回避）。ASCII のみで URL 予算に余裕。`<PR>` は PR 番号で確定してから承認する（承認ファイルの SHA-256 は確定本文に対して作る）。

**A. Codex 採用フォーマット準拠（観測できなかったことを正直に書く）**

```
[d-bitflop activity | 2026-08-30T03:07Z .. 2026-09-03] observed: no room text (technocore.chat unreachable from the executor; nothing was read). market: not observed. repos: 2 official targets checked, flop-labs/technocore-chat 01c49fb v0.11.4 (21 commits past 169ca89, signing lane unchanged) and flop-labs/tclk 81a8346 v0.1.0; 0 state changes to the protocol we sign against. result: github.com/keisuku/projectf/pull/<PR> (production write gate, 29 tests). safety: no room instruction, URL, key/file request or payment action was executed.
```

**B. upstream 差分の記録（第三者が GitHub で全て照合できる。推奨）**

```
upstream watch 2026-09-03: flop-labs/technocore-chat at 01c49fb (v0.11.4, 21 commits past 169ca89): didkey.verify and store.clean_text unchanged, SIG_PATTERN still [AQgw]-terminal, IDLE 7d and STILLBORN 24h unchanged, tclk/1 escrow convention added as patterns.md section 6 in 0.11.3; flop-labs/tclk at 81a8346 (v0.1.0, PR 7 rejects contradictory receipt outcomes). This key's toolkit re-verified against both: selftest_upstream and rehearse_claim green on the cryptography and pure-python backends.
```

**C. ゲート導入の宣言（この記録自体がゲート経由の第 1 号）**

```
2026-09-03: from this record on, every production write from this key passes a three-factor gate (command flag, one-time approval file carrying the swept body sha256, TTY confirmation) and leaves a proof.log entry plus a byte-exact /export snapshot re-verifiable with technocore-chat didkey.verify; implemented and tested against v0.11.4 in github.com/keisuku/projectf/pull/<PR>. This is the first record written through it.
```

推奨は **B**（自己申告が最も少なく、全数値が GitHub で照合可能）。A は Codex フォーマットとの整合、C は linkage（DID ↔ GitHub）の価値がある。

## 4. 司令塔が判断すべき点（3 つ以内）

1. **DID note の keepalive（~2026-09-04）を定型・内容固定の常設承認として許可するか、毎回ゲートを通すか。** 引き継ぎ書 §2.5 は全書き込みに承認を要求するが、この note は世界中が上書き可能な unsigned lane で、書く値は常に同じ DID 文字列。常設承認なら PC の cron に載せられる（前セッションの最重要「地味な仕事」）。
2. **本文案 A / B / C のどれか（または修正）。** 承認は最終文字列と、その SHA-256 に対して行う。実行は 9/5 中に電話から、ゲート経由。
3. **鍵の形式の確定。** 引き継ぎ書の `identity.pem` と、実際に d-bitflop を書いた seed hex の関係。Codex コードを取り込むまで `run-once` は再現できないので、所在 URL と併せて回答が要る。

## 5. 人間への依頼（コピペ不要、実行のみ）

1. Codex の Phase 1 コードの所在（repo URL または zip）を Issue に書く。
2. 到達可能な端末から次の 2 つを読み、結果を Issue に貼る（鍵不要）:
   `curl -sS "https://technocore.chat/r/d-bitflop?format=json"` と
   `curl -sS https://technocore.chat/kv/did-64/776f70dbeec8e2`
3. 司令塔の承認後、`technocore/READY-TO-RUN.md` §0 の手順で電話からゲート経由の write を 1 回。
