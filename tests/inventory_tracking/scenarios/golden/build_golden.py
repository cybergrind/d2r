"""Writes decisions.json: what every case of cases.py decides today.

    uv run --offline python -m tests.inventory_tracking.scenarios.golden.build_golden

Run it only to cut the net from a known base, or for a case added on purpose: a diff in the file is a
decision that changed (framework-plan.md, Task 0.2).
"""

import json
from pathlib import Path

from tests.inventory_tracking.scenarios.golden.cases import cases


GOLDEN = Path(__file__).with_name('decisions.json')


def recorded() -> dict[str, object]:
    return json.loads(GOLDEN.read_text())


def main() -> int:
    found = {case.name: case.run() for case in cases()}
    GOLDEN.write_text(json.dumps(found, indent=1, sort_keys=True) + '\n')
    print(f'{len(found)} cases written to {GOLDEN}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
