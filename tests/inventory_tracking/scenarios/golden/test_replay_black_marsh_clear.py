"""Freezes the log of the replayed quiet clear in Black Marsh (battle/black_marsh_clear.py), line by line: a refactor
that changes what the macro says there shows as a diff (framework-plan.md, Task 0.5). The rules are
today's: the stored log is what production does now when shown that recording, not the recorded log
(held against it in the last test).

GOLDEN_REGEN=1 rewrites the stored log instead of comparing with it.
"""

import functools
import json
import os
from pathlib import Path

from tests.inventory_tracking.scenarios.battle import black_marsh_clear as battle, evidence
from tests.inventory_tracking.scenarios.battle.replay import Replay


GOLDEN = Path(__file__).parent / 'black_marsh_clear.log.json'


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
    # 115 recorded actions in 31.4 s: 96 are replayed in order. The replay parts from the record in the
    # first six seconds (today's sweep jumps 1.0 s into the first fight, where that evening's struck on
    # for 1.5 s; an Engorge and the Sigil come in another order after it) and has no Engorge at 30.9 s;
    # between them every Blade Warp goes where the record's went. 94 since 2026-10-14: a key no longer waits out a
    # second for the key before once a look saw that one's cast (routines.quick_cast_over), so the record's "still on
    # the right button" lines of waits made then, and of none (a warp seconds old), are not said, and an Engorge
    # comes 3 s sooner (rca/2026-10-14/death-mark-engage.md §3).
    assert len(recorded) == 115
    assert len(found.same) >= 94, found.table()
    moves = [(a.kind, a.what) for a, _ in found.same if a.kind in ('sweep', 'walk', 'landed', 'skill', 'engorge')]
    assert moves.count(('skill', 'Blade Warp')) >= 8
    assert moves.count(('skill', 'Sigil: Lethargy')) >= 1
    # The record's Engorge (15.6 s) waited out the second after a Blade Warp; today's two come at 3.4 s and 19.6 s,
    # in no recorded place (2026-10-14): cast all the same
    assert sum(1 for action in played if action.kind == 'engorge') >= 1
