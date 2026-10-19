"""Drinking beside the fight: the belt key pressed while attack mode works (architecture.md §4.4).

The judgement is combat/survival.py's; this keeps the state between looks and presses the key. `Drinker.look` runs
in attack mode's every pause (hunt.py `sense`), at most every EVERY seconds. A potion gone from the belt counts as
drunk whoever drank it (this, the player, `make osd`), so two drinkers do not each take one for the same blow; before
its key the potion is claimed in the healer's ledger. A stopped key (player's key held, focus lost) leaves the drink
for the next look. Nothing is pressed with Shift down: Shift and a belt key feed the mercenary.
"""

import math
from collections import deque

from inventory_tracking.automation.ledger import Claim
from inventory_tracking.combat.survival import DrinkSettings, Pressure, Reading, Supply, drink, pressure
from inventory_tracking.common import LOG
from inventory_tracking.config import INPUT
from inventory_tracking.game.records import HEALING, REJUVENATION, Loot
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.pad import DRINK_WATCH
from inventory_tracking.models import Actor, PotionType
from inventory_tracking.native.layout import BELT_COLUMNS
from inventory_tracking.tracking.belt import potion_kind


EVERY = 0.2  # seconds between two looks at the life and the belt
KEPT = 6.0  # seconds of the life's history kept (survival.pressure's window is shorter)
NEAR = 20.0  # world units: a potion on the ground this near is at hand
GROUND = {HEALING: PotionType.HEALING, REJUVENATION: PotionType.REJUVENATION}
SHIFTS = (b'Shift_L', b'Shift_R')
NAMES = {PotionType.HEALING: 'Healing potion', PotionType.REJUVENATION: 'Rejuvenation potion'}
# Seconds after the healer's key for the mercenary within which a potion gone from the belt is taken for that one (it
# leaves the belt 0.17-0.19 s after the key, osd.log 2026-10-14)
GIVEN_WITHIN = 1.0
# Seconds after the healer's key for the character within which the macro leaves the blow to it: that leave time plus
# one look (two potions for one blow, rca/2026-10-14/run-1932-findings.md issue 2)
STAND_OFF = 0.5


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
        # A belt key pressed in controller mode, watched for its cell emptying:
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
        return kind if self.take(run, key, kind, loot, felt) else None

    def take(self, run: Run, key: str, kind: PotionType, loot: Loot, felt: Pressure) -> bool:
        """Claim the potion and press its key; whether it went out. A claim whose key did not go out is given back."""
        claim = self.claim(run, kind, run.clock())
        if claim is not None and not claim.taken:
            return False
        if self.press(run, key, kind, loot, felt):
            return True
        if claim is not None and run.ledger is not None:
            run.ledger.unclaim(Actor.PLAYER, kind, claim)
        return False

    def claim(self, run: Run, kind: PotionType, now: float) -> Claim | None:
        """One drinker per blow: claim the character's potion of `kind` in the healer's ledger, so `make osd` stands
        off; refused while the healer's own key for it is younger than STAND_OFF or the healer is pressing. None: no
        ledger, the key goes out."""
        if run.ledger is None:
            return None
        found = run.ledger.claim(Actor.PLAYER, kind, now, within=STAND_OFF)
        if not found.taken:
            LOG.info("Macro: drink: the healer has this blow's %s: %s; no key", NAMES[kind].lower(), found.why)
        elif found.why:
            LOG.info('Macro: drink: %s', found.why)
        return found

    def mercenarys(self, run: Run, kind: PotionType, now: float) -> int:
        """How many of the potions of `kind` gone since the last look the healer gave the mercenary (its key within
        GIVEN_WITHIN, each key counted once). Those do not hold back the character's
        (rca/2026-10-14/run-0305-findings.md §5.5)."""
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
        """Log whether a belt key acts in controller mode (rca/2026-10-13/controller-mode.md): once the cell has
        emptied, or after DRINK_WATCH without it."""
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
        self.busy = True  # the key's hold is a pause of the mode, which looks here in every pause
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
