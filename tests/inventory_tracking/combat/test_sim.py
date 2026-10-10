"""The simulator (combat/sim): contacts become damage with the duplicate rule, monsters die when
their points run out, the gate compares with the recorded kills."""

import json
from pathlib import Path

from inventory_tracking.combat.mechanics.echoing_strike import OUT_FRAMES
from inventory_tracking.combat.sim.engine import DUPLICATE, gate, replay, score, simulate
from inventory_tracking.combat.sim.situation import Cast, CompanionTrack, MonsterTrack, Situation, cut, describe
from inventory_tracking.combat.takes import Take


NO_LINK = (0.0, 0, 0.0)
NO_BLAST = (0.0, 0.0)
NO_MARK = (0.0, 0)


def situation(*monsters, frames=60, companions=()):
    origin = (5000.0, 5000.0)
    player = dict.fromkeys(range(frames + 1), origin)
    tracks = {m.unit: m for m in monsters}
    return Situation(0, frames, 108, 2560 / 1418, player, tracks, [], 0.0, {c.unit: c for c in companions})


def standing(unit, x, y, points, frames=60, txt=310, death=None):
    return MonsterTrack(unit, txt, points, dict.fromkeys(range(frames + 1), (x, y)), 1.0, death)


def test_blades_through_a_line_of_monsters_deal_full_damage_to_each_and_duplicates_a_tenth():
    near, far = standing(1, 5000.0, 5006.0, 10_000.0), standing(2, 5000.0, 5012.0, 10_000.0)
    outcome = simulate(
        situation(near, far),
        [(0, (5000.0, 5012.0))],
        lambda txt: 1000.0,
        companions={},
        link=NO_LINK,
        explosion=NO_BLAST,
    )
    # Five blades converge at the far monster: 1 + 4 * 0.1 blades out and again back. The near one sits
    # on the line where the fan is still 1.9 units wide: every blade passes within 2 units of it too.
    assert outcome.damage[2] == 1000.0 * (1 + 4 * DUPLICATE) * 2
    assert outcome.damage[1] == 1000.0 * (1 + 4 * DUPLICATE) * 2
    assert outcome.deaths == {}
    assert outcome.contacts == 20


def test_a_monster_dies_when_its_points_run_out_and_takes_nothing_after():
    weak = standing(1, 5000.0, 5008.0, 1200.0)
    casts = [(0, (5000.0, 5008.0)), (10, (5000.0, 5008.0))]
    outcome = simulate(situation(weak), casts, lambda txt: 1000.0, companions={}, link=NO_LINK, explosion=NO_BLAST)
    assert 1 in outcome.deaths
    assert outcome.damage[1] == 1000.0 + 100.0 + 100.0  # the first blade, then two duplicates finish it
    assert outcome.deaths[1] <= 10  # on the first cast's way out; the second cast and the return find a corpse
    assert score(situation(weak), outcome)['kills'] == 1


def test_the_gate_matches_simulated_kills_to_recorded_ones():
    a = standing(1, 5000.0, 5008.0, 1200.0, death=8)
    b = standing(2, 5004.0, 5000.0, 1200.0, death=30)  # off the line: never hit
    sit = situation(a, b)
    sit.recorded_damage = 2400.0
    outcome = simulate(
        sit, [(0, (5000.0, 5008.0))], lambda txt: 1000.0, companions={}, link=NO_LINK, explosion=NO_BLAST
    )
    report = gate(sit, outcome)
    assert report['recorded_kills'] == 2
    assert report['simulated_kills'] == 1
    assert report['matched_kills'] == 1
    assert report['kills_only_recorded'] == 1
    assert report['kills_within_tolerance'] == 1.0
    assert report['damage_ratio'] == 0.5


def test_a_companion_wears_down_the_nearest_hostile_within_its_reach_and_moves_on():
    close, far = standing(1, 5004.0, 5000.0, 1000.0), standing(2, 5005.0, 5000.0, 10_000.0)
    merc = CompanionTrack(9, 338, dict.fromkeys(range(61), (5000.0, 5000.0)))
    sit = situation(close, far, companions=[merc])
    outcome = simulate(sit, [], lambda txt: 0.0, companions={338: (6.0, 100.0)}, link=NO_LINK)
    assert outcome.deaths[1] == 9  # 100 points a frame from frame 0: the tenth tick (frame 9) empties 1000
    assert outcome.companion_damage[1] == 1000.0
    assert outcome.companion_damage[2] == 100.0 * (60 - 9)  # the rest of the frames go to the next one
    assert outcome.damage == {}
    assert score(sit, outcome)['companion_damage_points'] == 1000 + 5100


def test_a_companion_out_of_reach_or_without_a_model_deals_nothing():
    far = standing(1, 5020.0, 5000.0, 1000.0)
    merc = CompanionTrack(9, 338, dict.fromkeys(range(61), (5000.0, 5000.0)))
    demon = CompanionTrack(10, 361, dict.fromkeys(range(61), (5019.0, 5000.0)))
    sit = situation(far, companions=[merc, demon])
    outcome = simulate(sit, [], lambda txt: 0.0, companions={338: (6.0, 100.0)}, link=NO_LINK)
    assert outcome.companion_damage == {}


def test_health_link_shares_damage_among_the_monsters_nearest_the_defiler():
    hit = standing(1, 5000.0, 5008.0, 100_000.0)
    linked = standing(2, 5010.0, 5000.0, 100_000.0)  # 10 units from the Defiler: linked
    beyond = standing(3, 5040.0, 5000.0, 100_000.0)  # 40 units: outside the aura
    defiler = CompanionTrack(9, 744, dict.fromkeys(range(61), (5000.0, 5000.0)))
    sit = situation(hit, linked, beyond, companions=[defiler])
    outcome = simulate(
        sit, [(0, (5000.0, 5008.0))], lambda txt: 1000.0, companions={}, link=(25.0, 5, 0.5), explosion=NO_BLAST
    )
    assert outcome.damage[1] == 1000.0 * (1 + 4 * DUPLICATE) * 2
    assert outcome.linked_damage == {2: outcome.damage[1] * 0.5}
    assert 3 not in outcome.linked_damage
    assert score(sit, outcome)['linked_damage_points'] == round(outcome.damage[1] * 0.5)


def test_the_return_leg_homes_on_where_the_character_stands_at_that_take_frame():
    # review.md (2026-10-10): the engine handed `cast` take frames where it asks for path indices, so the
    # blades flew home to where the character stood at frames 20-37 of the take, wherever the cast was.
    player = dict.fromkeys(range(41), (5000.0, 5000.0)) | dict.fromkeys(range(41, 120), (5100.0, 5000.0))
    target = MonsterTrack(1, 310, 1_000_000.0, dict.fromkeys(range(120), (5100.0, 5008.0)))
    sit = Situation(0, 119, 108, 2560 / 1418, player, {1: target}, [], 0.0)
    outcome = simulate(
        sit, [(41, (5100.0, 5008.0))], lambda txt: 100.0, companions={}, link=NO_LINK, explosion=NO_BLAST
    )
    frames = sorted(frame for frame, _ in outcome.dealt_by[1])
    assert outcome.contacts == 10  # five blades out, five back through the same monster
    assert frames[0] >= 41
    assert any(frame > 41 + OUT_FRAMES for frame in frames)  # the return leg came back past it


def test_companion_damage_is_shared_through_the_link_too():
    hit = standing(1, 5004.0, 5000.0, 100_000.0)  # beside the mercenary
    linked = standing(2, 5010.0, 5010.0, 100_000.0)
    merc = CompanionTrack(9, 338, dict.fromkeys(range(61), (5000.0, 5000.0)))
    defiler = CompanionTrack(8, 744, dict.fromkeys(range(61), (5000.0, 5000.0)))
    sit = situation(hit, linked, companions=[merc, defiler])
    outcome = simulate(
        sit, [], lambda txt: 0.0, companions={338: (6.0, 100.0)}, link=(25.0, 5, 0.5), explosion=NO_BLAST
    )
    assert outcome.companion_damage[1] == 100.0 * 61
    assert outcome.linked_damage[2] == 50.0 * 61


def test_a_monster_without_a_table_row_gets_the_area_level_points(tmp_path):
    directory = tmp_path / '20261009T000000Z-108'
    directory.mkdir()
    (directory / 'manifest.json').write_text(json.dumps({'area': 108}))
    frame = {
        't': 0.0, 'n': 1, 'late': 0, 'game': True, 'panels': [], 'macro': False,
        'p': [1, 1, 108, 5000.0, 5000.0, 0, 388],
        'm': [[7, 99999, 1, 5010.0, 5000.0, 128, 128, 0, 0xFFFFFFFF, 0]], 'x': [], 'in': [0, 0, 0, 0.5, 0.5, []],
        'rect': [1920, 0, 2560, 1418],
    }  # fmt: skip
    (directory / 'frames.jsonl').write_text(json.dumps(frame) + '\n')
    (directory / 'events.jsonl').write_text('')
    sit = cut(Take.load(directory))
    assert sit.monsters[7].points == 4637.0  # monlvl HP(H) at the area's level 85
    assert describe(sit)['unknown_types'] == 1


def test_a_death_marked_monster_takes_more_from_every_source_until_the_mark_ends():
    marked = standing(1, 5004.0, 5000.0, 1_000_000.0)  # beside the mercenary
    merc = CompanionTrack(9, 338, dict.fromkeys(range(61), (5000.0, 5000.0)))
    sit = situation(marked, companions=[merc])
    sit.marks = [(10, 1)]
    outcome = simulate(
        sit, [], lambda txt: 0.0, companions={338: (6.0, 100.0)}, link=NO_LINK, explosion=NO_BLAST, mark=(0.31, 20)
    )
    assert outcome.companion_damage[1] == 100.0 * 61  # the source's own points are unchanged
    assert round(outcome.mark_damage[1], 6) == round(31.0 * 21, 6)  # frames 10..30 inclusive take 31% more
    assert score(sit, outcome)['death_mark_points'] == 651
    dealt = dict(outcome.dealt_by[1])
    assert dealt[9] == 100.0
    assert round(dealt[10], 6) == 131.0
    assert dealt[31] == 100.0


def test_death_marks_are_read_from_the_key_presses_at_the_hostile_under_the_pointer(tmp_path):
    from inventory_tracking.macros.routines import screen_fraction

    directory = tmp_path / '20261009T000000Z-108'
    directory.mkdir()
    (directory / 'manifest.json').write_text(json.dumps({'area': 108, 'keys': {'40': 'd', '16': '7'}}))
    rect = [1920, 0, 2560, 1418]
    aspect = rect[2] / rect[3]
    from inventory_tracking.macros.world import Player

    fx, fy = screen_fraction(Player(1, '', 1, 108, 5000.0, 5000.0, None), 5010.0, 5004.0, aspect)
    near = [7, 310, 1, 5010.0, 5004.0, 128, 128, 0, 0xFFFFFFFF, 0]
    far = [8, 310, 1, 5030.0, 5000.0, 128, 128, 0, 0xFFFFFFFF, 0]
    frames = [
        {
            't': n * 0.04, 'n': n, 'late': 0, 'game': True, 'panels': [], 'macro': False,
            'p': [1, 1, 108, 5000.0, 5000.0, 0, 388], 'm': [near, far], 'x': [], 'rect': rect,
            'in': [rect[0] + fx * rect[2], rect[1] + fy * rect[3], 0, fx, fy, [40] if n == 2 else []],
        }
        for n in range(1, 4)
    ]  # fmt: skip
    events = [
        {'t': 0.08, 'event': 'keys', 'down': [40], 'up': []},
        {'t': 0.12, 'event': 'keys', 'down': [], 'up': [40]},
    ]
    (directory / 'frames.jsonl').write_text(''.join(json.dumps(f) + '\n' for f in frames))
    (directory / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
    sit = cut(Take.load(directory))
    assert sit.marks == [(2, 7)]
    assert describe(sit)['death_marks'] == 1


def test_a_hexed_monster_explodes_on_death_and_an_unhexed_one_does_not():
    hexed = standing(1, 5000.0, 5008.0, 1000.0)  # dies to the first blade
    neighbour = standing(2, 5006.0, 5008.0, 100_000.0)  # 6 units from the corpse, off the blades' line
    far = standing(3, 5020.0, 5008.0, 100_000.0)
    sit = situation(hexed, neighbour, far)
    outcome = simulate(
        sit, [(0, (5000.0, 5008.0))], lambda txt: 1000.0, companions={}, link=NO_LINK, explosion=(8.0, 400.0)
    )
    assert 1 in outcome.deaths
    assert outcome.explosion_damage == {2: 400.0}
    assert score(sit, outcome)['explosion_damage_points'] == 400

    killed_by_merc = standing(1, 5004.0, 5000.0, 1000.0)
    bystander = standing(2, 5008.0, 5000.0, 100_000.0)
    merc = CompanionTrack(9, 338, dict.fromkeys(range(61), (5000.0, 5000.0)))
    sit = situation(killed_by_merc, bystander, companions=[merc])
    outcome = simulate(sit, [], lambda txt: 0.0, companions={338: (6.0, 100.0)}, link=NO_LINK, explosion=(8.0, 400.0))
    assert 1 in outcome.deaths
    assert outcome.explosion_damage == {}  # never hit by a blade: no hex, no explosion


FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'cast_hits.json').read_text())


def test_a_situation_is_cut_from_a_take_and_replayed(tmp_path):
    directory = tmp_path / '20261009T212147Z-108'
    directory.mkdir()
    (directory / 'manifest.json').write_text(json.dumps(FIXTURE['manifest']))
    (directory / 'frames.jsonl').write_text(''.join(json.dumps(f) + '\n' for f in FIXTURE['frames']))
    (directory / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in FIXTURE['events']))
    (directory / 'missiles.jsonl').write_text(''.join(json.dumps(m) + '\n' for m in FIXTURE['missiles']))
    sit = cut(Take.load(directory))
    assert describe(sit)['casts'] == 1
    assert describe(sit)['monsters'] > 3
    assert isinstance(sit.casts[0], Cast)
    report = replay(sit, 'fitted')
    assert report['score']['contacts'] > 0
    assert report['score']['damage_points'] > 0
    assert set(report['gate']) >= {'recorded_kills', 'simulated_kills', 'damage_ratio'}


def test_the_situation_blocks_blades_at_flight_walls_unread_cells_and_closed_doors_not_walk_blocked_cells():
    from inventory_tracking.levels.doors import Door
    from inventory_tracking.levels.model import Ground, Walkable, pack_cells

    off = {'companions': {}, 'link': NO_LINK, 'explosion': NO_BLAST, 'mark': NO_MARK, 'mana': (0.0, 0.0, 0.0)}
    rows = ['.' * 25 + '#' + '.' * 54] * 40  # a wall one sub-tile thick at world x = 5005 (tiles 996-1012)
    bits = ''.join('0' if c == '#' else '1' for row in rows for c in row)
    wall = Walkable(996, 996, 16, 8, pack_cells(bits))
    behind = standing(1, 5010.0, 5000.0, 100_000.0)
    sit = situation(behind, frames=60)
    sit.ground = Ground((wall,))
    flown = simulate(sit, [(0, (5010.0, 5000.0))], lambda txt: 1000.0, **off)
    assert flown.contacts > 0  # a cell that blocks walking does not stop a blade (the takes of 2026-10-10 11:24)
    assert flown.blades_walled == 0
    sit.ground = Ground((Walkable(996, 996, 16, 8, bits and pack_cells('1' * len(bits)), pack_cells(bits)),))
    walled = simulate(sit, [(0, (5010.0, 5000.0))], lambda txt: 1000.0, **off)
    assert (walled.contacts, walled.blades_walled) == (0, 5)  # the flight layer's wall stops them
    sit.ground = Ground((Walkable(996, 996, 1, 8, pack_cells('1' * 200)),))  # the far room unread
    walled = simulate(sit, [(0, (5010.0, 5000.0))], lambda txt: 1000.0, **off)
    assert (walled.contacts, walled.blades_walled) == (0, 5)
    sit.ground = None
    sit.doors = {n: (Door(9, 15, 0, 5005.0, 5000.0),) for n in range(61)}  # a closed door instead
    walled = simulate(sit, [(0, (5010.0, 5000.0))], lambda txt: 1000.0, **off)
    assert (walled.contacts, walled.blades_walled) == (0, 5)
    sit.doors = {n: (Door(9, 15, 2, 5005.0, 5000.0),) for n in range(61)}  # opened
    opened = simulate(sit, [(0, (5010.0, 5000.0))], lambda txt: 1000.0, **off)
    assert opened.contacts > 0
    assert opened.blades_walled == 0
