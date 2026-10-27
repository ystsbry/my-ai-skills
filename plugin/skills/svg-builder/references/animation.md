# アニメーション

このスキルが作る図はすべて動く。作るときの問いは*どの*動きかであって、動かす*かどうか*ではない。描く
価値のある主題の多くは何かをしていて、静止画では読み手が矢印の先からそれを自力で組み立て直すことに
なる。

この既定が生む失敗は装飾なので、基準は狭い。動きがその場所を得るのは、図がすでに主張していること
（流れ、伝播、回転、対流、状態の変化、あるいは主題が本当に静止しているなら、部品が意味をなす順序）を
エンコードするときだけ。指すもののない脈動は静止より悪い。存在しない振る舞いをほのめかすからだ。ある
動きの意味を一節で言えないなら、動きが多すぎるのではなく、動きの選び方を間違えている。

## 目次

- [仕組みの選択](#仕組みの選択)
- [何をアニメーションさせるか](#何をアニメーションさせるか)
- [静止状態](#静止状態)
- [形式ごとのレシピ](#形式ごとのレシピ)
- [動きの抑制設定](#動きの抑制設定)
- [CSS キーフレーム](#css-キーフレーム)
- [SMIL](#smil)
- [JS: 経路に沿った粒子](#js-経路に沿った粒子)
- [インタラクティブな操作部](#インタラクティブな操作部)
- [パフォーマンス](#パフォーマンス)

## 仕組みの選択

| 必要なこと | 仕組み | 理由 |
|---|---|---|
| 破線の進行、脈動、フェード、単純な transform | CSS `@keyframes` | JS 不要、スタンドアロンの `.svg` で動く、メディアクエリを尊重する |
| 1 つのオブジェクトが決まった経路を進む | SMIL `<animateMotion>` | 宣言的、JS 不要、`<path>` に正確に従う |
| 再生コントロール、生成、状態、物理 | JS + `requestAnimationFrame` | 一時停止、速度、オブジェクトのライフサイクルが要るなら唯一の選択肢 |

用が足りる中で最も安いものを選ぶ。JS に手を伸ばすのは図に状態が要るときだけ。

**スタンドアロンの `.svg` ファイル:** CSS も SMIL も動く。`<img src="…">` で読み込まれたファイルでは
スクリプトは走らない。図に JS が要るなら HTML にインライン化しなければならず、そのことをユーザーに
伝える。

## 何をアニメーションさせるか

**`transform` と `opacity` だけ。** これらは GPU で合成される。`x`、`y`、`cx`、`cy`、`width`、`r` を
アニメーションさせると毎フレームのレイアウトを強制し、オブジェクトが数十を超えたとたんにカクつく。

例外は `stroke-dashoffset` で、安価であり、線に沿って流れを進めたりパスを描き進めたりする標準の方法で
ある。

ループは約 2 秒以内。それより長いと、読み手はループと感じなくなり、何かが起きるのを待ち始める。

`transform: scaleY()` で棒を伸ばすと、そのストロークと中の文字も拡大される。rect だけを拡大し、ラベルは
拡大するグループの外に置き、`transform-box: fill-box; transform-origin: bottom` を設定して、キャンバスの
中心ではなく自分の底辺から伸びるようにする。

## 静止状態

ほとんどの読み手は 1 フレームも再生を見ない。スクリーンショット、PDF 書き出し、フィードの中の
`<img src="…">`、動きの抑制設定を使う読み手は、アニメーションが一度も始まらない状態で、書かれたとおりの
マークアップを受け取る。そのフレームを先に設計する。動きは、すでに成立している図に足すものである。

そこから導かれるルール: **要素を隠すものはすべて `no-preference` ブロックの中に置き、要素自身の属性は
完成状態を持つ。** これを満たす最も安い方法は `from` だけのキーフレームで、漏れ出す隠れた状態がそもそも
ない。

```css
/* rect はそこにある。reveal が無から浮かび上がらせる */
@keyframes reveal { from { opacity: 0; } }
@media (prefers-reduced-motion: no-preference) {
  .node { animation: reveal .4s ease-out; }
}
```

ずらして表示するには `animation-delay` の間の本物の開始状態が要る。さもないと各要素が見えた状態で待ち、
自分の番が来た瞬間に消えて点滅する。`animation-fill-mode: both` がそれを与える。遅延の間は `from` で
埋め、終わったあとは `to` を保持する。隠す指定はキーフレームの中に留まり、静止状態の読み手はそこに
決して到達しない。

```css
@keyframes reveal { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: no-preference) {
  .node { animation: reveal .4s ease-out both; }
  .node:nth-of-type(2) { animation-delay: .15s; }
}
```

**表示のキーフレームは両端を書く。** `from` だけのキーフレームは終端の値を暗黙にし、CSS はそれを要素
自身の算出スタイルから解決する。だから別のルールが `.node { opacity: 0 }` と言った瞬間、アニメーションは
0 から 0 へ補間し、要素は決して現れない。この失敗は静かで完全である。アニメーションは走り、`playState`
は `running` を報告し、図は白紙。`check_svg.py` はこれを `REVEAL_STUCK` としてエラーにする。`from` だけ
の省略形が安全なのは、他に何もそのプロパティに触れないとき（上の遅延なしの例）だけで、両端を書く形は
どちらの場合も正しいので、そちらを選ぶ。

白紙の絵を納品してしまうのは、*無条件に*宣言された隠蔽である。マークアップ属性としての `opacity="0"`、
またはガードの外の `.node { opacity: 0 }` ルール。どちらもアニメーションが走らない状態まで生き残り、
読み手はタイトルだけの空のキャンバスを受け取る。`check_svg.py` は両方を `STATIC_BLANK` としてエラーに
し、ガードの中やキーフレームの中の同じ宣言は無視する。

## 形式ごとのレシピ

どの形式にも、動きではなく意味として読める動きが 1 つある。ここから始め、主題の実際の振る舞いが別の
ものを求めるときだけ逸脱する。

| 形式 | 動き | 仕組み |
|---|---|---|
| フローチャート | エッジに沿った破線の進行。上流が先になるようずらす | `stroke-dashoffset` の CSS |
| 構造図 | 段階的な表示。コンテナが先、その中身が後 | CSS の `reveal` + `animation-delay` |
| 説明図 | 仕組みそのもの。図が説明している当のもの | 必要なものは何でも。多くは JS |
| チャート | マークがエンコーディング軸に沿ってだけ伸びる | CSS `transform: scaleY()` + `transform-box: fill-box` |

さらに 2 つの制約:

- **ループは連続した振る舞いのため**で、約 2 秒以内。表示は一度再生して止まる。無限に繰り返す表示は
  図を点滅する看板に変える。
- **動く考えは一度に 1 つ。** 進むエッジ*と*脈動するノード*と*回転するバッジはノイズとして読まれ、
  読み手はどの動きが要点だったか判別できない。

## 動きの抑制設定

すべてのアニメーションを包み、動きが既定でオプトアウトになるようにする。

```css
@media (prefers-reduced-motion: no-preference) {
  .flow { animation: march 1.6s linear infinite; }
}
```

向きに注意。アニメーションは `no-preference` の*中*で宣言するので、設定を表明していない読み手、または
動きを減らすよう求めた読み手は静止した図を得る。アニメーションをグローバルに宣言して `reduce` クエリで
無効化するのがよくある逆転で、設定が未指定の人すべてに対して失敗する。

JS 駆動の動きでは同じシグナルを確認し、静止フレームを 1 枚描画する。

```js
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
if (still) { drawStaticFrame(); } else { requestAnimationFrame(frame); }
```

## CSS キーフレーム

コネクタに沿った流れ。主力。パスに沿って進む破線は、動くオブジェクトがまったくなくても方向のある
動きとして読める。

```svg
<style>
  @keyframes march { to { stroke-dashoffset: -20; } }
  @media (prefers-reduced-motion: no-preference) {
    .flow { animation: march 1.6s linear infinite; }
  }
  .flow { stroke-dasharray: 5 5; }
</style>
<path class="flow" d="M120 76 L120 100 L340 100 L340 132"
      fill="none" stroke="#1D9E75" stroke-width="1"/>
```

同じ要素を複数ずらすには、キーフレームブロックを何個も書かず遅延を使う。

```css
.node:nth-child(2) { animation-delay: .15s; }
.node:nth-child(3) { animation-delay: .30s; }
```

**`transform-box: fill-box`** は SVG の子要素を回転・拡大するとき必須。既定では `transform-origin` が
SVG のビューポート全体を基準に解決されるので、`center` はキャンバスの中心になり、要素はその周りを
公転する。

```css
.spin { transform-box: fill-box; transform-origin: center; }
```

## SMIL

1 つのオブジェクトが 1 つの経路をたどり、スクリプトをゼロにしたいときに最適。

```svg
<path id="r1" d="M160 84 V108 H340 V214" fill="none" stroke="none"/>
<circle r="5" fill="#1D9E75">
  <animateMotion dur="3s" repeatCount="indefinite">
    <mpath href="#r1"/>
  </animateMotion>
</circle>
```

兄弟のコピーに `begin="0s"`、`begin="0.8s"`、`begin="1.6s"` を付けてずらす。`calcMode="linear"` と
`keyPoints`/`keyTimes` で経路上のペースを制御する。

**SMIL はメディアクエリを尊重しない。** `<animateMotion>` に `prefers-reduced-motion` を宣言的に
伝える方法はないので、代わりに動くオブジェクトを CSS でガードする。進む点は純粋な動きなので、それを
消すのが正しい静止フレームである。

```css
.dot { display: none; }
@media (prefers-reduced-motion: no-preference) { .dot { display: inline; } }
```

これは点がどこで静止するかの問題も片付ける。`<animateMotion>` は要素自身の座標*の上に* transform を
供給するので、慣用的には原点に書く。だからアニメーションが走らないとき、ガードのない点はキャンバスの
左上隅に座る。隠してあれば単に存在せず、図は本来どおりに読める。

SMIL はスクリプトなしでは操作部から一時停止や速度変更ができず、オブジェクトのライフサイクルという概念も
ない。そこまで来たら JS に切り替える。

## JS: 経路に沿った粒子

パイプライン、ネットワーク、メッセージフローの図のパターン。見えない経路を描き、毎フレーム経路上の
位置をサンプリングする。

```js
const routes = [...svg.querySelectorAll('.route')].map(el => ({
  el, len: el.getTotalLength()
}));

const SPEED = 180;              // px/秒。フレームあたりではない
let prev = 0, live = [];

function frame(t) {
  if (!prev) prev = t;
  const dt = Math.min((t - prev) / 1000, 0.05);   // クランプ: タブ切り替えから戻ると巨大な dt が返る
  prev = t;

  for (let i = live.length - 1; i >= 0; i--) {
    const m = live[i];
    m.d += SPEED * dt;
    if (m.d >= m.route.len) { m.el.remove(); live.splice(i, 1); continue; }
    const p = m.route.el.getPointAtLength(m.d);
    m.el.setAttribute('transform', `translate(${p.x} ${p.y})`);
    m.el.setAttribute('opacity', hidden(p.y) ? '0' : '1');
  }
  requestAnimationFrame(frame);
}
```

ここで重要なのは 4 つ:

1. **フレーム数ではなくフレーム間の差分で駆動する。** `d += SPEED * dt` は 60Hz でも 144Hz でも同じ
   速さで動く。`d += 3` はそうならない。
2. **`dt` をクランプする。** バックグラウンドのタブは復帰時に数秒の差分を返し、すべての粒子が経路の
   終端にテレポートする。
3. **`cx`/`cy` ではなく `transform` で動かす。** 理由は上と同じ。
4. **迂回させず、隠す。** 経路が塗りのあるノードの背後を通る区間では、その座標範囲で `opacity: 0` に
   する。粒子はノードに入って出てくるように読め、それが図の意味するところであり、すべての箱を迂回する
   配線を避けられる。

`getTotalLength()` と `getPointAtLength()` はパスが文書の中にないと使えない。文字列として組み立てている
最中ではなく、SVG が解析されたあとに呼ぶ。

固定の出演者なら、生成と削除を繰り返さず要素を再利用する。連続したストリームなら、アキュムレータで
生成する。

```js
acc += dt;
const gap = 1 / rate;
while (acc >= gap) { acc -= gap; spawn(); }
```

## インタラクティブな操作部

インライン SVG の隣に本物の HTML の操作部（`<button>`、`<input type="range">`）を使う。キーボードで
到達でき、スクリーンリーダー向けのラベルも無料で付く。`<g>` に生の `onclick` を付けたものはどちらでも
ない。

- すべての操作部に、見えるラベルか `aria-label` が要る。
- 再生／一時停止の切り替えは、同じハンドラの中でアイコンとアクセシブルネームの両方を更新する。
- 一時停止から再開するときは `prev = 0` にリセットする。さもないと再開後の最初のフレームが、停止して
  いた全時間を差分として受け取る。
- 表示する数字はすべて丸める。さもないと `0.1 + 0.2` は `0.30000000000000004` と表示される。

## パフォーマンス

- 動くオブジェクトが約 50 未満なら、ここにあることは何も問題にならない。数百を超えたら SVG は道具と
  して間違っている。`<canvas>` に移る。
- 読み取りと書き込みをまとめる。1 つのループの中で `getPointAtLength()`（読み取り）と
  `setAttribute()`（書き込み）を交互に行うのは問題ないが、ループの中で DOM を問い合わせるのは問題。
  セレクタはループの外に出す。
- `requestAnimationFrame` のループは図全体で 1 つ。オブジェクトごとに 1 つにしない。
- `filter`、`box-shadow`、その他広い領域の再描画を引き起こすものは決してアニメーションさせない。
