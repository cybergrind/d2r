"""The one designation of Death Mark (builds/warlock/mark.py DESIGNATED_MARK, 2026-10-22). The player, ~19:58: "we
must read mobs immunities and must correctly use our minions to handle immune mobs"; ~20:10: "we know who must be death
marked / we apply DM when designated mob doesn't have it / we clear DM when we're teleporting with mobs / we re-apply
DM because we have designated mob active"; "if designated minion has died -> DM disappears from it".

The fight: Tal Rasha's Tomb, 19:53:51-19:54:01 (take 20261022T165350Z-69): two elite 103s, physical 33, magic 100,
fire 20, lightning 20, cold 100, poison 50 (their stat lists), the bound Urdar and the Defiler by the first one; the
character Teleported 19.8 onto it at 19:53:52 (rca/2026-10-22/immune-mark-findings.md). Places are the take's, moved
so the character stands at the fakes' (5000, 5000)."""

import ast
import logging
from dataclasses import replace
from pathlib import Path

from inventory_tracking.builds.warlock import mark
from inventory_tracking.builds.warlock.echoing_strike.attack import ECHOING_STRIKE_ATTACK
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import pack
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.build import BuffFacts
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, world


NOW = 100.0
TOMB = 69
NOBODY = 0xFFFFFFFF
UNIQUE, MINION = 0x08, 0x10
RESISTS = ((36, 33), (37, 100), (39, 20), (41, 20), (43, 100), (45, 50))
ORIGIN = (22612.5, 9641.5)  # the character at 19:53:52.5


def at(x: float, y: float) -> tuple[float, float]:
    return 5000.0 + x - ORIGIN[0], 5000.0 + y - ORIGIN[1]


def foe(unit: int, txt: int, place: tuple[float, float], flags: int = UNIQUE, **changes) -> Monster:
    return replace(Monster(unit, txt, 1, *place, NOBODY, flags, life=128, max_life=128), **changes)


def demon(unit: int, txt: int, place: tuple[float, float]) -> Monster:
    return Monster(unit, txt, 1, *place, NOBODY, 0, ally=True, life=128, max_life=128)


FIRST = foe(1932335040, 103, at(22606.5, 9628.5), resists=RESISTS)  # 14.3 off
SECOND = foe(2431003951, 103, at(22625.5, 9619.5), resists=RESISTS)  # 25.6 off
ON_FIRST = (demon(3406472726, 189, at(22608.1, 9628.9)), demon(1245494591, 744, at(22607.1, 9627.9)))
ALONG = (demon(3406472726, 189, (5001.0, 5000.5)), demon(1245494591, 744, (5000.5, 4999.0)))  # by the character


def facts(*foes: Monster, demons=ON_FIRST, cast_at=None, missed=None, now: float = NOW) -> BuffFacts:
    seen = world(TOMB, slots=HUNT_SLOTS, monsters=(*foes, *demons))
    return BuffFacts(seen, now, tuple(foes), tuple(foes), cast_at=cast_at or {}, missed=missed or {})


def keyed(unit: int, when: float) -> dict[tuple[int, int | None], float]:
    return {(DEATH_MARK, None): when, (DEATH_MARK, unit): when}


def test_the_immune_one_is_designated_and_marked_and_held_while_its_mark_lasts(caplog) -> None:
    caplog.set_level(logging.INFO)
    asked = facts(FIRST, SECOND)
    assert mark.target(asked) is FIRST  # the nearer of the two immune to the magic
    assert mark.DESIGNATION.unit == FIRST.unit_id
    assert 'designated the elite 103 (1932335040), 128/128: immune to magic, cold' in caplog.text
    assert mark.worth_a_mark(asked, FIRST)  # the demons stand by it: an immune one is marked all the same
    assert mark.mark_ahead(asked)  # before the bout's first strike
    held = facts(FIRST, SECOND, cast_at=keyed(FIRST.unit_id, NOW - 1.0))
    assert mark.target(held) is None  # its mark lasts and the demons are on it: no other immune one meanwhile
    assert not mark.mark_ahead(held)


def test_a_teleport_with_the_demons_along_clears_the_aggro_and_the_mark_goes_again_at_the_landing(caplog) -> None:
    caplog.set_level(logging.INFO)
    lasting = keyed(FIRST.unit_id, NOW - 1.0)
    pack.hopped(NOW - 0.3, 19.8)  # the Teleport of 19:53:52 onto it
    landed = facts(FIRST, SECOND, demons=ALONG, cast_at=lasting)
    assert mark.target(landed) is FIRST  # 11 s of its mark left by the clock, but the demons came along
    assert mark.worth_a_mark(landed, FIRST)
    assert mark.mark_ahead(landed)
    assert 'the jump of 19.8 units 0.30s ago took the demons off the elite 103 (1932335040)' in caplog.text
    again = facts(FIRST, SECOND, demons=ALONG, cast_at=keyed(FIRST.unit_id, NOW - 0.1), now=NOW + 0.9)
    assert mark.target(again) is None  # marked again at the landing: once
    stayed = facts(FIRST, SECOND, demons=ON_FIRST, cast_at=lasting)
    assert mark.target(stayed) is None  # the demons did not come along: they hold it still


def test_the_designated_one_dead_the_next_is_designated_and_marked_at_once(caplog) -> None:
    caplog.set_level(logging.INFO)
    assert mark.target(facts(FIRST, SECOND, cast_at=keyed(FIRST.unit_id, NOW - 3.7))) is None  # held
    # 19:53:56.2: the first is gone from the hostiles (dead); its mark went with it: no 12 s wait
    dead = facts(SECOND, cast_at=keyed(FIRST.unit_id, NOW - 3.7), now=NOW + 0.1)
    assert mark.target(dead) is SECOND
    assert mark.worth_a_mark(dead, SECOND)
    assert mark.DESIGNATION.unit == SECOND.unit_id
    assert 'designated the elite 103 (2431003951)' in caplog.text


def test_keys_that_took_nowhere_take_the_designation_off_it() -> None:
    failed = facts(FIRST, SECOND, missed={(DEATH_MARK, FIRST.unit_id): mark.MARK_RECASTS})
    assert mark.target(failed) is SECOND


def test_the_reasons_rank_a_herald_an_immune_one_the_held_leader_then_a_leader() -> None:
    herald = foe(8, 103, (5020.0, 5000.0), tier=3)
    leader = foe(5, 310, (5008.0, 5000.0))
    other = foe(6, 310, (5009.0, 5001.0))
    away = (demon(70, 744, (4980.0, 5000.0)), demon(71, 189, (4981.0, 5000.0)))
    assert mark.target(facts(herald, FIRST, leader, demons=away)) is herald
    assert mark.target(facts(FIRST, leader, demons=away)) is FIRST
    ECHOING_STRIKE_ATTACK.held.unit = other.unit_id
    assert mark.target(facts(leader, other, demons=away)) is other  # the leader the strike holds, not the nearer
    assert mark.DESIGNATION.reason == 'the leader the strike holds'
    # The marked one is kept while it keeps its reason: the held leader's mark lasts, a Herald alone takes over
    lasting = keyed(other.unit_id, NOW - 2.0)
    assert mark.target(facts(leader, other, FIRST, demons=away, cast_at=lasting)) is FIRST  # an immune one comes
    assert mark.target(facts(herald, leader, other, demons=away, cast_at=lasting)) is herald


def test_without_the_model_the_mark_is_as_before(monkeypatch) -> None:
    monkeypatch.setattr(mark, 'DESIGNATED_MARK', False)
    pack.hopped(NOW - 0.3, 19.8)
    assert mark.target(facts(FIRST, SECOND)) is FIRST  # `unmarked_immune`
    assert mark.target(facts(FIRST, SECOND, demons=ALONG, cast_at=keyed(FIRST.unit_id, NOW - 1.0))) is None


def test_only_the_model_names_whom_death_mark_goes_on() -> None:
    """Architecture: one Buff row casts Death Mark, its target `mark.target`; no other code keys the skill."""
    root = Path(__file__).resolve().parents[4] / 'inventory_tracking'
    rows, keys = [], []
    for path in root.rglob('*.py'):
        if 'runs' in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            first = node.args[0]
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
            if name == 'Buff' and isinstance(first, ast.Name) and first.id == 'DEATH_MARK':
                target = next((k.value for k in node.keywords if k.arg == 'target'), None)
                rows.append((path.name, target.id if isinstance(target, ast.Name) else None))
            elif any(isinstance(a, ast.Name) and a.id == 'DEATH_MARK' for a in node.args) and name in ('key', 'press'):
                keys.append(path)
    assert rows == [('buffs.py', 'target')]
    from inventory_tracking.builds.warlock import buffs

    assert buffs.target is mark.target
    assert not keys
