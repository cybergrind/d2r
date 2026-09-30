"""Decorated IAS/fire sources bind socket-aware roles, never native-only helmets."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.item_bank.cases.andariel_fire_variants import VARIANTS


ROOT = Path(__file__).resolve().parents[5]


def test_fire_jewel_sources_require_the_actual_linked_payload():
    def read(path):
        return json.loads((ROOT / path).read_text())

    expected = {f'{build}-{variant}-merc-andariel-ias-fire' for build, variant, _, _ in VARIANTS}
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in expected
    ]
    assert len(rows) == len(expected) == 19
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == expected
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        assert {'op': 'socket_jewel_matches', 'count': 1, 'stats': {'93:0': 15, '39:0': 30}} in row[
            'required_predicates'
        ]
        assert {'op': 'fact_eq', 'field': 'sockets', 'value': 1} in row['required_predicates']
        assert {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'} in row['required_predicates']
