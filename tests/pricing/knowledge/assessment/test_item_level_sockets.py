import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from pricing.knowledge.assessment.engine import assess_result
from tests.pricing.knowledge.assessment.test_base_use import capture, word


def item_at(level, quality='normal'):
    item = capture(sockets=0, quality=quality)
    item['item']['item_level'] = level
    item['decoded_stats'] = []
    return item


@pytest.mark.parametrize(('level', 'cap'), [(1, 3), (25, 3), (26, 4), (40, 4), (41, 6), (99, 6)])
def test_known_item_level_selects_socket_cap_and_quote_eligibility(level, cap):
    item = item_at(level)
    facts = normalize(item)
    use = word(assess_runeword_base(facts), 'Infinity')
    actions = {a['action']: a for a in use['preparation']}
    assert actions['larzuk']['outcomes'] == [{'maximum': cap, 'success_weight': int(cap == 4), 'denominator': 1}]
    assert 'item_level' not in actions['cube_socket']['preconditions']
    assert actions['cube_socket']['outcomes'] == [
        {'maximum': cap, 'success_weight': 0 if cap < 4 else 3 if cap == 4 else 1, 'denominator': 6}
    ]
    requests = assess_result(item, profiles=[]).comparison_requests
    larzuk = [
        r for r in requests if r.preparation and r.preparation['action'] == 'larzuk' and r.contract['sockets'] == 4
    ]
    assert bool(larzuk) is (cap == 4)
    assert facts.item_level == level
    if cap < 4:
        assert use['status'] == 'cannot prepare this base'


@pytest.mark.parametrize('level', [None, True, 0, 100, -1, '40', 40.0])
def test_invalid_or_absent_item_level_remains_unknown(level):
    facts = normalize(item_at(level))
    assert facts.item_level is None
    use = word(assess_runeword_base(facts), 'Infinity')
    assert len(use['preparation'][0]['outcomes']) == 3


def test_normalization_replaces_original_item_level_for_socket_outcomes():
    facts = normalize(item_at(99, 'low_quality'))
    use = word(assess_runeword_base(facts), 'Infinity')
    assert use['status'] == 'normalization cannot supply sockets'
    assert all(option['outcomes'][0]['maximum'] == 3 for option in use['preparation'])
    assert facts.item_level == 99
