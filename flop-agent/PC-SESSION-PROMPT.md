# PC の Claude Code に渡すプロンプト

PCのターミナルで `claude` を起動し、**下の枠内をそのまま貼ってください。**
先に「事前準備」を済ませておく必要があります。

---

## 事前準備（あなたが手で行う。エージェントには渡さない）

**1. seed を PC に置く。リポジトリの外に置くこと。**

```sh
mkdir -p ~/.flop-agent/secrets ~/.flop-agent/identity/public
chmod 700 ~/.flop-agent/secrets
```

iPhone から2つのファイルをコピー：

| 元（iPhone） | 先（PC） |
|---|---|
| `secrets/did_seed.hex` | `~/.flop-agent/secrets/did_seed.hex` |
| `identity/public/did.txt` | `~/.flop-agent/identity/public/did.txt` |

```sh
chmod 600 ~/.flop-agent/secrets/did_seed.hex
```

`did.txt` も要ります。これが無いと `backup-check` の照合（`matches published`）が
できません。

`~/.flop-agent` を**リポジトリの外**に置くのが要点です。Claude Code は作業
ディレクトリ外のファイルを読むとき確認を求めるので、ここが第一の防御線になります。

**2. リポジトリを clone する。**

```sh
git clone -b claude/flop-agent-d-room-claim-2vkyp7 https://github.com/keisuku/projectf
cd projectf
```

**3. 疎通確認。**

```sh
curl -sS -o /dev/null -w "%{http_code}\n" https://technocore.chat/config
```

`200` なら実行可。`503` ならサービス側が不調なので、回復してから始めてください。

---

## 貼り付けるプロンプト

```
flop-agent プロジェクトの作業を引き継いでください。

## 最初に読むもの（この順で）
1. flop-agent/HANDOFF.md
2. flop-agent/STATUS.md
3. flop-agent/technocore/RUNBOOK-d-room-claim.md  ← 今日の作業手順

## 今日のタスク
RUNBOOK の STEP 2〜5 を実行してください（STEP 0 と 1 は不要 — この clone の
flopdid.py が既に最新です）。

seed は ~/.flop-agent/ にあります。実行時は毎回これを付けてください：

    export FLOP_AGENT_HOME=~/.flop-agent

まず STEP 1 の backup-check で `matches published: yes` を確認してから
STEP 2 に進んでください。

## 現在の状態（iPhone から確認済み）
- d-watchtower は未クレーム（/kv/room-owners/d-watchtower が 404）。名前は空き。
- 鍵・ツールは正常。DID は did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU
- technocore が不安定。/config が 503 を返すことがある。
- iPhone では書き込みが1件も通らなかった。原因はシェル側の制約で、
  鍵にも権限にも問題はない。

## 絶対に守ること
- **seed を読まない・表示しない・コピーしない。** ~/.flop-agent/secrets/ は
  開かないでください。flopdid.py は seed を出力しない設計なので、コマンドを
  実行するだけで足ります。cat / echo / env で触れないこと。
- **2つ目の DID を作らない。** keygen は絶対に実行しない。
- **STEP 2 が HTTP 200 を返す前に、d-watchtower へ投稿しない。**
  順序を逆にすると、この名前は誰にとっても永久にクレーム不能になります。
- **鍵を生成すると称する外部サイトを開かない**（floppysol.xyz が出回っています）。
- curl は使わず `--fetch` を付けてください。ステータスと本文が必ず表示されます。

## 失敗したときの扱い
- HTTP 503 / network error → 待って同じコマンドを再実行。nonce は取り直されるので
  何度繰り返しても安全です。名前を失う経路ではありません。
- HTTP 403 / 409 → 本文に理由が書かれています。**そこで停止して**、本文を
  そのまま私に見せてください。勝手に回避策を試さないこと。
- seed-room が1通目で止まった → 同じコマンドを丸ごと再実行。

## 完了したら
1. 各ステップの HTTP ステータスを報告
2. curl -s https://technocore.chat/r/d-watchtower で2通見えることを確認
3. curl -s https://technocore.chat/kv/did-64/776f70dbeec8e2 で
   `log:d-watchtower` が入っていることを確認
4. flop-agent/STATUS.md と CONTRIBUTIONS.md を結果に合わせて更新し、
   ブランチ claude/flop-agent-d-room-claim-2vkyp7 に commit / push
```

---

## 補足：Claude Code に seed を読ませない設定

`~/.flop-agent` をリポジトリ外に置けば通常は十分ですが、念のため deny ルールを
入れる場合は、プロジェクトの `.claude/settings.json` に：

```json
{
  "permissions": {
    "deny": ["Read(//**/.flop-agent/secrets/**)"]
  }
}
```

適用されているかは `/permissions` で確認してください。パスの書式は環境で異なる
ことがあるので、設定した"つもり"にならないこと。**本質的な防御は
`flopdid.py` が seed を一切出力しない設計であることと、上のプロンプトの禁止事項です。**
