---
name: dads-html
description: |
  デジタル庁デザインシステム（DADS）に沿った HTML ドキュメントを 1 ファイルで作る。公式のデザイントークンとコンポーネント CSS（MIT）を同梱し、使った部品の CSS だけを埋め込むビルドスクリプトと、見出し構造・コントラスト・パレット外の色・文字サイズなどを検査するチェッカーで仕上げる。
  「デジタル庁のデザインシステムで」「DADS で」「デジタル庁デザインシステムに沿って」「行政サイトのような見た目で」「アクセシブルな HTML 文書にして」「お知らせ・手続き案内・説明資料を HTML で」「dads-html」などと言われたときに使う。既存の HTML や Markdown を DADS の見た目に作り直す依頼にも使う。
  対象は読み物としての文書（案内・手順書・報告書・仕様説明・FAQ など）。入力フォームや画面遷移を持つアプリケーションの UI 実装、スライド、図そのものの作成（svg-builder の担当）には使わない。
---

# DADS 準拠 HTML ドキュメント作成（dads-html）

デジタル庁デザインシステム（DADS）の色・文字・部品で組んだ HTML 文書を 1 ファイル作る。

失敗するのはたいてい「それっぽい青と灰色で自作した CSS」になったときである。DADS らしさはトークンの値（文字色 #333、リンク #00118f、罫線 #949494 …）、テキストスタイル（本文 16px・行高 1.7・字間 0.02em）、部品ごとの細部（見出しの下線、表の見出しセル、黒＋黄のフォーカスリング）で決まり、目分量では再現できない。だから**見た目は自分で書かず、同梱の公式 CSS とクラスで組む**。自分で書く CSS は配置の微調整だけにして、値は必ずトークン変数で参照する。

## 入力

```
# Claude Code（ybaba プラグイン経由）
/ybaba:dads-html <作りたい文書の内容・素材・出力先>

# OpenAI Codex CLI
$ybaba:dads-html <作りたい文書の内容・素材・出力先>    # marketplace 経由のプラグイン
$dads-html <作りたい文書の内容・素材・出力先>          # ~/.agents/skills/ fallback 導入時
```

素材は会話の内容・Markdown・既存 HTML・メモなど何でもよい。本文中の `assets/`・`references/`・`scripts/` はこのスキルのディレクトリ基準のパス（Claude Code ではスキル読み込み時に示される Base directory を前置する）。

## ワークフロー

1. **要件を埋める** — 下の表。質問は最大 2 つ。
2. **構成を決める** — 見出しの木と、各ブロックに使う部品を決める。
3. **テンプレートから書く** — `assets/template.html` を出力先へコピーして本文を書く。
4. **ビルド** — `scripts/build.py` で DADS の CSS を埋め込む。
5. **検査** — `scripts/check.py` を通す。エラーを直して 4 からやり直す。
6. **目視確認** — 可能ならブラウザで開くかスクリーンショットを撮って崩れを見る。
7. **報告** — 出力先と、使った部品・残した警告を短く伝える。

## 1. 要件

| 項目 | 問い | 未指定時の既定 |
|---|---|---|
| 内容 | 何を伝える文書か、素材はどれか | — 必須 |
| 読み手 | 誰が読み、読んだ後に何をするか | 素材から推測する |
| 出力先 | ファイルパス | カレントディレクトリに `<内容を表す英語ケバブケース>.html` |
| 名義 | ヘッダー・フッターに出すサイト名・組織名・作成者 | 文書の題名だけ出し、組織名は書かない |
| フォント | Web フォント（Google Fonts の Noto Sans JP）を読み込むか | 読み込む。オフライン配布なら `--no-webfont` |

素材から読み取れる項目は黙って埋める。質問するのは、外すと書き直しになるもの（内容が曖昧、読み手によって構成が変わる）だけ。

**名義の注意:** DADS はだれでも使えるデザインシステムだが、作るのは「DADS の見た目の文書」であって政府の文書ではない。デジタル庁や省庁・自治体の名前、ロゴ、紋章を、ユーザーがその組織の人で明示的に求めた場合を除いて入れない。

## 2. 構成

書く前に、見出しの木と部品の割り当てをプレーンテキストで決める。

```
h1 経費精算の手続き
  lead   立て替えた経費は翌月 10 日までに申請する、と一文で
  banner warning: 期限を過ぎると翌々月の支払いになる
  h2 対象となる経費        → p, description-list（対象と上限額）
  h2 必要なもの            → list
  h2 申請の流れ            → list(number) + table（システムと紙の比較）
    h3 システムで申請する  → p, button(a)
    h3 紙で申請する        → p
  h2 よくある質問          → accordion ×3
  h2 関連資料              → resource-list
toc: h2 が 5 つ → 置く
```

- h1 は 1 つ。見出しレベルは飛ばさない。大きさは `data-size` で決め、レベルで調整しない。
- h2 が 3 つ以上なら目次（`dads-toc`）を置く。2 つ以下ならテンプレートの `<aside>` ごと消す。
- 部品は `references/components.md` の早見表から選ぶ。**同梱していない部品（カード、タブ、モーダル、フォーム部品など）は使わない。** 似た役割のものに置き換える（カードの並び → リソースリスト、タブ → 見出しで分けた節）。
- お知らせバナーは「読み落とすと困る」ことだけ。1 文書に 1〜2 枚まで。文書全体に関わるものは `<article>` の先頭（最初の `doc-section` の前）に置き、見出しは h2 にする。節の中に置くならその節の 1 つ下のレベル。
- アコーディオンを複数並べるときは、包まずに兄弟要素として続けて置く（document.css が間を詰める）。
- 文書の中の「ボタン」は別ページへの誘導だけなので `<a class="dads-button">` にする。`<button>` は JS が無いと何もしない。

## 3. テンプレートから書く

`assets/template.html` を出力先にコピーし、`{{…}}` を埋め、使わない部分を消す。テンプレートには次が入っている。

- `<head>` の `DADS:FONTS` と `DADS:STYLES` のマーカー（**消さない**。build.py がここを書き換える）
- スキップリンク、ヘッダー、パンくず（コメントアウト）、タイトル・メタ情報・リード文、目次、`doc-section` の入れ子、フッター

書くときのルール:

- **部品のマークアップは `references/components.md` から写す。** クラス名・`data-*` 属性・SVG アイコンを変えない。属性値は表にある値だけ。
- **本文の流れは `doc-flow` と `doc-section` に任せる。** 余白のための `style` 属性や `<br>` の連打を書かない。
- **本文のリンクにはすべて `class="dads-link"`。**
- 追加 CSS が要るときはテンプレートの 2 つ目の `<style>` に書く。色は `var(--color-…)`、サイズは `calc(px / 16 * 1rem)`、ウェイトは 400 / 700 だけ。値の選び方は `references/foundations.md` を読む。
- 色・文字・余白・アクセシビリティで迷ったら `references/foundations.md`。特に、白以外の面に文字を載せる、セマンティックカラーを文字に使う、のどちらかをするなら必ず読む。
- 文章自体は短い文で、結論を先に。手続きなら「誰が・いつまでに・何を・どこで」を最初の節で答える。

既存の HTML / Markdown を作り直すときは、元の内容と見出し構造を保ったまま、要素ごとに対応する部品へ置き換える（`<table>` → `dads-table` の形、注意書き → お知らせバナー、など）。元の CSS は持ち込まない。

## 4. ビルド

```sh
python3 scripts/build.py <出力先.html>                # 上書き（何度実行してもよい）
python3 scripts/build.py <出力先.html> --no-webfont   # Google Fonts を読まない
python3 scripts/build.py <下書き.html> -o <完成.html>  # 別名で出力
```

HTML 中の `dads-<部品>` クラスを拾い、`assets/dads/global.css`（トークン・フォーカス・テキストスタイル）+ 使った部品の CSS + `assets/document.css`（文書レイアウト層）をマーカーの間に埋め込む。DADS の MIT ライセンス表記も CSS コメントとして入る。外部ファイルへの依存は Web フォントだけになる。

同梱していない `dads-` クラスがあると警告して終了コード 1 を返す。部品名の打ち間違いか、使えない部品を使っている。

本文を直したら、そのたびに build.py を再実行する（部品を足したら CSS も増える）。

## 5. 検査

```sh
python3 scripts/check.py <出力先.html>
```

エラーは全部直す。警告は理由を確かめ、意図どおりならそのまま報告に書く。検査項目:

- **構造**: `lang`、`<title>`、h1 が 1 つ、見出しレベルの飛び、`alt`、表の `<th>` と `scope`、id の重複、`href="#…"` や `aria-labelledby` の参照先、`{{…}}` の残り、ビルド済みか
- **部品**: 同梱していない `dads-` クラス、document.css に無い `doc-` クラス、見出しの `data-size`
- **文言**: 「こちら」などのリンク文言、新規タブの明示、JS の無い `<button>`
- **追加 CSS**（`<style>` の追加分と `style` 属性）: パレット外の色、14px 未満の文字、400/700 以外のウェイト、イタリック、同じ規則の `color` と `background` のコントラスト比

check.py が見ないもの: 画像の中の文字、部品を入れ子にしたときの見た目、文章の分かりやすさ。これは 6 で見る。

## 6. 目視確認

幅 375px と 1280px でスクリーンショットを撮って見る。手段は環境にあるものを使う。

```sh
# Playwright（Python）が入っている場合
python3 -c "from playwright.sync_api import sync_playwright as p
with p() as pw:
    b = pw.chromium.launch(); pg = b.new_page()
    for w in (375, 1280):
        pg.set_viewport_size({'width': w, 'height': 800}); pg.goto('file://<絶対パス>.html')
        pg.screenshot(path=f'shot-{w}.png', full_page=True)"

# Chrome / Chromium だけある場合（全体を撮れないので高さを大きめに取る）
chromium --headless --screenshot=shot-1280.png --window-size=1280,4000 file://<絶対パス>.html
```

どちらも動かない（ブラウザが無い・共有ライブラリが足りない）なら、ここで環境を作り込まない。目視確認を省いたことを報告に書き、ユーザーにブラウザで開いてもらう。見るところ:

- 目次が広い画面で右に、狭い画面でタイトルの下に来ているか
- 表が画面からはみ出していないか（はみ出すなら `doc-scroll` で包む）
- お知らせバナーのアイコンと見出しが揃っているか
- 長い単語・URL が列を突き破っていないか

## 7. 報告

最初の一文で出力先のパスを伝える。続けて、構成（h2 の並び）、使った部品、残した警告とその理由を短く。本文で相対パスのファイル（`files/*.pdf` など）にリンクしたなら、それを HTML の隣に置く必要があることも書く。ユーザーが組織名やロゴを求めたのに入れなかった場合は、その理由も書く。

## 同梱物

| パス | 中身 |
|---|---|
| `assets/template.html` | ページの骨格（マーカー入り） |
| `assets/document.css` | 文書レイアウト層（このスキル独自。トークンだけで組む） |
| `assets/dads/global.css` | DADS のトークン・リンク・フォーカス・テキストスタイルのユーティリティ |
| `assets/dads/components/*.css` | DADS 公式コンポーネント 16 種（文書で使うもの） |
| `assets/dads/LICENSE` | DADS の MIT ライセンス |
| `references/components.md` | 部品ごとのマークアップと属性 |
| `references/foundations.md` | 色の役割・テキストスタイル・余白・アクセシビリティ |
| `scripts/build.py` | CSS の埋め込み |
| `scripts/check.py` | 検査 |

## 出典と更新

- CSS は [digital-go-jp/design-system-example-components-html](https://github.com/digital-go-jp/design-system-example-components-html)（MIT, © デジタル庁）の `src/global.css` と `src/components/<部品>/<部品>.css` をそのまま写したもの（2026-10-21 のコミット caa50d7 時点）。値は `@digital-go-jp/design-tokens` v2.1.0 と一致する。
- ガイドライン: https://design.digital.go.jp/dads/
- 更新するときは、上のリポジトリの同じファイルで `assets/dads/` を置き換え、`references/` の属性表と照らし合わせる。部品を増やすときは CSS を `assets/dads/components/` に置き、`scripts/build.py` の `COMPONENT_ORDER` と `references/components.md` に足す。
