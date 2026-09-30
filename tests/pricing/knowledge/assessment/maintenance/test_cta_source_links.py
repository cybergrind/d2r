"""Prebuff source coverage must distinguish swap companions and active buffs."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
WARLOCK = (
    'echoing-ubers',
    'abyss-standard',
    'abyss-mf',
    'mirrored-standard',
    'fire-standard',
    'echoing-standard',
    'fire-mf',
    'echoing-mf',
    'mirrored-ubers',
)
SORCERESS = (
    'meteor-mf',
    'blizzard-set',
    'lightning-mf',
    'lightning-standard',
    'blizzard-mf',
    'meteor-standard',
    'meteor-set',
)
EXPECTED = {
    f'{prefix}-cta-prebuff': klass
    for klass, prefixes in (('Warlock', WARLOCK), ('Sorceress', SORCERESS))
    for prefix in prefixes
}
NO_SPIRIT = {'meteor-mf-cta-prebuff', 'blizzard-mf-cta-prebuff'}


def test_cta_source_reviews_preserve_native_shouts_and_actual_swap_companion():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 16
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        profiles,
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    by_id = {r['id']: r for r in profiles}
    for row in rows:
        pid = row['profile_id']
        assert by_id[pid]['slot'] == 'Weapon-Swap'
        assert row['required_predicates'] == [
            {'op': 'context_eq', 'field': 'player_class', 'value': EXPECTED[pid]},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', 'crs'),
                    ('runeword', 'Call to Arms'),
                    ('sockets', 5),
                    ('socket_contents', 'filled'),
                )
            ],
            {'op': 'stat_at_least', 'key': '97:149', 'value': 1, 'absent_is_zero': True},
            {'op': 'stat_at_least', 'key': '97:155', 'value': 2, 'absent_is_zero': True},
        ]
        assert row['required_dependencies'] == (
            []
            if pid in NO_SPIRIT
            else [
                {'op': 'context_contains', 'field': 'player_swap_items', 'value': 'Spirit'},
            ]
        )
        assert row['required_conditions'] == [
            'Verify weapon and swap-shield equip requirements; cast Battle Command twice, then Battle Orders. '
            'This gear assessment does not establish an active buff.',
        ]
