# 部品カタログ

同梱している DADS 公式コンポーネント（`assets/dads/components/*.css`）と、文書レイアウト層（`assets/document.css`）のクラスの書き方。マークアップは公式の HTML 実装例から取り、文書向けに要らない部分（閉じるボタンなど JS 前提の部品）を外してある。

**ここに無い `dads-*` クラスは使わない**（スタイルが無く、`build.py` と `check.py` がエラーにする）。公式のガイドラインは `https://design.digital.go.jp/dads/components/<部品名>/`。

## 目次

1. [内容 → 部品の早見表](#1-内容--部品の早見表)
2. [見出し dads-heading](#2-見出し-dads-heading)
3. [リンク dads-link](#3-リンク-dads-link)
4. [リスト dads-list](#4-リスト-dads-list)
5. [説明リスト dads-description-list](#5-説明リスト-dads-description-list)
6. [表 dads-table](#6-表-dads-table)
7. [お知らせバナー dads-notification-banner](#7-お知らせバナー-dads-notification-banner)
8. [アコーディオン / ディスクロージャー](#8-アコーディオン--ディスクロージャー)
9. [引用 dads-blockquote](#9-引用-dads-blockquote)
10. [区切り線 dads-divider](#10-区切り線-dads-divider)
11. [チップラベル dads-chip-label](#11-チップラベル-dads-chip-label)
12. [ボタン dads-button](#12-ボタン-dads-button)
13. [リソースリスト dads-resource-list](#13-リソースリスト-dads-resource-list)
14. [パンくず・目次・ユーティリティリンク](#14-パンくず目次ユーティリティリンク)
15. [文書レイアウト層 doc-*](#15-文書レイアウト層-doc-)

---

## 1. 内容 → 部品の早見表

| 書きたいもの | 使う部品 |
|---|---|
| 章・節の見出し | `dads-heading`（レベルは文書構造、大きさは data-size） |
| 箇条書き・手順 | `dads-list`（手順は `data-marker="number"`） |
| 用語と説明、項目と値の組 | `dads-description-list` |
| 比較・一覧・数値 | `dads-table` |
| 読み手に必ず気づいてほしい注意・警告・完了・お知らせ | `dads-notification-banner` |
| 補足（読まなくても本筋が分かる） | `.doc-panel` か `dads-disclosure` |
| よくある質問・長い詳細の折りたたみ | `dads-accordion` |
| 他の文書・法令などからの引用 | `dads-blockquote` |
| 状態・分類のラベル（「必須」「対応済み」等） | `dads-chip-label` |
| 関連資料・ダウンロードの一覧 | `dads-resource-list` |
| 次の行動への誘導（申請ページへ、等） | `<a class="dads-button">` |
| 話題の切れ目 | `<hr class="dads-divider">` |
| コード・コマンド | `<pre><code>`（document.css が Mono で組む） |
| 図・画像 | `<figure class="doc-figure">` + `<figcaption>` |

---

## 2. 見出し dads-heading

```html
<div class="dads-heading" data-size="28" data-rule="4">
  <h2 id="overview" class="dads-heading__heading">概要</h2>
</div>
```

| 属性 | 値 | 意味 |
|---|---|---|
| `data-size` | 64, 57, 45, 36, 32, 28, 24, 20, 18, 16 | 文字サイズ（px）。テキストスタイル Std/Dsp の B に対応 |
| `data-rule` | 8, 6, 4, 2 | 見出しの下線の太さ |
| `data-chip` | （有無） | 左端の縦線 |

文書での割り当て: h1=36、h2=28（`data-rule="4"`）、h3=24、h4=20、h5=18。h2 には目次から飛べるよう `id` を付ける。

ショルダー（見出しの上の小さな文字。章番号や分類）を付けるときは `<hgroup>` にする:

```html
<hgroup class="dads-heading" data-size="28">
  <p class="dads-heading__shoulder">第2章</p>
  <h2 id="ch2" class="dads-heading__heading">申請の手順</h2>
</hgroup>
```

---

## 3. リンク dads-link

本文中のリンクにはすべて `class="dads-link"` を付ける（色・訪問済み・ホバー・フォーカスが揃う）。

```html
<a class="dads-link" href="https://example.go.jp/guide">申請の手引き</a>
```

新規タブで開くときはアイコンで明示する:

```html
<a class="dads-link" href="https://example.go.jp/" target="_blank" rel="noopener">
  参考サイト
  <svg class="dads-link__icon" width="16" height="16" viewBox="0 0 48 48" role="img" aria-label="新規タブで開きます">
    <path d="M22 6V9H9V39H39V26H42V42H6V6H22ZM42 6V20H39V11.2L21 29L19 27L36.8 9H28V6H42Z" fill="currentcolor"/>
  </svg>
</a>
```

---

## 4. リスト dads-list

```html
<ul class="dads-list" data-spacing="4">
  <li>本人確認書類</li>
  <li>申請書</li>
</ul>
```

番号付き（番号は手で書く。`<ol>` の自動番号ではなく `<span>` で入れるのが公式実装）:

```html
<ul class="dads-list" data-marker="number" data-spacing="8">
  <li><span>1. </span>申請書をダウンロードする</li>
  <li><span>2. </span>必要事項を記入する</li>
</ul>
```

`data-spacing` は項目の上下余白 4 / 8 / 12。入れ子は `<li>` の中に同じ `ul.dads-list` を入れる。

---

## 5. 説明リスト dads-description-list

```html
<dl class="dads-description-list" data-marker="bullet">
  <div class="dads-description-list__item">
    <dt>受付期間</dt>
    <dd>2026年11月1日〜2026年11月30日</dd>
  </div>
  <div class="dads-description-list__item">
    <dt>対象</dt>
    <dd>市内に住所がある方</dd>
  </div>
</dl>
```

`data-marker` を省くと点なし。項目と値が多く、比較が要るなら表にする。

---

## 6. 表 dads-table

```html
<figure class="dads-table">
  <figcaption class="dads-table__caption">表1: 手数料の一覧</figcaption>
  <table class="dads-table__table" data-cell-border="bottom">
    <thead>
      <tr>
        <th class="dads-table__col-header" scope="col">区分</th>
        <th class="dads-table__col-header doc-num" scope="col">手数料（円）</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <th class="dads-table__row-header" scope="row">窓口</th>
        <td class="doc-num">300</td>
      </tr>
      <tr>
        <th class="dads-table__row-header" scope="row">オンライン</th>
        <td class="doc-num">200</td>
      </tr>
    </tbody>
  </table>
</figure>
```

`.dads-table`（外側）に付ける属性:

| 属性 | 値 | 意味 |
|---|---|---|
| `data-size` | `dense` | 行高 1.3・余白小。行数が多い表 |
| `data-row-stripe` | （有無） | 偶数行に薄い背景 |
| `data-row-hover-highlight` | （有無） | ホバー行の強調 |

`table.dads-table__table` に付ける属性:

| 属性 | 値 | 意味 |
|---|---|---|
| `data-cell-border` | `bottom`（既定的に使う）/ `top right bottom left` の組 / 空値で全辺 | セルの罫線 |
| `data-width` | `full` | 表を本文列いっぱいに広げる。3 列以上の表や、文章が入るセルがある表には付ける（付けないと内容の幅に縮む） |
| `data-layout` | `fixed` | 列幅を固定（長文セルの暴れ防止） |

セル単位: `data-border="right"` 等で個別の罫線、`data-bg="solid-gray-50|solid-gray-100|white|transparent"` で背景。左上の空セルは `<td data-bg="solid-gray-100" data-border="right"></td>`。

- 見出しセルは必ず `<th scope="col|row">`。
- 数値列は `class="doc-num"`（右寄せ・等幅数字）。
- 列が多く画面幅を超える表は横スクロール領域で包む:

```html
<div class="doc-scroll" tabindex="0" role="region" aria-label="表2: 年度別の件数">
  <figure class="dads-table">…</figure>
</div>
```

---

## 7. お知らせバナー dads-notification-banner

文書の中で「読み落とすと困る」ことだけに使う。1 画面に何枚も並べない。閉じるボタンは JS が要るので文書では付けない。

```html
<div class="dads-notification-banner" data-style="standard" data-type="warning">
  <h2 class="dads-notification-banner__heading">
    <svg class="dads-notification-banner__icon" width="24" height="24" viewBox="0 0 24 24" role="img" aria-label="警告">
      <path d="M1 21 12 2l11 19H1Z" fill="currentcolor"/>
      <path d="M13 15h-2v-5h2v5Z" fill="Canvas"/>
      <circle cx="12" cy="17" r="1" fill="Canvas"/>
    </svg>
    <span class="dads-notification-banner__heading-text">提出期限は11月30日です</span>
  </h2>
  <div class="dads-notification-banner__body">
    <p>期限を過ぎた申請は受け付けられません。</p>
  </div>
</div>
```

- 見出しタグのレベルは置き場所に合わせる（h2 の節の中なら h3）。
- 日付を添えるなら本文の先頭に `<p class="dads-notification-banner__timestamp"><time datetime="2026-11-01">2026年11月1日</time></p>`。
- 次の行動があれば本文の後に `<div class="dads-notification-banner__actions"><a class="dads-button" data-size="md" data-type="solid-fill" href="…">申請する</a></div>`。

| `data-type` | 用途 | アイコン（`aria-label`） |
|---|---|---|
| `success` | 完了・成功を伝える | 成功 |
| `error` | エラー・問題・してはいけないこと | エラー |
| `warning` | 注意が要る | 警告 |
| `info-1` | お知らせ（キーカラー） | インフォメーション |
| `info-2` | お知らせ（グレー、控えめ） | インフォメーション |

`data-style`: `standard`（角丸の枠）/ `color-chip`（左に太い色帯。並べるときや控えめにしたいとき）。

アイコンの中身（`<svg …>` の内側）:

```html
<!-- success -->
<circle cx="12" cy="12" r="10" fill="currentcolor"/>
<path d="m17.6 9.6-7 7-4.3-4.3L7.7 11l2.9 2.9 5.7-5.6 1.3 1.4Z" fill="Canvas"/>

<!-- error -->
<path d="M8.25 21 3 15.75v-7.5L8.25 3h7.5L21 8.25v7.5L15.75 21h-7.5Z" fill="currentcolor"/>
<path d="m12 13.4-2.85 2.85-1.4-1.4L10.6 12 7.75 9.15l1.4-1.4L12 10.6l2.85-2.85 1.4 1.4L13.4 12l2.85 2.85-1.4 1.4L12 13.4Z" fill="Canvas"/>

<!-- warning -->
<path d="M1 21 12 2l11 19H1Z" fill="currentcolor"/>
<path d="M13 15h-2v-5h2v5Z" fill="Canvas"/>
<circle cx="12" cy="17" r="1" fill="Canvas"/>

<!-- info-1 / info-2 -->
<circle cx="12" cy="12" r="10" fill="currentcolor"/>
<circle cx="12" cy="8" r="1" fill="Canvas"/>
<path d="M11 11h2v6h-2z" fill="Canvas"/>
```

---

## 8. アコーディオン / ディスクロージャー

どちらも `<details>` なので JS 不要。

- **アコーディオン**: 同じ形の項目を並べて開閉する（よくある質問、長い詳細の束）。`<summary>` の中に見出しタグを入れる。
- **ディスクロージャー**: 単発の補足を隠す（「詳しい計算方法」など）。

```html
<details class="dads-accordion">
  <summary id="faq-1" class="dads-accordion__summary">
    <span class="dads-accordion__icon">
      <svg class="dads-accordion__icon-svg" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3.3 7.3L12 16L20.7 7.3" fill="none" stroke="currentcolor" stroke-width="2"/>
      </svg>
    </span>
    <h3>代理人でも申請できますか？</h3>
  </summary>
  <div class="dads-accordion__content">
    <p>できます。委任状が必要です。</p>
  </div>
</details>
```

```html
<details class="dads-disclosure">
  <summary id="calc-detail" class="dads-disclosure__summary">
    <svg class="dads-disclosure__icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="11" fill="currentcolor"/>
      <circle class="dads-disclosure__icon-circle" cx="12" cy="12" r="8" fill="currentcolor"/>
      <path class="dads-disclosure__icon-triangle" d="M17 10H7L12 15L17 10Z" fill="Canvas"/>
    </svg>
    計算方法の詳細
  </summary>
  <div class="dads-disclosure__content">
    <p>…</p>
  </div>
</details>
```

中身が長いときは末尾に「先頭に戻る」リンクを足せる（`summary` の id へ）:

```html
<a class="dads-accordion__back-link" href="#faq-1">
  <svg class="dads-accordion__back-link-icon" width="24" height="24" fill="none" aria-hidden="true">
    <path d="M6 7V14.5C6 16.8 8.2 19 10.5 19C12.8 19 15 16.8 15 14.5V6M10.709 9.7L15 5.414L19.291 9.7" stroke="currentcolor" stroke-width="2"/>
  </svg>
  「代理人でも申請できますか？」の先頭に戻る
</a>
```

（ディスクロージャーでは `dads-disclosure__back-link` / `dads-disclosure__back-link-icon`）

アコーディオンの中の段落は `dads-accordion__content` が余白を持たないので、`<p>` を複数置くなら `<div class="doc-flow">` で包む。

---

## 9. 引用 dads-blockquote

```html
<blockquote class="dads-blockquote">
  <p>引用する文章。</p>
</blockquote>
```

出典は直後に `<p class="doc-note">出典: <a class="dads-link" href="…">資料名</a></p>`。

---

## 10. 区切り線 dads-divider

```html
<hr class="dads-divider" data-color="solid-gray-420" data-style="solid" data-width="1">
```

`data-color`: solid-gray-420 / solid-gray-536 / black、`data-style`: solid / dashed、`data-width`: 1〜4。話題の切れ目なら `<hr>`、ただの飾りなら `<div class="dads-divider" …></div>`。節の区切りは見出しで足りるので多用しない。

---

## 11. チップラベル dads-chip-label

```html
<span class="dads-chip-label" data-style="outlined" data-color="red">必須</span>
```

| 属性 | 値 |
|---|---|
| `data-style` | `text` / `outlined` / `filled-1`（淡い面） / `filled-2`（濃い面・白文字） |
| `data-color` | gray, blue, light-blue, cyan, green, lime, yellow, orange, red, magenta, purple |

色は意味に合わせる（完了=green、要対応=red/orange、分類=blue/gray）。色だけでなく文言で区別できるようにする。並べるときは `<div class="doc-cluster">` で包む。

---

## 12. ボタン dads-button

文書の中のボタンは「別ページへ進む」誘導だけなので `<a>` で作る。

```html
<a class="dads-button" data-size="md" data-type="solid-fill" href="https://example.go.jp/apply">オンラインで申請する</a>
```

| 属性 | 値 |
|---|---|
| `data-type` | `solid-fill`（主。1 画面に 1 つ）/ `outline`（副）/ `text`（さらに弱い） |
| `data-size` | `lg` / `md` / `sm` / `xs` |

複数並べるときは `<div class="doc-cluster">` で包み、主ボタンを先に置く。

---

## 13. リソースリスト dads-resource-list

関連資料・ダウンロードファイルの一覧。

```html
<ul class="doc-resource-items">
  <li>
    <div class="dads-resource-list" data-style="frame">
      <div class="dads-resource-list__body">
        <div class="dads-resource-list__contents">
          <h3 class="dads-resource-list__title">
            <a href="files/guide.pdf">申請の手引き（PDF / 1.2MB）</a>
          </h3>
          <div class="dads-resource-list__support"><p>手続きの流れと記入例</p></div>
        </div>
      </div>
    </div>
  </li>
</ul>
```

`data-style`: `list`（下線だけ）/ `frame`（枠で囲む）。タイトル内の `<a>` には `dads-link` を付けない（resource-list.css が色を当てる）。ファイルへのリンクには形式とサイズを書く。

---

## 14. パンくず・目次・ユーティリティリンク

パンくずと目次は `assets/template.html` に入っている形をそのまま使う。

- **パンくず `dads-breadcrumb`**: 文書がサイトの階層の中にあるときだけ。最後の項目はリンクにせず `aria-current="page"`。
- **目次 `dads-toc`**: h2 が 3 つ以上あるとき。h2（必要なら h3 まで）の `id` へリンクする。入れ子は `<li>` の中に `ul.dads-list` を入れる。枠で囲むなら `data-border="solid"`。
- **ユーティリティリンク `dads-utility-link`**: ヘッダーやフッターの小さなリンク。

```html
<a class="dads-utility-link" href="#"><span class="dads-utility-link__label">お問い合わせ</span></a>
```

---

## 15. 文書レイアウト層 doc-*

`assets/document.css` で定義した、このスキル独自のクラス。DADS のトークンだけで組んである。

| クラス | 役割 |
|---|---|
| `doc-skip-link` | 「本文へ移動」。`dads-link` と併用 |
| `doc-header` / `doc-header__inner` / `doc-header__title` / `doc-header__nav` | ヘッダー |
| `doc-container` | 左右余白と最大幅 1200px |
| `doc-breadcrumb` | パンくずの置き場 |
| `doc-main` | `<main>` の上下余白 |
| `doc-layout` / `doc-layout__title` / `doc-layout__aside` / `doc-layout__body` | タイトル・目次・本文のグリッド（広い画面で目次が右に固定） |
| `doc-article` | 本文列（最大 736px ≒ 全角 45 字） |
| `doc-title-block` | h1・メタ情報・リード文のまとまり |
| `doc-meta` | 公開日・更新日などの `<dl>` |
| `doc-lead` | リード文 |
| `doc-flow` | 子要素の間を 24px 空ける流れ |
| `doc-section` | 見出し付きの節（`<section>`）。h2 の節は 64px、入れ子は 40px 空く |
| `doc-figure` | 図・画像の `<figure>` |
| `doc-scroll` | 横スクロール領域（表の包み） |
| `doc-num` | 数値セル（右寄せ・等幅数字） |
| `doc-panel` | 薄いグレーの補足パネル |
| `doc-label` | パネル内などの小さな見出しラベル（文書構造上の見出しではない） |
| `doc-cluster` | ボタンやチップの横並び |
| `doc-note` | 補足の小さい文（色だけ薄く、サイズは本文と同じ） |
| `doc-resource-items` | リソースリストを縦に並べる `<ul>` |
| `doc-footer` | フッター |
