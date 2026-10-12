"""The contracts a build fills (macros/build.py): the records, the settings and the choice of a build."""

import ast
import dataclasses
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from inventory_tracking.config import with_overrides
from inventory_tracking.macros import build as contracts
from inventory_tracking.macros.build import (
    Buff,
    BuffFacts,
    Build,
    BuildSettings,
    Casting,
    Intent,
    Leg,
    Loadout,
    MoveFacts,
    NoWay,
    Tried,
    choose,
)
from inventory_tracking.macros.travel import Step
from inventory_tracking.macros.world import Player, World


SOMEONE = Player(unit_id=1, name='Someone', mode=1, area=1, x=0.0, y=0.0, consume=None)
WORLD = World(in_game=True, open_panels=(), game_name='game', slots=(7, None, 9), player=SOMEONE)
OTHER = World(in_game=True, open_panels=(), game_name='game', slots=(None,), player=SOMEONE)
FACTS = MoveFacts(here=(1.0, 2.0), now=10.0, slots=(7,), staff=None, ground=None, doors=(), aspect=1.8)
INTENT = Intent('own move', reserve=10, may_swap=False, may_wait=False, distrust=30.0)


def build(name: str, applies) -> Build:
    return Build(name=name, applies=applies, attack=None, movement=())


FALLBACK = build('fallback', lambda world: False)


def test_choose_takes_the_first_build_that_applies():
    first, second = build('first', lambda world: True), build('second', lambda world: True)

    assert choose([first, second], WORLD, FALLBACK) is first


def test_choose_respects_the_order_given():
    first, second = build('first', lambda world: True), build('second', lambda world: True)

    assert choose([second, first], WORLD, FALLBACK) is second


def test_choose_passes_over_a_build_that_does_not_apply():
    asked = []

    def by_slot(skill: int):
        def applies(world: World) -> bool:
            asked.append(skill)
            return skill in world.slots

        return applies

    builds = [build('five', by_slot(5)), build('nine', by_slot(9)), build('seven', by_slot(7))]

    assert choose(builds, WORLD, FALLBACK).name == 'nine'
    assert asked == [5, 9]  # the builds after the first that applies are not asked


def test_choose_takes_the_fallback_with_no_character_in_the_world_and_asks_no_build():
    asked = []
    eager = build('eager', lambda world: asked.append(world) is None)

    assert choose([eager], dataclasses.replace(WORLD, player=None), FALLBACK) is FALLBACK
    assert asked == []
    assert choose([eager], WORLD, FALLBACK) is eager


def test_a_loadout_names_the_weapon_sets_by_what_they_are_for_and_a_build_has_none_until_a_layer_gives_it():
    sets = Loadout(prebuff=frozenset(('aaa', 'bbb')), battle=frozenset(('ccc',)))
    assert (sets.prebuff, sets.battle) == ({'aaa', 'bbb'}, {'ccc'})
    with pytest.raises(dataclasses.FrozenInstanceError):
        sets.battle = frozenset()  # type: ignore[misc]
    plain = build('plain', lambda world: True)
    assert plain.weapons is None
    layer = dataclasses.replace(plain, weapons=sets)
    assert layer.weapons is sets
    assert plain.weapons is None  # the layer is a build of its own: the one below is as it was


def test_choose_takes_the_fallback_when_none_applies_or_none_is_given():
    never = build('never', lambda world: False)

    assert choose([never], WORLD, FALLBACK) is FALLBACK
    assert choose([], WORLD, FALLBACK) is FALLBACK
    assert choose([build('nine', lambda world: 9 in world.slots)], OTHER, FALLBACK) is FALLBACK


def test_the_fallback_is_not_asked_whether_it_applies():
    assert not FALLBACK.applies(WORLD)
    assert choose([], WORLD, FALLBACK) is FALLBACK


def test_build_settings_are_frozen():
    settings = BuildSettings()

    with pytest.raises(ValidationError):
        settings.caution = 1.0


def test_build_settings_take_no_field_they_do_not_declare():
    with pytest.raises(ValidationError):
        BuildSettings(caution=1.0)  # pyrefly: ignore[unexpected-keyword]
    with pytest.raises(ValidationError):
        with_overrides(BuildSettings(), caution=1.0)


def test_build_settings_are_changed_only_through_with_overrides():
    class Tuned(BuildSettings):
        charges: int = 15

    tuned = Tuned()
    changed = with_overrides(tuned, charges=10)

    assert (tuned.charges, changed.charges) == (15, 10)
    assert isinstance(changed, Tuned)
    with pytest.raises(ValidationError):
        tuned.charges = 10  # pyrefly: ignore[read-only]
    with pytest.raises(ValidationError):
        with_overrides(tuned, charges='ten')  # validated again, where `model_copy(update=...)` is not


def test_a_build_has_settings_of_its_own_by_default():
    assert FALLBACK.settings == BuildSettings()
    assert (FALLBACK.buffs, FALLBACK.tactics, FALLBACK.weapons, dict(FALLBACK.casters)) == ((), (), None, {})


@pytest.mark.parametrize('reason', ['', ' ', '\n\t'])
def test_no_way_without_a_reason_is_refused(reason):
    with pytest.raises(ValueError, match='says why'):
        NoWay(reason)


def test_no_way_carries_its_reason():
    assert NoWay('the staff has no charges left').reason == 'the staff has no charges left'


def test_no_way_is_blocked_unless_it_says_the_character_has_arrived():
    blocked, arrived = NoWay('a wall in the line'), NoWay('already there', arrived=True)

    assert not blocked.arrived  # a move was wanted: the caller may ask another set
    assert arrived.arrived  # none is wanted: the caller stops
    assert blocked != NoWay('a wall in the line', arrived=True)
    with pytest.raises(ValueError, match='says why'):
        NoWay(' ', arrived=True)  # an arrival says so in words too


def test_a_step_is_a_contract_record_that_travel_still_names():
    assert Step.__module__ == contracts.__name__
    assert contracts.Step is Step  # macros/travel.py re-exports the one record


def test_a_leg_is_a_step_or_no_way_and_never_none():
    assert isinstance(Step((3.0, 4.0)), Leg)
    assert isinstance(NoWay('a wall in the line'), Leg)
    assert not isinstance(None, Leg)


RECORDS = [
    FACTS,
    INTENT,
    NoWay('too far'),
    Step((3.0, 4.0)),
    FALLBACK,
    BuffFacts(WORLD, 10.0),
    Buff(skill=7, phase='upkeep', due=lambda facts: True),
]


@pytest.mark.parametrize('record', RECORDS, ids=lambda record: type(record).__name__)
def test_the_records_are_frozen(record):
    first = dataclasses.fields(record)[0].name

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(record, first, getattr(record, first))


def test_every_dataclass_of_the_module_is_frozen():
    found = [
        thing
        for thing in vars(contracts).values()
        if dataclasses.is_dataclass(thing) and isinstance(thing, type) and thing.__module__ == contracts.__name__
    ]

    assert {thing.__name__ for thing in found} == {
        'Loadout',
        'MoveFacts',
        'Intent',
        'Step',
        'NoWay',
        'JumpSource',
        'BuffFacts',
        'Buff',
        'Tried',
        'Casting',
        'Build',
    }
    assert all(thing.__dataclass_params__.frozen for thing in found)  # pyrefly: ignore[missing-attribute]


def test_an_intent_shuns_no_place_and_stops_nowhere_short_unless_told():
    assert not INTENT.shuns((5.0, 5.0))
    assert (INTENT.short, INTENT.shot, INTENT.sparing, INTENT.walks_under) == (0.0, False, 0.0, 0.0)

    wary = dataclasses.replace(INTENT, shuns=lambda spot: spot[0] > 3)

    assert wary.shuns((5.0, 5.0))
    assert not wary.shuns((1.0, 5.0))


def test_move_facts_tell_how_long_since_a_skill_was_used_or_failed():
    facts = dataclasses.replace(FACTS, last_used={7: 9.5}, failed={9: 4.0})

    assert facts.since_used(7) == 0.5
    assert facts.since_failed(9) == 6.0
    assert facts.since_used(9) == math.inf
    assert facts.since_failed(7) == math.inf


def test_buff_facts_tell_how_long_since_a_cast_by_skill_and_unit():
    facts = BuffFacts(WORLD, 10.0, cast_at={(7, None): 8.0, (9, 41): 3.0})

    assert facts.since(7) == 2.0
    assert facts.since(9, 41) == 7.0
    assert facts.since(9) == math.inf  # cast under a unit, not on none
    assert facts.since(9, 42) == math.inf


def test_a_buff_is_cast_on_the_character_with_what_is_in_hand_by_the_shared_caster_unless_told():
    buff = Buff(skill=7, phase='fight', due=lambda facts: facts.since(7) > 5)
    facts = BuffFacts(WORLD, 10.0)

    assert (buff.on, buff.target, buff.state) == ('self', None, None)
    assert (buff.needs, buff.caster, buff.also) == (None, None, ())
    assert buff.due(facts)
    assert not buff.due(dataclasses.replace(facts, cast_at={(7, None): 6.0}))
    assert buff.worth(facts, None)


def test_buff_facts_take_the_window_to_be_in_front_and_the_corpses_unreadable_unless_told():
    facts = BuffFacts(WORLD, 10.0)

    assert facts.focused()
    assert facts.corpses is None
    assert not dataclasses.replace(facts, focused=lambda: False).focused()


def test_a_caster_answers_with_what_is_remembered_and_what_was_touched():
    assert Tried() == Tried(at=None, cast=False, touched=True)  # nothing remembered: asked again at the next look
    made = Tried(10.0, cast=True)
    assert (made.at, made.cast, made.touched) == (10.0, True, True)


def test_a_try_asked_again_in_n_seconds_counts_as_a_cast_that_much_short_of_the_rows_period():
    period, wait = 10.0, 1.0
    buff = Buff(skill=7, phase='fight', due=lambda facts: facts.since(7) > period)
    tried = Tried.again(100.0, period, wait)

    assert tried == Tried(at=100.0 - period + wait, cast=False, touched=True)
    assert tried.at is not None
    remembered = {(7, None): tried.at}
    assert not buff.due(BuffFacts(WORLD, 100.0 + wait, cast_at=remembered))
    assert buff.due(BuffFacts(WORLD, 100.0 + wait + 0.01, cast_at=remembered))
    assert not Tried.again(100.0, period, wait, touched=False).touched


def test_a_casting_carries_the_row_and_leaves_the_rest_to_who_has_it():
    buff = Buff(skill=7, phase='prebuff', due=lambda facts: True)
    asked = Casting(run=None, row=buff, buffs=None)  # type: ignore[arg-type]  # pyrefly: ignore[bad-argument-type]

    assert asked.row is buff
    assert (asked.world, asked.target, asked.aspect, asked.key_names, asked.fresh) == (None, None, None, None, None)


def imported(path: Path) -> set[str]:
    """Every module the file imports, at any depth of it (a function's own import too)."""
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, 'a relative import hides what it reaches'
            module = node.module or ''
            names |= {module} | {f'{module}.{alias.name}' for alias in node.names}
    return names


def test_the_contracts_import_nothing_from_a_build():
    modules = imported(Path(contracts.__file__))

    assert any(name.startswith('inventory_tracking.') for name in modules)  # the walk did find the imports
    assert not [name for name in modules if name.split('.')[:2] == ['inventory_tracking', 'builds']]
