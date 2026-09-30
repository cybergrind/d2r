"""Primary-source reviews of ordinary named definitions for Non-Ladder."""

import hashlib
import html
import re


ITEMS = 'third-parties/d2data/json/base/setitems.json'
SETS = 'third-parties/d2data/json/base/sets.json'
PATCH = 'pricing/raw/mr/leveling/blizzard-season15.html'
NAMES = frozenset(('Angelic Halo', 'Angelic Wings', 'Angelic Mantle', 'Angelic Sickle'))
UNIQUE_ITEMS = 'third-parties/d2data/json/base/uniqueitems.json'
UNIQUE_IDS = frozenset((12, 51, 54, 59, 62, 80, 101, 121, 154))


def ordinary_angelic(root, read, inputs):
    """Bind the ordinary sources to the cached primary mode restriction."""
    quotes = (
        'Items that have been changed will ONLY be available in Ladder.',
        'Angelic Sickle Added Damage +6 (3 set items).',
        'Angelic Mantle Added +100% Damage to Undead (3 set items).',
        'Full set bonus Added +1 to All Skills.',
    )
    review_patch(root, inputs, quotes)
    return (
        read(ITEMS),
        read(SETS),
        {
            'scope': 'softcore_non_ladder',
            'reviewed_at': '2026-09-30',
            'sources': [ITEMS, SETS, PATCH],
            'quotes': list(quotes),
            'decision': 'Ordinary bonuses are the Non-Ladder default; changed Ladder bonuses remain archived.',
        },
    )


def review_patch(root, inputs, quotes):
    raw = (root / PATCH).read_bytes()
    text = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', raw.decode())).split())
    if any(quote not in text for quote in quotes):
        raise ValueError('Non-Ladder mode evidence changed; review required')
    inputs[PATCH] = hashlib.sha256(raw).hexdigest()


def ordinary_unique_records(root, read, inputs):
    quotes = (
        'Items that have been changed will ONLY be available in Ladder.',
        'Bloodletter Added 20% Faster Run/Walk.',
        'The Battlebranch Reduced base Item level from 34 to 30. Reduced Required Level from 25 to 17.',
        "Rogue's Bow Added +[1-3] to either Cold Arrow or Fire Arrow (Amazon Only).",
        'Pluckeye Added +25% Increased Attack Speed.',
        'Bane Ash Removed +20% Increased Attack Speed.',
        'Gravenspine Added +10% Faster Cast Rate.',
        "Blinkbat's Form Increased +10% Faster Run/Walk to +30%.",
        'The Ward Added Socketed (1).',
        'Manald Heal Added +10% Faster Cast Rate.',
    )
    review_patch(root, inputs, quotes)
    return read(UNIQUE_ITEMS), {
        'scope': 'softcore_non_ladder',
        'reviewed_at': '2026-09-30',
        'sources': [UNIQUE_ITEMS, PATCH],
        'quotes': list(quotes),
        'decision': 'Ordinary unique versions are the Non-Ladder default; changed Ladder versions remain archived.',
    }
