# EPUB Notes

How `scripts/md2epub.py` behaves, why it makes the styling choices it makes,
and how to verify the output. Read this before making EPUB-specific decisions.

## What gets built

An EPUB 3 package containing, in spine order:

1. **Raster cover** (`cover.png`, 1600×2560) — the same dark cover design as
   the PDF, rendered with weasyprint and rasterized (pypdfium2, falling back
   to `pdftoppm`). This is what e-reader libraries and store shelves display.
2. **Title page** (XHTML) — kicker, title, subtitle, pills, foot, on the dark
   cover background.
3. **Nav page** — the reader-facing table of contents (also exposed as the
   reader's built-in TOC, nested: part dividers → chapters → sub-headings).
4. **Part dividers** — dark full-page breaks, mirroring the PDF's dividers
   (`warm: true` swaps the kicker color, same as the PDF).
5. **Chapters** — one XHTML file per chapter (see splitting below).

Plus: the bundled woff2 fonts, one stylesheet derived from the shared theme
tokens, an NCX for older readers, and any local images referenced in the
Markdown (copied in and re-linked automatically).

## Chapter splitting

E-readers handle many small files better than one huge one, and per-chapter
files give clean progress bars and TOC jumps. The splitter works per section
(per spec entry or per input file):

- **Auto (default)**: split at the shallowest heading level present — `#` if
  any, else `##`. With the common book pattern (`strip_h1: true` + `##`
  sections), each `##` becomes a chapter under its part divider.
- `--split 1` / `--split 2`: force splitting at h1 / h2.
- `--split 0`: never split (one file per section). Use for short documents.
- Headings one level below the split level become sub-entries in the TOC
  (fragment links), so readers get two levels of navigation per part.

## Metadata

Title and description default to the cover's `title` and `subtitle`. Set the
rest via CLI (`--author`, `--lang`) or a top-level `epub` object in the spec:

```json
{
  "epub": {
    "author": "Jane Doe",
    "language": "en",
    "publisher": "Self-published",
    "identifier": "urn:isbn:9781234567890",
    "description": "Overrides the cover subtitle as the store description."
  }
}
```

If no identifier is given, a random `urn:uuid:` is generated (fine for
personal use; use a real ISBN/URN for distribution). Always set `--author` —
e-reader libraries sort by it and "Unknown author" looks unfinished.

## E-reader-safe styling decisions (don't "fix" these)

- **Body text color and background are intentionally NOT set.** Readers apply
  their own themes (sepia, night mode, e-ink). Forcing dark-on-white body text
  breaks night mode. Brand color appears in borders, rules, links, and panels
  instead.
- **Every tinted panel pairs `background` with an explicit text `color`**
  (blockquotes, code, table headers, the dark title/divider pages), so they
  stay readable regardless of the reader's theme.
- **Code blocks use `pre-wrap`**, unlike the PDF's `pre`. E-reader screens are
  narrow; unwrapped code clips. Wide ASCII diagrams that look perfect in the
  PDF **will wrap and break** on a phone/e-ink screen — keep them under ~40
  characters wide if the EPUB matters, or accept the wrap.
- **Sizes are in `em`**, so the user's font-size setting scales everything.
- **No running footer or page numbers** — pagination is dynamic. The spec's
  `footer` key is ignored for EPUB.

## Cover safe margins (Kobo and other e-readers)

The raster cover (`cover.png`) is generated at a fixed 1600×2560 (5:8) canvas,
but the device that ends up displaying it — e.g. a Kobo Libra H2O's library
thumbnail — often crops to a different aspect ratio before showing it. On
Kobo devices in particular this has been observed to clip the left/right
edges of the image. To guard against this, the cover's horizontal padding is
intentionally generous (96px CSS / ~12% of width on each side, vs. 100px top
and bottom), keeping the kicker, title, pills, and foot text away from the
edges most likely to be cropped. Don't shrink this back down to make the
cover "look tighter" — it trades a real clipping bug for a cosmetic gain.

## Fonts

The woff2 set is embedded and referenced with `@font-face` (~180 KB). Notes:

- EPUB 3.3 readers (Apple Books, Kobo, recent KOReader/Calibre) support woff2.
  Some readers require the user to enable "publisher fonts"; others ignore
  embedded fonts entirely. The font stacks always end in `sans-serif` /
  `monospace`, so fallback is graceful.
- Kindle: send-to-kindle and modern Kindle firmware accept EPUB but often
  substitute fonts. The layout survives; the typefaces may not. That's normal.
- `--no-fonts` skips embedding for a smaller file with reader-default fonts.

## Verifying output

1. The script prints chapter count, whether a raster cover was produced, and
   file size. **If it says the raster cover was skipped, install weasyprint.**
2. Structural check (no e-reader needed):
   ```bash
   cd /tmp && rm -rf epubchk && mkdir epubchk && unzip -q out.epub -d epubchk
   cat epubchk/mimetype                     # application/epub+zip
   python3 -c "from lxml import etree; import glob; \
     [etree.parse(f) for f in glob.glob('epubchk/EPUB/*.xhtml')]; print('xhtml ok')"
   ```
3. Eyeball the cover: `unzip -p out.epub EPUB/cover.png > /tmp/c.png` and view it.
4. If Java + epubcheck are available, `java -jar epubcheck.jar out.epub` is the
   gold standard — but the build is already conformant EPUB 3 via ebooklib.

## Troubleshooting

- **"Missing dependency: EbookLib"** → `pip install EbookLib --break-system-packages`.
- **Cover skipped** → weasyprint missing, or neither pypdfium2 nor `pdftoppm`
  available for rasterizing. `pip install weasyprint pypdfium2 --break-system-packages`.
- **A chapter's TOC title looks wrong** → the splitter titles chapters from
  their leading heading; content before the first heading is titled with the
  part's name. Restructure the Markdown so each chapter opens with a heading.
- **Reader shows no styling** → some readers (or "publisher defaults off"
  settings) strip CSS. Content remains fully readable; that's by design.
