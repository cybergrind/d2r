"""Macro against manual from the takes (combat/compare.py), on the two fixture cuts of real play."""

from pathlib import Path

from inventory_tracking.combat.compare import compare, lines, opportunities, row
from inventory_tracking.combat.takes import Take, ground_under_pointer, monsters_of, player_of


FIXTURES = Path(__file__).parent / 'fixtures'


def test_a_take_is_the_macros_when_most_of_its_casts_were_made_while_a_macro_ran():
    assert row(Take.load(FIXTURES / 'catacombs-macro'))['side'] == 'macro'
    assert row(Take.load(FIXTURES / 'chaos-manual'))['side'] == 'manual'


def test_the_shares_of_the_frames_with_a_target_add_up_and_the_player_stands_less_than_the_macro_did():
    manual = opportunities(Take.load(FIXTURES / 'chaos-manual'))
    macro = opportunities(Take.load(FIXTURES / 'catacombs-macro'))
    for found in (manual, macro):
        assert found['frames'] > 100
        assert abs(found['casting'] + found['moving'] + found['standing'] - 1) < 0.02
    assert manual['moving'] > 0.1  # the player runs between casts
    assert macro['moving'] < 0.05  # attack mode stood where it was put


def test_the_comparison_groups_the_takes_by_level_and_side():
    report = compare(FIXTURES)
    assert set(report['takes']) == {'catacombs-macro', 'chaos-manual'}
    assert set(report['groups']) == {'37 macro', '108 manual'}
    chaos = report['takes']['chaos-manual']
    assert chaos['combat_seconds'] > 15
    assert chaos['points_per_combat_second'] > 5000
    assert chaos['kills_per_combat_minute'] > 30
    text = lines(report)
    assert len(text) == 4
    assert text[-2].startswith('37 macro')
    assert text[-1].startswith('108 manual')
    assert 'standing' in text[0]


def test_the_frame_rows_name_what_the_frames_hold():
    take = Take.load(FIXTURES / 'chaos-manual')
    frame = take.frames[0]
    player = player_of(frame)
    assert player is not None
    assert player.area == 108
    assert player.at == (frame['p'][3], frame['p'][4])
    monsters = monsters_of(frame)
    assert any(m.hostile for m in monsters)
    assert any(m.companion for m in monsters)
    assert not any(m.hostile and m.companion for m in monsters)
    assert all(0 <= m.life_share <= 1 for m in monsters)
    ground = ground_under_pointer(frame, 2560 / 1418)
    assert ground is not None
    assert abs(ground[0] - player.x) < 60
    assert player_of({'p': None}) is None
    assert ground_under_pointer({'p': None, 'in': [None] * 6}, 1.8) is None
