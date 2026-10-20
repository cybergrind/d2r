"""The M1 shadow log (inventory_tracking/loot/shadow.py): new decisions beside the old ones, log lines only."""

import pytest

from inventory_tracking.game.records import VALUABLE, Carried, Drop, Loot, Rolls
from inventory_tracking.loot import keep
from inventory_tracking.loot.facts import Owner, from_observation
from inventory_tracking.loot.shadow import BOOK, Appraised, Book, Shadow, note
from tests.inventory_tracking.loot.test_valuables import GOBLIN, observation


GOBLIN_TOE = 342  # Light Plated Boots (items metadata)
BOOTS = 339  # Boots (lbt)
RESULT = {'triage': {'verdict': 'slow', 'band': {'q1_ist': 0.647125, 'median_ist': 1.0, 'sellers': 3,
                                                 'observed_at': '2026-10-04'}}}  # fmt: skip


class Copies:
    def __init__(self, *eds: int) -> None:
        self.owned = [from_observation(observation({**GOBLIN, 'rolls': {'16:0': ed}}, 90 + ed), owner=Owner.PLAYER)
                      for ed in eds]  # fmt: skip

    def copies(self, facts):
        return self.owned


def shadow_with_toe(ed: int = 50) -> tuple[Shadow, list[str], Carried]:
    book, said = Book(), []
    shadow = Shadow(book, lambda fmt, *args: said.append(fmt % args))
    book.put(21, Appraised(observation({**GOBLIN, 'rolls': {'16:0': ed}}, 21), RESULT, 'slow'))
    return shadow, said, Carried(21, GOBLIN_TOE, 3, 0, (2, 2), 7, True, 110)


def test_the_identify_workers_appraisals_are_noted_and_a_bad_row_is_ignored():
    note({'item': {}}, RESULT, {'unit_id': 4242, 'verdict': 'slow'})
    note({'item': {}}, RESULT, {'verdict': 'slow'})  # no unit id: nothing, no error
    note({'item': {}}, None, {'unit_id': 4243})  # no KB result: nothing

    found = BOOK.get(4242)
    assert found is not None
    assert found.verdict == 'slow'
    assert BOOK.get(4243) is None


def test_the_goblin_toe_the_visit_kept_is_a_drop_beside_it():
    shadow, said, toe = shadow_with_toe()

    lines = shadow.town([toe], junk=frozenset(), copies=Copies(53, 56))

    assert lines[0].startswith('Macro: loot: shadow: Goblin Toe (Light Plated Boots): new drop K6 cheap (0.647 Ist)')
    assert '50 vs 53, 56' in lines[0]
    assert lines[0].endswith('/ old keep slow (differ)')
    assert lines[-1] == ('Macro: loot: shadow: town: 1 items, 1 differ (new gives up 1 the old keeps, new keeps 0 '
                         'the old sells)')  # fmt: skip
    assert said == lines


def test_an_item_is_said_once_per_decision_and_the_summary_each_visit():
    shadow, said, toe = shadow_with_toe(58)

    shadow.town([toe], junk=frozenset(), copies=Copies(53, 56))
    again = shadow.town([toe], junk=frozenset(), copies=Copies(53, 56))

    assert len(again) == 1  # the summary only
    assert 'new keep K6' in said[0]
    assert '(differ)' not in said[0]


def test_the_players_items_are_never_touched_and_sold_ones_say_so():
    shadow, _, toe = shadow_with_toe()
    # An unappraised magic item the visit sells (Boots: magic gloves no want row names are junk since ~13:30, K8)
    junk = Carried(22, BOOTS, 0, 0, (2, 2), 4, True)

    lines = shadow.town([toe, junk], junk=frozenset({22}), spared=frozenset({21}), copies=Copies(53))

    assert any('new never-touch K0' in line and 'old keep slow (protected)' in line for line in lines)
    assert any(line.endswith('new keep K9 unknown: no price, the first kept (for the update-kb skill) / old sell '
                             '(differ)') for line in lines)  # fmt: skip


def test_a_failing_shadow_is_logged_once_and_never_raises():
    shadow, said, toe = shadow_with_toe()

    class Broken:
        def copies(self, facts):
            raise OSError('the collection is locked')

    assert shadow.town([toe], frozenset(), copies=Broken()) == []
    assert shadow.town([toe], frozenset(), copies=Broken()) == []
    assert said == ['Macro: loot: shadow: town failed (OSError: the collection is locked); the visit goes on']


def test_with_the_switch_off_nothing_is_said(monkeypatch):
    monkeypatch.setattr(keep, 'SHADOW', False)
    shadow, said, toe = shadow_with_toe()

    assert shadow.town([toe], frozenset(), copies=Copies(53)) == []
    assert shadow.ground(Loot(drops=()), lambda drop: True) == []
    assert said == []


def dagger(unit: int, skill: int, sockets: int = 3) -> Drop:
    return Drop(unit, 1.0, 2.0, 'Cinquedeas', VALUABLE, (1, 3), prized=False, source='shown', txt=134, quality=2,
                rolls=Rolls(sockets, ((skill, 3),)))  # fmt: skip


def test_each_ground_item_is_said_once_a_game_and_again_in_the_next():
    said: list[str] = []
    shadow = Shadow(Book(), lambda fmt, *args: said.append(fmt % args))
    apocalypse = dagger(5, 401)
    look = Loot(drops=(apocalypse, dagger(6, 402)), game=('game-1', 1))

    shadow.ground(look, lambda drop: drop.unit_id == 6)
    shadow.ground(look, lambda drop: drop.unit_id == 6)
    shadow.ground(Loot(drops=(apocalypse,), game=('game-2', 1)), lambda drop: False)

    assert said == [
        'Macro: loot: shadow: ground: normal Cinquedeas 3os: new pick G8 keep / old leave (differ)',
        'Macro: loot: shadow: ground: normal Cinquedeas 3os: new pick G8 keep / old pick',
        'Macro: loot: shadow: ground: normal Cinquedeas 3os: new pick G8 keep / old leave (differ)',
    ]


@pytest.mark.parametrize('rolls', [None, Rolls(0)])
def test_a_wanted_base_whose_rolls_are_unread_is_left_and_said_again_once_read(rolls):
    said: list[str] = []
    shadow = Shadow(Book(), lambda fmt, *args: said.append(fmt % args))
    unread = Drop(7, 1.0, 2.0, 'Monarch', VALUABLE, (2, 3), prized=False, source='shown', txt=447, quality=3)

    shadow.ground(Loot(drops=(unread,), game=('g', 1)), lambda drop: False)
    shadow.ground(Loot(drops=(Drop(**{**unread.__dict__, 'rolls': rolls}),), game=('g', 1)), lambda drop: False)

    assert said[0] == 'Macro: loot: shadow: ground: superior Monarch: new leave (its rolls are not read) / old leave'
    assert len(said) == (1 if rolls is None else 2)
