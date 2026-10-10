"""The live scorer (combat/score.py): damage per combat second and kills per minute from world reads."""

from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.combat.score import LiveScore
from inventory_tracking.macros.world import Monster, Player


PLAYER = Player(1, 'CybergrindAA', 1, 108, 5000.0, 5000.0, None)
FULL = points_of(310, 108)


def foe(unit, x, life=128):
    return Monster(unit, 310, 1, x, 5000.0, 0xFFFFFFFF, life=life, max_life=128)


def test_life_drops_and_kills_within_reach_are_scored_per_combat_second():
    score = LiveScore()
    assert score.line() == 'no combat yet'
    score.note(0.0, PLAYER, [foe(10, 5010.0), foe(11, 5012.0)])
    score.note(0.2, PLAYER, [foe(10, 5010.0, 64), foe(11, 5012.0)])  # half a life
    score.note(0.4, PLAYER, [foe(11, 5012.0)])  # 10 is gone beside the character: a kill, its other half
    score.note(0.6, PLAYER, [foe(11, 5012.0)])
    found = score.totals()
    assert found['kills'] == 1
    assert found['points'] == round(FULL)
    assert found['combat_seconds'] == 0.6
    assert found['points_per_combat_second'] == round(FULL / 0.6)
    assert score.line().endswith('kills/min over 0.6s of combat')


def test_a_monster_far_away_is_no_combat_and_its_leaving_memory_is_no_kill():
    score = LiveScore()
    score.note(0.0, PLAYER, [foe(10, 5100.0)])
    score.note(0.2, PLAYER, [foe(10, 5100.0)])
    score.note(0.4, PLAYER, [])
    assert score.totals() == {
        'combat_seconds': 0.0, 'points': 0, 'kills': 0, 'points_per_combat_second': 0, 'kills_per_minute': 0.0,
    }  # fmt: skip


def test_the_score_looks_back_one_window_and_a_pause_is_not_play():
    score = LiveScore(window=10.0)
    score.note(0.0, PLAYER, [foe(10, 5010.0)])
    score.note(0.2, PLAYER, [foe(10, 5010.0, 64)])
    score.note(30.0, PLAYER, [foe(10, 5010.0, 64)])  # a long gap: not a stretch of combat
    score.note(30.2, PLAYER, [foe(10, 5010.0, 32)])
    found = score.totals()
    assert found['combat_seconds'] == 0.2
    assert found['points'] == round(FULL / 4)  # the first drop is out of the window
    score.note(31.0, None, [])  # out of the game: what was known of the monsters is dropped
    score.note(31.2, PLAYER, [])
    assert score.totals()['kills'] == 0
