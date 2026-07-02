"""copyright_source.py — fetches and parses copyright_utils.dart from the
devocional_nuevo app: the single source of truth for Bible-translation
copyright notices. Mirrors CopyrightUtils.getCopyrightText()'s lookup logic
exactly (version-code extraction, per-language default, English fallback)
so the EPUB never carries its own copy of this legal text."""

import re
from pathlib import Path
from urllib.request import urlopen

import yaml

_SOURCES_FILE = Path(__file__).parent / 'sources.yml'
_VERSION_CODE_RE = re.compile(r'\(([A-Z0-9]+)\)$')
_LANG_BLOCK_RE = re.compile(r"'(\w+)':\s*\{")
_KV_RE = re.compile(r"'((?:[^'\\]|\\.)*)':\s*((?:'(?:[^'\\]|\\.)*'\s*)+)", re.DOTALL)
_STR_LIT_RE = re.compile(r"'((?:[^'\\]|\\.)*)'")


def _app_repo():
    with open(_SOURCES_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f)['app_repo']


def _extract_braces(s, start_idx):
    """s[start_idx] is just past an opening '{'. Returns (body, index_after_closing_brace)."""
    depth = 1
    i = start_idx
    while depth > 0:
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
        i += 1
    return s[start_idx:i - 1], i


def fetch_copyright_map():
    """Downloads and parses copyright_utils.dart's `copyrightMap` literal
    into {lang: {version_code_or_display_name: text, 'default': text}}.
    Raises if the file can't be fetched or the expected literal isn't found."""
    repo = _app_repo()
    url = f"{repo['base_url']}/{repo['copyright_utils']}"
    with urlopen(url, timeout=30) as resp:
        text = resp.read().decode('utf-8')

    marker = 'copyrightMap = {'
    start = text.index(marker) + len(marker)
    outer_body, _ = _extract_braces(text, start)
    outer_body = re.sub(r'//[^\n]*', '', outer_body)

    result = {}
    pos = 0
    while True:
        m = _LANG_BLOCK_RE.search(outer_body, pos)
        if not m:
            break
        lang = m.group(1)
        block, pos = _extract_braces(outer_body, m.end())
        entries = {}
        for km in _KV_RE.finditer(block):
            key = km.group(1)
            value = ''.join(_STR_LIT_RE.findall(km.group(2)))
            entries[key] = value
        result[lang] = entries
    return result



def get_copyright_text(copyright_map, language, version, display_name_to_code=None):
    """Matches `version` (the encounter JSON's bible_version) against the
    app's copyright map: tries the bare value, then the code extracted from
    a trailing "(CODE)", then any key whose "Name (CODE)" starts with
    `version`, then — if `display_name_to_code` (from
    bible_versions_source.fetch_display_name_to_code) is given — the code
    for this language's display name, per the bible_versions repo's
    authoritative code<->name index. Falls back to that language's
    'default', then to English."""
    lang_map = copyright_map.get(language) or copyright_map['en']

    if version in lang_map:
        return lang_map[version]

    match = _VERSION_CODE_RE.search(version)
    if match and match.group(1) in lang_map:
        return lang_map[match.group(1)]

    for key in lang_map:
        if key.startswith(f'{version} ('):
            return lang_map[key]

    if display_name_to_code:
        code = display_name_to_code.get(language, {}).get(version)
        if code and code in lang_map:
            return lang_map[code]

    return lang_map['default']
