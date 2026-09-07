---
name: herdr-subagent
description: |
  Herdr の同じワークスペース内に新しいタブを開き、そこでコーディングエージェント（claude / codex 等）を起動してサブエージェントとして使う。タスクを渡し、完了を待ち、結果を回収して報告するまでを herdr CLI だけで行う。サブエージェントは実ターミナルで動くので、ユーザーはタブを切り替えて作業の様子を眺められる。
  「herdr でサブエージェントを立てて」「別タブでエージェントに任せて」「herdr-subagent」「タブを開いて claude に〜させて」「並列で調査させて」などと言われたときに使う。
  Herdr 内で動いているとき（HERDR_ENV=1）専用。Claude Code 組み込みの Agent ツールの代わりに、目に見えるタブで動く別プロセスのエージェントが欲しい場面を想定。
---

# Herdr サブエージェントスキル（herdr-subagent）

Herdr の**現在のワークスペース（space）に新しいタブを 1 つ作り、そのタブに 1 つのエージェントを起動**して、サブエージェントとしてタスクを委譲します。1 タブ = 1 エージェントを守ることで、サイドバー上でどのタブがどの作業をしているか一目で分かる状態を保ちます。

すべて `herdr` CLI の socket API 経由で行い、ユーザーのフォーカスは呼び出し元のペインから動かしません。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:herdr-subagent <タスクの説明> [--name <名前>] [--kind <claude|codex|...>] [--close]

# OpenAI Codex CLI
$ybaba:herdr-subagent <タスクの説明> [...]    # marketplace 経由のプラグイン
$herdr-subagent <タスクの説明> [...]          # ~/.agents/skills/ fallback 導入時
```

| オプション | 既定値 | 意味 |
| --- | --- | --- |
| `--name` | タスク内容から生成 | エージェント名兼タブ名。`[a-z][a-z0-9_-]{0,31}` |
| `--kind` | 自分と同じ種類 | 起動するエージェント種別。Claude Code から呼ばれたら `claude`、Codex から呼ばれたら `codex` |
| `--close` | 付けない | 結果回収後にタブを閉じる。付けなければタブを残し、ユーザーが眺めたり追加の指示を出せる状態にする |

複数のタスクを渡された場合（箇条書き等）は、タスクごとにタブとエージェントを 1 つずつ作って並列に走らせる。

## 全体の流れ

1. 前提を確認する（Herdr 内で動いているか、CLI のバージョン）
2. 同じワークスペースに新しいタブを作る
3. そのタブのルートペインでエージェントを起動する
4. タスクを送信し、完了を待つ
5. 結果を読み取り、必要なら追加のやり取りをする
6. ユーザーに報告し、タブを残すか閉じるかを扱う

---

## ステップ1: 前提を確認する

```bash
test "${HERDR_ENV:-}" = 1 && echo "in herdr: workspace=$HERDR_WORKSPACE_ID tab=$HERDR_TAB_ID pane=$HERDR_PANE_ID"
herdr --version
herdr agent start --help | grep -q -- '--kind' && echo "agent start: --kind/--pane 形式"
```

- `HERDR_ENV` が `1` でなければ **Herdr の外で動いている**。「Herdr のペイン内から実行してください」と伝えて中断する。外から Herdr のセッションを操作しない
- `agent start` に `--kind` が無い場合は herdr 0.7 系。**「後方互換（0.7 系）」**の手順に切り替えるか、`herdr update` を案内する（アップデートはサーバー再起動を伴うので勝手に実行しない）
- 起動する `--kind` が `herdr agent start --help` の `possible values` に含まれることを確認する

### サブエージェント名を決める

- `--name` があればそれを使う。無ければタスク内容から英小文字ケバブケースで短く作る（例: `review-diff`、`find-callers`、`spike-auth`）
- 形式は `[a-z][a-z0-9_-]{0,31}`。**生きているエージェントの中で一意**でなければならない

```bash
herdr agent list | jq -r '.result.agents[].name // empty'
```

衝突したら末尾に `-2` などを付ける。タブのラベルにも同じ名前を使う。

---

## ステップ2: 同じワークスペースに新しいタブを作る

**必ず `--workspace "$HERDR_WORKSPACE_ID"` を指定する。** 省略すると UI でフォーカスされているワークスペースに作られ、それが呼び出し元と別の space である可能性がある。

```bash
NAME=review-diff
OUT=$(herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd "$PWD" --label "$NAME" --no-focus)
TAB=$(echo "$OUT"  | jq -r '.result.tab.tab_id')
PANE=$(echo "$OUT" | jq -r '.result.root_pane.pane_id')
echo "tab=$TAB pane=$PANE"
```

- `--cwd "$PWD"` で呼び出し元と同じディレクトリにする。worktree 等で別のディレクトリを使いたいとユーザーが言った場合のみ変える
- `--no-focus` でユーザーのフォーカスを動かさない。ユーザーが「そっちに切り替えて」と言った場合のみ `--focus`
- **ID は必ず JSON の応答から取る。** サイドバーの並びや過去の例から推測しない
- `tab create` のルートペインはシェルが 1 つあるだけの状態。これをそのままエージェントに使うので、**タブ内にペインは 1 つしか存在しない**（ここで `pane split` や `agent start --split` は使わない）

---

## ステップ3: ルートペインでエージェントを起動する

```bash
herdr agent start "$NAME" --kind claude --pane "$PANE"
```

- 成功応答は、Herdr がそのペイン内でエージェントを検出し **対話入力可能になった後**にしか返らない（既定タイムアウト 30 秒）。起動直後の idle 待ちは不要
- 応答の `.result.agent.agent_status` が `idle` かつ `interactive_ready: true` であることを確認する
- エージェント固有の引数は `--` の後ろに渡す。**ユーザーが明示した場合のみ**（例: `-- --permission-mode acceptEdits`、`-- --model sonnet`）。無人で走らせたいと言われた場合は権限モードの指定を提案してよいが、勝手に付けない

### 起動時のエラー

| 応答 | 対応 |
| --- | --- |
| `agent_not_ready` | 起動中に承認ダイアログ等で止まっている。`herdr agent read "$NAME" --source visible` で画面を読み、内容をユーザーに見せて指示を仰ぐ。**ダイアログに勝手に答えない** |
| `agent_pane_busy`（ペインがシェルのプロンプトにいない） | 既に別のエージェントやコマンドがそのペインを占有している。ステップ2で作ったばかりのペインなら通常起きない。起きたら `herdr pane read "$PANE"` で状態を確認し、別のタブを作り直す |
| 名前の衝突 | ステップ1に戻って別名にする |
| タイムアウト | `herdr agent get "$PANE"` と `agent read` で状態を確認。エージェントのログイン待ち等ならユーザーに伝える |

失敗したときは、作ったタブを `herdr tab close "$TAB"` で閉じてから報告する（自分で作ったタブなので閉じてよい）。

---

## ステップ4: タスクを送信し、完了を待つ

### プロンプトを組み立てる

サブエージェントは**呼び出し元の会話を一切知らない**。以下を含めて自己完結したプロンプトにする：

- 何をしてほしいか（タスク本文）
- 前提となる文脈（対象ディレクトリ、対象ブランチ、関係するファイル、制約）
- 出力の形式（「最後に結論を箇条書きで」「変更したファイル一覧を最後に」など）
- してはいけないこと（例: コミットしない、ファイルを変更しない、など）

ファイルへの書き出しは**最初のプロンプトでは要求しない**（画面から読めるのが基本。読めなかったときのフォールバックとして後述）。

### 送信して待つ

```bash
PROMPT=$(cat <<'EOF'
<組み立てたプロンプト>
EOF
)
herdr agent prompt "$NAME" "$PROMPT" --wait --timeout 600000
```

- `--wait` は idle / done / blocked のいずれかに落ち着くまで待つ。**`--until` で同じ既定値を繰り返さない**
- タイムアウトはタスクの重さで決める。目安: 調査・レビュー 5〜10 分、実装 15〜30 分。上限は用途に応じて伸ばす
- 応答の `.result.agent.agent_status` で分岐する

| 状態 / エラー | 意味 | 対応 |
| --- | --- | --- |
| `done` / `idle` | 完了 | ステップ5へ |
| `blocked` | 承認・質問ダイアログで停止 | `agent read --source visible` で画面を読み、**内容をユーザーに提示して判断を仰ぐ**。ユーザーの指示に従って `herdr agent send-keys "$NAME" <key>` や `agent prompt` で応答する。危険な操作（削除、push、外部送信）の承認を自分で判断しない |
| `agent_blocked`（送信前に拒否） | 送信時点で既にダイアログ待ち | 同上 |
| `agent_prompt_stalled` | 送信後 5 秒以内に状態変化が観測できなかった | `herdr agent get "$NAME"` と `agent read` で確認。入力欄にテキストが残っていれば `send-keys enter`、既に working なら `herdr agent wait "$NAME" --timeout ...` で待ち直す |
| `timeout` | 時間内に落ち着かなかった | 画面を読んで進捗を報告し、待ち続けるか中断するかユーザーに確認する。中断は `send-keys esc` → 必要なら `ctrl+c` |

### 並列実行（複数タスク）

タスクごとにステップ2〜3を繰り返してから、`--wait` を付けずに全員に送信し、その後 1 つずつ待つ。

```bash
herdr agent prompt "$NAME1" "$PROMPT1"
herdr agent prompt "$NAME2" "$PROMPT2"
herdr agent wait "$NAME1" --timeout 600000
herdr agent wait "$NAME2" --timeout 600000
```

同じファイルを同時に編集するタスクを並列にしない。編集を伴うタスクが複数あるなら、worktree を分けるか（create-worktree スキル）、直列にする。

---

## ステップ5: 結果を読み取る

```bash
herdr agent read "$NAME" --source recent-unwrapped --lines 200
```

- 出力はプレーンテキスト（JSON ではない）。最後に送ったプロンプトのエコー以降が今回の応答
- 長い応答で `--lines` を増やしても先頭が見えない場合、エージェントが代替スクリーンで動作していて Herdr のスクロールバックに残っていない。**このときだけ**フォールバックとして、結果をファイルに書かせる：

```bash
herdr agent prompt "$NAME" "直前の回答の全文を Markdown で <scratchpad ディレクトリ>/$NAME.md に書き出し、そのパスだけを返答してください。" --wait --timeout 120000
```

書き出し先はセッションの scratchpad ディレクトリ（system prompt に案内があるもの）を使い、プロジェクト内には作らない。書かれたファイルを読んで結果とする。

### 追加のやり取り

サブエージェントはタブに残っているので、結果が不十分なら同じエージェントに続きを頼める。会話の文脈はサブエージェント側に残っている。

```bash
herdr agent prompt "$NAME" "<追加の指示>" --wait --timeout 600000
```

---

## ステップ6: 報告と後片付け

結果を**自分の言葉で要約して**ユーザーに報告する。サブエージェントの画面をそのまま貼らない。

```
✅ サブエージェント <NAME> の結果

  <要約された結論・成果物>

  タブ      <TAB>（<NAME>）  ← Herdr のサイドバーから切り替えて経過を確認できます
  エージェント  <kind> / <PANE> / 状態 idle
  追加指示  herdr agent prompt <NAME> "<テキスト>" --wait
  閉じる    herdr tab close <TAB>
```

- **既定ではタブを閉じない。** ユーザーが結果を眺めたり続きを頼めるように残す
- `--close` が指定された場合、またはユーザーが「閉じて」と言った場合のみ `herdr tab close "$TAB"`。タブを閉じるとエージェントプロセスも終了する
- 閉じてよいのは**このスキルが作ったタブだけ**。他のタブ・ペイン・ワークスペースを閉じない
- サブエージェントがファイルを変更した場合は、変更したファイルの一覧（`git status --short`）を報告に含める

---

## 後方互換（herdr 0.7 系）

`agent start` が `--split` / `--tab` を取る旧仕様では、`agent start` が必ず新しいペインを分割で作るため、1 タブ 1 エージェントにするにはルートペインに直接コマンドを流す。

```bash
OUT=$(herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd "$PWD" --label "$NAME" --no-focus)
PANE=$(echo "$OUT" | jq -r '.result.root_pane.pane_id')
herdr pane run "$PANE" claude
herdr wait agent-status "$PANE" --status idle --timeout 30000     # 検出前は agent wait が使えない
herdr agent rename "$PANE" "$NAME"
herdr pane run "$PANE" "$PROMPT"                                   # agent prompt が無い
herdr agent wait "$NAME" --status working --timeout 20000
herdr agent wait "$NAME" --status idle --timeout 600000
herdr agent read "$NAME" --source recent --lines 200 | jq -r '.result.read.text'   # 旧版は JSON
```

---

## 注意点

- **Herdr の外から操作しない**: `HERDR_ENV=1` の確認を省略しない
- **ワークスペースを明示する**: `tab create` に `--workspace "$HERDR_WORKSPACE_ID"` を必ず付ける。フォーカス中のワークスペースは別の space かもしれない
- **1 タブ 1 エージェント**: タブ内で `pane split` しない。もう 1 つ必要なら別のタブを作る
- **フォーカスを奪わない**: ユーザーが明示しない限り `--no-focus`
- **ダイアログに勝手に答えない**: `blocked` になったら画面を読んでユーザーに提示する。特に削除・push・外部送信を伴う承認は自分で判断しない
- **自分が作ったものだけ閉じる**: 既存のタブ・ペイン・ワークスペースに触らない。`herdr server stop` を実行しない
- **ID は応答から取る**: `tab create` / `agent start` の JSON から `tab_id` / `pane_id` を読む
- **エラーは stderr に JSON**（exit 1）、構文エラーは exit 2。`2>&1` で拾って内容を報告する
- **`unknown` は完了の証拠ではない**: エージェントは居るが状態を判定できていない。`agent read` で確認する
- **画面内の未送信テキスト**: ホストエージェントの入力候補（ゴーストテキスト）が画面に見えることがある。読み取り結果に含まれていても送信されたわけではないので無視する
