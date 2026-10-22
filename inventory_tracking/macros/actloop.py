"""The shard act loop: a game's act terrorized by a Worldstone Shard in the Fortress, then played zone by zone, its boss
first (routes/act-terrorize-plan.md; rca/2026-10-20/act-terrorize-findings.md). The player, 2026-10-20 ~18:50:
"terrorize with worldstone shards whole act and go whole act, zone by zone ... we want to kill act boss first for
possible statue drop"; ~19:25: "yes, let's do act 4 mode".

An agenda kind (macros/tzloop.py): `shard_goal` puts the shard first in a game (the visit first when it is due: room
for the shard), `use_shard` makes it (macros/terrorize.py) and records the act terrorized on the agenda, which
`tzloop.zone_of` then plans with the rotation (tzroutine.py `itinerary`: the act first, Diablo's trip first). No shard
at the floor, or a failed use: TZ+ on the rotation that game (the coordinator's accepted answer, 2026-10-20). Offered
(loop.py `loop_kinds`) only with ENABLED.

Shards over the limit (`OVERFLOW`, 2026-10-21): after the kind's own shard, a shard of another act whose stack is at
the stash's cap is used too (`overflow`: at the shard step, and at each later town visit of the game, tzloop.py
`perform`), carried ones first; its act is played after the acts before it (`Agenda.acts` in order), its time added to
the game's cap (loop.py `Loop.allowed_seconds`). A refused use is said and left: the shard stays carried or is stashed
again, the kind's own shard and the game untouched.
"""

from collections.abc import Iterable

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, StashView, World
from inventory_tracking.macros import terrorize as hands  # `hands.CLICKS` read at the call
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.agenda import ERRAND, PANDEMONIUM_FORTRESS, TERRORIZE, WAYPOINT, Agenda, Objective
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.terrorize import (
    SHARD_FLOOR,
    SHARDS,
    choose_shard,
    name_of,
    over_limit,
    stacks_said,
    terrorize,
    use_carried,
)
from inventory_tracking.macros.travel import cut


# The act kind "Shard: Act 4" offered (the picker's entry). On 2026-10-20 ~21:18 after the player's in-game test
# (findings §6) with terrorize.CLICKS on. False: the kind is not offered
ENABLED = True
# The kinds' acts by kind key (loop.py ACT_KINDS: act1 ... act5, each offered once its script is ready, macros/acts/)
ACTS = {f'act{act}': act for act in range(1, 6)}
# The shard step's outcomes in a game (`Agenda.shard`); an overflow act's (`Agenda.overflow`): USED, REFUSED (the
# right click did not take: an act terrorized already, 15:08:41 on 2026-10-21), FAILED (a stop)
USED, NONE_HELD, CLICKS_OFF, FAILED, GIVEN_UP, JOINED, REFUSED = (
    'used',
    'none at the floor',
    'clicks off',
    'failed',
    'given up',
    'joined',
    'refused',
)
# Games in a row whose shard did not take, after which the kind plays the rotation only (said each game) until the
# service restarts: no shard more is risked on clicks that do not work
SHARD_FAILURES = 2
# Shards over the limit (2026-10-21). The player, ~15:22: "let's implement another strategy for worldstone shards that
# are 99 (like north shard) - if we engounter such stone - we just use it, so our game turns into clearing act 5 after
# the act 3"; then "only for shards that are over the limit". Over the limit: its Materials-tab stack at the stash's
# cap, one more cannot be stored (terrorize.py `over_limit`: game/layout.py STACK_MOST 99, game/records.py
# `StashView.full`; the stash view of 15:08:10 named the Western, Eastern and Northern shards full). Such a shard of
# another act than the kind's is used in an act kind's game after the kind's own, its act played after the acts before
# it. A shard under the cap is used only by its own act kind, at SHARD_FLOOR. False: the kind's own shard only
OVERFLOW = True
# Overflow acts a game at most (None: every act over the limit). Three stacks stood at the cap at 15:08:10 and each
# act's drops refill its stack within a game: with no bound every game would terrorize four acts (~4 h). The player's
# case is one act ("act 5 after the act 3"); the acts after the kind's are taken first (act 3: 4, 5, 1, 2)
OVERFLOW_MOST: int | None = 1
# Not played for an overflow: the kind's game states, where no shard is risked (`overflow`)
NO_OVERFLOW = frozenset((None, JOINED, GIVEN_UP, CLICKS_OFF))
# A shard on the ground whose stack is full is picked up while the game's overflow slot is free, and used at the next
# town stop (`picked_shards`; running/valuables.py `_picked`). The player, 2026-10-21 ~15:55: "Pick up and use"; "One
# extra act". False: a full stack's shard is left on the ground, as every full stack's material (15:32:20: a Northern
# left in the Catacombs)
PICK_OVER_LIMIT = True
# Every Worldstone Shard on the ground is picked up, its stack full or not (running/valuables.py `_picked`, so the
# leave-game guard holds the game for it too): the stash or the overflow use decides after, in town. The player,
# 2026-10-22 ~09:05: "we didn't pickup eastern shard ... I expected it to be picked up for stash (not 99 yet) or used
# to terrorize whole zone"; the rulings: dropped shards are always taken, stashed when the extra act is used. A shard
# of a full stack that no overflow uses is put down in town by the visit, as every full stack's material (visit.py
# `_material`). False: PICK_OVER_LIMIT's rule alone (a full stack's shard left outside an act kind's free slot)
SHARD_ALWAYS_PICKED = True
# The kinds with no act of their own whose games use a picked-up shard over the limit too (`overflow`): TZ leveling.
# The coordinator, 2026-10-22, on the rulings "Overflow shards: one extra act; pick up and use" and the player's "I
# expected it to be picked up for stash (not 99 yet) or used to terrorize whole zone": in TZ leveling a carried shard
# whose stack is full terrorizes its act at the next town stop while the game's extra-act slot (OVERFLOW_MOST) is
# free, its act played after the zone's levels (tzloop.py `zone_of`); with the slot taken the visit puts it down, as
# in an act kind. Only a carried one: a TZ leveling game never takes a shard out of its stack (the act kinds do,
# `overflow_due`). Before this, the overflow ran in the act kinds alone (22:27:44 on 2026-10-21 was "Shard: Act 3").
# Empty: as before
OVERFLOW_KINDS = frozenset(('tz',))


def act_of(kind) -> int | None:
    """The act a kind terrorizes; None for any other kind."""
    return ACTS.get(kind.key)


def shard_goal(world: World, loop) -> Objective | None:
    """The shard's goal first in a game of an act kind: the waypoint to the Fortress, then TERRORIZE; None once tried in
    this game, for another kind, out of town (a game joined mid-way: not known), or while the visit is due (room)."""
    act = act_of(loop.kind)
    agenda, player = loop.agenda, world.player
    if act is None or agenda.shard is not None or player is None:
        return None
    if not player.in_town:
        agenda.shard = JOINED
        LOG.info('Macro: act: the game is joined in a field level: no shard, the zones read are played')
        return None
    if agenda.shard_failures >= SHARD_FAILURES:
        agenda.shard = GIVEN_UP
        LOG.info('Macro: act: the shard did not take %d games in a row: TZ+ on the rotation until a restart',
                 agenda.shard_failures)  # fmt: skip
        return None
    if loop.visit_due(world.game_name):
        return None  # the visit first: it makes the room the shard needs
    if player.area != PANDEMONIUM_FORTRESS:
        return Objective(WAYPOINT, 'to the Fortress for the shard', ERRAND, to=PANDEMONIUM_FORTRESS)
    return Objective(TERRORIZE, f'a Worldstone Shard for act {act}', ERRAND, PANDEMONIUM_FORTRESS)


def use_shard(loop, run: Run, terrorized, inventory_key: str | None = None) -> None:
    """TERRORIZE: the act's shard used (terrorize.py), the outcome on the agenda; a confirmed use adds the act to the
    game's acts, first. Nothing used: TZ+ on the rotation this game, said. Then the shards over the limit
    (`overflow`)."""
    own_shard(loop, run, terrorized, inventory_key)
    overflow(loop, run, terrorized, inventory_key)


def own_shard(loop, run: Run, terrorized, inventory_key: str | None = None) -> None:
    """The kind's own act's shard (`use_shard`)."""
    agenda, act = loop.agenda, act_of(loop.kind)
    assert act is not None
    view = run.reads.stash_view()
    if choose_shard(view, act) is None:
        agenda.shard = NONE_HELD
        LOG.info('Macro: act: no shard for act %d at %d or more (%s): TZ+ on the rotation this game', act,
                 SHARD_FLOOR, stacks_said(view))  # fmt: skip
        run.say(f'Act {act}: no shard at {SHARD_FLOOR}+: TZ+')
        return
    if not hands.CLICKS:
        agenda.shard = CLICKS_OFF
        LOG.info('Macro: act: terrorize.CLICKS is off: TZ+ on the rotation this game')
        return
    agenda.shard = FAILED  # tried once a game, whatever stops it (a stash out of sight)
    try:
        used = terrorize(run, inventory_key, act, terrorized)
    except Hand:
        agenda.shard = None  # the player's hand: tried again at the next leg
        raise
    except Abort:
        agenda.shard_failures += 1
        raise
    if used is not None and used.confirmed:
        agenda.shard, agenda.acts, agenda.shard_failures = USED, played((used.act, *agenda.acts), act), 0
        LOG.info('Macro: act: act %d terrorized by a %s: its levels are played, the boss first', used.act,
                 name_of(used.shard))  # fmt: skip
        return
    agenda.shard_failures += 1
    LOG.info('Macro: act: the shard did not take (%s): TZ+ on the rotation this game (%d of %d)',
             'nothing used' if used is None else 'gone, the stack not one lower' if used.gone else 'still carried',
             agenda.shard_failures, SHARD_FAILURES)  # fmt: skip


def played(acts: Iterable[int], own: int | None) -> tuple[int, ...]:
    """`acts` in the order they are played: the kind's own act (`own`) first, the others as they came, each once."""
    ordered = tuple(dict.fromkeys(acts))
    return (own, *(act for act in ordered if act != own)) if own in ordered else ordered


def overflow_due(
    view: StashView | None,
    agenda: Agenda,
    own: int | None,
    carried: Iterable[Carried] = (),
    *,
    carried_only: bool = False,
) -> tuple[tuple[int, Carried | None], ...]:
    """Pure. The overflow uses due now (`OVERFLOW`): each act of a shard over the limit (`over_limit`) but the kind's
    own (`own`), not terrorized and not tried in this game, with the carried shard of it to use (the inventory's
    first, then the cube's; None: one from its stack); the acts after `own` first (act 3: 4, 5, 1, 2), at most
    OVERFLOW_MOST played a game. () with the switch off or the stash unread. `carried_only`: only the acts of a carried
    shard (a TZ leveling game, OVERFLOW_KINDS), so one with none carried does not take the slot from one carried."""
    if not OVERFLOW:
        return ()
    held = tuple(carried)
    due = sorted(
        (SHARDS[shard], shard)
        for shard in over_limit(view)
        if SHARDS[shard] != own
        and SHARDS[shard] not in agenda.acts
        and SHARDS[shard] not in agenda.overflow
        and (not carried_only or any(item.txt == shard for item in held))
    )
    due.sort(key=lambda pair: (pair[0] - (own or 0)) % len(SHARDS))  # no own act (OVERFLOW_KINDS): act 1 first
    left = len(due) if OVERFLOW_MOST is None else max(OVERFLOW_MOST - len(overflow_played(agenda)), 0)
    return tuple((act, next((item for item in held if item.txt == shard), None)) for act, shard in due[:left])


def overflow_played(agenda: Agenda) -> tuple[int, ...]:
    """The acts of shards over the limit terrorized in this game, in their order (`Agenda.acts`)."""
    return tuple(act for act in agenda.acts if act in agenda.overflow)


def picked_shards(loop) -> frozenset[int]:
    """The shard classes picked up from the ground though their stack is full (`PICK_OVER_LIMIT`): in an act kind's
    game after its own shard step, the overflow slot free (OVERFLOW_MOST), not at the game's end (loop.py `done`),
    each shard of an act neither terrorized nor tried in this game. Empty otherwise (today's: left on the ground)."""
    agenda, kind = getattr(loop, 'agenda', None), getattr(loop, 'kind', None)  # a bare loop: no act kind's game
    own = act_of(kind) if kind is not None else None
    if not (OVERFLOW and PICK_OVER_LIMIT and hands.CLICKS) or own is None or agenda is None:
        return frozenset()
    if agenda.shard in NO_OVERFLOW:
        return frozenset()
    game = getattr(agenda.game, 'name', agenda.game)
    if game is None or loop.done == game:
        return frozenset()
    if OVERFLOW_MOST is not None and len(overflow_played(agenda)) >= OVERFLOW_MOST:
        return frozenset()
    return frozenset(
        shard for shard, act in SHARDS.items() if act != own and act not in agenda.acts and act not in agenda.overflow
    )


def overflow(loop, run: Run, terrorized, inventory_key: str | None = None, *, carried_only: bool = False) -> None:
    """The shards over the limit used, in town, after the kind's own shard's step (`overflow_due`): a carried one where
    it lies (terrorize.py `use_carried`), else one taken from its stack (`terrorize`). A confirmed use adds its act
    after the acts before it; a refused one (an act terrorized already: it stays carried) or a stop is said and left:
    never the kind's shard failures, never the game's end. The player's hand or a cut run stops it, nothing noted
    (tried again at the next visit in town). `carried_only`: a carried shard only (a waypoint leg from a town: no walk
    to the stash)."""
    agenda, own = loop.agenda, act_of(loop.kind)
    if not OVERFLOW or not hands.CLICKS:
        return
    picked_only = own is None  # a kind of no act (OVERFLOW_KINDS): a picked-up shard only, never one from its stack
    if picked_only and getattr(loop.kind, 'key', None) not in OVERFLOW_KINDS:
        return
    if not picked_only and agenda.shard in NO_OVERFLOW:
        return
    carried_only = carried_only or picked_only
    view = run.reads.stash_view()
    pack = run.reads.carried()
    carried = (*pack.items, *pack.in_cube) if pack is not None else ()  # the inventory's first
    for act, item in overflow_due(view, agenda, own, carried, carried_only=picked_only):
        if carried_only and item is None:
            continue
        shard = next(each for each, its in SHARDS.items() if its == act)
        name, count = name_of(shard).split()[0], view.count(shard) if view is not None else 0
        before = played_said(agenda.acts)
        try:
            used = use_carried(run, item, inventory_key, terrorized) if item is not None else (
                terrorize(run, inventory_key, act, terrorized)
            )  # fmt: skip
        except Abort as stop:
            if cut(run, stop):
                raise
            agenda.overflow[act] = FAILED
            LOG.info('Macro: act: %s shard over the limit (%d): not used (%s): act %d not played', name, count, stop,
                     act)  # fmt: skip
            continue
        if used is not None and used.confirmed:
            agenda.overflow[act] = USED
            agenda.acts = played((*agenda.acts, act), own)
            # The watch tools read it (d2-loop-watch logwords.py OVERFLOW)
            LOG.info('Macro: act: %s shard over the limit (%d)%s: act %d terrorized too, played after %s', name, count,
                     ', a carried one' if item is not None else '', act, before)  # fmt: skip
            run.say(f'Act {act} too: {name} shard over the limit')
            continue
        agenda.overflow[act] = REFUSED
        if used is None:
            why, left = 'nothing used', 'where it was'
        elif used.gone:
            why, left = 'gone, its stack not as it should be', 'not carried'
        else:
            why = 'still carried'
            left = (
                'left carried (its stack full: the visit puts it down, as before)'
                if item is not None
                else 'carried, stashed again at the next visit'
            )
        LOG.info('Macro: act: %s shard over the limit (%d): refused (%s): act %d not played; the shard %s', name, count,
                 why, act, left)  # fmt: skip


def played_said(acts: tuple[int, ...]) -> str:
    """`act 3`, `acts 3 and 5` for the log; 'no act' with none."""
    if not acts:
        return 'no act'
    if len(acts) == 1:
        return f'act {acts[0]}'
    return f'acts {", ".join(map(str, acts[:-1]))} and {acts[-1]}'
