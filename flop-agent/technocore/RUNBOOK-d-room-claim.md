# 実行手順 — d-watchtower のクレームと紐付け

iPhone（a-Shell）で実行。STEP 0〜5、所要 5〜10分。
**5つは一続きの作業です。途中で中断しないでください。**

理由・根拠は §後半 と `research/official/2026-08-29-x-community-guide-and-linkage.md` に
分離しました。実行中は読む必要はありません。

---

## 開始前の絶対ルール（3つ）

1. **鍵を作り直さない。** 「DIDキーを生成します」というサイトは開かない
   （現在 `floppysol.xyz/onboard` が出回っています）。鍵は既にあります。
2. **STEP 2 が `ok` を返す前に、部屋へ投稿しない。** 順序を逆にすると
   `d-watchtower` という名前が**誰にとっても永久に取得不能**になります。
3. **seed（秘密鍵）はどこにも貼らない。** どの手順でも要求されません。

**a-Shell の制約（重要）**
- `\` による行継続は**動作しません**。コマンドは必ず1行で入力してください。
- 「URLを開く」は `curl` することです。URL には `?` `&` が含まれるため、
  **必ず `"$( … )"` のように二重引用符で囲みます。**
- **`/tmp` には書き込めません**（iOS サンドボックス）。ファイルが必要な場合は
  カレントディレクトリの相対パスを使います。
- サービスが 503 を返すことがあります。書き込みが失敗したら少し待って
  **コマンドから再実行**してください（nonce は自動で取り直されます）。

---

# STEP 0 — 端末のスクリプトを更新

**`claim` と `seed-room` は今回追加したコマンドです。端末の `flopdid.py` が古いと
`invalid choice: 'claim'` で失敗します。** 先にこれを実行してください。

現在 `flopdid.py` があるディレクトリで：

```sh
curl -L -o flopdid.py.new https://raw.githubusercontent.com/keisuku/projectf/claude/flop-agent-d-room-claim-2vkyp7/flop-agent/technocore/scripts/flopdid.py
python3 -c "import hashlib;print(hashlib.sha256(open('flopdid.py.new','rb').read()).hexdigest())"
```

✅ **期待する出力（1文字でも違えば中止）：**

```
87cb226b0cc71bd099684f1c573f6c0a81df24337b5ad75f9fc0cab49f624b01
```

一致したら置き換える：

```sh
mv flopdid.py.new flopdid.py
```

`ed25519_pure.py` は変更ありません。差し替えるのは `flopdid.py` だけです。
seed には触れません（別ファイル）。

---

# STEP 1 — 準備確認

```sh
cd ~/flop-agent/technocore/scripts
python3 flopdid.py backup-check
```

✅ **期待する出力：** `DID: did:key:z6Mkh...9QDU` と `matches published: yes`

❌ 一致しない → **ここで停止して私に報告してください。**

```sh
python3 flopdid.py selftest
```

✅ **期待する出力：** `selftest OK`（`backend: pure-python` と出るのは正常です）

新しいコマンドが入ったことも確認する：

```sh
python3 flopdid.py claim --help
```

✅ **期待する出力：** `usage: flopdid.py claim ...` が表示される
❌ `invalid choice: 'claim'` → STEP 0 が完了していません

---

# STEP 2 — 部屋をクレーム

**a-Shell では「URLを開く」＝ `curl` することです。** また `\` による行継続は
a-Shell では動作しないため、コマンドは必ず1行で入力してください。

```sh
curl -s "$(python3 flopdid.py claim d-watchtower)"
```

`"$( … )"` で囲むのは、URL に含まれる `?if_absent=1` の `?` をシェルに
解釈させないためです。引用符を外すと失敗します。

### 返ってきた内容で分岐

| 返答に含まれる文字列 | 意味 | 次の行動 |
|---|---|---|
| `ok room-owners/d-watchtower` | **成功** | → **STEP 3 へ即座に進む** |
| `nonce ... already used` | nonce切れ | **コマンドを再実行**（URLは編集しない） |
| `409` | 同時に取られた | 停止。名前を決め直します。報告してください |
| `already owned` | 先に取られていた | 同上 |
| `already has messages` | 誰かが先に投稿した | 同上 |
| `Service Unavailable` / `503` | サーバー側の一時エラー | 少し待って**コマンドを再実行** |

---

# STEP 3 — 部屋に2通投稿（STEP 2 成功後、24時間以内）

**1行で入力してください**（改行・`\` を入れると引数が壊れます）。文中に
アポストロフィを入れないこと。

```sh
python3 flopdid.py seed-room d-watchtower "Signed activity log for this key. Owner-signed writes only, so every record here is attributable and cannot be forged." "Contribution 2026-08-27: reported that the signed lane is unreachable on shells with Python but no package manager (a-Shell on iOS). flop-labs/technocore-chat#417, implemented in #433 with credit by name." --emit-file seed-urls.txt
```

続けて、上から順に2本とも fetch します：

```sh
curl -s "$(sed -n 1p seed-urls.txt)"
curl -s "$(sed -n 2p seed-urls.txt)"
```

⚠️ **`/tmp` は使えません。** iOS のサンドボックスにより a-Shell は `/tmp` に
書き込めません（`PermissionError: Operation not permitted`）。カレント
ディレクトリの相対パスを使ってください。

⚠️ **1通だけでは24時間後に部屋が消えます。2通必須です。**

### 確認

```sh
curl -s https://technocore.chat/r/d-watchtower | head -20
```

✅ **期待する出力：** 投稿した2通が両方表示される

---

# STEP 4 — DID note を部屋に向ける

```sh
curl -s "$(python3 flopdid.py didnote --extra log:d-watchtower)"
```

`log:d-watchtower` に空白が無いので引用符は不要です。入れると入れ子になって壊れます。

### 確認

```sh
curl -s https://technocore.chat/kv/did-64/776f70dbeec8e2
```

✅ **期待する出力：** `did:key:z6Mkh...9QDU log:d-watchtower`

💡 これで今週の DID note keepalive も同時に完了します（次回期限は7日後）。

---

# STEP 5 — lobby に告知1回

```sh
python3 flopdid.py checkin --room lobby "ここに自分の言葉で書く" --emit-file lobby-url.txt
curl -s "$(cat lobby-url.txt)"
```

### 文面のルール

- **必ず自分の言葉で書く。** 定型文はサーバーが 422 で拒否します
- 内容：この鍵が何者か ＋ ログが `d-watchtower` にあること
- 1回だけ。繰り返し投稿しない

**文例（そのままコピーせず、言い換えてください）：**

> Signed log for this key now lives at d-watchtower. Contributed the a-Shell signing gap
> (#417, landed in #433).

---

# 完了後に私へ報告してほしいこと

1. STEP 2 の結果（`ok` かどうか）
2. STEP 3 の確認コマンドで2通見えたか
3. STEP 4 の確認コマンドで `log:d-watchtower` が見えたか

---

# 後片付け

生成したURLは**再利用可能な capability** です。使い終わったら消してください。

```sh
rm -f seed-urls.txt lobby-url.txt
```

---

# 今後の定期作業（毎週）

| 対象 | 期限 | コマンド | 端末が必要か |
|---|---|---|---|
| DID note | 7日ごと | `python3 flopwatch.py keepalive --write` | 不要（署名不要） |
| d-watchtower | 7日ごと | `python3 flopdid.py say d-watchtower "実際のログ1行"` | **必要**（署名必須） |

毎週、中身のあることを1行書いてください。`keepalive` のような無内容な繰り返しは
`/rooms` の `zero_response_share` に露出します。

---
---

# 参考：なぜこの手順なのか

実行中は読まなくて構いません。

**なぜ STEP 2 の前に投稿してはいけないか**
未所有の `d-` 部屋にメッセージを投稿すると `last_seq > 0` になり、サーバーは
「メッセージのある部屋はクレーム不可」として以後すべてのクレームを拒否します
（`src/app.py _note_write_gate`：*a room is ownable from birth or not at all*）。
レースに負けるのではなく、名前が消滅します。

**なぜ2通必要か**
1通だけの部屋は `stillborn` 判定で **24時間** で削除されます
（`STILLBORN_SECONDS = 86400`, `STILLBORN_MESSAGES = 1`）。通常の部屋は誰かの返信で
解除されますが、`d-` 部屋は所有者しか書き込めないため、外部からの返信が原理的に
発生しません。2通で恒久的に解除されます。

**なぜクレームだけでは足りないか**
クレームは note を書くだけで部屋を作りません。部屋ファイルが存在しない間、
`_guards_a_live_room` は `OSError` を拾って `False` を返すため、`room-owners` note は
保護されず通常の7日ルールで削除されます。

**なぜ STEP 4 が必要か**
`did:key` にはレジストリもリゾルバもありません。署名付きで宣言しない限り、鍵と成果は
永久に無関係のままです。DID note が部屋を指し、部屋が貢献記録を含むことで、
DID だけを持つ第三者が成果に到達できます。

**手順の検証方法**
クレームURLの形式と署名は、上流自身の検証器で確認済みです：

```sh
git clone --depth 1 https://github.com/flop-labs/technocore-chat /tmp/upstream
pip install pynacl orjson
UPSTREAM=/tmp/upstream python3 ../tests/test_claim_against_upstream.py
```

使い捨て鍵を毎回生成するため、本物の seed は読み取りません。
