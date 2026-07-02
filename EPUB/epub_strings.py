"""epub_strings.py — builds the per-language `strings` dict every EPUB
renderer consumes, fetched live from the devocional_nuevo app's i18n.
No local copy of the app's translated text is kept in this converter."""

from i18n_source import fetch_i18n

# strings-key -> dotted path into the app's i18n JSON
I18N_KEY_MAP = {
    'welcome_title_line1': 'encounters.welcome_title_line1',
    'welcome_title_line2': 'encounters.welcome_title_line2',
    'welcome_title_line3': 'encounters.welcome_title_line3',
    'welcome_subtitle': 'encounters.welcome_subtitle',
    'cover_label': 'encounters.section_title',
    'related_refs': 'encounters.deeper_connections',
    'prayer_default': 'encounters.prayer_label',
    'app_credit': 'about.developed_by',
    'colophon_title': 'settings.about',
}


def _dotted_get(d, path):
    """path is 'a.b.c' -> d['a']['b']['c']. Raises KeyError if any segment
    is missing — a renamed/removed app key must surface immediately, not
    fall back to guessed text."""
    node = d
    for part in path.split('.'):
        node = node[part]
    return node


def build_strings(lang):
    """Fetches this language's i18n live from GitHub and maps the keys the
    EPUB chrome needs. Raises if the fetch fails or a mapped key is missing."""
    i18n = fetch_i18n(lang)
    return {key: _dotted_get(i18n, path) for key, path in I18N_KEY_MAP.items()}
