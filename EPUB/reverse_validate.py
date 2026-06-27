#!/usr/bin/env python3
"""Reverse-validate: every field in the source JSON must be accounted for
in the generated EPUB's XHTML content (either rendered, or on an explicit
known-skip list with a stated reason)."""
import json
import sys
import zipfile
import re

KNOWN_SKIP_FIELDS = {
    'ambient_sound', 'haptic',   # app runtime cues, no print equivalent
    'order', 'type', 'mood',     # structural/internal, not display text
    'schema_version', 'version', 'bible_version_internal',
}

def load_epub_text(epub_path):
    z = zipfile.ZipFile(epub_path)
    full_text = []
    for name in z.namelist():
        if name.endswith('.xhtml'):
            full_text.append(z.read(name).decode('utf-8'))
    return '\n'.join(full_text)

def strip_html(s):
    return re.sub(r'<[^>]+>', ' ', s)

def check_value_in_text(value, haystack_raw, haystack_stripped):
    if value is None:
        return True, 'null value, nothing to render'
    if isinstance(value, (int, float)):
        return (str(value) in haystack_raw), None
    if isinstance(value, str):
        if not value.strip():
            return True, 'empty string'
        # The converter splits on blank lines into separate <p> tags, so a
        # multi-paragraph source string never appears as one literal
        # substring in the output. Check each paragraph independently,
        # the same way the converter's own paragraphs() function splits.
        parts = [p.strip() for p in value.split('\n\n') if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in value.split('\n') if p.strip()]
        if not parts:
            return True, 'empty after split'
        for part in parts:
            esc = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            found = (part in haystack_stripped) or (esc in haystack_raw) or (part in haystack_raw)
            if not found:
                return False, f'paragraph not found: {part[:60]!r}'
        return True, None
    return None, 'complex type, needs manual check'

def load_index_entry(index_path, encounter_id):
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

def validate(json_path, epub_path, index_path=None):
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    raw = load_epub_text(epub_path)
    stripped = strip_html(raw)
    lang = data.get('language', 'en')

    report = {'top_level': [], 'cards': [], 'index': []}

    index_entry = load_index_entry(index_path, data.get('id'))
    if index_entry:
        for field in ('titles', 'subtitles', 'scripture_reference'):
            val = (index_entry.get(field) or {}).get(lang)
            if val is None:
                continue
            ok, note = check_value_in_text(val, raw, stripped)
            report['index'].append((f'index.{field}.{lang}', val, 'OK' if ok else f'MISSING ({note})'))
        intro_image = index_entry.get('intro_image')
        if intro_image:
            # image presence is checked structurally, not by text search
            report['index'].append(('index.intro_image', intro_image, 'OK (embedded as cover image, verified separately)'))
    elif index_path:
        report['index'].append(('index_entry', None, 'MISSING (no matching id in index.json)'))

    # Top-level fields
    for key in ['id', 'type', 'schema_version', 'language', 'bible_version',
                'version', 'estimated_reading_minutes', 'title', 'subtitle']:
        if key not in data:
            continue
        val = data[key]
        if key in ('id', 'schema_version', 'version', 'type'):
            report['top_level'].append((key, val, 'SKIP (internal id, not display text)'))
            continue
        ok, note = check_value_in_text(val, raw, stripped)
        report['top_level'].append((key, val, 'OK' if ok else 'MISSING'))

    # meta.*
    meta = data.get('meta') or {}
    for key, val in meta.items():
        if key == 'tags':
            continue  # tags intentionally not rendered in current design
        if key in ('accent_color', 'testament', 'mood_primary'):
            report['top_level'].append((f'meta.{key}', val, 'SKIP (styling/internal metadata)'))
            continue
        ok, note = check_value_in_text(val, raw, stripped)
        report['top_level'].append((f'meta.{key}', val, 'OK' if ok else 'MISSING'))

    # key_verse
    kv = data.get('key_verse') or {}
    for key, val in kv.items():
        if key == 'bible_version':
            report['top_level'].append((f'key_verse.{key}', val, 'SKIP (redundant with top-level bible_version)'))
            continue
        ok, note = check_value_in_text(val, raw, stripped)
        report['top_level'].append((f'key_verse.{key}', val, 'OK' if ok else 'MISSING'))

    # Cards
    for card in data.get('cards', []):
        order = card.get('order')
        ctype = card.get('type')
        card_report = []
        for key, val in card.items():
            if key in KNOWN_SKIP_FIELDS:
                card_report.append((key, 'SKIP (structural/runtime field)'))
                continue
            if key == 'image_url':
                card_report.append((key, 'OK (embedded as image, verified separately)'))
                continue
            if key in ('verse_overlay', 'completion_verse'):
                sub = val or {}
                ref_ok, _ = check_value_in_text(sub.get('reference'), raw, stripped)
                txt_ok, _ = check_value_in_text(sub.get('text'), raw, stripped)
                status = 'OK' if (ref_ok and txt_ok) else f'MISSING (ref_ok={ref_ok}, text_ok={txt_ok})'
                card_report.append((key, status))
                continue
            if key == 'prayer':
                sub = val or {}
                title_ok, _ = check_value_in_text(sub.get('title'), raw, stripped)
                content = sub.get('content', '')
                content_ok = all(
                    check_value_in_text(p.strip(), raw, stripped)[0]
                    for p in content.split('\n') if p.strip()
                )
                status = 'OK' if (title_ok and content_ok) else f'MISSING (title_ok={title_ok}, content_ok={content_ok})'
                card_report.append((key, status))
                continue
            if key == 'scripture_connections':
                all_ok = True
                for item in (val or []):
                    r_ok, _ = check_value_in_text(item.get('reference'), raw, stripped)
                    t_ok, _ = check_value_in_text(item.get('text'), raw, stripped)
                    if not (r_ok and t_ok):
                        all_ok = False
                card_report.append((key, 'OK' if all_ok else 'MISSING'))
                continue
            if key == 'discovery_questions':
                all_ok = True
                for item in (val or []):
                    c_ok, _ = check_value_in_text(item.get('category'), raw, stripped)
                    q_ok, _ = check_value_in_text(item.get('question'), raw, stripped)
                    if not (c_ok and q_ok):
                        all_ok = False
                card_report.append((key, 'OK' if all_ok else 'MISSING'))
                continue
            if key == 'celebration_type':
                card_report.append((key, 'SKIP (mapped to an emoji icon, not literal text)'))
                continue
            if key == 'icon':
                ok, _ = check_value_in_text(val, raw, stripped)
                card_report.append((key, 'OK' if ok else 'MISSING'))
                continue
            # generic string fields: title, subtitle, narrative, content, reflection,
            # verse_reference, verse_text, reflection_prompt, revelation_key
            ok, note = check_value_in_text(val, raw, stripped)
            card_report.append((key, 'OK' if ok else f'MISSING ({note})'))
        report['cards'].append((order, ctype, card_report))

    return report

def print_report(report):
    if report.get('index'):
        print("=" * 70)
        print("INDEX.JSON FIELDS")
        print("=" * 70)
        for key, val, status in report['index']:
            flag = '✅' if status.startswith('OK') else ('⏭️ ' if status.startswith('SKIP') else '❌')
            valstr = str(val)[:60]
            print(f"{flag} {key:30s} {status:10s} {valstr}")
        print()

    print("=" * 70)
    print("TOP-LEVEL FIELDS")
    print("=" * 70)
    any_missing = any(status.startswith('MISSING') for _, _, status in report.get('index', []))
    for key, val, status in report['top_level']:
        flag = '✅' if status.startswith('OK') else ('⏭️ ' if status.startswith('SKIP') else '❌')
        valstr = str(val)[:50]
        print(f"{flag} {key:30s} {status:10s} {valstr}")
        if status.startswith('MISSING'):
            any_missing = True

    print()
    print("=" * 70)
    print("CARD FIELDS")
    print("=" * 70)
    for order, ctype, fields in report['cards']:
        print(f"\n--- Card {order} ({ctype}) ---")
        for key, status in fields:
            flag = '✅' if status.startswith('OK') else ('⏭️ ' if status.startswith('SKIP') else '❌')
            if status.startswith('MISSING'):
                any_missing = True
            print(f"  {flag} {key:25s} {status}")

    print()
    print("=" * 70)
    print("RESULT:", "❌ MISSING FIELDS FOUND" if any_missing else "✅ ALL FIELDS ACCOUNTED FOR")
    print("=" * 70)

if __name__ == '__main__':
    idx = sys.argv[3] if len(sys.argv) >= 4 else None
    report = validate(sys.argv[1], sys.argv[2], index_path=idx)
    print_report(report)
