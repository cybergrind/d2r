"""The demand rows (inventory_tracking/loot/data/wants.json, built by loot/build_wants.py)."""

import json

from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import build_wants, keep
from inventory_tracking.loot.wants import WANTS_FILE, load
from inventory_tracking.macros import pickmode


def test_the_committed_rows_are_what_the_builder_makes_from_the_sources():
    assert json.loads(WANTS_FILE.read_text()) == json.loads(json.dumps(build_wants.build()))


def test_every_row_says_its_source_and_names_codes_the_game_data_has():
    codes = {row['code'] for row in metadata()['bases'].values()}
    rows = load()
    assert rows
    for row in rows:
        assert row.source, row.id
        assert row.codes <= codes, row.id
        assert row.must is not None or row.then == 'identify', row.id  # a keeper row, or an identify class


def test_a_row_without_a_source_or_a_base_the_data_lacks_fails_the_build():
    for broken in ({'source': ''}, {'bases': ['Monarch of Deflecting']}):
        row = {**build_wants.ROWS[0], **broken}
        try:
            build_wants.built_row(row, json.loads((build_wants.ROOT / build_wants.PRICES).read_text()))
        except ValueError:
            continue
        raise AssertionError(f'built: {broken}')


def test_the_keep_layers_item_types_are_the_pickups():
    assert keep.RUNES == pickmode.RUNES
    assert keep.GEMS == pickmode.GEMS
    assert pickmode.CHARMS | {'csch'} == keep.CHARMS | keep.SUNDER
    assert keep.JEWELS == pickmode.JEWELS
    types = {row['type'] for row in metadata()['bases'].values()}
    assert keep.POTIONS - {'elix'} <= types
    assert types >= keep.LOOP_GEAR


def test_the_void_staff_mods_are_the_pickups():
    # The player, 2026-10-20 08:42: "+3os daggers with +3 apocalypse": today's pickup and the wants take the same three
    assert {f'107:{skill}' for skill in pickmode.VOID_STAFFMODS} == set(build_wants.VOID_STAFFMODS)
