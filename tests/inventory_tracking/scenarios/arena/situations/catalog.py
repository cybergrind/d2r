"""Every situation the layer knows, with the variants worth looking at side by side: what the combat viewer's
Situations tab lists and export_viz.py plays (`python -m ...situations.export_viz --list`).

A situation here is a name, whether it was recorded or constructed, one line about it, and its variants in
order: (label, the `Situation`, its presses; None: the situation's own). The first variant is the base the
others are compared with. To add one: write the fixture (record.py `from_take`, then `dump`) or the builder
function, and give it an entry in `catalog()`.

A variant named "...: today" and the next one named "...: new" are the same scene and the same presses played
by today's keys and by the pursuit loop (`Situation.logic('new')`: `BuildSettings.pursuit` on,
rca/2026-10-13/pursuit-v1.md), so Tab in the viewer flips between the two.
"""

from collections.abc import Callable
from dataclasses import dataclass

from tests.inventory_tracking.scenarios.arena.situations import cs_run, diablo, example, pocket, vizier
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


def both(label: str, situation: Situation, presses: list | None) -> list[Variant]:
    """The variant by today's keys and by the pursuit loop, side by side."""
    return [(f'{label}: today', situation, presses), (f'{label}: new', situation.logic('new'), presses)]


STALL_PAIRS = (  # the experiments of the stall played by both logics (vizier.py `experiments`)
    'as recorded (48 presses)',
    '(a) KP_4 held, every 0.3 s',
    '(a) attack mode on + KP_4 held, every 0.3 s',
    '(c) attack mode alone',
)


def stall() -> list[Variant]:
    found = vizier.experiments()
    near, far = vizier.distanced(12), vizier.distanced(25)
    picked: list = []
    for name in STALL_PAIRS:
        picked += both(name, *found[name])
    picked += both('(d) the pack 12 off, attack on + KP_4 every 0.3 s', *near['attack on + KP_4 every 0.3 s'])
    picked += both('(d) the pack 25 off, attack mode alone', *far['attack mode alone'])
    picked += [
        (name, *found[name]) for name in found if name not in STALL_PAIRS and not name.startswith('(e) aware within')
    ]
    picked += [(f'(d) the pack 12 off, {way}', *near[way]) for way in near if way != 'attack on + KP_4 every 0.3 s']
    picked += [(f'(d) the pack 25 off, {way}', *far[way]) for way in far if way != 'attack mode alone']
    return picked  # type: ignore[return-value]


def seal() -> list[Variant]:
    base = vizier.stored(vizier.SEAL)
    return [
        *both('as recorded', base, None),
        *both('attack mode alone', base, []),
        *both('attack on + KP_4 every 1 s', base, [held('teleport', every=1.0)]),
        *both('attack on + KP_4 every 0.3 s', base, [held('teleport', every=0.3)]),
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
                pocket.POCKET,
                'recorded',
                'the empty staff: 26 KP_4 presses back and forth by a walled pocket, the seal 270 units west '
                '(13:05, 2026-10-13)',
                pocket.pocket_variants,
                f'{pocket.POCKET}.json',
            ),
            Entry(
                pocket.PACK,
                'recorded',
                'a pack by Vizier seal 1: KP_4 mashed 16 times, the first strike 7.1 s after the landing '
                '(09:06, 2026-10-13)',
                pocket.pack_variants,
                f'{pocket.PACK}.json',
            ),
            Entry(
                'four-packs',
                'constructed',
                'four packs from four sides, a valuable drop, 30% life, attack mode on',
                four_packs,
            ),
            Entry(cs_run.NAME, 'recorded', cs_run.ABOUT, cs_run.variants, f'{cs_run.NAME}.json'),
            Entry(diablo.NAME, 'recorded', diablo.ABOUT, diablo.variants, f'{diablo.NAME}.json'),
        )
    }
