"""harm_path prices every captured call bit for bit as the plain loop did (cleanup-plan.md phase 2, 2026-10-19).

The fixture holds 450 calls the arena plays made (tests/inventory_tracking/scenarios, 2026-10-19), sampled across
legs, deaths, guards, ground, draws, walls and stand-ins: each one's look (walls as the points that stopped a line),
path, settings, deaths and the sha256 of the repr of the Harm the code before the speed-up returned. A repr
compares every float exactly (0.0 against -0.0 too), so any reordered sum fails here. A deliberate change to the
pricing repins the digests: `uv run python -m tests.inventory_tracking.combat.test_harm_parity --repin`.
"""

import gzip
import hashlib
import pickle
import sys
from dataclasses import replace
from pathlib import Path

from inventory_tracking.combat.harm import harm_path


FIXTURE = Path(__file__).parent / 'fixtures' / 'harm_parity.pkl.gz'


def load() -> list[tuple]:
    with gzip.open(FIXTURE, 'rb') as f:
        return pickle.load(f)


def priced(call: tuple) -> str:
    seen, path, settings, deaths, walls, bars = call[:6]
    look = replace(
        seen,
        memo={},
        blocked=None if walls is None else walls.__contains__,
        barred=None if bars is None else bars.__contains__,
    )
    return hashlib.sha256(repr(harm_path(look, path, settings, deaths)).encode()).hexdigest()


def test_every_captured_call_prices_bit_for_bit_as_before():
    calls = load()
    assert len(calls) == 450
    differ = [(index, call[7]) for index, call in enumerate(calls) if priced(call) != call[6]]
    assert not differ, f'{len(differ)} of {len(calls)} calls price otherwise (index, mean before): {differ[:10]}'


def test_a_look_shared_by_calls_prices_as_a_fresh_one():
    """The look's memo (exposures, threat parts, lines of sight) only saves work: one memo across the calls of a
    look prices as a fresh memo for each."""
    calls = load()
    shared: dict = {}
    for call in calls:
        seen, path, settings, deaths, walls, bars = call[:6]
        look = replace(
            seen,
            memo=shared.setdefault((seen, walls, bars), {}),
            blocked=None if walls is None else walls.__contains__,
            barred=None if bars is None else bars.__contains__,
        )
        assert hashlib.sha256(repr(harm_path(look, path, settings, deaths)).encode()).hexdigest() == call[6]


if __name__ == '__main__' and sys.argv[1:] == ['--repin']:
    repinned = [(*call[:6], priced(call), call[7]) for call in load()]
    with gzip.open(FIXTURE, 'wb', compresslevel=9) as f:
        pickle.dump(repinned, f, protocol=pickle.HIGHEST_PROTOCOL)
