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


def test_the_claw_rows_take_a_fast_base_and_one_skill_each():
    """The player, 2026-10-20 ~21:05 ("look up only elite claws with a specific base, not just random +3 skill";
    "yes" to two own-use trap claws): W1-W3 market rows, O1 own use capped at 2 (loot/build_wants.py)."""
    rows = {row.id: row for row in load() if 'claw-white' in row.id}
    assert set(rows) == {
        'claw-white-plus3-phoenix-strike', 'claw-white-plus3-lightning-sentry', 'claw-white-plus3-claws-of-thunder',
        'own-claw-white-plus3-traps',
    }  # fmt: skip
    talons = {code for code, row in metadata()['bases'].items() if row['name'] in ('Greater Talons', 'Runic Talons')}
    codes = {metadata()['bases'][txt]['code'] for txt in talons}
    assert codes == {'9tw', '7tw'}
    for row in rows.values():
        assert row.codes == codes, row.id
        assert row.qualities == {'normal', 'superior'}, row.id
        assert not row.always_keep, row.id
        assert not row.must_have, row.id
    assert [row.id for row in rows.values() if row.keep_up_to is not None] == ['own-claw-white-plus3-traps']
    assert rows['own-claw-white-plus3-traps'].keep_up_to == build_wants.TRAP_CLAW_CAP == 2


def test_a_lightning_sentry_claw_with_a_paid_second_plus3_ranks_higher():
    """W2's `matters` (Weapon Block, Mind Blast, Death Sentry beside Lightning Sentry): the copy compared and kept
    first (loot/value.py score, better_than); its price stays the appraisal's."""
    from inventory_tracking.loot.facts import ItemFacts
    from inventory_tracking.loot.value import better_than, matters_for, score
    from inventory_tracking.loot.wants import matching

    def talons(unit: int, rolls: dict[str, int]) -> ItemFacts:
        return ItemFacts(unit_id=unit, code='9tw', base_type='h2h2', size=(1, 3), quality=2, identified=True,
                         ethereal=False, sockets=0, rolls=rolls)  # fmt: skip

    alone, blocking = talons(1, {'107:271': 3}), talons(2, {'107:271': 3, '107:263': 3})
    wanted = {row.id for row in matching(blocking)}
    assert wanted == {'claw-white-plus3-lightning-sentry', 'own-claw-white-plus3-traps'}
    matters = matters_for(blocking, matching(blocking))
    assert score(blocking, matters) > score(alone, matters)
    assert better_than(blocking, [alone], matters).better
    assert not better_than(alone, [blocking], matters).better
    assert {row.id for row in matching(talons(3, {'107:267': 3}))} == set()  # +3 Fade alone: no row
