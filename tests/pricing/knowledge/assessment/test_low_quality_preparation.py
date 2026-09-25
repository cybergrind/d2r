from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from tests.pricing.knowledge.assessment.test_base_use import capture, word


def test_low_quality_armor_normalization_then_socketing_uses_level_one_cap():
    facts = normalize(capture('Archon Plate', sockets=0, quality='low_quality', ethereal=False))
    before = facts.to_dict()
    use = word(assess_runeword_base(facts), 'Enigma')
    assert use['status'] == 'needs normalization and sockets'
    routes = {row['steps'][-1]['action']: row for row in use['preparation']}
    quest = routes['larzuk']
    assert quest['feasibility'] == 'possible'
    assert quest['outcomes'] == [{'maximum': 3, 'success_weight': 1, 'denominator': 1}]
    assert quest['steps'][0]['action'] == 'normalize_low_quality'
    assert quest['steps'][0]['outcomes'] == [{'quality': 'normal', 'item_level': 1}]
    assert quest['steps'][0]['resources'] == [
        {'name': 'El Rune', 'quantity': 1},
        {'name': 'Chipped Gem (Any)', 'quantity': 1},
    ]
    assert routes['cube_socket']['outcomes'] == [{'maximum': 3, 'success_weight': 4, 'denominator': 6}]
    assert all('item_level' not in route['preconditions'] for route in routes.values())
    assert 'recheck' in ' '.join(use['missing']).lower()
    assert facts.to_dict() == before


def test_normalizing_monarch_cannot_prepare_four_socket_spirit():
    use = word(assess_runeword_base(normalize(capture('Monarch', sockets=0, quality='low_quality'))), 'Spirit')
    assert use['status'] == 'normalization cannot supply sockets'
    assert use['preparation']
    assert all(option['feasibility'] == 'impossible' for option in use['preparation'])
    assert all(option['outcomes'][0]['maximum'] == 3 for option in use['preparation'])
    assert not use['strengths']


def test_low_quality_weapon_route_has_weapon_normalization_cost_and_no_state_mutation():
    facts = normalize(capture('Phase Blade', sockets=0, quality='low quality', ethereal=False))
    use = word(assess_runeword_base(facts), 'Grief')
    assert all(option['feasibility'] == 'impossible' for option in use['preparation'])
    assert use['preparation'][0]['steps'][0]['resources'][0]['name'] == 'Eld Rune'
    assert facts.rarity == 'low quality'


def test_normalization_does_not_inherit_ethereal_trade_premium_or_comparison_contract():
    from pricing.knowledge.assessment.engine import assess

    result = assess(capture('Giant Thresher', sockets=0, quality='low_quality'), profiles=[])
    assert result['ethereal_preference'] is None
    assert result['contract'] is None
    assert result['comparison_requests'] == []
