"""The documented Ladder-only changes are not Non-Ladder item defaults."""

from pathlib import Path

import pytest

from pricing.knowledge.definitions import build_definitions


@pytest.fixture(scope='module')
def compiled():
    return build_definitions(Path(__file__).resolve().parents[3])


@pytest.mark.parametrize('table_id', [12, 51, 54, 59, 62, 80, 101, 121, 154])
def test_changed_unique_uses_ordinary_non_ladder_record(compiled, table_id):
    row = next(r for r in compiled['rows'] if r['rarity'] == 'unique' and r['table_id'] == table_id)
    assert row['source']['path'] == 'third-parties/d2data/json/base/uniqueitems.json'
    assert row['game_definition'].get('firstLadderSeason') != 15
    assert row['ladder_definition']['table_id'] == table_id
    assert row['mode_review']['scope'] == 'softcore_non_ladder'


def test_ordinary_bonuses_and_equip_level_are_not_replaced(compiled):
    rows = {r['table_id']: r for r in compiled['rows'] if r['rarity'] == 'unique'}
    assert rows[51]['game_definition']['lvl req'] == 25
    assert rows[54]['roll_ranges']['93']['min'] == 20
    assert rows[54]['roll_ranges']['17']['min'] == 50
    assert rows[80]['roll_ranges']['96']['min'] == 10
    assert '105' not in rows[121]['roll_ranges']
    assert '105' not in rows[12]['roll_ranges']
    assert '93' not in rows[59]['roll_ranges']
    assert '96' not in rows[154]['roll_ranges']


def test_portable_unique_facts_use_non_ladder_requirements_and_modifiers():
    from pricing.knowledge.facts import build_item_facts

    facts = build_item_facts(Path(__file__).resolve().parents[3])
    rows = {r['name']: r for r in facts['rows']}
    assert rows['The Battlebranch']['requirements']['level'] == 25
    for name in ('Manald Heal', 'Gravenspine', 'Bane Ash'):
        assert rows[name]['source'] == 'third-parties/d2data/json/base/uniqueitems.json'
        assert not any(r['property'] == 'cast2' for r in rows[name]['stats'])


def test_recognized_ladder_identity_stays_out_of_pricing_after_partial_projection(compiled, tmp_path):
    import json
    from dataclasses import replace

    from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
    from pricing.knowledge.definition_store import DefinitionStore, definition_snapshot
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    path = tmp_path / 'definitions.json'
    path.write_text(json.dumps(compiled))
    item = replace(
        facts('Ring', 'unique', 'Manald Heal'),
        capture_complete=False,
        provenance={
            'capture': {'item_identity': {'table': 'unique', 'table_id': 121, 'mode_eligibility': 'ladder_only'}}
        },
    )
    with definition_snapshot(DefinitionStore(path).load()):
        definition, gaps = resolve_named_definition(item)
        assert definition is None
        assert any('Ladder-only' in gap for gap in gaps)
        assert resolve_named_definition(item, identity_only=True)[0]['table_id'] == 121
