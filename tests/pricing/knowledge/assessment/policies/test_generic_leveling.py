from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.leveling import assess_leveling
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('base', 'stat', 'archetype'), [('Boots', 96, 'all'), ('Ring', 105, 'caster'), ('Small Charm', 41, 'all')]
)
def test_affixed_leveling_uses_positive_native_stat_and_preserves_conditions(base, stat, archetype):
    item = replace(facts(base, 'magic'), stats={f'{stat}:0': {'status': 'decoded', 'value': 10}})
    uses = assess_leveling(item)
    assert len(uses) == 1
    assert uses[0]['status'] == 'conditional'
    assert archetype in uses[0]['archetypes']
    assert uses[0]['conditions']
    assert uses[0]['required_level'] is None
    assert 'price' not in uses[0]
    for value in (0, -1, True, float('nan')):
        assert not assess_leveling(replace(item, stats={f'{stat}:0': {'status': 'decoded', 'value': value}}))
    assert not assess_leveling(replace(item, identified=False))
    assert not assess_leveling(replace(item, stats={f'{stat}:0': {'status': 'unresolved', 'value': 10}}))
    assert not assess_leveling(replace(item, ethereal=True))


def test_generic_leveling_requires_matching_slot_and_excludes_unreviewed_qualities():
    stats = {'105:0': {'status': 'decoded', 'value': 10}}
    assert not assess_leveling(replace(facts('Boots', 'rare'), stats=stats))
    assert not assess_leveling(replace(facts('Ring', 'unique'), stats=stats))
    assert assess_leveling(replace(facts('Ring', 'rare'), stats=stats))


def test_generic_leveling_changed_source_requires_review(tmp_path, monkeypatch):
    from pricing.knowledge.assessment.policies import generic_leveling

    source = tmp_path / 'research.json'
    source.write_bytes(generic_leveling.SOURCE.read_bytes() + b'\n')
    monkeypatch.setattr(generic_leveling, 'SOURCE', source)
    item = replace(facts('Boots', 'magic'), stats={'96:0': {'status': 'decoded', 'value': 20}})
    assert not assess_leveling(item)


def test_generic_leveling_reaches_shared_report_without_trade_tier():
    from inventory_tracking.appraisal.sections import leveling_lines
    from inventory_tracking.items.metadata import decode_stats
    from pricing.knowledge.assessment.engine import assess

    decoded, _, _ = decode_stats([{'id': 96, 'layer': 0, 'raw': 20}])
    result = assess(
        {
            'item': facts('Boots', 'magic').to_dict(),
            'decoded_stats': decoded,
            'source': {'stat_capture_complete': True},
        },
        profiles=[],
    )
    assert result['trade_tier']['tier'] is None
    lines = leveling_lines({'assessment': result})
    assert any('all classes' in line for line in lines)
    assert any('Early leveling' in line for line in lines)


@pytest.mark.parametrize(
    ('base', 'quality', 'stats', 'locator'),
    [
        ('Heavy Gloves', 'magic', {80: 15}, '/generic_patterns/2'),
        ('Heavy Gloves', 'rare', {93: 20, 39: 15}, '/generic_patterns/3'),
        ('Belt', 'crafted', {105: 10}, '/generic_patterns/4'),
        ('Belt', 'rare', {7: 40}, '/generic_patterns/11'),
        ('Ring', 'rare', {41: 20}, '/generic_patterns/8'),
    ],
)
def test_additional_affixed_leveling_patterns(base, quality, stats, locator):
    item = replace(facts(base, quality), stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in stats.items()})
    uses = assess_leveling(item)
    assert len(uses) == 1
    assert uses[0]['source']['locator'] == locator
    assert uses[0]['status'] == 'conditional'


def test_attack_speed_gloves_require_useful_secondary_stats_and_belt_craft_is_specific():
    gloves = replace(facts('Heavy Gloves', 'magic'), stats={'93:0': {'status': 'decoded', 'value': 20}})
    assert not assess_leveling(gloves)
    belt = replace(facts('Belt', 'magic'), stats={'105:0': {'status': 'decoded', 'value': 10}})
    assert not assess_leveling(belt)
    crafted_ring = replace(facts('Ring', 'crafted'), stats={'105:0': {'status': 'decoded', 'value': 10}})
    assert not assess_leveling(crafted_ring)


def test_ring_combination_does_not_repeat_same_source_recommendation():
    item = replace(facts('Ring', 'rare'), stats={f'{k}:0': {'status': 'decoded', 'value': 10} for k in (105, 7, 41)})
    uses = assess_leveling(item)
    assert len(uses) == 1
    assert uses[0]['archetypes'] == ['caster']
    assert 'breakpoint' in uses[0]['conditions'][0]


def test_crushing_blow_weapon_leveling_is_conditional_and_not_a_glove_rule():
    item = replace(facts('Axe', 'crafted'), stats={'136:0': {'status': 'decoded', 'value': 10}})
    uses = assess_leveling(item)
    assert len(uses) == 1
    assert uses[0]['source']['locator'] == '/generic_patterns/6'
    assert uses[0]['archetypes'] == ['attack']
    assert uses[0]['status'] == 'conditional'
    assert 'boss' in uses[0]['conditions'][0]
    assert not assess_leveling(replace(facts('Heavy Gloves', 'crafted'), stats=item.stats))
    assert not assess_leveling(replace(item, stats={'136:0': {'status': 'decoded', 'value': 0}}))
    assert not assess_leveling(replace(item, gaps=['Duplicate native stat 136:0.']))


def test_conflicting_leveling_stat_does_not_erase_independent_valid_utility():
    item = replace(
        facts('Boots', 'rare'),
        stats={f'{k}:0': {'status': 'decoded', 'value': 10} for k in (96, 80)},
        gaps=['Duplicate native stat 96:0.'],
    )
    uses = assess_leveling(item)
    assert [use['source']['locator'] for use in uses] == ['/generic_patterns/2']
