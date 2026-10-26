# Echoing Strike Warlock: tactics

The one place that says what the Warlock has and how it fights. Written 2026-10-25 at the player's ask (10:29: "write
all we discussed in a free form ... put this into a single file"). The player's full quotes, the rulings later
superseded and the questions never settled are in [dialogues.md](../../../rca/2026-10-25/tactics/dialogues.md). The
code survey behind §8 is [code-map.md](../../../rca/2026-10-25/tactics/code-map.md). The fight studies behind §2, §5 and §7
are [deaths.md](../../../rca/2026-10-25/tactics/deaths.md), [near-death.md](../../../rca/2026-10-25/tactics/near-death.md)
and [teleports.md](../../../rca/2026-10-25/tactics/teleports.md).

**Conventions.**
- Code paths are relative to `inventory_tracking/`. Times are the player's local time (UTC+3), as the code comments
  write them.
- Distances are world units (u), the same units the code uses.
- **V** = verified (measured in takes or logs, or read from the game's tables). **I** = inferred. **R** = the player's
  ruling.
- **Section numbers are stable.** Code comments refer here as `see builds/warlock/TACTICS.md §3.2`. Do not renumber.
  A new item goes at the end of its section.
- When a switch flips, update the table in §8 and the "now" line of the tactic in question.

---

## §1 The kit

### §1.1 Echoing Strike: the damage

- **The blades.** Five blades (missile 706) spawn 0.8 u ahead of the caster, spread ±0.95 and ±1.9 u across the aim
  line. They fly at 1.12 u a frame toward the point under the pointer, converge, fly through it for 19 frames, then
  home back. Hits land on the way out and on the way back.
- **Reach: 22.1 u** (0.8 + 1.12 × 19). Blades stop at walls. V: recordings fitted in
  `builds/history/warlock-echoing_strike-mechanics.md`, missiles.txt 706, skills.txt 388; `echoing_strike/mechanics.py`.
- **One body or a line.** On one monster, every blade after the first deals (100 / count) / 2 %. Five blades on one
  body are worth 1.4 blades; a line through five monsters is worth five. So **aim a line through the pack**, not
  at one body. The exception is a leader we hold: there the focal goes on its body (§4.3). V: skills.txt calc6.
- **Aim.** The blades converge at the pointer. To put all of them on a target, aim on a straight line through it
  and behind it (R 10-09 21:56). The blades go to the unit under the pointer, so the pointer must sit on the held
  leader's body, not on a monster in front of it. V: 21 of 46 casts hovered a Flame Spider
  (rca/2026-10-21/arachnid-herald-1-findings.md).
- **Hit share by distance** (the share of blades that hit; 694 casts; rca/2026-10-14/run-1932-findings.md §4.1). V:

  | distance | 6 | 10 | 14 | 18 | 22.1 |
  |---|---|---|---|---|---|
  | hit share | 74 % | 75 % | 61 % | 49 % | 36 % |

- **The engage ring: about 13.9 u**, half way between the best and the worst share. Camps and the ends of jumps are
  planned toward it (`echoing_strike/attack.py ENGAGE`, `combat/stance.py camp`). I: computed from the table.
- **Mana.** About 16 a strike (`STRIKE_MANA`). Its hits leech mana and life back, so **we keep striking**. A pause
  in striking ends the leech (R 10-21 18:58: "we're stopping attacking => no mana/hp leech => teleporting a lot").
- **Hex: Purge** carries the strike's damage (§1.11). Fights use the main weapons; the swap is only for Battle
  Orders (§1.10).

### §1.2 Enigma Teleport: the move, and what it costs

- **What it is.** Since 2026-10-17 the character wears Enigma. Its Teleport is the character's own: no weapon swap
  and no charges, and it comes first in the movement set, ahead of Blade Warp and the staff (R 10-18 01:09: "use only
  enigma and stop using blade warp in almost all situations"). V: `macros/movement.py OwnTeleport`,
  `builds/warlock/movement.py MOVEMENT`. The code never reads Enigma as an item; it knows only "no staff worn and
  Teleport on a key".
- **Time: 0.31 s** a hop (`macros/movement.py TELEPORT_SECONDS`). Reach: up to 26 u, in view (`macros/travel.py
  JUMP_REACH`); the pad's reach is 23. On LINE levels, such as Duriel's Lair, a hop needs a clear line
  (`levels/reach.py TELEPORT_LINE`). Stale: `combat/stance.py HOP_SECONDS = 1.5` is still the staff's swap-hop-swap
  price.
- **Mana: 24** a hop (skills.txt row 54 at level 1). The character's Teleport level is not read, so 24 is the code's
  figure, an upper bound. The pool is about 745. The mana floor keeps two Teleports and one strike in reserve
  (`combat/threats/manaburn.py RESERVE`).
- **The real cost: the fight.** Every Teleport pulls the demons and the merc back to us and takes them off what
  they were fighting (§2.1). In a fight a Teleport costs 0.31 s, 24 mana **and the Death Mark**. The 0.31 s and the
  24 mana are cheap. The mark is not.
- **When a Teleport is fine.** Fast travel is safe: repeated presses keep us ahead of what wants to burst us. A fight
  is a different case (R 10-12 13:56). A Teleport that comes 2 s late is dropped (R 10-11 22:01).

### §1.3 Death Mark: the demons' leash

- **What it does.** It sends the demons (the bound demon and the Defilers) to the marked monster and makes them
  attack it. The pack then turns on them. The merc is never sent. The mark also lowers the monster's defence by
  540 at level 15. It needs a demon out: with none out it sends nobody (near-death H2). V: `builds/warlock/mark.py`.
- **The jump.** The demons land a **median 0.28 s** after the key (quartiles 0.24-0.29, 409 jumps), 2.8 u from the
  marked monster (910 landings). V.
- **Range.** None: 11 of 11 demons that were farther away jumped, through walls too. V: `MARK_REACH = inf`, Param9 38;
  R 10-21 14:46: "we could use death mark to teleport our daemon even throught the walls".
- **Numbers.**
  - Lasts 12.28 s at level 15.
  - Cannot be cast again for 0.8 s.
  - Our cast takes about 0.37 s.
  - Its state (212) shows a median 0.43 s after the key (1,822 of 1,831 events).

  V: data/damage.json `death_mark`, rca/2026-10-20/mark-recast-leaders-findings.md.
- **What it buys.**
  - After a mark, 8 % of the hits land on the character, against 66 % without one (rca/2026-10-14/death-mark.md §2).
  - In T4-5 fights the share of the pack aiming at the companions goes 0.51 → 0.73 within 1-1.5 s of a mark at a
    landing (rca/2026-10-24/dm-latency-findings.md §4).
  - A demon a Teleport took off its fight is back in it within 1 s **71-83 %** of the time with a mark after the
    landing, and **9-12 %** without one (teleports.md §3.3).

  V, all three.
- How we use it: §3.

### §1.4 The Defiler (Summon Defiler)

- It is summoned at the pointer and needs a line of sight (skills.txt 377).
- Its aura makes the pack share part of the damage among themselves. The player calls it Health Link (R 10-10
  00:57). I: the player's account, not measured.
- A second tank besides the bound demon: Death Mark sends it too.
- **Keep one out.** If it dies, summon another, mid-fight too (R 10-14 23:22: "Yes, mid-fight"). Against a T4-5
  pack, summon a missing Defiler even under attack, from range (R 10-21 ~10:00, Q6).
- **Mana: about 42** (41.5 at level 14). No summon was cast with under 45 read. A key the mana does not cover casts
  nothing (`builds/warlock/defiler.py DEFILER_MANA`, `DEFILER_PAYS`). V: takes 2026-10-22/23.
- Demon slots: Consume uses one. The bound demon plus two summons cancels the Consume buff (R 10-10 18:51).

### §1.5 The bound demon and Bind Demon

- **The tank.** The bound demon (Pit Lord / Urdar, class 361) holds the pack: "keep group on our daemon, not
  ourselves or merc" (R 10-21 09:33).
- **Bind Demon** (skills.txt 382): one bound demon at a time. It works only on a monster monstats calls a demon,
  and the capture is a chance. The player could not bind uniques at level 17 (R 10-06 13:09).
- **The player binds it, never the macros** (R 10-21 16:27: "I will do bind daemon myself. you don't use bind daemon
  anywhere for now and keep it so"). So `builds/warlock/bind.py BIND_DEMON_CASTS = False`, which leaves
  `combat/pack.py REBIND_DEMON = True` with no effect.
- When the bound demon dies mid-run, the run goes on with the Defiler alone. What to do then was never ruled (§9).

### §1.6 Consume

- Consume eats a Defiler and gives a buff that speeds walking and running. It is wanted in town too (R 10-17 15:15,
  10-18 10:58).
- Mana about 40.
- **Never consume the bound demon** (R 10-06 20:51, after a prebuff ate it).
- Consume is renewed in the quiet, broken off by a fight, and not renewed while a Herald omen is pending
  (`buffs.py CONSUME_OMEN_DEFER`).

### §1.7 Engorge

- It is cast on a corpse, a foe's only (our own demons' corpses do not count).
- It heals the demons by 30 % + 1 % a level of their life (skills.txt 379) and gives them a buff that lasts 47.3 s
  (state 211). It heals demons only, not the merc. V: rca/2026-10-24/engorge-findings.md, `builds/warlock/pets.py`.
- **It keeps the bound demon alive.** The loss of 10-21 "could be very easily avoided if we just have use engorge"
  (R 10-21 15:43). A pet in danger gets it first and fast. A dangerous pack's arrival gets the buff first
  (`buffs.py ENGORGE_PACK_FIRST`).
- When Engorge cannot land and the bound demon is under 30 %, pull the fight off it: Teleport past the demon so it
  follows us out (R 10-21 16:27: "Yes, pull it out"; `pets.py PET_PULL`). This is the one place where a Teleport's
  pull is used on purpose.

### §1.8 Sigil: Lethargy

- **What it does.** It slows every monster standing in it.
- **Size.** Radius 6 u (the medium missile, at skill levels 10-19). It lasts 19 s, and a new sigil ends the last one.
  V: skills.txt 393 and the takes. The state (192) is on 84 % of the monsters within 6 u.
- **It is not laid through a wall.** 207 of 212 sigils with a clear line took, against 26 of 60 through a wall. V:
  `casters.py SIGIL_SIGHT`.
- **Kept on hard enemies all the time** (Herald, boss, leader): it is recast when they walk out (R 10-20 23:03).
- **Laid before a Herald pack spawns,** on its spawn spot (R 10-23 21:10; §4.3).
- **It never replaces the strike.** Casting the sigil and not striking kills nothing (R 10-09 20:08).

### §1.9 Psychic Ward

- A pool of 185 points that absorbs physical damage. V: takes of 2026-10-12/13, `builds/warlock/ward.py`. Mana about
  60.
- Kept up (R 10-12 02:36: "probably it will save us sometimes").
- In the T4-5 fights of 10-24 the ward was down 6.3 % of the time, and 76 % of the life was lost in that time. So a
  broken ward is cast again first (`buffs.py WARD_BROKEN_FIRST`). V: rca/2026-10-24/aggro-findings.md §9.9.

### §1.10 Battle Orders (Call to Arms, on the swap)

- **How it is cast.** Battle Orders lasts 180 s. It is cast with the swap weapons, in a spot with no hostile within
  10. In a fight it is renewed with under 10 s left.
- **Timing.** The code predicts when it runs out and retreats to a clear spot to rebuff first (R 10-22 09:51: "keep
  track of battle order and predict when it runs off, retreat and rebuff"; `macros/cta.py REBUFF`, `macros/safety.py
  REBUFF_RETREAT`, `ORDERS_PREDICT`).
- **Why it matters.** Its expiry cut the most life from 2,943 to 1,896 in the Fane death (§7.1).
- **Dolls.** It waits until a doll Herald is dead (`cta.py DOLL_HERALD_FIRST`).

### §1.11 Hex: Purge

- The strikes deal their damage through it, and its blasts hit an area. "Without it - there is no damage" (R 10-11
  00:52).
- It is cast whenever the state is missing: as a prebuff, in upkeep, and in a fight. V: skills.txt 389, `buffs.py`.

### §1.12 The mercenary

- An Act 2 Holy Freeze merc (R 10-06). It is not a healer. "The healer" is `make osd`, the potion feeder (§1.13).
- **Teleport pulls him too** (§2.1). A mark does not send him: he walks back. With a mark he is back in the fight
  within 2 s 46 % of the time, within 4 s 65 % (teleports.md §3.3).
- Blade Warp can take him out of danger (§2.2).
- A lost merc means a trip: go to town, refill potions, revive him, come back (R 10-21 20:04). Not dying ourselves
  comes first.

### §1.13 Potions and rejuvenations

- **The goal is to kill fast without taking damage**, not to drink through fights (R 10-12 14:23, 10-13 00:40).
- **The healer, `make osd`** (config.py; V):
  - It drinks a healing potion for the character at 65 % and a rejuvenation at 40 %.
  - It feeds the merc at 75 % (healing) and 40 % (rejuvenation), but never the belt's last two rejuvenations.
  - It feeds the merc first, unless the character is critical (R 10-13 22:28).
- **The macro's emergency rejuvenation.** It fires under 60 % life, looking 1.5 s ahead at the worst second's loss
  (`combat/survival.py EMERGENCY_REJUVENATION`).
- **The life budget ends at 65 %.** Potions on the belt are not budget (R 10-23 21:05: "No, keep the 65% floor").
- **Mana.** No mana potions. A rejuvenation restores mana only in really scary moments, and must not be overused (R
  10-21 16:27; `manaburn.py MANA_REJUVENATION`, under one strike's cost).
- **An empty belt is a defect.** Restock in town before the belt runs low: a nasty pack may need several tries (R
  10-21 20:04, 20:35: "hp refill is just an another step in routine"). Pick up only super healing and full rejuvenation
  potions.
- **No potion pickup inside a pack.** The Tower Cellar death (§7.1) was nine clicks on a potion among four hostiles
  (`macros/hunting/base.py GATHER_CLEAR = 12`, `hunting/choice.py POTION_HELD`).

---

## §2 Allies and movement

### §2.1 A Teleport takes every ally along: the rule

- **The rule.** Every Teleport, Blade Warp included, brings **every demon and the mercenary to within 4.5 u of the
  character, whatever their distance before**. No pet ever stayed behind. V: 0 of about 170,000 pet sightings, from
  0-3 u to 30-60 u away; the merc to 60+; short Teleports of 5-8 u too (3,498 sightings) (teleports.md §3.1).
- **What happens to them.** A demon that was fighting stops: 86-93 % of the engaged demons are taken off their fight
  by a fight Teleport. Left alone, the demons walk back in 2-4 s. But the next jump usually comes 0.1-0.3 s after the
  landing, and pulls them back again. Meanwhile the pack's aggro falls on us. V: teleports.md §3.2-3.3.
- **So any Teleport after a Death Mark undoes the mark.**
- **The code's model is wrong.** It says allies come along only from within 10 u: `combat/pack.py TAKEN_ALONG =
  10.0`, re-exported in `builds/warlock/mark.py`, and the arena's `ALLIES_ALONG`. Wrong for 10-60 u. Being fixed as
  **ALONG_ALL** (§8): the fix judges a landing with every pet beside the character. That applies to `breaks_range`
  and `range_kept`, to `hop_spots`' "the demons between", to manaburn's `pressing`, and to the arena.
- **Also unmeasured.** `mark.py REMARK_HOP = 4.0` ("a shorter jump takes no demon off its monster") is a stand-in
  below the shortest jumps measured (5 u).
- **The player's words** (R 10-21 20:47): "when we're teleporting - our minions are teleporting with us and stop
  attacking. so, if we want to re-aggro - use death mark and do not teleport, or, if you reposition - re-aggro again".
  And 10-24 13:31: "teleporting - takes aggro from our minions then we're starting attacking without bringind our
  minions into play => no re-aggro => we take multiple heavy hits => teleport => no re-aggro => ... => loop".

### §2.2 Blade Warp

- **It pulls every pet too**, 100 % (1,383 demon sightings, up to 30 u; teleports.md §3.1). The arena's `WARP_ALONG`
  plays it (off by default). V. A take from 10-24 20:18:41 (`20261024T171736Z-71`): after a Blade Warp of 15 both
  demons stood 0.1 u off us, idle, for 1.5 s.
- **Limits.** It needs a direct line (no walls) and cannot be used in town. The hop shows after 1.05 s
  (`WARP_DELAY`); the cast takes 0.35 s. V: `builds/warlock/movement.py`.
- **Since Enigma it is the fallback.** Its one use left is the pull on purpose: it takes the merc out of danger,
  as in the Diablo fight (R 10-14 23:22; `combat/escort.py`).

### §2.3 Walking

- **Walking leaves the pets where they are.** It is the only way to close in while the mark holds: "we just close
  distance walking (tp brings dameon back to us, we want to aoid it in this case)" (R 10-24 20:24).
- A 15 u walk takes about 2.5 s (`combat/pack.py WALK_HOLD` note); Consume makes it faster.
- Most of the places a "better place" Teleport goes to are 4-15 u away. The log already prices those as walks of
  0.6-0.7 s (teleports.md §4.8).
- Short distances in a hunt are walked (R 10-09 20:56).

### §2.4 The pull as a tool

The pull is a cost in a fight and a tool in two cases:
- taking the bound demon out of a fight it is losing (§1.7, `PET_PULL`);
- taking the merc out of danger with a Blade Warp (§2.2).

Everywhere else, plan the move as if the pets will be at our feet when we land.

---

## §3 Death Mark: how we use it

### §3.1 What it is for

Death Mark is not a damage curse first. It is **the way to put the pack's aggro on the demons**: "death mark is a
very effective mechanism that allow to distract/re-aggro enemies" (R 10-14 01:11). It sends them anywhere on the
screen, at once, through walls (§1.3).

### §3.2 The player's sequence: mark, then walk

The player, 10-24 20:24: "cast DM from safe distance => daemon gets teleported and gets aggro => we just close distance
walking (tp brings dameon back to us, we want to aoid it in this case) => apply full damage". And 10-25 10:29: "DM -
teleports daemons to desired location -> allows to safe tp back -> safely engage from distance -> walk closer to the
fight -> kill things".

As the measurements say it must be done (§2.1):

1. **Be at a safe distance first.** If a Teleport is needed to get there, it comes **before** the mark. A safe
   distance is out of the pack's reach: 18-30 u, or behind a wall.
2. **Mark a member drawn on the screen.** Take the designated one (§3.4) if it is on the screen, else the nearest
   clickable member. No line of sight or range is needed.
3. **Hold every voluntary jump for about 0.4 s** while the demons land: 0.28 s is their jump, the rest is margin.
   Then judge the range again, with the demons as the pack's holders (planned: MARK_HOLDS_JUMPS, §8).
4. **Strike from range** while the demons hold the pack. The strike reaches 22.1 u.
5. **Walk closer.** No Teleport while the mark holds. A better place within about 8 u is walked to.
6. **Full damage** from the engage ring (about 13.9 u) or closer.

- **"Allows to safe tp back."** Read with §2.1, this works only in the order *Teleport back, then mark*. A Teleport
  after the mark brings the demons back with us. The player's 10-24 20:04 question says the same: "Retreat = safety
  tp out. tp = we move with merc and daemons. So, what is the logical reason to do DM and then immediately call it
  off with tp?" (Put to the player in §9.)
- **If a Teleport must come after the mark** (a retreat, §5), the first act at the landing where we stay is the mark
  again. The landing in the middle of a chain gets none.

### §3.3 When to mark, and when not

**Mark** (R 10-24 20:26: "we don't need to cast DM like every second for regular enemies, but it is a great way to
handle hard situations"):
- **A hard fight**, as the code defines it (`combat/pack.py hard_fight`), within 30 u:
  - a member of a tier 5 Herald pack;
  - a boss or super unique;
  - holding our ground would cost more than the safety's life budget;
  - a monster that drains mana (but see "do not mark" below);
  - 8 or more of an elite pack.
- **After every landing in a hard fight**, before the first strike (R 10-24 20:24: "cast DM after the TP, so daemon is
  forced to attack"). At T5 Herald landings this is live (`HERALD_MARK_FIRST`). For every hard fight it is built and
  off (R1, `DM_AFTER_EVERY_MOVE`).
- **At the start of a dangerous engagement, from range, before contact** (§3.2). Opening this way is the cure in
  four of the six deaths (§7.1).
- **Who comes first.** Leaders and Heralds (R 10-20 18:31: "pack leader/herald first"). The nearest clickable member
  when the Herald hides behind its minions (R 10-21 09:50). A reviver raising its pack comes before both (§4.9).
- **Immune monsters, even plain trash.** Magic-immune ones (R 10-20 14:31: "our damage is mostly magic"), and
  physical-immune ones too (R 10-21 20:09).
- **Dolls**, through the wall (§4.4). **Bosses**: Baal (R 10-21 17:39: "we haven't used death mark on baal, that is
  incorrect"), Mephisto, Diablo.

**Do not mark:**
- **Regular trash every second.** The price rule refuses a mark on trash that the strike kills in about two casts
  (`mark.py TRASH_CASTS`).
- **Right before a retreat Teleport.** The move cancels it (R 10-24 20:04).
- **After every hop in a mana-burn fight.** Each mark costs mana, and mana is the escape. In the arena, R1 with no
  burn guard raised the manaburn deaths 3 → 6 of 40 and the Mana Burn hits 22.7 → 38.6 (dm-latency-findings.md §10).
  There: leave far first, then mark once from there (§4.6). Whether the first mark at a burner landing is right is
  open (§9).
- **Within reach of a one-shotter.** A mark cast there was itself a death in the arena (INSTANT_THROUGH, 1 of 240).
  Range first.
- **With no demon out.** It sends nobody. Get a Defiler out first (§1.4).

### §3.4 The designation: one target the demons must hold

- **The code keeps one designated target** (`mark.py designate`). Ranks, best first:
  1. a reviver raising its pack;
  2. a Herald or a doll Herald;
  3. a magic-immune monster;
  4. the leader the strike holds;
  5. another leader or boss;
  6. a pack member;
  7. the pack's re-aggro.
- **The designation changes only** when the target dies, goes out of reach, a better reason comes, or two casts in a
  row miss.
- **The mark is due again** when the target lacks it, when the minion carrying it dies (R 10-22 20:04), or when a jump
  took the demons off it (R 10-22 20:00: "we clear DM when we're teleporting with mobs - we re-apply DM because we
  have designaaated mob active").
- **With nobody designated**, after a jump that dragged the demons, or with the pack pressing on us, the member with
  most of the pack around it is designated (`REAGGRO_PACK`, live since 10-24 ~12:20). V: 774 of 872 unmarked hops had
  no designation; with a mark the demons struck 1.1 s after the landing, without one 3.3 s.
- **Known gap.** With a designation already held (the Fane Herald) the re-aggro did not fire. The mark's own "lasts
  on" check held it back (deaths.md §3).

### §3.5 How fast: landing to mark

- **The target is human speed, about 200 ms** (R 10-23 11:23: "human will react in under 200ms").
- The player saw a gap of a second or more between a Teleport and the mark in T5 fights (R 10-24 19:21, 19:23), and
  3-4 s against a zombie T5 Herald (R 10-24 20:19).
- **Now.** At T5 landings the mark comes a median 0.41 s after the landing (HERALD_MARK_FIRST); over all fights with
  a mark the median is 0.67 s (teleports.md §3.3).
- Delays are measured against what the game shows, not against the code's own intent (R 10-24 20:11).

### §3.6 Mark holds jumps (planned)

- **The commonest re-aggro failure is our own next hop** (teleports.md §3.4). Since 10-24 18:49, 198 fight Teleports an
  hour came within 1.5 s after a mark key, and 152 an hour of them pulled back the demon the mark had just sent. By
  source: better-place hops 106/h, pursuit moves 15/h, keep-range hops 14/h, retreats 9/h.
- **The fix: MARK_HOLDS_JUMPS** (being built, §8). For about 0.4 s after a mark key, no keep-range hop and no budget
  retreat: they wait, then are judged again with the demons on the pack. For about 1.5-2 s, a better place or a
  progress jump within about 8 u is walked; a farther one is held.
- **Exempt:** surrounded (3 within 5), a hit taken during the wait, life under the floor, a mana burn seen, the mana
  leave.
- R1 is worth shipping only together with this. Without it, R1's marks are undone by the next hop.

---

## §4 Engagement playbooks

### §4.1 Regular packs

- Go close enough to kill the whole group in under a second. A line through the group (§1.1), from about the engage
  ring or nearer.
  - Not so far that monsters are picked off one at a time (R 10-14 23:02: "we ofthen position us way to far away").
  - Not into the middle (R 10-12 09:57).
- **A few hits taken are cheaper than repositioning** (R 10-17 17:39).
- **No mark,** beyond the price rule's marks on immunes and leaders (§3.3).
- **Never wait for monsters to come.** Engage proactively (R 10-19 21:11).
- **Monsters that do not attack can be left,** on levels that are not terror zones (R 10-22 18:17). On terror-zone
  levels, kill the packs and every unique, champion and Herald, but do not hunt lone leftovers (R 10-21 21:18).
- The firing stand: a fight goal out of reach is approached to a firing spot, and we stand there
  (`macros/hunting/base.py FIRING_STAND`).

### §4.2 Big packs and hard fights

- **A big group:** a hard fight (§3.3) with 6 or more hostiles within 30 (`combat/pack.py big_group`).
- **The opening is §3.2:** mark from where we stand while nothing is in strike reach, then walk in, no Teleport toward
  the group. Built as R2, `MARK_THEN_WALK`, off: no arena gain recorded, but the arena under-plays the mark's aggro
  and plays pets 10+ u away as staying behind.
- Two packs together, or a Herald with a second unique pack, count as one hard fight. The Fane death had two (§7.1).

### §4.3 T5 Herald packs

The worst setting: five of the six deaths and 28 of the 70 near-deaths had a tier 5 pack (§7).

**Before the spawn:**
1. **The omen.** "A Herald is hunting you" and the heraldspawner missile (737). The pack shows **5.0 s** later (p05
   4.95, p95 5.04, 350 omens). V: rca/2026-10-23/omen-opening-findings.md. The real tier is unknown until the spawn.
2. **The stand.** 24 u from the spawn spot (`PACK_OMEN_STAND`; the full clear's own `OMEN_STAND` is 20), with a way
   out (`STAND_WAY_OUT`). Never on the spot, and never in a pocket. In H1 we stood 2.5 u from the spot, in a pocket
   with 10 of 16 rays blocked, and the escape failed three looks in a row.
3. **No move toward the spot** from the omen until 1 s after the spawn (rule R-H1, near-death.md P2). Not built (§8).
   - 9 of 18 omen episodes were within 14 u of the spot at the first hit.
   - Several came from a Teleport toward "the hostile by the Herald coming" 1-5 s before the spawn.
4. **The sigil on the spawn spot before the pack shows**, and **the strike on it too**: the pack arrives slowed and in
   hit recovery (R 10-23 21:10; `buffs.py OMEN_SIGIL`, `hunt.py OMEN_STRIKE`, both live). The hit-recovery part is the
   player's belief and not measured (§9).
5. **Against a ranged or Extra Fast T5 pack, distance is not enough.**
   - Slingers' javelins reach the 24 u stand (H5). Extra Fast Hulks cross 20 u in about 1 s (H3).
   - Stand behind a wall corner from the spot, or 30+ away (R-H3). Not built.

**At the spawn, or at any landing near the pack:**
1. **Death Mark first, from the stand, on a member on the screen** (R 10-24 17:38: "when we're repositioning for
   re-aggro against T5 heralds, the first things we need to do - drop off aggro from us == DM"). Live at landings
   (`HERALD_MARK_FIRST`). A pack that spawns on a standing character is not a landing, so it is not covered (H1: the
   "first at the landing" line came after the low point).
2. **Sigil: Lethargy over the whole group**, laid at the densest disc or on the demon that holds the pack
   (`SIGIL_COVER`).
3. **Kill in the most efficient way.**
   - Pierce the whole group; the Defiler's aura shares the damage (R 10-21 09:33).
   - In T5 packs, take the best line, minions included, not the Herald alone (R 10-23 21:05; `T5_BEST_LINE`, live,
     canyon kills 13.7 vs 8.4).
   - Other Herald fights hold the Herald with the focal on its body (`HOLD_LEADER`).
   - Focus so the blades converge: the "melt" phase, not the "chip" phase (R 10-21 20:43).
4. **Keep range.**
   - Fight from 14-18 u from the pack's centre.
   - Hop back when a member is within 10 or 3 are within 5. At most 3 hops for a pack. Then the plain safety
     (`PACK_KEEP_RANGE`, `PACK_HOPS`; R 10-21 09:50).
   - Every hop takes the demons along (§2.1). So with the demons on the pack, **wait for them to land before judging
     the range**, and walk where we can (§3.6).
   - The hop's "demons between us and the pack" (`hop_spots`) cannot happen while the hop brings them with it
     (ALONG_ALL).
5. **If too close or surrounded,** retreat and re-engage, up to 3 times. Keep the pack on the demon, never on us or
   the merc (R 10-21 09:33). The retreat is §5.1.
6. **Never stand idle under fire, and never leave a Herald unfought** (R 10-21 20:59, 21:07). When the safety refuses
   every spot near a T5 pack, skip the pack (R 10-23 21:05: "Skip it"). `T5_SKIP` is off: on its own it raised the
   canyon deaths 1 → 5 of 20, because the skip handed the next move to a pursuit that walked inside the Slingers'
   lines.
7. **No pickups in a T4-5 pack:** gold waits (`PACK_GOLD_WAIT`), potions wait (`POTION_HELD`).
8. **A missing Defiler is summoned from range,** whatever its price (`DEMON_GATE`).

### §4.4 Dolls (undead fetishes)

**What they do:**
- **The blast.** A dying Undead Stygian Doll or Soul Killer explodes within about 4.5 u. Median 1,166, max 2,603:
  40-90 % of our life in one blow. Dolls were 52 % of all life lost in the near-death episodes (38 of 70).
- **Their speed.** They run at 15.5 u a second, 21.9 with Extra Fast. V: near-death.md P1.
- **The usual shape:** we jump, the pets come with us, the dolls run onto the landing, we strike one at 2.2 u, and it
  blows.
  - 35 of the 38 blasts came within 3 s after one of our jumps.
  - The demon was within 2 u of us in 32 of them.
  - In 14 of the 21 with a mark before the blast, a Teleport after the mark had pulled the demons back.

**The rules:**
1. **A doll Herald: mark it, then kill it very fast.** It has low life even at T5 (R 10-22 12:40;
   `mark.py DOLL_HERALD_FIRST`, live). Battle Orders waits for its kill.
2. **Bait** (R 10-21 14:46-14:48: "we just need our daemon to take the aggro from dolls and then we could easily walk
   into any room"; rule R-D2):
   - At a landing with a live doll within 16 u (20 with Extra Fast), mark a doll from 10+ u before the first strike.
   - Then walk to about 12 u from the held dolls.
   - **No Teleport toward them while the mark holds.**
   - Built as `combat/threats/dolls.py DOLL_BAIT`, off: the arena gate showed fewer kills a minute.
3. **No killing blow on a live doll within 6 u of us.** Step or hop out first, so the strike's line kills it from 6+.
   A doll a demon holds blows on the demon (R-D1, missing).
4. **No escape Teleport timed against a dying doll.** At least 18 jumps pressed under 0.35 s before the blast never
   got us out. Hop first, strike after (R-D3, missing).
5. **No landing near a live doll** (`DOLL_LAND`, off since 10-21 ~14:55; 30 of the 38 doll episodes came after
   that). Escapes near dolls are barred only when a clean one exists (`DOLL_ESCAPES`, live). Pickups wait for dolls
   (`DOLL_GUARD`, live).
- The player found us "too reckless when engaging with dolls" (R 10-21 13:31). Also: "keep teleporting around without
  actuall kills" (R 10-21 14:46).

### §4.5 Ranged packs: javelins, darts, Succubi

- **The canyon death (§7.1, #4).** A T5 Hell Slinger pack hit about 1,000 times harder than the code priced it. We
  stood 6 s in the open at 21 u with no mark and no strike, and the cover (demon and merc at our feet) died first.
- **Mark from the stand at once.** The demons jump onto a shooter, its throws turn to them, and we are out of their
  line (I, from dm-latency §4's 0.51 → 0.73).
- **No Teleport into a shooter pack's reach once the cover is gone.** Either leave their reach (33+ u from every
  thrower) or put a wall between, then walk back behind the marked demons.
- **The live gap.** The code does not read the throws: `combat/bolts.py READ_THROWS = False`. Reading them passed
  survival (0 of 20 dead, against 1-2 of 20), but the kills fell 8.4 → 2.2, so it was withdrawn (journal 10-23
  19:40). Without it, `pursuit.py THROWN_OUT` (live) does nothing. **This is the most dangerous live gap.**
- **Walking into a walled room with shooters out of sight** (O1, Succubi and Gloams): mark what is on the screen first
  so the demons go ahead, then walk (R-W1, medium confidence).
- T5 Dark Archers are among the worst (R 10-21 15:45). Threat is burst: hard-hitting ranged monsters, fast dense
  packs, fast packs with bad auras. Slow zombies are no threat (R 10-07 01:40).

### §4.6 Mana burners and drainers

- **Who.** The Mana Burn modifier, and monster types whose own blows burn mana (Ghosts, Wraiths, Gloams, Souls: 200-300
  a hit; `combat/threats/drain_escape.py MANA_ELEMENT`). A T5 pack can burn the whole pool in one second (H8: 597 →
  0). With no mana, neither a hop nor a mark is possible.
- **Keep range 18,** up to 10 hops a pack (`manaburn.py BURN_RANGE`, `BURN_HOPS`).
- **The mana floor.** Leave while the mana still pays two Teleports and one strike. Only burners trigger it
  (`MANA_FLOOR`, `LEAVE_BURNERS_ONLY`).
- **The drain escape.**
  - The burn is read by type and remembered.
  - The leave goes 24-30 u.
  - A refill is followed by the Teleport, not counted as an escape.
  - Blade Warp is barred under its mana.

  (`drain_escape.py MANA_ESCAPE`, live since 10-24 ~09:50, R 10-24 09:36: "Turn it on"). Arena: 10 of 20 dead → 0 of
  20.
- **The order: leave far, keep the mana for Teleport, mark once from there.** Not a mark after every hop
  (`DM_MOVE_NO_BURN` exists for that and is off with R1).
- **Open from 30+ u** against a T5 burn pack (R-M1). From a safe distance, a mark sends the demons: this is the
  player's "cast DM from safe distance" case (teleports.md §4.2). Whether to mark first against burners was never
  settled (§9).
- **A physical-immune drain pack is given up, not fought.** The Flayer Dungeon Herald lost 5 of 128 in 16 s. Not
  built.

### §4.7 Extra Fast packs

- Kept at 18 u like burners (R 10-21 16:27: "Yes, 18 for Extra Fast"; `manaburn.py FAST_RANGE`).
- **The failing shape** (teleports.md §4.1). We land, mark first (right), and 0.32 s later the keep range hops,
  because the demons are still beside us mid-jump, so every member counts as "on the character". The mark is
  undone. In the example: 21 jumps, 0 kills, full life throughout.
- **The fix.** Wait about 0.4 s after the mark, judge the range with the demons as holders, strike from 7-18 u, and
  walk (§3.6).
- Against an Extra Fast melee pack the 24 u stand is inside one second of their run (H3, H8). It needs cover or 30+
  (§4.3).

### §4.8 Bosses

- **Act bosses are always killed** (R 10-22 09:43, 10:27). A boss on a level we only pass through is not a goal. A
  non-act boss never holds a game (R 10-23 08:47).
- **How.** Land offset from the boss and his group, not on them (R 10-11 15:59). Fight with the main weapons, mark the
  boss, keep a sigil under him (R 10-20 23:03).
- **Diablo.** No Teleport away from his lightning, because he follows. Walk a tight circle close round him (R 10-20
  23:07, 10-21 00:02; `combat/threats/diablo.py WALK_AROUND`, `macros/safety.py WALK_ROUND`). Clear each seal's pack.
- **Baal.** Kill the five waves, wait for his portal, go through, kill him. Mark him.
- **Mephisto.** Blade Warp near the portal, mark him so the demons hold him, sigil, kill, pick up, leave by the portal
  (R 10-12 09:40).
- **Moves toward a run's boss** skip the strike gap while nothing hurts (`pursuit.py RUSH_THE_BOSS`).

### §4.9 Revivers

- Shamans and Hollow Ones raise their pack again and again. Kill them first (R 10-10 21:57).
- A reviver raising its pack is designated before a Herald (`combat/revivers.py REVIVERS_FIRST`).
- The Halls death (§7.1) had a Hollow One beside the T5 pack.

### §4.10 Doors, walls, line of sight, things that cannot be hit

- **What blocks what:**
  - Blades stop at walls. Closed doors block the strike; open ones do not (R 10-24 20:34; `levels/doors.py SHOT_LEAF`,
    `PASSED_OPEN`).
  - The sigil needs a clear line (§1.8). Death Mark needs none (§1.3).
- **A firing spot needs a clear shot** (`macros/sight.py clear_shot`). A Teleport that lands where nothing can be shot
  is a wasted move.
- **Expected damage that does not come is logged and looked into** (R 10-24 20:34). A monster that takes no harm for 3
  s, or cannot be shot for 3 s, is left; the fight is not (`macros/hunting/base.py NO_HARM_SECONDS`,
  `UNSHOT_SECONDS`).
- **Things we cannot hurt are not fought:** immortal Hydras, birds over cliffs, frogs underground (R 10-10 22:23,
  10-19 09:22).
- **Walls are also cover.** No death came with a wall between us and the pack (deaths.md, pattern 7).

### §4.11 The T5 pack's plan (`ENGAGE_PLAN`, 2026-10-26)

The player, 2026-10-26 ~09:10: "teleport to safe spot, once - move daemons to get aggro with DM between char and pack
- walk closer, behind the daemons that gets aggro - put sigil of lethargy where the main battle will occur - deliver
damage, focus herald or fast pack killing". The evidence is in rca/2026-10-26/herald-engage-findings.md:

- 196 T5 fights had 6.2 jumps each and 1.9 flip-flops each (firing spot ↔ keep range).
- 29 % of the marks were undone by a jump within 2 s.
- 188 of 457 sigils were more than 6 u off the melee.

`combat/engage.py` keeps one plan from look to look for a tier 5 pack:

1. **STANDOFF.** The pack is on the character. One jump out is allowed.
2. **MARK.** No voluntary jump, and one Death Mark key per phase:
   - on the nearest member if the pack presses;
   - else on the member whose mark lasts;
   - else on the Herald.
3. **CLOSE_IN.** Walk in, never jump, and stay behind the point where the demons hold the pack. The keep range's bars
   do not apply to that walk. The sigil goes on that contact point.
4. **STRIKE.** Strike. No mark on a member the strike is killing.

The plan goes back to MARK only on a lost aggro or a pack on the character. A danger jump, which always takes the
demons along, also sends it back to MARK. `Safety.real_threat` (the exempt hold) and every retreat stay above the plan.
For 1.5 s after a real threat the plan steps aside (`THREAT_SECONDS`): in the v1 canyon gate its mark after every
danger jump under javelins raised the deaths 6 → 14 of 80.

**Gate, 2026-10-26** (findings §4): not passed, so the plan is off.

- Herald scene: killed 100 of 100 against 83 of 100, 8.5 s sooner.
- The sigil is 1.0 u from the melee against 2.7.
- No new deaths in any scene.
- Halls and canyon made more jumps (7.2 → 9.2, 14.3 → 15.5). In MARK the plan holds the jump while the keep range
  bars the walk, so every act is vetoed and the vetoed-escape Teleport is made instead. That is fixed next.

---

## §5 Retreat and disengage

### §5.1 Once, far, then the mark

- **The rule.** When a retreat is needed, make **one** move that lands out of the pack's reach: 24-30 u, or behind a
  wall. The first act at that landing is the mark on the pack. Then walk back in behind the demons (§3.2).
- **Never a chain of short hops.** Each one drags the demons along and moves the fight with us (§2.1).
- **What it would have saved:**
  - The Fane: five retreat hops in 5 s, the demons stripped off the Herald every time, no mark after any.
  - The Flayer Dungeon: seven hops in 6 s inside an Extra Fast drain pack.
  - 17-22 u south of the Fane fight was open.
- **No mark before the retreat Teleport** (R 10-24 20:04). The mark goes at the landing where we stay.
- **A real threat still retreats at once:** surrounded, a hit taken, life under the floor. For a budget retreat at
  full life just after a mark, give the mark about 1 s to take the pack first. In teleports.md §4.4, at Baal's waves,
  17 of 27 hostiles aimed at the pets 0.16 s after the mark, and the retreat 0.74 s later brought them all back on us.
  Candidate `MARK_CREDIT` (not built).
- **Not built as a sequence.** `Safety.pack_back` hops "with the demons between", but nothing makes the mark come first
  at the landing of a retreat, and nothing stops a mark right before an escape (code-map.md §10).

### §5.2 The dance: what it costs and its budgets

**What the dance is.**
- Teleporting round a pack without kills, back and forth in a small area, or around monsters that do not attack.
- It earns nothing, and each hop loses the demons' aggro, so we take the hits that made us hop (R 10-22 18:17: "what
  is estimated exp/hour if we're jumping around without kills?").

**Measured over 46.9 h** (10-21 10:00 to 10-25 10:35, teleports.md §2). V:
- Episodes of 4+ fight Teleports within 15 s: 4,153, **88.6 an hour, 1,035 s an hour**. Most still kill: 2.0 kills a
  jump.
- Bounces (kills no more than a quarter of the jumps): 280, **6.0/h, 63 s/h**, 148 of them with no kill. Since 10-22
  the bounce seconds are 23-64 s/h, down from 107-122 s/h on 10-21.
- **Excess: 222 s/h** (205 recently). That is an episode's seconds minus its kills at the fight's mean kill rate, the
  ceiling for what the fixes can win.
- Where the excess goes (s/h over 4 days, recent in brackets):

  | class | s/h |
  |---|---|
  | progress hops (full clear, room tour) | 60 (59) |
  | better-place hops | 31 (44) |
  | safety-veto ping-pong | 31 (11) |
  | re-aggro failure: keep range "on the character", budget retreats | 19 (15) |
  | goal flips | 18 (19) |
  | keep range against Extra Fast | 15 (19) |
  | pickups | 15 (10) |
  | keep range against mana burn | 10 (7) |

- T4-5 packs were in 498 episodes, with 71 s/h excess (81 recent) and 128 of the 280 bounces.
- About 30 landings an hour, made by our own progress moves, are left at once by the keep range.

**The budgets** (all live):
- `macros/hunting/judging.py DANCE_BUDGET`: give a goal up after 5 s of dancing.
- `STILL_BUDGET`, `NET_PROGRESS`, `KNOT_PASSES_PLACE`, `DANCE_PASSES_PACK`.
- The hop caps `PACK_HOPS` 3 and `BURN_HOPS` 10.
- `RANGE_STALL_LIFT`: lifts the keep range when it stalls. It ended the canyon spin (306 s, 397 jumps, 5 kills).

**The cure is the mark, not more hops** (§3.6, then R1).

### §5.3 QUIET_HOLD

- **The case:** Harem Level 2, 10-25 03:35. A Magic Alpha Helm lay 18 u from an idle T5 Herald pack. The run's goal
  flipped between the helm and the Herald's fight at the strike's reach: 62 Teleports in 64 s, 0 kills.
- **The rule:** a side drop that the boss rule deferred 3 times within 10 s is left alone while that boss lives, for
  60 s at most. The fight's goal and its safety then stand, and the budgets count. A potion is never held.
- **State:** live since 04:27 (`macros/hunt.py QUIET_HOLD`; rca/2026-10-25/pickup-veto-pingpong-findings.md). Since
  then 5 goal-flip episodes in 1.9 h, all with kills.

### §5.4 STAND_NOT_RETREAT

- **The case:** the approach-retreat dance, 26 episodes and 1,865 s in 23.9 h. An idle pack priced every retreat and
  every stand at harm 0, and the retreat won on time. From its landing a safe approach fitted again, and from there
  every progress act was refused again.
- **The rule:** when no progress act fits only because of a keep range, stand rather than take a retreat that saves
  no harm. At most 6 s for one goal.
- **Not for:** a refusal by the life budget (Radament), or a draining pack.
- **State:** `macros/pursuit.py STAND_NOT_RETREAT`, off, under test (rca/2026-10-25/approach-retreat-findings.md).
- **The tactic adds the mark from the stand.** The pack goes to the demons, the keep range then finds nobody "on the
  character", and the approach is walked (teleports.md §4.5).

### §5.5 Better places after a mark

- **Better-place hops pay on the whole:** 2.79 kills a jump.
- **They lose near a pack the demons hold.** 28 % of the recent ones came within 1.5 s after a mark key, and 97 % of
  those pulled the sent demon back. One case (teleports.md §4.3): the bound demon stood 3 u off the pack and counted
  as a holder at the new place; the Teleport brought it beside us; the member at 9.8 u was then "on the character",
  and the keep range hopped.
- **After a mark: walk the better place, or strike from where we stand** (§3.6).

---

## §6 Survival

### §6.1 The death rules

- **Do not die.** A death costs hours of Hell experience and risks the gear (R 10-19 09:38, 10-21 20:04: "we must have
  top priority to no die ourselves and prevent loosing experience").
- **If we died, we press nothing at all.** No revive, no Save and Exit, nothing (R 10-19 09:39: "if we died - we MUST
  not take ANY other actions, no reviving, no save/exits, nothing at all we could lose all our gear if do something
  incorrectly"). Code: `macros/routines.py Dead` stops the loop and presses nothing.
- **Safety is part of exp/hour, not traded against it.** A death wipes hours. A stop or an idle stand halves a night.
  A "safe" dance with no kills earns nothing (R 10-24 20:27: "killing many mobs as fast as possible - do not die").
- **Never stand still under attack** (R 10-19 09:38, 10-21 21:12, 10-22 20:51).

### §6.2 Potions

The numbers are in §1.13. In fights:
- **The belt refills from the ground after a fight,** instead of diving on with low stock (R 10-14 23:02).
- **The safety margin grows as healing potions run low** (R 10-14 23:22: "Yes, scale it").
- **Potions were not the cause in four of the six deaths:** they were drunk on time, and the belt emptied because we
  stood in the pack. In the Fane the drink rule held a rejuvenation back, since fixed (deaths.md, pattern 6).

### §6.3 The arena gate for safety changes

A safety, retreat, potion, buff or mark change ships only after the arena gate (R 10-22 08:11: "we need to have proper
simulation with walls"; R 10-23 19:06):
1. The fatal fight is played in the arena (`tests/inventory_tracking/scenarios/arena`, cut from its take) with the
   level's real walls.
2. Switch off, it reproduces the danger; switch on, it survives: 20+ seeds, 20 of 20.
3. The other danger scenes are no worse.
4. T5 Herald kill time is no worse.
5. Kills a second on the arena scenes and on a replay of live logs are no worse.

Report the off/on tables, and do not restart until the gate passes.

**Arena limits that matter here:**
- It still models the take-along as "within 10 u" (fix: ALONG_ALL).
- It under-plays the pack turning to the demons after a mark: 0.36 → 0.45, against 0.51 → 0.73 live. So every
  mark tactic is under-credited there (deaths.md, "the arena's death cases").

---

## §7 Lessons

### §7.1 The six deaths

All are in [deaths.md](../../../rca/2026-10-25/tactics/deaths.md). There has been none since 10-23 23:31.

1. **Tower Cellar 5, 10-11 22:51.** A tier 2 Herald pack walked up while we stood 9.6 s clicking a potion at 65 %
   life, on the weak weapon set.
   - **Differently:** no pickup inside a pack; main weapons against a Herald. Fixed.
2. **Tal Rasha's Tomb, 10-18 00:54.** A T5 Apparition pack (Extra Fast, Mana Burn, cursing) spawned within 2-3 u of
   our 14 u stand. The mark came 1.9 s later, in contact.
   - **Differently:** stand at 24; sigil and strike on the spot first; mark the pack as it shows. Fixed in parts.
     Still not covered: a mark on the spawn as it appears while we stand.
3. **Disused Fane, 10-21 23:35.** Five retreat hops in 5 s each took the demons off the Herald, with no mark after any.
   The last move, a walk, left the pets behind and ran into a second pack as Battle Orders ran out.
   - **Differently:** one far disengage, then the mark at the landing, then walk in (§5.1). The escape and drink
     fixes are live; the mark parts (R1, R2) are off.
4. **Canyon of the Magi, 10-23 14:52.** T5 Hell Slingers. We stood 6 s at 21 u in the open with no mark. Then came a
   Teleport toward them and an 8 u keep-range hop inside their throws, after the cover had died.
   - **Differently:** mark from the stand at once; never Teleport into a shooter pack's reach; cover or 33+ u.
     **Still open** (`READ_THROWS` off).
5. **Flayer Dungeon 1, 10-23 18:57.** Six keep-range hops inside an Extra Fast drain pack dragged the demons along
   each time. A plain Dark Shape's blow burned the mana, and with no mana there was no escape.
   - **Differently:** leave far with the mana kept, mark once from there; give up a physical-immune drainer. Mostly
     fixed (`MANA_ESCAPE`).
6. **Halls of the Dead 2, 10-23 23:31.** The run lost its fight goal and stood 21 s in a T5 pack under Amplify Damage
   with no strike. Before that, two Blade Warps back into the pack for gold.
   - **Differently:** the fight stays the run's goal; no gold in a T5 pack; mark from the clear landing at −22 s.
     Fixed.

**What the six share:**
- **The pets were with us, not on the pack, at the end**, every time.
- **No mark after the last move.** The last marks came 9-28 s before the death, or in contact.
- **Teleports moved the fight instead of ending it.**
- **The forecast saw less than came.**
- **Amplify Damage on us in five of the six.**
- **No death with a wall between us and the pack.**

### §7.2 The near-deaths

70 survived episodes in 67 h, 1.04 a level-hour; 8 of them under 35 % life. All are in
[near-death.md](../../../rca/2026-10-25/tactics/near-death.md).

- **P1, dolls** (38 episodes, 52 % of the life lost). A jump, the pets along, a doll blast at 2.2 u a median 0.76 s
  after the landing.
  - **Differently:** bait with a mark and walk (§4.4); no killing blow within 6; no escape timed against a dying doll.
- **P2, a T5 pack on us at its spawn** (18 episodes). We stood at the spot, or Teleported toward it 1-5 s before the
  spawn. Ranged and Extra Fast packs reached the 24 u stand.
  - **Differently:** no move toward the spot; the mark first from the stand; cover against shooters (§4.3).
- **P3, keep-range hops landing in the pack** (11 of 28 T5 episodes). After 3 hops, nothing more.
  - **Differently:** with the demons holding nothing, mark first, then step out (§4.3, §3.6).
- **P4, mana burn takes the escape** (H8: 597 → 0).
  - **Differently:** open from 30+, leave before the mana is under one Teleport and one mark (§4.6).
- **P5, walking into an unseen ranged pack.**
  - **Differently:** mark what is on the screen, then walk (§4.5).

### §7.3 Too many Teleports, aggro not kept

All are in [teleports.md](../../../rca/2026-10-25/tactics/teleports.md).
- **The hop after the mark is the commonest failure:** 152 an hour pulled a just-sent demon back.
- **The keep range is judged with demons that are about to come with us.**
- **Budget retreats fire 0.35-0.74 s after a mark,** before the pack has turned.
- **Differently:** mark, hold the jumps until the demons land, walk; correct the take-along model (§3.6, §2.1, §8).

---

## §8 Status

**As of 2026-10-25 10:58**, read from the working tree. The running `serve` may be on another revision. Planned
items are being built by the apply agent, one switch each, behind the §6.3 gate (journal 10-25 ~10:57). **Live** = on;
**off** = built behind a switch that is off; **missing** = no code; **planned** = being built.

| § | tactic | state | switch | file |
|---|---|---|---|---|
| 1.1 | line sweep through the pack | live | — | `builds/warlock/echoing_strike/attack.py` |
| 1.1 | lead moving targets | off | `LEAD_MOVING` | same |
| 1.1 | pointer on the held leader's body | live | `HELD_ON_BODY` | `macros/hunt.py` |
| 1.1 | no line to what walks out of reach | off (ready) | `ARRIVAL_REACH` | `echoing_strike/attack.py` |
| 1.2 | own Teleport (Enigma) first | live | — | `builds/warlock/movement.py`, `macros/movement.py` |
| 1.2 | camp hop priced at Enigma's 0.31 s | missing (stale 1.5 s) | `HOP_SECONDS` | `combat/stance.py` |
| 1.4 | Defiler kept out, mana paid | live | `DEFILER_PAYS` | `builds/warlock/defiler.py` |
| 1.5 | Bind Demon by the macros | off (player's ruling) | `BIND_DEMON_CASTS` (makes `REBIND_DEMON` moot) | `builds/warlock/bind.py` |
| 1.6 | Consume renewed, deferred at an omen | live | `CONSUME_BREAKS`, `CONSUME_OMEN_DEFER` | `casters.py`, `buffs.py` |
| 1.7 | Engorge: pet in danger first, pack first | live | `PET_ENGORGE`, `ENGORGE_PACK_FIRST`, `PET_DEMONS_ONLY` | `buffs.py`, `pets.py` |
| 1.7 | pull the fight off the bound demon | live | `PET_PULL`, `PULL_ONCE_OUT` | `pets.py` |
| 1.8 | sigil kept on hard enemies | live | `SIGIL_KEEPS` | `buffs.py` |
| 1.8 | sigil only in sight | live | `SIGIL_SIGHT` | `casters.py` |
| 1.8 | opener sigil before the first strike | off | `SIGIL_OPENER` | `buffs.py` |
| 1.9 | broken ward first | live | `WARD_BROKEN_FIRST` | `buffs.py` |
| 1.10 | Battle Orders predicted, rebuff retreat | live | `REBUFF`, `ORDERS_PREDICT`, `REBUFF_RETREAT` | `macros/cta.py`, `macros/safety.py` |
| 1.13 | emergency rejuvenation | live | `EMERGENCY_REJUVENATION` | `combat/survival.py` |
| 1.13 | no potion stop in a pack | live | `GATHER_CLEAR` 12, `POTION_HELD` | `macros/hunting/base.py`, `hunting/choice.py` |
| 2.1 | every pet comes along on any jump (model) | **planned** | `ALONG_ALL` (today `TAKEN_ALONG` 10, wrong) | `combat/pack.py`, arena `game.py` |
| 2.2 | Blade Warp escorts the merc out | live | — | `combat/escort.py` |
| 3.3 | mark first at a T5 landing | live | `HERALD_MARK_FIRST`, `HERALD_MARK_ANY_MEMBER` | `combat/pack.py` |
| 3.3 | mark after every move in a hard fight (R1) | off (gate done, waits on the player) | `DM_AFTER_EVERY_MOVE` + `DM_MOVE_NO_BURN` | `combat/pack.py` |
| 4.11 | the T5 pack's plan: one jump out, mark, walk in, sigil at the contact, strike | off (gate 2026-10-26: Herald +, halls/canyon more jumps; not passed) | `ENGAGE_PLAN` | `combat/engage.py` |
| 3.3 | no T5 landing mark in a burn fight | off | `HERALD_MARK_NO_BURN` | `combat/pack.py` |
| 3.3 | mark members on the screen at a landing | off | `LANDING_MARK` | `macros/hunt.py` |
| 3.3 | mark before the strike at any landing | off, **not wired** | `MARK_AT_LANDING`, `LANDING_IN_PACK` | `combat/pack.py` |
| 3.3 | leaders and Heralds first | live | `MARK_LEADERS` | `builds/warlock/mark.py` |
| 3.3 | no mark through the cast hold | off (after a Fane arena death) | `INSTANT_THROUGH` | `macros/hunt.py` |
| 3.3 | no mark before a retreat Teleport | missing | — | — |
| 3.4 | one designation | live | `DESIGNATED_MARK` | `mark.py` |
| 3.4 | pack re-aggro with nobody designated | live | `REAGGRO_PACK` | `mark.py` |
| 3.4 | re-aggro when a designation is already held | missing | — | `mark.py` |
| 3.6 | mark holds jumps (0.4 s hold, 1.5-2 s walk) | **planned** | `MARK_HOLDS_JUMPS` | — |
| 3.6 | re-aggro by the mark, not a hop | off, no test | `REAGGRO_BY_MARK` | `combat/pack.py`, `macros/safety.py` |
| 3.6 | price the hop's drag | off, **not wired** | `HOP_DRAG_PRICE` | `combat/pack.py` |
| 3.6 | mark through the hold | off, **not wired** | `MARK_THROUGH_HOLD` | `combat/pack.py` |
| 4.1 | firing stand | live | `FIRING_STAND` | `macros/hunting/base.py` |
| 4.2 | mark from range, then walk in (R2) | off | `MARK_THEN_WALK` | `combat/pack.py`, `macros/hunting/moves.py` |
| 4.3 | Herald pack tactic, keep range 14-18 | live | `PACK_TACTIC`, `PACK_KEEP_RANGE` | `combat/pack.py` |
| 4.3 | places and landings keep the range | live (with the take-along defect) | `PLACES_KEEP_RANGE`, `PACK_RANGE_LANDING`, `RANGE_LEAD` | `combat/pack.py`, `macros/safety.py` |
| 4.3 | omen stand 24, way out | live | `PACK_OMEN`, `PACK_OMEN_STAND`, `STAND_WAY_OUT`, `OMEN_HOLD` | `combat/pack.py`, `hunting/base.py`, `macros/agenda.py` |
| 4.3 | sigil and strike on the spawn spot | live | `OMEN_SIGIL`, `OMEN_STRIKE` | `buffs.py`, `macros/hunt.py` |
| 4.3 | no move toward the spawn spot (R-H1) | missing (waits for agenda.py to be free) | — | — |
| 4.3 | stand with cover against ranged / Extra Fast T5 (R-H3) | missing | — | — |
| 4.3 | T5 best line | live | `T5_BEST_LINE` | `echoing_strike/attack.py` |
| 4.3 | hold a leader till it dies | live | `HOLD_LEADER` | same |
| 4.3 | sigil at the densest disc, demons between, Defiler from range | live | `SIGIL_COVER`, `PETS_BETWEEN`, `DEMON_GATE` | `combat/pack.py` |
| 4.3 | the fight holds for a Herald pack | live | `PACK_FIGHT_FIRST`, `HERALD_KEPT` | `hunting/judging.py`, `macros/agenda.py` |
| 4.3 | skip a refused T5 pack | off | `T5_SKIP` | `hunting/judging.py` |
| 4.3 | no gold in a T4-5 pack | live | `PACK_GOLD_WAIT` | `macros/pickup.py` |
| 4.4 | doll Herald first | live | `DOLL_HERALD_FIRST` | `mark.py`, `macros/cta.py` |
| 4.4 | doll bait: mark, walk to 12 | off | `DOLL_BAIT` | `combat/threats/dolls.py` |
| 4.4 | no landing near a live doll | off | `DOLL_LAND` | same |
| 4.4 | dolls struck first | off | `DOLL_FIRST` | same |
| 4.4 | escapes near dolls barred | live | `DOLL_ESCAPES` | `macros/safety.py` |
| 4.4 | no killing blow within 6 (R-D1), no escape timed on a blast (R-D3) | missing | — | — |
| 4.5 | read and price the throws | off (kills 8.4 → 2.2) | `READ_THROWS` | `combat/bolts.py` |
| 4.5 | Teleport out of throwers' lines | live, inert without `READ_THROWS` | `THROWN_OUT` | `macros/pursuit.py` |
| 4.6 | burn / Extra Fast / caster keep range 18 | live | `BURN_RANGE`, `FAST_RANGE`, `CASTER_RANGE` | `combat/threats/manaburn.py` |
| 4.6 | mana floor, burners only | live | `MANA_FLOOR`, `LEAVE_BURNERS_ONLY`, `MANA_REJUVENATION` | same |
| 4.6 | drain escape | live | `MANA_ESCAPE` | `combat/threats/drain_escape.py` |
| 4.6 | give up a physical-immune drain pack | missing | — | `hunting/judging.py` |
| 4.8 | Diablo: walk round | live | `WALK_AROUND`, `WALK_ROUND` | `combat/threats/diablo.py`, `macros/safety.py` |
| 4.8 | rush the run's boss | live | `RUSH_THE_BOSS` | `macros/pursuit.py` |
| 4.9 | revivers first | live | `REVIVERS_FIRST`, `REVIVER_OWN_RUN` | `combat/revivers.py`, `hunting/revive.py` |
| 4.10 | closed doors block, open pass | live | `SHOT_LEAF`, `PASSED_OPEN` | `levels/doors.py` |
| 4.10 | Teleport over a clear line on LINE levels | live | `TELEPORT_LINE` | `levels/reach.py` |
| 5.1 | retreat away from the pack, clearest jump when all is vetoed | live | `RETREAT_AWAY`, `VETOED_ESCAPE`, `REACH_LIFT` | `macros/pursuit.py` |
| 5.1 | mark first at a retreat's landing | missing (R1 would cover it in hard fights) | — | — |
| 5.1 | a just-sent mark delays a budget retreat | missing (candidate) | `MARK_CREDIT` | — |
| 5.2 | dance and still budgets | live | `DANCE_BUDGET`, `STILL_BUDGET`, `NET_PROGRESS` | `macros/hunting/judging.py` |
| 5.2 | keep range lifted when it stalls | live | `RANGE_STALL_LIFT` | `macros/safety.py` |
| 5.3 | quiet hold | live | `QUIET_HOLD` | `macros/hunt.py` |
| 5.4 | stand, not retreat | off (under test) | `STAND_NOT_RETREAT` | `macros/pursuit.py` |
| 6.1 | nothing pressed after a death | live | `Dead` | `macros/routines.py` |
| 6.1 | reach bar, one cast a look near one-shotters | live | `REACH_BAR`, `WALK_REACH`, `FIGHT_CAST_REACH` | `macros/safety.py`, `macros/hunt.py` |

---

## §9 Open questions for the player

From [dialogues.md](../../../rca/2026-10-25/tactics/dialogues.md) (b), with what the measurements now add.

1. **"Allows to safe tp back."** Every Teleport brings the demons back to us, from any distance (§2.1). So the safe
   order is Teleport back first, then the mark, then walk in. Is that what you meant, or did you expect the demons to
   stay on the pack after our Teleport?
2. **How to retreat without pulling the demon.** If surrounded we retreat, but any Teleport takes the demon off the
   pack (§5.1). Is the retreat always "one far Teleport, then the mark again", or do we walk back while the mark holds?
3. **The first mark near mana burners.** In the arena the mark after every hop doubled the deaths there. You doubted
   the test (10-24 20:04: "why DM first even could be a bad idea?"). Mark once from 30+ u, or the burn leave first?
4. **How often to mark regular enemies.** "Not every second" (10-24 20:26). Today: hard fights (§3.3), immunes,
   leaders. Is that the right line?
5. **Walk-in distance.** Keep the pack at 14-18 (10-21), or walk to the engage ring of about 13.9, or closer, once the
   demons hold it (10-24)?
6. **Omen stand: 22 or 24 u**, and for ranged or Extra Fast T5 packs a wall corner or 30+ u (§4.3)?
7. **R1 is gated and waits on your word.** It is the mark after every move in a hard fight. Herald deaths 2 → 1, but
   dolls −10.6 kills a minute, and post-Teleport marks pull the pack out of the Herald's sigil (journal 10-25 02:05,
   02:48). Flip it, together with MARK_HOLDS_JUMPS?
8. **Mana.** No mana potions. When is a rejuvenation for mana right (10-21: "in a very scary moments")? And when do we
   stay and strike for leech, rather than escape a burner?
9. **The bound demon dies mid-run.** You bind it yourself (10-21). Does the run go on with the Defiler alone, or go to
   town, or wait for you?
10. **The life budget's form.** The 65 % floor was accepted as recommended. Is a hard cap right (10-12: "I'm not sure
    if hardcap will fell good")?
11. **Special tactics per monster type.** You asked for cows, archers and "nasty heralds" (10-12). Only dolls and
    Diablo have one. Which next?
12. **Striking the spawn spot before the pack shows** "makes them lose hit recovery" (10-23). That is not measured
    yet. Keep it as is?
13. **Fast travel vs engaging** (10-12): when does a run's Teleport chain become an engagement, so the fight rules
    apply?
