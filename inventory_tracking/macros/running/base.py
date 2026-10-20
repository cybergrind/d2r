"""The macro runner's constants: the request words and routines, the waits and limits (macros/runner.py and its parts in
macros/running/)."""

from inventory_tracking.macros.goals import USE_NEAR
from inventory_tracking.macros.pickmode import MOST, SURE


REQUEST_PREFIX = 'macro '
TELEPORT_PREFIX = 'teleport '
HUNT_ELITES_PREFIX, HUNT_ANY_PREFIX, PICKUP_PREFIX = 'hunt elites ', 'hunt any ', 'pickup '
LOOP_PREFIX = 'loop '
# The loop's kind chosen by request, `kind <stamp> <key>` (runner.py `choose_kind`); not 'loop kind ', which
# `LOOP_PREFIX` would take
KIND_PREFIX = 'kind '
# A Worldstone Shard used by request (macros/terrorize.py; request.py `terrorize`, 2026-10-20): a routine of its own
TERRORIZE_PREFIX, TERRORIZE = 'terrorize ', 'terrorize'
PREBUFF, TELEPORT, HUNT_ELITES, HUNT_ANY = 'prebuff', 'teleport', 'hunt elites', 'hunt any'  # routines
PICKUP = 'pickup'  # pick up what is worth it, else a seek step (pickup.py)
# The HUD's word for the pickup level (macros/pickmode.py)
PICK_WORDS = {SURE: 'GOOD', MOST: 'MOST'}
TRANSMUTES = 3  # transmutes of one gem kind per stash visit, at most (macros/cube.py `transmute`)
PICK_SLACK = 3  # pickups past the parked gems' count before the ground is taken for clear (`transmute_gems`)
MAKE_ROOM_AFTER = 5.0  # seconds stood by a valuable with no room before the loop makes room in the cube
FOCUS_POLL = 0.5  # seconds between focus checks while the loop waits for the game window
DROPPED_SECONDS = 600.0  # an item dropped for a valuable's room is not taken up again for this long (a game)
VERDICT_SECONDS = 4.0  # wait for the identify watcher's appraisals (it polls once a second)
LOOP = 'loop'  # the KP_6 loop's toggle; a run of it is one leg (macros/loop.py)
STEPS = frozenset((TELEPORT, HUNT_ELITES, PICKUP))  # one press is one step; the same key queues another
# A terror zone's full clear that ends at a door goes on through it with no press (the player, 2026-10-18: "yes, go to
# next level without press"): a teleport press ONWARD_PAUSE after, then the pickup press on the new level; nothing more
# once ONWARD_SECONDS pass.
DOOR_PRESS = 'going through takes a press'
ONWARD_PAUSE = 0.3
ONWARD_SECONDS = 20.0
ATTACK = HUNT_ANY  # the attack mode toggle
# Buff mode (macros/buffmode.py, running/buffing.py): the other active mode the attack mode key's double press picks
# (2026-10-19); a mode as ATTACK is, never queued
BUFF = 'buff'
# The order waiting requests run in: where the player wants to be, what to fight, the macro, the ground.
PRIORITY = (TELEPORT, HUNT_ELITES, PREBUFF, PICKUP, TERRORIZE)
# Seconds after its press a request is still worth starting (user, 2026-10-12: "teleporting after 2 seconds is way too
# late"); 90 % of waiting teleport presses had their key within 0.48 s (2026-10-11). The fight-waiting pickup has none.
EXPIRES = {TELEPORT: 1.0, HUNT_ELITES: 1.5, PREBUFF: 3.0, PICKUP: 2.0}
# Within this of the route's door an empty pickup press is the step through it (rca/2026-10-15/kp1-door-findings.md).
DOOR_NEAR = USE_NEAR
AT_DROP_UNITS = 3.0  # a trip back to a valuable this near is at it: no move to it first
THROTTLE = 0.3  # seconds between accepted macro requests (a bounce is not a cancel)
CARD_SECONDS = 4.0
# A routine's warning (engine.Run `warn`) stays on the card this long after it was last given, unless taken back.
WARNING_SECONDS = 30.0
RESEARCH_ENV = 'D2R_MACRO_RESEARCH'  # set: log which bytes name the unit under the pointer at a Consume
# Seconds attack mode stays out after a teleport step, so the next travel press finds no strike in flight (user,
# 2026-10-12: the teleport key is to work instantly); most presses came 200-600 ms after the step (2026-10-11).
TRAVEL_QUIET = 0.5
JOURNEY_SECONDS = 1.0  # how often the game and level are noted between presses
# A run the input mode flipped under restarts in the new mode (`again`, actuator.py `Flipped`), its start waiting up
# to FLIP_SETTLE for the flip (flips took 10-12 ms, 2026-10-14). FLIPS_AGAIN restarts within FLIPS_WINDOW s stop it.
FLIP_SETTLE = 1.0
FLIP_POLL = 0.02
FLIPS_AGAIN, FLIPS_WINDOW = 3, 10.0
