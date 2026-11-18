---
name: bg-herdr-subagent
description: |
  指定した Herdr のセッションに herdr-workspace スキルの手順でワークスペースを用意し、その中でコーディングエージェント（claude / codex 等）を起動してサブエージェントとして使う。呼び出し元のワークスペースとは別の場所（別のセッションでもよい）で動くので、手元の画面を散らかさずに裏で作業を任せられる。タスクを渡し、完了を待ち、結果を回収して報告するまでを herdr CLI だけで行う。セッション名・ワークスペース名が指定されていなければ聞き返す。
  「別のワークスペースでエージェントに任せて」「裏でサブエージェントを立てて」「my-ai-skills セッションにエージェントを立てて調査させて」「bg-herdr-subagent」などと言われたときに使う。
  Herdr 内で動いているとき（HERDR_ENV=1）専用。今のワークスペースに別タブで立てたいなら herdr-subagent、ワークスペースを作るだけなら herdr-workspace を使う。
---

# Herdr バックグラウンドサブエージェントスキル（bg-herdr-subagent）

[herdr-subagent](../herdr-subagent/SKILL.md) と同じようにサブエージェントへタスクを委譲しますが、**エージェントを立てる場所が呼び出し元のワークスペースではなく、[herdr-workspace](../herdr-workspace/SKILL.md) の手順で用意したワークスペース**です。ワークスペースは指定した Herdr セッション（`herdr --session <名前>`）の中に作るので、別のセッションに置けば手元のサイドバーにも出ません。

1 タブ = 1 エージェントは herdr-subagent と同じです。すべて `herdr --session "$SESSION" ...` の形で対象のセッションを明示して操作し、ユーザーのフォーカスは動かしません。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:bg-herdr-subagent <タスクの説明> [--session <セッション名>] [--workspace <ワークスペース名>] [--name <名前>] [--kind <claude|codex|...>] [--cwd <パス>] [--no-wait] [--close]

# OpenAI Codex CLI
$ybaba:bg-herdr-subagent <タスクの説明> [...]    # marketplace 経由のプラグイン
$bg-herdr-subagent <タスクの説明> [...]          # ~/.agents/skills/ fallback 導入時
```

| オプション | 既定値 | 意味 |
| --- | --- | --- |
| `--session` | **無し（聞き返す）** | エージェントを立てる Herdr のセッション。止まっていれば起動し、存在しなければ確認のうえ作る |
| `--workspace` | **無し（聞き返す）** | エージェントを立てるワークスペースの名前。そのセッションに無ければ新しく作り、あれば確認のうえそこに新しいタブを作る |
| `--name` | タスク内容から生成 | エージェント名兼タブ名。`[a-z][a-z0-9_-]{0,31}` |
| `--kind` | 自分と同じ種類 | 起動するエージェント種別。Claude Code から呼ばれたら `claude`、Codex から呼ばれたら `codex` |
| `--cwd` | 呼び出し元の `$PWD` | エージェントの作業ディレクトリ |
| `--no-wait` | 付けない | タスクを送ったら完了を待たずに戻る。結果は後で回収する |
| `--close` | 付けない | 結果回収後に、このスキルが作ったタブ（ワークスペースを作った場合はワークスペース）を閉じる |

自然文で頼まれた場合も同じ項目に読み替える（例:「revu セッションの pbi-900 ワークスペースで codex にこの差分をレビューさせて」→ `--session revu --workspace pbi-900 --kind codex`）。

複数のタスクを渡された場合は、同じワークスペースの中にタスクごとのタブとエージェントを 1 つずつ作って並列に走らせる。

## 全体の流れ

1. 前提を確認し、セッション名・ワークスペース名を確定する（herdr-workspace ステップ1〜2）
2. セッションを使える状態にする（herdr-workspace ステップ3）
3. ワークスペースとエージェント用のペインを用意する
4. そのペインでエージェントを起動する
5. タスクを送信し、完了を待つ
6. 結果を読み取り、必要なら追加のやり取りをする
7. ユーザーに報告し、タブ／ワークスペースを残すか閉じるかを扱う

---

## ステップ1: 前提を確認し、名前を確定する

[herdr-workspace](../herdr-workspace/SKILL.md) の**ステップ1・2をそのまま行う**。要点：

- `HERDR_ENV` が `1` でなければ中断する
- `herdr session list --json` でセッションの一覧と、今いるセッション（`socket_path` が `$HERDR_SOCKET_PATH` と一致するもの）を把握する
- **セッション名・ワークスペース名が指定されていなければ、作業を始める前に必ず聞き返す。** 足りない方だけを聞き、推測で決めない。Claude Code では `AskUserQuestion` で 1 回にまとめて聞く
- タスクの説明そのものが無い場合も一緒に聞く

あわせてエージェント側の前提を確認する：

```bash
herdr agent start --help | grep -q -- '--kind' && echo "agent start: --kind/--pane 形式"
```

- `--kind` が無ければ herdr 0.7 系。このスキルは 0.8 系以降の `--kind` / `--pane` 形式を前提にしているので、`herdr update` を案内して中断する（アップデートはサーバー再起動を伴うので勝手に実行しない）
- 起動する `--kind` が `possible values` に含まれることを確認する

---

## ステップ2: セッションを使える状態にする

[herdr-workspace](../herdr-workspace/SKILL.md) の**ステップ3をそのまま行う**。要点：

- 動作中ならそのまま進む
- 停止中なら、ヘッドレスのサーバーとして起動する。**`env -i` で環境変数を最小限にしてから起動する**（そうしないと呼び出し元エージェントの `CLAUDECODE`・`CLAUDE_CODE_*` などが新しいセッションのペインに引き継がれ、そこで起動するサブエージェントが自分を子セッションと誤認する）
- 存在しなければ、似た名前のセッションを見せたうえで新しく作るか確認する
- サーバーを起動したかどうか（`STARTED_SERVER=1`）を覚えておく。ステップ7で使う

```bash
SESSION='my-ai-skills'
```

以降のコマンドには**すべて `--session "$SESSION"` を付ける。** 付け忘れると今いるセッションが操作される。

---

## ステップ3: ワークスペースとエージェント用のペインを用意する

### エージェント名を決める

- `--name` があればそれを使う。無ければタスク内容から英小文字ケバブケースで短く作る（例: `review-diff`、`spike-auth`）
- 形式は `[a-z][a-z0-9_-]{0,31}`。**そのセッションの生きているエージェントの中で一意**にする。衝突したら末尾に `-2` などを付ける

```bash
herdr --session "$SESSION" agent list | jq -r '.result.agents[].name // empty'
```

### 同名のワークスペースがあるか調べる

```bash
LABEL='pbi-900'
herdr --session "$SESSION" workspace list | jq -r --arg n "$LABEL" '.result.workspaces[] | select(.label == $n) | "\(.workspace_id)\t#\(.number)\t\(.label)\t\(.tab_count) tabs"'
```

### A. 無い → ワークスペースを新しく作り、ルートペインを使う

[herdr-workspace](../herdr-workspace/SKILL.md) のステップ4の手順で作る。`--agent` は付けず、エージェントはこのスキルのステップ4で起動する。

```bash
OUT=$(herdr --session "$SESSION" workspace create --label "$LABEL" --cwd "$CWD" --no-focus 2>&1)
WS=$(echo "$OUT"   | jq -r '.result.workspace.workspace_id')
TAB=$(echo "$OUT"  | jq -r '.result.tab.tab_id')
PANE=$(echo "$OUT" | jq -r '.result.root_pane.pane_id')
herdr --session "$SESSION" tab rename "$TAB" "$NAME"
CREATED=workspace
```

`tab rename` が無いバージョンなら省略してよい（タブ名が番号のままになるだけ）。

### B. ある → ユーザーに確認し、そのワークスペースに新しいタブを作る

「既存の `<LABEL>`（`<WS>`、タブ `<n>` 個）に新しいタブでエージェントを立てる／別名で新しいワークスペースを作る」のどちらにするか確認する。既存を使う場合：

```bash
WS='<確認した workspace_id>'
OUT=$(herdr --session "$SESSION" tab create --workspace "$WS" --cwd "$CWD" --label "$NAME" --no-focus 2>&1)
TAB=$(echo "$OUT"  | jq -r '.result.tab.tab_id')
PANE=$(echo "$OUT" | jq -r '.result.root_pane.pane_id')
CREATED=tab
```

### 共通

- `CWD` は `--cwd` 指定があればそのパス（`test -d` で確認）、無ければ `$PWD`
- **ID は必ず JSON の応答から取る。** ワークスペース・タブ・ペインの ID はセッションごとに振られるので、今いるセッションの ID（`$HERDR_WORKSPACE_ID` など）と混同しない
- 作ったタブのルートペインをそのままエージェントに使う。`pane split` はしない（1 タブ 1 エージェント）
- 複数タスクのときは、1 つ目を A または B で用意し、2 つ目以降は同じ `$WS` に B の `tab create` でタブを足す

---

## ステップ4: ペインでエージェントを起動する

```bash
herdr --session "$SESSION" agent start "$NAME" --kind claude --pane "$PANE"
```

- 成功応答はエージェントが対話入力可能になった後に返る（既定タイムアウト 30 秒）。`.result.agent.interactive_ready` が `true` であることを確認する
- エージェント固有の引数は `--` の後ろに渡す。**ユーザーが明示した場合のみ**（例: `-- --model sonnet`、`-- --permission-mode acceptEdits`）

| 応答 | 対応 |
| --- | --- |
| `agent_not_ready` | 承認ダイアログ等で止まっている。`herdr --session "$SESSION" agent read "$NAME" --source visible` で画面を読み、内容をユーザーに見せて指示を仰ぐ。**ダイアログに勝手に答えない** |
| `agent_pane_busy` | 作ったばかりのペインなら通常起きない。`herdr --session "$SESSION" pane read "$PANE"` で確認し、タブを作り直す |
| 名前の衝突 | ステップ3に戻って別名にする |
| タイムアウト | `agent get` と `agent read` で状態を確認し、ログイン待ち等ならユーザーに伝える |

失敗したら、このスキルが作ったもの（`CREATED=workspace` なら `herdr --session "$SESSION" workspace close "$WS"`、`tab` なら `tab close "$TAB"`）を閉じてから報告する。

---

## ステップ5: タスクを送信し、完了を待つ

### プロンプトを組み立てる

サブエージェントは**呼び出し元の会話を一切知らない**。herdr-subagent と同じく、以下を含めて自己完結したプロンプトにする：

- 何をしてほしいか（タスク本文）
- 前提となる文脈（作業ディレクトリ、対象ブランチ、関係するファイル、制約）
- 出力の形式（「最後に結論を箇条書きで」「変更したファイル一覧を最後に」など）
- してはいけないこと（例: コミットしない、ファイルを変更しない）

### 送信して待つ

```bash
PROMPT=$(cat <<'EOF'
<組み立てたプロンプト>
EOF
)
herdr --session "$SESSION" agent prompt "$NAME" "$PROMPT" --wait --timeout 600000
```

- タイムアウトの目安: 調査・レビュー 5〜10 分、実装 15〜30 分
- 誰も見ていないセッションで終わったエージェントは `idle` ではなく `done` になる（`done` = まだ画面で見られていない完了）。どちらも完了として扱う

| 状態 / エラー | 対応 |
| --- | --- |
| `done` / `idle` | 完了。ステップ6へ |
| `blocked` / `agent_blocked` | `agent read --source visible` で画面を読み、**内容をユーザーに提示して判断を仰ぐ**。指示に従って `agent send-keys` や `agent prompt` で応答する。削除・push・外部送信の承認を自分で判断しない |
| `agent_prompt_stalled` | `agent get` と `agent read` で確認。入力欄にテキストが残っていれば `send-keys enter`、既に working なら `agent wait "$NAME" --timeout ...` で待ち直す |
| `timeout` | 画面を読んで進捗を報告し、待ち続けるか中断するかユーザーに確認する。中断は `send-keys esc` → 必要なら `ctrl+c` |

### `--no-wait` のとき

`--wait` を付けずに送信し、受け付けられたこと（`agent get` で `working`）だけ確認してステップ7の報告に進む。報告には結果の回収方法（`herdr --session <SESSION> agent wait <NAME>` → `agent read`）を書く。

Claude Code では、`herdr --session "$SESSION" agent wait "$NAME" --timeout ...` を Bash の `run_in_background` で走らせておけば、完了したときに通知を受けてステップ6に進める。ユーザーとは別の話を続けられる。

### 並列実行（複数タスク）

全員を起動してから `--wait` なしで送信し、その後 1 つずつ待つ。

```bash
herdr --session "$SESSION" agent prompt "$NAME1" "$PROMPT1"
herdr --session "$SESSION" agent prompt "$NAME2" "$PROMPT2"
herdr --session "$SESSION" agent wait "$NAME1" --timeout 600000
herdr --session "$SESSION" agent wait "$NAME2" --timeout 600000
```

同じファイルを同時に編集するタスクを並列にしない。編集を伴うタスクが複数あるなら、worktree を分けるか（create-worktree スキル）、直列にする。

---

## ステップ6: 結果を読み取る

```bash
herdr --session "$SESSION" agent read "$NAME" --source recent-unwrapped --lines 200
```

- 出力はプレーンテキスト。最後に送ったプロンプトのエコー以降が今回の応答
- 長い応答で先頭が読めない場合だけ、フォールバックとして結果をファイルに書かせる。書き出し先はセッションの scratchpad ディレクトリ（system prompt に案内があるもの）にし、プロジェクト内には作らない

```bash
herdr --session "$SESSION" agent prompt "$NAME" "直前の回答の全文を Markdown で <scratchpad ディレクトリ>/$NAME.md に書き出し、そのパスだけを返答してください。" --wait --timeout 120000
```

結果が不十分なら、同じエージェントに続きを頼める（会話の文脈はサブエージェント側に残っている）。

```bash
herdr --session "$SESSION" agent prompt "$NAME" "<追加の指示>" --wait --timeout 600000
```

---

## ステップ7: 報告と後片付け

結果を**自分の言葉で要約して**報告する。サブエージェントの画面をそのまま貼らない。

```
✅ サブエージェント <NAME> の結果

  <要約された結論・成果物>

  場所        セッション <SESSION> / ワークスペース「<LABEL>」(<WS>) / タブ <TAB>
  エージェント  <kind> / <PANE> / 状態 done
  眺める      herdr session attach <SESSION>   ← 別のターミナルから実行
  追加指示    herdr --session <SESSION> agent prompt <NAME> "<テキスト>" --wait
  閉じる      herdr --session <SESSION> workspace close <WS>   （既存ワークスペースに足した場合は tab close <TAB>）
```

- 今いるセッションに作った場合は「眺める」の行を「サイドバーから切り替えられます」に置き換える
- サーバーを起動した場合（`STARTED_SERVER=1`）はそのことと、止める方法（`herdr session stop <SESSION>`）を添える
- サブエージェントがファイルを変更した場合は、変更したファイルの一覧（`git status --short`）を報告に含める
- **既定では何も閉じない。** ユーザーが様子を眺めたり続きを頼めるように残す
- `--close` が指定された場合、またはユーザーが「閉じて」と言った場合のみ、このスキルが作ったものを閉じる
  - `CREATED=workspace` → `herdr --session "$SESSION" workspace close "$WS"`
  - `CREATED=tab` → `herdr --session "$SESSION" tab close "$TAB"`（既存のワークスペースは閉じない）
  - `STARTED_SERVER=1` で、閉じた結果そのセッションのワークスペースが 0 個になったら `herdr session stop "$SESSION"` でサーバーも止める。それ以外のときはサーバーを止めない

---

## 注意点

- **名前を推測しない**: セッション名・ワークスペース名とも、指定が無ければ必ず聞き返す
- **`--session` を付け忘れない**: 付けないと今いるセッションが操作対象になり、ID も別のものを指す
- **サーバーはきれいな環境で起動する**: 停止中のセッションを起動するときは `env -i` を使う（herdr-workspace のステップ3）
- **TUI を起動しない**: bare の `herdr` や `herdr session attach` はエージェントのペインで実行しない
- **1 タブ 1 エージェント**: タブ内で `pane split` しない。もう 1 つ必要なら同じワークスペースに別のタブを作る
- **フォーカスを奪わない**: `--no-focus` を付ける
- **ダイアログに勝手に答えない**: `blocked` になったら画面を読んでユーザーに提示する
- **自分が作ったものだけ閉じる**: 既存のワークスペース・タブ・ペイン・セッションに触らない。`herdr server stop` を実行しない
- **エラーは stderr に JSON**（exit 1）、構文エラーは exit 2。`2>&1` で拾って内容を報告する
- **`unknown` は完了の証拠ではない**: `agent read` で確認する
