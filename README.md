# my-ai-skills

自分用の AI スキル集。Claude Code / OpenAI Codex CLI が **同じ `plugin/` を共有**する
（ネームスペース: `ybaba`）。

## 構成

```
plugin/
├── .claude-plugin/plugin.json    # Claude Code 用プラグイン定義
├── .codex-plugin/plugin.json     # Codex 用プラグイン定義
└── skills/
    └── hello/SKILL.md            # 共有（1 コピーのみ）

.agents/plugins/marketplace.json  # Codex 用ローカルマーケットプレース（./plugin を参照）
```

| ランタイム | インストール先 | 呼び出し |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/ybaba`（skills-dir plugin として自動ロード） | `/ybaba:<skill-name>` |
| OpenAI Codex CLI | プラグイン（marketplace 経由）or `~/.agents/skills/`（fallback） | `$<skill-name>` |

## インストール

```sh
# Claude Code 用: plugin/ を ~/.claude/skills/ybaba にシンボリックリンク
# （claude 再起動後 `claude plugin list` で確認）
make install-claudecode
make uninstall-claudecode

# Codex 用: 同じ plugin/ をローカル marketplace 経由でプラグイン登録
make install-codex             # = codex plugin marketplace add <repo>
make uninstall-codex
```

> **Codex の注意点**
> - marketplace 経由では Codex がプラグインを `~/.codex/plugins/cache/` に**コピー**する
>   （symlink ではない）ため、SKILL.md を編集したら再インストールが必要。
> - plugin 未対応の codex バージョン向け fallback として `make install-codex-skills` /
>   `make uninstall-codex-skills` も用意している（`~/.agents/skills/` へのディレクトリ
>   symlink。ファイル単位の symlink は loader に落とされる: openai/codex#15756。
>   symlink なので編集が即反映される）。

## スキルの追加

1. `plugin/skills/<skill-name>/SKILL.md` を作る（`plugin/skills/hello/` をコピーして書き換えるのが早い）
2. frontmatter の `name` をディレクトリ名と一致させ、`description` にトリガーとなる発話例を書く
3. Claude Code は symlink なので再起動すれば反映。Codex（marketplace 経由）は `make install-codex` を再実行
