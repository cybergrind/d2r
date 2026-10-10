"""Echoing Strike's emulation (combat/mechanics) against one recorded cast (fixtures/cast_706.json:
42 frames of the second Chaos Sanctuary take, 2026-10-09, trimmed to the player, the pointer and
the five blades)."""

import json
import math
from pathlib import Path

from inventory_tracking.combat.mechanics.echoing_strike import (
    LIFE,
    OUT_FRAMES,
    RANGE,
    cast,
    errors,
    focal_point,
)
from inventory_tracking.combat.mechanics.validate import full_casts, validate


FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'cast_706.json').read_text())


def test_the_blades_spawn_ahead_converge_at_the_focal_point_turn_at_the_range_and_come_home():
    origin, focal = (5000.0, 5000.0), (5000.0, 5012.0)
    blades = cast(origin, focal, lambda frame: origin)
    assert len(blades) == 5
    starts = [b[0] for b in blades]
    assert all(abs(y - 5000.8) < 1e-9 for _, y in starts)  # AHEAD along the aim
    assert [round(x - 5000.0, 2) for x, _ in starts] == [1.9, 0.95, 0.0, -0.95, -1.9]  # across (left to right)
    at_focal = [min(math.dist(p, focal) for p in b) for b in blades]
    assert max(at_focal) < 0.6
    furthest = [max(math.dist(p, origin) for p in b) for b in blades]
    assert all(abs(f - RANGE) < 0.5 for f in furthest)  # the outer blades fly a little slanted
    assert all(math.dist(b[OUT_FRAMES], origin) == max(math.dist(p, origin) for p in b) for b in blades)
    assert all(len(b) == LIFE for b in blades)  # the return takes the whole life: they vanish beside the caster
    assert all(math.dist(b[-1], origin) < 2.0 for b in blades)


def test_the_focal_point_of_recorded_blades_is_where_they_converge():
    frames = FIXTURE['frames']
    (_, blades), *_ = full_casts(frames)
    focal = focal_point(blades)
    origin = (frames[8]['p'][3], frames[8]['p'][4])  # the cast frame: eight frames of pointer lead the fixture
    assert 8 < math.dist(focal, origin) < 20
    nearest = [min(math.dist(p, focal) for p in b[:OUT_FRAMES]) for b in blades]
    assert max(nearest) < 1.5


def test_the_emulation_follows_the_recorded_cast_within_a_unit_or_two():
    frames = FIXTURE['frames']
    (n, blades), *_ = full_casts(frames)
    by_n = {f['n']: f for f in frames}
    origin = (by_n[n]['p'][3], by_n[n]['p'][4])

    def player_at(k):
        later = by_n.get(n + k)
        return (later['p'][3], later['p'][4]) if later and later['p'] else origin

    out, back = errors(blades, origin, focal_point(blades), player_at)
    assert out < 1.3
    assert back < 2.5
    report = validate(frames, FIXTURE['manifest']['rect'])
    assert report['casts'] == 1
    assert report['fitted_focal']['out'] == round(out, 2)
    assert 0 < report['pointer_focal']['apart'] < 8.0  # the hand moves between the press and the blades


HITS = json.loads((Path(__file__).parent / 'fixtures' / 'cast_hits.json').read_text())


def test_contacts_name_the_monsters_the_blades_touch_and_the_recorded_drops_follow_them():
    from inventory_tracking.combat.mechanics.hits import contacts, match

    frames, rect = HITS['frames'], HITS['manifest']['rect']
    txt_ids = {m['unit_id']: m['txt_id'] for m in HITS['missiles']}
    found = contacts(frames, rect[2] / rect[3], txt_ids, focal='fitted')
    assert found, 'the fixture cast touches monsters'
    assert {leg for *_, leg in found} <= {'out', 'back'}
    assert all(HITS['manifest']['cast_frame'] <= k <= HITS['manifest']['cast_frame'] + LIFE for _, _, k, _ in found)
    frame_of = {f['t']: f['n'] for f in frames}
    report = match(found, HITS['events'], frame_of.get)
    assert report['contacts'] == len(found)
    assert report['contact_to_hit'] >= 0.75
    # Five other casts fly through the fixture's window with their blades cut out: their hits have no contact here.
    assert report['hit_from_contact'] >= 0.25


def test_a_blade_track_with_a_jump_is_left_out_of_the_validation():
    from inventory_tracking.combat.mechanics.validate import clean

    good = [(0.0, float(k)) for k in range(10)]
    bad = [*good[:5], (500.0, 500.0), *good[6:]]
    assert clean([good, bad]) == [good]


def test_a_blade_stops_at_a_wall_and_does_not_come_back():
    origin, focal = (5000.0, 5000.0), (5000.0, 5012.0)
    free = cast(origin, focal, lambda frame: origin)
    walled = cast(origin, focal, lambda frame: origin, blocked=lambda p: p[1] >= 5010.0)
    assert all(len(b) == LIFE for b in free)
    assert all(len(b) < 10 for b in walled)  # about nine units of flight before the wall
    assert all(max(p[1] for p in b) < 5010.0 for b in walled)
