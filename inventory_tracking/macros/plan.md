# Macro work and recent incidents

Current behavior: [README.md](README.md). Staged work: [framework-plan.digest.md](framework-plan.digest.md),
then the relevant section of [framework-plan.md](framework-plan.md).
The dated entries below are evidence and decisions, not a separate task queue.

## Older evidence

The [history through 2026-10-12](history-through-2026-10-12.md) preserves the earlier
contracts, implementation notes and incidents. Search before opening a section:

```sh
rg --no-config -n '<symbol>|<incident>' inventory_tracking/macros/plan.md inventory_tracking/macros/history-through-2026-10-12.md
```

- [Historical contract (2026-10-11)](history-through-2026-10-12.md#historical-contract-2026-10-11)
- [2026-10-12 02:10 — the teleport key at once; the queue by priority, with limits](history-through-2026-10-12.md#2026-10-12-0210--the-teleport-key-at-once-the-queue-by-priority-with-limits)
- [2026-10-12 05:00 — the death in Tower Cellar 5 (22:50:37 to 22:51:00, take 20261011T195037Z-25)](history-through-2026-10-12.md#2026-10-12-0500--the-death-in-tower-cellar-5-225037-to-225100-take-20261011t195037z-25)
- [2026-10-12 07:00 — the battle replay: the death in Tower Cellar 5 as a test ("red" first)](history-through-2026-10-12.md#2026-10-12-0700--the-battle-replay-the-death-in-tower-cellar-5-as-a-test-red-first)
- [2026-10-12 09:30 — the pickup step opens chests](history-through-2026-10-12.md#2026-10-12-0930--the-pickup-step-opens-chests)
- [2026-10-12 20:30 — a full inventory: a warning that stays, and a stop only for what is prized](history-through-2026-10-12.md#2026-10-12-2030--a-full-inventory-a-warning-that-stays-and-a-stop-only-for-what-is-prized)

## Recent entries

## 2026-10-13 — the healer under a held key: only a modifier refuses a potion

Found in the arena on 2026-10-12 (framework plan, Stage 1): `input/facade.py` `guard` refused a potion while
any key was down, so with the strike held on its skill key (not on the right button) `make osd` sent nothing
for the whole hold, and each refusal cost the potion's cooldown. The guard has a reason: a mercenary's potion
is Shift + the key, so a held Shift changes what the key means. User, 2026-10-13: "yes, refuse only while a
modifier is held".
- input/keyboard.py `modifier_keys` (MODIFIER_NAMES: both Shifts, Controls, Alts, Metas, Supers, level 3).
- input/facade.py `guard`: KEY_HELD only for a modifier, or for one of the keys the potion itself presses (a
  press and release would let the player's own key go).
- The arena's copy of the guard (tests/.../arena/game.py `Attempt`) follows in Stage 4.1.
- Not played yet.

## 2026-10-13 — after a Chaos Sanctuary game (session 20261012T201402Z-41a05b53): the empty staff, the route's end

The user's game of 23:15 to 23:18 (take 20261012T201527Z-108), three things of it:

- **The staff in hand with no charge.** The staff began at 18 charges; the last was spent at 23:16:26 and
  its set stayed in hand until the fight took the main weapons at 23:16:43: 17 s of Blade Warps and blows
  with the lower resistances and skill levels (user: "no reason to really do this"). Now a step with the
  staff empty takes the main weapons first: the teleport step (`Hunter.empty_hop`) and the seek step
  (`Hunter.afoot` with 0 charges). Not changed: with 1 to 14 charges the step spares them by Blade Warp
  with the staff still in hand (32 s in this game); when to hold which set is the swap rule of Stage 7.
- **The macro request after Diablo.** It only cast the buffs: `run_ended` knew no rule for the Chaos
  Sanctuary. Now a level whose route is at its end (`Progress.ending`: what is left of its script is the
  loot and the leaving) is a run's end for the request, whatever the level; the older rules stay for
  levels without a route and for a service without the monster tracker.
- **The pickup key after Diablo.** With nothing to pick up it went for "the remembered monster" by Blade
  Warp, three presses running. At a route's end it now does what the teleport key does there: the ground
  called clean ("nothing to pick up; the next press leaves the game"), and the press after leaves.
- Not played in the game yet.

## 2026-10-13 — Stage 4, the first half: the healer's burst rule, drinking in attack mode, no potion or chest among monsters

What does not wait for the arena's melee (framework-plan.md Stage 4: tasks 4.1, 4.2, 4.6 and a new one).
Unit-tested; the arena's verdict (trials) is owed once the monster model stops moving; not played in the game.

- **`make osd`, the burst rule (4.1).** `HealingConfig.burst_share` (30 for the player, 0 for the mercenary)
  and `burst_window` (1 s): the life fallen by that share of its most within the window, counted from the
  most it was in it, asks for a rejuvenation whatever is left (a healing potion where the belt has none).
  `HealController` keeps the window's readings; another game forgets them.
- **The pressure and the drink decision (4.2), `combat/survival.py`, pure.** `pressure(readings)`: the
  life now, every drop of the last 4 s summed (a refill is not taken off; a weapon swap is no drop), the
  rate, the worst second. `drink(pressure, supply, since, DrinkSettings)`: a healing potion under 90%
  while life is being lost, or under 75% anyway; 6 s between two, 2.5 s under 65%; the last 2 kept for
  under 65% unless more lie near; a rejuvenation when the loss played 1.5 s ahead takes the life under
  30% and it is under 55% already. The marks are `BuildSettings.drink`. They lie above the healer's
  (40%, and the burst), so `make osd` is left the urgent cases (user, 2026-10-12).
- **Attack mode drinks (4.6), `macros/drinking.py`.** `Drinker.look` from the mode's own look (`sense`,
  every pause), every 0.2 s: the life kept, a potion gone from the belt counted as drunk whoever drank
  it, potions on the ground within 20 units as supply, the belt key of the kind's hotkey cell. A key of
  the player's held or the focus lost leaves the drink for the next look and does not end the mode;
  nothing under Shift (Shift and a belt key feed the mercenary). Only in attack mode so far: a teleport
  or seek step on its own does not drink.
- **No potion and no chest among monsters (new).** Found by the replay of Tower Cellar 5 with the
  drinking on: one potion drunk in the fight left the belt short, and the pickup key went for the potion
  4 away with nine monsters near: the stop that killed the character there on 2026-10-11. Now the
  pickup key leaves a potion, and a chest, while a hostile stands within 12 units of it or the character
  (`hunt.threat`: the sweep's own measure, GATHER_CLEAR), and the press goes on to its step; a valuable
  and gold are gone for as before. Presence, not yet potential damage (user, 2026-10-13: "if we don't
  have immediate threat - probably we could open chest"): the price of a place is to replace it.
- Golden net: `decisions.json` unchanged; `tower_cellar5.today.log.json` regenerated (one healing potion
  at 8.86 s with the life at 79% after 13% lost in a second; the potions on the ground left, the fight
  goes on). The replay "as it was" pins both new rules off.

## 2026-10-13, later — the mercenary's rejuvenations, and out of a pack stood in

After the game of 00:08 (session 20261012T210610Z-7c76574f; user: "we were so aggressive, so spent all full
rejuv potions and almost all hp potions"; "ideally, we want to run CS without drinking most of our potions";
"find better stepping out point to be both safe and kill most of mobs as fast as before").

- **Where the potions went.** The belt began that game with 3 rejuvenations. The mercenary got 3
  rejuvenations and 4 healing potions from `make osd`, the character 1 and 4 (3 healing and the
  rejuvenation by attack mode's drinking, 1 healing by the healer). The life lost was the Infector seal
  again: 1,123 points in 9 s among 23 to 26 monsters, the least life 848 of 1,818.
- **The mercenary** (`MERC_HEALING`): a rejuvenation under 40% (was 65%), and none while the belt holds
  three or fewer (`HealingConfig.rejuvenation_reserve`): those are the character's.
- **Out of a pack stood in** (`combat/stance.py` CROWD_ESCAPE, ESCAPE_UNITS, ESCAPE_MOST). The crowd rule
  kept the character out of a pack but measured every place by the pack it stood in already, so in the
  middle of one it stood "well". Now, with more than 3 hostiles within 8 units, a place with at most 3 that
  near is taken when the next seconds there are worth half of what they are where it stands. Chosen on the
  replayed seal fight (the comment at the constants has the numbers): the life lost 727 -> 574 at the
  median and 1,836 -> 1,235 in the worst tenth, cleared no later. Not on the cows' level, where the herd
  is fought from inside (a `Tactic` to come).
- Golden net: 5 cases of `decisions.json` change, all of one moment (20261010T204605Z-21: a place 8 to 12
  units off where the character stood); `black_marsh_clear.log.json` regenerated. The replay of Tower
  Cellar 5 "as it was" pins the rule off.
- Still the larger part, and not done: the approach. The teleport step lands at a seal in the pack with the
  staff's set in hand; no place chosen after that makes the fight cheap.

## 2026-10-13, night — the approach: no hop to a mark a pack stands by

The seal fights of 2026-10-12 21:24 and 2026-10-13 00:09 were lost before they began: the teleport step went
to the second Infector seal, 35 to 40 units off, with 8 and 7 hostiles within 12 units of the seal (25 and
23 within 30 of the landing) and the staff's set in hand (user: "diving into big pack with staff in hand -
could be fatal"; "ideally, we want to run CS without drinking most of our potions").

- **Now** (`Hunter.pack_ahead`, runner.py's teleport step): when the mark is an object the step will stand
  at and use (a seal, a chest, a body: not a way on), within 45 units, and more than 3 hostiles stand
  within 12 units of it, the press does not hop there. It says "N monsters by <mark>: the fight first",
  takes the main weapons, and is the pickup key's step with hostiles near: the sweep, attack mode on,
  which goes to the places the stance gives (none in the middle of a pack) and fights from there. A press
  with the pack down to 3 or fewer by the mark goes on to it.
- On the two recorded games the rule fires at that seal in both (8 and 7 by the mark when it first came
  within 45 units), and once more at the first Vizier seal (4 by it).
- Not in the arena: the teleport step and the route are not played there (Stage 5 and 6), so this is
  tested on the fakes and counted on the takes only. Not played in the game.
- Presence again, not potential damage: four slow monsters by a chest stop the step as a seal pack does.
- **Withdrawn, 2026-10-13**, after the game of 09:06: KP_4 mashed by Vizier seal 1 was 16 presses saying "the
  fight first" and about 7 s with no strike (rca/2026-10-13/kp4-findings.md). `Hunter.pack_ahead` and the
  runner's branch are removed; KP_4 hops to the mark again, whatever stands by it.
