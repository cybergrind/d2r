import json
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import decode_stats, item_base, metadata


def test_screenshot_energy_and_scaled_life_are_separate_market_facets():
    decoded, affixes, unresolved = decode_stats(
        [
            {'id': 1, 'layer': 0, 'raw': 16},
            {'id': 7, 'layer': 0, 'raw': 20 * 256},
        ]
    )
    assert [s['text'] for s in decoded] == ['+16 to Energy', '+20 to Life']
    assert {a['property_id']: a['value'] for a in affixes} == {'421': 16, '418': 20}
    assert not unresolved


def test_every_stat_entry_survives_unknown_parameters_duplicates_and_negative_values():
    stats = [
        {'id': 39, 'layer': 0, 'raw': -30},
        {'id': 204, 'layer': 123, 'raw': 456},
        {'id': 999, 'layer': 1, 'raw': 2},
        {'id': 1, 'layer': 0, 'raw': 16},
        {'id': 1, 'layer': 0, 'raw': 16},
    ]
    decoded, affixes, unresolved = decode_stats(stats)
    assert [r['memory_stat'] for r in decoded] == stats
    assert decoded[0]['text'] == 'Fire Resist -30%'
    assert len(unresolved) == 4
    assert len(affixes) == 1


def test_base_catalog_spans_weapons_armor_misc_and_does_not_infer_unique_names():
    assert {r['category'] for r in metadata()['bases'].values()} == {'weapons', 'armor', 'misc'}
    assert item_base(537)['name'] == 'Ring'
    assert item_base(-1) is None


def test_host_verified_teleport_charge_encoding_and_multiple_skill_layers():
    decoded, affixes, unresolved = decode_stats(
        [
            {'id': 204, 'layer': 3457, 'raw': 8480},
            {'id': 204, 'layer': 3457 + 1, 'raw': 8479},
        ]
    )
    assert [r['text'] for r in decoded] == ['Level 1 Teleport (32/33 Charges)', 'Level 2 Teleport (31/33 Charges)']
    assert not affixes
    assert not unresolved


def test_proc_encoding_is_not_confused_with_charges_or_market_facets():
    decoded, affixes, unresolved = decode_stats([{'id': 198, 'layer': (54 << 6) | 2, 'raw': 5}])
    assert decoded[0]['text'] == '5% Chance to cast level 2 Teleport on striking'
    assert not affixes
    assert not unresolved


def test_total_defense_and_damage_are_not_searched_as_bonus_affixes():
    decoded, affixes, unresolved = decode_stats(
        [
            {'id': 31, 'layer': 0, 'raw': 500},
            {'id': 22, 'layer': 0, 'raw': 50},
            {'id': 194, 'layer': 0, 'raw': 4},
        ]
    )
    assert [r['text'] for r in decoded] == [
        'Defense: 500',
        'Maximum damage: 50',
        'Sockets: 4',
    ]
    assert not affixes
    assert not unresolved


def test_captured_self_repair_wand_matches_tooltip_modifiers():
    capture = json.loads((Path(__file__).parents[1] / 'fixtures/wand_self_repair.json').read_text())
    decoded, affixes, unresolved = decode_stats(capture['stats'], base=item_base(capture['class_id']))
    texts = [r['text'] for r in decoded]
    assert 'Repairs 1 durability in 33 seconds' in texts
    assert '+2 to Summon Resist (Necromancer Only)' in texts
    assert 'Poison Resist +39%' in texts
    assert '+50% Damage to Undead (inherent base-type bonus)' in texts
    assert 'Base weapon speed: -20 (lower is faster; not increased attack speed)' in texts
    assert not unresolved
    # The inherent modifier is not a rolled affix or a raw memory stat.
    assert decoded[-1]['origin'] == 'base_type'
    assert 'memory_stat' not in decoded[-1]
    assert {a['memory_stat']['id'] for a in affixes} == {45}


@pytest.mark.parametrize(('raw', 'layer'), [(0, 0), (-3, 0), (101, 0), (3, 1)])
def test_invalid_or_parameterized_repair_remains_unresolved(raw, layer):
    stat = {'id': 252, 'layer': layer, 'raw': raw}
    _, _, unresolved = decode_stats([stat])
    assert unresolved == [stat]


def test_blunt_base_bonus_does_not_replace_rolled_undead_bonus_or_leak_to_swords():
    wand = next(b for b in metadata()['bases'].values() if b['name'] == 'Bone Wand')
    sword = next(b for b in metadata()['bases'].values() if b['type'] == 'swor')
    stats = [{'id': 122, 'layer': 0, 'raw': 100}]
    decoded, _, _ = decode_stats(stats, base=wand)
    assert [r['value'] for r in decoded] == [100, 50]
    assert len(decode_stats(stats, base=sword)[0]) == 1


@pytest.mark.parametrize(
    'stat',
    [
        {'id': 252, 'layer': 0, 'raw': 101},
        {'id': 204, 'layer': 0, 'raw': 1},
        {'id': 198, 'layer': 0, 'raw': 101},
        {'id': 68, 'layer': 0, 'raw': 20},
        {'id': 21, 'layer': 0, 'raw': -1},
    ],
)
def test_invalid_specialized_stats_cannot_fall_back_to_generic_labels(monkeypatch, stat):
    # Future metadata updates must not turn invalid encodings into market facts.
    spec = dict(metadata()['stats'][str(stat['id'])], label='+{{value}} test', property_id='test')
    monkeypatch.setitem(metadata()['stats'], str(stat['id']), spec)
    decoded, affixes, unresolved = decode_stats([stat])
    assert unresolved == [stat]
    assert decoded[0]['status'] == 'unresolved'
    assert not affixes


_CAPTURED_ITEMS = json.loads((Path(__file__).parents[1] / 'fixtures/decoded_items.json').read_text())


@pytest.mark.parametrize('capture', _CAPTURED_ITEMS, ids=lambda c: f'{c["base"]["name"]}-{c["source"].split("/")[-3]}')
def test_captured_items_preserve_complete_decoder_output(capture):
    # Saved from the pre-refactor decoder, including unknowns and provenance.
    before = json.dumps(capture, sort_keys=True)
    result = decode_stats(capture['stats'], base=capture['base'])
    assert list(result) == capture['expected']
    assert json.dumps(capture, sort_keys=True) == before


@pytest.mark.parametrize(
    'stat',
    [
        {'id': 1, 'layer': 0, 'raw': True},
        {'id': 1, 'layer': 0, 'raw': 1.0},
        {'id': 7, 'layer': 0, 'raw': 257},
        {'id': 204, 'layer': 3457, 'raw': (32 << 8) | 33},
        {'id': 204, 'layer': 3457, 'raw': 65536},
        {'id': 204, 'layer': 3456, 'raw': 8480},
        {'id': 198, 'layer': 3457, 'raw': 101},
        {'id': 198, 'layer': 3457, 'raw': -1},
        {'id': 107, 'layer': 89, 'raw': 0},
        {'id': 83, 'layer': 8, 'raw': 1},
    ],
)
def test_invalid_payloads_preserve_raw_evidence_without_facets(stat):
    decoded, affixes, unresolved = decode_stats([stat])
    assert decoded[0]['memory_stat'] == stat
    assert decoded[0]['status'] == 'unresolved'
    assert unresolved == [stat]
    assert not affixes


def test_colliding_market_properties_suppress_both_facets_but_keep_readable_stats(monkeypatch):
    spec = dict(metadata()['stats']['9'], property_id=metadata()['stats']['7']['property_id'])
    monkeypatch.setitem(metadata()['stats'], '9', spec)
    decoded, affixes, unresolved = decode_stats(
        [{'id': 7, 'layer': 0, 'raw': 8960}, {'id': 9, 'layer': 0, 'raw': 1024}]
    )
    assert [row['text'] for row in decoded] == ['+35 to Life', '+4 to Mana']
    assert not affixes
    assert not unresolved


@pytest.mark.parametrize('stat_id', [21, 22, 23, 24])
def test_negative_captured_totals_are_not_reinterpreted_as_market_bonuses(stat_id):
    stat = {'id': stat_id, 'layer': 0, 'raw': -1}
    decoded, affixes, unresolved = decode_stats([stat])
    assert unresolved == [stat]
    assert decoded[0]['status'] == 'unresolved'
    assert not affixes


@pytest.mark.parametrize(
    'stats',
    [
        [{'id': 17, 'layer': 0, 'raw': 40}],
        [{'id': 17, 'layer': 0, 'raw': 40}, {'id': 18, 'layer': 0, 'raw': 41}],
        [{'id': 17, 'layer': 0, 'raw': 40}, {'id': 18, 'layer': 0, 'raw': 40}, {'id': 18, 'layer': 0, 'raw': 40}],
    ],
)
def test_partial_unequal_or_duplicate_damage_never_becomes_combined_bonus(stats):
    decoded, affixes, _ = decode_stats(stats)
    assert len(decoded) == len(stats)
    assert not any(a['property_id'] == '510' for a in affixes)
