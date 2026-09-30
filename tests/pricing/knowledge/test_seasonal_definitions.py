"""Non-Ladder defaults retain archived versions without pricing Ladder-only captures."""

from dataclasses import replace
from pathlib import Path

import pytest

from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.definition_store import DefinitionStore, definition_snapshot
from pricing.knowledge.definitions import build_definitions
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.fixture(scope='module')
def compiled():
    return build_definitions(Path(__file__).resolve().parents[3])


def test_compiler_preserves_ordinary_manald_with_its_own_ranges_and_source(compiled):
    row = next(r for r in compiled['rows'] if r['name'] == 'Manald Heal')
    old = row
    ladder = row['ladder_definition']
    assert old['table_id'] == row['table_id'] == 121
    assert '105' not in old['roll_ranges']
    assert ladder['roll_ranges']['105']['min'] == 10
    assert old['source']['path'] == 'third-parties/d2data/json/base/uniqueitems.json'
    assert old['source']['path'] in compiled['inputs']


def test_store_and_resolver_distinguish_complete_manald_captures(compiled, tmp_path):
    import json

    path = tmp_path / 'definitions.json'
    path.write_text(json.dumps(compiled))
    current = DefinitionStore(path).load()
    with definition_snapshot(current):
        assert len(current.named_variants['unique', 'Manald Heal']) == 1
        ordinary = replace(facts('Ring', 'unique', 'Manald Heal'), stats={})
        seasonal = replace(ordinary, stats={'105:0': {'value': 10, 'status': 'decoded'}})
        old, gaps = resolve_named_definition(ordinary)
        assert not gaps
        assert '105' not in old['roll_ranges']
        new, gaps = resolve_named_definition(seasonal)
        assert new is None
        assert any('Ladder-only' in gap for gap in gaps)
        partial = replace(ordinary, capture_complete=False)
        assert resolve_named_definition(partial)[0]['table_id'] == 121
        conflict = replace(seasonal, stats={'105:0': {'value': 7, 'status': 'decoded'}})
        assert resolve_named_definition(conflict)[0] is None


def test_all_nine_overrides_are_preserved_without_sunder_stat_duplicates(compiled):
    rows = [r for r in compiled['rows'] if r['rarity'] == 'unique' and r.get('ladder_definition')]
    assert {r['table_id'] for r in rows} == {12, 51, 54, 59, 62, 80, 101, 121, 154}
    assert all(r['ladder_definition']['table_id'] == r['table_id'] for r in rows)


def test_discriminators_do_not_guess_socketed_or_non_scalar_variants(compiled, tmp_path):
    import json

    path = tmp_path / 'definitions.json'
    path.write_text(json.dumps(compiled))
    with definition_snapshot(DefinitionStore(path).load()):
        for name in ('Manald Heal', 'The Ward', 'The Battlebranch'):
            row = next(r for r in compiled['rows'] if r['name'] == name)
            item = facts(row['base_name'], 'unique', name)
            item = replace(
                item, provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': row['table_id']}}}
            )
            if name == 'Manald Heal':
                item = replace(
                    item, sockets=1, socket_contents='filled', stats={'105:0': {'status': 'decoded', 'value': 10}}
                )
            selected, gaps = resolve_named_definition(item)
            assert not gaps
            assert selected['source']['path'].endswith('base/uniqueitems.json')
            if name == 'Manald Heal':
                from pricing.knowledge.assessment.handlers.seasonal import select_seasonal

                candidates = [row, row['ladder_definition']]
                assert select_seasonal(candidates, item) == candidates
            if name == 'The Battlebranch':
                assert selected['game_definition']['lvl req'] == 25


def test_capture_gaps_still_block_pricing_with_a_non_ladder_default(compiled, tmp_path):
    import json

    path = tmp_path / 'definitions.json'
    path.write_text(json.dumps(compiled))
    with definition_snapshot(DefinitionStore(path).load()):
        item = replace(facts('Ring', 'unique', 'Manald Heal'), gaps=['Unreadable native modifier'])
        assert resolve_named_definition(item)[0]['table_id'] == 121
        from pricing.knowledge.assessment.handlers.named import NamedHandler

        _, gaps = NamedHandler().contract(item, 'jewelry')
        assert 'Unreadable native modifier' in gaps


def test_native_manald_contracts_do_not_mix_seasonal_listings(compiled, tmp_path):
    import json

    from pricing.knowledge.assessment.comparables import evaluate
    from pricing.knowledge.assessment.maintenance.fixed_jewelry_market_review import native_jewelry_contract

    path = tmp_path / 'definitions.json'
    path.write_text(json.dumps(compiled))
    with definition_snapshot(DefinitionStore(path).load()):
        old = native_jewelry_contract('Manald Heal', {62: 7, 74: 8, 7: 20, 27: 20})
        with pytest.raises(ValueError, match='Ladder-only'):
            native_jewelry_contract('Manald Heal', {62: 7, 74: 8, 7: 20, 27: 20, 105: 10})
        listing = {
            'name': 'Manald Heal',
            'rarity': 'unique',
            'base_code': old['base_code'],
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'evidence_kind': 'ask',
            'scope_status': 'verified',
            'unit_policy': 'single_item',
            'seller_id': 'one',
            'listing_id': 'one',
            'ask_ist': 1,
            'observed_at': '2026-09-29',
        }
        from inventory_tracking.items.metadata import metadata

        fcr = metadata()['stats']['105']['property_id']
        assert evaluate(old, [{**listing, 'properties': {**old['properties'], fcr: 10}}])['accepted'] == []
        assert len(evaluate(old, [{**listing, 'properties': old['properties']}])['accepted']) == 1
        from inventory_tracking.items.metadata import metadata

        fcr_property = metadata()['stats']['105']['property_id']
        assert old['properties'].get(fcr_property) == 0
        unknown = {k: v for k, v in old['properties'].items() if k != fcr_property}
        assert evaluate(old, [{**listing, 'properties': unknown}])['accepted'] == []


@pytest.mark.parametrize(
    ('table_id', 'ordinary_stats', 'seasonal_stats'),
    [
        (12, {}, {105: 10}),
        (54, {93: 20}, {105: 20}),
        (59, {}, {93: 25}),
        (154, {93: 20}, {93: 20, 96: 20}),
    ],
)
def test_weapon_speed_discriminators_preserve_both_versions(compiled, table_id, ordinary_stats, seasonal_stats):
    from pricing.knowledge.assessment.handlers.seasonal import select_seasonal

    row = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == table_id)
    variants = [row, row['ladder_definition']]
    for expected, values in zip(variants, (ordinary_stats, seasonal_stats), strict=True):
        item = replace(
            facts(row['base_name'], 'unique', row['name']),
            stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in values.items()},
        )
        assert select_seasonal(variants, item) == [expected]


def test_non_ladder_identity_survives_partial_stats_but_rejects_table_conflict(compiled, tmp_path):
    import json

    path = tmp_path / 'definitions.json'
    path.write_text(json.dumps(compiled))
    with definition_snapshot(DefinitionStore(path).load()):
        item = replace(facts('Bone Wand', 'unique', 'Gravenspine'), capture_complete=False)
        assert resolve_named_definition(item)[0]['table_id'] == 12
        identity, gaps = resolve_named_definition(item, identity_only=True)
        assert not gaps
        assert identity['name'] == 'Gravenspine'
        assert identity['table_id'] == 12
        assert '105' not in identity['roll_ranges']
        assert identity['game_definition']['lvl req'] == 20
        conflict = replace(item, provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': 54}}})
        assert resolve_named_definition(conflict, identity_only=True)[0] is None
