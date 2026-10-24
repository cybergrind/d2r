"""The death in Tower Cellar 5 (22:50:37 on 2026-10-11), replayed to the production macro.

"Red" first (user, 2026-10-12): the test that reproduces what happened, action by action, before any
better decision is tried against it. 103 of the 110 recorded actions are replayed, in order and at
their moments (108 before the sigil was kept under dangerous monsters, 2026-10-20); the one strike that is not is a
strict xfail with its reason.
"""

import functools
import math

import pytest

from inventory_tracking.builds.warlock import mark
from inventory_tracking.macros.routines import press_skill
from inventory_tracking.takes.takes import monsters_of
from tests.inventory_tracking.scenarios.battle import evidence, tower_cellar5 as battle
from tests.inventory_tracking.scenarios.battle.replay import Replay, character


HERALD = 2960229440


@pytest.fixture(autouse=True)
def _reaggro_as_recorded(monkeypatch):
    """The recorded fight's marks: mark.REAGGRO_PACK (on 2026-10-24) designates plain packs the recording did not."""
    monkeypatch.setattr(mark, 'REAGGRO_PACK', False)


def key_as_it_was(rotation, run, skill):
    """A key under the strike as that evening: pressed once a look found the character free, the strike held."""
    press_skill(run, skill)


# The rules of that evening, where today's differ: the sweep stopped for a drop with hostiles beside it,
# and a key under the held strike waited for a free instant (rotation.Rotation.key lets the strike go now).
def tough_as_it_was(hunt, world, reachable):
    """The main weapons only for 40,000 points of life in reach by the tables: never asked for in this fight."""
    return False


def quick_cast_over_as_it_was(run, skill):
    """The wait for the key before to give the right button back as that evening (routines.quick_cast_over before
    2026-10-14): only its own looks counted, and a key long after the one before still said it had waited."""
    from inventory_tracking.common import LOG
    from inventory_tracking.macros.routines import ACTING, QUICK_SECONDS, QUICK_UNSEEN
    from inventory_tracking.macros.skills import skill_name

    if run.quick is None or run.quick[0] == skill:
        return
    before, home, tapped, held = run.quick
    seen = False
    while run.clock() - tapped < QUICK_SECONDS:
        player = run.world().player
        if player is None or player.right_skill is None or home is None:
            break
        seen = seen or player.right_skill == before
        if seen and player.right_skill == home:
            break
        if not seen and not held and player.mode not in ACTING and run.clock() - tapped >= QUICK_UNSEEN:
            break
        run.pace.sleep(0.02)
    else:
        LOG.info('Macro: %s still on the right button %.1fs after its key', skill_name(before), QUICK_SECONDS)
    run.quick = None


# Also since: a jump keeps clear of where the melee monsters will be when it lands (stance.CLOSING_MOST),
# and a Herald's pack gets the main weapons (hunt.Hunter.tough).
AS_IT_WAS = {
    'inventory_tracking.macros.hunting.base.GATHER_CLEAR': 0.0,
    'inventory_tracking.macros.hunting.choice.GATHER_CLEAR': 0.0,
    'inventory_tracking.macros.hunting.sweep.GATHER_CLEAR': 0.0,
    'inventory_tracking.macros.rotation.Rotation.key': key_as_it_was,
    'inventory_tracking.combat.stance.CLOSING_MOST': 0.0,
    'inventory_tracking.combat.stance.CROWD_ESCAPE': 0.0,  # no step out of a pack stood in (2026-10-13)
    'inventory_tracking.macros.hunt.Hunter.tough': tough_as_it_was,
    # and attack mode drinks beside the fight (macros/drinking.py, 2026-10-13)
    'inventory_tracking.macros.drinking.Drinker.look': lambda self, run, here: None,
    # and a potion among monsters is left by the pickup key too (hunt.threat, the same day)
    'inventory_tracking.macros.hunting.choice.threat': lambda run: lambda here, spot: 0,
    'inventory_tracking.macros.hunting.moves.threat': lambda run: lambda here, spot: 0,
    'inventory_tracking.macros.hunting.sweep.threat': lambda run: lambda here, spot: 0,
    'tests.inventory_tracking.scenarios.battle.replay.threat': lambda run: lambda here, spot: 0,
    # and a key waits only for the button's return once any look saw the key before's cast (2026-10-14)
    'inventory_tracking.macros.routines.quick_cast_over': quick_cast_over_as_it_was,
    # and a drop was clicked from afar round a wall (2026-10-14: only on a clear line since, macros/travel.py
    # `walk_reaches`): the potion 8.6 away was 12.5 round a thin wall, and the click left the character where it stood
    'inventory_tracking.macros.travel.ROUND_CLICK': math.inf,
    # and a leader's mark was the price's to refuse (2026-10-20: a leader in reach is marked whatever the price,
    # builds/warlock/mark.py MARK_LEADERS; the elite 55 refused at 6.71 s is marked by today's rule)
    'inventory_tracking.builds.warlock.mark.MARK_LEADERS': False,
}
END = 22.7  # just before the teleport key (22.77 s), whose handling has changed since


def record() -> list[evidence.Action]:
    return evidence.read([(at, text) for at, text in battle.recorded() if 0.4 <= at <= END])


def replayed(as_it_was: bool) -> tuple[tuple[float, str], ...]:
    """The macro's lines of one replay to END: (seconds into the take, the line), by the rules of that evening or
    today's."""
    replay = Replay(battle.FIXTURE, battle.script(patches=AS_IT_WAS if as_it_was else {}))
    replay.key_names = battle.key_names
    return tuple((line.at, line.text) for line in replay.run(END))


@functools.cache
def said(as_it_was: bool) -> tuple[tuple[float, str], ...]:
    """One replay by each rules, made once for the tests here and golden/test_replay_log.py, which freezes the same
    two logs."""
    return replayed(as_it_was)


@functools.cache
def played(as_it_was: bool) -> list[evidence.Action]:
    actions = evidence.read([(at, text) for at, text in said(as_it_was) if at <= END])
    # The mode's start is the replay's own first press (battle.script), not a key of the player's.
    return [action for action in actions if (action.kind, action.what) != ('press', 'hunt any')]


def compared(as_it_was: bool = True) -> evidence.Compared:
    return evidence.compare(record(), played(as_it_was))


def kinds(actions, *wanted):
    return [(round(action.at, 1), action.kind, action.what) for action in actions if action.kind in wanted]


def test_the_fixture_holds_the_fight_to_the_death():
    replay = Replay(battle.FIXTURE, battle.script())
    died = next(at for at, frame in zip(replay.times, replay.frames, strict=True) if character(frame).mode in (0, 17))
    assert died == pytest.approx(battle.DEATH, abs=0.05)
    seen = [
        (at, m)
        for at, frame in zip(replay.times, replay.frames, strict=True)
        for m in monsters_of(frame)
        if m.unit == HERALD
    ]
    assert seen[0][0] == pytest.approx(13.1, abs=0.1)  # the Herald comes 13 s in
    assert seen[0][1].elite
    at_death = min(seen, key=lambda pair: abs(pair[0] - died))[1]
    assert at_death.life == 82  # of 128: it was never close to dead
    assert len(battle.presses()) == 14  # thirteen pickup keys and the teleport key 0.3 s before the death


def test_the_log_reads_as_actions_with_nothing_unknown_left_out():
    actions = record()
    assert [action.what for action in actions if action.kind == 'press'].count('pickup') == 13
    assert kinds(actions, 'sweep stops', 'drink', 'picking') == [
        (18.2, 'sweep stops', 'a super healing potion'),
        (18.2, 'drink', '3'),
        (18.4, 'picking', 'a super healing potion'),
    ]
    unknown = [action.text for action in actions if action.kind == 'other' and action.at <= battle.DEATH]
    assert all(
        text.startswith(('step asked in the fight', 'pickup: a super healing', 'no aim had'))
        or ' ' not in text.strip()
        or text in ('Blade Warp', 'Sigil: Lethargy')
        for text in unknown
    ), unknown


def test_the_replay_makes_the_decision_that_killed_the_character():
    found = compared()
    same = [recorded for recorded, _ in found.same]
    # The fight is stopped for a potion with the pack around, a potion is drunk for room, the
    # pickup begins and its first click takes nothing: 18.2 to 20.6 s.
    assert kinds(same, 'sweep stops', 'drink', 'picking', 'click missed') == [
        (18.2, 'sweep stops', 'a super healing potion'),
        (18.2, 'drink', '3'),
        (18.4, 'picking', 'a super healing potion'),
        (20.6, 'click missed', '0, 0'),
    ]
    # And before it: the stand is judged good five times beside the pack ("Standing well").
    assert len(kinds(same, 'stand')) >= 5


# The leader held (attack.py HOLD_LEADER, 2026-10-21; the player ~18:58: "we're not focusing"; findings
# rca/2026-10-21/herald-aiming-findings.md): from 6.44 s the replay strikes the elite 1816397095 until it is gone
# (11.24 s), from 13.48 s the Herald, where the game's lines went from monster to monster. The aim is what differs;
# the rest of the game's actions are replayed in order.
HELD = ('1816397095', str(HERALD))


def test_the_replay_does_what_the_game_did_action_by_action():
    found = compared()
    # 110 recorded actions in 22.7 s. Not replayed: the game's lines and strikes through other monsters while a
    # leader was held (18), and the pickup press of 15.47 s with its look for a step and its stand, which come 0.7 s
    # sooner (14.75 s) in the fight the hold made. Before 2026-10-21: 103 in order, 7 missing (the sigil of 14.87 s,
    # since 2026-10-20, SIGIL_KEEPS: it is laid at 18.53 s now, with a line saying the Herald stands in it).
    assert len(found.same) >= 92, found.table()
    moved = [('press', 'pickup'), ('no step', ''), ('stand', '')]
    missing = [(action.kind, action.what) for action in found.missing]
    assert [found for found in missing if found[0] not in ('strike', 'line')] == moved
    assert not [what for kind, what in missing if kind == 'strike' and what in HELD]  # no strike of a held one lost
    extra = [(action.kind, action.what) for action in found.extra]
    assert [found for found in extra if found in moved] == moved
    others = [found for found in extra if found not in moved]
    assert all(
        what in HELD
        if kind in ('strike', 'line')
        else kind == 'other' and what.startswith(('strike: the leader', 'sigil'))
        for kind, what in others
    ), others
    assert ('other', f'strike: the leader {HERALD} held until it dies, 17.1 away') in others


def test_the_replay_keeps_the_games_time_without_being_held_to_its_log():
    # Up to the Herald's hold (13.48 s, HELD above) the replay acts as the game did; after it the fight is another
    # one, its pickup 0.7 s sooner and its sigil 3.7 s later (2026-10-21)
    gaps = sorted(abs(recorded.at - replayed.at) for recorded, replayed in compared().same if recorded.at < 13.4)
    assert len(gaps) >= 70
    assert gaps[len(gaps) // 2] <= 0.04  # the median action is 19 ms from its recorded moment
    assert gaps[int(0.9 * len(gaps))] <= 0.12
    assert gaps[-1] <= 0.3


def test_the_slow_keys_under_the_held_strike_are_replayed_at_their_moments():
    # The Sigil came 1.2 s and the Engorge 1.4 s after they were due: a key under the held strike
    # waits for the instant between two casts, and a look every 0.03 s catches one in three or four.
    same = {
        (recorded.kind, recorded.what, round(recorded.at, 1)): replayed.at for recorded, replayed in compared().same
    }
    assert same['skill', 'Sigil: Lethargy', 7.8] == pytest.approx(7.82, abs=0.05)
    assert same['key wait', 'Sigil: Lethargy', 8.8] == pytest.approx(8.83, abs=0.05)
    assert same['skill', 'Engorge', 10.2] == pytest.approx(10.22, abs=0.05)


def test_a_replay_is_the_same_replay_again():
    """The replay harness (battle/replay.py `Replay`) is deterministic: the same take and script give the same lines
    at the same moments. One test for the harness: every take is replayed by the same `Replay.run` with the script's
    one seed (`Script.seed`), so the cows' and Black Marsh's goldens no longer replay theirs a second and third time
    (rca/2026-10-19/cleanup/tests.md P5)."""
    assert replayed(True) == said(True)


@pytest.mark.xfail(
    strict=True,
    reason='the replay holds a leader (attack.py HOLD_LEADER, 2026-10-21) where the game struck the pack: 18 lines '
    'and strikes are its own (test_the_replay_does_what_the_game_did_action_by_action). Before it, one strike of 110: '
    'at 13.67 s the game struck through the monster 740045072 (worth 32327) and the replay through 46244625 (worth '
    '32048), 0.9% apart, the monsters moving between the frames of 13.48 s and 13.52 s',
)
def test_every_recorded_action_is_replayed():
    found = compared()
    assert not found.missing, found.table()
    assert not found.extra, found.table()


def test_with_todays_rule_the_sweep_leaves_the_potion_and_the_fight_goes_on():
    replayed = played(False)
    assert kinds(replayed, 'sweep stops') == []
    assert kinds(replayed, 'sweep leaves')[0][2] == 'a super healing potion'
