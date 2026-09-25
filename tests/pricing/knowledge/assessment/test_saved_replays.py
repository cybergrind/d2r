import pytest

from pricing.knowledge.assessment.maintenance.replay import replay


@pytest.mark.parametrize(
    ('stem', 'name'),
    [
        ('authority_mage_plate', 'Authority'),
        ('tancred_crowbill', "Tancred's Crowbill"),
        ('harlequin_crest', 'Harlequin Crest'),
        ('atma_scarab', "Atma's Scarab"),
        ('large_charm_life20', None),
        ('large_charm_life35', None),
    ],
)
def test_saved_items_reach_offline_assessment_and_report(stem, name):
    result = replay(stem)
    if name:
        assert result['extraction']['item']['name'] == name
    assert result['assessment']['quality_policy'] in ('named', 'runeword', 'affixed')
    assert result['text']
    assert result['source']
    if stem == 'harlequin_crest':
        assert not result['assessment']['price_gaps']
        contract = result['assessment']['contract']
        assert contract['socket_payload'] == ['Um Rune']
        assert all(contract['properties'][key] == 15 for key in ('427', '428', '426', '401'))
    if result['assessment']['price_gaps']:
        assert result['price_estimate']['estimate_ist'] is None


@pytest.mark.parametrize(
    ('stem', 'text', 'quality'),
    [
        ('harlequin_crest', 'Defense: 99 (98-141)', 'low'),
        ('large_charm_life20', '+20 (6-35) to Life [T4; T1: 31-35]', 'normal'),
        ('large_charm_life35', '+35 (6-35) to Life [T1; T1: 31-35]', 'perfect'),
    ],
)
def test_expanded_replays_preserve_reported_roll_ranges(stem, text, quality):
    result = replay(stem)
    stat = next(row for row in result['extraction']['decoded_stats'] if row.get('text') == text)
    assert stat['roll_quality'] == quality
    assert text in result['text']


def test_atma_replay_preserves_poison_components_through_report():
    result = replay('atma_scarab')
    assert '+40 Poison Damage over 4 Seconds' in result['text']


def test_hellplague_replay_keeps_fire_skills_and_combined_damage():
    result = replay('hellplague')
    assert result['extraction']['item']['name'] == 'Hellplague'
    assert '+2 to Fire Skills' in result['text']
    assert '25-75 Fire Damage' in result['text']


def test_old_runic_capture_preserves_unknown_socket_contents():
    result = replay('runic_talons')
    item = result['extraction']['item']
    assert item['sockets'] == 3
    assert item['socket_contents'] is None
    assert result['price_estimate']['estimate_ist'] is None
    assert result['assessment']['price_gaps']


def test_hellplague_fire_skill_projects_distinct_from_sorceress_fire_tab():
    result = replay('hellplague')
    assert 'No verified market mapping for native stat 126:1.' not in result['assessment']['price_gaps']


def test_hellplague_rejects_changed_fixed_fire_skill_bonus():
    from dataclasses import replace

    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.handlers.named import NamedHandler

    result = replay('hellplague')
    facts = normalize(result['extraction'])
    assert facts.properties['586'] == 2
    assert NamedHandler().contract(facts, 'weapon')[0] is not None
    changed = replace(
        facts,
        stats={**facts.stats, '126:1': {**facts.stats['126:1'], 'value': 3}},
        properties={**facts.properties, '586': 3},
    )
    contract, gaps = NamedHandler().contract(changed, 'weapon')
    assert contract is None
    assert any('126:1' in gap for gap in gaps)
