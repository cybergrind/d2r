from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.role_rows import role_rows
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'name', 'base', 'slot'),
    [
        ('kira', "Kira's Guardian", 'Tiara', 'Helmet'),
        ('duriel', "Duriel's Shell", 'Cuirass', 'Body Armor'),
    ],
)
def test_budget_kicker_cannot_be_frozen_alternatives(slug, name, base, slot):
    profile = next((p for p in build()['profiles'] if p['id'] == f'dragon-talon-budget-cbf-{slug}'), None)
    assert profile is not None
    assert profile['slot'] == slot
    item = replace(
        facts(base, 'unique', name),
        stats={
            key: {'status': 'decoded', 'value': value}
            for key, value in [
                ('153:0', 1),
                ('39:0', 50 if slug == 'kira' else 20),
                ('41:0', 50 if slug == 'kira' else 20),
                ('43:0', 50),
                ('45:0', 50 if slug == 'kira' else 20),
            ]
        },
    )
    context = {'player_class': 'Assassin'}
    result = role_rows(item, [profile], context)[0]
    assert result['rule_trace']['truth'] == 'true'
    assert result['status'] == 'partial'
    assert any('Attack Rating' in c for c in result['missing'])
    for changed in (replace(item, ethereal=True), replace(item, stats={})):
        assert role_rows(changed, [profile], context)[0]['status'] == 'failed'
    unknown = replace(item, stats={}, capture_complete=False)
    assert role_rows(unknown, [profile], context)[0]['rule_trace']['truth'] == 'unknown'
    assert role_rows(item, [profile], {'player_class': 'Sorceress'})[0]['status'] == 'failed'
    assert not role_rows(replace(item, name='Unrelated unique'), [profile], context)
    assert 'price' not in result
