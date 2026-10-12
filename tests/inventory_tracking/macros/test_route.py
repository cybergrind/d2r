"""The teleport key on a level that has a route stage (levels/routes.md, T7 and T8 for chains of doors).

The levels are made up: a corridor east of the character with the stage's door at its far end and
the way back marked first, as a card without a route would lead with it.
"""

from dataclasses import replace
from itertools import pairwise

import pytest

from inventory_tracking.levels.guide import lead_first
from inventory_tracking.levels.model import SEALS, SUPER_CHEST, Lead, Poi, Room, Target
from inventory_tracking.macros import route
from inventory_tracking.macros.teleport import step_toward
from inventory_tracking.macros.world import Teleport, Thing
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.model import Route, enter, fight, leave, level, loot, stand, use
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.macros.fakes import KEYS, Game, player, world


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))
ROOMS = (HERE, *EAST)
DOOR = (1030.5, 1000.5)  # two hops and a walk from the character
PRESSES = 8  # more than a level of this size takes

CAVE = Route(
    'Cave',
    (3,),
    (level(3, enter('Cave', 9)), level(9, fight('Coldcrow', 'Coldcrow'), loot(), enter('Next level', 13))),
)


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def mark(label, area=3, kind='stairs'):
    return Target(area, ROOMS, DOOR, label, kind, True)


def game(area=3):
    play = Game(world(player=player(area)))
    play.staff = Teleport(40, 40, True)
    return play


def test_a_stage_whose_mark_leads_the_card_is_followed_and_logged(caplog):
    play = game()
    with caplog.at_level('INFO'):
        found = route.card(play.run(), lambda: mark('Cave'), Progress([CAVE]))

    assert found.label == 'Cave'
    assert any('route Cave: enter Cave' in record.message for record in caplog.records)
    assert play.said == []


def test_a_stage_whose_mark_is_not_on_the_card_yet_says_so_and_the_step_follows_the_card():
    play = game()

    found = route.card(play.run(), lambda: mark('Stony Field'), Progress([CAVE]))

    assert found.label == 'Stony Field'
    assert play.said == ['Cave: Cave is not marked yet; toward Stony Field']


def test_a_stage_that_is_not_performed_yet_leaves_the_card_as_it_is(caplog):
    play = game(9)
    with caplog.at_level('INFO'):
        found = route.card(play.run(), lambda: mark('Next level', 9), Progress([CAVE]))

    assert found.label == 'Next level'
    assert play.said == []
    assert not any('route' in record.message for record in caplog.records)


@pytest.mark.parametrize('progress', [None, Progress([])])
def test_without_a_route_the_card_is_the_cards(progress):
    play = game()
    assert route.card(play.run(), lambda: mark('Stony Field'), progress).label == 'Stony Field'
    assert route.card(play.run(), None, progress) is None
    assert play.said == []


def test_a_card_for_another_level_is_left_to_the_step_to_refuse():
    play = game()
    found = route.card(play.run(), lambda: mark('Next level', 9), Progress([CAVE]), seconds=0.0)
    assert found.area == 9
    assert play.said == []


class Levels:
    """A game of made-up levels: each one's card holds the way back and the door of its stage."""

    def __init__(self, start: int, progress: Progress) -> None:
        self.play, self.progress = game(start), progress
        self.passed = [start]
        self.arrive()

    @property
    def area(self) -> int:
        return self.play.world.player.area

    def arrive(self) -> None:
        """In a new level: the character at its entrance, the service's note of the level made."""
        here = self.play.world.player
        self.play.world = replace(self.play.world, player=replace(here, x=5000.0, y=5000.0))
        self.progress.note(self.play.world.game_name, self.area)
        step = self.progress.step(self.area)
        self.play.door = DOOR
        self.play.staff = Teleport(40, 40, True)  # the chain is about the doors, not the charges
        self.play.next_area = step.stage.to if step is not None else 0

    def card(self) -> Target | None:
        area, step = self.area, self.progress.step(self.area)
        pois = [Poi('Back', HERE, 'previous', (997.5, 1000.5))]
        if step is not None and step.stage.mark:
            pois.append(Poi(step.stage.mark, EAST[-1], 'previous' if step.stage.to < area else 'stairs', DOOR))
        first = lead_first(tuple(pois), self.progress.lead(area))[0]
        return Target(area, ROOMS, first.spot, first.label, first.kind, True)

    def press(self) -> None:
        run = self.play.run()
        step_toward(run, route.card(run, self.card, self.progress), keys)
        if self.area != self.passed[-1]:
            self.passed.append(self.area)
            self.arrive()

    def follow(self) -> list[int]:
        """The key pressed until no door leads on: the levels passed."""
        while (lead := self.progress.lead(self.area)) is not None and lead.area:
            before = len(self.passed)
            for _ in range(PRESSES):
                self.press()
                if len(self.passed) > before:
                    break
            else:
                raise AssertionError(f'{PRESSES} presses in level {self.area} and no way on taken')
        return self.passed


@pytest.mark.parametrize(
    ('start', 'expected'),
    [
        (6, [6, 20, 21, 22, 23, 24, 25]),  # Black Marsh to the Countess's cellar
        (3, [3, 9]),  # Cold Plains into the Cave: Coldcrow is a fight, and the card's own order goes on from there
        (27, [27, 26, 7, 12, 16]),  # Outer Cloister, Monastery Gate, Tamoe Highland, Pit 1 and 2
        (5, [5, 10, 14]),  # Dark Wood, the Underground Passage
        (115, [115, 116]),  # Glacial Trail, Drifter Cavern
        (113, [113, 114]),  # Crystalline Passage, Frozen River
        (118, [118, 119]),  # the Ancients' Way, Icy Cellar
    ],
)
def test_the_key_pressed_from_a_routes_start_passes_its_doors_to_the_last_level(start, expected):
    assert Levels(start, Progress(ROUTES)).follow() == expected


def starts():
    progress = Progress(ROUTES)
    return [area for area in sorted(progress.scripts) if progress.lead(area) is not None]


@pytest.mark.parametrize('start', starts())
def test_from_every_level_with_a_door_to_take_the_key_reaches_a_level_without_one(start):
    progress = Progress(ROUTES)

    passed = Levels(start, progress).follow()

    assert len(passed) == len(set(passed)) > 1
    assert progress.lead(passed[-1]) is None
    for area, after in pairwise(passed):
        assert progress.scripts[area][1].way_on.to == after


def test_a_door_taken_is_not_led_with_again_in_this_game_and_is_in_the_next():
    progress = Progress([CAVE])
    levels = Levels(3, progress)
    assert levels.follow() == [3, 9]

    assert progress.lead(3) is None
    progress.note('another', 3)
    assert progress.lead(3) is not None


# --- `use`: the objects of a level (Phase 4) ---

CHESTS = Route('Pit', (111,), (level(125, use('Super chest'), loot(), leave()),))
SANCTUARY = Route(
    'Diablo',
    (107,),
    (
        level(
            108,
            use('Vizier seal 1'),
            use('Vizier seal 2'),
            fight('Grand Vizier of Chaos'),
            use('De Seis seal'),
            fight('Diablo'),
            loot(),
            leave(),
        ),
    ),
)


class Objects:
    """One made-up level with objects to click: the card leads with its handler's own mark, then the
    objects in `places`, as the Chaos Sanctuary's card leads with the star."""

    def __init__(self, area: int, progress: Progress, places: list[tuple[str, int, tuple[float, float]]]) -> None:
        self.play, self.progress, self.area = game(area), progress, area
        self.pois = (
            Poi('Own', HERE, 'target', (997.5, 1000.5)),
            *(Poi(label, EAST[0], 'target', spot, use=kind) for label, kind, spot in places),
        )
        self.things = {
            spot: Thing(70 + n, kind, 0, spot[0] * 5, spot[1] * 5) for n, (_label, kind, spot) in enumerate(places)
        }
        self.clicked: list[str] = []
        progress.note(self.play.world.game_name, area)

    def card(self) -> Target:
        first = lead_first(self.pois, self.progress.lead(self.area))[0]
        return Target(self.area, ROOMS, first.spot, first.label, first.kind, use=first.use)

    def marks(self, label: str) -> tuple[tuple[float, float], ...]:
        return tuple(poi.spot for poi in self.pois if poi.label == label)

    def press(self) -> Target:
        """One press; the game shows the object at the mark gone for, as it shows what is near."""
        target = self.card()
        self.play.thing, self.play.thing_above = self.things.get(target.point), 10
        run = self.play.run()
        found = route.card(run, self.card, self.progress)
        step_toward(run, found, keys)
        route.note_used(run, found, self.progress, self.marks)
        if self.play.thing is not None and self.play.thing.mode and not self.things[target.point].mode:
            self.clicked.append(target.label)
        if self.play.thing is not None:
            self.things[target.point] = self.play.thing
        return target

    def follow(self) -> list[str]:
        """The key pressed until the card leads with its own mark again: what was clicked, in order."""
        for _ in range(4 * PRESSES):
            if self.progress.lead(self.area) is None:
                return self.clicked
            self.press()
        raise AssertionError(f'the objects of level {self.area} were not done: {self.clicked}')


def test_a_chest_is_gone_to_opened_and_then_the_card_is_the_levels_own_again():
    level_ = Objects(125, Progress([CHESTS], route.PERFORMED), [('Super chest', SUPER_CHEST, (1006.0, 1000.5))])

    assert level_.follow() == ['Super chest']
    assert level_.card().label == 'Own'
    assert 'Super chest: opened' in level_.play.said


def test_every_chest_with_the_label_is_opened_once():
    spots = [(1006.0, 1000.5), (1020.0, 1000.5), (1034.0, 1000.5)]
    level_ = Objects(125, Progress([CHESTS], route.PERFORMED), [('Super chest', SUPER_CHEST, spot) for spot in spots])

    assert level_.follow() == ['Super chest'] * 3
    assert all(thing.mode for thing in level_.things.values())


def test_the_seals_are_opened_in_the_scripts_order_and_then_the_star_leads():
    places = [  # as the handler lists them: not the order they are opened in
        ('De Seis seal', SEALS[2], (1020.0, 1000.5)),
        ('Vizier seal 2', SEALS[3], (1034.0, 1000.5)),
        ('Vizier seal 1', SEALS[4], (1006.0, 1000.5)),
    ]
    level_ = Objects(108, Progress([SANCTUARY], route.PERFORMED), places)

    assert level_.follow() == ['Vizier seal 1', 'Vizier seal 2', 'De Seis seal']
    assert level_.card().label == 'Own'


def test_an_object_found_operated_is_noted_without_a_click():
    level_ = Objects(125, Progress([CHESTS], route.PERFORMED), [('Super chest', SUPER_CHEST, (1001.0, 1000.5))])
    spot = (1001.0, 1000.5)
    level_.things[spot] = Thing(70, SUPER_CHEST, 2, 5005.0, 5002.5)  # opened by the pickup key before

    level_.press()

    assert level_.play.keys.events == []
    assert level_.progress.lead(125) is None


def test_a_use_is_not_noted_for_a_mark_that_is_not_the_stages_or_an_object_not_operated():
    progress = Progress([CHESTS], route.PERFORMED)
    play = game(125)
    play.thing = Thing(70, SUPER_CHEST, 0, 5010.0, 5002.0)
    chest = Target(125, ROOMS, (1002.0, 1000.4), 'Super chest', 'target', use=SUPER_CHEST)

    route.note_used(play.run(), chest, progress, None)  # still closed
    route.note_used(play.run(), mark('Next level', 125), progress, None)  # a door
    route.note_used(play.run(), None, progress, None)
    assert progress.lead(125) is not None

    play.thing = Thing(70, SUPER_CHEST, 2, 5010.0, 5002.0)
    route.note_used(play.run(), chest, progress, None)
    assert progress.lead(125) is None


def test_the_catalogues_chest_levels_and_the_sanctuary_lead_with_their_objects():
    progress = Progress(ROUTES, route.PERFORMED)
    assert {area: progress.lead(area).label for area in (13, 16, 116, 119, 125)} == dict.fromkeys(
        (13, 16, 116, 119, 125), 'Super chest'
    )
    assert progress.lead(108).label == 'Vizier seal 1'
    assert progress.lead(102) == Lead('Red portal')  # the stand by it, not the way out: no level behind the lead
    assert progress.lead(79) is None  # Lower Kurast's chests are pending


# --- `stand`, `fight`, `loot`, `leave`: one press of the key through `route.press` (Phase 5) ---

COUNTESS = Route('Countess', (6,), (level(25, fight('The Countess', 'Countess'), loot(), leave()),))
MEPHISTO = Route(
    'Mephisto',
    (101,),
    (level(102, stand('Red portal'), fight('Mephisto'), loot(), use('Red portal', 103), leave()),),
)
THERE = (1002.0, 1000.4)  # a mark two tiles from the character


class Pressed:
    """One made-up level and what the runner gives a press: the plain step, attack mode, the way out."""

    def __init__(self, routes, area, first, *, dead=None):
        self.dead: set[str] = set() if dead is None else dead
        self.progress = Progress(routes, route.PERFORMED, dead=lambda: frozenset(self.dead))
        self.play, self.area = game(area), area
        self.first = first  # (label, kind, place) of the card's own first mark
        self.drops = 0  # valuables on the ground: a pickup takes one
        self.did: list[str] = []
        self.progress.note(self.play.world.game_name, area)

    def card(self):
        label, kind, spot = self.first
        own = Poi(label, HERE, kind, spot)
        lead = self.progress.lead(self.area)
        marks = (own, *((Poi(lead.label, EAST[0], 'target', THERE),) if lead and lead.label != label else ()))
        found = lead_first(marks, lead)[0]
        return Target(self.area, ROOMS, found.spot, found.label, found.kind)

    def pick(self, run, level_, key_names, otherwise):
        if not self.drops:
            otherwise()
            return False
        self.drops -= 1
        self.did.append('pick')
        return True

    def press(self, monkeypatch):
        monkeypatch.setattr(route, 'pick_up', self.pick)
        route.press(
            self.play.run(),
            self.progress,
            self.card,
            None,
            keys,
            plain=lambda target: self.did.append(f'step {target.label}'),
            level=lambda: None,
            attack=lambda: self.did.append('attack'),
            leave=lambda run, key_names: self.did.append('leave'),
        )
        return self.did


def test_at_a_fights_mark_the_press_steps_there_and_turns_attack_mode_on(monkeypatch):
    here = Pressed([COUNTESS], 25, ('Countess', 'target', THERE))
    assert here.press(monkeypatch) == ['step Countess', 'attack']


def test_far_from_a_fights_mark_the_press_is_only_the_step(monkeypatch):
    here = Pressed([COUNTESS], 25, ('Countess', 'target', DOOR))
    assert here.press(monkeypatch) == ['step Countess']


def test_the_countess_dead_the_presses_pick_up_then_say_and_only_then_leave(monkeypatch):
    here = Pressed([COUNTESS], 25, ('Countess', 'target', THERE), dead={'The Countess'})
    here.drops = 2

    assert here.press(monkeypatch) == ['pick']
    assert here.press(monkeypatch) == ['pick', 'pick']
    assert here.press(monkeypatch) == ['pick', 'pick']  # nothing left: said, the game not left by this press
    assert here.play.said[-1] == 'Countess: nothing to pick up; the next press leaves the game'
    assert here.press(monkeypatch) == ['pick', 'pick', 'leave']


def test_a_drop_that_fell_after_the_ground_was_clean_is_picked_up_before_leaving(monkeypatch):
    here = Pressed([COUNTESS], 25, ('Countess', 'target', THERE), dead={'The Countess'})
    here.press(monkeypatch)  # nothing: the loot is done
    here.drops = 1

    assert here.press(monkeypatch) == ['pick']
    assert here.press(monkeypatch) == ['pick', 'leave']


def test_mephisto_stand_by_the_portal_fight_pick_up_and_then_the_portal_leads(monkeypatch):
    here = Pressed([MEPHISTO], 102, ('Mephisto', 'target', DOOR))

    assert here.press(monkeypatch) == ['step Red portal']  # two tiles from it: stood there
    assert here.play.said[-1] == 'Mephisto: at Red portal'
    assert here.progress.step(102).stage.kind == 'fight'

    here.did.clear()
    assert here.press(monkeypatch) == ['attack']  # the fight names no mark: from where the character stands
    here.dead.add('Mephisto')
    here.did.clear()
    assert here.press(monkeypatch) == ['step Red portal']  # nothing to pick up: on to the portal in this press
    assert here.progress.lead(102).area == 103


def test_a_level_without_a_stage_is_the_plain_step(monkeypatch):
    here = Pressed([], 25, ('Countess', 'target', THERE))
    assert here.press(monkeypatch) == ['step Countess']


def test_the_countess_run_from_black_marsh_to_the_next_game(monkeypatch):
    """T8: the doors by the made-up levels, then the cellar's stages by presses."""
    dead: set[str] = set()
    progress = Progress(ROUTES, route.PERFORMED, dead=lambda: frozenset(dead))
    assert Levels(6, progress).follow() == [6, 20, 21, 22, 23, 24, 25]

    cellar = Pressed([], 25, ('Tower Cellar 4', 'previous', DOOR), dead=dead)
    cellar.progress = progress
    assert cellar.press(monkeypatch) == ['step Countess', 'attack']
    dead.add('The Countess')
    cellar.drops = 1
    for _ in range(3):
        cellar.press(monkeypatch)
    assert cellar.did == ['step Countess', 'attack', 'pick', 'leave']


def test_leaving_makes_the_next_game_and_casts_the_buffs_wherever_the_character_stands():
    play = Game(world(112))  # Arreat Plateau: the macro request alone only prebuffs here
    route.leave(play.run(), lambda w: dict(KEYS))
    pressed = play.pressed()
    assert pressed[0] == 'Escape'
    assert pressed[1 : pressed.index('Return')] == ['End', 'BackSpace', '3']
    assert pressed[pressed.index('Return') + 1 :] == ['q', '6', 'q', 'g', 'r']
    assert play.world.game_name == 'cyber33'
    assert play.said[-1] == 'Prebuff done'


# --- a border: no door to click, the character walks over the edge (Phase 6) ---

OUTER = Route('Pit', (27,), (level(27, enter('Monastery Gate', 26)), level(26, enter('Tamoe Highland', 7))))
EDGE = replace(EAST[-1], leads_to=(26,))  # the level's easternmost room: the Monastery Gate lies east of it
EDGE_MARK = (EDGE.x + EDGE.width / 2, EDGE.y + EDGE.height / 2)


def border_press(play, progress, did):
    route.press(
        play.run(),
        progress,
        lambda: Target(27, (HERE, *EAST[:-1], EDGE), EDGE_MARK, 'Monastery Gate', 'stairs'),
        None,
        keys,
        plain=lambda target: did.append('step'),
        level=lambda: None,
        attack=lambda: did.append('attack'),
        leave=lambda run, key_names: did.append('leave'),
    )


def at_the_edge():
    play = game(27)
    play.world = replace(play.world, player=replace(play.world.player, x=EDGE_MARK[0] * 5, y=EDGE_MARK[1] * 5))
    return play


def test_beside_a_border_mark_the_press_walks_on_toward_the_level_behind_it():
    play, did = at_the_edge(), []
    progress = Progress([OUTER], route.PERFORMED)

    border_press(play, progress, did)

    assert did == []  # no hop: the character is at the mark already
    assert len(play.walks) == route.CROSS_CLICKS
    xs = [x for x, _y in play.walks]
    assert xs == sorted(xs)  # east, each click further
    assert xs[0] > EDGE_MARK[0] * 5 + 5
    assert all(abs(y - EDGE_MARK[1] * 5) < 3 for _x, y in play.walks)
    assert play.said[0] == 'Pit: walking across to Monastery Gate'


def test_the_walk_ends_when_the_level_changes():
    play, did = at_the_edge(), []
    react = play.react

    def crossing(event):
        react(event)
        here = play.world.player
        if here.x > (EDGE.x + EDGE.width) * 5:  # over the edge: the game puts the character on the next level
            play.world = replace(play.world, player=replace(here, area=26))

    play.keys.on_event = crossing
    border_press(play, Progress([OUTER], route.PERFORMED), did)

    assert play.world.player.area == 26
    assert len(play.walks) < route.CROSS_CLICKS + 1
    assert play.said[-1] == 'Monastery Gate: there'


def test_far_from_the_border_the_press_is_the_step_toward_its_mark():
    play, did = game(27), []
    border_press(play, Progress([OUTER], route.PERFORMED), did)
    assert did == ['step']
    assert play.walks == []


def test_a_door_is_not_walked_past_as_a_border_is():
    play, did = at_the_edge(), []
    doors = Route('Cave', (27,), (level(27, enter('Monastery Gate', 28)),))  # joined by a door, not an edge
    border_press(play, Progress([doors], route.PERFORMED), did)
    assert did == ['step']
    assert play.walks == []


def test_a_room_that_holds_a_door_is_not_walked_past():
    play, did = at_the_edge(), []
    stairs = replace(EDGE, preset=144)  # 'Act 1 - Crypt Next E': the Tower Cellar's stairs
    route.press(
        play.run(),
        Progress([OUTER], route.PERFORMED),
        lambda: Target(27, (HERE, *EAST[:-1], stairs), EDGE_MARK, 'Monastery Gate', 'stairs'),
        None,
        keys,
        plain=lambda target: did.append('step'),
        level=lambda: None,
        attack=lambda: None,
        leave=lambda run, key_names: None,
    )
    assert did == ['step']
    assert play.walks == []
