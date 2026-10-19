"""Freezes the log of the replayed Tower Cellar 5 battle, line by line: a refactor that changes what the macro
says shows as a diff (framework-plan.md, Task 0.3). The replays are battle/test_tower_cellar5.py's own (`said`,
one per rules and process): that file holds the same two plays against the recorded log."""

import json
import os
from pathlib import Path

import pytest

from tests.inventory_tracking.scenarios.battle.test_tower_cellar5 import said


HERE = Path(__file__).parent
# The rules as they were when the battle was recorded, and the rules of today: the first is held against
# the recorded log elsewhere (battle/test_tower_cellar5.py), the second is what a refactor must not change.
RULES = {
    'as_it_was': (True, HERE / 'tower_cellar5.log.json'),
    'today': (False, HERE / 'tower_cellar5.today.log.json'),
}


@pytest.mark.parametrize('rules', sorted(RULES))
def test_the_replayed_battle_says_what_it_said(rules):
    as_it_was, golden = RULES[rules]
    lines = [[round(at, 2), text] for at, text in said(as_it_was)]
    if os.environ.get('GOLDEN_REGEN') == '1':
        golden.write_text(json.dumps(lines, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        return
    stored = json.loads(golden.read_text(encoding='utf-8'))
    for index, (got, want) in enumerate(zip(lines, stored, strict=False)):
        assert got == want, f'first differing line is index {index}: replayed {got!r}, stored {want!r}'
    assert len(lines) == len(stored), f'{len(lines)} lines replayed, {len(stored)} stored'
