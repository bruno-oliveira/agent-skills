---
name: md2pdf-creator
description: Turn Markdown into a polished, branded PDF and/or EPUB with a dark cover, part dividers, and refined typography (Bricolage Grotesque + IBM Plex). PDFs get a running footer and page numbers; EPUBs get a raster cover, chapter navigation, and e-reader-safe styling. Use this whenever the user wants a good-looking PDF or EPUB from Markdown or prose content — reports, whitepapers, guides, references, design docs, essays, ebooks, one-pagers, documentation, or multi-part "books" — and especially when they mention a branded PDF, a cover page, a nicely typeset document, a professional-looking export, an e-reader, Kindle, Kobo, "read on the go", or ask to "make this a PDF/EPUB/ebook." Prefer this over ad-hoc reportlab, pandoc, or plain HTML-to-PDF whenever visual quality, consistent branding, or a cover/part structure matters. One spec file can produce both formats. Also use it to re-theme an existing document's colors or fonts.
---

# md2pdf-creator

Turn Markdown into a professional, branded **PDF** and/or **EPUB** from one pipeline. The PDF has a dark cover page, optional part dividers, a running footer with page numbers, code blocks, tables, blockquotes, and clean editorial typography — the same template that produced "The Constraint Dojo" collection. The EPUB is its e-reader sibling: same cover design (rendered as a raster cover image), same theme, reflowable chapters with nested navigation, built for Kindle/Kobo/Apple Books.

## When to use this

Reach for this skill whenever the deliverable is a **PDF or EPUB that should look good**: reports, whitepapers, technical references, design docs, guides, essays, ebooks, one-pagers, or multi-part books assembled from several Markdown files. If the user hands you Markdown (or asks you to write prose and package it), and quality or branding matters, use this rather than reportlab, pandoc, or bare HTML. If they want to read it "on the go" or on an e-reader, produce the EPUB (or both formats — same spec, two commands).

## Requirements

Install what the target format needs (idempotent):

```bash
# PDF
pip install markdown weasyprint pypdf --break-system-packages
# EPUB (weasyprint is optional here but recommended — it renders the cover image)
pip install markdown EbookLib weasyprint --break-system-packages
```

Fonts are bundled under `assets/fonts/`. If they're missing the engine falls back to system fonts automatically — but bundled fonts give the intended look, so keep them.

## The two ways to drive it

### 1. Quick single document (most common)

Write or obtain a Markdown file, then run the engine with cover flags:

```bash
python3 scripts/md2pdf.py report.md -o /mnt/user-data/outputs/report.pdf \
  --kicker "QUARTERLY REVIEW" \
  --title "Q3 Performance Report" \
  --subtitle "Revenue, growth, and the road to Q4." \
  --footer "Q3 REPORT · ACME" \
  --pill-a "TARGET: 20% GROWTH" --pill-b "ACHIEVED: 24%"
```

- `--title` enables the dark cover page. Use `\n` in the title for a line break.
- `--kicker` is the small uppercase label above the title.
- `--subtitle` is the descriptive paragraph under the title.
- `--pill-a` / `--pill-b` render two small outlined "pills" with a `↔` between them — great for a tension, a before/after, or a headline metric. Omit both to hide them.
- `--footer` is the running footer text repeated on every content page (page numbers are added automatically on the right).
- Omit all cover flags to render a plain (coverless) document.

You can pass **multiple markdown files** and they'll be concatenated in order:

```bash
python3 scripts/md2pdf.py intro.md body.md appendix.md -o out.pdf --title "My Guide"
```

### 2. Multi-part book with a spec (covers, dividers, TOC)

For anything with **part dividers**, a **table of contents**, or per-section control, write a small JSON (or YAML) spec and pass `--spec`. This is how you build a real "book" like the reference document. See `references/spec-format.md` for the full schema. Minimal shape:

```json
{
  "footer": "MY BOOK · 2026",
  "cover": {
    "kicker": "A FIELD GUIDE",
    "title": "The Book\nof Things",
    "subtitle": "Everything worth knowing, in one place.",
    "pill_a": "PART ONE", "pill_b": "PART TWO",
    "foot": "FIRST EDITION"
  },
  "sections": [
    { "divider": { "kicker": "Part I", "title": "Foundations",
                   "description": "Where it all begins." },
      "file": "part1.md", "strip_h1": true },
    { "divider": { "kicker": "Part II", "title": "Practice", "warm": true },
      "file": "part2.md", "strip_h1": true }
  ]
}
```

Then:

```bash
python3 scripts/md2pdf.py --spec book.json -o /mnt/user-data/outputs/book.pdf
```

## EPUB output for e-readers

`scripts/md2epub.py` accepts the **same spec files and the same cover flags** as `md2pdf.py`, so producing both formats is two commands on one spec:

```bash
python3 scripts/md2pdf.py  --spec book.json -o /mnt/user-data/outputs/book.pdf
python3 scripts/md2epub.py --spec book.json -o /mnt/user-data/outputs/book.epub --author "Jane Doe"
```

Quick single-document path (mirrors the PDF flags, plus metadata):

```bash
python3 scripts/md2epub.py guide.md -o /mnt/user-data/outputs/guide.epub \
  --kicker "A FIELD GUIDE" --title "The Guide" \
  --subtitle "Everything worth knowing." \
  --pill-a "THEORY" --pill-b "PRACTICE" \
  --author "Jane Doe" --lang en
```

What you get and how it differs from the PDF:

- **Cover**: the identical dark cover design, rendered via weasyprint and rasterized to a 1600×2560 PNG cover image (what e-reader libraries display). Plus a styled XHTML title page. If weasyprint is missing, it degrades to the title page only.
- **Chapters**: content is split into chapter files at the shallowest heading level (h1 if present, else h2 — override with `--split 1|2|0`), and the reader's table of contents nests chapters under part dividers automatically. No hand-written TOC needed, unlike the PDF.
- **No running footer / page numbers** — e-readers paginate dynamically, so the spec's `footer` is ignored for EPUB.
- **Fonts**: the bundled woff2 set is embedded (readers may still let users override; disable with `--no-fonts` for a ~180 KB smaller file).
- **Metadata**: pass `--author`/`--lang` on the CLI, or add an `"epub"` object to the spec: `{ "epub": { "author": "…", "language": "en", "publisher": "…", "identifier": "…", "description": "…" } }`. Title and description default to the cover's title and subtitle.

Read `references/epub-notes.md` before making EPUB-specific styling or splitting decisions — it covers e-reader quirks (night mode, Kindle, embedded-font behavior) and how to verify output.

## Recommended workflow

1. **Install deps** (the pip line above) if not already present.
2. **Get the content as Markdown.** If the user gave you prose or asked you to write it, produce clean Markdown first — use `##` for section headers (they get an underline rule), tables, fenced code blocks, and `>` blockquotes for callouts. The template styles all of these.
3. **Choose the path:** single file with cover flags for a normal document; a spec for a multi-part book with dividers or a TOC. Choose the format(s): PDF for print/sharing, EPUB for e-readers — or both from one spec.
4. **Render to `/mnt/user-data/outputs/`** so the file is downloadable.
5. **Verify** — the scripts print page/chapter count and size. For a PDF visual check, rasterize a page: `pdftoppm -png -r 60 -f 1 -l 1 out.pdf /tmp/preview` then view `/tmp/preview-01.png`. Always eyeball the cover at least once. For EPUB checks see `references/epub-notes.md`.
6. **Present** the PDF with `present_files`.

## Theming

The default palette is a deep teal/green editorial look. To re-brand (different accent color, cover background, fonts), pass a `theme` object in the spec — every color and font is overridable, and **the same theme tokens drive both the PDF and the EPUB**. See `references/theming.md` for the full list of tokens and worked examples (corporate blue, warm editorial, monochrome). The quick CLI path always uses the default theme; use a spec to theme.

## Markdown authoring tips for best results

- `## Heading` gets a bottom rule; `###` and `####` are lighter. Lead sections with `##`.
- A leading `>` blockquote right after a heading reads as a highlighted callout / thesis line.
- Tables render with uppercase mono headers and a first-column emphasis — great for comparison/decision tables.
- Fenced code blocks (```) render in a bordered panel; ASCII diagrams inside them work well and keep their spacing.
- Keep ASCII diagrams under ~66 characters wide so they don't overflow the code panel (it does not wrap).
- Use `---` for a horizontal rule between major movements.
- `**bold**` is semibold, not heavy — it's for gentle emphasis, not shouting.

## Files in this skill

- `scripts/md2pdf.py` — the PDF rendering engine (CLI + spec driver). Read its docstring for the full flag list.
- `scripts/md2epub.py` — the EPUB engine. Same spec and cover flags, plus `--author`, `--lang`, `--split`, `--no-fonts`, `--no-cover`.
- `references/spec-format.md` — the complete JSON/YAML spec schema for multi-part books.
- `references/theming.md` — palette tokens, layout knobs, and re-brand examples.
- `references/epub-notes.md` — e-reader behavior, chapter splitting, metadata, and verification for EPUB output.
- `examples/` — a runnable single-doc example and a multi-part spec example.
- `assets/fonts/` — the bundled woff2 font set (Bricolage Grotesque + IBM Plex Sans/Mono).
