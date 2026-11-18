---
name: herdr-workspace
description: |
  指定した Herdr のセッション（`herdr --session <名前>` で使う名前付きの永続セッション）の中に、新しいワークスペースを 1 つ作る。セッション名とワークスペース名は、指定されていなければ作成前に必ず聞き返す（勝手に決めない）。止まっているセッションはヘッドレスで起動し、存在しないセッションは確認のうえ新しく作る。作業ディレクトリの指定とルートペインでのエージェント起動にも対応する。
  「herdr で新しいワークスペースを作って」「my-ai-skills のセッションにワークスペースを追加して」「revu セッションに pbi-900 のワークスペースを切って」「herdr-workspace」などと言われたときに使う。
  Herdr 内で動いているとき（HERDR_ENV=1）専用。同じワークスペース内に別タブでエージェントを立てたいだけなら herdr-subagent、git worktree ごと作業環境を用意したいなら create-worktree を使う。
---

# Herdr ワークスペース作成スキル（herdr-workspace）

**ユーザーが指定した Herdr のセッションの中に、新しいワークスペースを 1 つ作ります。**

Herdr のセッションは `herdr --session <名前>` で使う名前付きの永続セッションで、セッションごとに別のサーバーが動き、それぞれが自分のワークスペース一覧を持っています（`herdr session list` で一覧できる `default`・`my-ai-skills`・`revu` など）。どのセッションに作るか、ワークスペースに何という名前を付けるかはユーザーが決めることなので、**セッション名・ワークスペース名が指定されていなければ推測せずに聞き返します**。

すべて `herdr` CLI で行います。別のセッションは `herdr --session <名前> <サブコマンド>` で操作できます。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:herdr-workspace [<セッション名>] [<ワークスペース名>] [--cwd <パス>] [--focus] [--agent <claude|codex|...>]

# OpenAI Codex CLI
$ybaba:herdr-workspace [<セッション名>] [<ワークスペース名>] [...]    # marketplace 経由のプラグイン
$herdr-workspace [<セッション名>] [<ワークスペース名>] [...]        # ~/.agents/skills/ fallback 導入時
```

| 引数 / オプション | 既定値 | 意味 |
| --- | --- | --- |
| `<セッション名>` | **無し（聞き返す）** | ワークスペースを作る Herdr のセッション。使える文字は ASCII の英数字と `.` `_` `-` だけ |
| `<ワークスペース名>` | **無し（聞き返す）** | ワークスペースのラベル（サイドバーに出る名前）。例: `pbi-900`、`[spike] auth`。空白や記号を含んでよい。`--label <名前>` の形で渡されてもよい |
| `--cwd` | 呼び出し元の `$PWD` | ワークスペースのルートペインの作業ディレクトリ |
| `--focus` | 付けない | そのセッションの中で新しいワークスペースにフォーカスを移す |
| `--agent` | 付けない | 作成後、ルートペインでそのエージェントを起動する。付けなければシェルのままにする |

自然文で頼まれた場合も同じ項目に読み替える（例:「revu セッションに pbi-900 っていうワークスペースを作って」→ セッション名 `revu`、ワークスペース名 `pbi-900`）。どちらか片方だけ言われた場合は、足りない方だけを聞き返す。

## 全体の流れ

1. 前提を確認する（Herdr 内で動いているか、セッションの一覧）
2. セッション名とワークスペース名を確定する（指定が無ければ聞き返す）
3. セッションの状態に応じて準備する（動いている／止まっている／存在しない）
4. ワークスペースを作る
5. （`--agent` 指定時のみ）ルートペインでエージェントを起動する
6. ユーザーに報告する

---

## ステップ1: 前提を確認する

```bash
test "${HERDR_ENV:-}" = 1 && echo "in herdr: socket=$HERDR_SOCKET_PATH workspace=$HERDR_WORKSPACE_ID"
herdr --version
herdr session list --json | jq -r '.sessions[] | "\(.name)\t\(if .running then "running" else "stopped" end)\t\(.socket_path)"'
```

- `HERDR_ENV` が `1` でなければ **Herdr の外で動いている**。「Herdr のペイン内から実行してください」と伝えて中断する
- 自分が今いるセッションは、`socket_path` が `$HERDR_SOCKET_PATH` と一致するもの。報告やフォーカスの判断に使う
- **`herdr workspace create` を引数なしで試し打ちしない**（既定値でそのまま作成されてしまう）。オプションは `--help` で確認する
- **bare の `herdr` や `herdr session attach` を実行しない**。どちらも TUI を起動するので、エージェントのペインが乗っ取られる

---

## ステップ2: セッション名とワークスペース名を確定する

ユーザーの発話または引数にセッション名・ワークスペース名が含まれていれば、それを使う。

**どちらかが指定されていない場合は、ワークスペースを作る前に必ず聞き返す。** 足りない方だけを聞く。作業ディレクトリ名・ブランチ名・今いるセッションなどから推測して作ってはいけない。「今のセッションに作る」「ディレクトリ名をそのまま名前にする」と決めてよいのも、ユーザーがそう答えたときだけ。

- **Claude Code では必ず `AskUserQuestion` の選択式で聞く。** 文章だけの質問で済ませない。両方足りなければ 1 回の呼び出しに 2 問まとめて聞く
  - セッション名: ステップ1の一覧から、今いるセッションと動いているセッションを中心に 2〜3 個を選択肢にする（例: `my-ai-skills（動作中）`）。選択肢は 1 問 4 個までなので全部は並べない。一覧に無い停止中のセッションや新しい名前は自由入力（Other）で指定できることを、質問文に書き添える
  - ワークスペース名: 現在のブランチ名や作業ディレクトリ名など、手がかりになる候補を 2〜3 個選択肢にする。自由入力（Other）で好きな名前を付けられる
  - 選択肢に「おまかせ」のような名前を決めない項目は入れない
- `AskUserQuestion` が無い環境（Codex など）でだけ、次のように文章で質問し、**ユーザーの返答を待ってこのターンを終える**（足りない方の項目だけ載せる）

```
ワークスペースを作る前に教えてください。

1. どの Herdr セッションに作りますか？
     動作中: default（今ここ）, my-ai-skills, shisha-news-app
     停止中: revu, docs, exq, ...
   新しいセッション名を指定することもできます。

2. ワークスペースの名前は何にしますか？（例: pbi-900 / [spike] auth）
```

- 名前が決まらない返答（「おまかせ」など）なら、候補を出してもう一度確認する。決まるまで作成しない
- 前後の空白は取り除く。それ以外の加工（小文字化など）はしない
- セッション名に使える文字は ASCII の英数字と `.` `_` `-` だけ。それ以外を含む場合は、その旨を伝えて聞き直す
- ワークスペース名は空白や記号を含んでよい。空文字だけは不可

---

## ステップ3: セッションの状態に応じて準備する

```bash
SESSION='my-ai-skills'
herdr session list --json | jq -r --arg s "$SESSION" '.sessions[] | select(.name == $s) | if .running then "running" else "stopped" end'
```

### 動いている（`running`）

そのままステップ4へ。

### 止まっている（`stopped`）

ヘッドレスのサーバーとして起動する。前回保存されたワークスペースはそのまま復元される。

```bash
(cd ~ && setsid nohup env -i HOME="$HOME" USER="$USER" LOGNAME="${LOGNAME:-$USER}" \
  PATH="$PATH" SHELL="$SHELL" LANG="${LANG:-C.UTF-8}" TERM=xterm-256color \
  herdr --session "$SESSION" server >/dev/null 2>&1 &)
for i in $(seq 1 20); do
  herdr --session "$SESSION" workspace list 2>/dev/null | grep -q '"result"' && break
  sleep 0.5
done
herdr --session "$SESSION" workspace list | jq -c '.result.workspaces[] | {workspace_id, label}'
```

- `setsid nohup ... &` でエージェントのプロセスから切り離す。切り離さないと、エージェントのシェルが終わったときにサーバーごと止まる
- `env -i` で環境変数を最小限にしてから起動する。そのまま起動すると、呼び出し元のエージェントの環境変数（`CLAUDECODE`・`CLAUDE_CODE_*`・今いるセッションの `HERDR_*` など）がサーバー経由で新しいセッションの全ペインに引き継がれ、そこで起動したエージェントが自分を子セッションと誤認する（Claude Code なら会話の記録が保存されなくなる）。`HERDR_*` はペインごとに Herdr が正しく設定し直す
- 10 秒待っても `workspace list` が成功しなければ、`<session_dir>/herdr-server.log` の末尾を読んでユーザーに伝え、中断する
- 起動したことは報告に必ず含める（ユーザーが知らないうちにサーバーが増えないようにする）

### 存在しない（一覧に無い）

**新しいセッションを作る前にユーザーに確認する。** タイプミスの可能性があるので、一覧の中に似た名前（例: `my-ali-skills` と `my-ai-skills`）があれば並べて見せる。

```
セッション「<SESSION>」はまだありません。新しく作りますか？
（似た名前の既存セッション: my-ai-skills）
```

作ると答えられたら、「止まっている」と同じ手順でサーバーを起動する。新しいセッションはワークスペースが 0 個の状態で起動する。

---

## ステップ4: ワークスペースを作る

同じ名前のワークスペースが既にそのセッションにある場合は、それを見せて「別名にする／同名でもう 1 つ作る」のどちらにするか確認する。

```bash
LABEL='pbi-900'   # ステップ2で確定したワークスペース名
herdr --session "$SESSION" workspace list | jq -r --arg n "$LABEL" '.result.workspaces[] | select(.label == $n) | "\(.workspace_id)\t#\(.number)\t\(.label)"'
```

作成する：

```bash
CWD="$PWD"   # --cwd 指定があればそのパス
OUT=$(herdr --session "$SESSION" workspace create --label "$LABEL" --cwd "$CWD" --no-focus 2>&1)
echo "$OUT"
WS=$(echo "$OUT"   | jq -r '.result.workspace.workspace_id')
TAB=$(echo "$OUT"  | jq -r '.result.tab.tab_id')
PANE=$(echo "$OUT" | jq -r '.result.root_pane.pane_id')
NUM=$(echo "$OUT"  | jq -r '.result.workspace.number')
echo "session=$SESSION workspace=$WS tab=$TAB pane=$PANE"
```

- `--label` は必ず渡す。省略すると Herdr が作業ディレクトリ名を付けてしまい、ユーザーが決めた名前にならない
- `--focus` 指定時だけ `--no-focus` を `--focus` に置き換える。今いるセッションに作る場合、フォーカスを移すとユーザーの画面が切り替わるので、特に明示が無い限り移さない
- `--cwd` が指定されたら `test -d` で存在を確認してから渡す。存在しなければユーザーに伝えて止まる
- **ID は必ず JSON の応答から取る。** ワークスペース ID（`w1` など）はセッションごとに振られるので、別のセッションの ID と混同しない。以降の操作も必ず `herdr --session "$SESSION"` を付けて行う
- 失敗した場合（stderr に JSON、exit 1）はその内容をそのまま伝える

---

## ステップ5: エージェントを起動する（`--agent` 指定時のみ）

```bash
herdr --session "$SESSION" agent start "<agent-name>" --kind claude --pane "$PANE"
```

- エージェント名は `[a-z][a-z0-9_-]{0,31}` で、そのセッションの生きているエージェントの中で一意にする（`herdr --session "$SESSION" agent list | jq -r '.result.agents[].name // empty'`）。ワークスペース名から作る（例: `pbi-900` → `pbi-900`、`[spike] auth` → `spike-auth`）。衝突したら末尾に `-2` などを付ける
- `--kind` は `herdr agent start --help` の `possible values` に含まれるものだけ使う
- エージェント固有の引数（`-- --model sonnet` など）はユーザーが明示した場合のみ付ける
- `agent_not_ready`（承認ダイアログ等で停止）になったら `herdr --session "$SESSION" agent read "<agent-name>" --source visible` で画面を読み、内容をユーザーに見せて判断を仰ぐ。**ダイアログに勝手に答えない**
- 起動に失敗してもワークスペースは閉じない。失敗した事実を報告に含める

---

## ステップ6: 報告する

```
✅ Herdr セッション <SESSION> にワークスペースを作成しました

  セッション      <SESSION>（もともと動作中 / 停止中だったのでヘッドレスで起動 / 新規作成）
  ワークスペース  <WS>「<label>」（サイドバー #<NUM>）
  作業ディレクトリ  <CWD>
  ルートペイン    <PANE>（シェル / <kind> エージェント <agent-name>）
  開く            herdr session attach <SESSION>   ← 別のターミナルから実行
  閉じる          herdr --session <SESSION> workspace close <WS>
```

- 今いるセッションに作った場合は「開く」の行を「サイドバーから切り替えられます」に置き換える
- サーバーを起動した場合は、止める方法（`herdr session stop <SESSION>`）も添える。止めてもワークスペースは保存され、次の起動で復元される

---

## 注意点

- **名前を推測しない**: セッション名・ワークスペース名とも、指定が無ければ必ず聞き返し、返答を得てから作成する。今いるセッションやディレクトリ名を勝手に既定にしない
- **新しいセッションは確認してから作る**: 一覧に無い名前はタイプミスかもしれない
- **TUI を起動しない**: bare の `herdr` や `herdr session attach` はエージェントのペインで実行しない。止まっているセッションは `herdr --session <名前> server` をヘッドレスで起動する
- **`--session` を付け忘れない**: 付けないと今いるセッションが操作対象になる
- **既存のものに触らない**: 既存のワークスペース・タブ・ペイン・セッションを閉じたり改名したり止めたりしない。`herdr server stop` を実行しない
- **Herdr の外から操作しない**: `HERDR_ENV=1` の確認を省略しない
- **エラーは stderr に JSON**（exit 1）、構文エラーは exit 2。`2>&1` で拾って内容を報告する
