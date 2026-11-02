#!/usr/bin/env python3
"""DADS に沿った HTML 文書かを検査する。

見るもの:
  構造     lang / title / h1 が 1 つ / 見出しレベルの飛び / alt / 表の th と scope /
           id の重複とリンク先の存在 / プレースホルダ {{…}} の残り / build.py 未実行
  部品     同梱していない dads- クラス・document.css にない doc- クラス・見出しの data-size
  文言     「こちら」等の曖昧なリンク文言 / 新規タブで開くことの明示 / JS なしの <button>
  CSS      （<style> の追加分と style 属性だけ。埋め込んだ DADS の CSS は見ない）
           パレット外の色 / 14px 未満の文字 / 400・700 以外のウェイト / イタリック /
           color と background を同じ規則で指定したときのコントラスト比 4.5:1

使い方:
    python3 check.py <html>
終了コード: エラーがあれば 1、警告だけなら 0。
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True  # スキルのフォルダに __pycache__ を作らない
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import COMMENT_RE, DOCUMENT_CSS, DADS_DIR, STYLES_RE, resolve_components  # noqa: E402

HEADING_SIZES = {"64", "57", "45", "36", "32", "28", "24", "20", "18", "16"}
VAGUE_LINK_TEXT = {"こちら", "ここ", "こちらをクリック", "ここをクリック", "詳細はこちら", "click here", "here", "リンク", "link"}
NAMED_COLORS = {
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "gray", "grey", "black", "white",
    "navy", "teal", "aqua", "lime", "maroon", "olive", "silver", "fuchsia", "brown", "gold", "cyan", "magenta",
}
COLOR_PROPS = re.compile(
    r"^(color|background(-color)?|border(-(top|right|bottom|left))?(-color)?|outline(-color)?|"
    r"fill|stroke|box-shadow|text-decoration(-color)?|caret-color|accent-color|column-rule(-color)?)$"
)


# ---------------------------------------------------------------- パレット

def load_tokens() -> dict[str, str]:
    css = (DADS_DIR / "global.css").read_text(encoding="utf-8")
    root = css[css.index(":root") : css.index("}", css.index(":root"))]
    tokens: dict[str, str] = {}
    for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", root):
        tokens[name] = " ".join(value.split())
    return tokens


def resolve(value: str, tokens: dict[str, str], depth: int = 0) -> str:
    if depth > 10:
        return value
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", value.strip())
    if not m:
        return value.strip()
    name, fallback = m.group(1), m.group(2)
    if name in tokens:
        return resolve(tokens[name], tokens, depth + 1)
    return resolve(fallback, tokens, depth + 1) if fallback else value.strip()


def parse_color(value: str) -> tuple[float, float, float, float] | None:
    v = value.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})", v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)", v)
    if m:
        a = m.group(4)
        alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return float(m.group(1)), float(m.group(2)), float(m.group(3)), alpha
    if v == "white":
        return 255, 255, 255, 1.0
    if v == "black":
        return 0, 0, 0, 1.0
    return None


def palette(tokens: dict[str, str]) -> set[tuple[int, int, int, float]]:
    out = set()
    for name, raw in tokens.items():
        if not name.startswith("--color-"):
            continue
        c = parse_color(resolve(raw, tokens))
        if c:
            out.add(norm(c))
    return out


def norm(c: tuple[float, float, float, float]) -> tuple[int, int, int, float]:
    return round(c[0]), round(c[1]), round(c[2]), round(c[3], 2)


def over_white(c: tuple[float, float, float, float]) -> tuple[float, float, float]:
    r, g, b, a = c
    return r * a + 255 * (1 - a), g * a + 255 * (1 - a), b * a + 255 * (1 - a)


def luminance(rgb: tuple[float, float, float]) -> float:
    def ch(x: float) -> float:
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(fg: tuple[float, float, float, float], bg: tuple[float, float, float, float]) -> float:
    bg_rgb = over_white(bg)
    r, g, b, a = fg
    fg_rgb = (r * a + bg_rgb[0] * (1 - a), g * a + bg_rgb[1] * (1 - a), b * a + bg_rgb[2] * (1 - a))
    l1, l2 = sorted((luminance(fg_rgb), luminance(bg_rgb)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# ---------------------------------------------------------------- 結果

class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, int, str]] = []

    def error(self, line: int, msg: str) -> None:
        self.items.append(("エラー", line, msg))

    def warn(self, line: int, msg: str) -> None:
        self.items.append(("警告", line, msg))

    @property
    def errors(self) -> int:
        return sum(1 for k, _, _ in self.items if k == "エラー")


# ---------------------------------------------------------------- 構造

class Walker(HTMLParser):
    def __init__(self, report: Report) -> None:
        super().__init__(convert_charrefs=True)
        self.r = report
        self.html_lang: str | None = None
        self.title_text = ""
        self.in_title = False
        self.h1 = 0
        self.last_level = 0
        self.ids: dict[str, int] = {}
        self.refs: list[tuple[int, str, str]] = []
        self.has_script = False
        self.buttons: list[int] = []
        self.tables: list[dict] = []
        self.links: list[dict] = []
        self.classes: dict[str, int] = {}
        self.inline_styles: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = {k: (v or "") for k, v in attrs_list}
        line = self.getpos()[0]
        for cls in attrs.get("class", "").split():
            self.classes.setdefault(cls, line)
        if "style" in attrs:
            self.inline_styles.append((line, attrs["style"]))
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.r.error(line, f'id="{attrs["id"]}" が重複している（{self.ids[attrs["id"]]} 行目にもある）')
            self.ids.setdefault(attrs["id"], line)
        for key in ("aria-labelledby", "aria-describedby", "aria-controls"):
            for ref in attrs.get(key, "").split():
                self.refs.append((line, key, ref))

        if tag == "html":
            self.html_lang = attrs.get("lang")
        elif tag == "title":
            self.in_title = True
        elif re.fullmatch(r"h[1-6]", tag):
            level = int(tag[1])
            if level == 1:
                self.h1 += 1
            if self.last_level and level > self.last_level + 1:
                self.r.error(line, f"見出しレベルが飛んでいる: h{self.last_level} の次に h{level}")
            if not self.last_level and level != 1:
                self.r.error(line, f"最初の見出しが h{level}。h1 から始める")
            self.last_level = level
        elif tag == "img":
            if "alt" not in attrs:
                self.r.error(line, '<img> に alt がない（装飾なら alt=""）')
            if re.match(r"https?://", attrs.get("src", "")):
                self.r.warn(line, f"外部画像を参照している: {attrs['src']}")
        elif tag == "script":
            self.has_script = True
            if attrs.get("src", "").startswith(("http://", "https://", "//")):
                self.r.warn(line, f"外部スクリプトを読み込んでいる: {attrs['src']}")
        elif tag == "link" and "stylesheet" in attrs.get("rel", ""):
            href = attrs.get("href", "")
            if href.startswith(("http://", "https://", "//")) and "fonts.googleapis.com" not in href:
                self.r.warn(line, f"外部 CSS を読み込んでいる: {href}")
        elif tag == "button":
            self.buttons.append(line)
        elif tag == "table":
            self.tables.append({"line": line, "th": 0, "th_no_scope": 0})
        elif tag == "th" and self.tables:
            self.tables[-1]["th"] += 1
            if "scope" not in attrs and "id" not in attrs:
                self.tables[-1]["th_no_scope"] += 1
        elif tag == "a":
            href = attrs.get("href", "")
            if href.startswith("#") and len(href) > 1:
                self.refs.append((line, "href", href[1:]))
            self.links.append({"line": line, "text": "", "attrs": attrs, "labels": []})
        if self.links and self.links[-1].get("open", True) and tag != "a":
            label = attrs.get("aria-label", "")
            if label:
                self.links[-1]["labels"].append(label)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "a" and self.links:
            self.links[-1]["open"] = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_text += data
        if self.links and self.links[-1].get("open", True):
            self.links[-1]["text"] += data


def check_structure(html: str, r: Report) -> Walker:
    w = Walker(r)
    # テンプレートの未使用部品（コメント内）は数えない。行番号は保つ
    w.feed(COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), html))
    w.close()

    if not w.html_lang:
        r.error(1, '<html> に lang がない（日本語文書なら lang="ja"）')
    elif not w.html_lang.lower().startswith("ja"):
        r.warn(1, f'<html lang="{w.html_lang}">。日本語文書なら "ja"')
    if not w.title_text.strip():
        r.error(1, "<title> が空")
    if w.h1 != 1:
        r.error(1, f"h1 は 1 つにする（現在 {w.h1} 個）")
    for t in w.tables:
        if t["th"] == 0:
            r.error(t["line"], "表に見出しセル <th> がない")
        elif t["th_no_scope"]:
            r.warn(t["line"], f'<th> {t["th_no_scope"]} 個に scope="col|row" がない')
    for line, key, ref in w.refs:
        if ref not in w.ids:
            r.error(line, f'{key} の参照先 id="{ref}" が存在しない')
    for link in w.links:
        text = " ".join(link["text"].split())
        attrs = link["attrs"]
        if text.lower() in VAGUE_LINK_TEXT and not attrs.get("aria-label"):
            r.warn(link["line"], f"リンク文言「{text}」は行き先が分からない。行き先の名前をリンクにする")
        if attrs.get("target") == "_blank":
            notice = " ".join(link["labels"]) + text + attrs.get("aria-label", "")
            if "新規タブ" not in notice and "新しいタブ" not in notice and "新しいウィンドウ" not in notice:
                r.warn(link["line"], "新規タブで開くリンクに、そのことの明示がない（dads-link__icon の aria-label など）")
    if w.buttons and not w.has_script:
        r.warn(w.buttons[0], f"<button> が {len(w.buttons)} 個あるが JS がない。押しても何も起きない。移動なら <a class=\"dads-button\">")
    no_comments = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), html)
    for m in re.finditer(r"\{\{[^}]*\}\}", no_comments):
        r.error(no_comments.count("\n", 0, m.start()) + 1, f"プレースホルダが残っている: {m.group(0)}")
    return w


def check_classes(w: Walker, r: Report) -> None:
    _, unknown = resolve_components(set(w.classes))
    for cls in unknown:
        r.error(w.classes[cls], f"同梱していない DADS クラス: {cls}")
    defined_doc = set(re.findall(r"\.(doc-[\w-]+)", DOCUMENT_CSS.read_text(encoding="utf-8")))
    for cls, line in w.classes.items():
        if cls.startswith("doc-") and cls not in defined_doc:
            r.error(line, f"document.css にないクラス: {cls}")


def check_heading_sizes(html: str, r: Report) -> None:
    for m in re.finditer(r"<(?:div|hgroup)[^>]*class=\"[^\"]*\bdads-heading\b[^\"]*\"[^>]*>", html):
        size = re.search(r'data-size="([^"]*)"', m.group(0))
        line = html.count("\n", 0, m.start()) + 1
        if not size:
            r.error(line, "dads-heading に data-size がない")
        elif size.group(1) not in HEADING_SIZES:
            r.error(line, f'dads-heading の data-size="{size.group(1)}" は無い値（{"/".join(sorted(HEADING_SIZES, key=int))}）')


def check_built(html: str, r: Report) -> None:
    m = STYLES_RE.search(html)
    if not m:
        r.error(1, "DADS:STYLES マーカーがない。テンプレートから写して build.py を実行する")
    elif "--color-primitive-blue-900" not in m.group(2):
        r.error(1, "DADS の CSS が埋め込まれていない。scripts/build.py を実行する")


# ---------------------------------------------------------------- CSS

def custom_css_blocks(html: str) -> list[tuple[int, str]]:
    """マーカーの外にある <style> の中身を (開始行, 本文) で返す。"""
    masked = STYLES_RE.sub(lambda m: "\n" * m.group(0).count("\n"), html)
    masked = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), masked)
    out = []
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", masked, re.S):
        out.append((masked.count("\n", 0, m.start(1)) + 1, m.group(1)))
    return out


def declarations(body: str) -> list[tuple[str, str]]:
    out = []
    for decl in body.split(";"):
        if ":" in decl:
            prop, value = decl.split(":", 1)
            out.append((prop.strip().lower(), value.strip()))
    return out


def check_declarations(line: int, where: str, decls, tokens, pal, r: Report) -> None:
    color = bg = None
    for prop, value in decls:
        v = value.replace("!important", "").strip()
        if COLOR_PROPS.match(prop):
            for lit in re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)", v):
                c = parse_color(lit)
                if c is None or norm(c) not in pal:
                    r.error(line, f"{where}: パレット外の色 {lit}（{prop}）。var(--color-…) を使う")
            for word in re.findall(r"\b[a-z]+\b", re.sub(r"var\([^)]*\)", "", v.lower())):
                if word in NAMED_COLORS and word not in {"white", "black"}:
                    r.error(line, f"{where}: 色名 {word} はパレット外（{prop}）。var(--color-…) を使う")
        if prop == "color":
            color = parse_color(resolve(v, tokens))
        if prop in ("background", "background-color"):
            bg = parse_color(resolve(v, tokens))
        if prop == "font-size":
            px = None
            m = re.fullmatch(r"([\d.]+)px", v)
            if m:
                px = float(m.group(1))
            m = re.fullmatch(r"([\d.]+)rem", v)
            if m:
                px = float(m.group(1)) * 16
            m = re.fullmatch(r"calc\(\s*([\d.]+)\s*/\s*16\s*\*\s*1rem\s*\)", v)
            if m:
                px = float(m.group(1))
            if px is not None and px < 14:
                r.error(line, f"{where}: 文字サイズ {v}（{px:g}px）は 14px 未満で使えない")
            elif px == 14:
                r.warn(line, f"{where}: 14px はフッターなど付随情報に限る")
        if prop == "font-weight" and v not in ("400", "700", "normal", "bold", "inherit"):
            r.warn(line, f"{where}: font-weight {v}。DADS のウェイトは 400 と 700 だけ")
        if prop == "font-style" and v == "italic":
            r.warn(line, f"{where}: 和文のイタリックは避ける")
    if color and bg:
        ratio = contrast(color, bg)
        if ratio < 4.5:
            r.error(line, f"{where}: 文字色と背景色のコントラスト比 {ratio:.2f}:1（4.5:1 以上が必要）")


def check_css(html: str, w: Walker, r: Report) -> None:
    tokens = load_tokens()
    pal = palette(tokens)
    for start, css in custom_css_blocks(html):
        css_nc = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_nc):
            line = start + css_nc.count("\n", 0, m.start(2))
            selector = " ".join(m.group(1).split())
            check_declarations(line, f"<style> {selector}", declarations(m.group(2)), tokens, pal, r)
    for line, style in w.inline_styles:
        check_declarations(line, "style 属性", declarations(style), tokens, pal, r)


# ---------------------------------------------------------------- main

def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    html = path.read_text(encoding="utf-8")
    r = Report()
    check_built(html, r)
    w = check_structure(html, r)
    check_classes(w, r)
    keep_lines = lambda m: "\n" * m.group(0).count("\n")  # noqa: E731
    check_heading_sizes(COMMENT_RE.sub(keep_lines, STYLES_RE.sub(keep_lines, html)), r)
    check_css(html, w, r)

    for kind, line, msg in sorted(r.items, key=lambda x: (x[0] != "エラー", x[1])):
        print(f"{kind} {path.name}:{line}: {msg}")
    warns = len(r.items) - r.errors
    print(f"\n結果: エラー {r.errors} 件 / 警告 {warns} 件")
    return 1 if r.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
