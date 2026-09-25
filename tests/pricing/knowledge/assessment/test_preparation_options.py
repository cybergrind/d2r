from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from tests.pricing.knowledge.assessment.test_base_use import capture, word


def test_preparation_records_conditional_odds_without_changing_observed_item():
    facts = normalize(capture('Monarch', sockets=0, quality='normal', ethereal=False))
    before = facts.to_dict()
    use = word(assess_runeword_base(facts), 'Spirit')
    options = {o['action']: o for o in use['preparation']}
    cube = options['cube_socket']
    assert cube['destination'] == 'Spirit'
    assert cube['target_sockets'] == 4
    assert cube['feasibility'] == 'conditional'
    assert cube['outcomes'] == [
        {'maximum': 3, 'success_weight': 0, 'denominator': 6},
        {'maximum': 4, 'success_weight': 3, 'denominator': 6},
    ]
    assert 'item_level' in cube['preconditions']
    assert facts.to_dict() == before


def test_superior_cannot_cube_and_removal_declares_destruction():
    use = word(assess_runeword_base(normalize(capture('Phase Blade', sockets=0, ethereal=False))), 'Grief')
    assert {o['action'] for o in use['preparation']} == {'larzuk'}
    assert use['preparation'][0]['feasibility'] == 'impossible'
    filled = normalize(capture(contents='filled'))
    use = word(assess_runeword_base(filled), 'Infinity')
    assert use['preparation'] == [
        {
            'destination': 'Infinity',
            'target_sockets': 4,
            'action': 'clear_sockets',
            'feasibility': 'possible',
            'preconditions': ['horadric_cube', 'ingredients_available'],
            'outcomes': [],
            'destroys_contents': True,
            'resources': [
                {'name': 'Hel Rune', 'quantity': 1},
                {'name': 'Scroll of Town Portal', 'quantity': 1},
            ],
            'source': 'third-parties/d2data/json/cubemain.json#141',
        }
    ]
    assert filled.socket_contents == 'filled'
    assert word(assess_runeword_base(normalize(capture())), 'Infinity')['preparation'] == []


def test_unknown_socket_count_does_not_offer_unverified_actions():
    for changes in ({'sockets': None},):
        use = word(assess_runeword_base(normalize(capture(**changes))), 'Infinity')
        assert use['preparation'] == []


def test_conflicting_socket_capture_cannot_offer_preparation():
    facts = normalize(capture(sockets=0, contents='filled'))
    use = word(assess_runeword_base(facts), 'Infinity')
    assert use['status'] == 'unverified'
    assert use['preparation'] == []


def test_typed_outcomes_are_detached_from_mutable_inputs():
    import pytest

    from pricing.knowledge.assessment.domain.preparation import PreparationOption

    outcomes = [{'maximum': 4, 'success_weight': 3, 'denominator': 6}]
    option = PreparationOption('Spirit', 4, 'cube_socket', 'conditional', outcomes=outcomes)
    outcomes[0]['success_weight'] = 6
    assert option.to_dict()['outcomes'][0]['success_weight'] == 3
    with pytest.raises(TypeError):
        option.outcomes[0]['success_weight'] = 6
