#!/usr/bin/env python3
"""
encounters_to_epub.py — Convert devocional_nuevo "Encounter" JSON files
(schema_version: encounters_v1) into a single, polished EPUB3 ebook
with embedded images, sourced from the public devocionales-json +
Devocionales-assets repos (or local copies of the same layout).

Card types handled (matches encounters_master_validator.py):
  cinematic_scene, scripture_moment, character_moment,
  theological_depth, interactive_moment, discovery_activation,
  completion

Usage:
  python encounters_to_epub.py <encounter.json> <assets_dir> [output.epub] [index.json]

  <assets_dir> must contain the image referenced by each card's
  "image_url" (bare filename, e.g. "bartimaeus_intro.png"). Pass the
  folder that holds the AVIF/PNG files for that one encounter
  (e.g. .../images/encounters/bartimaeus_001/).

  [index.json] is optional. It carries the *authored* per-language title,
  subtitle, scripture_reference, and cover (intro_image) for each encounter
  — real cover copy, not a fallback derived from meta.character. If not
  passed explicitly, the converter looks for encounters/index.json one
  directory above the input file (the standard repo layout) and uses it
  automatically when found.
"""

import io
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen

import yaml

from PIL import Image
try:
    import pillow_avif  # noqa: F401  (registers AVIF codec with Pillow)
except ImportError:
    pass

from ebooklib import epub

# ── i18n: UI strings shown in the ebook chrome (not the devotional content) ──

UI_STRINGS = {
    'es': {
        'cover_label': 'Un Encuentro Bíblico', 'reading_time': 'min de lectura',
        'related_refs': 'CONEXIONES PROFUNDAS', 'your_encounter': 'Tu Encuentro',
        'prayer_default': 'ORACIÓN', 'reflect': 'Reflexiona', 'amen': 'Amén',
        'colophon_title': 'Información', 'app_credit': 'Desarrollado con ❤️ por Develop4God.',
        'scripture_heading': 'Sobre el texto bíblico utilizado',
        'get_app': 'Descarga la app',
        'welcome_title_line1': 'Ellos lo encontraron.',
        'welcome_title_line2': 'Cambiaron para siempre.',
        'welcome_title_line3': 'El mismo Jesús. Aquí. Ahora.',
        'welcome_subtitle': 'Historias reales. El Jesús real.',
    },
    'en': {
        'cover_label': 'A Bible Encounter', 'reading_time': 'min read',
        'related_refs': 'DEEPER CONNECTIONS', 'your_encounter': 'Your Encounter',
        'prayer_default': 'PRAYER', 'reflect': 'Reflect', 'amen': 'Amen',
        'colophon_title': 'About this ebook', 'app_credit': 'Developed with ❤️ by Develop4God.',
        'scripture_heading': 'About the Bible text used',
        'get_app': 'Get the app',
        'welcome_title_line1': 'They found Him.',
        'welcome_title_line2': 'Changed forever.',
        'welcome_title_line3': 'The same Jesus. Here. Now.',
        'welcome_subtitle': 'Real stories. The real Jesus.',
    },
    'pt': {
        'cover_label': 'Um Encontro Bíblico', 'reading_time': 'min de leitura',
        'related_refs': 'CONEXÕES PROFUNDAS', 'your_encounter': 'Seu Encontro',
        'prayer_default': 'ORAÇÃO', 'reflect': 'Reflita', 'amen': 'Amém',
        'colophon_title': 'Sobre este ebook', 'app_credit': 'Desenvolvido com ❤️ por Develop4God.',
        'scripture_heading': 'Sobre o texto bíblico utilizado',
        'get_app': 'Baixe o app',
        'welcome_title_line1': 'Eles encontraram.',
        'welcome_title_line2': 'Foram transformados para sempre.',
        'welcome_title_line3': 'O mesmo Jesus. Aqui. Agora.',
        'welcome_subtitle': 'Histórias reais. O verdadeiro Jesus.',
    },
    'fr': {
        'cover_label': 'Une Rencontre Biblique', 'reading_time': 'min de lecture',
        'related_refs': 'CONNEXIONS PROFONDES', 'your_encounter': 'Votre Rencontre',
        'prayer_default': 'PRIÈRE', 'reflect': 'Réfléchissez', 'amen': 'Amen',
        'colophon_title': 'À propos de cet ebook', 'app_credit': 'Développé avec ❤️ par Develop4God.',
        'scripture_heading': 'À propos du texte biblique utilisé',
        'get_app': 'Téléchargez l\'application',
        'welcome_title_line1': 'Ils l\'ont trouvé.',
        'welcome_title_line2': 'Transformés pour toujours.',
        'welcome_title_line3': 'Le même Jésus. Ici. Maintenant.',
        'welcome_subtitle': 'Des histoires vraies. Le vrai Jésus.',
    },
    'de': {
        'cover_label': 'Eine biblische Begegnung', 'reading_time': 'Min. Lesezeit',
        'related_refs': 'TIEFERE VERBINDUNGEN', 'your_encounter': 'Deine Begegnung',
        'welcome_title_line1': 'Sie fanden Ihn.',
        'welcome_title_line2': 'Für immer verändert.',
        'welcome_title_line3': 'Derselbe Jesus. Hier. Jetzt.',
        'welcome_subtitle': 'Wahre Geschichten. Der wahre Jesus.',
        'prayer_default': 'GEBET', 'reflect': 'Reflektiere', 'amen': 'Amen',
        'colophon_title': 'Über dieses E-Book', 'app_credit': 'Entwickelt mit ❤️ von Develop4God.',
        'scripture_heading': 'Über den verwendeten Bibeltext',
        'get_app': 'App herunterladen',
    },
}

DEVELOP4GOD_URL = 'https://www.develop4god.com'
DEFAULT_UI = UI_STRINGS['en']


def ui(language):
    return UI_STRINGS.get(language, DEFAULT_UI)


# ── Bible version copyright/usage notices ─────────────────────────────────────
# Researched per-translation. "public_domain": True means the underlying
# translation text itself is out of copyright (age-based), though note that
# specific *modern* publisher editions/typesetting of even old translations
# can carry their own edition-level copyright — when in doubt, the safer
# move is to still print a clear source attribution, which we always do
# below regardless of public-domain status.
BIBLE_COPYRIGHT = {
    'RVR1960': {
        'public_domain': False,
        'notice': {
            'es': 'El texto bíblico ha sido tomado de la versión Reina-Valera © 1960 Sociedades '
                  'Bíblicas en América Latina; © renovado 1988 Sociedades Bíblicas Unidas. '
                  'Utilizado con permiso. Reina-Valera 1960® es una marca registrada de '
                  'Sociedades Bíblicas Unidas.',
            'en': 'Scripture taken from the Reina-Valera 1960 Spanish translation, '
                  '© 1960 Sociedades Bíblicas en América Latina; © renewed 1988 Sociedades '
                  'Bíblicas Unidas. Used with permission. Reina-Valera 1960® is a registered '
                  'trademark of Sociedades Bíblicas Unidas.',
        },
    },
    'KJV': {
        'public_domain': True,
        'notice': {
            'es': 'El texto de la Versión King James (1611) es de dominio público.',
            'en': 'Scripture quotations are from the King James Version (1611), which is in '
                  'the public domain.',
        },
    },
    'ARC': {
        'public_domain': True,
        'notice': {
            'es': 'El texto base de la Almeida Revista e Corrigida (edición de 1898) es de '
                  'dominio público. Confirme la edición específica utilizada, ya que algunas '
                  'tipografías/ediciones modernas publicadas por sociedades bíblicas pueden '
                  'tener derechos propios sobre esa edición particular.',
            'pt': 'O texto-base da Almeida Revista e Corrigida (edição de 1898) é de domínio '
                  'público. Confirme a edição específica utilizada, pois algumas tipografias/'
                  'edições modernas publicadas por sociedades bíblicas podem ter direitos '
                  'próprios sobre essa edição em particular.',
            'en': 'The base text of the Almeida Revista e Corrigida (1898 edition) is in the '
                  'public domain. Confirm the specific edition used, since some modern '
                  'typesettings/editions published by Bible societies may carry their own '
                  'rights over that particular edition.',
        },
    },
    'LSG1910': {
        'public_domain': True,
        'notice': {
            'es': 'El texto de la Bible Louis Segond (revisión de 1910) es de dominio público.',
            'fr': 'Le texte de la Bible Louis Segond (révision de 1910) appartient au domaine public.',
            'en': 'Scripture quotations are from the Louis Segond Bible (1910 revision), which '
                  'is in the public domain.',
        },
    },
    'LU17': {
        'public_domain': True,
        'notice': {
            'es': 'El texto de la Biblia de Lutero (revisión de 1912/1917) es de dominio público.',
            'de': 'Der Text der Lutherbibel (Revision von 1912/1917) ist gemeinfrei.',
            'en': 'Scripture quotations are from the Luther Bible (1912/1917 revision), which '
                  'is in the public domain.',
        },
    },
    'SCH2000': {
        'public_domain': False,
        'notice': {
            'es': 'El texto de la Schlachter 2000 © Genfer Bibelgesellschaft / CLV. Utilizado con '
                  'permiso. Verifique los términos de uso vigentes con el titular de derechos.',
            'de': 'Schlachter 2000 © Genfer Bibelgesellschaft / CLV. Verwendet mit Genehmigung. '
                  'Bitte aktuelle Nutzungsbedingungen beim Rechteinhaber prüfen.',
            'en': 'Schlachter 2000 © Geneva Bible Society / CLV. Used with permission. Verify '
                  'current usage terms with the rights holder.',
        },
    },
    'NVI': {
        'public_domain': False,
        'notice': {
            'es': 'La Santa Biblia, Nueva Versión Internacional® NVI® © 1999, 2015 por Biblica, '
                  'Inc.® Utilizado con permiso. Todos los derechos reservados en todo el mundo.',
            'en': 'Scripture quotations are from La Santa Biblia, Nueva Versión Internacional® '
                  'NVI® © 1999, 2015 by Biblica, Inc.® Used by permission. All rights reserved '
                  'worldwide.',
        },
    },
    'NIV': {
        'public_domain': False,
        'notice': {
            'es': 'El texto de La Santa Biblia, Nueva Versión Internacional® NIV® © 1973, 1978, '
                  '1984, 2011 por Biblica, Inc.® Utilizado con permiso. Todos los derechos '
                  'reservados en todo el mundo.',
            'en': 'Scripture quotations taken from The Holy Bible, New International Version® '
                  'NIV® Copyright © 1973, 1978, 1984, 2011 by Biblica, Inc.™ Used by permission. '
                  'All rights reserved worldwide.',
        },
    },
}


def bible_copyright_notice(bible_version, language):
    """Returns the best-available copyright/usage notice text for this Bible
    version, preferring the encounter's own language, falling back to English,
    or a generic caution if the version isn't in our researched table yet."""
    entry = BIBLE_COPYRIGHT.get(bible_version)
    if not entry:
        return {
            'es': f'Texto bíblico: {bible_version}. Verifique los términos de uso y derechos de '
                  f'autor de esta traducción con la sociedad bíblica o editorial correspondiente '
                  f'antes de distribuir este archivo ampliamente.',
            'en': f'Bible text: {bible_version}. Verify the usage terms and copyright status of '
                  f'this translation with the relevant Bible society or publisher before '
                  f'distributing this file widely.',
        }.get(language, None) or f'Bible text: {bible_version}. Verify copyright status before wide distribution.'
    notice = entry['notice'].get(language) or entry['notice'].get('en')
    return notice




# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
@charset "UTF-8";
body { font-family: Georgia, "Times New Roman", serif; font-size: 1em; line-height: 1.7; margin: 1.2em; color: #1a1a1a; }
h1 { font-size: 1.6em; margin-top: 0.6em; margin-bottom: 0.2em; color: #2c2c2c; }
h2 { font-size: 1.2em; margin-top: 1.4em; margin-bottom: 0.3em; color: #3a3a3a; }
h3 { font-size: 1.0em; margin-top: 1.2em; margin-bottom: 0.2em; color: #444; }
p { margin: 0.7em 0; }

.full-image { text-align: center; margin: 0 0 1em 0; }
.full-image img { max-width: 100%; height: auto; border-radius: 4px; }

.cover { text-align: center; padding: 1em 0.5em; }
.cover .full-image { margin-bottom: 0.8em; }
.cover .character-kicker { font-size: 0.85em; letter-spacing: 0.08em; text-transform: uppercase; color: #999; margin: 0.4em 0 0 0; }
.cover .emoji { font-size: 2.4em; }
.cover h1 { font-size: 1.9em; margin: 0.2em 0 0.1em 0; }
.cover .subtitle { font-size: 1em; color: #555; font-style: italic; margin-top: 0.2em; }
.cover .scripture-passage { font-size: 0.9em; color: #888; letter-spacing: 0.02em; margin-top: 0.1em; }
.cover .key-verse { margin: 1.6em auto; max-width: 30em; border-left: 3px solid #999;
    padding-left: 1em; text-align: left; font-style: italic; color: #333; }
.cover .key-verse .ref { font-weight: bold; font-style: normal; font-size: 0.85em; color: #666; margin-top: 0.4em; }
.cover .meta-line { font-size: 0.8em; color: #999; margin-top: 2em; }
.cover .welcome-tagline { margin-top: 1.6em; font-style: italic; color: #777; }
.cover .welcome-tagline p { margin: 0.3em 0; }
.cover .welcome-subtitle { font-size: 0.9em; color: #999; }

.card-subtitle { font-size: 0.95em; color: #666; font-style: italic; margin-bottom: 1.2em; }
.icon-line { font-size: 1.8em; margin-bottom: 0.2em; }

.scripture-item { margin: 1.2em 0; padding: 0.8em 1em; border-left: 3px solid #888; background: #f9f7f4; }
.scripture-ref { font-weight: bold; font-size: 0.85em; color: #666; margin-bottom: 0.3em; }
.scripture-text { font-style: italic; font-size: 0.97em; color: #333; line-height: 1.6; }

.revelation-box { background: #f5f5f5; border-left: 4px solid #555;
    padding: 0.8em 1em; margin: 1.5em 0; font-style: italic; color: #333; }

.scripture-connections { margin-top: 1.6em; }
.scripture-connections h3 { font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.04em; color: #777; }

.question { margin: 1em 0; padding-left: 1em; border-left: 2px solid #aaa; }
.question-cat { font-weight: bold; font-size: 0.82em; color: #666; text-transform: uppercase; letter-spacing: 0.03em; }

.prayer { border-top: 1px solid #ccc; margin-top: 1.6em; padding-top: 1em; font-style: italic; }
.prayer-title { font-weight: bold; font-style: normal; font-size: 1.1em; margin-bottom: 0.8em; }

.completion { text-align: center; }
.completion .celebration { font-size: 2em; margin-bottom: 0.4em; }
.completion .prompt { margin-top: 1.6em; font-style: italic; color: #444; }

.tags { margin-top: 2em; font-size: 0.8em; color: #999; text-align: center; }

.colophon { font-size: 0.92em; color: #444; }
.colophon h2 { font-size: 1.1em; margin-top: 1.6em; }
.colophon .app-credit { font-style: italic; color: #555; margin-bottom: 1.6em; }
.colophon .app-link { font-size: 0.92em; color: #555; margin-bottom: 1.6em; }
.colophon .notice { background: #f7f7f5; border-left: 3px solid #aaa; padding: 0.8em 1em; margin: 0.8em 0; }
.colophon .small-note { font-size: 0.85em; color: #888; margin-top: 1em; }
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def paragraphs(text):
    """Plain prose -> <p> blocks per blank-line-separated paragraph."""
    if not text:
        return ''
    parts = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(parts) <= 1:
        # fall back to single-newline split if no blank lines present
        parts = [p.strip() for p in text.split('\n') if p.strip()]
    return '\n'.join(f'<p>{esc(p)}</p>' for p in parts)


def wrap_xhtml(title, body_content, lang):
    return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}">
<head><title>{esc(title)}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
{body_content}
</body></html>"""


def find_image_file(assets_dir, image_url):
    """image_url is a bare filename. Prefer .avif (decode), fall back to .png/.jpg."""
    if not image_url:
        return None
    stem = Path(image_url).stem
    for ext in ('.png', '.jpg', '.jpeg', '.webp', '.avif'):
        candidate = assets_dir / f'{stem}{ext}'
        if candidate.exists():
            return candidate
    direct = assets_dir / image_url
    return direct if direct.exists() else None


def load_image_as_jpeg_bytes(path, max_width=900, quality=82):
    """Decode any supported source (incl. AVIF) and re-encode as JPEG.
    JPEG is used over AVIF for the EPUB itself because most e-reader
    apps (Kindle, Apple Books, many EPUB readers) don't yet render AVIF
    reliably, while JPEG is universally supported."""
    img = Image.open(path)
    if img.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[-1])
        img = bg
    else:
        img = img.convert('RGB')
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality, optimize=True)
    return buf.getvalue()


# ── Shared block builders ─────────────────────────────────────────────────────

def build_image_block(book, assets_dir, image_url, image_registry, counter):
    """Embeds the image (once per unique filename) and returns the <div> HTML."""
    img_path = find_image_file(assets_dir, image_url)
    if not img_path:
        return '', counter
    key = img_path.stem
    if key not in image_registry:
        try:
            jpeg_bytes = load_image_as_jpeg_bytes(img_path)
        except Exception:
            return '', counter
        fname = f'images/img_{counter:03d}.jpg'
        counter += 1
        item = epub.EpubItem(uid=f'img_{key}', file_name=fname,
                              media_type='image/jpeg', content=jpeg_bytes)
        book.add_item(item)
        image_registry[key] = fname
    html = f'<div class="full-image"><img src="{image_registry[key]}" alt=""/></div>\n'
    return html, counter


def safe_dict(card, key):
    """card.get(key, {}) is not enough: JSON can store an explicit null,
    which .get() happily returns as None instead of falling back to {}."""
    return card.get(key) or {}


def build_verse_block(reference, text, css_class='scripture-item'):
    if not text:
        return ''
    return (f'<div class="{css_class}">'
            f'<p class="scripture-ref">{esc(reference)}</p>'
            f'<p class="scripture-text">«{esc(text)}»</p></div>\n')


def build_scripture_connections(card, strings):
    items = card.get('scripture_connections') or []
    if not items:
        return ''
    html = f'<div class="scripture-connections"><h3>{esc(strings["related_refs"])}</h3>\n'
    for s in items:
        html += build_verse_block(s.get('reference', ''), s.get('text', ''))
    html += '</div>\n'
    return html


def build_revelation(card):
    rev = card.get('revelation_key', '')
    return f'<div class="revelation-box">{esc(rev)}</div>\n' if rev else ''


# ── Card-type renderers ───────────────────────────────────────────────────────

def render_cinematic_scene(card, book, assets_dir, registry, counter, strings, lang):
    img_html, counter = build_image_block(book, assets_dir, card.get('image_url'), registry, counter)
    body = f"""{img_html}
<h1>{esc(card.get('title', ''))}</h1>
{paragraphs(card.get('narrative', ''))}
{build_verse_block(safe_dict(card, 'verse_overlay').get('reference', ''), safe_dict(card, 'verse_overlay').get('text', ''))}
{build_revelation(card)}"""
    return wrap_xhtml(card.get('title', ''), body, lang), counter


def render_scripture_moment(card, book, assets_dir, registry, counter, strings, lang):
    img_html, counter = build_image_block(book, assets_dir, card.get('image_url'), registry, counter)
    body = f"""{img_html}
{build_verse_block(card.get('verse_reference', ''), card.get('verse_text', ''))}
{paragraphs(card.get('reflection', ''))}
{build_scripture_connections(card, strings)}
{build_revelation(card)}"""
    return wrap_xhtml(card.get('verse_reference', 'Escritura'), body, lang), counter


def render_character_or_theological(card, book, assets_dir, registry, counter, strings, lang):
    img_html, counter = build_image_block(book, assets_dir, card.get('image_url'), registry, counter)
    body = f"""{img_html}
<h1>{esc(card.get('title', ''))}</h1>
<p class="card-subtitle">{esc(card.get('subtitle', ''))}</p>
{paragraphs(card.get('content', ''))}
{build_verse_block(safe_dict(card, 'verse_overlay').get('reference', ''), safe_dict(card, 'verse_overlay').get('text', ''))}
{build_scripture_connections(card, strings)}
{build_revelation(card)}"""
    return wrap_xhtml(card.get('title', ''), body, lang), counter


def render_interactive_moment(card, book, assets_dir, registry, counter, strings, lang):
    img_html, counter = build_image_block(book, assets_dir, card.get('image_url'), registry, counter)
    icon = card.get('icon', '')
    body = f"""{img_html}
<p class="icon-line">{icon}</p>
<h1>{esc(card.get('title', ''))}</h1>
<p class="card-subtitle">{esc(card.get('subtitle', ''))}</p>
<div class="question"><p>{esc(card.get('reflection_prompt', ''))}</p></div>"""
    return wrap_xhtml(card.get('title', ''), body, lang), counter


def render_discovery_activation(card, book, assets_dir, registry, counter, strings, lang):
    img_html, counter = build_image_block(book, assets_dir, card.get('image_url'), registry, counter)
    body = f"""{img_html}
<h1>{esc(card.get('title', '') or strings['your_encounter'])}</h1>
<p class="card-subtitle">{esc(card.get('subtitle', ''))}</p>
"""
    questions = card.get('discovery_questions') or []
    for q in questions:
        body += (f'<div class="question"><p class="question-cat">{esc(q.get("category", ""))}</p>'
                  f'<p>{esc(q.get("question", ""))}</p></div>\n')

    prayer = safe_dict(card, 'prayer')
    if prayer:
        title = prayer.get('title', strings['prayer_default'])
        paras = ''.join(f'<p>{esc(p)}</p>' for p in prayer.get('content', '').split('\n') if p.strip())
        body += f'<div class="prayer"><p class="prayer-title">{esc(title)}</p>{paras}</div>\n'

    return wrap_xhtml(card.get('title', '') or strings['your_encounter'], body, lang), counter


def render_completion(card, book, assets_dir, registry, counter, strings, lang):
    img_html, counter = build_image_block(book, assets_dir, card.get('image_url'), registry, counter)
    cv = safe_dict(card, 'completion_verse')
    celebration_icons = {
        'gentle_light': '✨', 'warm_glow': '🌅', 'triumphant': '🎉',
        'peaceful': '🕊️', 'joyful': '☀️',
    }
    icon = celebration_icons.get(card.get('celebration_type', ''), '✨')
    body = f"""{img_html}
<div class="completion">
<p class="celebration">{icon}</p>
{build_verse_block(cv.get('reference', ''), cv.get('text', ''), css_class='scripture-item')}
<p class="prompt">{esc(card.get('reflection_prompt', ''))}</p>
</div>"""
    return wrap_xhtml('Completado', body, lang), counter


RENDERERS = {
    'cinematic_scene': render_cinematic_scene,
    'scripture_moment': render_scripture_moment,
    'character_moment': render_character_or_theological,
    'theological_depth': render_character_or_theological,
    'interactive_moment': render_interactive_moment,
    'discovery_activation': render_discovery_activation,
    'completion': render_completion,
}


# ── index.json resolution ──────────────────────────────────────────────────────
# index.json (in devocionales-json/encounters/) carries the *authored* title,
# subtitle, scripture_reference, and intro_image per encounter per language —
# this is real cover copy written for each encounter, not just a derived
# fallback from meta.character. Always prefer it when available.

def load_index_entry(index_path, encounter_id):
    """encounter_id is the json data's own "id" field, e.g. "zacchaeus_001".
    Returns the matching index entry dict, or None if not found."""
    if not index_path:
        return None
    try:
        with open(index_path, encoding='utf-8') as f:
            index = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    for entry in index.get('encounters', []):
        if entry.get('id') == encounter_id:
            return entry
    return None


def resolve_cover_fields(data, index_entry, lang):
    """Index entry wins when present for this language; otherwise fall back
    to the per-encounter JSON's own meta/key_verse fields, then to id-derived
    defaults. Returns (title, subtitle, scripture_ref, intro_image_filename)."""
    meta = safe_dict(data, 'meta')

    title = subtitle = scripture_ref = intro_image = None
    if index_entry:
        title = (index_entry.get('titles') or {}).get(lang)
        subtitle = (index_entry.get('subtitles') or {}).get(lang)
        scripture_ref = (index_entry.get('scripture_reference') or {}).get(lang)
        intro_image = index_entry.get('intro_image')

    if not title:
        title = data.get('title') or meta.get('character') or data.get('id', '')
    if not subtitle:
        subtitle = data.get('subtitle') or ''
    if not scripture_ref:
        scripture_ref = meta.get('scripture_reference', '')

    return title, subtitle, scripture_ref, intro_image


# ── Cover ──────────────────────────────────────────────────────────────────────

def build_cover(data, strings, lang, index_entry, assets_dir, book, image_registry, img_counter):
    meta = safe_dict(data, 'meta')
    kv = safe_dict(data, 'key_verse')
    emoji = meta.get('emoji', '') or (index_entry or {}).get('emoji', '')
    character = meta.get('character', '')

    title, subtitle, scripture_ref, intro_image = resolve_cover_fields(data, index_entry, lang)

    img_html = ''
    if intro_image:
        img_html, img_counter = build_image_block(book, assets_dir, intro_image, image_registry, img_counter)

    # The index gives a crafted, often abstract title ("El Hombre en el
    # Árbol"). meta.character is the plain identity ("Zaqueo"). Show the
    # character name as a small kicker whenever the title doesn't already
    # spell it out, so the identity is never lost from the cover.
    character_html = ''
    if character and character.lower() not in title.lower():
        character_html = f'  <p class="character-kicker">{esc(character)}</p>\n'

    body = f"""<div class="cover">
{img_html}  <p class="emoji">{emoji}</p>
{character_html}  <h1>{esc(title)}</h1>
  <p class="scripture-passage">{esc(scripture_ref)}</p>
  <p class="subtitle">{esc(subtitle)}</p>
  <div class="key-verse">
    <p>«{esc(kv.get('text', ''))}»</p>
    <p class="ref">— {esc(kv.get('reference', ''))}</p>
  </div>
  <p class="meta-line">{esc(strings['cover_label'])} · {esc(data.get('bible_version', ''))} · {data.get('estimated_reading_minutes', '')} {esc(strings['reading_time'])}</p>
  <div class="welcome-tagline">
    <p>{esc(strings['welcome_title_line1'])}<br/>{esc(strings['welcome_title_line2'])}<br/>{esc(strings['welcome_title_line3'])}</p>
    <p class="welcome-subtitle">{esc(strings['welcome_subtitle'])}</p>
  </div>
</div>"""
    return wrap_xhtml(title, body, lang), img_counter


def build_colophon(data, strings, lang):
    """Closing page: Develop4God authorship credit + Bible translation notice.
    Placed as the last chapter so it doesn't interrupt the reading experience."""
    bible_version = data.get('bible_version', '')
    notice = bible_copyright_notice(bible_version, lang) if bible_version else ''

    body = f"""<div class="colophon">
<h1>{esc(strings['colophon_title'])}</h1>
<p class="app-credit">{esc(strings['app_credit'])}</p>
<p class="app-link"><a href="{esc(DEVELOP4GOD_URL)}">{esc(strings['get_app'])}</a>: {esc(DEVELOP4GOD_URL)}</p>
<h2>{esc(strings['scripture_heading'])}</h2>
<div class="notice"><p>{esc(notice)}</p></div>
<p class="small-note">{esc(bible_version)}</p>
</div>"""
    return wrap_xhtml(strings['colophon_title'], body, lang)


# ── Converter ─────────────────────────────────────────────────────────────────

def convert(input_path, assets_dir, output_path, index_path=None):
    with open(input_path, encoding='utf-8') as f:
        data = json.load(f)

    lang = data.get('language', 'en')
    strings = ui(lang)
    assets_dir = Path(assets_dir)

    # Auto-discover index.json sitting next to the encounters/<lang>/ folder
    # (i.e. encounters/index.json, one level up from the input file) if the
    # caller didn't pass one explicitly.
    if index_path is None:
        guess = Path(input_path).parent.parent / 'index.json'
        if guess.exists():
            index_path = guess

    index_entry = load_index_entry(index_path, data.get('id'))

    meta = safe_dict(data, 'meta')
    title, subtitle, scripture_ref, intro_image = resolve_cover_fields(data, index_entry, lang)

    book = epub.EpubBook()
    book.set_identifier(data.get('id', 'encounter_001'))
    book.set_title(title)
    book.set_language(lang)
    book.add_author('Develop4God')
    book.add_metadata('DC', 'description', subtitle or scripture_ref)

    css_item = epub.EpubItem(uid='style', file_name='style.css',
                              media_type='text/css', content=CSS.encode('utf-8'))
    book.add_item(css_item)
    chapters = []
    image_registry = {}
    img_counter = 1

    def make_ch(ch_title, fname, html_str):
        ch = epub.EpubHtml(title=ch_title or fname, file_name=fname, lang=lang)
        ch.content = html_str.encode('utf-8')
        ch.add_item(css_item)
        book.add_item(ch)
        chapters.append(ch)

    cover_html, img_counter = build_cover(data, strings, lang, index_entry, assets_dir, book, image_registry, img_counter)
    make_ch(title, 'cover.xhtml', cover_html)

    for card in sorted(data.get('cards', []), key=lambda c: c.get('order', 0)):
        ctype = card.get('type', '')
        renderer = RENDERERS.get(ctype)
        if not renderer:
            continue
        html_str, img_counter = renderer(card, book, assets_dir, image_registry, img_counter, strings, lang)
        if ctype == 'completion':
            ch_title = safe_dict(card, 'completion_verse').get('reference') or strings.get('amen', 'Amén')
        else:
            ch_title = card.get('title') or card.get('verse_reference') or ctype
        fname = f"card_{card.get('order', 0):02d}.xhtml"
        make_ch(ch_title, fname, html_str)

    make_ch(strings['colophon_title'], 'colophon.xhtml', build_colophon(data, strings, lang))

    book.toc = [(epub.Section(title), chapters)]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters

    epub.write_epub(output_path, book, options={'epub3_pages': False})
    return len(chapters), len(image_registry)


# ── Interactive menu helpers (sources.yml driven) ────────────────────────────

_SOURCES_FILE = Path(__file__).parent / 'sources.yml'


def _load_sources():
    with open(_SOURCES_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f)


def _fetch_url(url):
    resp = urlopen(url, timeout=30)
    return resp.read()


def _fetch_json(url):
    return json.loads(_fetch_url(url).decode('utf-8'))


def _prompt_choice(label, options, allow_multi=False):
    print(f'\n{label}')
    for i, (key, desc) in enumerate(options, 1):
        print(f'  {i}) {desc}')
    if allow_multi:
        print('  (comma-separated numbers, or "a" for all)')
    while True:
        raw = input('> ').strip()
        if allow_multi and raw.lower() == 'a':
            return [key for key, _ in options]
        try:
            if allow_multi:
                indices = [int(x.strip()) for x in raw.split(',')]
                picks = [options[i - 1][0] for i in indices if 1 <= i <= len(options)]
                if picks:
                    return picks
            else:
                idx = int(raw)
                if 1 <= idx <= len(options):
                    return options[idx - 1][0]
        except (ValueError, IndexError):
            pass
        print('  Invalid selection, try again.')


def _fetch_index(sources):
    jr = sources['json_repo']
    url = f"{jr['base_url']}/{jr['index']}"
    print(f'  Fetching index from {url} ...')
    return _fetch_json(url)


def _encounter_character(encounter_id):
    """Strip the version suffix (_001) from an encounter ID to get the character name."""
    return re.sub(r'_\d{3}$', '', encounter_id)


def _fetch_encounter_json(sources, encounter_id, lang, work_dir):
    jr = sources['json_repo']
    character = _encounter_character(encounter_id)
    path = jr['encounter_pattern'].format(lang=lang, character=character)
    url = f"{jr['base_url']}/{path}"
    print(f'  Fetching {url} ...')
    data = _fetch_json(url)
    local = work_dir / f'{character}_{lang}_001.json'
    local.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return str(local), data


def _fetch_encounter_assets(sources, encounter_id, work_dir):
    ar = sources['assets_repo']
    assets_path = ar['assets_pattern'].format(encounter_id=encounter_id)
    assets_dir = work_dir / 'assets' / encounter_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    api_url = f"https://api.github.com/repos/develop4God/Devocionales-assets/contents/{assets_path}"
    print(f'  Fetching asset list for {encounter_id} ...')
    try:
        listing = _fetch_json(api_url)
    except Exception as exc:
        print(f'  ⚠ Could not list assets: {exc}')
        return str(assets_dir)

    for item in listing:
        if item.get('type') != 'file':
            continue
        name = item['name']
        if not any(name.endswith(ext) for ext in ('.png', '.jpg', '.jpeg')):
            continue
        dl_url = item['download_url']
        dest = assets_dir / name
        if dest.exists():
            continue
        print(f'    ↓ {name}')
        dest.write_bytes(_fetch_url(dl_url))

    return str(assets_dir)


def interactive():
    print('═' * 50)
    print('  Encounter → EPUB  Converter')
    print('═' * 50)

    sources = _load_sources()

    # 1. Select language
    lang_options = [(entry['code'], f"{entry['code']}  —  {entry['name']}") for entry in sources['languages']]
    lang = _prompt_choice('Select language:', lang_options)

    # 2. Fetch index and list encounters for that language
    index_data = _fetch_index(sources)
    encounters = []
    for entry in index_data.get('encounters', []):
        eid = entry.get('id', '')
        title = (entry.get('titles') or {}).get(lang) or eid
        encounters.append((eid, f'{eid}  —  {title}'))

    if not encounters:
        print(f'No encounters found in index for "{lang}".')
        sys.exit(1)

    selected = _prompt_choice('Select encounter(s):', encounters, allow_multi=True)
    if isinstance(selected, str):
        selected = [selected]

    # 3. Output directory
    default_out = str(Path(__file__).parent / 'output')
    out_dir_str = input(f'\nOutput directory [{default_out}]: ').strip() or default_out
    out_dir = Path(out_dir_str)
    out_dir.mkdir(parents=True, exist_ok=True)

    import tempfile
    with tempfile.TemporaryDirectory(prefix='epub_') as tmp:
        work_dir = Path(tmp)

        index_local = work_dir / 'index.json'
        index_local.write_text(json.dumps(index_data, ensure_ascii=False, indent=2))

        print(f'\nConverting {len(selected)} encounter(s)...\n')
        ok = 0
        for encounter_id in selected:
            try:
                json_path, _ = _fetch_encounter_json(sources, encounter_id, lang, work_dir)
                assets_dir = _fetch_encounter_assets(sources, encounter_id, work_dir)
                character = _encounter_character(encounter_id)
                out_path = out_dir / f'{character}_{lang}_001.epub'
                n_ch, n_img = convert(json_path, assets_dir, str(out_path), index_path=str(index_local))
                print(f'  ✅  {out_path.name}  ({n_ch} chapters, {n_img} images)')
                ok += 1
            except Exception as exc:
                print(f'  ❌  {encounter_id}: {exc}')

    print(f'\nDone. {ok}/{len(selected)} EPUB(s) written to {out_dir}')


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        interactive()
    elif len(sys.argv) >= 3:
        inp = sys.argv[1]
        assets = sys.argv[2]
        out = sys.argv[3] if len(sys.argv) >= 4 else str(Path(inp).with_suffix('.epub'))
        idx = sys.argv[4] if len(sys.argv) >= 5 else None
        n_chapters, n_images = convert(inp, assets, out, index_path=idx)
        print(f"✅  {out}  ({n_chapters} chapters, {n_images} images embedded)")
    else:
        print(__doc__)
        sys.exit(1)
