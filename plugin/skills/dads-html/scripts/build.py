#!/usr/bin/env python3
"""DADS の CSS を HTML に埋め込む。

HTML 内の `dads-<コンポーネント>` クラスを拾い、使われているコンポーネントの CSS だけを
global.css（トークン・フォーカス・テキストスタイル）と document.css（文書レイアウト層）と一緒に
`<!-- DADS:STYLES:BEGIN -->` 〜 `<!-- DADS:STYLES:END -->` の間へ書き込む。
フォント読み込みは `<!-- DADS:FONTS:BEGIN -->` 〜 `<!-- DADS:FONTS:END -->` の間に入れる。

マーカーの間は毎回作り直すので、本文を直したら何度でも再実行してよい（冪等）。

使い方:
    python3 build.py <html> [-o <出力先>] [--no-webfont]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DADS_DIR = SKILL_DIR / "assets" / "dads"
COMPONENT_DIR = DADS_DIR / "components"
DOCUMENT_CSS = SKILL_DIR / "assets" / "document.css"

# 依存関係で後に来るべきもの（notification-banner は button を内包しうる）を後ろに置く
COMPONENT_ORDER = [
    "link",
    "list",
    "heading",
    "divider",
    "blockquote",
    "description-list",
    "table",
    "chip-label",
    "button",
    "utility-link",
    "breadcrumb",
    "toc",
    "accordion",
    "disclosure",
    "resource-list",
    "notification-banner",
]

# 他のコンポーネントの内側で必ず使われるもの
IMPLIED = {
    "toc": {"list", "link"},
}

WEBFONT = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700'
    '&family=Noto+Sans+Mono:wght@400;700&display=swap" rel="stylesheet">\n'
)

STYLES_RE = re.compile(r"(<!-- DADS:STYLES:BEGIN -->)(.*?)(<!-- DADS:STYLES:END -->)", re.S)
FONTS_RE = re.compile(r"(<!-- DADS:FONTS:BEGIN -->)(.*?)(<!-- DADS:FONTS:END -->)", re.S)
CLASS_RE = re.compile(r"""\bclass\s*=\s*(["'])(.*?)\1""", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def license_banner() -> str:
    text = (DADS_DIR / "LICENSE").read_text(encoding="utf-8").strip()
    return (
        "/*!\n"
        " * デジタル庁デザインシステム（DADS）の CSS を含む\n"
        " * https://github.com/digital-go-jp/design-system-example-components-html\n *\n"
        + "\n".join(f" * {line}".rstrip() for line in text.splitlines())
        + "\n */\n"
    )


def used_classes(html: str) -> set[str]:
    # マーカー内（前回の埋め込み）とコメント（テンプレートの未使用部品）は数えない
    body = STYLES_RE.sub("", html)
    body = COMMENT_RE.sub("", body)
    classes: set[str] = set()
    for _, value in CLASS_RE.findall(body):
        classes.update(value.split())
    return classes


def resolve_components(classes: set[str]) -> tuple[list[str], list[str]]:
    available = {p.stem for p in COMPONENT_DIR.glob("*.css")}
    wanted: set[str] = set()
    unknown: list[str] = []
    for cls in sorted(classes):
        if not cls.startswith("dads-") or cls.startswith("dads-u-"):
            continue
        name = cls[len("dads-"):].split("__", 1)[0]
        if name in available:
            wanted.add(name)
        else:
            unknown.append(cls)
    for name in list(wanted):
        wanted |= IMPLIED.get(name, set())
    ordered = [c for c in COMPONENT_ORDER if c in wanted]
    ordered += sorted(wanted - set(ordered))
    return ordered, unknown


def build(html: str, webfont: bool) -> tuple[str, list[str], list[str]]:
    if not STYLES_RE.search(html):
        raise SystemExit(
            "エラー: <!-- DADS:STYLES:BEGIN --> / <!-- DADS:STYLES:END --> が見つからない。"
            " assets/template.html の <head> からマーカーを写してから再実行する。"
        )
    components, unknown = resolve_components(used_classes(html))

    parts = [license_banner(), (DADS_DIR / "global.css").read_text(encoding="utf-8")]
    for name in components:
        css = (COMPONENT_DIR / f"{name}.css").read_text(encoding="utf-8")
        parts.append(f"/* ---- dads: {name} ---- */\n{css}")
    parts.append(DOCUMENT_CSS.read_text(encoding="utf-8"))
    style = "\n<style>\n" + "\n".join(p.strip() + "\n" for p in parts) + "</style>\n"

    out = STYLES_RE.sub(lambda m: m.group(1) + style + m.group(3), html, count=1)
    if FONTS_RE.search(out):
        fonts = "\n" + WEBFONT if webfont else "\n"
        out = FONTS_RE.sub(lambda m: m.group(1) + fonts + m.group(3), out, count=1)
    return out, components, unknown


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="出力先（省略時は入力を上書き）")
    ap.add_argument(
        "--no-webfont",
        action="store_true",
        help="Google Fonts を読み込まない（完全オフライン。端末のフォントで表示される）",
    )
    args = ap.parse_args()

    html = args.html.read_text(encoding="utf-8")
    out, components, unknown = build(html, webfont=not args.no_webfont)
    dest = args.output or args.html
    dest.write_text(out, encoding="utf-8")

    print(f"書き出し: {dest}")
    print(f"埋め込んだコンポーネント: {', '.join(components) or '(なし)'}")
    if unknown:
        print("警告: 同梱していない dads- クラス（スタイルが当たらない）:", file=sys.stderr)
        for cls in unknown:
            print(f"  - {cls}", file=sys.stderr)
        print("  references/components.md にある部品へ置き換えるか、document.css のクラスを使う。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
