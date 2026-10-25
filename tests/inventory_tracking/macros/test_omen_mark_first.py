"""The mark first as a Herald's pack shows (macros/hunt.py OMEN_MARK_FIRST, 2026-10-25). The player, ~11:33: "we need
near instant cast after pack has appeared"; ~11:36: "we can both strike firind + cast DM / when I'm playing it by
hand it feels way smoother" (rca/2026-10-25/mark-at-spawn-findings.md). And the mark's measured aim shape
(game/view.py `markable`, macros/buffs.py MARK_SHAPE)."""

import math

import pytest

from inventory_tracking.builds.warlock import buffs as plan
from inventory_tracking.combat import pack
from inventory_tracking.game import view as view_module
from inventory_tracking.game.layout import MONSTER_UNIT
from inventory_tracking.game.view import Viewport
from inventory_tracking.macros import buffs as buffs_module, hunt as hunt_module
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.hunt import OMEN_SPAWN
from inventory_tracking.macros.hunting.base import HERALD_OMEN
from tests.inventory_tracking.macros.test_herald_mark_first import Timed, _barred
from tests.inventory_tracking.macros.test_hunt import ASPECT, MINION, appear, demon, foe, game, hunter, keys, me


SPOTS = ((0.0, 0.0), (1.0, 2.0), (-1.0, -2.0), (2.0, -1.0))
BODY = 0.02  # window heights: a body's half under the pointer


def played(monkeypatch, *, on: bool, strike: bool = True, until: float = 7.5, away: float = 18.0, hover: bool = True):
    """Attack mode alone with an omen `away` east read at the start and its pack of four tier 5 members OMEN_SPAWN s
    on (a demon of the character's beside it; HERALD_MARK_FIRST off: no landing here): the game, the spawn's clock and
    the order of the marks and strikes cast after the spawn, and the clocks the Death Mark key went down at (`keyed`).
    `strike`: OMEN_STRIKE (on live), the strike held on the spot before it; `hover`: the hover names the monster
    whose body is under the pointer (`named_under_pointer`), as the game's record does a frame after a move."""
    from inventory_tracking.builds.warlock import mark as mark_module
    from inventory_tracking.builds.warlock.skills import DEATH_MARK

    monkeypatch.setattr(mark_module, 'why_not', lambda facts, monster: None)  # the mark's worth is not asked here
    monkeypatch.setattr(hunt_module, 'OMEN_READ_ALONE', True)
    monkeypatch.setattr(hunt_module, 'OMEN_STRIKE', strike)
    monkeypatch.setattr(hunt_module, 'OMEN_MARK_FIRST', on)
    monkeypatch.setattr(plan, 'OMEN_SIGIL', False)
    monkeypatch.setattr(pack, 'HERALD_MARK_FIRST', False)
    play = game(demon(x=4999.0, y=5001.0))
    hunt = hunter(play, pursuit=False)
    order: list[str] = []
    play.marks, play.strikes = Timed('mark', order, play.clock), Timed('strike', order, play.clock)
    here = (me(play.world).x, me(play.world).y)
    spot = (here[0] + away, here[1])
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    start = play.clock.now
    spawn = start + OMEN_SPAWN
    if hover:
        run.hovered = named_under_pointer(play, run.hovered)
    run.flights = lambda kinds: ((0, HERALD_OMEN, *spot),) if HERALD_OMEN in kinds and play.clock.now < spawn else ()
    members = [
        foe(20 + k, spot[0] + dx, spot[1] + dy, flags=MINION, tier=5, life=900, max_life=900)
        for k, (dx, dy) in enumerate(SPOTS)
    ]
    play.toughness.update({m.unit_id: 50 for m in members})  # they stand the bout out
    keyed: list[float] = []
    real = buffs_module.press_through

    def press_through(run, skill) -> None:
        if skill == DEATH_MARK:
            keyed.append(run.clock())
        real(run, skill)

    monkeypatch.setattr(buffs_module, 'press_through', press_through)
    seen: dict[str, int] = {}
    play.arrivals += [
        (spawn - 0.001, lambda: seen.setdefault('spawn', len(order))),
        (spawn, appear(play, *members)),
        (start + until, run.cancelled.set),
    ]
    play.arrivals.sort(key=lambda pair: pair[0])
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    return play, spawn, order[seen.get('spawn', 0) :], [at - spawn for at in keyed if at >= spawn]


def named_under_pointer(play, inner):
    """The hover record: the live monster whose body is drawn within BODY of the pointer (the fake game's own
    `unit_under_pointer` names no monster), else what `inner` names."""

    def hovered():
        player = me(play.world)
        view = Viewport(ASPECT)
        at = play.keys.fraction()
        for m in play.world.monsters:
            if not m.ally and math.dist(at, view.body((player.x, player.y), m.x, m.y)) <= BODY:
                return (MONSTER_UNIT, m.unit_id)
        return inner() if inner is not None else None

    return hovered


def first_mark(play, spawn: float) -> tuple[float, int | None]:
    """Seconds from the pack's first frame to the first Death Mark cast after it (the fake casts a key that came
    during a cast at its end, as the game), and the unit it went on."""
    index = next(i for i, at in enumerate(play.marks.at) if at >= spawn)
    return play.marks.at[index] - spawn, play.marks[index]


# The fake's figures, measured 2026-10-25 (the findings' §4): off, the key 0.37 s (hold) / 0.08 s (no hold) after the
# spawn, behind the strike's press; on, 0.00 s / 0.00 s, the mark's cast at the strike's cast end.


@pytest.mark.parametrize('strike', [True, False])
def test_off_the_mark_waits_behind_the_strike(monkeypatch, strike) -> None:
    play, spawn, after, keyed = played(monkeypatch, on=False, strike=strike)
    assert 'mark' in after
    assert after[0] == 'strike'
    assert keyed[0] > 0.05
    print(f'off, strike {strike}: key {keyed[0]:.3f} s, cast {first_mark(play, spawn)[0]:.3f} s after the spawn')


@pytest.mark.parametrize(('strike', 'within'), [(True, 0.1), (False, 0.15)])
def test_on_the_mark_s_key_goes_within_a_look_of_the_pack(monkeypatch, strike, within) -> None:
    # In the omen's hold (`omen_strike`, the strike held on the spot: the pointer on the pack already) or with none
    # (the look's top, the pointer elsewhere: one move, 0.096 s in this fake, 15 ms p50 live): the key at the look
    # that sees the pack, its cast at the cast under way's end at the latest, on a member of the pack
    play, spawn, after, keyed = played(monkeypatch, on=True, strike=strike)
    took, unit = first_mark(play, spawn)
    print(f'on, strike {strike}: key {keyed[0]:.3f} s, cast {took:.3f} s after the spawn')
    assert keyed[0] <= within
    assert took <= keyed[0] + 0.4  # one strike's cast at most (the game keeps a key that comes during a cast)
    assert unit in {20, 21, 22, 23}
    assert after.index('mark') <= 1  # a strike cast already under way at the spawn is the only one before it
    assert 'strike' in after[after.index('mark') :]  # then the fight


def test_on_the_strike_held_through_the_mark(monkeypatch) -> None:
    # The player: "we can both strike firind + cast DM": the strike held on the spot is not let go for the mark's key
    released: list[float] = []
    real = buffs_module.Buffs.let_go_first

    def let_go_first(self, run):
        released.append(run.clock())
        real(self, run)

    monkeypatch.setattr(buffs_module.Buffs, 'let_go_first', let_go_first)
    _play, spawn, _after, keyed = played(monkeypatch, on=True, strike=True)
    assert keyed
    assert not [at for at in released if spawn <= at <= spawn + keyed[0]]


def test_on_the_fight_casts_hold_keeps_the_mark_back(monkeypatch) -> None:
    # Blows that take the life can come in reach (FIGHT_CAST_REACH): no mark before the strike, survival first
    monkeypatch.setattr(hunt_module.Hunter, 'fight_facts', _barred(hunt_module.Hunter.fight_facts))
    _play, _spawn, after, _keyed = played(monkeypatch, on=True, strike=False)
    assert 'mark' not in after[:1]


def test_on_a_real_threat_the_safety_saw_goes_first(monkeypatch) -> None:
    # The safety's last look saw one (it prices nothing in the quiet: pinned here for every look)
    threat = property(lambda self: 'surrounded: 6 within 5', lambda self, value: None)
    monkeypatch.setattr(hunt_module.Safety, 'hold_exempt', threat, raising=False)
    _play, _spawn, after, keyed = played(monkeypatch, on=True, strike=False)
    assert after[0] == 'strike'
    assert not keyed or keyed[0] > 0.05


# --- the mark's aim shape (game/view.py `markable`, measured on the host's 2560 x 1418 window) ---


@pytest.mark.parametrize(
    ('point', 'inside'),
    [
        ((0.56, 0.83), True),  # the 11:37:30 spawn's refused mark: ground above the skill bar
        ((0.50, 0.90), True),
        ((0.50, 0.93), False),  # the skill bar (its top at 0.92)
        ((0.22, 0.83), True),  # above the life orb's angel (0.845)
        ((0.22, 0.86), False),
        ((0.80, 0.80), True),  # above the mana orb's demon's horns (0.815)
        ((0.80, 0.82), False),
        ((0.05, 0.95), True),  # the bottom corners show the ground
        ((0.95, 0.95), True),
        ((0.95, 0.995), False),  # the window's edge
        ((0.30, 0.03), True),  # the top below the desktop's bar
        ((0.30, 0.01), False),
        ((0.05, 0.05), False),  # the companions' portraits
        ((0.995, 0.5), False),
    ],
)
def test_the_mark_s_shape_is_the_hud_s_outline(point, inside) -> None:
    assert view_module.markable(point) is inside


def test_mark_shape_is_the_mark_s_alone(monkeypatch) -> None:
    from inventory_tracking.builds.warlock.skills import DEATH_MARK, SIGIL_LETHARGY

    buffs = buffs_module.Buffs(_build())
    below = (0.56, 0.83)
    monkeypatch.setattr(buffs_module, 'MARK_SHAPE', False)
    assert not buffs.aimable(DEATH_MARK, below)
    monkeypatch.setattr(buffs_module, 'MARK_SHAPE', True)
    monkeypatch.setattr(pack, 'FIRST', {DEATH_MARK})
    assert buffs.aimable(DEATH_MARK, below)
    assert not buffs.aimable(SIGIL_LETHARGY, below)  # AIM_LIMITS for the other casts


def _build():
    from tests.inventory_tracking.macros.test_hunt import warlock

    return warlock(game().world)
