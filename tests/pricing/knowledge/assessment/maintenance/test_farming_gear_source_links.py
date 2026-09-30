"""Farming source links retain class, breakpoint and companion requirements."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'berserk-starter-nagelring': ('Barbarian', None, None),
    'strafe-amazon-1-laying-hands': ('Amazon', None, None),
    'berserk-barbarian-1-goldwrap': ('Barbarian', None, None),
    'lightning-strike-starter-nagelring': ('Amazon', None, None),
    'gold-find-barbarian-3-goldwrap': ('Barbarian', None, None),
    'meteor-mf-war-traveler': ('Sorceress', 105, 60),
    'gold-find-barbarian-1-goldwrap': ('Barbarian', None, None),
    'gold-find-barbarian-2-goldwrap': ('Barbarian', 105, None),
    'enchant-mf-nagelring': ('Sorceress', None, None),
    'lightning-mf-war-traveler': ('Sorceress', 117, None),
    'blizzard-mf-war-traveler': ('Sorceress', 105, None),
    'meteor-mf-chance-guards': ('Sorceress', 105, 60),
    'fire-warlock-guide-2-goldwrap': ('Warlock', None, None),
    'berserk-standard-nagelring': ('Barbarian', None, None),
}
TAL_SETUP = {
    'meteor-mf-war-traveler',
    'lightning-mf-war-traveler',
    'blizzard-mf-war-traveler',
    'meteor-mf-chance-guards',
}


def test_farming_source_links_preserve_breakpoints_and_tal_companions():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 14
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        occurrences,
        profiles,
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        klass, fcr, fhr = EXPECTED[row['profile_id']]
        predicates = row['required_predicates']
        assert {'op': 'context_eq', 'field': 'player_class', 'value': klass} in predicates
        for field, threshold in (('player_total_fcr', fcr), ('player_total_fhr', fhr)):
            assert [p for p in predicates if p.get('field') == field] == (
                [] if threshold is None else [{'op': 'context_at_least', 'field': field, 'value': threshold}]
            )
        dependencies = row.get('required_dependencies', [])
        assert dependencies == (
            [
                {'op': 'context_contains', 'field': 'player_items', 'value': name}
                for name in ("Tal Rasha's Guardianship", "Tal Rasha's Fine-Spun Cloth", "Tal Rasha's Adjudication")
            ]
            if row['profile_id'] in TAL_SETUP
            else []
        )
