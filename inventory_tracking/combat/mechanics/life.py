"""A hostile's life at full health for the decisions: its type's points in the area (at the Terror Zone's monster
level on a terrorized level, TZ_LEVEL_LIFE), times its Herald's tier (and its rank, on RANK_POINTS)
(rca/2026-10-21/herald-fight-findings.md §2 step 5, §3.0).

The forecasts of what the strikes kill and when (combat/stance.py `falls`), of what holding a place costs
(macros/safety.py `Pricing.holding`) and of a mark's worth (builds/warlock/mark.py) all start from a foe's points
(combat/policy.py `observe`). Until 2026-10-21 those were a plain monster's (`points_of`) whatever the monster: the
tier 5 Herald of 09:30:41 and its 14 Bramble Hulks were forecast to die in 0.36 s, holding beside them was priced at
28.5 life while they took 400-800 a second, and the safety fought out instead of a Teleport (5640 life, 7 potions,
lowest 35%). The arena's cut has had the boost since 2026-10-12 (tests/.../arena/cut.py `full_points`); this is the
same rule for the live decisions.

- rank: a leader (unique, champion, super unique: LEADER_FLAGS without MINION_FLAG) RANK_LIFE times its type's points,
  as macros/rotation.py ELITE_LIFE (a test holds them equal);
- Herald tier (stat 367, `Monster.tier`, the Herald and its minions alike): the Terror Zone config's
  `herald_health_boost_percent` for the Herald, `minion_health_boost_percent` for the rest of its pack
  (combat/data/tables.json `heralds`: T5 +2000% and +750%);
- the Terror Zone's monster level, with TZ_LEVEL_LIFE, on a terrorized level (`monster_level`): the character's
  level plus `boost_level` (2), within `bound_incl_min`..`bound_incl_max` (70..96), never under the monster's own
  level (the area's), monlvl's HP(H) at that level in place of the area's. The rule is the game's Terror Zone config
  (terror_zones/data/desecratedzones-game.json rotw hell defaults; its schema: "How many levels to add to player
  level to get the desecrated monster level", "If a monster's base level is higher than it will be used instead"),
  bundled as combat/data/tables.json `terror`. The client agrees: its Terror Zone entries read level 96 for Great
  Marsh (77) and the act 3 levels at character level 95 on 2026-10-21 (the probe.log of 20261021T055642Z-49f05219,
  "Terror Zone memory"); 'Terrorized: 95' at character level 93 (terror/tracker.py TERROR_LEVEL_BONUS, 2026-10-06).
  A monster's stat 12 in the client is its type's monstats Level(H) (80 for every Bramble Hulk of the 09:30 take,
  79 for the frogs, 81 for the vultures), not its level in the game: it says nothing of the zone.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from inventory_tracking.combat.mechanics.tables import area_level, points_of, tables
from inventory_tracking.game.layout import LEADER_FLAGS, MINION_FLAG


# The player, 2026-10-21 ~10:00, answering "fix the foe life model first, on its own switch?": "fix it first" (the
# life model shipped and measured before the Herald pack tactic). True: a foe's points carry its Herald's tier
# (`tier_boost`). False: the plain type's points, as before.
TIER_LIFE = True
# The rank in the points themselves (`foe_points`), so that the forecasts of what the strikes kill (combat/stance.py
# `falls`, macros/safety.py) count a leader's life too. Off (2026-10-21): it also raises what the aim and the stand are
# worth on every elite (the line policy weighs points), which moved 115 golden decisions of the 2026-10-10 takes
# (tests/inventory_tracking/scenarios/golden) where the tier alone moved none; that change of aim is a ruling of its
# own. False: the readers that want a leader's life multiply its points by RANK_LIFE themselves (`rank_share`:
# builds/warlock/mark.py `life_to_come`, macros/hunt.py the weapon swap's TOUGH_POINTS), as before.
RANK_POINTS = False
RANK_LIFE = 2.0  # a unique's or champion's life in Hell in its type's points (macros/rotation.py ELITE_LIFE)
# 2026-10-21 (the player: "start implementation for ready to build items without questions"; findings §3.0's third
# factor): on a terrorized level the decisions price a foe at the Terror Zone's monster level (`monster_level`), 96
# for this character at level 95, not the area's (Great Marsh 80: HP(H) 5585 for 4205, x1.33). It only raises a
# life, so the forecasts of what the strikes kill come later and holding beside a pack costs more. False: the
# area's level, as before.
TZ_LEVEL_LIFE = True


@dataclass
class ZoneSource:
    """What the service may attach (`attach`): whether a level is terrorized now (terror/tracker.py `terrorized`) and
    the character's level (stat 12). Unattached, a look's own hostiles tell a terrorized level (`evident`) and the
    character's level is taken as the one that puts the zone at its cap (the most life: the careful side)."""

    terrorized: Callable[[int], bool | None] | None = None
    player_level: Callable[[], int | None] | None = None


SOURCE = ZoneSource()


def attach(
    terrorized: Callable[[int], bool | None] | None = None, player_level: Callable[[], int | None] | None = None
) -> None:
    """The service's sources for `terrorized` and `zone_level` (None: unattached)."""
    SOURCE.terrorized, SOURCE.player_level = terrorized, player_level


def leader(flags: int) -> bool:
    """A pack's leader by its type flags: unique, champion or super unique, no minion."""
    return bool(flags & LEADER_FLAGS) and not flags & MINION_FLAG


def tier_boost(flags: int, tier: int) -> float:
    """The factor a Herald's tier puts on a life: the Herald's own boost for a leader, its minions' for the rest of
    the pack; 1 with no tier (or a tier the config does not hold)."""
    found = tables()['heralds'].get(str(tier)) if tier else None
    if found is None:
        return 1.0
    return 1.0 + found['life' if leader(flags) else 'minion_life'] / 100


def full_points(txt: int, area: int, flags: int = 0, tier: int = 0) -> float:
    """Life points at full health: the type's in the area (`points_of`), RANK_LIFE times for a leader, times the
    Herald's tier boost (`tier_boost`)."""
    return points_of(txt, area) * (RANK_LIFE if leader(flags) else 1.0) * tier_boost(flags, tier)


def foe_points(txt: int, area: int, flags: int = 0, tier: int = 0, level: int | None = None) -> float:
    """The points the decisions give a foe at full life: the type's (at monster level `level` when given, the
    area's otherwise: `monster_level`), times its rank with RANK_POINTS and its Herald's tier boost with TIER_LIFE."""
    rank = RANK_LIFE if RANK_POINTS and leader(flags) else 1.0
    return points_of(txt, area, level) * rank * (tier_boost(flags, tier) if TIER_LIFE else 1.0)


def terror() -> dict[str, Any]:
    """Hell's Terror Zone rule (combat/data/tables.json `terror`): `bound_min`, `bound_max`, `boost_level`, the
    forced `modifiers` (the always-unique-mod pool) and the `levels` a Terror Zone can hold."""
    return tables()['terror']


def evident(hostiles: Iterable[Any]) -> bool:
    """Whether a look's hostiles show a terrorized level: a Herald's tier (stat 367) on any, or a forced modifier
    (`terror()['modifiers']`) as the first of most plain ones (no type flags, no tier), the evidence terror/tracker.py
    counts (`saw`, `terrorized`). Outside a Terror Zone a plain monster carries no modifier and none a tier."""
    forced = frozenset(terror()['modifiers'])
    plain = marked = 0
    for m in hostiles:
        if getattr(m, 'tier', 0):
            return True
        if getattr(m, 'flags', 0) == 0:
            plain += 1
            modifiers = getattr(m, 'modifiers', ())
            marked += bool(modifiers) and modifiers[0] in forced
    return marked * 2 > plain


def terrorized(area: int, hostiles: Iterable[Any] = ()) -> bool:
    """Whether the decisions take `area` as terrorized now: a level a Terror Zone can hold, which the attached source
    says is terrorized or whose hostiles show it (`evident`). Either is enough: a wrong True only adds life."""
    if area not in terror()['levels']:
        return False
    said = SOURCE.terrorized(area) if SOURCE.terrorized is not None else None
    return bool(said) or evident(hostiles)


def zone_level(area: int, player_level: int | None = None) -> int | None:
    """The monster level of terrorized `area` in Hell: `player_level` (else the attached source's) plus
    `boost_level`, within `bound_min`..`bound_max`, never under the area's own; `bound_max` with no character level
    (the most it can be). None for an area without a level."""
    own = area_level(area)
    if own is None:
        return None
    rule = terror()
    if player_level is None and SOURCE.player_level is not None:
        player_level = SOURCE.player_level()
    raised = rule['bound_max'] if not player_level else player_level + rule['boost_level']
    return max(own, min(max(raised, rule['bound_min']), rule['bound_max']))


def monster_level(area: int, hostiles: Iterable[Any] = ()) -> int | None:
    """The monster level the decisions price `area`'s foes at (`foe_points`): the Terror Zone's with TZ_LEVEL_LIFE
    on a terrorized level (`terrorized`, `zone_level`), else None (the area's own)."""
    if not TZ_LEVEL_LIFE or not terrorized(area, hostiles):
        return None
    return zone_level(area)


def rank_share(elite: bool) -> float:
    """What a reader of `Foe.left` multiplies an elite's points by to get its life: 1 with RANK_POINTS (the rank is in
    the points already), else RANK_LIFE for an elite."""
    return RANK_LIFE if elite and not RANK_POINTS else 1.0
