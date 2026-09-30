"""Socket-decorated sources retain the correct attack stat and resistance floor."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'dream-paladin-1-merc-shaftstop-ias-res': (93, 15),
    'dream-paladin-2-merc-shaftstop-ias-res': (93, 15),
    'lightning-strike-amazon-1-merc-shaftstop-ias-res': (93, 15),
    'smite-paladin-1-merc-gaze-max-res': (22, 11),
    'smite-paladin-2-merc-gaze-max-res': (22, 11),
}


def test_reviewed_resistance_jewel_sources_keep_actual_child_guards():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 5
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert all(r['state'] == 'reviewed' for r in result)
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    for row in rows:
        stat, value = EXPECTED[row['profile_id']]
        assert {
            'op': 'socket_jewel_matches',
            'count': 1,
            'stats': {f'{stat}:0': value, **{f'{sid}:0': 11 for sid in (39, 41, 43, 45)}},
        } in row['required_predicates']
        assert {'op': 'fact_eq', 'field': 'sockets', 'value': 1} in row['required_predicates']
        assert {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'} in row['required_predicates']
        if stat == 22:
            assert any('supplies no IAS' in text for text in row['required_conditions'])
        assert any('lower native' in text for text in row['required_conditions'])
