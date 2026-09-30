"""Remaining named glove sources retain caster breakpoints and set companions."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'blizzard-mf-chance-guards': ('Sorceress', 105),
    'lightning-mf-chance-guards': ('Sorceress', 117),
    'mirrored-blades-warlock-guide-1-laying-hands': ('Warlock', None),
    'mirrored-blades-warlock-guide-2-laying-hands': ('Warlock', None),
    'dream-paladin-0-laying-hands': ('Paladin', None),
    'dream-paladin-1-laying-hands': ('Paladin', None),
    'echoing-strike-warlock-guide-1-trang-claws': ('Warlock', 125),
    'echoing-strike-warlock-guide-2-trang-claws': ('Warlock', 125),
    'echoing-strike-warlock-guide-3-trang-claws': ('Warlock', None),
    'fissure-druid-3-magefist': ('Druid', None),
    'blizzard-sorceress-1-trang-claws': ('Sorceress', 105),
}


def test_exact_glove_sources_preserve_build_qualifications():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 11
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        klass, fcr = EXPECTED[row['profile_id']]
        assert {'op': 'context_eq', 'field': 'player_class', 'value': klass} in row['required_predicates']
        if fcr:
            assert {'op': 'context_at_least', 'field': 'player_total_fcr', 'value': fcr} in row['required_predicates']
        if 'chance-guards' in row['profile_id']:
            assert row['required_dependencies'] == [
                {'op': 'context_contains', 'field': 'player_items', 'value': name}
                for name in ("Tal Rasha's Guardianship", "Tal Rasha's Fine-Spun Cloth", "Tal Rasha's Adjudication")
            ]
        if 'laying-hands' in row['profile_id']:
            assert any('not general damage' in text for text in row['required_conditions'])
        assert row['required_conditions']
