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

from inventory_tracking.game.records import VALUABLE, Carried, Drop, Pack
from inventory_tracking.loot import api
from inventory_tracking.loot.api import CLASSES, FIELD_IDENTIFY, MOST_TRIES, Field, droppable, reserve_short
from inventory_tracking.loot.facts import ItemFacts, Owner, Where, from_observation
from inventory_tracking.loot.keep import Action
from inventory_tracking.loot.shadow import Appraised
from inventory_tracking.loot.value import assess
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
    the big items, ~12:00: "start all three"."""
    assert FIELD_IDENTIFY
    assert api.FIELD_BIG
    assert api.FIELD_OVERSIZE
    assert frozenset(('G6', 'G9', 'G10', 'G11', 'G14', 'G15')) == CLASSES
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
    assert droppable(unique) == 'a set or unique item'
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
