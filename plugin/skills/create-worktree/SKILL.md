---
name: create-worktree
description: |
  新しい PBI の実装を始める前に、git worktree を切って作業環境を用意する。分岐元ブランチを最新化した状態から新しいブランチを作成し、必要なセットアップ（.env コピー・依存インストール等）を検出してユーザー承認のうえ実行する。
  「ワークツリーを切って」「新しいブランチで作業を始めたい」「PBIの実装を始める」「create-worktree」「worktree 作って」などと言われたときに使う。
  refine-pbi / implement-plan など、実装系スキルの前段として使うことを想定。
---

# ワークツリー作成スキル（create-worktree）

新しい PBI に着手するとき、**本体のリポジトリを一切汚さずに**独立した作業ツリーを用意します。分岐元は必ず `git fetch` 直後のリモート最新状態から取り、作業に必要なセットアップまで面倒を見ます。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:create-worktree <ブランチ名 または PBIのタイトル・概要>

# OpenAI Codex CLI
$ybaba:create-worktree <ブランチ名 または PBIのタイトル・概要>    # marketplace 経由のプラグイン
$create-worktree <ブランチ名 または PBIのタイトル・概要>          # ~/.agents/skills/ fallback 導入時
```

## 全体の流れ

1. 前提確認とブランチ名の決定
2. worktree の配置先パスを算出する
3. リモートを最新化して worktree とブランチを作成する
4. セットアップ内容を検出し、承認を得て実行する
5. 結果を報告する

---

## ステップ1: 前提を確認し、ブランチ名を決める

```bash
git worktree list --porcelain | head -1      # 本体 worktree の絶対パス（"worktree <path>"）
git worktree list
git branch -r --sort=-committerdate | head -20
```

- **git リポジトリでない場合**は中断してユーザーに伝える
- **すでに worktree の中から実行された場合でも動作する**。`git worktree list` の**1行目が常に本体（main worktree）**であり、`--porcelain` なら linked worktree の中から実行しても絶対パスで返る。これを以降の `$MAIN_WT` として使う
  （`git rev-parse --git-common-dir` は本体で実行すると相対パス `.git` を返すため、パス算出には使わない）
- 現在の作業ツリーに未コミットの変更があっても**中断しない**。worktree の作成は現在の作業ツリーに影響しないため。ただし報告時に「現在のツリーはそのまま残っている」ことに触れる

### ブランチ名

- 引数がブランチ名として妥当な形（`feat/xxx` など）ならそのまま使う
- PBI のタイトルや概要が渡された場合は、**リモートブランチの既存の命名規則**（上の `git branch -r` の結果）に倣って英小文字ケバブケースで案を作り、ユーザーに確認してから進める
- 既存の命名規則が読み取れない場合は `feat/` `fix/` `chore/` の prefix を内容に応じて使う

---

## ステップ2: 配置先パスを算出する

**ghq root の隣に専用ルートを作り、ghq のパス構造をミラーする。**

```bash
GHQ_ROOT=$(ghq root)                         # 例: /home/ybaba/ghq
MAIN_WT=<git worktree list の1行目のパス>     # 例: /home/ybaba/ghq/github.com/ystsbry/my-ai-skills
WT_ROOT=${GHQ_WORKTREE_ROOT:-${GHQ_ROOT}-worktrees}
REL=${MAIN_WT#$GHQ_ROOT/}                    # 例: github.com/ystsbry/my-ai-skills
DIR=$WT_ROOT/$REL/<ブランチ名の / を - に置換>
```

```
/home/ybaba/ghq/github.com/ystsbry/my-ai-skills/            # 本体（ghq 管理）
/home/ybaba/ghq-worktrees/github.com/ystsbry/my-ai-skills/
  ├── feat-add-login/                                       # feat/add-login
  └── fix-cache-bug/                                        # fix/cache-bug
```

この配置を選ぶ理由（ユーザーに聞かれたら説明できるようにしておく）：

- worktree の `.git` は「ファイル」として存在するため、`~/ghq` 配下に置くと `ghq list` が worktree をリポジトリとして拾ってしまう
- リポジトリ内 `.worktrees/` に置くと tsc / jest / eslint / ripgrep / IDE インデックスが全 worktree を舐めてしまい、重複モジュール警告や検索ノイズの原因になる
- ghq のパス構造をミラーするので、リポジトリのパスから worktree のパスが機械的に決まる

### 例外ケース

- **本体が ghq root 配下にない場合**: パスを機械的に算出できない。`$WT_ROOT/_local/<リポジトリ名>/<ブランチ>` を提案し、ユーザーに確認する
- **算出したディレクトリが既に存在する場合**: 中身を確認し、`git worktree list` に載っている正規の worktree なら「既にあります」と案内して終了（**勝手に消さない**）。載っていない残骸なら削除してよいかユーザーに確認する

---

## ステップ3: 最新化して worktree とブランチを作成する

### 3-1. デフォルトブランチを特定する

```bash
git symbolic-ref --short refs/remotes/origin/HEAD    # 例: origin/main
```

取得できない場合は `git remote set-head origin -a` で更新してから再取得する。それでも駄目なら `git remote show origin | grep 'HEAD branch'` を使う。ユーザーが分岐元を明示した場合はそちらを優先する。

### 3-2. リモートを最新化する

```bash
git fetch origin --prune
```

fetch が認証エラー等で失敗した場合は、エラー内容を伝えてユーザーの対応を待つ。**古いままブランチを切らない。**

### 3-3. worktree とブランチを同時に作成する

```bash
git worktree add --no-track -b <ブランチ名> "$DIR" origin/<デフォルトブランチ>
```

ポイント：

- **ローカルの `main` を更新する必要はない。** `origin/<デフォルトブランチ>` から直接生やすので、fetch した時点で「最新化」は達成されている
- むしろ `git fetch origin main:main` 形式は、`main` が本体 worktree でチェックアウトされていると git に拒否されるため使わない
- `--no-track` は必須。付けないと upstream が `origin/<デフォルトブランチ>` に設定され、後で `git push` したときにブランチ名の不一致で弾かれる（push は後続の create-pr スキルが `git push -u origin <branch>` で行う）

### エラー時の対応

- `fatal: a branch named '<name>' already exists`
  → 既存ブランチをそのまま使う worktree にするか、別名にするかをユーザーに確認する。既存ブランチを使う場合は **`-b` と `--no-track` の両方を外す**（`--no-track` は新規ブランチ作成時にしか使えず、付けたままだと `fatal: --[no-]track can only be used if a new branch is created` で失敗する）

  ```bash
  git worktree add "$DIR" <ブランチ名>
  ```

- `fatal: '<name>' is already used by worktree at '<path>'`
  → そのブランチは既に別の worktree で作業中。git が出力したパスをそのまま案内して終了する
- `fatal: '<path>' already exists`
  → ステップ2の例外ケースに従って対応する

### （任意）ローカルのデフォルトブランチも最新化する

ユーザーが望む場合のみ、本体 worktree がクリーンなときに限って fast-forward する。**強制はしない。**

```bash
git -C "$MAIN_WT" merge --ff-only origin/<デフォルトブランチ>
```

---

## ステップ4: セットアップを検出し、承認を得て実行する

worktree には **git 管理外のファイルが一切コピーされない**（`.env`、`node_modules`、ビルド成果物など）。必要なものを検出し、**実行内容を提示してユーザーの承認を得てから**実行する。承認なしに実行しない。

### 4-1. 検出する

**リポジトリ固有の手順を最優先**する。以下にセットアップ手順の記載があれば、それに従う：

- `CLAUDE.md` / `AGENTS.md`
- `README.md` の「セットアップ」「Getting Started」節
- `Makefile` の `setup` / `bootstrap` / `init` ターゲット
- `package.json` の `scripts.setup` / `scripts.bootstrap`

**git 管理外の設定ファイル**（本体 worktree 側を見る）：

```bash
git -C "$MAIN_WT" ls-files --others --ignored --exclude-standard --directory
```

この出力から、`.env` 系・ローカル設定・証明書・認証情報など**手で作られた設定ファイル**を候補として拾う。`node_modules/` `dist/` `.next/` などの生成物は候補にしない（次項で再生成する）。

**依存インストール**（lockfile から判定する）：

| 検出したファイル | コマンド |
| --- | --- |
| `pnpm-lock.yaml` | `pnpm install --frozen-lockfile --prefer-offline` |
| `package-lock.json` | `npm ci` |
| `yarn.lock` | `yarn install --immutable` |
| `bun.lock` / `bun.lockb` | `bun install --frozen-lockfile` |
| `uv.lock` | `uv sync` |
| `poetry.lock` | `poetry install` |
| `Gemfile.lock` | `bundle install` |
| `go.sum` | 通常不要（モジュールキャッシュは共有される） |
| `Cargo.lock` | 通常不要（`target/` が再生成されるだけ） |

### 4-2. 提示して承認を得る

検出結果を以下の形式で提示し、**ユーザーの返答を待つ**：

```
worktree を作成しました: <パス>（<ブランチ名> ← origin/<デフォルトブランチ> の <短縮SHA>）

セットアップ候補:
  1. .env.local を本体からコピー
  2. pnpm install --frozen-lockfile --prefer-offline
  3. make setup（README に記載あり）

実行してよいですか？（不要なものがあれば番号で除外を指示してください）
```

- 候補が1つもない場合はその旨を伝えて、承認を求めずステップ5へ進む
- **秘匿情報を含むファイル**（`.env`、鍵ファイル等）は中身をコンソールに出力しない。ファイル名のみ提示する

### 4-3. 実行する

承認された項目を上から順に実行する。

- コピーは `cp -a <本体>/<file> <worktree>/<file>` で、ディレクトリ構造を保って行う
- 失敗した項目があれば**そこで止めてエラー内容を報告**し、続行するかユーザーに確認する（残りを勝手にスキップしない）
- 依存インストールが極端に遅い場合、pnpm なら store が worktree と同じファイルシステム上にあるか確認するよう助言する（別ファイルシステムだとハードリンクできず全ファイルコピーになる）

---

## ステップ5: 結果を報告する

```
✅ worktree を作成しました

  パス      <絶対パス>
  ブランチ  <ブランチ名>
  分岐元    origin/<デフォルトブランチ> (<短縮SHA> <コミットサマリー>)
  セットアップ  <実行した内容 / スキップした内容>

  cd <絶対パス>

現在の作業ツリー（<本体パス>）は変更していません。
```

- 移動コマンドは**提示するだけ**。このスキル自身がユーザーのシェルのカレントディレクトリを変えることはできない
- 後続として refine-pbi / implement-plan などの実装系スキルに繋げられることを一言添える

---

## 注意点

- **破壊的な操作をしない**: 既存の worktree・ブランチ・ディレクトリを、ユーザーの明示的な承認なしに削除しない。`git worktree remove --force` や `git branch -D` は使わない
- **本体の作業ツリーに触らない**: 本体のブランチ切り替え、stash、`git reset` は行わない。ローカルのデフォルトブランチの fast-forward だけは、ユーザーが望みかつクリーンな場合に限り許容する
- **fetch を省略しない**: 「最新化してからブランチを切る」がこのスキルの主目的。fetch に失敗したら止める
- **後片付けの案内**: 作業完了後は本体側で `git worktree remove <パス>` → 必要なら `git branch -d <ブランチ>`。手動でディレクトリを消してしまった場合は `git worktree prune` で管理情報を掃除する
- **docker compose を使うリポジトリ**: プロジェクト名（デフォルトはディレクトリ名）が worktree ごとに変わるためコンテナは分離されるが、**ホスト側のポートは衝突する**。同時起動するなら `COMPOSE_PROJECT_NAME` とポートの調整が必要な旨を伝える
- **dev サーバーのポート衝突**: 複数 worktree で同時に開発サーバーを立てる場合も同様。必要なら別ポートを案内する
