import struct

import pytest

from inventory_tracking.items.identity import resolve_identity
from inventory_tracking.items.metadata import metadata


def resolve(name, base_name, quality):
    table = 'unique' if quality == 7 else 'set'
    table_id, entry = next((k, v) for k, v in metadata()['identities'][table].items() if v['name'] == name)
    base = next(v for v in metadata()['bases'].values() if v['name'] == base_name)
    raw = bytearray(0x60)
    struct.pack_into('<I', raw, 0, quality)
    struct.pack_into('<I', raw, 0x18, 0x10)
    struct.pack_into('<I', raw, 0x34, int(table_id))
    return resolve_identity({'quality': quality}, {'item_data_hex': raw.hex()}, base), entry


@pytest.mark.parametrize(
    ('name', 'base', 'quality'),
    [
        ('Shaftstop', 'Boneweave', 7),
        ("Sazabi's Mental Sheath", 'Giant Conch', 5),
        ("Tancred's Crowbill", 'War Spike', 5),
    ],
)
def test_memory_identity_retains_named_table_id_for_verified_upgrade(name, base, quality):
    identity, original = resolve(name, base, quality)
    assert identity is not None
    assert identity['name'] == name
    assert identity['table_id'] == original['table_id']
    assert identity['roll_ranges'] == original['roll_ranges']


@pytest.mark.parametrize('base', ['Chain Mail', 'Archon Plate'])
def test_memory_identity_rejects_downgrade_or_unrelated_base(base):
    assert resolve('Shaftstop', base, 7)[0] is None


def test_upgraded_plain_defense_uses_new_base_range():
    # Aldur's Advance has no enhanced or flat defense bonus.
    identity, original = resolve("Aldur's Advance", 'Mirrored Boots', 5)
    assert identity is not None
    assert original['base_defense_range']['max'] == 47
    assert identity['base_defense_range']['min'] == 59
    assert identity['base_defense_range']['max'] == 68


def test_saved_crowbill_capture_with_upgraded_base_reaches_assessment_identity():
    import json
    from pathlib import Path

    from inventory_tracking.items.decode import decode_items
    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition

    capture = json.loads((Path(__file__).parents[1] / 'fixtures/tancred_crowbill.json').read_text())
    target_id, target = next((k, v) for k, v in metadata()['bases'].items() if v['name'] == 'War Spike')
    capture['snapshot']['resources']['items'][0]['txt_id'] = int(target_id)
    decoded = decode_items(capture['snapshot'], capture['report'])[0]
    assert decoded['item']['name'] == "Tancred's Crowbill"
    assert decoded['item']['base_code'] == target['code']
    assert decoded['source']['item_identity']['table'] == 'set'
    definition, gaps = resolve_named_definition(normalize(decoded))
    assert not gaps
    assert definition['name'] == "Tancred's Crowbill"
    assert definition['base_name'] == 'Military Pick'


def test_upgrade_compiler_rejects_inconsistent_target_chain():
    from inventory_tracking.items.build_metadata import named_upgrade_variants

    chain = {'normcode': 'normal', 'ubercode': 'exceptional', 'ultracode': 'elite'}
    bases = {code: dict(chain) for code in chain.values()}
    bases['elite']['normcode'] = 'unrelated'
    entry = {'base_code': 'normal', 'base_defense_range': None}
    assert set(named_upgrade_variants(entry, bases)) == {'exceptional'}
    assert named_upgrade_variants({**entry, 'base_code': 'missing'}, bases) == {}
