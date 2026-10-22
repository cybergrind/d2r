"""The stash has one record (inventory_tracking/game/stash.py `Stash`): no module reads the stash's memory but through
it, no copy of its full stacks is kept in a file, and its numbers are defined there alone.

The player, 2026-10-22: "we need some generic approach to check stash - one object that is used everywhere, updated
every time we're in town/after each interaction with stash / no hardcoded, no copies, no stale records / make sure
that we have no places that interact with anything but it". The stale copy (runs/alt-d/full-stacks.json) left an
Eastern Worldstone Shard on the ground at 08:59:26 (rca/2026-10-22/eastern-shard-findings.md).
"""

import io
import os
import re
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'inventory_tracking'
TOOLS = ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'
STASH = PACKAGE / 'game' / 'stash.py'


SKIPPED = frozenset(('runs', '__pycache__', 'data'))  # the service's logs and the data files: no code


def sources(*roots: Path) -> list[Path]:
    found = []
    for root in roots:
        for folder, folders, files in os.walk(root):
            folders[:] = [name for name in folders if name not in SKIPPED]
            found.extend(Path(folder) / name for name in files if name.endswith('.py'))
    return sorted(found)


def code_lines(path: Path) -> list[tuple[int, str]]:
    """(line number, the line's code) with comments and strings blanked: what the module does, not what it says."""
    text = path.read_text()
    lines = text.splitlines()
    blank: dict[int, list[tuple[int, int]]] = {}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type in (tokenize.COMMENT, tokenize.STRING):
            (row, col), (end_row, end_col) = token.start, token.end
            for line in range(row, end_row + 1):
                start = col if line == row else 0
                end = end_col if line == end_row else len(lines[line - 1])
                blank.setdefault(line, []).append((start, end))
    found = []
    for number, line in enumerate(lines, 1):
        chars = list(line)
        for start, end in blank.get(number, ()):
            chars[start:end] = ' ' * (end - start)
        found.append((number, ''.join(chars)))
    return found


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def test_the_raw_stash_read_is_reached_only_through_the_stash_record():
    # GameMemory.read_stash (game/memory.py) is handed only to the record (`Stash.attach` / `Stash.read`); its decode
    # (game/decode.py `stash_view_of`) is the memory's alone
    wrong = []
    for path in sources(PACKAGE, TOOLS):
        for number, line in code_lines(path):
            raw = re.search(r'\bread_stash\b', line) and path != PACKAGE / 'game' / 'memory.py'
            if raw and not re.search(r'stash\.(attach|read)\(', line):
                wrong.append(f'{rel(path)}:{number}: {line.strip()}')
            if 'stash_view_of' in line and path.name not in ('decode.py', 'memory.py'):
                wrong.append(f'{rel(path)}:{number}: {line.strip()}')
    assert wrong == []


def test_no_module_keeps_a_file_of_the_stash_but_the_records_snapshot():
    # The full stacks' file is gone; the snapshot (game/stash.py SNAPSHOT) is written by the record and read by the
    # watch tools, never written by them
    wrong = []
    for path in sources(PACKAGE, TOOLS):
        text = path.read_text()
        if re.search(r"""['"]full-stacks\.json['"]|FULL_FILE""", text):
            wrong.append(f'{rel(path)}: full-stacks.json')
        if path != STASH and re.search(r"""['"]stash\.json['"]""", text) and path.parent != TOOLS:
            wrong.append(f'{rel(path)}: its own stash.json')
    for path in sources(TOOLS):
        if re.search(r'STASH_SNAPSHOT\)\.write|write_text\(.*stash', path.read_text()):
            wrong.append(f'{rel(path)}: writes the snapshot')
    assert wrong == []


def test_the_stash_numbers_are_defined_in_the_stash_module_alone():
    names = ('STACK_MOST', 'RUNES_AIM', 'SHARD_FLOOR', 'STACK_ROOM', 'BANK_STAT', 'GOLDBANK')
    wrong = []
    for path in sources(PACKAGE):
        if path == STASH:
            continue
        for number, line in code_lines(path):
            if re.match(rf'\s*({"|".join(names)})\s*(:[^=]+)?=', line):
                wrong.append(f'{rel(path)}:{number}: {line.strip()}')
    assert wrong == []


def test_no_literal_stack_limit_beside_a_stack_or_count():
    # 99 (the cap), 90 and 80 (the player's floor and aim) as a number on a line about a stack or a count: the stash
    # module's names instead (game/stash.py)
    words = re.compile(r'\b(count|counts|stack|stacks|stacked)\b', re.IGNORECASE)
    wrong = []
    for path in sources(PACKAGE / 'macros', PACKAGE / 'loot', PACKAGE / 'game'):
        if path == STASH:
            continue
        for number, line in code_lines(path):
            if words.search(line) and re.search(r'(?<![\w.])(99|90|80)(?![\w.])', line):
                wrong.append(f'{rel(path)}:{number}: {line.strip()}')
    assert wrong == []
