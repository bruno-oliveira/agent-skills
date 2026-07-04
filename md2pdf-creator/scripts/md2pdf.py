#!/usr/bin/env python3
"""md2pdf — turn Markdown into a branded, well-typeset PDF.

The "Constraint Dojo" document pipeline, generalized. Renders one or more
Markdown files into a single PDF with an optional dark branded cover, part
dividers, running footer, and page numbers. Uses weasyprint for layout and
a bundled font set for consistent typography.

Two ways to drive it:

  1. Quick single file:
       python md2pdf.py doc.md -o out.pdf --title "My Report" \
           --subtitle "A short description" --footer "MY REPORT"

  2. Spec-driven (multi-part books, covers, dividers) via JSON/YAML:
       python md2pdf.py --spec book.json -o book.pdf

See references/spec-format.md for the full spec schema, and
references/theming.md for palette and layout overrides.
"""
import argparse
import json
import os
import sys

try:
    import markdown
except ImportError:
    sys.exit("Missing dependency: pip install markdown --break-system-packages")
try:
    from weasyprint import HTML
except ImportError:
    sys.exit("Missing dependency: pip install weasyprint --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "assets", "fonts").replace(os.sep, "/")
MD_EXT = ["tables", "fenced_code", "sane_lists"]

# ---------------------------------------------------------------------------
# Default theme. Every value is overridable via the spec's "theme" object.
# ---------------------------------------------------------------------------
DEFAULT_THEME = {
    "page_size": "A4",
    "margin": "20mm 18mm 22mm",
    "base_pt": "10pt",
    "ink": "#14262B",          # body text
    "ink_strong": "#0C1A1E",   # headings
    "accent": "#0E6B5C",       # rules, links, code borders (the "fixes" green)
    "accent_warm": "#B5401F",  # the "breaks" divider kicker
    "cover_bg": "#0C1A1E",     # dark cover background
    "cover_ink": "#E8F0ED",
    "cover_title": "#FFFFFF",
    "cover_sub": "#B9CCC6",
    "cover_kicker": "#8FB5AB",
    "pill_a": "#F0906E",       # warm pill on the cover
    "pill_b": "#63C7B2",       # cool pill on the cover
    "muted": "#4B6360",        # captions, footer, part-divider prose
    "hairline": "#DDE6E3",
    "rule": "#CBD8D4",
    "panel": "#F0F4F3",        # code/table-header background
    "panel_code": "#E4EBE9",   # inline code background
    "quote_bg": "#DCEBE6",
    "font_display": "Bricolage Grotesque",
    "font_body": "IBM Plex Sans",
    "font_mono": "IBM Plex Mono",
}

FACE = """
@font-face {{ font-family: 'Bricolage Grotesque'; font-weight: 700; src: url('file://{F}/bricolage-grotesque-latin-700-normal.woff2'); }}
@font-face {{ font-family: 'Bricolage Grotesque'; font-weight: 800; src: url('file://{F}/bricolage-grotesque-latin-800-normal.woff2'); }}
@font-face {{ font-family: 'IBM Plex Sans'; font-weight: 400; src: url('file://{F}/ibm-plex-sans-latin-400-normal.woff2'); }}
@font-face {{ font-family: 'IBM Plex Sans'; font-style: italic; font-weight: 400; src: url('file://{F}/ibm-plex-sans-latin-400-italic.woff2'); }}
@font-face {{ font-family: 'IBM Plex Sans'; font-weight: 600; src: url('file://{F}/ibm-plex-sans-latin-600-normal.woff2'); }}
@font-face {{ font-family: 'IBM Plex Sans'; font-weight: 700; src: url('file://{F}/ibm-plex-sans-latin-700-normal.woff2'); }}
@font-face {{ font-family: 'IBM Plex Mono'; font-weight: 400; src: url('file://{F}/ibm-plex-mono-latin-400-normal.woff2'); }}
@font-face {{ font-family: 'IBM Plex Mono'; font-weight: 600; src: url('file://{F}/ibm-plex-mono-latin-600-normal.woff2'); }}
""".format(F=FONTS)


def build_css(theme, footer):
    t = dict(DEFAULT_THEME)
    t.update(theme or {})
    face = FACE if os.path.isdir(FONTS) else ""  # graceful fallback to system fonts
    return face + f"""
@page {{
  size: {t['page_size']};
  margin: {t['margin']};
  @bottom-left {{ content: '{footer}'; font-family: '{t['font_mono']}', monospace; font-size: 7pt; color: {t['muted']}; letter-spacing: 0.08em; }}
  @bottom-right {{ content: counter(page) ' / ' counter(pages); font-family: '{t['font_mono']}', monospace; font-size: 7pt; color: {t['muted']}; }}
}}
@page cover {{ margin: 0; background: {t['cover_bg']}; @bottom-left {{ content: none }} @bottom-right {{ content: none }} }}

html {{ font-size: {t['base_pt']}; }}
body {{ font-family: '{t['font_body']}', sans-serif; color: {t['ink']}; line-height: 1.55; }}

/* cover */
.cover {{ page: cover; height: 257mm; padding: 30mm 24mm; color: {t['cover_ink']}; page-break-after: always; position: relative; }}
.cover .kicker {{ font-family: '{t['font_mono']}', monospace; font-size: 8pt; letter-spacing: 0.2em; text-transform: uppercase; color: {t['cover_kicker']}; }}
.cover h1 {{ font-family: '{t['font_display']}', sans-serif; font-weight: 800; font-size: 33pt; line-height: 1.08; color: {t['cover_title']}; margin: 10mm 0 8mm; letter-spacing: -0.01em; }}
.cover .sub {{ font-size: 11.5pt; color: {t['cover_sub']}; max-width: 120mm; line-height: 1.6; }}
.cover .pills {{ margin-top: 18mm; font-family: '{t['font_mono']}', monospace; font-size: 8pt; }}
.cover .pill-a {{ color: {t['pill_a']}; border: 0.4mm solid {t['pill_a']}; border-radius: 2mm; padding: 2.4mm 4mm; display: inline-block; }}
.cover .vs {{ color: #7E9C95; margin: 0 3mm; }}
.cover .pill-b {{ color: {t['pill_b']}; border: 0.4mm solid {t['pill_b']}; border-radius: 2mm; padding: 2.4mm 4mm; display: inline-block; }}
.cover .foot {{ position: absolute; bottom: 22mm; left: 24mm; right: 24mm; font-family: '{t['font_mono']}', monospace; font-size: 7.5pt; color: #7E9C95; letter-spacing: 0.1em; }}

/* part divider */
.part {{ page-break-before: always; padding-top: 60mm; page-break-after: always; }}
.part .kicker {{ font-family: '{t['font_mono']}', monospace; font-size: 8pt; letter-spacing: 0.2em; text-transform: uppercase; color: {t['accent']}; }}
.part.warm .kicker {{ color: {t['accent_warm']}; }}
.part h1 {{ font-family: '{t['font_display']}', sans-serif; font-weight: 800; font-size: 26pt; margin: 5mm 0 6mm; letter-spacing: -0.01em; color: {t['ink_strong']}; }}
.part p {{ color: {t['muted']}; max-width: 125mm; font-size: 10.5pt; }}

/* body */
h1, h2, h3, h4 {{ font-family: '{t['font_display']}', sans-serif; font-weight: 700; color: {t['ink_strong']}; page-break-after: avoid; letter-spacing: -0.005em; }}
h1 {{ font-size: 19pt; margin: 8mm 0 3mm; }}
h2 {{ font-size: 15pt; margin: 9mm 0 3mm; padding-bottom: 1.6mm; border-bottom: 0.3mm solid {t['rule']}; }}
h3 {{ font-size: 11.5pt; margin: 6mm 0 2mm; }}
h4 {{ font-family: '{t['font_body']}', sans-serif; font-size: 10pt; margin: 5mm 0 1.5mm; }}
p, li {{ font-size: 9.5pt; }}
hr {{ border: none; border-top: 0.2mm solid {t['hairline']}; margin: 6mm 0; }}
blockquote {{ margin: 3mm 0; padding: 2.5mm 5mm; border-left: 0.8mm solid {t['accent']}; background: {t['quote_bg']}; font-size: 9.5pt; }}
blockquote p {{ margin: 1mm 0; }}
code {{ font-family: '{t['font_mono']}', monospace; font-size: 8.3pt; background: {t['panel_code']}; padding: 0 1mm; border-radius: 0.8mm; }}
pre {{
  font-family: '{t['font_mono']}', 'DejaVu Sans Mono', monospace; font-size: 7.3pt; line-height: 1.45;
  background: {t['panel']}; border: 0.2mm solid {t['rule']}; border-left: 0.8mm solid {t['accent']};
  border-radius: 1.5mm; padding: 3.5mm 4mm; white-space: pre; overflow: hidden;
}}
pre code {{ background: none; padding: 0; font-size: inherit; }}
table {{ border-collapse: collapse; width: 100%; margin: 3mm 0; font-size: 8.3pt; page-break-inside: auto; }}
th {{ font-family: '{t['font_mono']}', monospace; font-size: 6.8pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: {t['muted']}; text-align: left; padding: 2mm 2.5mm; border-bottom: 0.3mm solid {t['rule']}; background: {t['panel']}; }}
td {{ padding: 2mm 2.5mm; border-bottom: 0.2mm solid {t['hairline']}; vertical-align: top; }}
td:first-child {{ font-weight: 600; color: {t['ink_strong']}; }}
tr {{ page-break-inside: avoid; }}
strong {{ font-weight: 600; }}
a {{ color: {t['accent']}; text-decoration: none; }}
img {{ max-width: 100%; }}
"""


# ---------------------------------------------------------------------------
# HTML block builders
# ---------------------------------------------------------------------------
def md_to_html(text):
    return markdown.markdown(text, extensions=MD_EXT)


def cover_block(c):
    pills = ""
    if c.get("pill_a") or c.get("pill_b"):
        pills = (
            '<div class="pills">'
            f'<span class="pill-a">{c.get("pill_a","")}</span>'
            '<span class="vs">&#8596;</span>'
            f'<span class="pill-b">{c.get("pill_b","")}</span></div>'
        )
    sub = f'<p class="sub">{c["subtitle"]}</p>' if c.get("subtitle") else ""
    kicker = f'<div class="kicker">{c["kicker"]}</div>' if c.get("kicker") else ""
    foot = f'<div class="foot">{c["foot"]}</div>' if c.get("foot") else ""
    title = c.get("title", "").replace("\n", "<br>")
    return f'<div class="cover">{kicker}<h1>{title}</h1>{sub}{pills}{foot}</div>'


def part_block(p):
    cls = "part warm" if p.get("warm") else "part"
    kicker = f'<div class="kicker">{p["kicker"]}</div>' if p.get("kicker") else ""
    desc = f'<p>{p["description"]}</p>' if p.get("description") else ""
    return f'<div class="{cls}">{kicker}<h1>{p.get("title","")}</h1>{desc}</div>'


def read_md(path, base):
    full = path if os.path.isabs(path) else os.path.join(base, path)
    with open(full, encoding="utf-8") as f:
        return f.read()


def strip_leading_h1(text):
    """Drop a leading '# Title' line so a part divider can carry the title."""
    lines = text.splitlines()
    out, dropped = [], False
    for ln in lines:
        if not dropped and ln.startswith("# ") and not out:
            dropped = True
            continue
        out.append(ln)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def render_from_spec(spec, out_path, base_dir):
    theme = spec.get("theme", {})
    footer = spec.get("footer", "")
    body = ""

    if spec.get("cover"):
        body += cover_block(spec["cover"])

    # Optional raw HTML injected right after the cover (e.g. a table of contents)
    if spec.get("html_after_cover"):
        body += spec["html_after_cover"]

    for sec in spec.get("sections", []):
        if sec.get("divider"):
            body += part_block(sec["divider"])
        if sec.get("file"):
            text = read_md(sec["file"], base_dir)
            if sec.get("strip_h1"):
                text = strip_leading_h1(text)
            body += md_to_html(text)
        if sec.get("markdown"):
            body += md_to_html(sec["markdown"])
        if sec.get("html"):
            body += sec["html"]

    # Back-compat / simple path: a flat list of markdown files
    for f in spec.get("files", []):
        body += md_to_html(read_md(f, base_dir))

    css = build_css(theme, footer)
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<style>{css}</style></head><body>{body}</body></html>")
    HTML(string=html, base_url=base_dir).write_pdf(out_path)
    return out_path


def spec_from_args(args):
    """Build a minimal spec from CLI flags for the quick single-file path."""
    spec = {"footer": args.footer or "", "sections": []}
    if args.title:
        spec["cover"] = {
            "kicker": args.kicker or "",
            "title": args.title,
            "subtitle": args.subtitle or "",
            "pill_a": args.pill_a or "",
            "pill_b": args.pill_b or "",
            "foot": args.cover_foot or "",
        }
    for md_file in args.markdown:
        spec["sections"].append({"file": md_file})
    return spec


def load_spec(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
            return yaml.safe_load(raw)
        except ImportError:
            sys.exit("YAML spec needs pyyaml: pip install pyyaml --break-system-packages")
    return json.loads(raw)


def main():
    ap = argparse.ArgumentParser(
        description="Turn Markdown into a branded PDF (the Constraint Dojo pipeline).")
    ap.add_argument("markdown", nargs="*", help="One or more markdown files (quick path).")
    ap.add_argument("-o", "--output", required=True, help="Output PDF path.")
    ap.add_argument("--spec", help="JSON/YAML spec for multi-part documents.")
    ap.add_argument("--title", help="Cover title (enables the cover).")
    ap.add_argument("--subtitle", help="Cover subtitle / description.")
    ap.add_argument("--kicker", help="Small uppercase label above the cover title.")
    ap.add_argument("--pill-a", dest="pill_a", help="Left cover pill text.")
    ap.add_argument("--pill-b", dest="pill_b", help="Right cover pill text.")
    ap.add_argument("--cover-foot", dest="cover_foot", help="Small text at cover bottom.")
    ap.add_argument("--footer", help="Running footer text on every content page.")
    args = ap.parse_args()

    if args.spec:
        spec = load_spec(args.spec)
        base = os.path.dirname(os.path.abspath(args.spec))
    else:
        if not args.markdown:
            ap.error("Provide markdown file(s) or a --spec.")
        spec = spec_from_args(args)
        base = os.getcwd()

    out = os.path.abspath(args.output)
    render_from_spec(spec, out, base)

    # Report page count if pypdf is available.
    try:
        from pypdf import PdfReader
        n = len(PdfReader(out).pages)
        kb = os.path.getsize(out) // 1024
        print(f"wrote {out}: {n} pages, {kb} KB")
    except Exception:
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
