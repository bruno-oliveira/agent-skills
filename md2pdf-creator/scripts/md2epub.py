#!/usr/bin/env python3
"""md2epub — turn Markdown into a branded EPUB 3 for e-readers.

The e-reader sibling of md2pdf.py. It accepts the SAME spec files and the
same cover flags, so one spec can produce both a PDF and an EPUB:

  1. Quick single file:
       python md2epub.py doc.md -o out.epub --title "My Report" \
           --subtitle "A short description" --author "Jane Doe"

  2. Spec-driven (multi-part books, covers, dividers) via JSON/YAML:
       python md2epub.py --spec book.json -o book.epub

What it produces:
  - A raster cover image rendered with the SAME dark cover design as the PDF
    (weasyprint renders the cover HTML, then it's rasterized to PNG). If
    weasyprint or a rasterizer is unavailable it degrades gracefully to a
    styled XHTML title page only.
  - A styled title page and part-divider pages.
  - Content split into chapter XHTML files (reflowable, e-reader friendly),
    with a nested navigation TOC built from part dividers and headings.
  - An e-reader-safe stylesheet derived from the shared theme tokens, with
    the bundled fonts embedded (disable with --no-fonts).

EPUB-specific spec keys (all optional), under a top-level "epub" object:
  { "epub": { "author": "...", "language": "en", "publisher": "...",
              "identifier": "urn:isbn:...", "description": "..." } }

See references/epub-notes.md for e-reader quirks and validation tips.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid

try:
    import markdown
except ImportError:
    sys.exit("Missing dependency: pip install markdown --break-system-packages")
try:
    from ebooklib import epub
except ImportError:
    sys.exit("Missing dependency: pip install EbookLib --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "assets", "fonts")
MD_EXT = ["tables", "fenced_code", "sane_lists", "toc"]

# Kept in sync with DEFAULT_THEME in md2pdf.py (duplicated so this script
# doesn't import md2pdf, which hard-requires weasyprint at import time).
DEFAULT_THEME = {
    "ink": "#14262B",
    "ink_strong": "#0C1A1E",
    "accent": "#0E6B5C",
    "accent_warm": "#B5401F",
    "cover_bg": "#0C1A1E",
    "cover_ink": "#E8F0ED",
    "cover_title": "#FFFFFF",
    "cover_sub": "#B9CCC6",
    "cover_kicker": "#8FB5AB",
    "pill_a": "#F0906E",
    "pill_b": "#63C7B2",
    "muted": "#4B6360",
    "hairline": "#DDE6E3",
    "rule": "#CBD8D4",
    "panel": "#F0F4F3",
    "panel_code": "#E4EBE9",
    "quote_bg": "#DCEBE6",
    "font_display": "Bricolage Grotesque",
    "font_body": "IBM Plex Sans",
    "font_mono": "IBM Plex Mono",
}

FONT_FILES = [
    ("bricolage-grotesque-latin-700-normal.woff2", "Bricolage Grotesque", "700", "normal"),
    ("bricolage-grotesque-latin-800-normal.woff2", "Bricolage Grotesque", "800", "normal"),
    ("ibm-plex-sans-latin-400-normal.woff2", "IBM Plex Sans", "400", "normal"),
    ("ibm-plex-sans-latin-400-italic.woff2", "IBM Plex Sans", "400", "italic"),
    ("ibm-plex-sans-latin-600-normal.woff2", "IBM Plex Sans", "600", "normal"),
    ("ibm-plex-sans-latin-700-normal.woff2", "IBM Plex Sans", "700", "normal"),
    ("ibm-plex-mono-latin-400-normal.woff2", "IBM Plex Mono", "400", "normal"),
    ("ibm-plex-mono-latin-600-normal.woff2", "IBM Plex Mono", "600", "normal"),
]

H_RE = re.compile(r"<h([1-6])((?:\s[^>]*)?)>(.*?)</h\1>", re.S)
ID_RE = re.compile(r'id="([^"]*)"')
TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r'(<img[^>]*\ssrc=")([^"]+)(")', re.S)


# ---------------------------------------------------------------------------
# Stylesheet (e-reader safe: body color/background left to the reader so
# night mode works; every tinted panel pairs background WITH text color).
# ---------------------------------------------------------------------------
def build_css(theme, embed_fonts):
    t = dict(DEFAULT_THEME)
    t.update(theme or {})
    faces = ""
    if embed_fonts:
        for fname, family, weight, style in FONT_FILES:
            faces += (
                f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
                f"font-style: {style}; src: url('../fonts/{fname}'); }}\n"
            )
    disp = f"'{t['font_display']}', sans-serif"
    body = f"'{t['font_body']}', sans-serif"
    mono = f"'{t['font_mono']}', monospace"
    return faces + f"""
body {{ font-family: {body}; line-height: 1.55; margin: 0 4%; }}

h1, h2, h3, h4 {{ font-family: {disp}; font-weight: 700; line-height: 1.15; }}
h1 {{ font-size: 1.7em; margin: 1.2em 0 0.4em; }}
h2 {{ font-size: 1.35em; margin: 1.4em 0 0.4em; padding-bottom: 0.15em;
     border-bottom: 1px solid {t['rule']}; }}
h3 {{ font-size: 1.1em; margin: 1.2em 0 0.3em; }}
h4 {{ font-family: {body}; font-size: 1em; margin: 1em 0 0.2em; }}

hr {{ border: none; border-top: 1px solid {t['hairline']}; margin: 1.6em 0; }}
strong {{ font-weight: 600; }}
a {{ color: {t['accent']}; text-decoration: none; }}
img {{ max-width: 100%; }}

blockquote {{ margin: 0.8em 0; padding: 0.5em 1em;
  border-left: 3px solid {t['accent']};
  background: {t['quote_bg']}; color: {t['ink']}; }}
blockquote p {{ margin: 0.3em 0; }}

code {{ font-family: {mono}; font-size: 0.85em;
  background: {t['panel_code']}; color: {t['ink']};
  padding: 0 0.2em; border-radius: 2px; }}
pre {{ font-family: {mono}; font-size: 0.72em; line-height: 1.45;
  background: {t['panel']}; color: {t['ink']};
  border: 1px solid {t['rule']}; border-left: 3px solid {t['accent']};
  border-radius: 3px; padding: 0.8em 1em;
  white-space: pre-wrap; overflow-wrap: break-word; }}
pre code {{ background: none; padding: 0; font-size: inherit; }}

table {{ border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 0.8em; }}
th {{ font-family: {mono}; font-size: 0.85em; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em; text-align: left;
  color: {t['muted']}; background: {t['panel']};
  padding: 0.4em 0.5em; border-bottom: 2px solid {t['rule']}; }}
td {{ padding: 0.4em 0.5em; border-bottom: 1px solid {t['hairline']};
  vertical-align: top; }}
td:first-child {{ font-weight: 600; }}

/* dark branded pages (title page, part dividers): bg and ink always paired */
.titlepage {{ background: {t['cover_bg']}; color: {t['cover_ink']};
  padding: 12% 8%; text-align: left; }}
.titlepage .kicker {{ font-family: {mono}; font-size: 0.75em;
  letter-spacing: 0.2em; text-transform: uppercase; color: {t['cover_kicker']}; }}
.titlepage h1 {{ font-family: {disp}; font-weight: 800; font-size: 2.2em;
  color: {t['cover_title']}; margin: 0.6em 0 0.4em; border: none; }}
.titlepage .sub {{ color: {t['cover_sub']}; line-height: 1.6; }}
.titlepage .pills {{ margin-top: 2.5em; font-family: {mono}; font-size: 0.75em; }}
.titlepage .pill-a {{ color: {t['pill_a']}; border: 1px solid {t['pill_a']};
  border-radius: 4px; padding: 0.4em 0.8em; display: inline-block; }}
.titlepage .vs {{ color: #7E9C95; margin: 0 0.6em; }}
.titlepage .pill-b {{ color: {t['pill_b']}; border: 1px solid {t['pill_b']};
  border-radius: 4px; padding: 0.4em 0.8em; display: inline-block; }}
.titlepage .foot {{ margin-top: 4em; font-family: {mono}; font-size: 0.7em;
  color: #7E9C95; letter-spacing: 0.1em; }}

.part {{ background: {t['cover_bg']}; color: {t['cover_ink']}; padding: 18% 8%; }}
.part .kicker {{ font-family: {mono}; font-size: 0.75em; letter-spacing: 0.2em;
  text-transform: uppercase; color: {t['pill_b']}; }}
.part.warm .kicker {{ color: {t['pill_a']}; }}
.part h1 {{ font-family: {disp}; font-weight: 800; font-size: 1.9em;
  color: {t['cover_title']}; margin: 0.5em 0 0.5em; border: none; }}
.part p {{ color: {t['cover_sub']}; }}
"""


# ---------------------------------------------------------------------------
# Cover image: render the SAME cover design md2pdf uses, then rasterize.
# ---------------------------------------------------------------------------
def make_cover_png(cover, theme, target_w=1600, target_h=2560):
    """Return PNG bytes of the branded cover, or None if tooling is missing."""
    try:
        from weasyprint import HTML
    except ImportError:
        return None

    t = dict(DEFAULT_THEME)
    t.update(theme or {})
    w_css, h_css = target_w // 2, target_h // 2  # CSS px; rasterized at 2x
    faces = ""
    if os.path.isdir(FONTS):
        fdir = FONTS.replace(os.sep, "/")
        for fname, family, weight, style in FONT_FILES:
            faces += (
                f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
                f"font-style: {style}; src: url('file://{fdir}/{fname}'); }}\n"
            )
    pills = ""
    if cover.get("pill_a") or cover.get("pill_b"):
        pills = (
            '<div class="pills">'
            f'<span class="pa">{cover.get("pill_a", "")}</span>'
            '<span class="vs">&#8596;</span>'
            f'<span class="pb">{cover.get("pill_b", "")}</span></div>'
        )
    title = cover.get("title", "").replace("\\n", "<br/>").replace("\n", "<br/>")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
{faces}
@page {{ size: {w_css}px {h_css}px; margin: 0; }}
body {{ margin: 0; }}
.cover {{ width: {w_css}px; height: {h_css}px; box-sizing: border-box;
  background: {t['cover_bg']}; color: {t['cover_ink']};
  padding: 100px 64px; position: relative;
  font-family: '{t['font_body']}', sans-serif; }}
.kicker {{ font-family: '{t['font_mono']}', monospace; font-size: 17px;
  letter-spacing: 0.2em; text-transform: uppercase; color: {t['cover_kicker']}; }}
h1 {{ font-family: '{t['font_display']}', sans-serif; font-weight: 800;
  font-size: 64px; line-height: 1.08; color: {t['cover_title']};
  margin: 40px 0 32px; letter-spacing: -0.01em; }}
.sub {{ font-size: 23px; color: {t['cover_sub']}; line-height: 1.6; }}
.pills {{ margin-top: 72px; font-family: '{t['font_mono']}', monospace; font-size: 16px; }}
.pa {{ color: {t['pill_a']}; border: 2px solid {t['pill_a']}; border-radius: 8px;
  padding: 10px 16px; display: inline-block; }}
.vs {{ color: #7E9C95; margin: 0 12px; }}
.pb {{ color: {t['pill_b']}; border: 2px solid {t['pill_b']}; border-radius: 8px;
  padding: 10px 16px; display: inline-block; }}
.foot {{ position: absolute; bottom: 72px; left: 64px; right: 64px;
  font-family: '{t['font_mono']}', monospace; font-size: 15px;
  color: #7E9C95; letter-spacing: 0.1em; }}
</style></head><body><div class="cover">
{f'<div class="kicker">{cover["kicker"]}</div>' if cover.get("kicker") else ''}
<h1>{title}</h1>
{f'<p class="sub">{cover["subtitle"]}</p>' if cover.get("subtitle") else ''}
{pills}
{f'<div class="foot">{cover["foot"]}</div>' if cover.get("foot") else ''}
</div></body></html>"""

    with tempfile.TemporaryDirectory() as td:
        pdf_path = os.path.join(td, "cover.pdf")
        HTML(string=html).write_pdf(pdf_path)
        png = _rasterize_first_page(pdf_path, td, target_w)
        return png


def _rasterize_first_page(pdf_path, workdir, target_w):
    """PDF page 1 -> PNG bytes via pypdfium2, falling back to pdftoppm."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf_path)
        page = doc[0]
        scale = target_w / page.get_width()
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        out = os.path.join(workdir, "cover.png")
        pil.save(out)
        bitmap.close()
        page.close()
        doc.close()
        with open(out, "rb") as f:
            return f.read()
    except Exception:
        pass
    try:
        dpi = int(target_w / (8.3333 / 2))  # cover page is target_w/2 CSS px wide
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", "1", "-l", "1",
             pdf_path, os.path.join(workdir, "cov")],
            check=True, capture_output=True)
        hits = sorted(glob.glob(os.path.join(workdir, "cov*.png")))
        if hits:
            with open(hits[0], "rb") as f:
                return f.read()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Markdown -> chapters
# ---------------------------------------------------------------------------
def md_to_html(text):
    return markdown.markdown(text, extensions=MD_EXT, output_format="xhtml")


def parse_headings(html):
    out = []
    for m in H_RE.finditer(html):
        level = int(m.group(1))
        idm = ID_RE.search(m.group(2) or "")
        text = TAG_RE.sub("", m.group(3)).strip()
        out.append({"level": level, "id": idm.group(1) if idm else "",
                    "text": text, "start": m.start()})
    return out


def split_chapters(html, split_level=None, fallback_title="Content"):
    """Split converted HTML into (title, html, sub_heads) chunks.

    split_level None = auto: split at the shallowest heading level present
    (h1 if any, else h2). split_level 0 = never split.
    """
    heads = parse_headings(html)
    if split_level is None:
        levels = [h["level"] for h in heads if h["level"] <= 2]
        split_level = min(levels) if levels else 0
    cuts = [h for h in heads if h["level"] == split_level] if split_level else []
    if len(cuts) < 2 and not (cuts and cuts[0]["start"] > 200):
        title = heads[0]["text"] if heads else fallback_title
        subs = [h for h in heads[1:] if h["level"] == (heads[0]["level"] + 1)] if heads else []
        return [(title or fallback_title, html, subs)]

    chunks = []
    if cuts[0]["start"] > 0 and html[: cuts[0]["start"]].strip():
        pre = html[: cuts[0]["start"]]
        chunks.append((fallback_title, pre, []))
    for i, cut in enumerate(cuts):
        end = cuts[i + 1]["start"] if i + 1 < len(cuts) else len(html)
        seg = html[cut["start"]: end]
        subs = [h for h in parse_headings(seg) if h["level"] == split_level + 1]
        chunks.append((cut["text"] or fallback_title, seg, subs))
    return chunks


def strip_leading_h1(text):
    lines, out, dropped = text.splitlines(), [], False
    for ln in lines:
        if not dropped and ln.startswith("# ") and not out:
            dropped = True
            continue
        out.append(ln)
    return "\n".join(out)


def read_md(path, base):
    full = path if os.path.isabs(path) else os.path.join(base, path)
    with open(full, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------
def titlepage_html(c):
    pills = ""
    if c.get("pill_a") or c.get("pill_b"):
        pills = ('<div class="pills">'
                 f'<span class="pill-a">{c.get("pill_a", "")}</span>'
                 '<span class="vs">&#8596;</span>'
                 f'<span class="pill-b">{c.get("pill_b", "")}</span></div>')
    title = c.get("title", "").replace("\\n", "<br/>").replace("\n", "<br/>")
    kicker = f'<div class="kicker">{c["kicker"]}</div>' if c.get("kicker") else ""
    sub = f'<p class="sub">{c["subtitle"]}</p>' if c.get("subtitle") else ""
    foot = f'<div class="foot">{c["foot"]}</div>' if c.get("foot") else ""
    return f'<div class="titlepage">{kicker}<h1>{title}</h1>{sub}{pills}{foot}</div>'


def part_html(p):
    cls = "part warm" if p.get("warm") else "part"
    kicker = f'<div class="kicker">{p["kicker"]}</div>' if p.get("kicker") else ""
    desc = f'<p>{p["description"]}</p>' if p.get("description") else ""
    return f'<div class="{cls}">{kicker}<h1>{p.get("title", "")}</h1>{desc}</div>'


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
MEDIA = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp"}


def _collect_images(html, base_dir, book, registry):
    """Move local <img> targets into the EPUB and rewrite their src."""
    def repl(m):
        src = m.group(2)
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        full = src if os.path.isabs(src) else os.path.join(base_dir, src)
        if not os.path.isfile(full):
            return m.group(0)
        if full not in registry:
            ext = os.path.splitext(full)[1].lower()
            name = f"images/img{len(registry):03d}{ext}"
            with open(full, "rb") as f:
                item = epub.EpubItem(uid=f"img{len(registry):03d}", file_name=name,
                                     media_type=MEDIA.get(ext, "image/png"),
                                     content=f.read())
            book.add_item(item)
            registry[full] = name
        return m.group(1) + registry[full] + m.group(3)
    return IMG_RE.sub(repl, html)


def build_epub(spec, out_path, base_dir, args):
    theme = spec.get("theme", {})
    meta = spec.get("epub", {})
    cover = spec.get("cover", {})
    lang = args.lang or meta.get("language", "en")

    title = (cover.get("title", "") or meta.get("title", "") or "Untitled").replace("\\n", " ").replace("\n", " ")
    author = args.author or meta.get("author", "")

    book = epub.EpubBook()
    book.set_identifier(meta.get("identifier", f"urn:uuid:{uuid.uuid4()}"))
    book.set_title(title)
    book.set_language(lang)
    if author:
        book.add_author(author)
    desc = meta.get("description", cover.get("subtitle", ""))
    if desc:
        book.add_metadata("DC", "description", desc)
    if meta.get("publisher"):
        book.add_metadata("DC", "publisher", meta["publisher"])

    css = epub.EpubItem(uid="style", file_name="style/epub.css",
                        media_type="text/css",
                        content=build_css(theme, not args.no_fonts))
    book.add_item(css)

    if not args.no_fonts and os.path.isdir(FONTS):
        for i, (fname, _, _, _) in enumerate(FONT_FILES):
            fpath = os.path.join(FONTS, fname)
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    book.add_item(epub.EpubItem(
                        uid=f"font{i}", file_name=f"fonts/{fname}",
                        media_type="font/woff2", content=f.read()))

    spine, toc, img_registry = [], [], {}
    has_cover_img = False
    if cover and not args.no_cover:
        png = make_cover_png(cover, theme)
        if png:
            book.set_cover("cover.png", png)
            spine.append("cover")
            has_cover_img = True
        else:
            print("note: weasyprint/rasterizer unavailable — skipping raster "
                  "cover, keeping the styled title page.", file=sys.stderr)

    def add_page(uid, fname, title_, body):
        page = epub.EpubHtml(title=title_, file_name=fname, lang=lang)
        page.content = _collect_images(body, base_dir, book, img_registry)
        page.add_item(css)
        book.add_item(page)
        spine.append(page)
        return page

    if cover:
        tp = add_page("titlepage", "titlepage.xhtml", title, titlepage_html(cover))
        toc.append(epub.Link("titlepage.xhtml", "Title Page", "titlepage"))

    nav = epub.EpubNav()
    nav.add_item(css)
    book.add_item(nav)
    book.add_item(epub.EpubNcx())
    spine.append(nav)

    chap_n, part_n = 0, 0
    sections = list(spec.get("sections", []))
    for f in spec.get("files", []):
        sections.append({"file": f})

    for sec in sections:
        part_entry = None
        if sec.get("divider"):
            part_n += 1
            d = sec["divider"]
            fname = f"part{part_n:02d}.xhtml"
            add_page(f"part{part_n}", fname, d.get("title", f"Part {part_n}"),
                     part_html(d))
            part_entry = (epub.Section(d.get("title", f"Part {part_n}"), href=fname), [])
            toc.append(part_entry)

        text = ""
        if sec.get("file"):
            text = read_md(sec["file"], base_dir)
            if sec.get("strip_h1"):
                text = strip_leading_h1(text)
        if sec.get("markdown"):
            text = (text + "\n\n" + sec["markdown"]) if text else sec["markdown"]

        chapters = []
        if text.strip():
            html = md_to_html(text)
            fallback = (sec.get("divider") or {}).get("title") or "Content"
            chapters = split_chapters(html, args.split, fallback_title=fallback)
        if sec.get("html"):
            chapters.append(("", sec["html"], []))

        for ctitle, chtml, subs in chapters:
            chap_n += 1
            fname = f"chap{chap_n:03d}.xhtml"
            add_page(f"chap{chap_n}", fname, ctitle or f"Chapter {chap_n}", chtml)
            if not ctitle:
                continue
            sub_links = [epub.Link(f"{fname}#{h['id']}", h["text"],
                                   f"chap{chap_n}-{h['id']}")
                         for h in subs if h.get("id")]
            entry = ((epub.Section(ctitle, href=fname), sub_links)
                     if sub_links else epub.Link(fname, ctitle, f"chap{chap_n}"))
            (part_entry[1] if part_entry else toc).append(entry)

    book.toc = toc
    book.spine = spine
    epub.write_epub(out_path, book)
    kb = os.path.getsize(out_path) // 1024
    print(f"wrote {out_path}: {chap_n} chapters, "
          f"{'raster cover, ' if has_cover_img else ''}{kb} KB")
    return out_path


# ---------------------------------------------------------------------------
# CLI (mirrors md2pdf.py, plus EPUB metadata flags)
# ---------------------------------------------------------------------------
def spec_from_args(args):
    spec = {"sections": []}
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
        description="Turn Markdown into a branded EPUB (md2pdf's e-reader sibling).")
    ap.add_argument("markdown", nargs="*", help="One or more markdown files (quick path).")
    ap.add_argument("-o", "--output", required=True, help="Output EPUB path.")
    ap.add_argument("--spec", help="JSON/YAML spec (same format as md2pdf).")
    ap.add_argument("--title", help="Cover/book title (enables cover + title page).")
    ap.add_argument("--subtitle", help="Cover subtitle / description.")
    ap.add_argument("--kicker", help="Small uppercase label above the cover title.")
    ap.add_argument("--pill-a", dest="pill_a", help="Left cover pill text.")
    ap.add_argument("--pill-b", dest="pill_b", help="Right cover pill text.")
    ap.add_argument("--cover-foot", dest="cover_foot", help="Small text at cover bottom.")
    ap.add_argument("--author", help="Author metadata (shows in e-reader libraries).")
    ap.add_argument("--lang", help="Language code (default: en, or spec epub.language).")
    ap.add_argument("--split", type=int, default=None,
                    help="Chapter split heading level: 1 or 2. 0 = never split. "
                         "Default: auto (h1 if present, else h2).")
    ap.add_argument("--no-fonts", action="store_true",
                    help="Skip embedding the bundled fonts (smaller file; "
                         "reader default fonts).")
    ap.add_argument("--no-cover", action="store_true",
                    help="Skip the raster cover image (title page only).")
    args = ap.parse_args()

    if args.spec:
        spec = load_spec(args.spec)
        base = os.path.dirname(os.path.abspath(args.spec))
    else:
        if not args.markdown:
            ap.error("Provide markdown file(s) or a --spec.")
        spec = spec_from_args(args)
        base = os.getcwd()

    build_epub(spec, os.path.abspath(args.output), base, args)


if __name__ == "__main__":
    main()
