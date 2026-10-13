"""Every situation the layer knows, with the variants worth looking at side by side: what the combat viewer's
Situations tab lists and export_viz.py plays (`python -m ...situations.export_viz --list`).

A situation here is a name, whether it was recorded or constructed, one line about it, and its variants in
order: (label, the `Situation`, its presses; None: the situation's own). The first variant is the base the
others are compared with. To add one: write the fixture (record.py `from_take`, then `dump`) or the builder
function, and give it an entry in `catalog()`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from tests.inventory_tracking.scenarios.arena.situations import example, vizier
from tests.inventory_tracking.scenarios.arena.situations.situation import Situation, held


Variant = tuple[str, Situation, list | None]
SEED = 3  # the seed of every exported run unless the command line says another


@dataclass(frozen=True)
class Entry:
    name: str
    kind: str  # 'recorded' or 'constructed'
    about: str
    variants: Callable[[], list[Variant]]
    fixture: str | None = None  # the fixture's file name, for a recorded one


def stall() -> list[Variant]:
    found = vizier.experiments()
    near, far = vizier.distanced(12), vizier.distanced(25)
    picked = [(name, *found[name]) for name in found if not name.startswith('(e) aware within')]
    picked += [(f'(d) the pack 12 off, {way}', *near[way]) for way in near]
    picked += [(f'(d) the pack 25 off, {way}', *far[way]) for way in far]
    return picked  # type: ignore[return-value]


def seal() -> list[Variant]:
    base = vizier.stored(vizier.SEAL)
    return [
        ('as recorded', base, None),
        ('attack mode alone', base, []),
        ('attack on + KP_4 every 1 s', base, [held('teleport', every=1.0)]),
        ('attack on + KP_4 every 0.3 s', base, [held('teleport', every=0.3)]),
    ]


def four_packs() -> list[Variant]:
    return [(name, situation, presses) for name, (situation, presses) in example.variants().items()]


def catalog() -> dict[str, Entry]:
    return {
        entry.name: entry
        for entry in (
            Entry(
                vizier.STALL,
                'recorded',
                'the Grand Vizier 57 units off, 48 KP_4 presses that moved nothing (09:06, 2026-10-13)',
                stall,
                f'{vizier.STALL}.json',
            ),
            Entry(
                vizier.SEAL,
                'recorded',
                "Vizier seal 1 opened, the Vizier's pack appears 0.95 s later (12:34, 2026-10-13)",
                seal,
                f'{vizier.SEAL}.json',
            ),
            Entry(
                'four-packs',
                'constructed',
                'four packs from four sides, a valuable drop, 30% life, attack mode on',
                four_packs,
            ),
        )
    }
