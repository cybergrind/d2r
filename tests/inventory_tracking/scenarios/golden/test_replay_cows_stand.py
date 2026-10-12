"""Freezes the log of the replayed stand among the cows (battle/cows_stand.py), line by line: a refactor
that changes what the macro says there shows as a diff (framework-plan.md, Task 0.5). The rules are
today's: the stored log is what production does now when shown that recording, not the recorded log
(held against it in the last test).

GOLDEN_REGEN=1 rewrites the stored log instead of comparing with it.
"""

import functools
import json
import os
from pathlib import Path

from tests.inventory_tracking.scenarios.battle import cows_stand as battle, evidence
from tests.inventory_tracking.scenarios.battle.replay import Replay


GOLDEN = Path(__file__).parent / 'cows_stand.log.json'


def replayed() -> list[list]:
    replay = Replay(battle.FIXTURE, battle.script())
    replay.key_names = battle.key_names
    return [[round(line.at, 2), line.text] for line in replay.run(battle.END)]


@functools.cache
def once() -> tuple[tuple[float, str], ...]:
    return tuple((at, text) for at, text in replayed())


def test_the_replayed_battle_says_what_it_said():
    lines = [list(line) for line in once()]
    if os.environ.get('GOLDEN_REGEN') == '1':
        GOLDEN.write_text(json.dumps(lines, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        return
    stored = json.loads(GOLDEN.read_text(encoding='utf-8'))
    for index, (got, want) in enumerate(zip(lines, stored, strict=False)):
        assert got == want, f'first differing line is index {index}: replayed {got!r}, stored {want!r}'
    assert len(lines) == len(stored), f'{len(lines)} lines replayed, {len(stored)} stored'


def test_three_replays_say_the_same():
    first = [list(line) for line in once()]
    assert replayed() == first
    assert replayed() == first


def test_the_replay_fights_the_fight_of_the_record():
    # The macro's own lines of the stretch (the service's other lines, and the gold piles its reading of
    # the ground names, are not the fight's), held against the replay's as battle/evidence.py reads them.
    recorded = evidence.read(
        [
            (at, text)
            for at, text in battle.recorded()
            if battle.BEGAN - 0.01 <= at <= battle.END and text.startswith('Macro') and 'gold pile' not in text
        ]
    )
    played = [
        action
        for action in evidence.read([(at, text) for at, text in once() if at <= battle.END])
        if (action.kind, action.what) != ('press', 'hunt any')  # the replay's own start of the mode
    ]
    found = evidence.compare(recorded, played)
    # 60 recorded actions in 18.3 s: 53 are replayed in order, all five Blade Warps and the walk among
    # them, each to the place of the record; the seven others are the two lines about the potions the
    # script leaves out and five strikes' lines inside the 5.6 s in the herd, where the replay strikes
    # through other cows of the same crowd (nine lines of its own).
    assert len(recorded) == 60
    assert len(found.same) >= 53, found.table()
    moves = [(a.kind, a.what) for a, _ in found.same if a.kind in ('sweep', 'walk', 'landed', 'skill')]
    assert moves.count(('skill', 'Blade Warp')) == 5
    assert moves.count(('landed', '')) == 4  # the fifth lands after the stretch
    assert moves.count(('walk', '')) == 1
    assert found.off() <= 7.0  # world units between a recorded focal point or place and the replay's
