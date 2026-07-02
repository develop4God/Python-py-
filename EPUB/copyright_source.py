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


def get_copyright_text(copyright_map, language, version):
    """Replicates CopyrightUtils.getCopyrightText: extracts a version code
    from a trailing "(CODE)" if present, looks it up under `language`,
    falling back to that language's 'default', falling back to English."""
    match = _VERSION_CODE_RE.search(version)
    version_key = match.group(1) if match else version

    lang_map = copyright_map.get(language) or copyright_map['en']
    return lang_map.get(version_key) or lang_map['default']
