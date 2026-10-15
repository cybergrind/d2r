"""Freezes the log of the replayed Tower Cellar 5 battle, line by line: a refactor that changes what the macro
says shows as a diff (framework-plan.md, Task 0.3)."""

import json
import os
from pathlib import Path

import pytest

from tests.inventory_tracking.scenarios.battle import tower_cellar5 as battle
from tests.inventory_tracking.scenarios.battle.replay import Replay
from tests.inventory_tracking.scenarios.battle.test_tower_cellar5 import AS_IT_WAS, END


HERE = Path(__file__).parent
# The rules as they were when the battle was recorded, and the rules of today: the first is held against
# the recorded log elsewhere (battle/test_tower_cellar5.py), the second is what a refactor must not change.
RULES = {
    'as_it_was': (AS_IT_WAS, HERE / 'tower_cellar5.log.json'),
    'today': ({}, HERE / 'tower_cellar5.today.log.json'),
}


@pytest.mark.parametrize('rules', sorted(RULES))
def test_the_replayed_battle_says_what_it_said(rules):
    patches, golden = RULES[rules]
    replay = Replay(battle.FIXTURE, battle.script(patches=patches))
    replay.key_names = battle.key_names
    said = replay.run(END)
    lines = [[round(line.at, 2), line.text] for line in said]
    if os.environ.get('GOLDEN_REGEN') == '1':
        golden.write_text(json.dumps(lines, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        return
    stored = json.loads(golden.read_text(encoding='utf-8'))
    for index, (got, want) in enumerate(zip(lines, stored)):
        assert got == want, f'first differing line is index {index}: replayed {got!r}, stored {want!r}'
    assert len(lines) == len(stored), f'{len(lines)} lines replayed, {len(stored)} stored'
