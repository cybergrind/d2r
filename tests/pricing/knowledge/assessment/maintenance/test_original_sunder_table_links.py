"""Original-sunder table links require the native identity witness, not just a name."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.item_bank.cases.original_sunder_tables import SPECS


def test_original_sunder_links_cover_the_nine_verified_build_references():
    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    inventory = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())
    bundle = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    rows = compile_table_equivalence(doc, inventory['occurrences'], bundle['profiles'], uses, Path.cwd())
    occurrences = {o['id']: o for o in inventory['occurrences']}
    reviewed = {r['occurrence_id']: r for r in doc['rows']}
    linked = {
        (o['build'], o['name']): reviewed[r['occurrence_id']]
        for r in rows
        if (o := occurrences[r['occurrence_id']])['slot'] == 'Unique Charms'
    }
    for build, _, name, *_ in SPECS:
        row = linked.get((build, name))
        assert row is not None
        paths = {p['path'] for p in row.get('corroborating', [])}
        assert 'pricing/raw/mr/planners/game-data.json' in paths
        assert len(paths) == 2
