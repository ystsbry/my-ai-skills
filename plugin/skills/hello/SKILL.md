---
name: hello
description: プラグインの動作確認用サンプルスキル。「hello」「動作確認して」などと言われたら使う。新しいスキルを作るときのテンプレートとしてもコピーして使う。
---

# hello

プラグインが正しくロードされているかを確認するサンプルスキル。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:hello

# OpenAI Codex CLI
$ybaba:hello        # marketplace 経由のプラグイン
$hello              # ~/.agents/skills/ fallback 導入時
```

## 手順

1. 「ybaba plugin is working! 🎉」とユーザーに伝える
2. このプラグインに含まれるスキル一覧（`plugin/skills/*/SKILL.md` の name と description）を表示する

## 新しいスキルの作り方（メモ）

1. このディレクトリを `plugin/skills/<skill-name>/` としてコピーする
2. frontmatter の `name` をディレクトリ名と一致させる
3. `description` にはトリガーとなるユーザーの発話例を含める（スキル選択の判断材料になる）
4. 本文には入力形式と手順を書く。参照ファイルが必要なら同じディレクトリに置き、SKILL.md から相対パスで言及する
