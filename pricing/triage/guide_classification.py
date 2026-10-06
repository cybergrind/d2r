"""Source-purpose classification, independent of whether the assessor passes a row."""

CONTEXT_SECTIONS = {
    'guides/pricing-primer.html#s2-why': 'Explains base demand and mechanics; variant verdicts are in the base tables',
    'guides/pricing-primer.html#twin': 'Navigation summary; detailed tables contain the item cases',
    **{
        f'guides/pricing-primer.html#d{i}': 'Decision-flow summary; concrete item verdicts belong to its linked tables'
        for i in range(8)
    },
    'guides/warlock.html#guide-3-1-item-level-why-where-the-base-comes-from-matters': (
        'Crafting and shopping mechanics, not a drop verdict'
    ),
    'guides/warlock.html#guide-3-2-shopping-list-per-craft-from-one-pindle-anya-run': (
        'Crafting ingredient acquisition instructions, not a drop verdict'
    ),
}
OWN_SECTIONS = {
    'guides/pricing.html#s6',
    *{f'guides/warlock.html#{section}' for section in ('s0', 's0-1', 's1', 's2', 's3')},
}
CONTEXT_ROWS = {
    'guides/pricing.html#s8:5': (
        'Historical orb note omits all three staffmod identities; '
        'no exact item or transferable verdict can be reconstructed'
    ),
    'guides/pricing.html#s8:17': (
        'Historical glove title conflicts with native of Thawing eligibility; not a reproducible item case'
    ),
    'guides/pricing.html#s2-yellow:10': 'Introduces the following slot-specific rare-item tests',
    'guides/pricing.html#s3:5': 'Required level is an affix clue, explicitly not a verdict gate',
    **{
        f'guides/pricing-primer.html#s2-1:{i}': 'Base facet or socket mechanic; variant verdicts are in the tables'
        for i in range(5, 9)
    },
    'guides/pricing-primer.html#s2-4:3': 'Runeword naming equivalence, not a drop verdict',
    'guides/pricing-primer.html#s2-2:4': (
        'Larzuk/cube socket counts and runeword rarity eligibility; no keep/sell or own-use recommendation'
    ),
    'guides/pindle-anya.html#s5:103': 'Table group heading for the affixed items that follow',
    'guides/warlock.html#s0:10': 'Combat rotation advice for the current character',
    'guides/warlock.html#s0:12': 'Historical mercenary equipment observation; upgrades are in section 0.1',
    **{
        f'guides/warlock.html#s0-1:{i}': 'Mercenary combat tactics or unverified mechanics, not an equipment verdict'
        for i in (5, 6, 7)
    },
    'guides/warlock.html#s5:5': 'Failed-unique durability explanation; not an item keep rule',
}


def classify(row):
    identity, source = row['id'], row['source']
    category = 'verdict'
    reason = 'Item or variant trade guidance: ' + row.get('description', row.get('text', identity))[:140]
    if row['kind'] == 'context':
        category, reason = 'context', row['context_reason']
    elif identity in CONTEXT_ROWS or source in CONTEXT_SECTIONS:
        category, reason = 'context', CONTEXT_ROWS.get(identity, CONTEXT_SECTIONS.get(source))
    elif source in OWN_SECTIONS or identity == 'guides/pricing.html#s2-blue:9':
        category, reason = 'own-use', 'Player or mercenary equipment/crafting recommendation; test against own.json'
    elif source in {'guides/warlock.html#s5', 'guides/warlock.html#s6'} or (
        source == 'guides/pindle-anya.html#s3' and identity != 'guides/pindle-anya.html#s3:30'
    ):
        category, reason = 'pickup', 'Ground pickup or filter instruction before item identification'
    return {'classification': category, 'classification_reason': reason}
