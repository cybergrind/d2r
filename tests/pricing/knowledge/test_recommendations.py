import pytest

from pricing.knowledge.recommendations import build_recommendations


def candidate(name, context='leveling utility', kind='unique'):
    return {'name': name, 'item_kind': kind, 'context': context, 'utility_tags': ['life'], 'source_timestamp': '01:00'}


def build(items, facts=None, utility=None):
    facts = (
        facts
        if facts is not None
        else [{'name': item['name'], 'item_id': 'test:' + item['name'], 'aliases': []} for item in items]
    )
    return build_recommendations(
        {'items': items, 'generic_patterns': [], 'negative_or_scope_mentions': []},
        {'rows': facts},
        utility or {'rows': [], 'sources': []},
    )


def test_cross_class_defense_and_caster_weapon_are_reviewed_without_attack_claims():
    payload = build([candidate('Bloodfist'), candidate('Maelstrom')])
    blood = next(r for r in payload['rows'] if r['name'] == 'Bloodfist')
    assert {'sorceress', 'necromancer', 'warlock'} <= set(blood['classes'])
    assert blood['archetypes'] == ['general']
    assert 'attack speed' not in blood['reason'].lower()
    wand = next(r for r in payload['rows'] if r['name'] == 'Maelstrom')
    assert wand['archetypes'] == ['caster']
    assert 'sorceress' in wand['classes']


def test_conditional_set_requires_companion_and_incidental_is_not_recommendation():
    payload = build([candidate("Death's Hand", kind='set'), candidate("Sander's Superstition")])
    hand = payload['rows'][0]
    assert any("Death's Guard" in c for c in hand['conditions'])
    assert not any(r['name'] == "Sander's Superstition" for r in payload['rows'])
    assert payload['coverage']['named'][1]['status'] == 'gap'


def test_missing_identity_and_ambiguous_alias_are_explicit_gaps():
    items = [candidate('Bloodfist'), candidate('Maelstrom')]
    payload = build(
        items,
        facts=[
            {'name': 'x', 'aliases': ['Bloodfist'], 'item_id': '1'},
            {'name': 'y', 'aliases': ['Bloodfist'], 'item_id': '2'},
        ],
    )
    assert payload['rows'] == []
    assert {x['status'] for x in payload['coverage']['named']} == {'gap'}


def test_vendor_and_shared_planner_mentions_never_promoted():
    utility = {
        'sources': [],
        'rows': [
            {
                'name': 'Ring',
                'class': 'sorceress',
                'kind': 'leveling',
                'details': {'context_excerpt': 'pick up items to sell, like Rings'},
            },
            {
                'name': 'Bloodfist',
                'class': 'sorceress',
                'kind': 'leveling',
                'source_id': 'shared-planner',
                'details': {'recommended': True},
            },
        ],
    }
    assert build([], utility=utility)['rows'] == []


def test_class_items_and_patterns_cannot_become_universal_named_items():
    payload = build([candidate('The Oculus')])
    assert payload['rows'][0]['classes'] == ['sorceress']
    candidates = {
        'items': [],
        'generic_patterns': [
            {'name': 'leveling rings', 'context': 'Cast rate when needed', 'source_timestamp': '24:19'}
        ],
        'negative_or_scope_mentions': [{'name': 'Death Cleaver', 'context': 'endgame scope', 'timestamp': '46:28'}],
    }
    payload = build_recommendations(candidates, {'rows': []}, {'rows': [], 'sources': []})
    assert payload['rows'] == []
    assert payload['patterns'][0]['item_id'] is None
    assert payload['coverage']['exclusions'][0]['status'] == 'excluded'


def test_mercenary_survival_advice_preserves_equipment_prerequisites():
    payload = build([candidate('Rockstopper')])
    merc = next(r for r in payload['rows'] if r['side'] == 'merc')
    assert 'mercenary' in ' '.join(merc['conditions']).lower()
    assert merc['evidence_strength'] == 'explicit'


def test_reviewed_guide_advice_is_class_specific_and_priority_is_not_frequency():
    reviewed = {
        'name': 'Magefist',
        'class': 'sorceress',
        'kind': 'leveling',
        'source_id': 'leveling-sorceress',
        'source_locator': 'essentials-header/item/80@(77, 233)',
    }
    utility = {'sources': [], 'rows': [reviewed] * 8}
    payload = build([candidate('Magefist'), candidate('Nagelring')], utility=utility)
    explicit = [r for r in payload['rows'] if r['source_id'] == 'leveling-sorceress']
    assert len(explicit) == 1
    assert explicit[0]['classes'] == ['sorceress']
    assert explicit[0]['evidence_strength'] == 'explicit'
    assert explicit[0]['priority'] < next(r for r in payload['rows'] if r['name'] == 'Nagelring')['priority']


def test_portable_review_census_accounts_for_transcript_and_eight_classes():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    path = root / 'pricing/data/appraisal-recommendations.json'
    if not path.exists():
        pytest.skip('Separate local KB snapshot is not installed')
    payload = json.loads(path.read_text())
    assert len(payload['coverage']['named']) == 70
    assert len(payload['patterns']) == 13
    assert len(payload['coverage']['exclusions']) == 4
    assert len(payload['coverage']['classes']) == 8
    assert all(r['source_locator'] and r['reason'] for r in payload['rows'])
    assert all(p['item_id'] is None for p in payload['patterns'])
    assert len({r['id'] for r in payload['rows']}) == len(payload['rows'])
