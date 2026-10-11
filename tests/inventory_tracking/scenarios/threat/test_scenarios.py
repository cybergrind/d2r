"""Battlefields where the line worth the most life points is the wrong one (scenes.py), scored with the
incoming-damage model of harness.py. Each test states the behaviour wanted of the fight; where the game's
decision of today (`harness.today`: `observe` + `LinePolicy` + `aim_choice`, standing still) does not
give it, the test is a strict xfail with the measured numbers. The numbers are the model's, at the Terror
Zone's monster level 95: they rank decisions, they do not predict a real fight (no companions, no
defence, no potions)."""

import pytest

from tests.inventory_tracking.scenarios.threat.harness import TICKS, Controller, Result, Survivor, ThreatAim, run, today
from tests.inventory_tracking.scenarios.threat.scenes import SCENES


NEAR = 1.25  # a decision costing this many times the best wanted one's damage is near enough
SLACK = 25.0  # points: and this much on top (a tick or two of one monster)


def play(name: str, controller: Controller = today) -> Result:
    spec = SCENES[name]
    return run(spec.scene(), controller, spec.horizon)


def best(name: str) -> Result:
    """The cheapest of the scene's wanted decisions."""
    return min((play(name, make()) for make in SCENES[name].wanted.values()), key=lambda result: result.taken)


def near_enough(result: Result, name: str) -> bool:
    return result.taken <= NEAR * best(name).taken + SLACK


def killable(name: str) -> set[int]:
    return {h.unit for h in SCENES[name].scene().hostiles if not h.immune}


def spent_on_the_killable(result: Result, name: str) -> bool:
    """Everything that can die died, and no cast went on after it (two casts a monster are plenty here)."""
    return set(result.kills) == killable(name) and len(result.casts) <= 2 * len(killable(name))


# --- which line: threat, not points ----------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True, reason=('today the 4 slow Bramble Hulks (46k points on a line) go first: 1098 taken, Gloams first 274')
)
def test_the_shooters_behind_a_fat_slow_pack_die_first():
    result = play('gloams_behind_hulks')
    assert result.first in (10, 11, 12)
    assert near_enough(result, 'gloams_behind_hulks')


@pytest.mark.xfail(
    strict=True, reason=('today the unique Death Lord (points x2) goes first: 1420 taken, soul and witch first 475')
)
def test_the_frail_casters_die_before_the_tanky_elite():
    result = play('witch_and_soul_beside_tanky_elite')
    assert result.kills[-1] == 1  # the elite last
    assert near_enough(result, 'witch_and_soul_beside_tanky_elite')


@pytest.mark.xfail(
    strict=True,
    reason=('today the fresh Bramble Hulk (4760 points a cast) beats the Gloam with 357 left: 274 taken, 0 wanted'),
)
def test_a_dying_shooter_is_finished_before_a_fresh_brute():
    result = play('dying_gloam_fresh_hulk')
    assert result.kills[0] == 2
    assert near_enough(result, 'dying_gloam_fresh_hulk')


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today a tie goes to the monster read first, the pair 16 units '
        'off: 693 taken, 277 with the pair in contact first'
    ),
)
def test_of_two_lines_worth_the_same_the_one_in_contact_goes_first():
    result = play('equal_lines_far_and_in_contact')
    assert result.kills[:2] in ([3, 4], [4, 3])
    assert near_enough(result, 'equal_lines_far_and_in_contact')


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today the 5 Death Lords go first and 2 dolls are blown up on the '
        'character: 1098 taken (900 of blasts), dolls first 579'
    ),
)
def test_exploding_dolls_die_before_they_arrive():
    result = play('dolls_running_in')
    assert result.blasts == 0
    assert near_enough(result, 'dolls_running_in')


def test_beside_an_aura_elite_the_line_of_minions_stays_right():
    """A guard for the day threat is weighed: Might on the elite does not make the elite the first target."""
    result = play('might_elite_beside_minions')
    assert result.first != 10
    assert near_enough(result, 'might_elite_beside_minions')  # 410 today; minions first 341, elite first 1136


def test_the_recorded_chaos_mix_keeps_the_line_of_venom_lords():
    """A guard: threat first is not shooters first. Three Venom Lords arrive within the second."""
    result = play('venom_lords_and_casters')
    assert result.first in (0, 1, 2)
    assert near_enough(result, 'venom_lords_and_casters')  # 1017 today and lords first; casters first 1758


# --- what the blades cannot hurt --------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today all 28 casts of 10 s go through the immune unique Ghoul '
        '(points x2, life never falls): 0 kills, 4077 taken'
    ),
)
def test_no_cast_goes_through_an_immune_elite_while_killable_shooters_stand_beside():
    result = play('stone_skin_elite_soaks')
    assert result.first != 1
    assert spent_on_the_killable(result, 'stone_skin_elite_soaks')


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today the line of 3 immune Ghosts takes 28 casts of 10 s; only the Slayer that walked into it dies, 4793 taken'
    ),
)
def test_the_killable_die_first_when_immune_ghosts_stand_in_front():
    result = play('ghosts_in_front_of_archers')
    assert result.first in killable('ghosts_in_front_of_archers')
    assert spent_on_the_killable(result, 'ghosts_in_front_of_archers')


@pytest.mark.xfail(
    strict=True,
    reason=('today the fight stands and casts 28 times at 5 immune Hell Bovines: dead after 4.3 s, 7288 taken in 10 s'),
)
def test_a_pack_the_blades_cannot_hurt_is_not_stood_in():
    """In the takes immune elites died as fast as the others (companions, Hex Purge off the deaths around
    them); here every monster is immune (Stone Skin forced on the zone), so nothing dies to start that."""
    assert play('stone_skin_zone').alive


# --- the character's life ---------------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=('today the fight stands between both packs: 647 taken; 14 units north first, then the same aim: 69'),
)
def test_a_step_out_of_the_pincer_before_it_closes():
    assert near_enough(play('bovines_closing_from_two_sides'), 'bovines_closing_from_two_sides')


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today 500 life and 3 Hell Bovines in contact: dead after 0.8 s, 624 '
        'taken; 7 units through the gap first: 200 and alive'
    ),
)
def test_low_life_in_melee_breaks_contact_first():
    assert play('low_life_in_melee').alive


def test_low_life_fights_on_when_its_kills_come_first():
    """A guard for the day the fight may yield: two Gloams one cast from dead are shot, not run from."""
    result = play('low_life_two_dying_gloams')
    assert result.alive
    assert result.cleared_at is not None
    assert result.cleared_at <= TICKS
    assert play('low_life_two_dying_gloams', Survivor()).moved == 0


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today 600 life under 4 fresh Oblivion Knights (578 a second, 8 '
        'casts to clear): dead after 1.0 s; leaving: 428 taken'
    ),
)
def test_low_life_under_fire_it_cannot_outkill_yields():
    assert play('low_life_under_knights').alive


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today 3 dolls in contact are killed where they stand: 1350 of blasts on 900 '
        'life, dead by the second cast; a step back first: 45 taken'
    ),
)
def test_dolls_on_the_character_are_not_blown_up_there():
    result = play('dolls_on_the_character')
    assert result.blasts == 0
    assert result.alive


@pytest.mark.xfail(
    strict=True,
    reason=(
        'today the fight stands in a tier 1 Herald pack (1517 a second) and aims '
        'at the Herald: dead after 1.2 s; leaving: 1389 taken'
    ),
)
def test_a_herald_pack_that_kills_in_a_second_is_not_stood_in():
    assert play('herald_with_minions').alive


# --- the wanted is reachable: what each missing input buys, in the same model ---------------------------


@pytest.mark.parametrize(
    'name',
    [
        'gloams_behind_hulks',
        'witch_and_soul_beside_tanky_elite',
        'dying_gloam_fresh_hulk',
        'equal_lines_far_and_in_contact',
        'dolls_running_in',
        'might_elite_beside_minions',
        'venom_lords_and_casters',
    ],
)
def test_a_line_scored_by_the_damage_it_removes_is_near_the_best_order(name):
    assert near_enough(play(name, ThreatAim(immunity=False)), name)


@pytest.mark.parametrize('name', ['stone_skin_elite_soaks', 'ghosts_in_front_of_archers'])
def test_knowing_immunity_alone_turns_the_casts_to_the_killable(name):
    assert spent_on_the_killable(play(name, ThreatAim(weights=False)), name)


@pytest.mark.parametrize(
    'name',
    ['low_life_in_melee', 'low_life_under_knights', 'dolls_on_the_character', 'herald_with_minions', 'stone_skin_zone',
     'stone_skin_elite_soaks', 'ghosts_in_front_of_archers'],
)  # fmt: skip
def test_looking_ahead_at_its_own_life_keeps_the_character_alive(name):
    assert not play(name).alive
    assert play(name, Survivor()).alive
