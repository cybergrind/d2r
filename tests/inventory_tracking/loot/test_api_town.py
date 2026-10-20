"""M6, the town's one decision (inventory_tracking/loot/api.py `town_verdicts`, `town_kept`, `town_sold`; loot/keep.py
TOWN_DECIDES): the field's keep rules for every carried item, under the town's guards. The player, 2026-10-20 16:55:
"go ahead with the merge agent". The acceptance cases with a `town` aspect run in test_valuables.py."""

from dataclasses import replace

import pytest

from inventory_tracking.game.records import Carried
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import keep
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


def test_a_cheap_unpriced_copy_is_kept_unless_its_band_is_under_1_ist():
    # S8 / Q13: no price by its rolls -> only an equal or worse copy with a KB band under 1 Ist (as the field)
    toe = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    from inventory_tracking.loot.value import Band

    unpriced = assess(toe, worth=None, verdict='slow')
    assert not town_verdicts([(toe, unpriced)], owned(53))[0].sold
    banded = assess(toe, worth=None, verdict='slow', band=Band(0.2, 0.6, 5, '2026-10-04'))
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
def test_a_rare_amulet_the_amulet_keeper_keeps_is_kept_by_the_wants_row(rolls):
    # macros/keepers.py `amulet_keeper` (any FCR, any life, +2 all/class/tree skills) as the row rare-amulet-fcr-life-
    # skills (loot/build_wants.py G11) when TOWN_DECIDES is on
    from inventory_tracking.macros.keepers import amulet_keeper

    amulet = facts_of({'base': 'Amulet', 'code': 'amu', 'quality': 'rare', 'rolls': rolls})
    stats = {int(key.partition(':')[0]): raw for key, raw in rolls.items()}
    assert amulet_keeper(Carried(1, amulet.txt or 0, 0, 0, (1, 1), 6, True), stats) is not None
    [found] = town_verdicts([(amulet, assess(amulet, worth=0.05, verdict='vendor'))], lambda _facts: [])
    assert not found.sold, found.said()
    assert found.decision is not None
    assert found.decision.rule == 'K3'


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
