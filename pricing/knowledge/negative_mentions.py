"""Reviewed negative guide occurrences; other occurrences keep their own demand."""

import hashlib


# Exact source review: ECHOING_UBERS_REMAINING_SOURCES.json. The linked tooltip
# happens to use a Magic Find profile; its surrounding Ubers advice says remove.
NEGATIVE = {
    ('pricing/raw/mr/guides__echoing-strike-warlock-guide.html', 11): {
        'sha256': '08024534e035dd39cc599510f2e8bdafb6596c7aa27fc1f0c4fcfab24f13660c',
        'label': "Gheed's Fortune",
        'side': 'player',
        'slot': 'unspecified',
    },
}


def recommendation(source_id, ordinal, mention, raw_html):
    expected = NEGATIVE.get((source_id, ordinal))
    if expected is None:
        return True
    if hashlib.sha256(raw_html.encode()).hexdigest() != expected['sha256'] or any(
        mention.get(key) != expected[key] for key in ('label', 'side', 'slot')
    ):
        raise ValueError('Reviewed negative demand evidence changed; source review required')
    return False
