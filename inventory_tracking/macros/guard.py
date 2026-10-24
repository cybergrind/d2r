"""The stand guard: after a stop the KP_6 loop made itself, the character is not left standing defenceless in a level.

20:48:09 on 2026-10-22 (cyberg65, a Shard: Act 1 game, the Arcane Sanctuary): the loop stopped itself by a Superior
Flail it could not pick up ("... lies on the ground: the loop stops here"). Attack mode was off and the loop's own
watchdogs (running/watch.py `poll`: beset, still) look only while the loop is on, so nothing defended the character:
it stood 3.5 min while three hostiles 14-23 away shot it, 2943 -> 1550 of 1896 life by the restart at 20:51:37 (take
20261022T174637Z-74). The player, 20:50: "we're standing without enabled fight under heavy damage. don't you thin that
we need to fix that immediately?"; standing rulings: "we must not die or we lose exp and our gear"; "if we died - we
MUST not take ANY other actions"; the player's own KP_6 pause wins (rca/2026-10-22/guard-findings.md).

The one owner of that watch. A stop of the loop's own (running/recovery.py `_stop_loop`: a hold by a valuable, a
stop for the player with bosses alive, a recovery that could not leave, a stop the rules make) arms it; while armed,
in a level of the game it was armed in, each poll (`Guard.look`, about once a second) reads the life and the hostiles:

- hit (life missing grew by HIT_SHARE of the most since the last look) or a hostile within the hunt's SIGHT, with no
  run working and no mode on: FIGHT, attack mode on, the hunt's own fight in place with its own safety (the pursuit's
  pricing: a better place, the retreat by Teleport to safety when the danger model says so; the drinker) - no second
  danger model here; the level run the stop left posted is ended first, so no leg of the loop goes on;
- the guard's fight with neither for QUIET seconds, or in a town: CALM, its attack mode off again;
- disarmed (`disarm`): the player's KP_6 (the loop on or off: the player's pause wins), the player's attack mode key,
  the loop on again by any way, a death (nothing at all is pressed then, not even the mode's end), the game left or
  another game, the service closed.

It never leaves the game, casts no Town Portal of its own, makes no Save and Exit and resumes no leg of the loop.
GUARD (2026-10-22) False: no guard, the stand as before."""

from dataclasses import dataclass
from enum import StrEnum


__all__ = ['GUARD', 'HIT_SHARE', 'QUIET', 'Act', 'Guard', 'Look']

# The switch, 2026-10-22 (on). False: a stop of the loop's own leaves the character as it was, no watch
GUARD: bool = True
# Life missing grown by this share of the most since the last look is a hit: the 20:48 stand's blows were 15-50 of
# 2943 (0.5-1.7 %), the regeneration between looks a few points the other way
HIT_SHARE = 0.003
# Seconds with no hostile within SIGHT and no hit before the guard's fight is over and its attack mode off again
QUIET = 5.0


class Act(StrEnum):
    NOTHING = 'nothing'
    FIGHT = 'fight'  # attack mode on: the hunt's fight in place
    CALM = 'calm'  # the guard's attack mode off again
    DISARM = 'disarm'  # the watch is over (the loop on, a death, another game)


@dataclass(frozen=True)
class Look:
    """What one poll read for the guard. `life`: (points, most); `near`: a hostile within SIGHT; `busy`: a run working
    or a mode on that is not the guard's."""

    now: float
    game: str | None
    in_town: bool
    dead: bool
    life: tuple[int, int] | None
    near: bool
    loop_on: bool
    busy: bool = False


@dataclass
class Guard:
    """The watch after a stop of the loop's own (the module text). Its state is the runner's, read and changed under
    the runner's lock."""

    armed: bool = False
    why: str = ''  # the stop that armed it
    game: str | None = None  # the game it guards in, bound at its first look in one
    fighting: bool = False  # attack mode on is the guard's (FIGHT), not the player's
    missing: int | None = None  # life missing at the last look
    calm_since: float | None = None  # the guard's fight has seen no hit and no hostile near since then
    fights: int = 0  # FIGHTs since it was armed

    def arm(self, why: object) -> bool:
        """Armed by a stop of the loop's own (`why`); whether it was (GUARD on)."""
        if not GUARD:
            return False
        self.armed, self.why, self.game, self.fighting = True, str(why), None, False
        self.missing, self.calm_since, self.fights = None, None, 0
        return True

    def disarm(self) -> bool:
        """Disarmed; whether its own attack mode was on (the caller turns it off, a death aside)."""
        fought = self.armed and self.fighting
        self.armed, self.fighting, self.game, self.missing, self.calm_since = False, False, None, None, None
        return fought

    def look(self, look: Look) -> Act:
        """One poll's verdict (the module text)."""
        if not self.armed:
            return Act.NOTHING
        if look.loop_on or look.dead or look.game is None or (self.game is not None and look.game != self.game):
            return Act.DISARM
        self.game = look.game
        if look.in_town:
            self.missing = None
            if self.fighting:
                self.fighting, self.calm_since = False, None
                return Act.CALM
            return Act.NOTHING
        hit = False
        life = look.life
        if life is not None and life[1] > 0:
            missing = life[1] - life[0]
            hit = self.missing is not None and missing - self.missing >= HIT_SHARE * life[1]
            self.missing = missing
        threat = hit or look.near
        if self.fighting:
            if threat:
                self.calm_since = None
                return Act.NOTHING
            if self.calm_since is None:
                self.calm_since = look.now
            if look.now - self.calm_since >= QUIET:
                self.fighting, self.calm_since = False, None
                return Act.CALM
            return Act.NOTHING
        if threat and not look.busy:
            self.fighting, self.calm_since = True, None
            self.fights += 1
            return Act.FIGHT
        return Act.NOTHING
