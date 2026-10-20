"""The shard act loop: a game's act terrorized by a Worldstone Shard in the Fortress, then played zone by zone, its boss
first (routes/act-terrorize-plan.md; rca/2026-10-20/act-terrorize-findings.md). The player, 2026-10-20 ~18:50:
"terrorize with worldstone shards whole act and go whole act, zone by zone ... we want to kill act boss first for
possible statue drop"; ~19:25: "yes, let's do act 4 mode".

An agenda kind (macros/tzloop.py): `shard_goal` puts the shard first in a game (the visit first when it is due: room
for the shard), `use_shard` makes it (macros/terrorize.py) and records the act terrorized on the agenda, which
`tzloop.zone_of` then plans with the rotation (tzroutine.py `itinerary`: the act first, Diablo's trip first). No shard
at the floor, or a failed use: TZ+ on the rotation that game (the coordinator's accepted answer, 2026-10-20). Offered
(loop.py `loop_kinds`) only with ENABLED.
"""

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.macros import terrorize as hands  # `hands.CLICKS` read at the call
from inventory_tracking.macros.actuator import Abort, Hand
from inventory_tracking.macros.agenda import ERRAND, PANDEMONIUM_FORTRESS, TERRORIZE, WAYPOINT, Objective
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.terrorize import SHARD_FLOOR, choose_shard, name_of, stacks_said, terrorize


# The act kind "Shard: Act 4" offered (the picker's entry). On 2026-10-20 ~21:18 after the player's in-game test
# (findings §6) with terrorize.CLICKS on. False: the kind is not offered
ENABLED = True
# The kinds' acts by kind key (loop.py ACT4)
ACTS = {'act4': 4}
# The shard step's outcomes in a game (`Agenda.shard`)
USED, NONE_HELD, CLICKS_OFF, FAILED, GIVEN_UP, JOINED = (
    'used',
    'none at the floor',
    'clicks off',
    'failed',
    'given up',
    'joined',
)
# Games in a row whose shard did not take, after which the kind plays the rotation only (said each game) until the
# service restarts: no shard more is risked on clicks that do not work
SHARD_FAILURES = 2


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
    game's acts. Nothing used: TZ+ on the rotation this game, said."""
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
        agenda.shard, agenda.acts, agenda.shard_failures = USED, agenda.acts | {used.act}, 0
        LOG.info('Macro: act: act %d terrorized by a %s: its levels are played, the boss first', used.act,
                 name_of(used.shard))  # fmt: skip
        return
    agenda.shard_failures += 1
    LOG.info('Macro: act: the shard did not take (%s): TZ+ on the rotation this game (%d of %d)',
             'nothing used' if used is None else 'gone, the stack not one lower' if used.gone else 'still carried',
             agenda.shard_failures, SHARD_FAILURES)  # fmt: skip
