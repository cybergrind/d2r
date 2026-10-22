"""M6, the town's one decision (inventory_tracking/loot/api.py `town_verdicts`, `town_kept`, `town_sold`; loot/keep.py
TOWN_DECIDES): the field's keep rules for every carried item, under the town's guards. The player, 2026-10-20 16:55:
"go ahead with the merge agent". The acceptance cases with a `town` aspect run in test_valuables.py."""

from dataclasses import replace

import pytest

from inventory_tracking.game.records import Carried
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import api, keep
from inventory_tracking.loot.api import town_asks, town_kept, town_sold, town_verdicts
from inventory_tracking.loot.facts import Owner
from inventory_tracking.loot.keep import Action, Decision
from inventory_tracking.loot.shadow import Appraised, Book, Shadow
from inventory_tracking.loot.value import assess
from tests.inventory_tracking.loot.test_valuables import GOBLIN, facts_of, observation


DROP = Decision(Action.DROP, 'K8', 'worthless (forged for the guard)')


def class_of(code: str) -> int:
    return next(int(txt) for txt, row in metadata()['bases'].items() if row.get('code') == code)


def owned(*eds: int):
    copies = [facts_of({**GOBLIN, 'rolls': {'16:0': ed}}, 90 + ed, owner=Owner.PLAYER) for ed in eds]
    return lambda _facts: copies


@pytest.mark.parametrize(
    ('spec', 'why'),
    [
        ({'base': 'Ist Rune', 'code': 'r24', 'quality': 'normal'}, 'never sold'),
        ({'base': 'Flawless Ruby', 'code': 'glr', 'quality': 'normal'}, 'never sold'),
        ({'base': 'Western Worldstone Shard', 'code': 'xa1', 'quality': 'normal'}, 'never sold'),
        ({'base': "Wirt's Leg", 'code': 'leg', 'quality': 'normal'}, 'never sold'),
        ({'base': 'Key', 'code': 'key', 'quality': 'normal'}, 'never sold'),
        ({'base': 'Tome of Identify', 'code': 'ibk', 'quality': 'normal'}, 'never sold'),
        ({'base': 'Horadric Cube', 'code': 'box', 'quality': 'normal'}, 'never sold'),
        ({'base': 'Grand Charm', 'code': 'cm3', 'quality': 'unique', 'name': "Gheed's Fortune"}, 'never sold'),
    ],
)
def test_a_never_sold_kind_is_kept_whatever_the_decision_says(spec, why):
    facts = facts_of(spec)
    found = town_kept(facts, assess(facts, worth=0.01, verdict='vendor'), DROP, [])
    assert found is not None
    assert why in found


def test_the_players_item_and_an_unidentified_one_are_kept_whatever_the_decision_says():
    spec = {'base': 'Sash', 'code': 'lbl', 'quality': 'magic'}
    facts = facts_of(spec, owner=Owner.PLAYER)
    assert town_kept(facts, assess(facts, worth=None, verdict='vendor'), DROP, None) == "not the loop's (owner player)"
    facts = replace(facts_of(spec), identified=False)
    assert town_kept(facts, assess(facts, worth=None, verdict='vendor'), DROP, None) == 'not identified'


def test_no_appraisal_is_kept_and_a_vendor_item_is_sold():
    sash = facts_of({'base': 'Sash', 'code': 'lbl', 'quality': 'magic', 'rolls': {'7:0': 2048}})
    [unread] = town_verdicts([(sash, None)], lambda _facts: [])
    assert (unread.sold, unread.why) == (False, 'no appraisal (S8)')
    [vendor] = town_verdicts([(sash, assess(sash, worth=None, verdict='vendor'))], lambda _facts: [])
    assert vendor.sold
    assert vendor.said().startswith('sell: K8 worthless')


def test_a_cheap_copy_appraised_other_than_vendor_or_slow_is_kept_for_the_player_to_rule():
    # The coordinator, 2026-10-20 ~17:05 (Trang-Oul's Claws, `self`, 0.2 Ist, 2 owned, stashed): K6 alone sells over
    # `slow` only (M2's "Sell cheap duplicates"); `self`, `sell`, `check` are a question for the player
    toe = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    for verdict, sold in (('slow', True), ('self', False), ('sell', False), ('check', False), ('vendor', True)):
        [found] = town_verdicts([(toe, assess(toe, worth=0.65, verdict=verdict))], owned(53, 56))
        assert found.decision is not None
        assert found.decision.rule in ('K6', 'K8')
        assert found.sold == sold, (verdict, found.said())


def test_a_better_copy_is_kept_even_when_worthless_and_the_worse_one_sold():
    # The best copy first (the player, 2026-10-18); Demon Limb at 17:09:07 on 2026-10-20 (K8 before the comparison)
    better = facts_of({**GOBLIN, 'rolls': {'16:0': 58}})
    worse = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    for facts, sold in ((better, False), (worse, True)):
        [found] = town_verdicts([(facts, assess(facts, worth=0.1, verdict='vendor'))], owned(53, 56))
        assert found.sold == sold, found.said()
    [kept] = town_verdicts([(better, assess(better, worth=0.1, verdict='vendor'))], owned(53, 56))
    assert kept.decision is not None
    assert (kept.decision.action, kept.decision.rule) == (Action.KEEP, 'K6')


def test_two_copies_in_one_visit_the_best_kept_and_the_worse_sold_against_it():
    best = facts_of({**GOBLIN, 'rolls': {'16:0': 58}}, 1)
    worse = facts_of({**GOBLIN, 'rolls': {'16:0': 55}}, 2)
    items = [(worse, assess(worse, worth=0.65, verdict='slow')), (best, assess(best, worth=0.85, verdict='slow'))]
    found = {verdict.facts.unit_id: verdict.sold for verdict in town_verdicts(items, owned(53))}
    assert found == {1: False, 2: True}


def test_the_first_copy_unreadable_copies_and_an_expensive_copy_are_kept():
    toe = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    vendor = assess(toe, worth=0.1, verdict='vendor')
    assert not town_verdicts([(toe, vendor)], lambda _facts: [])[0].sold  # K4 the first copy
    assert not town_verdicts([(toe, vendor)], lambda _facts: None)[0].sold  # K4 cannot be told (S8)
    dear = assess(toe, worth=1.5, verdict='slow')
    assert not town_verdicts([(toe, dear)], owned(53, 56))[0].sold  # K5


def test_a_cheap_unpriced_copy_worse_than_an_owned_one_is_sold_whatever_its_band(monkeypatch):
    # WORSE_COPY_GOES (the player, 2026-10-21 08:27, on a 4th Bloodthief kept by its 2 Ist ask median: "Worse copy
    # goes"); off: S8 / Q13, only an equal or worse copy with a KB band under 1 Ist (as the field)
    import inventory_tracking.loot.api as api

    toe = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    from inventory_tracking.loot.value import Band

    unpriced = assess(toe, worth=None, verdict='slow')
    dear_band = assess(toe, worth=None, verdict='slow', band=Band(0.2, 2.0, 24, '2026-09-18'))
    banded = assess(toe, worth=None, verdict='slow', band=Band(0.2, 0.6, 5, '2026-10-04'))
    assert town_verdicts([(toe, unpriced)], owned(53))[0].sold
    assert town_verdicts([(toe, dear_band)], owned(53))[0].sold
    assert not town_verdicts([(toe, unpriced)], owned(48))[0].sold  # better than the owned copy: kept
    monkeypatch.setattr(api, 'WORSE_COPY_GOES', False)
    assert not town_verdicts([(toe, unpriced)], owned(53))[0].sold
    assert not town_verdicts([(toe, dear_band)], owned(53))[0].sold
    assert town_verdicts([(toe, banded)], owned(53))[0].sold


def test_a_rare_circlet_no_row_names_is_sold_by_its_dated_rule_and_a_cheap_check_charm_kept():
    # K8 by kind (keep.py JUNK_UNWANTED, the player ~12:50) sells over a `check` verdict; a priced charm under KEEP_IST
    # with `check` is no dated rule: kept (a question for the player)
    circlet = facts_of({'base': 'Tiara', 'code': 'ci2', 'quality': 'rare', 'rolls': {'0:0': 5}})
    [found] = town_verdicts([(circlet, assess(circlet, worth=0.4, verdict='check'))], lambda _facts: [])
    assert found.sold, found.said()
    charm = facts_of({'base': 'Small Charm', 'code': 'cm1', 'quality': 'magic', 'rolls': {'19:0': 12}})
    [found] = town_verdicts([(charm, assess(charm, worth=0.1, verdict='check'))], lambda _facts: [])
    assert not found.sold
    assert 'not vendor' in found.why


def test_a_small_charm_with_no_price_is_kept_by_k7():
    # S8: the 13:30:27 shadow line "magic Small Charm: new drop K7 used in multiples, worthless (no price, unknown,
    # verdict check)" -- no price read as 0 Ist
    charm = facts_of({'base': 'Small Charm', 'code': 'cm1', 'quality': 'magic', 'rolls': {'19:0': 12}})
    decision = keep.decide(charm, assess(charm, worth=None, verdict='check'), [])
    assert (decision.action, decision.rule) == (Action.KEEP, 'K7')
    assert 'no price' in decision.reason
    decision = keep.decide(charm, assess(charm, worth=None, verdict='vendor'), [])
    assert (decision.action, decision.rule) == (Action.DROP, 'K7')  # vendor with no price: worthless


@pytest.mark.parametrize(
    'rolls',
    [{'105:0': 10}, {'7:0': 40 * 256}, {'127:0': 2}, {'83:7': 2}, {'188:57': 2}, {'188:0': 2}],
)
def test_a_rare_amulet_the_amulet_keeper_keeps_is_kept_by_the_wants_row(rolls, monkeypatch):
    # macros/keepers.py `amulet_keeper` (any FCR, any life, +2 all/class/tree skills) as the row rare-amulet-fcr-life-
    # skills (loot/build_wants.py G11) when TOWN_DECIDES is on; the keep bar off (loot/wants.py KEEP_BAR)
    from inventory_tracking.loot import wants
    from inventory_tracking.macros.keepers import amulet_keeper

    monkeypatch.setattr(wants, 'KEEP_BAR', False)
    amulet = facts_of({'base': 'Amulet', 'code': 'amu', 'quality': 'rare', 'rolls': rolls})
    stats = {int(key.partition(':')[0]): raw for key, raw in rolls.items()}
    assert amulet_keeper(Carried(1, amulet.txt or 0, 0, 0, (1, 1), 6, True), stats) is not None
    [found] = town_verdicts([(amulet, assess(amulet, worth=0.05, verdict='vendor'))], lambda _facts: [])
    assert not found.sold, found.said()
    assert found.decision is not None
    assert found.decision.rule == 'K3'


@pytest.mark.parametrize(
    'rolls',
    [{'105:0': 10}, {'7:0': 40 * 256}, {'127:0': 2}, {'83:7': 2}, {'188:57': 2}, {'188:0': 2}],
)
def test_with_the_keep_bar_one_good_stat_on_a_rare_amulet_is_sold(rolls):
    # The keep bar (loot/wants.py KEEP_BAR; the player, 2026-10-21 ~08:55: "we need not just 1 row, but probably 3
    # stats with good rolls to keep"): +2 skills and three good stats, else sold; the amulet guard spares it no more
    from inventory_tracking.macros.keepers import amulet_keeper

    amulet = facts_of({'base': 'Amulet', 'code': 'amu', 'quality': 'rare', 'rolls': rolls})
    stats = {int(key.partition(':')[0]): raw for key, raw in rolls.items()}
    assert amulet_keeper(Carried(1, amulet.txt or 0, 0, 0, (1, 1), 6, True), stats) is None
    [found] = town_verdicts([(amulet, assess(amulet, worth=0.05, verdict='vendor'))], lambda _facts: [])
    assert found.sold, found.said()
    three = facts_of({'base': 'Amulet', 'code': 'amu', 'quality': 'rare',
                      'rolls': {**rolls, '83:2': 2, '105:0': 10, '7:0': 45 * 256}})  # fmt: skip
    [found] = town_verdicts([(three, assess(three, worth=0.05, verdict='vendor'))], lambda _facts: [])
    assert not found.sold, found.said()


def test_town_sold_reads_the_workers_book_and_spares_the_players():
    book = Book()
    sash = class_of('lbl')
    book.put(5, Appraised(observation({'base': 'Sash', 'code': 'lbl', 'quality': 'magic'}, 5), {}, 'vendor'))
    book.put(6, Appraised(observation({'base': 'Sash', 'code': 'lbl', 'quality': 'magic'}, 6), {}, 'vendor'))
    carried = [
        Carried(5, sash, 0, 0, (2, 1), 4, True),
        Carried(6, sash, 2, 0, (2, 1), 4, True),
        Carried(7, sash, 4, 0, (2, 1), 4, True),  # no read: kept (S8)
        Carried(8, sash, 6, 0, (2, 1), 4, False),  # unidentified: Cain's
    ]

    class Copies:
        def copies(self, facts):
            return []

    found = town_sold(carried, frozenset({6}), book, Copies())
    assert list(found) == [5]
    assert found[5][1].startswith('K8 worthless')


def test_the_appraisal_is_asked_only_for_what_may_be_sold():
    assert town_asks(Carried(1, class_of('lbl'), 0, 0, (2, 1), 4, True))
    assert not town_asks(Carried(2, class_of('lbl'), 0, 0, (2, 1), 4, False))
    for code in ('r24', 'glr', 'xa1', 'leg', 'key', 'ibk', 'box'):
        assert not town_asks(Carried(3, class_of(code), 0, 0, (1, 1), 2, True)), code


def test_the_shadow_logs_the_merged_decision_beside_the_visits_while_the_switch_is_off(monkeypatch):
    said: list[str] = []
    book = Book()
    shadow = Shadow(book, lambda fmt, *args: said.append(fmt % args))
    sash = class_of('lbl')
    book.put(5, Appraised(observation({'base': 'Sash', 'code': 'lbl', 'quality': 'magic'}, 5), {}, 'vendor'))
    book.put(6, Appraised(observation({'base': 'Sash', 'code': 'lbl', 'quality': 'magic'}, 6), {}, 'check'))
    gem = Carried(9, class_of('glr'), 6, 0, (1, 1), 2, True)
    carried = [Carried(5, sash, 0, 0, (2, 1), 4, True), Carried(6, sash, 2, 0, (2, 1), 4, True), gem]

    class Copies:
        def copies(self, facts):
            return []

    monkeypatch.setattr(keep, 'TOWN_DECIDES', False)
    lines = shadow.town(carried, junk=frozenset({6, 9}), copies=Copies(), stacked=frozenset({9}))
    merge = [line for line in lines if 'town merge:' in line]
    assert merge == [
        'Macro: loot: shadow: town merge: magic Sash: would sell: K8 worthless (no price, worthless, verdict vendor), '
        'no want / old keep (differ)',
        'Macro: loot: shadow: town merge: magic Sash: would keep: K9 unknown: no price, the first kept (for the '
        'update-kb skill) / old sell (differ)',
        'Macro: loot: shadow: town merge: 3 items, would sell 2, 2 differ (sells 1 the old keeps, keeps 1 the old '
        'sells)',
    ]
    monkeypatch.setattr(keep, 'TOWN_DECIDES', True)
    said.clear()
    assert not [line for line in shadow.town(carried, frozenset({5, 9}), copies=Copies()) if 'merge' in line]


SKULLDER = {'base': 'Russet Armor', 'code': 'xpl', 'quality': 'unique', 'name': "Skullder's Ire",
            'ranges': {'16:0': [150, 200]}}  # fmt: skip


def test_an_equal_cheap_slow_copy_an_own_use_row_names_is_sold_as_the_shadow_says():
    # Game 3 of 20261020T164916Z-454aec6d, 19:57:52 (probe.log): Skullder's Ire (Russet Armor) at (3, 0), identified at
    # Cain, `slow`, 0.842 Ist, ED 193 vs the one owned 193. The shadow said "drop K6 cheap (0.842 Ist), not better than
    # the 1 owned", the town kept it unsaid: the own-use row own-88-skullder-s-ire (an Echoing Strike MF body
    # alternative, no always_keep, no cap) made `surplus_copy` say "wanted". A want row spares one copy, not an equal
    # cheap duplicate ("we keep dublicates only for expensive items", the player, 2026-10-20)
    unit = 2945455011
    book = Book()
    book.put(unit, Appraised(observation({**SKULLDER, 'rolls': {'16:0': 193}}, unit),
                             {'triage': {'decision_ist': 0.842, 'verdict': 'slow'}}, 'slow'))  # fmt: skip
    mine = facts_of({**SKULLDER, 'rolls': {'16:0': 193}}, 9, owner=Owner.PLAYER)

    class Copies:
        def copies(self, facts):
            return [mine]

    carried = [Carried(unit, class_of('xpl'), 3, 0, (2, 3), 7, True)]
    kept: dict[int, tuple[str, str]] = {}
    found = town_sold(carried, frozenset(), book, Copies(), kept)
    assert list(found) == [unit], kept
    assert found[unit][1].startswith('K6 cheap (0.842 Ist), not better than the 1 owned')
    assert kept == {}


# The first copy no build names (keep.py FIRST_COPY_USABLE_ONLY; the player, 2026-10-20 ~20:10, after Corpsemourn
# 0.48 Ist was stashed as K4 "the first copy": "ok, let's probably keep only uniques that are mentioned in guides as
# something that I probably could use"; ~20:17: "... paladin, sorc, barb, necro, traps and amazon builds")
CORPSEMOURN = {'base': 'Ornate Armor', 'code': 'xar', 'quality': 'unique', 'name': 'Corpsemourn'}
SHELTER = {'base': 'Gothic Plate', 'code': 'gth', 'quality': 'set', 'name': "Sigon's Shelter"}


def first(spec: dict, worth: float | None, verdict: str):
    facts = facts_of(spec)
    [found] = town_verdicts([(facts, assess(facts, worth=worth, verdict=verdict))], lambda _facts: [])
    return found


def test_a_cheap_first_copy_no_build_names_is_sold_and_a_usable_one_kept():
    sold = first(CORPSEMOURN, 0.48, 'slow')
    assert sold.sold, sold.said()
    assert sold.said() == 'sell: K4 the first copy, no build names it (0.48 Ist, slow)'
    assert first(CORPSEMOURN, 0.3, 'vendor').sold
    usable = first(SKULLDER, 0.84, 'slow')  # an Echoing Strike MF body alternative (and Barbarian/Paladin/Sorc gear)
    assert not usable.sold
    assert usable.decision is not None
    assert (usable.decision.action, usable.decision.rule) == (Action.KEEP, 'K4')
    assert any(want.klass == 'usable' for want in (usable.value.wants if usable.value else ()))


@pytest.mark.parametrize(
    ('worth', 'verdict', 'why'),
    [
        (None, 'slow', 'no price (S8)'),
        (1.5, 'slow', 'expensive'),
        (0.48, 'self', 'own use'),
        (0.48, 'check', 'a question for the player'),
        (0.48, 'sell', 'a question for the player'),
    ],
)
def test_an_unpriced_expensive_or_not_vendor_or_slow_first_copy_is_kept(worth, verdict, why):
    found = first(CORPSEMOURN, worth, verdict)
    assert not found.sold, (why, found.said())


def test_the_first_copy_rule_and_its_set_switch_and_never_the_players(monkeypatch):
    assert first(SHELTER, 0.3, 'slow').sold  # a set item no build names (FIRST_COPY_SETS)
    spec = {**CORPSEMOURN, 'owner': 'player'}
    assert not first(spec, 0.48, 'slow').sold  # the player's item: never (K0)
    unread = facts_of(CORPSEMOURN)
    [told] = town_verdicts([(unread, assess(unread, worth=0.48, verdict='slow'))], lambda _facts: None)
    assert not told.sold  # copies cannot be told (S8)
    monkeypatch.setattr(keep, 'FIRST_COPY_SETS', False)
    assert not first(SHELTER, 0.3, 'slow').sold
    assert first(CORPSEMOURN, 0.48, 'slow').sold
    monkeypatch.setattr(keep, 'FIRST_COPY_USABLE_ONLY', False)
    kept = first(CORPSEMOURN, 0.48, 'slow')
    assert not kept.sold
    assert kept.why == 'K4 the first copy (0.48 Ist)'


def test_town_sold_says_the_give_ups_its_guards_keep():
    book = Book()
    book.put(5, Appraised(observation({**CORPSEMOURN, 'rolls': {'16:0': 190}}, 5), {}, 'check'))
    book.put(6, Appraised(observation({**CORPSEMOURN, 'rolls': {'16:0': 190}}, 6),
                          {'triage': {'decision_ist': 0.48}}, 'slow'))  # fmt: skip
    mine = facts_of({**CORPSEMOURN, 'rolls': {'16:0': 200}}, 9, owner=Owner.PLAYER)

    class Copies:
        def copies(self, facts):
            return [mine]

    carried = [Carried(5, class_of('xar'), 0, 0, (2, 3), 7, True), Carried(6, class_of('xar'), 2, 0, (2, 3), 7, True)]
    kept: dict[int, tuple[str, str]] = {}
    found = town_sold(carried, frozenset(), book, Copies(), kept)
    assert list(found) == [6]
    assert list(kept) == [5]  # no price, `check`: K6 gives it up, the town keeps it (S8)
    title, why = kept[5]
    assert title == 'Corpsemourn (Ornate Armor)'
    assert why.startswith('drop K6 ')
    assert 'not vendor' in why  # `check`: K6 alone sells no such item (the copy rule would let it go)


# The best copy only for a usable or dear one (keep.py BEST_COPY_USABLE_ONLY; the player, 2026-10-21 ~08:55,
# answering "What should count as usable?": "Top picks + usable best"; rca/2026-10-21/weak-keepers-findings.md B5):
# the 107% Patriarch of 04:35:32 was kept as "K6 the best copy (0.48 Ist, worthless, verdict vendor)" over a 105% one
PATRIARCH = {'base': 'Great Sword', 'code': 'gsd', 'quality': 'unique', 'name': 'The Patriarch', 'size': [2, 4],
             'ranges': {'17:0': [100, 120], '18:0': [100, 120]}}  # fmt: skip


def patriarch(ed: int, unit: int = 1, owner: Owner | None = None):
    return facts_of({**PATRIARCH, 'rolls': {'17:0': ed, '18:0': ed}}, unit, owner=owner)


@pytest.mark.parametrize(('worth', 'verdict'), [(0.48, 'vendor'), (0.78, 'slow')])
def test_a_better_copy_no_build_names_is_sold_and_a_usable_better_one_kept(worth, verdict):
    better = patriarch(107)
    mine = [patriarch(105, 9, Owner.PLAYER)]
    value = assess(better, worth=worth, verdict=verdict)
    assert not value.wants
    decision = keep.decide(better, value, mine)
    assert (decision.action, decision.rule) == (Action.DROP, 'K6'), decision.said()
    assert 'no build names it' in decision.reason
    [found] = town_verdicts([(better, value)], lambda _facts: mine)
    assert found.sold, found.said()
    toe = facts_of({**GOBLIN, 'rolls': {'16:0': 58}})  # usable (berserk-barbarian Boots, the 3rd option)
    [kept] = town_verdicts([(toe, assess(toe, worth=worth, verdict=verdict))], owned(53, 56))
    assert not kept.sold, kept.said()


@pytest.mark.parametrize(
    ('worth', 'verdict', 'why'),
    [(None, 'vendor', 'no price (S8)'), (0.48, 'self', 'own use'), (0.48, 'check', 'a question for the player'),
     (1.2, 'slow', 'dear by its own rolls: K5')],
)  # fmt: skip
def test_a_better_unusable_copy_unpriced_not_vendor_or_dear_is_kept(worth, verdict, why):
    better = patriarch(107)
    [found] = town_verdicts([(better, assess(better, worth=worth, verdict=verdict))], lambda _f: [patriarch(105, 9)])
    assert not found.sold, (why, found.said())


def test_the_best_copy_switch_off_keeps_the_better_unusable_copy(monkeypatch):
    better = patriarch(107)
    mine = [patriarch(105, 9, Owner.PLAYER)]
    monkeypatch.setattr(keep, 'BEST_COPY_USABLE_ONLY', False)
    decision = keep.decide(better, assess(better, worth=0.48, verdict='vendor'), mine)
    assert (decision.action, decision.rule) == (Action.KEEP, 'K6')
    assert decision.reason.startswith('the best copy')
    [found] = town_verdicts([(better, assess(better, worth=0.48, verdict='vendor'))], lambda _facts: mine)
    assert not found.sold


# Gheed's Fortune by its roll (keep.py GHEEDS_BY_ROLL; the player, 2026-10-21 ~09:00: "I have dropped low roll gheed's
# charms, it looks like we don't need that many of them. low rolls doesn't sell"; keep only "MF38, or MF35 + very good
# gold roll"; ~09:05: "also - do not sell our current gheed charm"). uniqueitems.json Gheed's Fortune: mag% (80) 20-40,
# gold% (79) 80-160, cheap (87) 10-15
def gheeds(mf: int, gold: int, unit: int = 1, owner: Owner | None = None):
    spec = {'base': 'Grand Charm', 'code': 'cm3', 'quality': 'unique', 'name': "Gheed's Fortune",
            'rolls': {'80:0': mf, '79:0': gold, '87:0': 12}}  # fmt: skip
    return facts_of(spec, unit, owner=owner)


@pytest.mark.parametrize(
    ('mf', 'gold', 'sold'),
    [(40, 100, False), (38, 80, False), (36, 150, False), (35, 140, False), (36, 120, True), (34, 160, True),
     (30, 160, True)],
)  # fmt: skip
def test_a_loop_found_gheeds_fortune_is_kept_only_by_a_good_roll(mf, gold, sold):
    charm = gheeds(mf, gold)
    value = assess(charm, worth=0.5, verdict='slow')
    decision = keep.decide(charm, value, [])
    assert decision.gives_up == sold, decision.said()
    assert decision.rule == 'K1'
    [found] = town_verdicts([(charm, value)], lambda _facts: [])
    assert found.sold == sold, found.said()
    if sold:
        assert "Gheed's Fortune" in found.said()
        assert api.droppable(charm, value, []) is not None  # never put down in the field: sold in town


def test_a_low_gheeds_with_no_roll_read_unidentified_or_the_players_is_kept():
    unread = replace(gheeds(30, 100), rolls=None)
    assert not town_verdicts([(unread, assess(unread, worth=0.5, verdict='slow'))], lambda _facts: [])[0].sold
    hidden = replace(gheeds(30, 100), identified=False, name=None)
    assert not town_verdicts([(hidden, assess(hidden, worth=None))], lambda _facts: [])[0].sold
    mine = gheeds(30, 100, owner=Owner.PLAYER)  # "do not sell our current gheed charm"
    decision = keep.decide(mine, assess(mine, worth=0.5, verdict='vendor'), [])
    assert decision.action == Action.NEVER_TOUCH
    assert not town_verdicts([(mine, assess(mine, worth=0.5, verdict='vendor'))], lambda _facts: [])[0].sold


def test_the_carried_gheeds_is_never_sold_and_a_low_loop_find_beside_it_is():
    # The town visit's `town_sold` with the character's own Gheed's Fortune spared (the player's, K0) and a low loop
    # find carried beside it (the swap's new one before the choice, or one found outside the swap): only the find goes
    book = Book()
    for unit, mf in ((5, 30), (6, 30)):
        spec = {'base': 'Grand Charm', 'code': 'cm3', 'quality': 'unique', 'name': "Gheed's Fortune",
                'rolls': {'80:0': mf, '79:0': 100}}  # fmt: skip
        book.put(unit, Appraised(observation(spec, unit), {'triage': {'decision_ist': 0.5}}, 'slow'))
    grand = class_of('cm3')
    carried = [Carried(5, grand, 0, 0, (1, 3), 7, True), Carried(6, grand, 1, 0, (1, 3), 7, True)]

    class Copies:
        def copies(self, facts):
            return []

    found = town_sold(carried, frozenset({5}), book, Copies())
    assert list(found) == [6]


@pytest.mark.parametrize(
    'spec',
    [{'base': 'Small Charm', 'code': 'cm1', 'quality': 'unique', 'name': 'Annihilus', 'rolls': {'127:0': 1}},
     {'base': 'Large Charm', 'code': 'cm2', 'quality': 'unique', 'name': 'Hellfire Torch', 'rolls': {'0:0': 10}}],
)  # fmt: skip
def test_other_unique_charms_stay_never_sold(spec):
    charm = facts_of(spec)
    [found] = town_verdicts([(charm, assess(charm, worth=0.01, verdict='vendor'))], lambda _facts: [])
    assert not found.sold
    assert found.decision is not None
    assert (found.decision.action, found.decision.rule) == (Action.KEEP, 'K1')


def test_the_gheeds_switch_off_keeps_every_gheeds(monkeypatch):
    monkeypatch.setattr(keep, 'GHEEDS_BY_ROLL', False)
    charm = gheeds(30, 100)
    [found] = town_verdicts([(charm, assess(charm, worth=0.5, verdict='vendor'))], lambda _facts: [])
    assert not found.sold
    assert found.decision is not None
    assert found.decision.reason.startswith('never sold')
