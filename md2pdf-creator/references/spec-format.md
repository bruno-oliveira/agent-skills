# Spec Format

The `--spec` file (JSON or YAML) drives multi-part documents: covers, part
dividers, tables of contents, and per-section control. Pass it with
`python3 scripts/md2pdf.py --spec book.json -o out.pdf`. Paths inside the spec
are resolved relative to the spec file's own directory.

## Top-level keys

| Key | Type | Description |
|---|---|---|
| `footer` | string | Running footer text on every content page. Page numbers (`n / total`) are added automatically on the right. |
| `theme` | object | Palette/font/layout overrides. See `theming.md`. Omit for the default teal look. |
| `cover` | object | The dark cover page. Omit for a coverless document. |
| `html_after_cover` | string | Raw HTML injected right after the cover — use for a custom table of contents page. |
| `sections` | array | The ordered content. Each item may carry a `divider`, a `file`, inline `markdown`, and/or raw `html`. |
| `files` | array | Shortcut: a flat list of markdown files concatenated with no dividers (ignored if `sections` is used for those parts). |

## The `cover` object

| Key | Description |
|---|---|
| `kicker` | Small uppercase mono label above the title. |
| `title` | The big title. Use `\n` for a line break (rendered as `<br>`). |
| `subtitle` | Descriptive paragraph under the title. |
| `pill_a` | Left outlined pill text (e.g. a tension pole, a before value). Omit to hide both pills. |
| `pill_b` | Right outlined pill text. A `↔` is drawn between the pills. |
| `foot` | Small mono text pinned to the bottom of the cover. |

## Each `sections` item

An item can combine several of these; they render in this order: divider, then file, then markdown, then html.

| Key | Description |
|---|---|
| `divider` | A part-divider page (see below). Starts on a fresh page. |
| `file` | Path to a markdown file to render. |
| `strip_h1` | If true, drops the file's leading `# Title` line (so the divider carries the title instead). |
| `markdown` | Inline markdown string to render (alternative to `file`). |
| `html` | Raw HTML injected as-is (for custom blocks the template doesn't cover). |

## The `divider` object

| Key | Description |
|---|---|
| `kicker` | Small uppercase label (e.g. "Part II"). |
| `title` | The divider's large title. |
| `description` | A paragraph under the title (muted). |
| `warm` | If true, the kicker uses the warm accent color instead of the cool one — handy for alternating parts or a "problems vs solutions" rhythm. |

## Table of contents pattern

The engine has no automatic TOC (weasyprint page numbers aren't known until
render). For a book, hand-write a TOC as `html_after_cover` using a simple
table, and add matching CSS via the theme's `extra_css` escape hatch (see
`theming.md`). Keep it simple — part title + one-line description per row, no
page numbers, or fill page numbers after a first render if you need them.

## Full example

```json
{
  "footer": "THE FIELD GUIDE · 2026",
  "theme": { "accent": "#0E6B5C" },
  "cover": {
    "kicker": "A PRACTICAL FIELD GUIDE",
    "title": "The Field\nGuide",
    "subtitle": "A complete, opinionated method — for now and the future.",
    "pill_a": "THEORY", "pill_b": "PRACTICE",
    "foot": "FIRST EDITION · 2026"
  },
  "html_after_cover": "<div class='toc'>...custom TOC html...</div>",
  "sections": [
    {
      "divider": { "kicker": "Part I", "title": "Foundations",
                   "description": "The ideas everything else rests on." },
      "file": "part1.md", "strip_h1": true
    },
    {
      "divider": { "kicker": "Part II", "title": "In Practice",
                   "description": "Applying the ideas.", "warm": true },
      "file": "part2.md", "strip_h1": true
    },
    { "markdown": "## Appendix\n\nInline content works too." }
  ]
}
```

YAML works identically — pass a `.yaml`/`.yml` path (needs `pyyaml`).
