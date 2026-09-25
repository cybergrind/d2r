import json

from pricing.knowledge.assessment.base_use import assess_runeword_base, recipe_catalog
from pricing.knowledge.assessment.build_profiles import ROOT
from pricing.knowledge.assessment.maintenance.base_matrix import audit_bases
from pricing.knowledge.assessment.maintenance.coverage_matrix import build_matrix


def test_actual_base_uses_survive_matrix_join_without_claiming_verified_item_fit():
    weapons = json.loads((ROOT / 'third-parties/d2data/json/weapons.json').read_text())
    types = json.loads((ROOT / 'third-parties/d2data/json/itemtypes.json').read_text())
    code, base = next((c, b) for c, b in weapons.items() if b['name'] == 'Giant Thresher')
    matrix = audit_bases({code: base}, types, recipe_catalog(), [], {}, base_use_evaluator=assess_runeword_base)
    row = next(r for r in matrix['rows'] if r['quality'] == 'superior')
    infinity = next(r for r in row['base_uses'] if r['runeword'] == 'Infinity')
    assert infinity['status'] == 'unverified'
    assert infinity['sources']
    assert any('Base rolls need verification' in reason for reason in infinity['missing'])
    assert row['dimensions']['base_use_routing']['state'] == 'reviewed'
    assert row['dimensions']['desirability']['state'] == 'pending'
    assert matrix['counts']['base_use_rows'] == 3
    joined = build_matrix({'identities': [], 'occurrences': []}, matrix, {'rows': []}, {'profiles': []})
    assert next(r for r in joined['rows'] if r['quality'] == 'superior')['base_uses'] == row['base_uses']
    assert all(r['dimensions']['market']['state'] == 'pending' for r in joined['rows'])


def test_omitted_runtime_audit_is_pending_not_an_empty_reviewed_use_list():
    result = audit_bases({'test': {'name': 'Test', 'gemsockets': 0}}, {}, [], [], {})
    assert all(r['dimensions']['base_use_routing']['state'] == 'pending' for r in result['rows'])
