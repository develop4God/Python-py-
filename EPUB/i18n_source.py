"""i18n_source.py — fetches the devocional_nuevo app's i18n JSON files live
from GitHub. Single responsibility: know the URL, download, parse.
No caching, no fallback — a failed fetch is a failed fetch."""

import json
from pathlib import Path
from urllib.request import urlopen

import yaml

_SOURCES_FILE = Path(__file__).parent / 'sources.yml'


def _app_repo():
    with open(_SOURCES_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f)['app_repo']


def fetch_i18n(lang):
    """Returns the parsed i18n dict for `lang`. Raises on any network or
    parse failure — callers must not silently swallow this."""
    repo = _app_repo()
    url = f"{repo['base_url']}/{repo['i18n_pattern'].format(lang=lang)}"
    with urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def list_available_languages():
    """Returns the language codes the app actually ships, derived from the
    filenames under i18n/ in the app repo — never a hardcoded list."""
    repo = _app_repo()
    with urlopen(repo['i18n_dir_api'], timeout=30) as resp:
        listing = json.loads(resp.read().decode('utf-8'))
    return sorted(Path(item['name']).stem for item in listing if item['name'].endswith('.json'))
