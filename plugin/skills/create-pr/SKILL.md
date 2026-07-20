---
name: create-pr
description: |
  カレントブランチの変更内容から、リポジトリのPRテンプレートに沿ったPR本文を日本語で作成し、gh で PR（または Draft PR）を作成する。動作確認レポートがあればトグル形式でテスト項目に含める。
  「PRを作って」「PRテンプレートに沿ってPR作成」「Draft PRにして」「create-pr」「プルリク作成」などと言われたときに使う。
  git-commit スキルの後続として、コミット→プッシュ→PR作成のチェーンで使うことを想定。
---

# PR作成スキル（create-pr）

カレントブランチのコミット・差分を分析し、**リポジトリの PR テンプレートに準拠した本文**を日本語で作成して、`gh` で PR を作成します。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:create-pr [--draft] [ベースブランチや補足の指示]

# OpenAI Codex CLI
$ybaba:create-pr [--draft] [ベースブランチや補足の指示]    # marketplace 経由のプラグイン
$create-pr [--draft] [ベースブランチや補足の指示]          # ~/.agents/skills/ fallback 導入時
```

---

## ステップ1: 前提を確認する

```bash
git status
git log --oneline <ベースブランチ>..HEAD
git diff <ベースブランチ>...HEAD --stat
gh pr view 2>/dev/null   # 既存PRの有無
```

- ベースブランチは指示がなければリポジトリのデフォルトブランチ（`gh repo view --json defaultBranchRef`）
- **未コミットの変更がある場合**は先にコミットするか確認する（git-commit スキルの出番）
- **未 push の場合**は push する（upstream 未設定なら `git push -u origin <branch>`）
- **既に PR が存在する場合**は新規作成せず、本文更新（`gh pr edit`）に切り替えるか確認する

---

## ステップ2: PRテンプレートを探す

以下の順で探し、**見つかったテンプレートの構成に厳密に従う**：

```bash
ls .github/PULL_REQUEST_TEMPLATE.md .github/pull_request_template.md \
   docs/PULL_REQUEST_TEMPLATE.md PULL_REQUEST_TEMPLATE.md 2>/dev/null
ls .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null   # 複数テンプレート
```

- テンプレートの見出し・チェックボックス・コメント（`<!-- -->`）の指示をすべて読み、**項目を勝手に削除・改変しない**
- 複数テンプレートがある場合はユーザーに選んでもらう
- テンプレートがない場合は「概要 / 変更内容 / テスト / 影響範囲」の基本構成で書く

---

## ステップ3: PR本文を書く

コミットと差分の内容から、テンプレートの各項目を日本語で埋める。

- **概要・背景**: 「何を・なぜ」を、差分を読んでいない人にも伝わるように書く。関連チケット（Linear・Issue）が会話に出ていれば参照を入れる
- **変更内容**: 論理単位ごとの箇条書き。ファイル列挙ではなく変更の意味を書く
- **テスト・動作確認**: 実施済みの確認内容を書く。**動作確認レポートが会話にある場合は、トグル形式で詳細を含める**：

```markdown
<details>
<summary>動作確認レポート</summary>

（確認手順・結果・スクリーンショット参照など）

</details>
```

- 未実施の項目は空欄やチェック済みにせず、「未実施」と明記する
- 書き終えたら**タイトルと本文の全文をユーザーに提示して確認を得る**。タイトルはコミット規約に合わせた日本語（例: `feat: 〜を追加`）

---

## ステップ4: PRを作成する

```bash
gh pr create --base <ベースブランチ> --title '<タイトル>' --body "$(cat <<'EOF'
<PR本文>
EOF
)"
```

- `--draft` 指定時、または実装が途中・レビュー前提の共有と判断できる場合は Draft で作成する（Draft にするか迷う場合は確認する）
- 作成後、**PR の URL を報告**する

---

## ステップ5: 後続の案内

作成後、状況に応じて後続アクションを提案する（実行はユーザーの指示があってから）：

- Linear チケットのステータス更新・PR リンク添付
- レビュアーのアサイン（`gh pr edit --add-reviewer`）
- レビュー指摘が来たら respond-review スキルで対応
