import json
from pathlib import Path

import pytest

from pricing.knowledge.recommendations import build_recommendations


MEMBERS = [
    (cls, "Mara's Kaleidoscope", 67) for cls in ['barbarian', 'druid', 'necromancer', 'paladin', 'sorceress']
] + [
    ('necromancer', 'Homunculus', 42),
    ('amazon', 'Raven Frost', 45),
    ('amazon', 'The Stone of Jordan', 29),
    ('amazon', 'The Eye of Etlich', 15),
    ('amazon', "The Cat's Eye", 50),
    ('amazon', "Highlord's Wrath", 65),
]


def load(name):
    return json.loads(Path('pricing/data/' + name).read_text())


@pytest.mark.parametrize(('cls', 'name', 'level'), MEMBERS)
def test_leveling_jewelry_and_necro_shield_preserve_native_requirements_and_source(cls, name, level):
    utility = load('appraisal-utility.json')
    facts = load('appraisal-item-facts.json')
    candidates = {'items': [], 'generic_patterns': [], 'negative_or_scope_mentions': []}
    result = build_recommendations(candidates, facts, utility)
    row = next((r for r in result['rows'] if r['name'] == name and r['source_id'] == 'leveling-' + cls), None)
    assert row is not None
    assert row['classes'] == [cls]
    assert row['review'].startswith('2026-09-26:')
    native = next(f for f in facts['rows'] if f['item_id'] == row['item_id'])
    assert native['requirements']['level'] == level
    advice = ' '.join([row['reason'], *row['conditions']])
    if name == "Mara's Kaleidoscope":
        assert row['source_label'] == 'Maras Kaleidoscope'
        assert row['archetypes'] == ['caster']
        assert '67' in advice
        if cls in ('paladin', 'barbarian'):
            assert 'respec' in advice
    elif name == 'Homunculus':
        assert '+2 to Necromancer Skills' in advice
        assert 'all skills' in advice.lower()  # Explicitly correct the source wording.
    elif name == "Highlord's Wrath":
        assert 'Deadly Strike' in advice
        assert 'lightning damage' in advice
    elif name == 'Raven Frost':
        assert "Ancient's Pledge" in advice
        assert 'Rhyme' in advice
    for source in utility['sources']:
        if source['id'] == 'leveling-' + cls:
            source['sha256'] = 'changed'
    stale = build_recommendations(candidates, facts, utility)
    assert not any(r['name'] == name and r['source_id'] == 'leveling-' + cls for r in stale['rows'])
