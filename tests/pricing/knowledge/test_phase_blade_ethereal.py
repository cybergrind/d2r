import pytest

from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.test_named_equipment_facts import normalized


@pytest.mark.parametrize('quality', ['normal', 'superior', 'low quality', 'low_quality'])
def test_phase_blade_runeword_base_quality_cannot_be_ethereal(quality):
    props = [{'property_id': 797, 'type': 'string', 'string': quality}]
    row = normalized('Phase Blade', 'base', props)
    assert row['ethereal'] is False
    assert row.get('sockets') is None
    assert '738' not in row['properties']
    bad = normalized('Phase Blade', 'base', [*props, {'property_id': 738, 'type': 'bool', 'bool': True}])
    assert bad['ethereal'] is True
    assert bad['mechanics_conflicts']


@pytest.mark.parametrize('quality', ['rare', 'unique', 'magic', None])
def test_phase_blade_with_upgrade_history_or_unknown_quality_is_not_defaulted(quality):
    props = [] if quality is None else [{'property_id': 797, 'type': 'string', 'string': quality}]
    assert normalized('Phase Blade', 'base', props).get('ethereal') is None
    assert (
        normalized('Dimensional Blade', 'base', [{'property_id': 797, 'type': 'string', 'string': 'normal'}]).get(
            'ethereal'
        )
        is None
    )


def test_completed_grief_phase_blade_proves_ordinary_base_eligibility():
    raw = {
        'id': 'fixture',
        'amount': 1,
        'properties': [
            {'property_id': 820, 'property': 'Base Item (Axe, Sword) 5', 'type': 'string', 'string': 'Phase Blade'}
        ],
    }
    row = normalize_listing(raw, name='Grief', category='runewords', source='fixture')
    assert row['ethereal'] is False
    assert row['sockets'] == 5
    assert row['socket_contents'] == 'filled'
    raw['properties'][0]['string'] = 'Berserker Axe'
    assert normalize_listing(raw, name='Grief', category='runewords', source='fixture').get('ethereal') is None
