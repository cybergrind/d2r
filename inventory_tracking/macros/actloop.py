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

Every overflow shard used (2026-10-22, the player: "use all overflow shards => maybe more acts"): no bound on the acts
a game (OVERFLOW_MOST None), a carried shard counted toward its stack (CARRIED_COUNT), a usable one never put down
(SPARE_USABLE, `spared`), and one carried at the game's end used there, the game going on (END_USE, `use_at_end`).
"""

from collections.abc import Callable, Iterable

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Carried, Pack, StashView, World
from inventory_tracking.game.stash import NORTHERN_FLOOR
from inventory_tracking.macros import (
    midgame,
    terrorize as hands,  # `hands.CLICKS` read at the call
)
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
from inventory_tracking.macros.tzroutine import alone_act
from inventory_tracking.native.layout import TOWN_IDS


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
# Overflow acts a game at most (None: every act over the limit); the acts after the kind's are taken first (act 3: 4,
# 5, 1, 2). 1 from 2026-10-21 ("one extra act"). None since 2026-10-22 ~21:00, the player's ruling: "no save/exits on
# games with worldstone shards spent! you must finish the game correctly => all levels + use all overflow shards =>
# maybe more acts + rotating TZ"; "why we don't use northern shards and just ddroppped them" (rca/2026-10-22/
# overflow-findings.md). Each act over the limit is played, its time added to the game's cap (loop.py
# `allowed_seconds`): a game with k stacks at the cap at its shard step plays 1 + k acts. 1: one extra act, as before
OVERFLOW_MOST: int | None = None
# A carried shard counts toward its stack (2026-10-22, rca/2026-10-22/overflow-findings.md): over the limit when the
# stack has no room for every carried one (terrorize.py `over_limit`), so the visit uses one before the stash step.
# Game cyberg65 at 20:07:59: the Northern stack at 98, three Northerns carried, nothing due (98 < 99); the stash took
# one (99) and the other two were put down in the Fortress. False: the stack's count alone, as before
CARRIED_COUNT = True
# A carried shard the game can still use is never put down (2026-10-22, `spared`, through engine.py `protected`, which
# every put-down asks): one a class (the inventory's first, then the cube's) of an act neither terrorized nor refused in
# this game, in a kind with a shard use. Only a shard that cannot be used falls: its act terrorized already (a second
# Northern after act 5's), its use refused by the game, a kind with no shard use, a game where no shard is risked
# (NO_OVERFLOW). False: the visit puts every full stack's shard down, as before
SPARE_USABLE = True
# A carried shard over the limit used at the game's end too (2026-10-22, `use_at_end`; the ruling above: "use all
# overflow shards => maybe more acts"): the end's town visit and Save and Exit in a town use it first, and a confirmed
# use takes the game's end back, its act's levels owed (tzloop.py ACT_OWED). False: never at the game's end, as before
END_USE = True
# The kind's own act's shard carried is kept for the next game and used first (2026-10-23 02:12:26: two Western shards
# found in an act 1 game were put down, its stack full and no vendor buying one; the player, 2026-10-22: "why we don't
# use northern shards and just ddroppped them", "use all overflow shards"): the next game's own act uses a carried one
# before its stack (`own_shard`), and the first carried copy is never put down (`spared`); a second copy still falls.
# False: the own act's shard always from its stack, and a carried one of it put down, as before
OWN_CARRIED = True
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
# A spare Northern Worldstone Shard for the Baal kind (the player, 2026-10-25 ~12:50: "keep northern shards +1, if we
# can - use before running baal"). True: every kind keeps one Northern past its full stack carried (`spared`: the first
# carried copy; a second still falls), and a Baal game's start in town uses a carried one, or in the Fortress one of a
# stack at the cap, on act 5 before its waypoint (`baal_shard`, loop.py BAAL_SHARD): the Keep 2 and 3 and the Throne
# terrorized. Nothing spare: the Baal game as before. False: a full stack's Northern put down in a kind with no use for
# it, and no shard step in a Baal game, as before
# NORTHERN_STACK (the player, 2026-10-25 ~13:48, asked whether every Baal game takes a Northern from the stash's stack:
# "floor is 40, use up to it"): True: a Baal game with no Northern carried takes one from the stack, in any town
# (Harrogath, where its games start), while the stack holds more than NORTHERN_FLOOR (game/stash.py). False: the stack
# only at the cap and in the Fortress, as before.
NORTHERN_STACK = True
NORTHERN_FOR_BAAL = True  # on 2026-10-25 ~13:35: "we could run terrorized baal that drops an expensive statue"
NORTHERN_ACT = 5
NORTHERN = next(shard for shard, act in SHARDS.items() if act == NORTHERN_ACT)


def act_of(kind) -> int | None:
    """The act a kind terrorizes; None for any other kind."""
    return ACTS.get(kind.key)


def alone(act: int | None) -> bool:
    """Whether act `act`'s game plays it alone (macros/acts/engine.py `ActScript.alone`; act2.py ALONE, the player,
    2026-10-25 ~17:15: "act 2 tz leveling ... go all canyon of the magi + all tals rasha tombs ... go full arcane
    sanctuary"): its kind's game uses no shard over the limit (`overflow_due`, `picked_shards`, `unusable`: the acts
    would not be played, tzroutine.py `itinerary` plans the alone act only), and no game of a kind with no act of its
    own (TZ leveling, OVERFLOW_KINDS) uses its shard as an overflow (it would be the game's first act: alone, the
    rotation dropped). False for None."""
    return act is not None and alone_act((act,)) == act


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
    if OWN_CARRIED and hands.CLICKS and (item := carried_own(run, act)) is not None:
        agenda.shard = FAILED  # tried once a game, as below
        midgame.keep(loop)
        try:
            used = use_carried(run, item, inventory_key, terrorized)
        except Hand:
            agenda.shard = None
            raise
        except Abort:
            agenda.shard_failures += 1
            raise
        if used is not None and used.confirmed:
            agenda.shard, agenda.acts, agenda.shard_failures = USED, played((used.act, *agenda.acts), act), 0
            midgame.keep(loop)
            LOG.info('Macro: act: act %d terrorized by a carried %s (OWN_CARRIED): its levels are played, the boss '
                     'first', used.act, name_of(used.shard))  # fmt: skip
            return
        LOG.info('Macro: act: the carried %s did not take: one from its stack', name_of(item.txt))
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
    midgame.keep(loop)  # in the game's record before the click: a crash under it never tries a second shard
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
        midgame.keep(loop)  # the shard spent and its act in the game's record at once
        LOG.info('Macro: act: act %d terrorized by a %s: its levels are played, the boss first', used.act,
                 name_of(used.shard))  # fmt: skip
        return
    agenda.shard_failures += 1
    LOG.info('Macro: act: the shard did not take (%s): TZ+ on the rotation this game (%d of %d)',
             'nothing used' if used is None else 'gone, the stack not one lower' if used.gone else 'still carried',
             agenda.shard_failures, SHARD_FAILURES)  # fmt: skip


def carried_own(run: Run, act: int) -> Carried | None:
    """OWN_CARRIED: the first carried shard of `act` (the inventory's, then the cube's), None with none."""
    pack = run.reads.carried()
    if pack is None:
        return None
    return next((each for each in (*pack.items, *pack.in_cube) if SHARDS.get(each.txt) == act), None)


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
    """Pure. The overflow uses due now (`OVERFLOW`): each act of a shard over the limit (`over_limit`: its stack at the
    cap, or with no room for the `carried` ones, CARRIED_COUNT) but the kind's own (`own`), not terrorized and not
    tried in this game, with the carried shard of it to use (the inventory's
    first, then the cube's; None: one from its stack); the acts after `own` first (act 3: 4, 5, 1, 2), at most
    OVERFLOW_MOST played a game. () with the switch off or the stash unread. `carried_only`: only the acts of a carried
    shard (a TZ leveling game, OVERFLOW_KINDS), so one with none carried does not take the slot from one carried."""
    if not OVERFLOW or alone(own):
        return ()
    held = tuple(carried)
    due = sorted(
        (SHARDS[shard], shard)
        for shard in over_limit(view, held if CARRIED_COUNT else ())
        if SHARDS[shard] != own
        and not (own is None and alone(SHARDS[shard]))  # a TZ game's first act: alone, its rotation dropped
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
    if not (OVERFLOW and PICK_OVER_LIMIT and hands.CLICKS) or own is None or agenda is None or alone(own):
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
            midgame.keep(loop)
            LOG.info('Macro: act: %s shard over the limit (%d): not used (%s): act %d not played', name, count, stop,
                     act)  # fmt: skip
            continue
        if used is not None and used.confirmed:
            agenda.overflow[act] = USED
            agenda.acts = played((*agenda.acts, act), own)
            midgame.keep(loop)  # the overflow shard spent and its act in the game's record at once
            # The watch tools read it (d2-loop-watch logwords.py OVERFLOW)
            LOG.info('Macro: act: %s shard over the limit (%d)%s: act %d terrorized too, played after %s', name, count,
                     ', a carried one' if item is not None else '', act, before)  # fmt: skip
            run.say(f'Act {act} too: {name} shard over the limit')
            continue
        agenda.overflow[act] = REFUSED
        midgame.keep(loop)
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


def use_at_end(loop, run: Run, terrorized, inventory_key: str | None = None) -> bool:
    """END_USE: at the game's end in a town (its town visit, Save and Exit there), the carried shards over the limit
    used (`overflow`, carried only); whether one was. A confirmed use takes the game's end back (`Loop.done`): its act's
    levels are owed (tzloop.py ACT_OWED) and planned at the next leg. Never in a game given up (`Loop.abandon`)."""
    if not END_USE or getattr(loop, 'abandon', False):
        return False
    before = loop.agenda.acts
    overflow(loop, run, terrorized, inventory_key, carried_only=True)
    added = tuple(act for act in loop.agenda.acts if act not in before)
    if not added:
        return False
    loop.done = None
    midgame.keep(loop)
    LOG.info('Macro: act: the game goes on: %s terrorized at its end by a carried shard over the limit, played now',
             played_said(added))  # fmt: skip
    run.say(f'The game goes on: {played_said(added)}')
    return True


def end_due(loop, run: Run) -> tuple[int, ...]:
    """END_USE: the acts a carried shard over the limit would terrorize at the game's end (`overflow_due`, carried
    only); () with none, the switch off, a game given up or no shard risked in it. Read anywhere (the stash's record),
    so a game ending in a field level goes to town for it first (tzloop.py LEAVE_GAME)."""
    agenda, kind = loop.agenda, getattr(loop, 'kind', None)
    own = act_of(kind) if kind is not None else None
    if not (END_USE and OVERFLOW and hands.CLICKS) or getattr(loop, 'abandon', False) or kind is None:
        return ()
    if own is None and getattr(kind, 'key', None) not in OVERFLOW_KINDS:
        return ()
    if own is not None and agenda.shard in NO_OVERFLOW:
        return ()
    view = run.reads.stash_view() or run.stash.current()
    pack = run.reads.carried()
    carried = (*pack.items, *pack.in_cube) if pack is not None else ()
    return tuple(act for act, item in overflow_due(view, agenda, own, carried, carried_only=True) if item is not None)


def unusable(loop, act: int) -> str | None:
    """Why this game cannot use a carried shard of `act` over the limit (`overflow`); None: it can (SPARE_USABLE)."""
    if not (OVERFLOW and hands.CLICKS):
        return 'the overflow is off'
    kind, agenda = getattr(loop, 'kind', None), getattr(loop, 'agenda', None)
    if kind is None or agenda is None:
        return 'no loop kind'
    own = act_of(kind)
    if own is None and getattr(kind, 'key', None) not in OVERFLOW_KINDS:
        return f'{getattr(kind, "name", kind.key)} has no shard use'
    if alone(own) and act != own:
        return f'act {own} plays alone (macros/acts/act{own}.py ALONE): no other act in its game'
    if own is None and alone(act):
        return f'act {act} plays alone (macros/acts/act{act}.py ALONE): never an overflow act of this kind'
    if own is not None and agenda.shard is not None and agenda.shard in NO_OVERFLOW:
        return f'no shard is risked in this game ({agenda.shard})'
    if act == own:
        return f"act {act} is the kind's own (its shard from its stack)"
    if act in agenda.acts:
        return f'act {act} is terrorized in this game already'
    if agenda.overflow.get(act) == REFUSED:
        return f'its use was refused by the game (act {act})'
    if OVERFLOW_MOST is not None and len(overflow_played(agenda)) >= OVERFLOW_MOST:
        return f"the game's {OVERFLOW_MOST} extra acts are played"
    return None


_said_down: set[tuple[object, int]] = set()  # (game, unit): the shard's put-down said once a game (`spared`)


def spared(loop, item: Carried, carried: Callable[[], Pack | None] | None = None) -> str | None:
    """SPARE_USABLE: why the carried shard `item` is never put down now (engine.py `protected`): this game can still
    use it (`unusable`), and it is the first carried of its class (the inventory's, then the cube's: the one
    `overflow_due` takes; `carried` reads the pack now). None for any other item, or a shard that falls: why said once
    a game (a second Northern after act 5's)."""
    if not SPARE_USABLE or item.txt not in SHARDS:
        return None
    act, name = SHARDS[item.txt], name_of(item.txt)
    agenda = getattr(loop, 'agenda', None)
    said = (getattr(agenda, 'game', None), item.unit_id)
    why = unusable(loop, act)
    kept = f'a {name} act {act} can still use in this game'
    if OWN_CARRIED and why is not None and getattr(loop, 'kind', None) is not None and act == act_of(loop.kind):
        # the next game's own act uses it first (`own_shard`): the first copy kept, a second falls below
        why, kept = None, f"a {name} kept for the next game's act {act} (OWN_CARRIED)"
    if NORTHERN_FOR_BAAL and why is not None and act == NORTHERN_ACT:
        # any kind: one Northern carried for a Baal game's start (`baal_shard`), a second falls below
        why, kept = None, f'a {name} kept for a Baal game'

    if why is None and carried is not None and (pack := carried()) is not None:
        first = next((each for each in (*pack.items, *pack.in_cube) if each.txt == item.txt), None)
        if first is not None and first.unit_id != item.unit_id:
            why = f'another {name} (unit {first.unit_id}) is kept for act {act}'
    if why is None:
        return kept
    if said not in _said_down:
        _said_down.difference_update({each for each in _said_down if each[0] != said[0]})  # this game's only
        _said_down.add(said)
        LOG.info('Macro: act: the %s (unit %d) may be put down: %s', name, item.unit_id, why)
    return None


def northern_ready(run: Run, area: int | None) -> str | None:
    """NORTHERN_FOR_BAAL: where a Baal game's shard step finds its Northern: 'carried' (the inventory's, then the
    cube's), or 'stack' in a town with its stack over NORTHERN_FLOOR (NORTHERN_STACK off: the Fortress with the
    stack at the cap, `over_limit`); None with none, the switch or the clicks off."""
    if not (NORTHERN_FOR_BAAL and hands.CLICKS):
        return None
    if carried_own(run, NORTHERN_ACT) is not None:
        return 'carried'
    if NORTHERN_STACK:
        view = run.reads.stash_view()
        if area in TOWN_IDS and view is not None and view.count(NORTHERN) > NORTHERN_FLOOR:
            return 'stack'
        return None
    if area == PANDEMONIUM_FORTRESS and NORTHERN in over_limit(run.reads.stash_view()):
        return 'stack'
    return None


def baal_shard(loop, run: Run, terrorized, inventory_key: str | None = None) -> bool:
    """BAAL_SHARD (loop.py): act 5 terrorized before a Baal game's waypoint by a carried Northern where it lies
    (`use_carried`), else in the Fortress one from its stack at the cap (`terrorize`), as the overflow's uses
    (`overflow`); whether it took. A refusal (act 5 terrorized already) or a stop is said and the game goes on as
    before; the player's hand or a cut run raises, so the step is tried again."""
    item = carried_own(run, NORTHERN_ACT)
    player = run.world().player
    town = TOWN_IDS if NORTHERN_STACK else (PANDEMONIUM_FORTRESS,)
    if item is None and (player is None or player.area not in town or northern_ready(run, player.area) != 'stack'):
        LOG.info('Macro: act: no Northern Worldstone Shard carried for the Baal run: act 5 is not terrorized')
        return False
    floor = NORTHERN_FLOOR + 1 if NORTHERN_STACK else SHARD_FLOOR
    try:
        used = use_carried(run, item, inventory_key, terrorized) if item is not None else (
            terrorize(run, inventory_key, NORTHERN_ACT, terrorized, floor)
        )  # fmt: skip
    except Abort as stop:
        if cut(run, stop):
            raise
        LOG.info('Macro: act: the Northern Worldstone Shard for the Baal run stopped (%s): the run as before',
                 stop)  # fmt: skip
        return False
    if used is not None and used.confirmed:
        LOG.info('Macro: act: act 5 terrorized by a %s Northern Worldstone Shard before the Baal run',
                 'carried' if item is not None else "stack's")  # fmt: skip
        run.say('Act 5 terrorized: the Baal run')
        return True
    why = 'nothing used' if used is None else 'gone, its stack not as it should be' if used.gone else 'still carried'
    LOG.info('Macro: act: the Northern Worldstone Shard for the Baal run did not take (%s): the run as before', why)
    return False


def played_said(acts: tuple[int, ...]) -> str:
    """`act 3`, `acts 3 and 5` for the log; 'no act' with none."""
    if not acts:
        return 'no act'
    if len(acts) == 1:
        return f'act {acts[0]}'
    return f'acts {", ".join(map(str, acts[:-1]))} and {acts[-1]}'
