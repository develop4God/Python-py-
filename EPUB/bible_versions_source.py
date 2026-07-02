"""bible_versions_source.py — fetches the auto-generated bible_versions repo
index: the single source of truth mapping each language's Bible version
codes to their display names (e.g. ar: NAV <-> "الترجمة العربية الجديدة").
Used to resolve devocionales-json's bible_version display names to the
codes copyright_utils.dart keys its notices by."""

import json
from pathlib import Path
from urllib.request import urlopen

import yaml

_SOURCES_FILE = Path(__file__).parent / 'sources.yml'


def _bible_versions_repo():
    with open(_SOURCES_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f)['bible_versions_repo']


def fetch_display_name_to_code():
    """Returns {lang: {display_name: code}} built from index.json's
    languages[lang].versions[code].name. Raises on fetch/parse failure."""
    repo = _bible_versions_repo()
    with urlopen(repo['index'], timeout=30) as resp:
        index = json.loads(resp.read().decode('utf-8'))

    result = {}
    for lang, entry in index['languages'].items():
        result[lang] = {v['name']: code for code, v in entry['versions'].items()}
    return result
