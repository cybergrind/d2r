"""A Death Mark that did not take is cast again (the player, 2026-10-20 ~18:45: "ok, recast"), played in the arena:
the Chaos Sanctuary's seal moment of test_replay.py, one seed whose play marks the elite 306 of the Vizier's pack, with
the arena's mark taking always or never (`Arena.mark_misses`; the takes of 2026-10-20: 26 of 397 keys on a live
target took nowhere). The arena shows the mark as the game's state words do (`Arena.unit_states`), and its hover
record names the monster under the pointer, which the mark goes on (macros/buffs.py AIM_CHECK)."""

import logging
import re
from collections import Counter
from itertools import pairwise

import pytest

from inventory_tracking.builds.warlock.mark import MARK_RECASTS
from inventory_tracking.macros import hunt
from tests.inventory_tracking.scenarios.arena import replay
from tests.inventory_tracking.scenarios.arena.game import Arena


SEED = 4  # the seal's play whose fight marks a leader (elite 306 at 8.3 s)
CAST = re.compile(r'^Macro: Death Mark on (.*\(\d+\)), \d+/\d+$')


def played(monkeypatch, caplog, misses: float) -> tuple[list[str], list[tuple[float, int | None]]]:
    """The seal's play with the mark missing `misses` of its keys: the macro's log lines and the arena's mark keys."""
    arenas: list[Arena] = []

    class Missing(Arena):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.mark_misses = misses
            arenas.append(self)

    monkeypatch.setattr(replay, 'Arena', Missing)
    # The recasts, not the bout's cast hold: the seal's Venom Lords (blows of 4-9k against 1818 life within 1.0 s) hold
    # every fight cast under the strike (macros/hunt.py FIGHT_CAST_REACH, 2026-10-22), so the play is staged without it
    # (rca/2026-10-23/arena-red.md, survival-findings.md §2)
    monkeypatch.setattr(hunt, 'FIGHT_CAST_REACH', False)
    staging = replay.stored(next(moment for moment in replay.MOMENTS if moment.name == 'vizier-seal'))
    assert staging is not None, 'stage it: python -m tests.inventory_tracking.scenarios.arena.replay --cut'
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        replay.played(staging, SEED)
    return [record.getMessage() for record in caplog.records], arenas[0].mark_keys


def test_a_mark_that_takes_is_cast_once_a_target(monkeypatch, caplog):
    lines, keys = played(monkeypatch, caplog, 0.0)
    casts = Counter(found.group(1) for line in lines if (found := CAST.match(line)))
    assert casts, 'the play marks a leader'
    assert all(count == 1 for count in casts.values()), casts
    assert [line for line in lines if 'did not take' in line] == []
    assert all(unit is not None for _, unit in keys)


@pytest.mark.parametrize('misses', [1.0])
def test_a_mark_that_never_takes_is_cast_again_recasts_times_and_said(monkeypatch, caplog, misses):
    lines, keys = played(monkeypatch, caplog, misses)
    casts = Counter(found.group(1) for line in lines if (found := CAST.match(line)))
    assert casts
    assert all(unit is None for _, unit in keys)
    assert max(casts.values()) <= 1 + MARK_RECASTS  # bounded, a target
    said = [line for line in lines if 'did not take' in line]
    assert said
    assert any(line.endswith('cast again (try 2)') for line in said)
    first = max(casts, key=casts.__getitem__)
    unit = first.rsplit('(', 1)[1].rstrip(')')
    # A target killed after its last try leaves nothing more to say (2026-10-22: with the arena's Might at level 16,
    # x2.9, the elite 306 died right after the third try; macros/hunt.py "the leader ... held is gone")
    if casts[first] == 1 + MARK_RECASTS and not any(f'leader {unit} held is gone' in line for line in lines):
        assert any(first in line and line.endswith('not cast again on it while the last would last') for line in said)
    # The key comes MARK_SHOWS (0.8 s) after the one before at the soonest: the check's window, then the skill's delay
    gaps = [later - before for (before, _), (later, _) in pairwise(keys)]
    assert min(gaps) >= 0.8
