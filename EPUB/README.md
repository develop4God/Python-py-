# Encounters → EPUB Converter

Converts your devotional **Encounter** JSON files (schema `encounters_v1`)
into polished, valid EPUB3 ebooks with embedded images — built specifically
for the real Encounters schema, not the daily-devotional schema your old
converter was based on.

## What changed vs. your old `json_to_epub.py`

Your previous converter assumed fields like `greek_words`, `identity_statement`,
`action_steps`, and an emoji-as-`icon` text header — none of which exist in
the Encounters JSON. It also never touched images at all (`image_url` was
read from the JSON but never used). The result was blank covers (no
`title`/`subtitle` at the top level — those live in `meta.character` /
`meta.scripture_reference`) and missing artwork throughout.

This converter is built directly from the real schema used by
`encounters_master_validator.py` / `validate_encounters.py`, and from the
actual files in `devocionales-json/encounters/<lang>/*.json`. It handles
all 7 real card types:

- `cinematic_scene`
- `scripture_moment`
- `character_moment`
- `theological_depth`
- `interactive_moment`
- `discovery_activation`
- `completion`

## Images

Each card's `image_url` is a bare filename (e.g. `bartimaeus_intro.png`)
resolved against `Devocionales-assets/images/encounters/<encounter_id>_001/`.
That folder holds both `.png` (2-4MB, full quality) and `.avif` (50-120KB,
same quality) versions of every image.

**The converter sources from the small `.avif` files**, decodes them, resizes
to max 900px wide, and re-encodes as JPEG (quality 82) before embedding.
JPEG — not AVIF — is used inside the EPUB itself because most e-reader apps
(Kindle, Apple Books, and many EPUB reading apps) don't yet render AVIF
reliably, while JPEG works everywhere. Net result: ~500KB–1.1MB per finished
EPUB instead of 20-30MB+ if the raw PNGs were embedded directly.

## Language support

Cover/chrome strings (reading time, "Related References", "Your Encounter",
etc.) are localized for `es`, `en`, `pt`, `fr`, `de`. Any other language
(`hi`, `ja`, `zh`, `ar`, `fil`, ...) falls back to English chrome — the
actual devotional content (titles, verses, narrative, prayers) always
renders in the encounter's own language straight from the JSON, since that
text never goes through the UI-string dictionary.

To add real localized chrome for another language, add an entry to
`UI_STRINGS` in `encounters_to_epub.py`.

## Usage

### Single file

```bash
python encounters_to_epub.py <encounter.json> <assets_dir> [output.epub]
```

`<assets_dir>` is the folder holding that one encounter's images, e.g.:

```bash
python encounters_to_epub.py \
  devocionales-json/encounters/es/bartimaeus_es_001.json \
  Devocionales-assets/images/encounters/bartimaeus_001 \
  bartimaeus_es.epub
```

### Batch — every encounter in one language

```bash
python batch_convert.py <lang> <devocionales-json_repo> <devocionales-assets_repo> <output_dir>
```

```bash
python batch_convert.py es ./devocionales-json ./Devocionales-assets ./epubs_es
```

This walks `devocionales-json/encounters/<lang>/*.json`, auto-resolves each
file's asset folder from its `id` field, and writes one EPUB per encounter.

## Index.json — authored titles, subtitles, and cover images

`encounters/index.json` carries the *real, authored* cover copy for every
encounter, per language — crafted hooks like "El Hombre en el Árbol" /
"El hombre más odiado en Jericó — y Jesús eligió su casa", not a flat
fallback like "Zaqueo" / "Lucas 19:1-10". It also names a dedicated
`intro_image` per encounter, separate from any card image.

The converter auto-discovers `index.json` one directory above the input
file (the standard repo layout: `encounters/index.json` next to
`encounters/<lang>/`). You can also pass it explicitly as a 4th CLI arg,
or via `index_path=` when calling `convert()` from Python. If no index is
found, the cover quietly falls back to the encounter JSON's own
`meta.character` / `meta.scripture_reference` — nothing breaks, you just
get the older (terser) cover copy.

The cover always shows, in this order: a small "character kicker" (e.g.
"Zaqueo") *only if* the title doesn't already name the character, the
authored title, the scripture passage range (e.g. "Lucas 19:1-10"), the
authored subtitle, and the key verse. This was specifically added after
reverse-validation caught `meta.character` ("La Mujer Samaritana") being
silently dropped once the index title ("La Mujer que Dejó el Cántaro")
took over — the kicker line guarantees the character's identity is never
lost from the cover even when the title is poetic/abstract.

## Authorship credit + Bible copyright notice

Every EPUB now ends with an "About this ebook" page (colophon) that includes:

1. **Develop4God authorship credit** — states the ebook was created by
   Develop4God, as part of the Devocional app.
2. **A Bible-translation usage notice**, looked up from a researched table
   (`BIBLE_COPYRIGHT` in `encounters_to_epub.py`) keyed by the encounter's
   `bible_version` field.

### What's researched so far

| Version | Status | Notes |
|---|---|---|
| RVR1960 | **Copyrighted** | © Sociedades Bíblicas en América Latina / renewed 1988 Sociedades Bíblicas Unidas. Required attribution text included. A retired preacher was sued by American Bible Society for distributing 160,000+ uncredited RVR1960 copies — this is enforced, not theoretical. |
| KJV | Public domain | 1611 text, free to use. |
| ARC (Almeida Revista e Corrigida) | Public domain *base text* | The 1898 translation itself is PD, but confirm which specific modern edition/typesetting you're sourcing from — some publishers claim rights on their own edition layout even of PD source text. |
| LSG1910 (Louis Segond) | Public domain | 1910 revision, explicitly released PD by multiple Bible sites. |
| LU17 (Luther) | Public domain | 1912/1917 revision. |
| SCH2000 (Schlachter) | **Copyrighted** | © Geneva Bible Society / CLV. Used in your pipeline per memory — verify current license terms. |
| NVI | **Copyrighted** | © 1999, 2015 Biblica, Inc.® Up to 500 verses quotable without written permission if under 25% of the work and properly credited — this app likely qualifies, but the attribution is still required. |
| NIV | **Copyrighted** | © 1973, 1978, 1984, 2011 Biblica, Inc.® Same 500-verse / 25% fair-use ceiling as NVI. |

**Not yet researched** (no entry in the table): 和合本1919 (Chinese), 新改訳2003
(Japanese — confirmed copyrighted, actively managed by 新日本聖書刊行会, requires
attribution under Japanese copyright law and a usage application for
distribution beyond a single church), पवित्र बाइबिल/O.V. (Hindi), Magandang
Balita Biblia (Filipino), and the Arabic translation in use. For any
`bible_version` not in the table, the colophon prints a generic caution
("verify copyright status before wide distribution") instead of inventing a
claim — add a real entry to `BIBLE_COPYRIGHT` once you've confirmed the
terms for these.

### Recommendation

Given the catalog mixes copyrighted translations (RVR1960, NVI, NIV,
SCH2000, likely 新改訳2003) with public-domain ones (KJV, LSG1910, LU17,
ARC base text), I'd treat the colophon notice as a minimum, not a nice-to-have:
RVR1960 in particular has a documented enforcement history. The safest
long-term move, if you plan to distribute these ebooks beyond personal/church
use, is a short written request to Sociedades Bíblicas Unidas (for RVR1960)
and Biblica (for NVI/NIV) — most Bible societies grant free permission to
ministries for non-commercial use, they just want to be asked and credited.

## Reverse validation

`reverse_validate.py` (in this package) walks every field in a source JSON
and confirms it's either rendered somewhere in the EPUB's text, or explicitly
marked as an intentional skip (structural fields like `order`/`type`/`mood`,
or app-runtime-only fields like `ambient_sound`/`haptic`). All 6 Spanish
encounters plus English and Hindi test files pass with zero missing fields.

```bash
python reverse_validate.py <encounter.json> <output.epub> [index.json]
```

Passing `index.json` additionally checks that the authored `titles`,
`subtitles`, and `scripture_reference` for that encounter/language made it
onto the cover, and that `intro_image` got embedded.

## Requirements

```bash
pip install ebooklib pillow pillow-avif-plugin --break-system-packages
```

## Validated

Every EPUB produced by this converter passes
[epubcheck](https://github.com/w3c/epubcheck) (the official IDPF/W3C EPUB
validator) with zero errors and zero warnings. Tested against all 6
Spanish encounters (bartimaeus, mary_garden, peter_water, saulo,
woman_well, zacchaeus), an English encounter, and a Hindi encounter
(confirming Devanagari renders correctly and the English chrome fallback
doesn't break).

## Known non-goals

- `ambient_sound` and `haptic` fields are intentionally not rendered —
  they're app runtime cues with no print/ebook equivalent.
- The `mary_garden_image_prompts.json` file in `encounters/es/` is not an
  encounter and is skipped automatically by `batch_convert.py` (no
  `cards` array, used by `batch_convert.py`'s `.glob('*.json')` — it just
  won't find a matching asset folder and gets skipped with a warning).
