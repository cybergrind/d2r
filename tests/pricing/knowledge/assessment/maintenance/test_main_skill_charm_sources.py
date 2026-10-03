"""Each reviewed main skill-charm table must retain its native planner witness."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]


def test_four_builds_have_exact_main_skill_charm_table_links():
    def read(path):
        return json.loads((ROOT / path).read_bytes())

    inventory = read('pricing/data/appraisal-guide-inventory.json')
    links = compile_table_equivalence(
        read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json'),
        inventory['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    expected = {
        f'{build}-main-skiller-{suffix}'
        for build, suffixes in (
            ('lightning-sentry-assassin', ('vita',)),
            ('lightning-sorceress', ('vita', 'balance', 'plain')),
            ('lightning-strike-amazon', ('vita', 'balance', 'inertia', 'plain')),
            ('poison-nova-necromancer', ('vita', 'balance', 'plain')),
        )
        for suffix in suffixes
    }
    assert expected <= {row['profile_id'] for row in links if row['state'] == 'reviewed'}
