"""Socket configurations, rather than native-only Vipermagi, cover socketed sources."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
IDS = {'enchant-sorceress-2-vipermagi-fire-facet', 'nova-sorceress-guide-2-vipermagi-ist'}


def test_socketed_vipermagi_sources_pin_actual_payload_and_fcr_scope():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in IDS
    ]
    assert len(rows) == 2
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert all(r['state'] == 'reviewed' for r in result)
    for r in rows:
        predicates = r['required_predicates']
        assert {'op': 'fact_eq', 'field': 'sockets', 'value': 1} in predicates
        assert {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'} in predicates
        if r['profile_id'].endswith('ist'):
            assert {'op': 'socket_runes_equal', 'value': ['Ist Rune']} in predicates
            assert {'op': 'context_at_least', 'field': 'player_total_fcr', 'value': 105} in predicates
        else:
            assert {
                'op': 'socket_jewel_matches',
                'count': 1,
                'name': 'Rainbow Facet',
                'stats': {'329:0': 3, '333:0': 3},
            } in predicates
            for key in ('329:0', '333:0'):
                assert {'not': {'op': 'socket_jewel_matches', 'name': 'Rainbow Facet', 'stats': {key: 6}}} in predicates
            assert 'does not increase crossbow attack speed' in ' '.join(r['required_conditions'])
