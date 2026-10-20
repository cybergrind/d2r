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


def test_a_counted_condition_asks_that_many_stats_at_the_floor():
    """Rare boots "two resistances >= 25" (loot/build_wants.py G21, 2026-10-20): the second best of the four; an
    unread one says nothing; the said text names the count."""
    from inventory_tracking.loot.facts import ItemFacts
    from inventory_tracking.loot.wants import Need

    def boots(rolls: dict[str, int] | None) -> ItemFacts:
        return ItemFacts(unit_id=1, code='xhb', base_type='boot', size=(2, 2), quality=6, identified=True,
                         ethereal=False, sockets=0, rolls=rolls)  # fmt: skip

    two = Need(('39:0', '41:0', '43:0', '45:0'), min=25, count=2)
    assert two.holds(boots({'39:0': 40, '43:0': 25})) is True
    assert two.holds(boots({'39:0': 40, '43:0': 24})) is False
    assert two.holds(boots({'39:0': 40})) is False  # the others read as 0
    assert two.holds(boots(None)) is None
    assert two.said() == '2 of 39:0|41:0|43:0|45:0>=25'
    assert Need(('39:0', '41:0'), min=1, count=3).holds(boots({'39:0': 40, '41:0': 40})) is None  # asks more than keys


def test_the_rare_boots_and_belts_rows_keep_only_the_really_good_ones_and_the_priced_belt_gate():
    """G21 / G22 (the player, 2026-10-20 ~19:25: "we can keep really good ones"): the rows by id, each kept only by
    its full combination (loot/keep.py drops the rest: JUNK_UNWANTED)."""
    rows = {row.id: row for row in load() if row.klass in ('G21', 'G22')}
    assert set(rows) == {
        'boots-rare-identify', 'rare-boots-30frw-fhr-2res-extra', 'rare-boots-20frw-fhr-2res30-extra',
        'rare-boots-20frw-fhr-3res', 'belt-rare-identify', 'rare-belt-24fhr-life-res-extra',
        'rare-belt-24fhr-companion',
    }  # fmt: skip
    assert rows['boots-rare-identify'].then == rows['belt-rare-identify'].then == 'identify'
    assert not any(row.always_keep or row.must_have for row in rows.values())  # no price: a want, never a must-have
    assert {'boot', 'belt'} <= keep.JUNK_UNWANTED
