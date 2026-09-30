import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


@pytest.mark.parametrize(
    ('build', 'parent'),
    [
        ('berserk-barbarian', 87),
        ('double-throw-barbarian-guide', 143),
        ('lightning-strike-amazon', 107),
    ],
)
def test_player_topaz_links_preserve_the_armor_and_nested_gem(build, parent):
    def read(path):
        return json.loads(Path(path).read_text())

    doc = read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')
    inventory = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    expected = {
        o['id']
        for o in inventory
        if o['source_id'] == f'pricing/raw/mr/guides__{build}.html'
        and o['source_locator'] in (f'/item-spans/{parent}', f'/item-spans/{parent + 1}')
    }
    assert len(expected) == 2
    rows = compile_table_equivalence(doc, inventory, profiles, uses, Path.cwd())
    actual = {r['occurrence_id'] for r in rows if r['profile_id'] == build + '-perfect-topaz-general-armor'}
    assert actual == expected
