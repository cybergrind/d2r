"""The teleport key's two moments of 2026-10-13 in the arena (kp4.py): that the play is the recording's, and
what is asked of the key there. The requirements that the code does not meet yet are `xfail(strict=True)`:
each turns into a failure the day it is met, and the mark is then taken off.

The pack by the seal was played with a rule withdrawn the same day ("N monsters by <mark>: the fight first"):
its replay has that rule from the test's side (kp4.py `fight_first`, "as it was"), and pins that morning. The
plays of the same scene with the rule gone and the pursuit off ("today's key") were deleted on the player's ruling
of 2026-10-19: the loop no longer uses that mode."""

import functools

import pytest

from inventory_tracking.macros.runner import ATTACK, TELEPORT
from inventory_tracking.routes.catalog import ROUTES
from inventory_tracking.routes.progress import Progress
from tests.inventory_tracking.scenarios.arena import kp4
from tests.inventory_tracking.scenarios.arena.game import Arena
from tests.inventory_tracking.scenarios.arena.kp4 import BOSS_AWAY, FIGHT_NEAR, SEAL_PACK, STAGED, Told, said


SEEDS = (1, 2, 3, 4, 5)
QUIET_MOST = 2.0  # seconds without a strike, a hostile in reach, that a press of the key may cost
LIFE_FLOOR = 0.5  # of the most life: the mashed key must not take the character under it
FIRST_SEAL, SECOND_SEAL = 'Vizier seal 1', 'Vizier seal 2'
BOSS_LINE = 'Grand Vizier of Chaos, attack mode'


@functools.cache
def moment(name: str):
    found = kp4.stored(next(staged for staged in STAGED if staged.name == name))
    assert found is not None, 'cut it: python -m tests.inventory_tracking.scenarios.arena.kp4 --cut'
    return found


@functools.cache
def play(
    name: str, seed: int, presses: tuple | None = None, as_it_was: bool | None = None
) -> tuple[Told, tuple[tuple[float, str], ...]]:
    """One play, kept. `as_it_was` None: with the rules the moment was recorded under; False: today's."""
    staged = next(staged for staged in STAGED if staged.name == name)
    scene, marks, _ = moment(name)
    told, lines = kp4.played(scene, marks, staged, seed, presses, as_it_was)
    return told, tuple(lines)


def plays(staged: kp4.Staged) -> list[tuple[Told, tuple[tuple[float, str], ...]]]:
    return [play(staged.name, seed) for seed in SEEDS]


# -- the pieces -----------------------------------------------------------------------------------------


def test_a_timed_wait_of_the_runners_event_passes_on_the_arenas_clock() -> None:
    scene, _, _ = moment(SEAL_PACK.name)
    arena = Arena(scene)
    event = kp4.ArenaThreading(arena).Event()
    assert event.wait(0.5) is False
    assert arena.clock.now == pytest.approx(0.5)
    event.set()
    assert event.wait(0.5) is True
    assert arena.clock.now == pytest.approx(0.5)


def test_the_card_is_the_handlers_and_leads_with_the_seal_the_route_is_at() -> None:
    scene, marks, _ = moment(SEAL_PACK.name)
    assert [mark.label for mark in marks] == [
        'Diablo', FIRST_SEAL, SECOND_SEAL, 'De Seis seal', 'Infector seal 1', 'Infector seal 2',
    ]  # fmt: skip
    progress = Progress(ROUTES, kp4.PERFORMED, dead=frozenset)
    progress.note('arena', 108)
    card = kp4.Card(lambda: kp4.Level(108, (), ()), marks, progress)
    first = card.target()
    assert first is not None
    # probe.log 09:06:40.203 and .690: "object 2960892495 (class 396) of Vizier seal 1 at (7655.0, 5315.0), 0.0
    # from the mark" and "use Vizier seal 1 is done at (1531.0, 1063.0)"
    assert (first.label, first.point, first.use) == (FIRST_SEAL, (1531.0, 1063.0), 396)
    assert [(prop.unit, prop.txt, prop.at, prop.mode) for prop in scene.things if prop.txt == 396] == [
        (2960892495, 396, (7655.0, 5315.0), 0)
    ]
    progress.used(108, FIRST_SEAL, first.point, card.marks(FIRST_SEAL))
    second = card.target()
    assert second is not None
    assert (second.label, second.point, second.use) == (SECOND_SEAL, (1531.0, 1055.0), 395)


@pytest.mark.parametrize('staged', STAGED, ids=lambda staged: staged.name)
def test_a_stored_moment_plays(staged) -> None:
    # A play of the seeds the tests below read (`plays`), so a moment that no longer plays fails here and not only
    # inside their strict expected failures. That the same seed gives the same play is the arena's, tested once
    # (situations/test_situations.py `test_the_example_plays_the_same_twice`).
    _, lines = play(staged.name, 3)
    assert lines


# -- the pack by the seal, the key mashed: as it was that morning ---------------------------------------


def test_the_recording_has_no_strike_for_seven_seconds_with_hostiles_in_reach() -> None:
    _, _, truth = moment(SEAL_PACK.name)
    assert truth.strikes[0] == pytest.approx(7.11, abs=0.05)
    assert truth.quiet_mashed == pytest.approx(6.75, abs=0.1)
    assert truth.opened == 21.03


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SIM-CASTERS (rca/2026-10-13/sim-casters.md): since the casters think by the client's code the pack "
        'by the seal comes off it toward the character and its companions; 10 of the 16 presses see 8 by the '
        'seal in seeds 1 and 2 (16 as recorded in seed 3); the same with a quarter of the damage'
    ),
)
def test_every_mashed_press_says_the_fight_first_and_pauses_the_mode_as_recorded() -> None:
    # probe.log 09:06:19.686 to 26.028: sixteen times "N monsters by Vizier seal 1: the fight first", the first
    # with 8 of them; one press of the toggle among them ("Attack mode off")
    burst = [at for at, routine in SEAL_PACK.incident.presses if routine == TELEPORT and at <= SEAL_PACK.mashed]
    assert len(burst) == 16
    for told, lines in plays(SEAL_PACK):
        assert said(lines, 'by Vizier seal 1: the fight first', SEAL_PACK.mashed) == 16
        assert next(text for _, text in lines) == 'Macro: 8 monsters by Vizier seal 1: the fight first'
        assert said(lines, 'Attack mode off', SEAL_PACK.mashed) == 1
        assert said(lines, 'Attack mode paused', SEAL_PACK.mashed) >= 13  # 14 in the log
        assert not told.dead


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SIM-CASTERS (rca/2026-10-13/sim-casters.md): since the casters think by the client's code the pack "
        'by the seal comes off it toward the character and its companions; the first strike comes 15.9 s in, '
        'not 6 to 7.5 (7.11 recorded)'
    ),
)
def test_no_strike_begins_while_the_key_is_mashed_as_recorded() -> None:
    # The recording's first strike is 7.11 s after the landing; the arena's comes with the burst's last press
    # (6.27 s: the mode had been on for 0.1 s then and its ward was up already, which the recording's was not).
    for told, _ in plays(SEAL_PACK):
        assert told.strikes
        assert 6.0 <= told.strikes[0] <= 7.5
        assert told.quiet_mashed >= 6.0


def test_one_press_alone_is_followed_by_the_fight_at_once() -> None:
    """The same scene with the first press only: what the mashed key costs is the other fifteen."""
    for seed in SEEDS[:3]:
        told, lines = play(SEAL_PACK.name, seed, ((0.0, TELEPORT),))
        assert said(lines, 'the fight first') == 1
        assert told.strikes[0] <= 1.5
        assert told.quiet <= QUIET_MOST


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SIM-CASTERS (rca/2026-10-13/sim-casters.md): since the casters think by the client's code the pack "
        'by the seal comes off it toward the character and its companions; in one seed of five the mode is '
        'already off when the toggle comes'
    ),
)
def test_the_toggle_pressed_in_the_burst_turns_the_mode_off_as_recorded() -> None:
    # 09:06:22.945 "request hunt any ... while hunt any" / "Attack mode off": the attack key, pressed to start
    # the fight the teleport key had already asked for, ended it; nothing ran for the 1.2 s to the next press.
    assert (3.28, ATTACK) in SEAL_PACK.incident.presses
    for _, lines in plays(SEAL_PACK):
        after = [text for at, text in lines if 3.28 <= at < 4.5]
        assert after == ['Macro: Attack mode off']


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SIM-CASTERS: the casters' blows come from the tables; Psychic Ward is played since (sim-casters.md section 9) "
        "and takes their physical points, not the Venom Lords' flames: least life 785 (719 before it), 1570 recorded"
    ),
)
def test_the_mashed_key_does_not_take_the_character_under_half_its_life() -> None:
    """Asked as a requirement (the presses must not kill), and met in the arena as in the recording (least life
    1570 of 1783): the stall costs time here, not the character. Kept as a guard for the fix."""
    _, _, truth = moment(SEAL_PACK.name)
    scene, _, _ = moment(SEAL_PACK.name)
    assert truth.low >= LIFE_FLOOR * scene.hero.max_life
    for told, _ in plays(SEAL_PACK):
        assert not told.dead
        assert told.low >= LIFE_FLOOR * scene.hero.max_life


@pytest.mark.xfail(strict=True, reason='every press of the teleport key pauses attack mode and the quiet after it')
def test_a_press_of_the_teleport_key_does_not_stop_the_attack() -> None:
    """With a pack by the seal the key said "the fight first": the fight must then go on, however often the
    key is pressed. No more than QUIET_MOST seconds without a strike while a hostile is in reach. The defect
    of that morning, by the rule as it was; the rule is withdrawn, and a rule put in its place must meet this."""
    assert SEAL_PACK.as_it_was
    for told, _ in plays(SEAL_PACK):
        assert told.quiet_mashed <= QUIET_MOST


# -- the boss out of reach ------------------------------------------------------------------------------


def test_the_boss_moment_is_played_by_todays_rules() -> None:
    assert not BOSS_AWAY.as_it_was


def test_the_recording_has_the_boss_57_units_off_and_the_character_still() -> None:
    _, _, truth = moment(BOSS_AWAY.name)
    assert truth.boss_gap == (57.4, 57.4)
    assert truth.moved == 0.0
    assert truth.boss_dead is None


def test_the_presses_at_the_boss_stage_say_attack_mode_and_move_nothing_as_recorded() -> None:
    # probe.log 09:06:42.585 to 09:07:06.140: 48 times "Diablo: Grand Vizier of Chaos, attack mode"
    assert len(BOSS_AWAY.incident.presses) == 48
    for told, lines in plays(BOSS_AWAY):
        assert said(lines, BOSS_LINE) == 48
        assert said(lines, 'Attack mode paused') == 47
        assert told.moved == 0.0
        assert told.boss_gap == (57.4, 57.4)
        assert told.boss_dead is None
        assert told.stage == 'fight Grand Vizier of Chaos'
        assert not said(lines, 'Teleport')
        assert not said(lines, 'Blade Warp')


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SIM-CASTERS (rca/2026-10-13/sim-casters.md): since the casters think by the client's code the pack "
        'by the seal comes off it toward the character and its companions; a monster comes by later (13 to 16'
        " s, as the recording's 16.4) and the fight's count differs (not 4 down)"
    ),
)
def test_the_monsters_by_the_seal_are_fought_and_then_nothing_is_in_reach_as_recorded() -> None:
    # 09:06:43.392 to 45.559: "Echoing Strike ... at the monster 362", "Nothing left in reach: 4 down in 1 casts"
    _, _, truth = moment(BOSS_AWAY.name)
    # six strikes in the first three seconds; one more 16.4 s in, at a monster that came by
    assert [at < 4.0 for at in truth.strikes] == [True] * 6 + [False]
    for told, lines in plays(BOSS_AWAY):
        assert told.strikes
        assert max(told.strikes) < 6.0
        assert said(lines, 'Nothing left in reach: 4 down') == 1


@pytest.mark.xfail(strict=True, reason='a fight stage without a mark is attack mode where the character stands')
def test_repeated_presses_bring_the_character_within_fight_distance_of_the_boss() -> None:
    """The route is at a boss that stands out of attack mode's sight: the key must take the character to it
    (within macros/route.py FIGHT_NEAR, where a fight's own mark turns the mode on), or the boss be dead."""
    for told, _ in plays(BOSS_AWAY):
        assert told.boss_gap is not None
        assert told.boss_dead is not None or told.boss_gap[0] <= FIGHT_NEAR
