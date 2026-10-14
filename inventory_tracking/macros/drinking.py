"""Drinking beside the fight: the belt key pressed while attack mode works (architecture.md §4.4).

The judgement is combat/survival.py's (`pressure`, `drink`); this keeps what it needs between two looks and
presses the key. `Drinker.look` is called from attack mode's own look at the game (hunt.py `sense`, every
pause of the mode), and looks at the life and the belt every EVERY seconds:

- the life of the last seconds is kept for the pressure;
- a potion gone from the belt since the last look was drunk, by this, by the player or by `make osd`: the
  time since is counted from it, so two drinkers do not each take one for the same blow;
- the potions on the ground within NEAR of the character count as supply;
- the key is the belt column's whose hotkey cell holds a potion of the kind asked for.

What stops a key of the macro's stops this one too (a key of the player's held, the focus lost), without
ending the mode: the drink is left for the next look. Nothing is pressed while a Shift key is down: Shift
and a belt key give the potion to the mercenary.
"""

import math
from collections import deque

from inventory_tracking.combat.survival import DrinkSettings, Pressure, Reading, Supply, drink, pressure
from inventory_tracking.common import LOG
from inventory_tracking.config import INPUT
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pad import DRINK_WATCH
from inventory_tracking.macros.world import HEALING, REJUVENATION, Loot
from inventory_tracking.models import PotionType
from inventory_tracking.native.layout import BELT_COLUMNS
from inventory_tracking.tracking.belt import potion_kind


EVERY = 0.2  # seconds between two looks at the life and the belt
KEPT = 6.0  # seconds of the life's history kept (survival.pressure's window is shorter)
NEAR = 20.0  # world units: a potion on the ground this near is at hand
GROUND = {HEALING: PotionType.HEALING, REJUVENATION: PotionType.REJUVENATION}
SHIFTS = (b'Shift_L', b'Shift_R')
NAMES = {PotionType.HEALING: 'Healing potion', PotionType.REJUVENATION: 'Rejuvenation potion'}
# Seconds from the healer's key for the mercenary (its ledger's stamp) within which a potion of that kind gone from the
# belt is taken for that one: the healer saw its potion leave the belt 0.17 to 0.19 s after its key (osd.log of
# 2026-10-14, 06:08:53.19 to 57.72, four potions), and this looks at the belt every EVERY.
GIVEN_WITHIN = 1.0


def on_belt(loot: Loot) -> dict[PotionType, int]:
    found = dict.fromkeys(PotionType, 0)
    for cell in loot.belt:
        kind = potion_kind(cell)
        if kind is not None:
            found[kind] += 1
    return found


def key_of(loot: Loot, kind: PotionType) -> str | None:
    """The belt key whose hotkey cell holds a potion of `kind`."""
    column = next((c for c in range(BELT_COLUMNS) if potion_kind(loot.belt[c]) == kind), None)
    return None if column is None else INPUT.column_keys[column + 1]


class Drinker:
    """The drinking of one hunt: its marks, and what it remembers between looks."""

    def __init__(self, settings: DrinkSettings | None = None) -> None:
        self.settings = settings or DrinkSettings()
        self.readings: deque[Reading] = deque()
        self.belt: dict[PotionType, int] | None = None
        self.drunk_at: dict[PotionType, float] = {}
        self.pressed_at: dict[PotionType, float] = {}  # clock time of the macro's own last key, by kind
        self.given: dict[PotionType, float] = {}  # the healer's last key for the mercenary counted, by kind
        self.last: Loot | None = None  # the loot of the last look (macros/supply.py reads the belt from it)
        self.looked_at = -math.inf
        self.busy = False
        # A belt key pressed in controller mode, watched for its cell emptying (macros/pad.py `Pad drink:`):
        # (key, kind, potions of the kind on the belt before, clock time of the key)
        self.pad_drink: tuple[str, PotionType, int, float] | None = None

    def look(self, run: Run, here: tuple[float, float] | None) -> PotionType | None:
        """One look: the potion drunk by it, if any. `here`: where the character stands, for what lies near."""
        now = run.clock()
        if self.busy or run.loot is None or not self.settings.enabled or now - self.looked_at < EVERY:
            return None
        self.looked_at = now
        loot = self.last = run.loot()
        if not loot.max_life or not loot.life:
            return None  # unread, or dead
        self.readings.append(Reading(now, float(loot.life), float(loot.max_life)))
        while now - self.readings[0].at > KEPT:
            self.readings.popleft()
        belt = on_belt(loot)
        self.watch_pad_drink(belt, now)
        for kind, count in belt.items():
            if self.belt is not None and count < self.belt[kind]:
                gone = self.belt[kind] - count - self.mercenarys(run, kind, now)
                if gone > 0:
                    self.drunk_at[kind] = now
        self.belt = belt
        felt = pressure(self.readings)
        near = [GROUND[drop.kind] for drop in loot.drops if drop.kind in GROUND and self.near(here, drop.x, drop.y)]
        supply = Supply(
            belt[PotionType.HEALING],
            belt[PotionType.REJUVENATION],
            near.count(PotionType.HEALING),
            near.count(PotionType.REJUVENATION),
        )
        since = {kind: now - at for kind, at in self.drunk_at.items()}
        kind = drink(felt, supply, since, self.settings)
        key = None if kind is None else key_of(loot, kind)
        if kind is None or key is None or self.shift_down(run):
            return None
        return kind if self.press(run, key, kind, loot, felt) else None

    def mercenarys(self, run: Run, kind: PotionType, now: float) -> int:
        """Of the potions of `kind` gone from the belt since the last look, how many the healer gave the mercenary
        (`Run.given`, its ledger): its key within GIVEN_WITHIN before now, each key counted once. Those do not hold
        back the character's (the game of 06:05 on 2026-10-14, run-0305-findings.md §5.5: three potions of the
        mercenary's kept the character at 67-70% without one for 7 s); the rest are taken for the character's."""
        given = run.given(kind) if run.given is not None else None
        if given is None or given == self.given.get(kind) or not 0.0 <= now - given <= GIVEN_WITHIN:
            return 0
        self.given[kind] = given
        LOG.info(
            "Macro: drink: a %s went to the mercenary %.2fs ago (the healer's): the character's own gap is kept",
            NAMES[kind], now - given,
        )  # fmt: skip
        return 1

    def watch_pad_drink(self, belt: dict[PotionType, int], now: float) -> None:
        """Whether a belt key acts in controller mode (rca/2026-10-13/controller-mode.md, plan step 8b): said
        once the cell has emptied, or once DRINK_WATCH has gone by without it."""
        if self.pad_drink is None:
            return
        key, kind, before, at = self.pad_drink
        if belt[kind] < before:
            LOG.info(
                'Pad drink: %s on %s in controller mode: the belt cell emptied within %.0f ms of the key',
                NAMES[kind], key, 1000 * (now - at),
            )  # fmt: skip
        elif now - at >= DRINK_WATCH:
            LOG.info(
                'Pad drink: %s on %s in controller mode: the belt unchanged %.1fs after the key',
                NAMES[kind], key, now - at,
            )  # fmt: skip
        else:
            return
        self.pad_drink = None

    @staticmethod
    def near(here: tuple[float, float] | None, x: float, y: float) -> bool:
        return here is not None and math.dist(here, (x, y)) <= NEAR

    @staticmethod
    def shift_down(run: Run) -> bool:
        keys = run.actuator.keys
        shifts = frozenset(keys.keycodes(list(SHIFTS)) or ())
        return bool(shifts & frozenset(keys.held_keys()))

    def press(self, run: Run, key: str, kind: PotionType, loot: Loot, felt: Pressure) -> bool:
        self.busy = True  # the key's hold is a pause of the mode, and the mode looks here in every pause
        try:
            run.actuator.tap(key)
        except Cancelled:
            raise
        except Abort as stop:
            if run.stops(stop):
                raise
            LOG.info('Macro: no %s on %s now: %s', NAMES[kind].lower(), key, stop)
            return False
        finally:
            self.busy = False
        self.drunk_at[kind] = self.pressed_at[kind] = run.clock()
        if run.pad is not None:
            self.pad_drink = (key, kind, on_belt(loot)[kind], run.clock())
        LOG.info(
            'Macro: %s on %s: life %d/%d, %.0f%% lost in the last seconds (%.0f%% a second, %.0f%% within one)',
            NAMES[kind], key, loot.life, loot.max_life, 100 * felt.lost, 100 * felt.rate, 100 * felt.burst,
        )  # fmt: skip
        run.say(NAMES[kind])
        return True
