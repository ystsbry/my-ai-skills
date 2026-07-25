---
name: cleanup-worktree
description: |
  使われていない git worktree を、PR の状態・最終コミット・最終アクティビティから判定して一覧化し、ユーザーがチェックを付けたものだけを安全に削除する。未コミット・未 push の作業は検出して削除対象から除外する。
  「使ってない worktree を消したい」「worktree を掃除して」「cleanup-worktree」「不要なワークツリーを整理」などと言われたときに使う。
  create-worktree スキルで作った worktree の後片付けを想定。
---

# ワークツリー削除スキル（cleanup-worktree）

放置された worktree を棚卸しし、**ユーザーがチェックを付けたものだけ**を削除します。未コミット・未 push の作業を握り潰さないことを最優先にします。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:cleanup-worktree [--all]

# OpenAI Codex CLI
$ybaba:cleanup-worktree [--all]    # marketplace 経由のプラグイン
$cleanup-worktree [--all]          # ~/.agents/skills/ fallback 導入時
```

- 引数なし: **カレントリポジトリ**の worktree が対象
- `--all`: `ghq list` 配下の**全リポジトリ**を横断して対象にする

## 全体の流れ

1. worktree を列挙する
2. 各 worktree の状態を収集する
3. チェックリストを提示し、ユーザーの選択を待つ
4. 安全ゲートを通ったものだけ削除する
5. 結果を報告する

---

## ステップ1: worktree を列挙する

```bash
# カレントリポジトリ
git worktree list --porcelain

# --all の場合
ghq list -p | while read -r r; do
  echo "### $r"
  git -C "$r" worktree list --porcelain
done
```

`--porcelain` の出力は空行区切りのブロックで、`worktree <絶対パス>` / `HEAD <sha>` / `branch refs/heads/<名前>` が並ぶ。以下のように仕分ける：

- **1ブロック目は本体（main worktree）**。**絶対に削除対象に含めない**
- `prunable <理由>` が付いているもの → ディレクトリが既に消えている残骸。削除対象ではなく **`git worktree prune` の対象**として別枠で報告する
- `locked` が付いているもの → 意図的にロックされている。**対象から除外**し、ロックされている旨だけ報告する
- `branch` 行がなく `detached` のもの → ブランチ名で判定できないため、パスと HEAD の日時だけで扱い、判定材料が乏しいことを明示する

対象が0件なら、その旨を伝えて終了する。

---

## ステップ2: 各 worktree の状態を収集する

`$WT`（worktree パス）、`$BR`（ブランチ名）、`$MAIN`（本体 worktree パス）として、以下を集める。

### 安全ゲート用（削除可否を決める）

```bash
# 未コミットの変更・未追跡ファイル（空なら綺麗）
git -C "$WT" status --porcelain

# リモートのどこにも存在しないコミット（upstream 未設定でも正しく動く）
git -C "$MAIN" log --oneline "$BR" --not --remotes
```

`--not --remotes` を使うのが重要。`@{u}` は upstream 未設定のブランチで `fatal: no upstream configured` になるため使わない（create-worktree は `--no-track` でブランチを作るので、upstream 未設定が通常の状態）。

### 判断材料用（不要かどうかを示す）

```bash
# デフォルトブランチにマージ済みか
git -C "$MAIN" branch --merged origin/<デフォルトブランチ> --format='%(refname:short)'

# PR の状態（gh が使える場合）
gh pr list -R <owner/repo> --head "$BR" --state all --json number,state,title,url

# 最終コミット日時
git -C "$MAIN" log -1 --format='%cs (%cr)' "$BR"

# 最終編集: git 管理下のファイルのみを見る（node_modules 等は自然に除外される）
git -C "$WT" ls-files -z | xargs -0 stat -c '%Y' 2>/dev/null | sort -rn | head -1

# 最後にエージェントで作業した日（Claude Code のセッション履歴）
ls -t ~/.claude/projects/"$(echo "$WT" | sed 's#[/.]#-#g')"/*.jsonl 2>/dev/null | head -1 | xargs -r stat -c '%y'
```

- `owner/repo` は `gh repo view --json nameWithOwner -q .nameWithOwner`（本体リポジトリで実行）で取得する
- **gh が未認証・リモートが GitHub でない場合はスキップ**し、「PR 情報なし」として続行する。エラーで止めない
- セッション履歴のディレクトリ名は、絶対パスの `/` と `.` を `-` に置換したもの（例: `/home/ybaba/ghq-worktrees/github.com/x/y/feat-z` → `-home-ybaba-ghq-worktrees-github-com-x-y-feat-z`）。存在しなければ「記録なし」として扱う

### atime は使わない

ext4 は通常 `relatime` でマウントされており、atime の更新は「24時間以上古い場合」等に限られるうえ、`git status`・ripgrep・IDE のインデクサ・バックアップが走るだけで更新される。**「触っていないのに新しく見える」誤判定を生む方向**なので、判定に使わない。ユーザーから明示的に要求された場合のみ参考値として併記する。

---

## ステップ3: チェックリストを提示する

収集結果を**削除しやすい順**（PR merged かつ変更なし → 判断が必要なもの → 危険なもの）に並べ、**worktree ルートの直下**に書き出す：

```
${GHQ_WORKTREE_ROOT:-$(ghq root)-worktrees}/.cleanup-checklist.md
```

対象の worktree 群と同じ場所に置くことで、`--all` でリポジトリを横断しても1ファイルに収まる。実行のたびに上書きしてよい。

```markdown
# worktree 削除候補

削除したいものに `[x]` を付けて保存し、「チェックしました」と伝えてください。
番号で「1と3を削除」と会話で指示してもらっても構いません。

- [ ] 1. feat-add-login  `/home/ybaba/ghq-worktrees/github.com/ystsbry/app/feat-add-login`
      ✅ PR #123 merged / main にマージ済み / 未コミット変更なし / 未 push なし
      最終コミット 2026-06-02 (53日前) ・ 最終編集 2026-06-02 ・ 最終セッション 2026-06-03

- [ ] 2. spike-perf  `/home/ybaba/ghq-worktrees/github.com/ystsbry/app/spike-perf`
      ❓ PR なし / 未マージ / 未コミット変更なし / 未 push なし
      最終コミット 2026-04-11 (105日前) ・ 最終編集 2026-04-11 ・ 最終セッション 記録なし

- [ ] 3. fix-cache-bug  `/home/ybaba/ghq-worktrees/github.com/ystsbry/app/fix-cache-bug`
      ⚠ PR #131 open / 未コミット変更 3ファイル / 未 push コミット 2件
      最終コミット 2026-07-20 (5日前) ・ 最終編集 2026-07-24 ・ 最終セッション 2026-07-24
```

- **初期状態は全て未チェック**にする。安全側の候補を先回りしてチェック済みにしない
- 判定マークの基準
  - `✅` PR が merged/closed、またはデフォルトブランチにマージ済み。かつ未コミット変更なし・未 push コミットなし
  - `⚠` 未コミット変更あり、または未 push コミットあり（＝失われる作業がある）
  - `❓` 上記どちらでもない（PR なし・未マージだが、作業も残っていない）
- `prunable` な残骸と `locked` な worktree は、チェックリストとは**別のセクション**にまとめて報告する
- ファイルに書き出したうえで、**コンソールにも同じ一覧を出力**する（ファイルを開かずに番号で指示できるように）

提示したら**ユーザーの返答を待つ**。勝手に削除しない。

---

## ステップ4: 削除する

チェックされた（または番号指定された）worktree について、**1件ずつ**以下を実行する。

### 4-1. 安全ゲート

`⚠` が付いているものがチェックされていた場合、**そのまま削除せず**、失われる内容を具体的に示して再確認する：

```bash
git -C "$WT" status --short                          # 失われる変更
git -C "$MAIN" log --oneline "$BR" --not --remotes   # 失われるコミット
```

ユーザーが明示的に「それでも消す」と言うまで削除しない。`git worktree remove` は未追跡ファイルがあると
`fatal: ... contains modified or untracked files, use --force to delete it` で拒否するが、**この拒否に頼らず事前に提示する**。

### 4-2. worktree を削除する

```bash
git -C "$MAIN" worktree remove "$WT"
```

- **`--force` は付けない。** 拒否された場合はエラーをそのまま報告し、ユーザーが明示的に強制削除を指示した場合に限り `--force` を使う
- 失敗した項目があってもそこで止めず、**残りの項目の処理は続行**して、最後にまとめて報告する

### 4-3. ブランチを削除する

**worktree の削除後に実行する。** 先にやると `error: cannot delete branch '<name>' used by worktree at '<path>'` で失敗する。

```bash
git -C "$MAIN" branch -d "$BR"
```

- `-d` はマージ済みでなければ拒否される。**拒否されたら `-D` は使わず**、ブランチを残したことを報告する
- リモートブランチ（`origin/<BR>`）は**削除しない**。PR がマージされていれば GitHub 側で削除済みのことが多く、必要なら別途ユーザーが判断する

### 4-4. 後始末

```bash
git -C "$MAIN" worktree prune              # prunable な残骸の管理情報を掃除
rmdir -p --ignore-fail-on-non-empty "$(dirname "$WT")" 2>/dev/null   # 空になった親ディレクトリ
```

`rmdir` は空のときしか成功しないため、他の worktree が残っていれば何も起きない。

---

## ステップ5: 結果を報告する

```
🧹 worktree を整理しました

  削除          feat-add-login  (ブランチ feat/add-login も削除)
                spike-perf      (ブランチ spike/perf は未マージのため保持)
  スキップ      fix-cache-bug   (未 push コミット 2件のため中止)
  prune         1件の残骸の管理情報を掃除

  残っている worktree: 2件
```

- 削除したもの・残したもの・その理由を明示する
- ブランチを残した場合は、後で消すためのコマンド（`git branch -D <name>`）を案内するが、**このスキルからは実行しない**

---

## 注意点

- **本体（main worktree）を削除対象に含めない。** `git worktree list` の1行目は常に本体
- **`--force` と `git branch -D` を自発的に使わない。** どちらもユーザーの明示的な指示があるときだけ
- **git 管理外のファイルは復旧できない。** worktree 内の `.env` やローカル設定は削除で失われる。強制削除を求められた場合は、失われるファイルの一覧を必ず提示してから実行する
- **stash はリポジトリ共通**。worktree を削除しても stash は消えないが、どの worktree で作ったものか分からなくなる。`git stash list` に項目がある場合は報告に一言添える
- **`--all` 実行時**は、リポジトリごとにセクションを分けて提示する。番号はリポジトリを跨いで通し番号にし、取り違えを防ぐ
- 判定はあくまで材料の提示。**「不要そう」と判断したものを自動で削除しない**。チェックが付いたものだけを消す
