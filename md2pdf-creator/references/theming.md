# Theming

Every color, font, and key layout value is overridable through the spec's
`theme` object. The quick CLI path always uses the default theme; to re-brand,
use a `--spec` and add a `theme`.

## Palette tokens

| Token | Default | Used for |
|---|---|---|
| `ink` | `#14262B` | Body text |
| `ink_strong` | `#0C1A1E` | Headings, emphasized table cells |
| `accent` | `#0E6B5C` | Section-heading rules, links, code left-border, divider kicker (cool) |
| `accent_warm` | `#B5401F` | Warm divider kicker (`"warm": true` dividers) |
| `cover_bg` | `#0C1A1E` | Cover background |
| `cover_ink` | `#E8F0ED` | Cover default text |
| `cover_title` | `#FFFFFF` | Cover title |
| `cover_sub` | `#B9CCC6` | Cover subtitle |
| `cover_kicker` | `#8FB5AB` | Cover kicker label |
| `pill_a` | `#F0906E` | Left cover pill (warm) |
| `pill_b` | `#63C7B2` | Right cover pill (cool) |
| `muted` | `#4B6360` | Footer, captions, divider prose, table headers |
| `hairline` | `#DDE6E3` | Light row/rule lines |
| `rule` | `#CBD8D4` | Heavier rules (h2 underline, table header border) |
| `panel` | `#F0F4F3` | Code block and table-header background |
| `panel_code` | `#E4EBE9` | Inline `code` background |
| `quote_bg` | `#DCEBE6` | Blockquote background |

## Font tokens

| Token | Default | Notes |
|---|---|---|
| `font_display` | `Bricolage Grotesque` | Headings, cover, divider titles |
| `font_body` | `IBM Plex Sans` | Body text |
| `font_mono` | `IBM Plex Mono` | Code, footer, kickers, table headers, pills |

Only the bundled families are guaranteed to embed. To use a different family,
add its woff2 to `assets/fonts/`, add matching `@font-face` rules (edit
`FACE` in `scripts/md2pdf.py`), then point the token at it. If you just set a
token to a system font name (e.g. `"Georgia"`), weasyprint will use it if it's
installed on the box; otherwise it falls back.

## Layout tokens

| Token | Default | Notes |
|---|---|---|
| `page_size` | `A4` | e.g. `letter`, `A4`, `A5` |
| `margin` | `20mm 18mm 22mm` | CSS margin shorthand (top, sides, bottom) |
| `base_pt` | `10pt` | Root font size; scales the whole document |

## Re-brand examples

**Corporate blue.** A cooler, more formal palette:

```json
{
  "theme": {
    "accent": "#1D4E89",
    "accent_warm": "#B4531A",
    "cover_bg": "#0B1F3A",
    "cover_kicker": "#7FA8D9",
    "cover_sub": "#B9C9DE",
    "pill_b": "#5FA8D3",
    "quote_bg": "#E3ECF6",
    "panel": "#EEF3F9",
    "rule": "#C7D4E4"
  }
}
```

**Warm editorial.** An amber/ink literary feel:

```json
{
  "theme": {
    "accent": "#9A5B2E",
    "cover_bg": "#241A12",
    "cover_kicker": "#C9A87F",
    "cover_sub": "#D8C6AE",
    "pill_a": "#E0A05A",
    "pill_b": "#C97B4A",
    "quote_bg": "#F3EADD",
    "panel": "#F4EEE4",
    "panel_code": "#EDE4D5",
    "rule": "#D8CBB8",
    "font_display": "Bricolage Grotesque"
  }
}
```

**Monochrome / minimal.** Near-black on white, no color:

```json
{
  "theme": {
    "accent": "#222222",
    "accent_warm": "#222222",
    "cover_bg": "#111111",
    "cover_kicker": "#AAAAAA",
    "cover_sub": "#CCCCCC",
    "pill_a": "#DDDDDD", "pill_b": "#DDDDDD",
    "quote_bg": "#F2F2F2",
    "panel": "#F4F4F4", "panel_code": "#ECECEC",
    "rule": "#DADADA", "hairline": "#E6E6E6"
  }
}
```

## Advanced: extra CSS

For anything the tokens don't reach (a custom TOC layout, a bespoke callout
class used via a section's `html`), append raw CSS by editing the returned
string in `build_css`, or add a small `extra_css` handling block. The simplest
path for one-off documents: include a `<style>` tag inside `html_after_cover`
or a section's `html` — weasyprint honors inline styles.
