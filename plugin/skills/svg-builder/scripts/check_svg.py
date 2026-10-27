#!/usr/bin/env python3
"""生成した SVG を、決まって踏む失敗パターンに対して検証する。

使い方:
    python3 check_svg.py diagram.svg
    python3 check_svg.py page.html --json
    python3 check_svg.py diagram.svg --strict     # 警告でも非ゼロ終了
    python3 check_svg.py foreign.svg --allow-static   # 動きの検査を飛ばす

終了コード: 0 問題なし（または警告のみ）、1 エラーあり、2 解析不能。

標準ライブラリのみ。文字幅は文字数からの推定なので、文字のはみ出しは
エラーではなく警告にしてある。確認はすること。ただし鵜呑みにしないこと。
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
NS = {"svg": SVG_NS}

# フォントサイズとウェイトごとの 1 文字あたり px。references/layout.md と一致させる。
CHAR_W = {(14, 500): 8.5, (14, 400): 8.0, (12, 400): 7.0, (11, 400): 6.5}
WIDE_GLYPH = re.compile(r"[　-鿿＀-￯Ͱ-Ͽ∀-⋿₀-₉⁰-⁹]")

CONNECTOR_HINTS = ("edge", "arr", "conn", "link", "route", "flow", "leader", "path")


def classes_setting_fill(style_text):
    """CSS ルールで `fill` を設定している class 名。これが付いた要素はスタイル済みとみなす。

    これがないと、class でスタイルを当てたコネクタ（慣用的な書き方）が
    fill="none" 欠落として誤検出される。
    """
    found = set()
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style_text):
        if not re.search(r"(^|[;\s])fill\s*:", body):
            continue
        for cls in re.findall(r"\.([A-Za-z_][-\w]*)", selector):
            found.add(cls)
    return found


def resting_css(style_text):
    """アニメーションが一度も再生されないときにも効いている CSS。

    2 つを落とす。どちらも静止した図を受け取る読み手には届かないからだ。
    @keyframes の本体（ここでの `from { opacity: 0 }` は正しい書き方）と、
    prefers-reduced-motion: no-preference ブロック（その中のルールは構造上オプトイン）。
    残ったものが静止状態であり、スクリーンショットに写るのはそれである。
    """
    block = r"(?:[^{}]*\{[^{}]*\})*[^{}]*\}"
    text = re.sub(r"@keyframes[^{]*\{" + block, "", style_text)
    text = re.sub(
        r"@media[^{]*prefers-reduced-motion\s*:\s*no-preference[^{]*\{" + block,
        "",
        text,
    )
    return text


def tag(el):
    return el.tag.split("}")[-1] if "}" in el.tag else el.tag


def fnum(v, default=None):
    """単位付きかもしれない SVG の数値を解析する。"""
    if v is None:
        return default
    m = re.match(r"\s*(-?\d*\.?\d+)", str(v))
    return float(m.group(1)) if m else default


def extract_svg(text):
    """HTML かもしれないファイルから最初の <svg>...</svg> を取り出す。"""
    m = re.search(r"<svg\b.*?</svg\s*>", text, re.S | re.I)
    return m.group(0) if m else None


def char_width(size, weight):
    key = (int(size), 500 if weight >= 500 else 400)
    if key in CHAR_W:
        return CHAR_W[key]
    return size * 0.58


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def error(self, code, msg, line=None):
        self.errors.append({"code": code, "message": msg, "line": line})

    def warn(self, code, msg, line=None):
        self.warnings.append({"code": code, "message": msg, "line": line})

    def note(self, code, msg, line=None):
        self.notes.append({"code": code, "message": msg, "line": line})


def inherited(el, parents, attr):
    """親をたどって、属性か class が付いているかを調べる。"""
    cur = el
    while cur is not None:
        if cur.get(attr) or cur.get("class"):
            return True
        cur = parents.get(id(cur))
    return False


def collect(root, parents, parent=None):
    for child in root:
        parents[id(child)] = parent if parent is not None else root
        collect(child, parents, child)


def rects_of(svg, parents):
    out = []
    for el in svg.iter():
        if tag(el) != "rect":
            continue
        x, y = fnum(el.get("x"), 0), fnum(el.get("y"), 0)
        w, h = fnum(el.get("width")), fnum(el.get("height"))
        if w is None or h is None:
            continue
        out.append({"el": el, "x": x, "y": y, "w": w, "h": h})
    return out


def text_extent(el):
    """<text> 要素の文字列全体から (幅, サイズ) を推定する。"""
    size = fnum(el.get("font-size"))
    cls = el.get("class") or ""
    if size is None:
        size = 12.0 if "ts" in cls.split() else 14.0
    weight = fnum(el.get("font-weight"), 400) or 400
    if "th" in cls.split():
        weight = 500

    tspans = [t for t in el.iter() if tag(t) == "tspan"]
    if tspans:
        lines = ["".join(t.itertext()).strip() for t in tspans]
    else:
        lines = ["".join(el.itertext()).strip()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return 0.0, size, ""

    cw = char_width(size, weight)
    widest, longest = 0.0, ""
    for ln in lines:
        wide = len(WIDE_GLYPH.findall(ln))
        w = (len(ln) - wide) * cw + wide * cw * 1.8
        if w > widest:
            widest, longest = w, ln
    return widest, size, longest


def check(svg_src, report, allow_static=False):
    try:
        svg = ET.fromstring(svg_src)
    except ET.ParseError as exc:
        report.error("PARSE", f"SVG が整形式の XML ではありません: {exc}")
        return None

    parents = {}
    collect(svg, parents)

    style_text = " ".join("".join(s.itertext()) for s in svg.iter() if tag(s) == "style")
    fill_classes = classes_setting_fill(style_text)

    # --- アクセシビリティのブロック -------------------------------------------
    if svg.get("role") != "img":
        report.error("A11Y_ROLE", 'ルートの <svg> に role="img" がありません。')
    kids = [tag(c) for c in list(svg)]
    head = [k for k in kids if k in ("title", "desc")]
    if "title" not in kids:
        report.error("A11Y_TITLE", "ルートの <svg> に <title> がありません。")
    if "desc" not in kids:
        report.warn("A11Y_DESC", "ルートの <svg> に <desc> がありません。")
    if head and kids[: len(head)] != head:
        report.warn(
            "A11Y_ORDER",
            "<title>/<desc> はありますが <svg> の最初の子要素ではありません。"
            "スクリーンリーダーによってはその位置にあるときだけ読み上げます。",
        )

    # --- viewBox -------------------------------------------------------------
    vb = svg.get("viewBox")
    vb_w = vb_h = None
    if not vb:
        report.error("VIEWBOX_MISSING", "ルートの <svg> に viewBox がありません。")
    else:
        parts = [fnum(p) for p in re.split(r"[,\s]+", vb.strip()) if p != ""]
        if len(parts) != 4 or any(p is None for p in parts):
            report.error("VIEWBOX_MALFORMED", f'viewBox="{vb}" の形式が不正です。')
        else:
            _, _, vb_w, vb_h = parts
            if svg.get("width") == "100%" and vb_w and abs(vb_w - 680) > 1:
                report.note(
                    "VIEWBOX_WIDTH",
                    f"viewBox の幅が既定の 680 ではなく {vb_w:g} です。"
                    f'width="100%" では全単位が 680/{vb_w:g} 倍に拡大され、'
                    "文字が書いたより大きく描画されます。意図したものですか？",
                )

    # --- ジオメトリの走査 ------------------------------------------------------
    max_y = 0.0
    max_x = 0.0
    for el in svg.iter():
        t = tag(el)
        # <animateMotion> を持つ要素はパスによって配置される。動きは自身の座標の上に
        # 重ねる transform なので、慣用的には原点に書かれる。その原点をジオメトリとして
        # 読むと、存在しないものを報告してしまう。
        if any(tag(c) == "animateMotion" for c in el):
            continue
        if t == "rect":
            x, y = fnum(el.get("x"), 0), fnum(el.get("y"), 0)
            w, h = fnum(el.get("width"), 0), fnum(el.get("height"), 0)
            max_y, max_x = max(max_y, y + h), max(max_x, x + w)
            if x < 0 or y < 0:
                report.error("NEG_COORD", f"<rect> が負の座標 ({x:g},{y:g}) にあります。")
        elif t == "circle":
            cx, cy = fnum(el.get("cx"), 0), fnum(el.get("cy"), 0)
            r = fnum(el.get("r"), 0)
            max_y, max_x = max(max_y, cy + r), max(max_x, cx + r)
            if cx - r < 0 or cy - r < 0:
                report.error("NEG_COORD", f"<circle> が ({cx:g},{cy:g}) で 0 より外にはみ出しています。")
        elif t == "text":
            y = fnum(el.get("y"), 0)
            x = fnum(el.get("x"), 0)
            max_y = max(max_y, y + 4)
            max_x = max(max_x, x)
            if x < 0 or y < 0:
                report.error("NEG_COORD", f"<text> が負の座標 ({x:g},{y:g}) にあります。")
        elif t in ("line",):
            for a in ("y1", "y2"):
                max_y = max(max_y, fnum(el.get(a), 0))
            for a in ("x1", "x2"):
                max_x = max(max_x, fnum(el.get(a), 0))
        elif t in ("path", "polyline", "polygon"):
            d = el.get("d") or el.get("points") or ""
            nums = [float(n) for n in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", d)]
            if nums:
                max_x = max([max_x] + nums[0::2])
                max_y = max([max_y] + nums[1::2])

    if vb_h:
        if max_y > vb_h + 0.5:
            report.error(
                "CLIPPED",
                f"内容が y={max_y:g} まで達していますが viewBox の高さは {vb_h:g} です。"
                f"下の {max_y - vb_h:.0f}px が見切れます。高さを "
                f"{max_y + 20:.0f} にしてください。",
            )
        elif vb_h - max_y > 60:
            report.warn(
                "DEAD_SPACE",
                f"最下端の要素（y={max_y:g}）の下に {vb_h - max_y:.0f}px の空白があります。"
                f"viewBox の高さを {max_y + 20:.0f} にしてください。",
            )
    if vb_w and max_x > vb_w + 0.5:
        report.error(
            "OVERFLOW_X",
            f"内容が x={max_x:g} まで達し、viewBox の幅 {vb_w:g} を超えています。",
        )

    # --- fill="none" のないコネクタの path -------------------------------------
    for el in svg.iter():
        if tag(el) not in ("path", "polyline"):
            continue
        fill = el.get("fill")
        raw_cls = (el.get("class") or "").split()
        cls = " ".join(raw_cls).lower()
        if any(c in fill_classes for c in raw_cls):
            continue
        has_stroke = bool(el.get("stroke") or "stroke" in (el.get("style") or ""))
        parent_fill = None
        p = parents.get(id(el))
        while p is not None and parent_fill is None:
            parent_fill = p.get("fill")
            p = parents.get(id(p))
        if fill is None and parent_fill is None:
            style = el.get("style") or ""
            if "fill" in style:
                continue
            looks_like_connector = has_stroke or any(h in cls for h in CONNECTOR_HINTS)
            if looks_like_connector:
                d = (el.get("d") or "")[:48]
                report.error(
                    "PATH_FILL",
                    f'<{tag(el)}> に fill="none" がありません（d="{d}..."）。'
                    "SVG の既定の fill は黒なので、線ではなく塗りつぶされた塊として"
                    "描画されます。",
                )

    # --- 文字のスタイル --------------------------------------------------------
    texts = []
    for el in svg.iter():
        if tag(el) != "text":
            continue
        texts.append(el)
        content = "".join(el.itertext()).strip()
        if not content:
            continue

        styled = el.get("fill") or el.get("class") or "fill" in (el.get("style") or "")
        if not styled and not inherited(parents.get(id(el)), parents, "fill"):
            report.error(
                "TEXT_UNSTYLED",
                f'<text> "{content[:34]}" に fill も class もありません。'
                "黒を継承し、ダークモードで消えます。",
            )

        size = fnum(el.get("font-size"))
        if size is not None and size < 11:
            report.error(
                "TEXT_TINY", f'<text> "{content[:34]}" は {size:g}px です。最小は 11px です。'
            )

        if content.isupper() and len(content) > 3 and content.isalpha():
            report.note(
                "TEXT_CAPS",
                f'<text> "{content[:34]}" がすべて大文字です。既定は文頭だけ大文字です。',
            )

    # --- 文字と、それを含む箱 ----------------------------------------------------
    boxes = rects_of(svg, parents)
    for el in texts:
        x, y = fnum(el.get("x")), fnum(el.get("y"))
        if x is None or y is None:
            continue
        width, size, longest = text_extent(el)
        if not longest:
            continue

        anchor = el.get("text-anchor", "start")
        if anchor == "middle":
            x0, x1 = x - width / 2, x + width / 2
        elif anchor == "end":
            x0, x1 = x - width, x
        else:
            x0, x1 = x, x + width

        if x0 < 0:
            report.error(
                "TEXT_OFF_CANVAS",
                f'<text anchor="{anchor}"> "{longest[:30]}" が x={x0:.0f} から始まり、'
                f"左端の外に出ています。推定幅 {width:.0f}px に対して x={x:g} です。",
            )

        # アンカー点を含む最小の rect
        container = None
        for b in boxes:
            if b["x"] <= x <= b["x"] + b["w"] and b["y"] <= y <= b["y"] + b["h"]:
                if container is None or b["w"] * b["h"] < container["w"] * container["h"]:
                    container = b
        if container and container["w"] < 560:  # 全幅の帯は対象外
            pad = 12
            if x0 < container["x"] + pad or x1 > container["x"] + container["w"] - pad:
                need = width + 24
                report.warn(
                    "TEXT_OVERFLOW",
                    f'"{longest[:30]}" は約 {width:.0f}px で、箱の幅は {container["w"]:g}px です。'
                    f"約 {need:.0f}px 必要です。ラベルを短くするか箱を広げてください。",
                )

        if size >= 13 and el.get("dominant-baseline") is None and container:
            report.warn(
                "TEXT_BASELINE",
                f'"{longest[:30]}" が dominant-baseline="central" のない箱の中にあります。'
                "約 4px 浮いて描画されます。",
            )

    # --- rect の重なり ----------------------------------------------------------
    def contains(a, b):
        return (
            a["x"] <= b["x"]
            and a["y"] <= b["y"]
            and a["x"] + a["w"] >= b["x"] + b["w"]
            and a["y"] + a["h"] >= b["y"] + b["h"]
        )

    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if ox > 1 and oy > 1 and not contains(a, b) and not contains(b, a):
                report.error(
                    "RECT_OVERLAP",
                    f"rect が {ox:.0f}x{oy:.0f}px 重なっています: "
                    f'({a["x"]:g},{a["y"]:g},{a["w"]:g},{a["h"]:g}) と '
                    f'({b["x"]:g},{b["y"]:g},{b["w"]:g},{b["h"]:g})。',
                )

    # --- 段の中の横の間隔 -------------------------------------------------------
    tiers = {}
    for b in boxes:
        if b["w"] > 400:
            continue
        tiers.setdefault(round(b["y"] / 4) * 4, []).append(b)
    for y, row in tiers.items():
        row.sort(key=lambda b: b["x"])
        for a, c in zip(row, row[1:]):
            gap = c["x"] - (a["x"] + a["w"])
            if 1 < gap < 20:
                report.warn(
                    "TIGHT_GAP",
                    f"y={y:g} の箱の間隔が {gap:.0f}px しかありません。最小は 20px です。",
                )

    # --- アニメーション ----------------------------------------------------------
    has_css_anim = "@keyframes" in style_text or "animation:" in style_text
    has_smil = any(
        tag(e) in ("animate", "animateTransform", "animateMotion") for e in svg.iter()
    )
    animated = has_css_anim or has_smil

    if not animated and not allow_static:
        report.error(
            "NO_MOTION",
            "アニメーションが見つかりません。動きが既定の出力です。この図の意味を担う"
            "パターン（エッジに沿った流れ、段階的な表示、状態の変化）を選んでください。"
            "意図的に静止させた SVG には --allow-static を付けてください。",
        )

    if animated and "prefers-reduced-motion" not in style_text:
        report.error(
            "MOTION_PREF",
            "アニメーションがあるのに prefers-reduced-motion のガードがありません。"
            "@media (prefers-reduced-motion: no-preference) の中で宣言してください。",
        )
    elif animated and "no-preference" not in style_text:
        report.warn(
            "MOTION_PREF_INVERTED",
            "動きがグローバルに宣言され、`reduce` で無効化されているようです。設定が"
            "未指定の読み手にはそのまま動きが届きます。代わりに "
            "@media (prefers-reduced-motion: no-preference) の中でアニメーションを"
            "宣言してください。",
        )

    # 動きを宣言していても動かないことがある。どの要素も持たない class に対する
    # キーフレームや、誰も定義していないキーフレームを指すアニメーション。NO_MOTION は
    # どちらも見つけられない。マークアップにはアニメーションがあり、ただ何もしないだけだから。
    if has_css_anim and not has_smil:
        used_classes = set()
        for el in svg.iter():
            used_classes.update((el.get("class") or "").split())
        kf_names = set(re.findall(r"@keyframes\s+([A-Za-z_][-\w]*)", style_text))
        animated_classes, opaque_selector, undefined = set(), False, set()
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style_text):
            decls = re.findall(r"(?:^|[;\s])animation(?:-name)?\s*:([^;]*)", body)
            if not decls:
                continue
            tokens = set(re.findall(r"[A-Za-z_][-\w]*", " ".join(decls)))
            if tokens and not (tokens & kf_names) and not (
                tokens & {"none", "inherit", "initial", "unset", "revert"}
            ):
                undefined.add(" ".join(d.strip() for d in decls))
            cls = re.findall(r"\.([A-Za-z_][-\w]*)", selector)
            if cls:
                animated_classes.update(cls)
            else:
                opaque_selector = True

        for value in sorted(undefined):
            report.error(
                "MOTION_UNDEFINED",
                f"`animation: {value}` が指す @keyframes が存在しないため、何も再生"
                "されません。キーフレームを定義するか名前を直してください。",
            )
        if animated_classes and not opaque_selector and not (
            animated_classes & used_classes
        ):
            report.error(
                "MOTION_INERT",
                "アニメーションが "
                + ", ".join("." + c for c in sorted(animated_classes))
                + " に宣言されていますが、その class を持つ要素がありません。図は"
                "静止しています。動きの対象となる要素に class を付けてください。",
            )

    # 決して現れない表示。`from` だけのキーフレームでは終端値が暗黙で、要素自身の
    # スタイルから解決される。だから `opacity: 0` も設定しているルールは 0 から 0 へ
    # アニメーションし、要素は永遠に見えない。他の検査ではこれを見つけられない。
    # アニメーションは走り、ただ何も描画しないだけだから。
    if has_css_anim:
        kf_bodies = {
            m.group(1): m.group(2)
            for m in re.finditer(
                r"@keyframes\s+([A-Za-z_][-\w]*)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}",
                style_text,
            )
        }
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style_text):
            if not re.search(r"(^|[;\s])opacity\s*:\s*0(\.0+)?\s*(;|$)", body):
                continue
            decls = re.findall(r"(?:^|[;\s])animation(?:-name)?\s*:([^;]*)", body)
            for name in set(re.findall(r"[A-Za-z_][-\w]*", " ".join(decls))) & set(kf_bodies):
                if not re.search(r"(to|100%)[^{}]*\{[^{}]*opacity", kf_bodies[name]):
                    report.error(
                        "REVEAL_STUCK",
                        f"`{selector.strip()}` が opacity 0 を設定しつつ @keyframes "
                        f"{name} を実行していますが、そのキーフレームに明示的な `to` が"
                        "ありません。暗黙の終端値は同じ 0 に解決されるため、要素は決して"
                        f"現れません。@keyframes {name} に明示的な `to {{ opacity: 1 }}` を"
                        "与えてください。",
                    )

    # 既定で動くということは、静止状態が要になるということ。スクリーンショット、
    # PDF 書き出し、動きの抑制設定を使う読み手は、マークアップどおりのものを受け取る。
    # 静止時に隠れていてアニメーションで現れる要素は、彼らに白紙を渡す。
    if animated:
        hidden_at_rest = re.compile(r"(^|[;\s])opacity\s*:\s*0(\.0+)?\s*(;|$)")
        for el in svg.iter():
            if tag(el) in ("svg", "defs", "style", "title", "desc", "marker"):
                continue
            op = fnum(el.get("opacity"))
            if (op is not None and op < 0.05) or el.get("visibility") == "hidden" or (
                el.get("style") and hidden_at_rest.search(el.get("style"))
            ):
                ident = el.get("id") or el.get("class") or ""
                report.error(
                    "STATIC_BLANK",
                    f'<{tag(el)}{" " + ident if ident else ""}> は静止時に見えず、'
                    "アニメーションだけが表示します。完成状態をマークアップに残し、"
                    "代わりに `from { opacity: 0 }` でアニメーションさせてください。",
                )
        for selector, body in re.findall(
            r"([^{}]+)\{([^{}]*)\}", resting_css(style_text)
        ):
            if hidden_at_rest.search(body):
                report.error(
                    "STATIC_BLANK",
                    f"`{selector.strip()}` が静止時に opacity 0 のため、動きが再生される"
                    "まで図が白紙です。`from { opacity: 0 }` でアニメーションさせ、"
                    "ルールには完成状態を持たせてください。",
                )

    banned = re.findall(r"\b(filter|box-shadow|backdrop-filter)\s*:", style_text)
    for b in set(banned):
        report.note("EFFECT", f"<style> に CSS `{b}` があります。効果は既定でオフです。")

    return {"max_y": max_y, "max_x": max_x, "viewbox": (vb_w, vb_h)}


def main():
    ap = argparse.ArgumentParser(description="生成した SVG を検証する。")
    ap.add_argument("path", help=".svg または .html ファイルのパス")
    ap.add_argument("--json", action="store_true", help="機械可読な出力")
    ap.add_argument("--strict", action="store_true", help="警告でも非ゼロ終了にする")
    ap.add_argument(
        "--allow-static",
        action="store_true",
        help="動きの検査を飛ばす（静止させる意図の SVG をデバッグするとき）",
    )
    args = ap.parse_args()

    try:
        with open(args.path, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        print(f"{args.path} を読めません: {exc}", file=sys.stderr)
        return 2

    svg_src = extract_svg(raw)
    if not svg_src:
        print(f"{args.path} に <svg> 要素が見つかりません", file=sys.stderr)
        return 2

    if len(re.findall(r"<svg\b", raw, re.I)) > 1:
        print("注: <svg> が複数見つかりました。最初のものを検証します。", file=sys.stderr)

    report = Report()
    check(svg_src, report, allow_static=args.allow_static)

    if args.json:
        print(
            json.dumps(
                {
                    "file": args.path,
                    "errors": report.errors,
                    "warnings": report.warnings,
                    "notes": report.notes,
                    "ok": not report.errors,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        for label, items in (
            ("ERROR", report.errors),
            ("WARN", report.warnings),
            ("NOTE", report.notes),
        ):
            for it in items:
                print(f"{label:5} [{it['code']}] {it['message']}")
        n_e, n_w, n_n = len(report.errors), len(report.warnings), len(report.notes)
        if not (n_e or n_w or n_n):
            print("問題なし: エラー、警告、注記はありません。")
        else:
            print(f"\nエラー {n_e} 件、警告 {n_w} 件、注記 {n_n} 件。")

    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
