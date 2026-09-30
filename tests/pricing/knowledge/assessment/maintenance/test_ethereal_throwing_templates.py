"""Exact ethereal alternatives preserve unknown status and upgraded-base requirements."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.maintenance.throwing_templates import expand_named_throwing
from pricing.knowledge.assessment.profiles import assess_role_results
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base'),
    [
        ('Gimmershred', 'Flying Axe'),
        ('Warshrike', 'Winged Knife'),
        ('Lacerator', 'Winged Axe'),
        ("Demon's Arch", 'Balrog Spear'),
        ("Gargoyle's Bite", 'Winged Harpoon'),
        ('Deathbit', 'Flying Knife'),
        ('The Scalper', 'Flying Axe'),
    ],
)
def test_exact_ethereal_throwing_variant_requires_known_ethereal_item(name, base):
    row = {
        'id': 'exact-ethereal',
        'item': name,
        'class': 'Barbarian',
        'build': 'double-throw-barbarian-guide',
        'side': 'player',
        'slot': 'Weapon',
        'variant': 'Main alternatives',
        'source': {'path': 'fixture', 'locator': '/0'},
        'ethereal_only': True,
    }
    role = expand_named_throwing(row)
    item = replace(
        facts(base, 'unique', name),
        ethereal=True,
        stats={'253:0': {'status': 'decoded', 'value': 30, 'unit': 'replenishment_rate'}},
    )

    def outcome(candidate, profile=role):
        return assess_role_results(candidate, [profile], {'player_class': 'Barbarian'})[0]

    assert outcome(item).rule_trace['truth'] == 'true'
    assert outcome(replace(item, ethereal=False)).status == 'failed'
    unknown = outcome(replace(item, ethereal=None))
    assert unknown.rule_trace['truth'] == 'unknown'
    assert unknown.status == 'partial'
    # A new exact variant must not narrow the existing broad alternative.
    broad = expand_named_throwing({k: v for k, v in row.items() if k != 'ethereal_only'})
    assert outcome(replace(item, ethereal=False), broad).rule_trace['truth'] == 'true'
    if name in ('Deathbit', 'The Scalper'):
        native = replace(item, base_code=facts('Battle Dart' if name == 'Deathbit' else 'Francisca').base_code)
        assert outcome(native).status == 'failed'


@pytest.mark.parametrize('value', ['yes', 1, None])
def test_ethereal_selector_rejects_non_boolean_configuration(value):
    row = {
        'item': 'Lacerator',
        'class': 'Barbarian',
        'build': 'double-throw-barbarian-guide',
        'side': 'player',
        'slot': 'Weapon',
        'ethereal_only': value,
    }
    with pytest.raises(ValueError, match='ethereal'):
        expand_named_throwing(row)


def test_ethereal_configuration_cannot_override_nonrepairable_amazon_policy():
    row = {
        'item': 'Thunderstroke',
        'class': 'Amazon',
        'build': 'lightning-fury-amazon-guide',
        'side': 'player',
        'slot': 'Weapon',
        'ethereal_only': True,
    }
    with pytest.raises(ValueError, match='ethereal'):
        expand_named_throwing(row)


def test_registered_ethereal_variants_have_exact_source_and_stat_endorsements():
    from pricing.knowledge.assessment.build_profiles import build
    from pricing.knowledge.assessment.maintenance.qualified_table_context import require_qualification

    bundle = build()
    roles = [p for p in bundle['profiles'] if p['id'].endswith('-ethereal-throwing-alternative')]
    assert len(roles) == 14
    expected = {'Gimmershred', 'Warshrike', 'Lacerator', "Demon's Arch", "Gargoyle's Bite", 'Deathbit', 'The Scalper'}
    assert {(p['names'][0], p['slot']) for p in roles} == {
        (name, slot) for name in expected for slot in ('Weapon', 'Off-Hand')
    }
    for role in roles:
        label = (
            'Ethereal ' + role['names'][0] + (' (Upgraded)' if role['names'][0] in ('Deathbit', 'The Scalper') else '')
        )
        assert role['source']['quotes'] == [label]
        require_qualification(role, label)
        uses = [u for u in bundle['guide_demand']['uses'] if u['profile_id'] == role['id']]
        assert len(uses) == 1
        assert uses[0]['review_state'] == 'reviewed'
        configs = [c for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']]
        assert len(configs) == 1
