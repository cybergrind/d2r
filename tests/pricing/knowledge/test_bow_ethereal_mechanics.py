import json

import pytest

from pricing.knowledge.legacy import import_catalog
from tests.pricing.knowledge.test_named_equipment_facts import normalized


def test_catalog_retains_native_no_durability_flag_without_defaulting_missing(tmp_path):
    raw = tmp_path / 'pricing/raw'
    raw.mkdir(parents=True)
    (raw / 'd2data-weapons.json').write_text(
        json.dumps(
            {
                'explicit': {'name': 'Explicit', 'type': 'bow', 'nodurability': 1},
                'missing': {'name': 'Missing', 'type': 'bow'},
            }
        )
    )
    rows = import_catalog(tmp_path)['rows']
    assert rows[0]['details']['no_durability'] == 1
    assert rows[1]['details']['no_durability'] is None


@pytest.mark.parametrize(
    ('name', 'category'),
    [
        ('Windforce', 'uniques'),
        ('Buriza-Do Kyanon', 'uniques'),
        ('Widowmaker', 'uniques'),
        ('Grand Matron Bow', 'base'),
        ('Blade Bow', 'base'),
        ('Demon Crossbow', 'base'),
    ],
)
def test_bow_families_are_nonethereal_without_guessing_socket_state(name, category):
    row = normalized(name, category)
    assert row['ethereal'] is False
    assert row.get('sockets') is None
    assert row['socket_contents'] == 'unknown'
    assert '738' not in row['properties']
    assert row['facet_basis']['ethereal']['kind'] == 'bow_ethereal_mechanics'
    bad = normalized(name, category, [{'property_id': 738, 'type': 'bool', 'bool': True}])
    assert bad['ethereal'] is True
    assert bad['mechanics_conflicts']


def test_no_durability_is_not_a_universal_nonethereal_rule():
    assert normalized('Phase Blade', 'base').get('ethereal') is None
    assert normalized('Matriarchal Javelin', 'base').get('ethereal') is None
