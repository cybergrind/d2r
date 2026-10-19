"""Traderie scope decisions (AGENTS.md rule 1), shared by the predicate's test and its callers' tests."""

ROTW = {
    799: ('string', 'softcore'),
    800: ('bool', False),
    798: ('string', 'PC'),
    1854: ('string', 'reign of the warlock'),
}


def changed(**changes):
    """ROTW with properties replaced (`p1854=('string', 'classic')`) or removed (`p1854=None`)."""
    properties = dict(ROTW)
    for key, value in changes.items():
        if value is None:
            properties.pop(int(key[1:]))
        else:
            properties[int(key[1:])] = value
    return properties


# (case id, raw listing properties, scope_status)
CASES = [
    ('rotw', ROTW, 'verified'),
    ('rotw-and-lod', changed(p1854=('string', 'lord of destruction,reign of the warlock')), 'verified'),
    ('rotw-title-case', changed(p1854=('string', 'Reign of the Warlock')), 'verified'),
    ('no-version', changed(p1854=None), 'unknown'),  # pricecheck and wp_b_buckets kept this until 2026-10-19
    ('empty-version', changed(p1854=('string', '')), 'unknown'),
    ('unknown-version', changed(p1854=('string', 'beta')), 'unknown'),
    ('lod', changed(p1854=('string', 'lord of destruction')), 'rejected'),
    ('classic', changed(p1854=('string', 'classic')), 'rejected'),
    ('classic-base-game', changed(p1854=('string', 'classic (base game)')), 'rejected'),
    ('lod-and-classic', changed(p1854=('string', 'lord of destruction,classic')), 'rejected'),
    ('hardcore', changed(p799=('string', 'hardcore')), 'rejected'),
    ('ladder', changed(p800=('bool', True)), 'rejected'),
    ('numeric-ladder-flag', changed(p800=('number', 0)), 'rejected'),
    ('console', changed(p798=('string', 'Playstation')), 'rejected'),
    ('no-mode', changed(p799=None), 'unknown'),
    ('no-ladder-flag', changed(p800=None), 'unknown'),
    ('no-platform', changed(p798=None), 'unknown'),
    ('nothing', {}, 'unknown'),
]
IDS = [case for case, _, _ in CASES]


def raw_properties(properties):
    return [{'property_id': pid, 'type': kind, kind: value} for pid, (kind, value) in properties.items()]


def listings(**fields):
    """One Traderie listing per case; `id` is the case id, each from its own seller, priced 1 Ist."""
    return [
        {
            'id': case,
            'seller_id': f'seller-{case}',
            'updated_at': '2026-10-19T00:00:00Z',
            'amount': 1,
            'prices': [{'name': 'Ist Rune', 'quantity': 1, 'group': 0, 'type': 'runes'}],
            'properties': raw_properties(properties),
            **fields,
        }
        for case, properties, _ in CASES
    ]


VERIFIED = [case for case, _, status in CASES if status == 'verified']
