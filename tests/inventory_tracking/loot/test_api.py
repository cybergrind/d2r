"""The field identify and drop (loot/api.py, M4 of inventory_tracking/loot/design.md). The player, 2026-10-20: "we
don't want to bring all trash monarchs in town. just get it, identify with scroll, and drop if it is bad"; "4os
monarch deflection -- we absolutely want to keep it"; "also start M4 field identify".

The routine runs on fake hands (`Hands`): what it identifies, what it puts down and what it never touches."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest

from inventory_tracking.game.decode import item_size
from inventory_tracking.game.records import VALUABLE, Carried, Drop, Pack
from inventory_tracking.loot import api
from inventory_tracking.loot.api import CLASSES, FIELD_IDENTIFY, MOST_TRIES, Field, droppable, reserve_short
from inventory_tracking.loot.facts import ItemFacts, Owner, Where, from_observation
from inventory_tracking.loot.keep import Action
from inventory_tracking.loot.shadow import Appraised
from inventory_tracking.loot.value import Band, assess
from inventory_tracking.macros.actuator import Hand
from inventory_tracking.macros.pickmode import MONARCH


FIXTURES = Path(__file__).parent / 'fixtures' / 'field'
BLOCKING = json.loads((FIXTURES / 'monarch-of-blocking.json').read_text())
GAME = 'game-1'
KRISS, CIRCLET, RING, SACRED_TARGE, TOME, GHEEDS_BASE = 41, 418, 537, 498, 534, 603  # items metadata classes
MAGIC, RARE, UNIQUE = 4, 6, 7


def monarch(unit: int, *, x: int = 0, y: int = 0, identified: bool = False, quality: int = MAGIC) -> Carried:
    return Carried(unit, MONARCH, x, y, (2, 3), quality, identified)


def drop_of(unit: int, txt: int = MONARCH, quality: int = MAGIC, **changes: Any) -> Drop:
    found = Drop(unit, 100.0, 100.0, 'Magic Monarch', VALUABLE, (2, 3), False, 'shown', txt, quality)
    return replace(found, **changes)


def read(sockets: int, block: int, faster_block: int, *, identified: bool = True) -> dict[str, Any]:
    """An identify read of a magic Monarch as the worker gives it: block is the base's and the affix's (the read of
    unit 1728653239 says 32 = 22 + 10)."""
    stats = (('toblock', 20, block), ('item_fasterblockrate', 102, faster_block))
    rows = [
        {'name': name, 'memory_stat': {'id': stat, 'layer': 0, 'raw': raw}, 'value': raw, 'status': 'decoded'}
        for name, stat, raw in stats
        if raw
    ]
    return {
        'item': {'name': 'Monarch', 'base_name': 'Monarch', 'base_code': 'uit', 'rarity': 'magic',
                 'identified': identified, 'ethereal': False, 'sockets': sockets},
        'source': {},
        'decoded_stats': rows,
    }  # fmt: skip


VENDOR = {'triage': {'verdict': 'vendor', 'reason': 'no supported trade combination for these stats', 'band': None}}


@dataclass
class Hands:
    """The game as the field routine sees it: a pack, the reads the worker gives after an identify, the drops."""

    pack: Pack
    reads: dict[int, Appraised] = field(default_factory=dict)
    own: frozenset[int] = frozenset()  # the player's units: never the loop's
    quiet: str | None = None
    takes: bool = True  # an identify click takes
    raises: BaseException | None = None
    falls: bool = True
    name: str | None = GAME
    identified: list[int] = field(default_factory=list)
    dropped: list[int] = field(default_factory=list)
    rejected: list[int] = field(default_factory=list)
    appraised: list[list[int]] = field(default_factory=list)
    gives: bool = True  # the cube's items come out
    taken_out: list[int] = field(default_factory=list)
    put_in: list[int] = field(default_factory=list)

    def game(self) -> str | None:
        return self.name

    def carried(self) -> Pack | None:
        return self.pack

    def loops(self, pack: Pack) -> Sequence[Carried]:
        return [item for item in pack.items if item.unit_id not in self.own and item.txt != TOME]

    def unquiet(self) -> str | None:
        return self.quiet

    def identify(self, items: Sequence[Carried]) -> list[Carried]:
        if self.raises is not None:
            raise self.raises
        if not self.takes:
            return []
        units = {item.unit_id for item in items}
        self.identified += sorted(units)
        charges = (self.pack.identifies or 0) - len(units)
        items_now = tuple(replace(i, identified=True) if i.unit_id in units else i for i in self.pack.items)
        self.pack = replace(self.pack, items=items_now, identifies=charges)
        return [replace(item, identified=True) for item in items]

    def appraise(self, units: Sequence[int]) -> Mapping[int, Appraised]:
        self.appraised.append(list(units))
        return {unit: self.reads[unit] for unit in units if unit in self.reads}

    def copies(self, facts: ItemFacts) -> Sequence[ItemFacts] | None:
        return []

    def drop(self, item: Carried, why: str) -> bool:
        assert why.startswith('in the field: ')
        if self.falls:
            self.dropped.append(item.unit_id)
            self.pack = replace(self.pack, items=tuple(i for i in self.pack.items if i.unit_id != item.unit_id))
        return self.falls

    def reject(self, item: Carried, why: str) -> None:
        self.rejected.append(item.unit_id)

    def cubed(self, pack: Pack) -> Sequence[Carried]:
        return [item for item in pack.in_cube if item.unit_id not in self.own]

    def take_out(self, items: Sequence[Carried]) -> list[int]:
        """Each into the inventory's first free block (cube.py `unpack`'s Ctrl + click), when `gives`."""
        self.taken_out += [item.unit_id for item in items]
        if not self.gives:
            return []
        for item in items:
            spot = self.pack.inventory.first_spot(item.size)
            assert spot is not None, item
            self.pack = replace(
                self.pack,
                items=(*self.pack.items, replace(item, x=spot[0], y=spot[1])),
                in_cube=tuple(i for i in self.pack.in_cube if i.unit_id != item.unit_id),
                cube_items=self.pack.cube_items - {item.unit_id},
            )
        return [item.unit_id for item in items]

    def put_back(self, units: Sequence[int]) -> int:
        self.put_in += list(units)
        back = [i for i in self.pack.items if i.unit_id in units]
        self.pack = replace(
            self.pack,
            items=tuple(i for i in self.pack.items if i.unit_id not in units),
            in_cube=(*self.pack.in_cube, *back),
            cube_items=self.pack.cube_items | {i.unit_id for i in back},
        )
        return len(back)


@pytest.fixture
def lines() -> list[str]:
    return []


@pytest.fixture
def looped(lines: list[str]) -> Field:
    found = Field(log=lambda text, *args: lines.append(text % args))
    found.looping = lambda: True
    return found


def picked(found: Field, *units: int, txt: int = MONARCH, quality: int = MAGIC) -> None:
    for unit in units:
        assert found.pick(drop_of(unit, txt, quality), (GAME, 7)), unit


def tome_pack(*items: Carried, charges: int = 20) -> Pack:
    return Pack((Carried(1, TOME, 9, 0, (1, 2)), *items), identifies=charges)


# -- the switch and the classes ---------------------------------------------------------------------------------------


def test_m4_ships_on_for_every_class_built():
    """G6 first (design.md §7 M4), then G9-G11: the player, 2026-10-20 ~11:05: "turn on G9-G11 too"; G14 and G15,
    the big items, ~12:00: "start all three"; G18 the big uniques and sets, ~13:28: "identify a big items in the
    middle of the run"; G19 the magic gloves, ~13:30: "we want to identify magic gloves"."""
    assert FIELD_IDENTIFY
    assert api.FIELD_BIG
    assert api.FIELD_OVERSIZE
    assert api.FIELD_NAMED
    assert frozenset(('G6', 'G9', 'G10', 'G11', 'G14', 'G15', 'G18', 'G19')) == CLASSES
    assert frozenset(('G9', 'G10', 'G11')) <= api.IMPLEMENTED
    assert api.IDENTIFY_RESERVE == 5


def test_a_magic_monarch_the_good_pickup_leaves_is_picked_for_the_field_identify(looped):
    assert looped.takes(drop_of(10)) == 'G6'
    assert looped.pick(drop_of(10), (GAME, 7))
    assert looped.class_of(10, GAME) == 'G6'
    assert looped.class_of(10, 'another game') is None


@pytest.mark.parametrize(
    ('why', 'drop'),
    [
        ('a white Monarch: judged off the ground (G5), never a field identify', drop_of(11, quality=2)),
        ('a rare Monarch: no G6 row', drop_of(12, quality=RARE)),
        ('a prized drop is a sure valuable already', drop_of(13, prized=True)),
        ('a magic Sacred Targe: no class', drop_of(14, SACRED_TARGE)),
        ('a potion or gold: no valuable', drop_of(15, kind='healing')),
    ],
)
def test_what_no_class_takes_is_not_picked_for_it(looped, why, drop, monkeypatch):
    monkeypatch.setattr(api, 'FIELD_BIG', False)  # the size classes: their own tests below
    monkeypatch.setattr(api, 'FIELD_OVERSIZE', False)
    assert looped.takes(drop) is None, why


# -- the big items (G14, G15) ----------------------------------------------------------------------------------------

ARCHON, GRAND_MATRON_BOW, ZAKARUM, HEAVY_BELT = 443, 302, 501, 347  # items metadata classes (utp, amc, pae, tbl)


def big(unit: int, txt: int, quality: int, size: tuple[int, int], **changes: Any) -> Drop:
    return drop_of(unit, txt, quality, size=size, label='Magic' if quality == MAGIC else 'Rare', **changes)


@pytest.mark.parametrize(
    ('klass', 'drop'),
    [
        ('G14', big(60, ARCHON, MAGIC, (2, 3))),  # a magic Archon Plate: no field class before (G12 is off)
        ('G14', big(61, SACRED_TARGE, MAGIC, (2, 2))),  # 4 cells, the least of Q6's "every item >= 4 cells"
        ('G14', big(62, MONARCH, RARE, (2, 3))),  # a rare Monarch: no G6 row
        ('G15', big(63, GRAND_MATRON_BOW, RARE, (2, 4))),  # over the cap: "like spears, matron bow"
        ('G15', big(64, ZAKARUM, RARE, (2, 4))),
        ('G6', big(65, MONARCH, MAGIC, (2, 3))),  # a class of its own first
    ],
)
def test_a_big_shown_magic_or_rare_item_is_picked_for_the_field_check(looped, klass, drop):
    """The player, 2026-10-20 ~11:55: "bases or blue/rare items might take much place (like spears, matron bow) --
    we want to check them and drop in the middle of the run"; ~12:00 "start all three"."""
    assert looped.takes(drop) == klass
    assert looped.pick(drop, (GAME, 7))
    assert looped.class_of(drop.unit_id, GAME) == klass


def test_the_size_classes_take_only_what_the_filter_shows_and_each_switch_turns_one_off(looped, monkeypatch):
    assert looped.takes(big(70, HEAVY_BELT, RARE, (2, 1))) is None  # 2 cells: carried as before
    assert looped.takes(big(71, ARCHON, MAGIC, (2, 3), source='material')) is None  # not the filter's gear
    assert looped.takes(big(72, ARCHON, MAGIC, (2, 3), prized=True)) is None  # the marks': a sure valuable
    assert Field().takes(big(73, ARCHON, MAGIC, (2, 3))) is None  # the loop off: KP_1 by hand as before
    monkeypatch.setattr(api, 'FIELD_BIG', False)
    assert looped.takes(big(74, ARCHON, MAGIC, (2, 3))) is None
    assert looped.takes(big(75, GRAND_MATRON_BOW, RARE, (2, 4))) == 'G15'
    monkeypatch.setattr(api, 'FIELD_OVERSIZE', False)
    assert looped.takes(big(76, GRAND_MATRON_BOW, RARE, (2, 4))) is None


ROOMY = ('..........', '..........', '..........', '..........')


def test_a_big_item_is_taken_only_with_a_grand_charms_room_left_after_it(looped):
    bow = big(80, GRAND_MATRON_BOW, RARE, (2, 4))
    assert api.leaves_room(ROOMY, (2, 4))
    assert api.leaves_room(None, (2, 4))  # unread: the pickup's own room rule decides
    two = ('########..', '########..', '########..', '########..')  # a 2x4 hole and nothing else
    assert not api.leaves_room(two, (2, 4))
    three = ('#######...', '#######...', '#######...', '#######...')  # a 1x4 column left beside it
    assert api.leaves_room(three, (2, 4))
    assert not looped.pick(bow, (GAME, 7), two)
    assert looped.class_of(80, GAME) is None  # not remembered: seen again at the next look
    assert looped.pick(bow, (GAME, 7), three)
    ring = drop_of(81, RING, source='material', size=(1, 1))
    assert looped.pick(ring, (GAME, 7), ('#########.', '##########', '##########', '##########'))  # small: as before


def archon_read(sockets: int, life: int = 0) -> dict[str, Any]:
    stats = [{'name': 'maxhp', 'memory_stat': {'id': 7, 'layer': 0, 'raw': life * 256}, 'value': life,
              'status': 'decoded'}] if life else []  # fmt: skip
    return {
        'item': {'name': 'Archon Plate', 'base_name': 'Archon Plate', 'base_code': 'utp', 'rarity': 'magic',
                 'identified': True, 'ethereal': False, 'sockets': sockets},
        'source': {},
        'decoded_stats': stats,
    }  # fmt: skip


def test_a_bad_big_item_is_dropped_in_the_field_and_a_jewelers_one_kept(looped):
    """Q6/G14: a magic Archon Plate with no paid roll is put down where it was identified; a 4os one (Jeweler's,
    a want row) is kept whatever the appraisal says (api.droppable)."""
    plain, jewelers = Carried(90, ARCHON, 0, 0, (2, 3), MAGIC, False), Carried(91, ARCHON, 2, 0, (2, 3), MAGIC, False)
    hands = Hands(tome_pack(plain, jewelers))
    hands.reads[90] = Appraised(archon_read(0, life=20), VENDOR, 'vendor')
    hands.reads[91] = Appraised(archon_read(4), VENDOR, 'vendor')
    for unit in (90, 91):
        assert looped.pick(big(unit, ARCHON, MAGIC, (2, 3)), (GAME, 7))

    done = looped.settle(hands, 'Town Portal')

    assert sorted(hands.identified) == [90, 91]
    assert hands.dropped == [90]
    assert hands.rejected == [90]
    assert done.dropped == 1


def test_nothing_is_picked_for_it_with_the_loop_off_or_the_switch_off(looped, monkeypatch):
    by_hand = Field()
    assert by_hand.takes(drop_of(10)) is None  # KP_1 and attack mode by hand keep the GOOD pickup as it was
    monkeypatch.setattr(api, 'FIELD_IDENTIFY', False)
    assert looped.takes(drop_of(10)) is None
    assert not looped.pick(drop_of(10), (GAME, 7))


@pytest.mark.parametrize(
    ('klass', 'drop'),
    [
        ('G9', drop_of(20, KRISS)),
        ('G9', drop_of(21, KRISS, RARE)),
        ('G10', drop_of(22, CIRCLET)),
        ('G11', drop_of(23, RING, source='material')),
    ],
)
def test_the_other_classes_are_on_and_each_off_alone(looped, klass, drop):
    assert looped.takes(drop) == klass  # the player, 2026-10-20 ~11:05: "turn on G9-G11 too"
    assert looped.takes(drop, frozenset(('G6',))) is None


# -- the routine ------------------------------------------------------------------------------------------------------


def test_the_real_monarch_of_blocking_is_identified_and_dropped_at_the_feet_and_never_picked_again(looped, lines):
    """unit 1728653239 (2026-10-18 00:04:34 picked, 00:06:54 identified): suffix 172, block 10 / faster block 15,
    appraised vendor. With M4 it is put down where it was identified."""
    unit = BLOCKING['observation']['source']['unit_id']
    hands = Hands(tome_pack(monarch(unit, x=3)))
    hands.reads[unit] = Appraised(BLOCKING['observation'], BLOCKING['result'], BLOCKING['verdict'])
    picked(looped, unit)

    done = looped.settle(hands, 'Town Portal')

    assert hands.identified == [unit]
    assert hands.dropped == [unit]
    assert hands.rejected == [unit]  # PutDown.reject: not picked up again this game
    assert done.dropped == 1
    assert done.judged[0].decision is not None
    assert (done.judged[0].decision.action, done.judged[0].decision.rule) == (Action.DROP, 'K8')
    assert any('drop K8 worthless' in line for line in lines)
    assert lines[-1] == 'Macro: loot: field: Town Portal: 1 identified, 1 dropped, 0 kept'
    again = looped.settle(hands, 'Save and Exit')  # safe to call again: nothing is left
    assert again.judged == ()
    assert hands.identified == [unit]


@pytest.mark.parametrize(
    ('why', 'sockets', 'block', 'faster'),
    [
        ('Jeweler\'s Monarch of Deflecting, 4os: "we absolutely want to keep it"', 4, 42, 30),
        ('a 4os magic Monarch of any suffix (9.3->71.5 asks)', 4, 32, 15),
        ('a 3os Monarch of Deflecting (q1 6, 20 sellers)', 3, 42, 30),
    ],
)
def test_a_wanted_monarch_is_kept_even_when_the_appraisal_says_vendor(looped, why, sockets, block, faster):
    hands = Hands(tome_pack(monarch(30)))
    hands.reads[30] = Appraised(read(sockets, block, faster), VENDOR, 'vendor')
    picked(looped, 30)

    done = looped.settle(hands, 'Town Portal')

    assert hands.identified == [30], why
    assert hands.dropped == [], why
    assert hands.rejected == [], why
    decision = done.judged[0].decision
    assert decision is not None, why
    assert decision.action == Action.KEEP, (why, decision)


def test_only_the_items_picked_for_the_field_identify_are_touched(looped):
    """Today's pickup (a magic Monarch the MOST level took, the player's own) keeps today's town path."""
    hands = Hands(tome_pack(monarch(40), monarch(41, x=2), monarch(42, x=4)), own=frozenset((42,)))
    for unit in (40, 41, 42):
        hands.reads[unit] = Appraised(read(0, 32, 15), VENDOR, 'vendor')
    picked(looped, 40, 42)  # 41 was not picked for it; 42 sits on the player's cell

    looped.settle(hands, 'Town Portal')

    assert hands.identified == [40]
    assert hands.dropped == [40]


def test_it_waits_near_a_hostile_and_says_so_once(looped, lines):
    hands = Hands(tome_pack(monarch(50)), quiet='2 hostiles within 30')
    picked(looped, 50)

    first = looped.settle(hands, 'Town Portal')
    looped.settle(hands, 'Town Portal')

    assert first.waited == '2 hostiles within 30'
    assert first.pending == 1
    assert hands.identified == []
    assert hands.dropped == []
    assert lines == ['Macro: loot: field: Town Portal: 1 to identify wait: 2 hostiles within 30']


def test_no_charge_nothing_identified_cain_in_town(looped, lines):
    hands = Hands(tome_pack(monarch(60), charges=0))
    picked(looped, 60)
    looped.settle(hands, 'Town Portal')
    assert hands.identified == []
    assert any('empty or not carried' in line for line in lines)


def test_an_identify_that_does_not_take_is_tried_a_bounded_number_of_times(looped):
    hands = Hands(tome_pack(monarch(70)), takes=False)
    picked(looped, 70)
    for _ in range(MOST_TRIES + 3):
        looped.settle(hands, 'Town Portal')
    assert looped.tries[70] == MOST_TRIES
    assert hands.dropped == []


def test_the_players_hand_ends_the_batch_and_counts_no_failure(looped):
    hands = Hands(tome_pack(monarch(80)), raises=Hand('the player moved the pointer'))
    picked(looped, 80)
    with pytest.raises(Hand):
        looped.settle(hands, 'Town Portal')
    assert looped.tries[80] == 0
    assert hands.dropped == []


def test_no_identified_read_or_no_appraisal_keeps_the_item(looped):
    hands = Hands(tome_pack(monarch(90), monarch(91, x=2)))
    hands.reads[90] = Appraised(read(0, 32, 15, identified=False), VENDOR, 'vendor')  # the read says unidentified
    picked(looped, 90, 91)  # 91: the worker gave nothing
    done = looped.settle(hands, 'Town Portal')
    assert hands.dropped == []
    assert [judged.decision for judged in done.judged] == [None, None]


def test_a_drop_that_does_not_fall_is_not_remembered_as_put_down(looped):
    hands = Hands(tome_pack(monarch(100)), falls=False)
    hands.reads[100] = Appraised(read(0, 32, 15), VENDOR, 'vendor')
    picked(looped, 100)
    looped.settle(hands, 'Town Portal')
    assert hands.rejected == []


def test_an_item_identified_but_not_yet_decided_is_decided_without_a_second_scroll(looped):
    hands = Hands(tome_pack(monarch(110, identified=True)))
    hands.reads[110] = Appraised(read(0, 32, 15), VENDOR, 'vendor')
    picked(looped, 110)
    looped.settle(hands, 'room')
    assert hands.identified == []
    assert hands.dropped == [110]


def test_the_batch_is_capped_by_the_charges_largest_class_first(looped):
    hands = Hands(tome_pack(monarch(120), monarch(121, x=2), monarch(122, x=4), charges=2))
    picked(looped, 120, 121, 122)
    done = looped.settle(hands, 'Town Portal')
    assert hands.identified == [120, 121]
    assert done.pending == 1  # the third waits (Cain in town); the two with no read are kept (S8)


def test_a_new_game_forgets_the_last_games_picks(looped):
    picked(looped, 130)
    hands = Hands(tome_pack(monarch(130)), name='game-2')
    hands.reads[130] = Appraised(read(0, 32, 15), VENDOR, 'vendor')
    looped.settle(hands, 'Town Portal')
    assert hands.identified == []  # unit ids are dealt again each game: not the item picked for it


def test_nothing_with_the_loop_off():
    hands = Hands(tome_pack(monarch(140)))
    off = Field()
    off.picked[140] = (GAME, 'G6')
    assert off.settle(hands, 'Town Portal').judged == ()
    assert hands.identified == []


# -- the guards below the decision ------------------------------------------------------------------------------------


def facts_of(observation: dict[str, Any], owner: Owner = Owner.LOOP) -> ItemFacts:
    return from_observation(observation, where=Where.INVENTORY, owner=owner, unit_id=1)


def test_the_field_drop_refuses_the_players_the_unidentified_named_kinds_and_wanted_items():
    junk = facts_of(read(0, 32, 15))
    assert droppable(junk, assess(junk, worth=None, verdict='vendor')) is None
    assert droppable(facts_of(read(0, 32, 15), Owner.PLAYER)) == "not the loop's (owner player)"
    assert droppable(facts_of(read(0, 32, 15), Owner.UNKNOWN)) == "not the loop's (owner unknown)"
    assert droppable(facts_of(read(0, 32, 15, identified=False))) == 'not identified'
    deflecting = facts_of(read(4, 42, 30))
    assert (droppable(deflecting, assess(deflecting, worth=None, verdict='vendor')) or '').startswith('wanted: ')
    assert droppable(junk, assess(junk, worth=2.0, verdict='vendor')) == 'expensive (2 Ist)'
    unique = replace(junk, quality=UNIQUE)
    assert droppable(unique) == 'a small set or unique item'  # G18 takes BIG_CELLS cells and more only
    assert droppable(replace(unique, size=(2, 3))) == 'a set or unique item with no appraisal'
    for kind in ('rune', 'gemr', 'hpot', 'scha', 'lcha', 'jewl', 'book', 'key'):
        assert droppable(replace(junk, base_type=kind)) is not None, kind


def test_the_tome_reserve_counts_only_with_the_switch_on(monkeypatch):
    assert reserve_short(4)
    assert not reserve_short(5)
    assert not reserve_short(None)  # unread, or no tome: says nothing
    monkeypatch.setattr(api, 'FIELD_IDENTIFY', False)
    assert not reserve_short(0)


def test_the_hook_calls_the_runs_field_routine_and_never_raises_but_the_players_hand():
    calls: list[str] = []

    class Run:
        field = staticmethod(calls.append)

    api.settle(Run(), 'Town Portal')
    assert calls == ['Town Portal']
    api.settle(object(), 'Town Portal')  # a run with none: nothing

    def broken(when: str) -> None:
        raise ValueError('a bug')

    def hand(when: str) -> None:
        raise Hand('the player')

    Run.field = staticmethod(broken)
    api.settle(Run(), 'room')  # logged, the leg goes on
    Run.field = staticmethod(hand)
    with pytest.raises(Hand):
        api.settle(Run(), 'room')


# -- the acceptance table through the field routine (fixtures/valuables.json, design.md §6.1) ----------------------


def field_cases() -> list:
    from tests.inventory_tracking.loot.test_valuables import CASES

    return [
        pytest.param(case, id=case['id'])
        for case in CASES
        if case['item'].get('code') == 'uit'
        and case['item']['quality'] == 'magic'
        and case['item'].get('identified', True)
        and 'decision' in case['expect']
    ]


@pytest.mark.parametrize('case', field_cases())
def test_each_magic_monarch_of_the_acceptance_table_is_kept_or_dropped_in_the_field_as_decided(looped, case):
    from tests.inventory_tracking.loot.test_valuables import observation, owned_of

    given = case['value']
    triage: dict[str, Any] = {'verdict': given['verdict']}
    if given['worth'] is not None:
        triage |= {'decision_ist': given['worth'], 'roll_comparison': {'by': 'the fixture'}}
    hands = Hands(tome_pack(monarch(200)))
    hands.reads[200] = Appraised(observation(case['item'], 200), {'triage': triage}, given['verdict'])
    owned = owned_of(case)
    hands.copies = lambda facts: owned  # pyrefly: ignore[bad-assignment] # the case's owned copies
    picked(looped, 200)

    done = looped.settle(hands, 'Town Portal')

    expect = case['expect']
    (judged,) = done.judged
    assert judged.decision is not None, case['id']
    assert (judged.decision.action.value, judged.decision.rule) == (expect['decision'], expect['rule']), judged
    assert hands.dropped == ([200] if expect['decision'] == 'drop' else []), (case['id'], case['source'])


# -- G18: the big uniques and sets, and the cube's items (the player, 2026-10-20 ~13:28) ------------------------------

WAR_CLUB, GOTHIC_PLATE, GRAND_CHARM = 116, 324, 620  # items metadata classes of 9m9, gth, cm3
STUMP = {'base': 'War Club', 'code': '9m9', 'quality': 'unique', 'name': 'Bloodtree Stump', 'size': [2, 4],
         'ranges': {'17:0': [180, 220]}}  # fmt: skip # uniqueitems.json:5377: dmg% 180-220 the only variable roll


def club(unit: int, *, x: int = 0, y: int = 0, identified: bool = False) -> Carried:
    return Carried(unit, WAR_CLUB, x, y, (2, 4), UNIQUE, identified)


def stump_read(unit: int, damage: int, worth: float | None, verdict: str = 'vendor') -> Appraised:
    from tests.inventory_tracking.loot.test_valuables import observation

    triage: dict[str, Any] = {'verdict': verdict}
    if worth is not None:
        triage |= {'decision_ist': worth, 'roll_comparison': {'by': 'the test'}}
    return Appraised(observation({**STUMP, 'rolls': {'17:0': damage}}, unit), {'triage': triage}, verdict)


def stumps(*damages: int) -> list[ItemFacts]:
    from tests.inventory_tracking.loot.test_valuables import facts_of as owned_facts

    return [owned_facts({**STUMP, 'rolls': {'17:0': d}}, 100 + i, owner=Owner.PLAYER) for i, d in enumerate(damages)]


def noted(found: Field, unit: int, txt: int = WAR_CLUB, size: tuple[int, int] = (2, 4), quality: int = UNIQUE) -> bool:
    return found.note(drop_of(unit, txt, quality, size=size, source='unique', prized=True), (GAME, 7))


def test_only_a_big_set_or_unique_item_is_noted_with_the_loop_and_the_switch_on(looped, monkeypatch):
    assert noted(looped, 30)
    assert looped.class_of(30, GAME) == 'G18'
    assert not noted(looped, 31, RING, (1, 1))  # a unique ring: small, to town as before
    assert not noted(looped, 32, GRAND_CHARM, (1, 3))  # a unique charm (Gheed's, Torch, Anni): never
    assert not noted(looped, 33, MONARCH, quality=MAGIC)  # magic: the other classes' (`takes`)
    assert noted(looped, 34, GOTHIC_PLATE, (2, 3), quality=5)  # a set item of 6 cells
    assert not Field().note(drop_of(35, WAR_CLUB, UNIQUE, size=(2, 4)), (GAME, 7))  # the loop off
    monkeypatch.setattr(api, 'FIELD_NAMED', False)
    assert not noted(looped, 36)


@pytest.mark.parametrize(
    ('damage', 'worth', 'verdict', 'owned', 'dropped'),
    [
        pytest.param(190, 0.719, 'vendor', (205,), True, id='surplus_not_better_cheap_dropped'),
        pytest.param(205, 0.719, 'vendor', (205,), True, id='equal_cheap_dropped'),
        pytest.param(190, 0.719, 'vendor', (), False, id='first_copy_kept'),
        pytest.param(215, 0.8, 'vendor', (200,), False, id='better_than_every_owned_kept_though_vendor'),
        pytest.param(215, 0.8, 'slow', (200, 210), False, id='better_cheap_kept'),
        pytest.param(190, 1.4, 'sell', (205,), False, id='expensive_duplicate_kept'),
        pytest.param(190, None, 'vendor', (205,), False, id='no_price_by_its_rolls_kept'),
    ],
)
def test_a_big_unique_is_put_down_in_the_field_only_as_a_surplus_copy(looped, lines, damage, worth, verdict, owned,
                                                                       dropped):  # fmt: skip
    hands = Hands(tome_pack(club(30)))
    hands.reads[30] = stump_read(30, damage, worth, verdict)
    copies = stumps(*owned)
    hands.copies = lambda facts: copies  # pyrefly: ignore[bad-assignment] # the case's owned copies
    assert noted(looped, 30)

    done = looped.settle(hands, 'Town Portal')

    assert hands.identified == [30]
    assert hands.dropped == ([30] if dropped else [])
    (judged,) = done.judged
    assert judged.dropped == dropped, lines
    if dropped:
        assert hands.rejected == [30]  # never picked up again this game


def test_the_surplus_rule_is_pure_and_never_drops_without_evidence():
    from tests.inventory_tracking.loot.test_valuables import facts_of as fixture_facts

    stump = replace(fixture_facts({**STUMP, 'rolls': {'17:0': 190}}), size=(2, 4))
    owned = stumps(205)
    assert api.surplus(stump, assess(stump, worth=0.5, verdict='slow'), owned) is None
    assert api.surplus(stump, assess(stump, worth=0.5, verdict='slow'), None) == 'its owned copies cannot be told'
    assert api.surplus(stump, assess(stump, worth=0.5, verdict='slow'), []) == 'the first copy'
    # No price by its rolls: dropped only as the same item, equal or worse, with a KB band under 1 Ist
    under = Band(0.2, 0.6, 15, '2026-10-04')
    assert api.surplus(stump, assess(stump, worth=None, band=under), owned) is None
    assert api.surplus(stump, assess(stump, worth=None, band=Band(0.2, 1.0)), owned) is not None
    assert api.surplus(stump, assess(stump, worth=None), owned) is not None  # no band at all: kept (Q13)
    sigon = replace(
        fixture_facts({'base': 'Gothic Plate', 'code': 'gth', 'quality': 'set', 'name': "Sigon's Shelter"}), size=(2, 3)
    )
    same = [replace(sigon, unit_id=101, owner=Owner.PLAYER)]
    assert api.surplus(sigon, assess(sigon, worth=None), same) is not None  # the KB has no price (unresolved)
    assert api.droppable(sigon, assess(sigon, worth=None), same) is not None


def in_cube(*items: Carried, inventory: tuple[Carried, ...] = (), charges: int = 20) -> Pack:
    pack = tome_pack(*inventory, charges=charges)
    return replace(pack, in_cube=items, cube_items=frozenset(i.unit_id for i in items), cube=('...',) * 4)


def test_a_big_unique_in_the_cube_is_taken_out_identified_and_dropped_or_put_back(looped, lines):
    """The War Club of 13:19:34 (put into the cube with the inventory full): out of the cube, the Tome on it in the
    inventory, put down when surplus; a kept one goes back into the cube."""
    hands = Hands(in_cube(club(30), club(31, x=2)))
    hands.reads[30] = stump_read(30, 190, 0.719)  # surplus: dropped
    hands.reads[31] = stump_read(31, 219, 0.9, 'slow')  # better than the owned: kept
    copies = stumps(205)
    hands.copies = lambda facts: copies  # pyrefly: ignore[bad-assignment] # one owned copy
    assert noted(looped, 30)
    assert noted(looped, 31)

    done = looped.settle(hands, 'Town Portal')

    assert sorted(hands.taken_out) == [30, 31]
    assert sorted(hands.identified) == [30, 31]
    assert hands.dropped == [30]
    assert hands.put_in == [31]
    assert [i.unit_id for i in hands.pack.in_cube] == [31]
    assert done.dropped == 1
    assert 'Macro: loot: field: Town Portal: 2 of 2 taken out of the cube to identify' in lines
    assert 'Macro: loot: field: Town Portal: 1 of 1 put back into the cube' in lines
    assert looped.settle(hands, 'Town Portal') == api.Settled()  # decided: nothing again


def test_an_unidentified_big_item_in_the_cube_from_an_earlier_game_is_seen_by_its_kind(looped):
    """An item carried into a new game has a new unit: the cube's unidentified big uniques and magic or rare items
    are field items by their kind; a unique charm, a small item or an identified one is not touched."""
    charm = Carried(40, GRAND_CHARM, 4, 0, (1, 3), UNIQUE, False)
    small = Carried(41, RING, 5, 0, (1, 1), UNIQUE, False)
    known = club(42, x=6, identified=True)
    hands = Hands(in_cube(club(30), charm, small, known))
    hands.reads[30] = stump_read(30, 190, 0.719)
    copies = stumps(205)
    hands.copies = lambda facts: copies  # pyrefly: ignore[bad-assignment] # one owned copy

    looped.settle(hands, 'Save and Exit')

    assert hands.taken_out == [30]
    assert hands.dropped == [30]
    assert looped.class_of(30, GAME) == 'G18'
    assert {40, 41, 42} & set(hands.identified) == set()


def test_the_cubes_items_wait_for_cain_without_room_and_a_stuck_one_is_tried_a_bounded_number_of_times(looped, lines):
    full = tuple(Carried(50 + i, RING, x, y, (1, 1), MAGIC, True) for i, (x, y) in
                 enumerate((x, y) for y in range(4) for x in range(10) if (x, y) not in ((9, 0), (9, 1))))  # fmt: skip
    hands = Hands(in_cube(club(30), inventory=full))
    hands.loops = lambda pack: [i for i in pack.items if i.unit_id < 50 and i.txt != TOME]  # pyrefly: ignore[bad-assignment]
    assert noted(looped, 30)
    done = looped.settle(hands, 'room')
    assert hands.taken_out == []
    assert done.pending == 1
    assert 'Macro: loot: field: room: 1 in the cube wait: no room to take them out (Cain in town)' in lines

    stuck = Hands(in_cube(club(30)), gives=False)
    for _ in range(MOST_TRIES + 2):
        looped.settle(stuck, 'Town Portal')
    assert stuck.taken_out == [30] * MOST_TRIES  # then Cain in town
    assert stuck.identified == []


def test_the_cubes_items_are_not_taken_out_near_a_hostile(looped):
    hands = Hands(in_cube(club(30)), quiet='1 hostiles within 30')
    assert noted(looped, 30)
    assert looped.settle(hands, 'Town Portal').waited == '1 hostiles within 30'
    assert hands.taken_out == []


def test_a_magic_glove_the_filter_shows_is_picked_for_the_field_identify_as_g19(looped):
    """The player, 2026-10-20 ~13:30: "we want to identify magic gloves that can roll something like 40ias + annother
    valuable roll, like skills" (20 IAS is the most a magic glove rolls: loot/build_wants.py G19)."""
    from inventory_tracking.loot.facts import base_of_code

    gloves = base_of_code('hgl')
    assert gloves is not None
    drop = drop_of(60, gloves[0], MAGIC, size=(2, 2), label='Magic Gauntlets')
    assert looped.takes(drop) == 'G19'
    assert looped.pick(drop, (GAME, 7))
    assert looped.takes(replace(drop, quality=RARE)) == 'G14'  # a rare glove: by its size, as before


# -- room for the big items mid-run (FIELD_AT_ONCE) ------------------------------------------------------------------
# The player, 2026-10-20 ~14:28: "we must redesign our routins to actually have space for mid-run identifying big
# items". A magic Monarch at 14:24:32 (game 15) and two magic gloves at 13:53 were never picked: after a visit the
# player's items fill 30 of the 40 cells (visits/142128.json, the `end` stop) and `leaves_room` wanted a 1x3 after.

VISIT = ('###..#####', '###..#####', '##...#####', '##...#####')  # the free cells after a visit, exactly
DEMONHIDE_GLOVES, VAMBRACES, GRAND_CHARM, IST = 380, 452, 620, 648  # items metadata classes
OWN = frozenset((101, 102, 103, 104))
EMPTY_CUBE = ('...', '...', '...', '...')
FULL_CUBE = ('###', '###', '###', '###')


def players_items() -> tuple[Carried, ...]:
    """The player's items on exactly the visit's taken cells (VISIT), the Tome among them (the Gheed's, the charms,
    the keys: never moved, sold or dropped)."""
    return (
        Carried(101, GHEEDS_BASE, 0, 0, (3, 2), UNIQUE, True),
        Carried(102, GRAND_CHARM, 0, 2, (2, 2), MAGIC, True),
        Carried(103, GRAND_CHARM, 5, 0, (4, 4), MAGIC, True),
        Carried(1, TOME, 9, 0, (1, 2)),
        Carried(104, 543, 9, 2, (1, 2), 2, True),  # the keys
    )


def visited(*items: Carried, charges: int = 20, cube: tuple[str, ...] | None = EMPTY_CUBE) -> Pack:
    return Pack((*players_items(), *items), cube=cube, identifies=charges)


def ground(unit: int, txt: int, **changes: Any) -> Drop:
    """A magic drop the filter shows, its size from sizes.json (game/decode.py `item_size`), never written here."""
    return drop_of(unit, txt, MAGIC, size=item_size(txt), **changes)


def carried_monarch(unit: int, x: int = 3, y: int = 0) -> Carried:
    return Carried(unit, MONARCH, x, y, item_size(MONARCH), MAGIC, False)


def squeeze(found: Field, drop: Drop, *, carried: frozenset[int] = frozenset(), waiting: Sequence[Drop] = (),
            charges: int | None = 20, room: tuple[str, ...] = VISIT) -> bool:  # fmt: skip
    return found.pick(drop, (GAME, 7), room, carried=carried, waiting=lambda: list(waiting), tome=lambda: charges)


def test_the_visits_free_cells_leave_no_grand_charm_after_a_monarch_or_a_glove():
    assert visited().inventory == api.Grid(VISIT)  # the fixture is the visit's grid
    assert item_size(MONARCH) == (2, 3)  # sizes.json: Monarch 2x3 (the player: "monarch is 2x3")
    for txt in (MONARCH, DEMONHIDE_GLOVES, VAMBRACES):
        assert not api.leaves_room(VISIT, item_size(txt)), txt  # the skip of 14:24:32 and 13:53


@pytest.mark.parametrize(('txt', 'klass'), [(MONARCH, 'G6'), (DEMONHIDE_GLOVES, 'G19'), (VAMBRACES, 'G19')])
def test_a_big_field_item_with_only_the_visits_cells_free_is_taken_into_the_block(looped, lines, txt, klass):
    drop = ground(10, txt)
    assert squeeze(looped, drop)
    assert looped.class_of(10, GAME) == klass
    assert looped.waiting == {10: GAME}  # for the identify at once
    assert lines == []


def test_with_the_switch_off_it_is_left_as_before_and_said_once(looped, lines, monkeypatch):
    monkeypatch.setattr(api, 'FIELD_AT_ONCE', False)
    drop = ground(10, MONARCH)
    assert not squeeze(looped, drop)
    assert not squeeze(looped, drop)
    assert looped.class_of(10, GAME) is None
    assert lines == ['Macro: loot: field: magic Monarch (unit 10) left: no room for a 1x3 valuable after it']


@pytest.mark.parametrize(
    ('why', 'kwargs', 'said'),
    [
        ('the Tome is empty', {'charges': 0}, 'the Tome of Identify is empty'),
        ("the Tome's charges unread", {'charges': None}, "the Tome of Identify's charges are unread"),
        ('a Grand Charm lies: it would lose its room', {'waiting': (ground(20, GRAND_CHARM, label='Grand Charm'),)},
         'Grand Charm would lose its room'),
        ('no room for it at all', {'room': ('##########',) * 4}, 'no room for its 2x3'),
    ],
)  # fmt: skip
def test_a_big_item_is_left_when_a_rule_says_so_with_the_reason(looped, lines, why, kwargs, said):
    assert not squeeze(looped, ground(10, MONARCH), **kwargs), why
    assert looped.class_of(10, GAME) is None, why
    assert lines == [f'Macro: loot: field: magic Monarch (unit 10) left: {said}'], why


def test_a_rune_on_the_ground_keeps_its_room_beside_the_monarch(looped):
    """A rune (1x1) still fits after the Monarch: the press goes to it first anyway (pickup.py `choose`)."""
    assert squeeze(looped, ground(10, MONARCH), waiting=(ground(20, IST, label='Ist Rune'),))


def test_only_one_big_item_is_carried_unidentified_at_a_time(looped, lines):
    """The first Monarch taken (still unidentified in the inventory): a pair of gloves next is left until it is
    decided; once it is (dropped or kept), the next big one may come."""
    assert squeeze(looped, ground(10, MONARCH))
    room = ('###..#####', '###..#####', '##...#####', '##...#####')  # read before the first is taken
    assert not squeeze(looped, ground(11, VAMBRACES), carried=frozenset((10,)), room=room)
    assert lines == ['Macro: loot: field: magic Vambraces (unit 11) left: another big item waits to be identified '
                     '(unit 10)']  # fmt: skip
    assert squeeze(looped, ground(11, VAMBRACES), room=room)  # the first still on the ground: no block yet
    looped.judged[10] = 'drop'
    assert squeeze(looped, ground(12, VAMBRACES), carried=frozenset((10, 11)) - {11}, room=room)


def test_the_tomes_charges_are_read_once_in_a_while(looped):
    reads: list[int] = []

    def tome() -> int:
        reads.append(1)
        return 20

    looped.clock = lambda: 100.0
    for unit in (10, 11):
        looped.pick(ground(unit, MONARCH), (GAME, 7), VISIT, tome=tome)
    assert len(reads) == 1  # TOME_FRESH: one inventory read serves the looks after it
    looped.clock = lambda: 100.0 + api.TOME_FRESH
    looped.pick(ground(12, MONARCH), (GAME, 7), VISIT, tome=tome)
    assert len(reads) == 2


def at_once_hands(*items: Carried, **changes: Any) -> Hands:
    return Hands(visited(*items, **{k: changes.pop(k) for k in ('charges', 'cube') if k in changes}), own=OWN,
                 **changes)  # fmt: skip


def test_a_bad_monarch_is_identified_at_the_first_quiet_look_and_dropped_at_the_feet(looped, lines):
    """From the ground to the feet: taken into the block, identified at once, dropped, never picked again; the
    player's items untouched."""
    assert squeeze(looped, ground(10, MONARCH))
    hands = at_once_hands(carried_monarch(10))
    hands.reads[10] = Appraised(read(0, 32, 15), VENDOR, 'vendor')

    assert looped.due()
    assert looped.at_once(hands)

    assert hands.identified == [10]
    assert hands.dropped == [10]
    assert hands.rejected == [10]
    assert hands.put_in == []
    assert not (OWN & {*hands.identified, *hands.dropped, *hands.put_in})
    assert 'Macro: loot: field: at once: 1 identified, 1 dropped, 0 kept' in lines
    assert not looped.due()  # decided: nothing more to look for


def test_a_kept_monarch_goes_into_the_cube_and_the_block_is_free_again(looped, lines):
    assert squeeze(looped, ground(10, MONARCH))
    hands = at_once_hands(carried_monarch(10))
    hands.reads[10] = Appraised(read(4, 42, 30), VENDOR, 'vendor')  # 4os of Deflecting: always kept

    assert looped.at_once(hands)

    assert hands.dropped == []
    assert hands.put_in == [10]
    assert 10 in hands.pack.cube_items
    assert hands.pack.inventory == api.Grid(VISIT)  # the block is free again
    assert 'Macro: loot: field: at once: magic Monarch 4os (unit 10) kept: into the cube' in lines


def test_a_kept_monarch_stays_when_the_cube_is_full_and_the_room_rules_answer_the_next_rune(looped, lines):
    """It stays in the inventory; the next valuable with no room is the room rules' (the pickup's stand and stop,
    lootpolicy.py `verdict`: in the loop a valuable with no room holds; then the cube, the Gheed's swap, a trip:
    running/watch.py `stood_after_cube`)."""
    from inventory_tracking.macros.lootpolicy import PRESS, verdict

    assert squeeze(looped, ground(10, MONARCH))
    hands = at_once_hands(carried_monarch(10), cube=FULL_CUBE)
    hands.reads[10] = Appraised(read(4, 42, 30), VENDOR, 'vendor')

    assert looped.at_once(hands)

    assert hands.put_in == []
    assert hands.dropped == []
    assert 'Macro: loot: field: at once: magic Monarch 4os (unit 10) kept: it stays in the inventory, the cube has '\
           'no room for it' in lines  # fmt: skip
    charm = ground(20, GRAND_CHARM, label='Grand Charm', prized=True)
    assert not hands.pack.inventory.has_room(charm.size)
    assert verdict(charm, PRESS, room=False, shown=False, looped=True).hold  # a 'room' stop: the room rules
    assert squeeze(looped, ground(11, VAMBRACES), carried=frozenset((10,)),
                   room=tuple(str(row) for row in hands.pack.inventory)) is False  # no room: left  # fmt: skip


def test_it_waits_while_a_hostile_is_near_and_identifies_once_quiet(looped, lines):
    assert squeeze(looped, ground(10, MONARCH))
    hands = at_once_hands(carried_monarch(10), quiet='1 hostiles within 30')
    hands.reads[10] = Appraised(read(0, 32, 15), VENDOR, 'vendor')
    looped.clock = lambda: 0.0

    assert looped.due()
    assert not looped.at_once(hands)
    assert hands.identified == []
    assert not looped.due()  # AT_ONCE_EVERY between two looks
    looped.clock = lambda: api.AT_ONCE_EVERY
    hands.quiet = None
    assert looped.due()
    assert looped.at_once(hands)
    assert hands.dropped == [10]
    assert lines[0] == 'Macro: loot: field: at once: 1 to identify wait: 1 hostiles within 30'


def test_a_big_item_still_on_the_ground_reads_no_routine(looped):
    assert squeeze(looped, ground(10, MONARCH))
    hands = at_once_hands()  # not picked up yet
    assert not looped.at_once(hands)
    assert hands.identified == []
    assert hands.appraised == []


def test_no_charge_at_once_waits_for_cain_and_is_not_looked_for_again(looped, lines):
    assert squeeze(looped, ground(10, MONARCH))
    hands = at_once_hands(carried_monarch(10), charges=0)
    assert not looped.at_once(hands)
    assert hands.identified == []
    assert not looped.due()
    assert lines == ['Macro: loot: field: at once: the Tome of Identify is empty or not carried: 1 big wait for Cain']


def test_the_hook_makes_no_hands_until_one_is_due_and_lets_only_the_hand_through(looped):
    made: list[int] = []

    def hands() -> Hands:
        made.append(1)
        return at_once_hands(carried_monarch(10), raises=Hand('the player clicked'))

    assert not api.at_once(hands, looped)
    assert made == []
    assert squeeze(looped, ground(10, MONARCH))
    with pytest.raises(Hand):
        api.at_once(hands, looped)
    assert made == [1]


def test_the_loop_off_or_the_switch_off_makes_no_identify_at_once(looped, monkeypatch):
    assert squeeze(looped, ground(10, MONARCH))
    looped.looping = lambda: False
    assert not looped.due()
    looped.looping = lambda: True
    monkeypatch.setattr(api, 'FIELD_AT_ONCE', False)
    assert not looped.due()


# The Unique Thresher of game 4 (session 20261020T112607Z-7288f87b, Cave Level 2; the player: "could you analyze why
# unique tresher wasn't identified min-run?"): picked at 14:38:57 after a trip for room, put into the cube with a magic
# Ring by the room rule for a Grand Charm at 14:39:23 (hostiles near: the routine waited), and at Save and Exit only the
# Ring came out: a 2x4 with the visit's cells free leaves no 1x3. Now one big item a batch comes out bare.

THRESHER = 255  # items metadata class (Thresher, pole)


def thresher(unit: int = 30, x: int = 0, y: int = 0) -> Carried:
    return Carried(unit, THRESHER, x, y, item_size(THRESHER), UNIQUE, False)


def thresher_hands(*boxed: Carried, read_of: dict[int, Appraised], **changes: Any) -> Hands:
    pack = replace(visited(cube=('...',) * 4), in_cube=boxed, cube_items=frozenset(i.unit_id for i in boxed))
    hands = Hands(pack, own=OWN, **changes)
    hands.reads.update(read_of)
    copies = stumps(205)
    hands.copies = lambda facts: copies  # pyrefly: ignore[bad-assignment] # one owned copy: a surplus one drops
    return hands


def test_the_visits_cells_leave_no_grand_charm_after_a_thresher():
    assert item_size(THRESHER) == (2, 4)
    assert not api.leaves_room(VISIT, item_size(THRESHER))


@pytest.mark.parametrize(('read', 'dropped'), [((190, 0.719), True), ((219, 0.9, 'slow'), False)])
def test_a_big_item_in_the_cube_comes_out_into_the_block_at_save_and_exit(looped, lines, read, dropped):
    """The read stands in for the Thresher's (a surplus copy drops, a better one is kept): out of the cube into the
    2x4 block without the 1x3 after it, identified, then put down or back into the cube; the player's untouched."""
    assert noted(looped, 30, THRESHER, item_size(THRESHER))
    hands = thresher_hands(thresher(), read_of={30: stump_read(30, *read)})

    looped.settle(hands, 'Save and Exit')

    assert hands.taken_out == [30]
    assert hands.identified == [30]
    assert hands.dropped == ([30] if dropped else [])
    assert hands.put_in == ([] if dropped else [30])
    assert not (OWN & {*hands.identified, *hands.dropped, *hands.put_in, *hands.taken_out})
    assert hands.pack.inventory == api.Grid(VISIT)  # the block is free again either way
    assert not any('wait (Cain in town)' in line for line in lines)


def test_where_room_is_made_for_a_valuable_the_reserve_holds_and_it_waits(looped, lines):
    assert noted(looped, 30, THRESHER, item_size(THRESHER))
    hands = thresher_hands(thresher(), read_of={30: stump_read(30, 190, 0.719)})

    done = looped.settle(hands, 'room')

    assert hands.taken_out == []
    assert done.pending == 1
    assert 'Macro: loot: field: room: 1 in the cube wait: no room to take them out (Cain in town)' in lines


def test_one_big_item_a_batch_comes_out_without_the_reserve(looped):
    assert noted(looped, 30, THRESHER, item_size(THRESHER))
    assert noted(looped, 31, THRESHER, item_size(THRESHER))
    kept = {unit: stump_read(unit, 219, 0.9, 'slow') for unit in (30, 31)}
    hands = thresher_hands(thresher(30), thresher(31, x=2), read_of=kept)
    looped.settle(hands, 'Save and Exit')
    assert len(hands.taken_out) == 1


def test_a_big_item_the_room_rules_put_into_the_cube_is_identified_at_the_next_quiet_look(looped, lines):
    """14:39:23: the stash moved it into the cube (2 hostiles within 30); the level run's next quiet look takes it
    out, identifies it and puts it down (or back)."""
    assert noted(looped, 30, THRESHER, item_size(THRESHER))
    hands = thresher_hands(thresher(), read_of={30: stump_read(30, 190, 0.719)})

    assert looped.due()
    assert looped.at_once(hands)

    assert hands.taken_out == [30]
    assert hands.dropped == [30]
    assert 'Macro: loot: field: at once: 1 identified, 1 dropped, 0 kept' in lines


# The rare Kriss of 14:52:26 on 2026-10-20 (20261020T112607Z-7288f87b; the player: "why we couldn't
# pickup/identify/drop rare kris in the last game?"): flawless gems filled the visit's free cells, an identify candidate
# got no cube room or trip. The ruling ~14:58: "we need to optimize space (move to cube) and identify items during games
# / if we have no room for optimization to keep picking up items - we need to do town routine".

FLAWLESS_RUBY, FLAWLESS_TOPAZ, FLAWLESS_AMETHYST = 595, 580, 575  # items metadata classes


def gems() -> tuple[Carried, ...]:
    """The loop's flawless gems on (3, 1) and (4, 1), and one on (2, 3): no 1x3 is free in the visit's cells."""
    return tuple(Carried(200 + i, txt, x, y, item_size(txt), 2, True)
                 for i, (txt, x, y) in enumerate(((FLAWLESS_RUBY, 3, 1), (FLAWLESS_TOPAZ, 4, 1),
                                                  (FLAWLESS_AMETHYST, 2, 3))))  # fmt: skip


def kriss(unit: int = 7) -> Drop:
    return drop_of(unit, KRISS, RARE, size=item_size(KRISS), label='Rare Kriss', source='shown')


def rows(pack: Pack) -> tuple[str, ...]:
    return tuple(str(row) for row in pack.inventory)


def kriss_hands(*, cube: tuple[str, ...] = EMPTY_CUBE, **changes: Any) -> Hands:
    return Hands(visited(*gems(), cube=cube), own=OWN, **changes)


def test_a_field_candidate_with_no_room_gets_the_loops_gems_moved_into_the_cube(looped, lines):
    hands = kriss_hands()
    assert not hands.pack.inventory.has_room(item_size(KRISS))
    assert looped.pick(kriss(), (GAME, 7), rows(hands.pack))  # small: taken as before, now remembered for room
    assert looped.roomless == {7: (GAME, (1, 3), 'rare Kriss')}

    assert looped.due()
    assert looped.at_once(hands)

    assert hands.put_in == [200]  # the fewest, smallest first: the ruby frees column 3, rows 0-2
    assert hands.pack.inventory.has_room(item_size(KRISS))
    assert not (OWN & set(hands.put_in))
    assert "Macro: loot: field: at once: rare Kriss (unit 7): room: 1 of the loop's items into the cube" in lines
    assert not looped.at_once(hands)  # once a drop a game
    assert hands.put_in == [200]


def test_the_cube_full_too_the_room_rules_trip_is_asked_once(looped, lines):
    asked: list[str] = []
    looped.trip = lambda label: asked.append(label) is None
    hands = kriss_hands(cube=FULL_CUBE)
    assert looped.pick(kriss(), (GAME, 7), rows(hands.pack))

    assert looped.at_once(hands)

    assert asked == ['rare Kriss']
    assert hands.put_in == []
    assert 'Macro: loot: field: at once: rare Kriss (unit 7): the cube has no room for its 1x3: a trip to town for ' \
           'room' in lines  # fmt: skip
    looped.looked_at = -1e9
    assert not looped.at_once(hands)
    assert asked == ['rare Kriss']  # no trip for an item already left once in this game


def test_no_trip_possible_it_is_left_and_said(looped, lines):
    hands = kriss_hands(cube=FULL_CUBE)
    assert looped.pick(kriss(), (GAME, 7), rows(hands.pack))
    assert not looped.at_once(hands)
    assert lines[-1] == ('Macro: loot: field: at once: rare Kriss (unit 7) left: the cube can make no room for its '
                         '1x3 and no trip is made')  # fmt: skip


def test_room_is_not_made_near_a_hostile_and_is_once_quiet(looped):
    hands = kriss_hands(quiet='1 hostiles within 30')
    assert looped.pick(kriss(), (GAME, 7), rows(hands.pack))
    assert not looped.at_once(hands)
    assert hands.put_in == []
    hands.quiet = None
    assert looped.at_once(hands)
    assert hands.put_in == [200]


def test_a_candidate_picked_up_meanwhile_needs_no_room(looped):
    hands = kriss_hands()
    assert looped.pick(kriss(), (GAME, 7), rows(hands.pack))
    hands.pack = replace(hands.pack, items=(*hands.pack.items, Carried(7, KRISS, 0, 0, (1, 3), RARE, False)))
    assert not looped.at_once(hands)
    assert hands.put_in == []


def test_a_big_one_left_for_its_size_gets_room_too_then_the_squeeze_takes_it(looped):
    """14:55:53: a magic Blood Spirit (2x2) 'left: no room for its 2x2'."""
    hands = kriss_hands()
    gloves = ground(8, VAMBRACES)
    full = rows(replace(hands.pack, items=(*hands.pack.items, Carried(300, IST, 3, 3, (1, 1), 2, True))))
    assert not squeeze(looped, gloves, room=full)
    assert 8 in looped.roomless


def test_room_moves_frees_a_block_with_the_fewest_and_never_the_others():
    pack = visited(*gems())
    assert [i.unit_id for i in api.room_moves(pack, gems(), (1, 3))] == [200]
    assert api.room_moves(pack, gems()[2:], (1, 3)) == []  # the amethyst alone frees no column
    assert api.room_moves(replace(pack, cube=FULL_CUBE), gems(), (1, 3)) == []
    assert api.room_moves(replace(pack, cube=None), gems(), (1, 3)) == []


# The stash-bound items into the cube after their pickup (CUBE_AT_PICKUP; the player, 2026-10-20 ~15:02: "probably we
# should move all items that we're going to stash in town (gems/runes/statues/etc) pickup and stash in cube, to have
# space for identifying items along the way").


def test_what_is_stash_bound_is_the_resource_tabs_and_no_potion_charm_ring_or_tool():
    from inventory_tracking.loot.facts import base_of_code

    def txt(code: str) -> int:
        found = base_of_code(code)
        assert found is not None, code
        return found[0]

    for code in ('r01', 'r31', 'gzv', 'gpr', 'xa1', 'ua1', 'pk1', 'tes'):  # El, Ber? no: runes; gems; shard; statue
        assert api.stash_bound(txt(code)), code
    for code in ('rvl', 'rvs', 'cm3', 'rin', 'amu', 'jew', 'ibk', 'box', 'key', 'hp5'):
        assert not api.stash_bound(txt(code)), code


def parked(found: Field, *items: Carried) -> None:
    for item in items:
        assert found.park(drop_of(item.unit_id, item.txt, 2, size=item.size, source='material'), (GAME, 7))


def test_the_loops_gems_go_into_the_cube_in_one_batch_at_the_quiet_look_after_the_pickup(looped, lines):
    unknown_ring = Carried(250, RING, 4, 3, (1, 1), MAGIC, False)  # needs the Tome or Cain: stays
    hands = Hands(visited(*gems(), unknown_ring, cube=EMPTY_CUBE), own=OWN)
    parked(looped, gems()[0])  # the ruby just picked; the others were carried already

    assert looped.due()
    assert looped.at_once(hands)

    assert sorted(hands.put_in) == [200, 201, 202]  # one batch: every stash-bound item of the loop's
    assert not ({250, 1} | OWN) & set(hands.put_in)  # never the ring, the Tome or the player's
    assert lines == ["Macro: loot: cube: 3 of the loop's stash-bound items moved in (Flawless Ruby, Flawless Topaz, "
                     'Flawless Amethyst)']  # fmt: skip
    assert not looped.due()  # once a pickup


def test_the_cube_full_they_stay_and_it_is_said_once(looped, lines):
    hands = Hands(visited(*gems(), cube=FULL_CUBE), own=OWN)
    parked(looped, gems()[0])
    assert not looped.at_once(hands)
    assert hands.put_in == []
    assert lines == ["Macro: loot: cube: 3 of the loop's stash-bound items stay in the inventory: no room in the cube"]
    assert not looped.at_once(hands)
    assert len(lines) == 1


def test_they_wait_near_a_hostile_and_for_the_pickup(looped):
    hands = Hands(visited(*gems()[1:], cube=EMPTY_CUBE), own=OWN, quiet='1 hostiles within 30')
    parked(looped, gems()[0])  # not picked up yet: on the ground
    assert not looped.at_once(hands)
    hands.pack = visited(*gems(), cube=EMPTY_CUBE)
    assert not looped.at_once(hands)  # carried now, a hostile near
    assert hands.put_in == []
    hands.quiet = None
    assert looped.at_once(hands)
    assert sorted(hands.put_in) == [200, 201, 202]


def test_parking_is_off_with_its_switch_or_the_loop(looped, monkeypatch):
    ruby = drop_of(200, FLAWLESS_RUBY, 2, size=(1, 1), source='material')
    assert not Field().park(ruby, (GAME, 7))  # the loop off
    monkeypatch.setattr(api, 'CUBE_AT_PICKUP', False)
    assert not looped.park(ruby, (GAME, 7))
    monkeypatch.setattr(api, 'CUBE_AT_PICKUP', True)
    monkeypatch.setattr(api, 'FIELD_AT_ONCE', False)
    assert not looped.park(ruby, (GAME, 7))
    assert not looped.park(drop_of(201, RING, MAGIC, size=(1, 1)), (GAME, 7))
