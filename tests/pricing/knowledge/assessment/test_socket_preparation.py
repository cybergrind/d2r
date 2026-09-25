from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base
from pricing.knowledge.utility import socket_options
from tests.pricing.knowledge.assessment.test_base_use import capture, word


def test_cube_socket_outcomes_preserve_unknown_level_brackets():
    base = {'gemsockets': 6, 'type': 'test'}
    types = {'test': {'maxsock1': 3, 'maxsock25': 4, 'maxsock40': 6}}
    result = socket_options(base, types, method='cube')
    assert result['cube_outcomes'] == [
        {'maximum': 3, 'denominator': 6, 'weights': {1: 1, 2: 1, 3: 4}},
        {'maximum': 4, 'denominator': 6, 'weights': {1: 1, 2: 1, 3: 1, 4: 3}},
        {'maximum': 6, 'denominator': 6, 'weights': {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}},
    ]
    known = socket_options(base, types, method='cube', ilvl=30)
    assert known['cube_outcomes'] == [result['cube_outcomes'][1]]
    superior = socket_options(base, types, method='cube', quality='superior')
    assert superior['eligible'] is False
    assert not superior.get('cube_outcomes')


def test_base_report_gives_conditional_target_socket_chances():
    result = word(
        assess_runeword_base(normalize(capture('Monarch', sockets=0, quality='normal', ethereal=False))), 'Spirit'
    )
    text = ' '.join(result['missing'])
    assert '50%' in text
    assert '0%' in text
    assert 'item level' in text
    superior = word(assess_runeword_base(normalize(capture('Phase Blade', sockets=0, ethereal=False))), 'Grief')
    assert superior['status'] == 'cannot prepare this base'
    assert not any('Cube chance' in line for line in superior['missing'])
