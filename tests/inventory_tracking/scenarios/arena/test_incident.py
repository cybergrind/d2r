"""The incident comparison: how the recording's side is read, the band, and the stored incidents playing."""

import pytest

from tests.inventory_tracking.scenarios.arena.incident import (
    INCIDENTS,
    Row,
    Track,
    births,
    compare,
    played,
    quantile,
    stored,
)


BLADE = 706


def frame(t: float, *units: int, txt: int = BLADE) -> dict:
    return {'t': t, 'x': [[unit, txt, 0, 0.0, 0.0, ''] for unit in units]}


def test_blades_born_together_are_one_cast_and_a_later_birth_is_another() -> None:
    frames = [frame(0.0), frame(0.04, 1, 2), frame(0.08, 1, 2, 3), frame(0.5, 1, 2, 3, 4), frame(0.54, 4, 5)]
    assert births(frames, BLADE) == [0.04, 0.5]


def test_missiles_in_the_air_at_the_start_and_other_missiles_are_no_cast() -> None:
    assert births([frame(0.0, 1), frame(0.04, 1), frame(0.5, 9, txt=5)], BLADE) == []


def test_the_recording_inside_the_plays_band_is_inside_and_outside_it_says_by_how_much() -> None:
    assert Row('taken', 100.0, 50.0, 90.0, 150.0).verdict == 'inside'
    assert Row('taken', 1000.0, 50.0, 250.0, 600.0).verdict == 'outside: the arena has 0.25 of it'
    assert Row('strikes', 0.0, 2.0, 3.0, 3.0).verdict == 'outside'


def test_the_band_is_the_tenth_and_ninetieth_percentile_of_the_plays() -> None:
    plays = [Track((float(n),), (n,), (n,), float(n), float(n)) for n in range(11)]
    rows = compare(Track((5.0,), (20,), (0,), 5.0, 5.0), plays, (2.0,))
    assert [(row.what, row.low, row.median, row.high) for row in rows][:2] == [
        ('taken by 2 s', 1.0, 5.0, 9.0),
        ('alive at 2 s', 1, 5, 9),
    ]
    assert [row.inside for row in rows] == [True, False, False, True, True]
    assert quantile([3.0, 1.0, 2.0], 1.0) == 3.0


@pytest.mark.parametrize('incident', INCIDENTS, ids=lambda incident: incident.name)
def test_a_stored_incident_plays_a_track_at_every_mark(incident) -> None:
    # That the same seed gives the same track is the arena's, tested once (situations/test_situations.py
    # `test_the_example_plays_the_same_twice`).
    found = stored(incident)
    assert found is not None, 'cut it: python -m tests.inventory_tracking.scenarios.arena.incident --cut'
    scene, truth = found
    assert len(truth.taken) == len(truth.alive) == len(truth.strikes) == len(incident.marks)
    assert len(played(scene, incident, 3).taken) == len(incident.marks)
