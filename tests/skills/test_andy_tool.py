"""The Andariel tool (the d2-loop-watch skill's tools/andy.py): a Baal game's legs (macros/loop.py `baal_leg`,
2026-10-25) are neither Andariel's nor Lower Kurast's play, the trip legs it shares included."""

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.agents' / 'skills' / 'd2-loop-watch' / 'tools'))
andy = importlib.import_module('andy')


def leg(clock: str, number: int, name: str) -> str:
    return f'2026-10-25 {clock},000 INFO Macro: Loop: game {number}, {name}\n'


def test_a_baal_games_legs_are_baal_play_and_its_trip_legs_keep_the_kind(tmp_path):
    (tmp_path / 'probe.log').write_text(
        '2026-10-25 12:59:59,000 INFO Macro: Loop run: Baal\n'
        + leg('13:00:00', 1, 'to the Worldstone Keep')
        + leg('13:00:10', 1, 'down the Worldstone Keep')
        + leg('13:01:00', 1, 'to town for room')
        + leg('13:01:05', 1, 'back through the portal')
        + leg('13:01:10', 1, "the Throne's waves")
        + leg('13:03:00', 1, 'Baal')
        + leg('13:04:00', 2, 'to the Catacombs')  # the kind switched: Andariel's from here
        + leg('13:04:10', 2, 'to town for room')
    )
    runs = [(event.data[1], event.run) for event in andy.parse(tmp_path) if event.kind == 'leg']
    assert runs == [
        ('to the Worldstone Keep', 'baal'),
        ('down the Worldstone Keep', 'baal'),
        ('to town for room', 'baal'),
        ('back through the portal', 'baal'),
        ("the Throne's waves", 'baal'),
        ('Baal', 'baal'),
        ('to the Catacombs', 'andariel'),
        ('to town for room', 'andariel'),
    ]


def test_the_baal_legs_are_the_loops():
    from inventory_tracking.macros import loop

    legs = {loop.TO_THE_KEEP, loop.DOWN_THE_KEEP, loop.FIGHT_THRONE, loop.TO_THE_CHAMBER, loop.FIGHT_BAAL}
    assert legs | {loop.TO_HARROGATH} == andy.BAAL_LEGS
