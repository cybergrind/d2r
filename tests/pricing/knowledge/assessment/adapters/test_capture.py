from dataclasses import FrozenInstanceError

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize


def capture(**item):
    return {'item': item, 'decoded_stats': [], 'source': {'stat_capture_complete': True}}


def test_capture_facts_cannot_be_changed_by_input_or_result_consumers():
    extraction = capture(ethereal=False, sockets=0, socket_contents='empty')
    facts = normalize(extraction)
    extraction['source']['stat_capture_complete'] = False
    assert facts.provenance['capture']['stat_capture_complete'] is True
    with pytest.raises(FrozenInstanceError):
        facts.ethereal = True
    with pytest.raises(TypeError):
        facts.provenance['capture']['stat_capture_complete'] = False
    exported = facts.to_dict()
    exported['provenance']['capture']['stat_capture_complete'] = False
    assert facts.provenance['capture']['stat_capture_complete'] is True


def test_known_false_and_zero_are_distinct_from_unknown_and_conflicting_facts():
    from pricing.knowledge.assessment.domain.facts import FactStatus

    known = normalize(capture(ethereal=False, sockets=0, socket_contents='empty'))
    unknown = normalize(capture())
    conflict = normalize(capture(sockets=0, socket_contents='filled'))
    assert known.fact('ethereal').status == FactStatus.KNOWN
    assert known.fact('ethereal').value is False
    assert known.fact('sockets').value == 0
    assert unknown.fact('ethereal').status == FactStatus.UNKNOWN
    assert conflict.fact('sockets').status == FactStatus.CONFLICTING


def test_native_skill_parameters_remain_distinct_and_missing_stat_is_unknown():
    from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey

    extraction = capture()
    extraction['decoded_stats'] = [
        {'status': 'decoded', 'value': value, 'memory_stat': {'id': 107, 'layer': skill, 'raw': value}}
        for skill, value in [(1, 2), (2, 3)]
    ]
    facts = normalize(extraction)
    assert facts.stat(StatKey(107, 1)).value == 2
    assert facts.stat(StatKey(107, 2)).value == 3
    assert facts.stat(StatKey(107, 3)).status == FactStatus.UNKNOWN


@pytest.mark.parametrize('complete', [False, True])
def test_partial_socket_children_do_not_imply_remaining_sockets_are_empty(complete):
    from pricing.knowledge.assessment.domain.facts import FactStatus

    item = {'sockets': 3, 'socket_contents': 'filled', 'socket_items': [{'name': 'Ral Rune', 'position': 0}]}
    if complete:
        item.update(filled_sockets=1, empty_sockets=2)
    state = normalize(capture(**item)).socket_state
    assert state.total.value == 3
    assert state.occupied.value == (1 if complete else None)
    assert state.empty.value == (2 if complete else None)
    assert state.empty.status == (FactStatus.KNOWN if complete else FactStatus.UNKNOWN)


def test_invalid_socket_counts_block_price_contract_without_erasing_known_stat():
    from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey

    extraction = capture(sockets=3, socket_contents='filled', filled_sockets=2, empty_sockets=2)
    extraction['decoded_stats'] = [
        {'status': 'decoded', 'value': 20, 'memory_stat': {'id': 105, 'layer': 0, 'raw': 20}}
    ]
    facts = normalize(extraction)
    assert facts.socket_state.empty.status == FactStatus.CONFLICTING
    assert any('Socket' in gap for gap in facts.gaps)
    assert facts.stat(StatKey(105)).value == 20
