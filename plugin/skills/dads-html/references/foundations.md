# 基礎ルール（色・文字・余白・アクセシビリティ）

出典: デジタル庁デザインシステム（DADS）
- ガイドライン: https://design.digital.go.jp/dads/
- トークン: `@digital-go-jp/design-tokens` v2.1.0（Figma 2.0.4〜2.18.1 相当）
- HTML 実装: https://github.com/digital-go-jp/design-system-example-components-html

値は `assets/dads/global.css` の CSS 変数として埋め込まれる。**追加 CSS では値を直書きせず、必ず変数で参照する。**

---

## 1. 色

### 役割ごとの使い分け

| 役割 | 変数 | 値 | 白地のコントラスト | 用途 |
|---|---|---|---|---|
| 本文テキスト | `--color-neutral-solid-gray-800` | #333333 | 12.6:1 | 本文の既定 |
| 見出し・強いテキスト | `--color-neutral-solid-gray-900` | #1a1a1a | 17.4:1 | 表の見出しセル、ラベル |
| 補足テキスト | `--color-neutral-solid-gray-600` | #666666 | 5.7:1 | 日付・キャプション・注記 |
| テキストの下限 | `--color-neutral-solid-gray-536` | #767676 | 4.5:1 | これより薄いグレーを文字に使わない |
| 罫線・区切り線 | `--color-neutral-solid-gray-420` | #949494 | 3.0:1 | 意味のある罫線（非テキストの下限） |
| 装飾的な罫線 | `--color-neutral-solid-gray-200` | #cccccc | — | 意味を持たない薄い線だけ |
| 面（薄い背景） | `--color-neutral-solid-gray-50` | #f2f2f2 | — | パネル・フッター・コード |
| 面（見出しセル） | `--color-neutral-solid-gray-100` | #e6e6e6 | — | 表の見出しセル |
| 背景 | `--color-neutral-white` | #ffffff | — | ページ背景（DADS はライトテーマのみ） |
| キーカラー（主） | `--color-key-900` = blue-900 | #0017c1 | 11.1:1 | 主ボタン、選択状態、強調の線 |
| キーカラー（淡） | `--color-key-50` = blue-50 | #e8f1fe | — | 淡い強調面 |
| リンク | `--color-primitive-blue-1000` | #00118f | 14.2:1 | `dads-link` が自動で当てる |
| 訪問済みリンク | `--color-primitive-magenta-900` | #8b008b | 8.5:1 | 同上 |
| フォーカス | black + `--color-primitive-yellow-300` | #000 / #ffd43d | — | **変更禁止**。global.css が当てる |

`--color-key-*` は blue の別名。キーカラーを他の色相に替えたいときは、`:root` で `--color-key-*` を同じ段の別色相（例: `--color-primitive-green-*`）に差し替える。その場合も主に使う段（900 前後）が白地で 4.5:1 以上あるかを確認する。

### セマンティックカラー（色相を変えてはいけない）

| 意味 | 変数（-1 / -2） | 値 | 使う場面 |
|---|---|---|---|
| 成功 | `--color-semantic-success-1` / `-2` | green-600 #259d63 / green-800 #197a4b | 完了・安全 |
| エラー | `--color-semantic-error-1` / `-2` | red-800 #ec0000 / red-900 #ce0000 | エラー・危険・制限 |
| 警告（黄） | `--color-semantic-warning-yellow-1` / `-2` | yellow-700 #b78f00 / yellow-900 #927200 | 注意 |
| 警告（橙） | `--color-semantic-warning-orange-1` / `-2` | orange-600 #fb5b01 / orange-800 #c74700 | 禁止・強い注意 |

- 文字として使うなら白地で 4.5:1 以上が要る。success-1（3.4:1）・warning-yellow-1（3.0:1）・warning-orange-1（3.2:1）は文字には薄いので、文字には **-2** を使う（error-1 は 4.6:1 で文字にも使える）。
- エラーを緑で示す、のような色相の入れ替えはしない。
- 意味を色だけで伝えない。必ずアイコンか文言を添える（お知らせバナーは両方入っている）。

### 原色（プリミティブ）

blue / light-blue / cyan / green / lime / yellow / orange / red / magenta / purple の 10 色相 × 13 段（50, 100, 200 … 900, 1000, 1100, 1200）。変数名は `--color-primitive-<色相>-<段>`。目安:

- **50〜200**: 背景の面。上に gray-800 の文字を載せられる。
- **600〜800**: アイコン・罫線（非テキスト 3:1）。文字にはそのまま使わない（明るい色相は 4.5:1 に届かない）。
- **900〜1200**: 文字・太い線。白地で 4.5:1 を超える。
- グラフや分類で複数の色が要るときも、この表の中から選ぶ。

グレーは `--color-neutral-solid-gray-<50|100|200|300|400|420|500|536|600|700|800|900>`、半透明の黒は `--color-neutral-opacity-gray-<同じ段>`。

### 組み合わせのルール

- 文字と背景: **4.5:1 以上**。白以外の面に文字を載せるときは毎回確かめる（`scripts/check.py` は、同じ規則に `color` と `background` を書けば計算する）。
- 罫線・アイコンなど非テキスト: 隣の背景と **3:1 以上**。
- グラデーション・影で意味を出さない。影はエレベーション（`--elevation-1`〜`-8`）だけで、文書ではほぼ使わない。

---

## 2. 文字

### フォント

- 和文・欧文: `var(--font-family-sans)` = "Noto Sans JP", -apple-system, BlinkMacSystemFont, sans-serif
- コード: `var(--font-family-mono)` = "Noto Sans Mono", monospace
- 端末のフォントで表示されても意味が変わらないように書く（書体に情報を持たせない）。

### テキストスタイル

名前は「種別-サイズ ウェイト-行高」。N=400、B=700。**ウェイトはこの 2 つだけ。**

| 種別 | 用途 | サイズ(px) | 行高 | 字間 |
|---|---|---|---|---|
| Dsp | 表紙のキャッチなど強い印象が要る所 | 64 / 57 / 48 | 1.4 | 0 |
| Std | 見出し・本文の標準 | 45〜16 | 1.4〜1.75 | 45px: 0 / 36〜28px: 0.01em / 26px 以下: 0.02em |
| Dns | 管理画面・データ表など情報量優先 | 17 / 16 / 14 | 1.2 / 1.3 | 0 |
| Oln | ボタンなど 1 行の UI | 17 / 16 / 14 | 1.0 | 0.02em |
| Mono | コード | 17 / 16 / 14 | 1.5 | 0 |

Std の行高: 45・36px は 1.4、32〜20px は 1.5、18px は 1.6、17・16px は 1.7（16px のみ 1.75 もある）。

ユーティリティクラス `dads-u-<種別>-<サイズ><N|B>-<行高>`（例 `dads-u-std-18B-160`、`dads-u-dns-16N-130`、`dads-u-mono-16N-150`）で当てられる。一覧は global.css の末尾。

### 文書での割り当て（このスキルの既定）

| 要素 | スタイル | 実装 |
|---|---|---|
| 文書タイトル h1 | Std-36B-140（長い題なら 32） | `dads-heading data-size="36"` |
| 大見出し h2 | Std-28B-150 + 下線 4px | `dads-heading data-size="28" data-rule="4"` |
| 中見出し h3 | Std-24B-150 | `dads-heading data-size="24"` |
| 小見出し h4 | Std-20B-150 | `dads-heading data-size="20"` |
| h5 | Std-18B-160 | `dads-heading data-size="18"` |
| リード文 | Std-18N-160 | `.doc-lead` |
| 本文 | Std-16N-170 | `body` の既定 |
| 補足・日付 | Std-16N-170, gray-600 | `.doc-meta` `.doc-note` |
| 表 | Std-16N-170（密な表は Dns-16N-130） | `dads-table`（`data-size="dense"`） |
| コード | Mono-16N-150 | `pre` `code` の既定 |
| フッター | Dns-14N-130 | `.doc-footer` |

- **本文と UI は 16px 以上。** 14px はフッターなど付随情報か、領域が足りないときだけ。14px 未満は使わない。
- 本文の行高は 1.5 以上（既定 1.7）。
- 1 行は全角 45 字前後まで（`.doc-article` の最大幅 736px）。
- イタリックは使わない（和文は擬似斜体になり読みにくい）。強調は `<strong>`。
- 下線はリンク専用。強調に下線を使わない。リンクの下線を消さない。

---

## 3. 余白

DADS の部品は `calc(px / 16 * 1rem)` で余白を指定し、罫線だけ px にする。追加 CSS も同じ書き方にする。値は 4 の倍数（4, 8, 12, 16, 24, 32, 40, 48, 64, 80）から選ぶ。

| 間隔 | 値 | このスキルでの用途 |
|---|---|---|
| 段落どうし | 16 | `.doc-section > p + p` |
| ブロックどうし | 24 | `.doc-flow > * + *`、`.doc-section > * + *` |
| h3 以下の節 | 40 | 入れ子の `.doc-section` |
| h2 の節 | 64 | `.doc-flow > .doc-section` |

角丸は 4 / 6 / 8 / 12 / 16 / 24 / 32 / full。文書ではパネル 12、コード 8、インラインコード 4。

---

## 4. アクセシビリティ（WCAG 2.2 AA が目標）

- `<html lang="ja">`、`<title>` は「文書名｜サイト名」。
- h1 は 1 つ。見出しレベルを飛ばさない。見た目の大きさは `data-size` で変え、レベルは文書構造で決める。
- 先頭にスキップリンク（`.doc-skip-link`）、本文は `<main id="main">`。
- 画像は `alt` 必須（装飾は `alt=""`）。図表には文章でも要点を書く。
- 表は `<th scope="col|row">`、題は `<figcaption class="dads-table__caption">`。横に長い表は `<div class="doc-scroll" tabindex="0" role="region" aria-label="〇〇の表">` で包む。
- リンク文言は行き先の名前にする（「こちら」禁止）。新規タブで開くなら `dads-link__icon`（aria-label="新規タブで開きます"）を付ける。
- 色だけで意味を伝えない。
- フォーカスリング（黒 4px + 黄）を消さない・変えない。`outline: none` を書かない。
- JS を書かない文書では `<button>` を置かない（押しても何も起きない）。開閉は `<details>`（`dads-accordion` / `dads-disclosure`）で作る。
