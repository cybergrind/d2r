# macros/pickmode.py — rulings and market evidence (moved from the module, 2026-10-19)

## Rulings behind the modes

- 2026-10-16: "by default only 100% valuables (rare rings, known good uniques, all runes, all gems, all charms). and
  can switch for pickup regular - what do we have right now"; "we pickup gold, we need it to repair our staff of
  teleportation"; later that day: "make sure that we still pickup all jewels".
- 2026-10-17: "rare amulets - also pickup". The read finds jewelry as a material, so a set or unique one is not the
  loot filter's `NAMED` and is taken by the sure mode (a set Amulet was left at 08:10:10). "+ pickup worldstone
  shards/other valuable drops". "good void base with +3 for example".
- 2026-10-17: "picking items with +skill, identifying them, appraising, selling [bad ones] and repairing on these
  money". The trade goods were in the sure mode while gold paid the staff's Teleport charges.
- 2026-10-18 (Enigma): "because we now don't need gold anymore ... move things that we're added for gold trades (to
  repair our staff charges) into separate category ... and use sure for valuable things or small things" → `TRADE`.

## SKILLED (types that roll skills)

The player, 2026-10-17: "the most gold cost is weapons and items that can give +skills (35k for good rolls)
blades/daggers/necro/sorc, also class specific offhands can roll"; at 13:36: "high-value trade only". Sales
11:26-13:36 on 2026-10-17 (trade.py), gold a sale: Paladin shields 32.5k, rare daggers 35k, claws 22.5k, magic
daggers 20.2k (15), circlets 15.4k, grimoires 14.1k (11), Barbarian helms 13.3k (10), Druid pelts 12.4k; magic
amulets 2.2k (8) and Amazon javelins 1.1k — so the Amazon's bows, spears and javelins and magic amulets were dropped.
Wands, heads, orbs, scepters kept untried (the player's "necro/sorc ... class specific offhands").

## Void bases

Bases from items metadata (2026-10-17): Kriss, Blade, Cinquedeas, Stilleto, Fanged Knife, Legend Spike; the others of
the line hold one socket at most. The player, 2026-10-17 18:56: "we're storing daggers with 1os ... we need good staff
mod and we need 3os; we shouldn't waste shared stash tab". At 19:40: "0 socket +3 abyss - let's pickup them" (sockets
by Larzuk's quest).

Market (scoped Traderie asks, fills and buyers, pulls of 2026-09-18 to 10-09): a white or superior 3os base with +3
Abyss asked a median 11.4 Ist (32 sellers) and filled at 8.2 (23); +3 Hex: Purge filled at 17.5 (7); 14 and 4 of 26
buyers want them, every other skill one or none; +2 at best filled at 1.0-1.4. 1os and 2os bases had no market; elite
bases no premium of their own. Abyss = Traderie property 1579, Hex: Purge 1566.

## Monarchs and Paladin shields

The player, 19:10 on 2026-10-17: "start picking up monarchs (for 4os deflecting) and sacred targes (check what are
expensive ones)". Market study of 19:15 on 2026-10-17 (scoped Traderie, 2026-09-18 to 10-09): a Monarch normal 4os
asked 0.79 Ist (16 sellers), superior under 15% ED 4os 2.0 (5), superior 15% ED 4os 17.1, 0os 11.4 (Larzuk), eth 137
(thin, asks only); magic 4os 28.6 (14), of Deflecting 103 (8). Sacred Targe 45 all res asked 11.4 (4os, 12; fills
11.4-17.3), 40.6 (3os, 12; fills 34.3), eth 68.5 (fills 34.3-45.7); 40-44 all res 3/4os filled 2.0-11.4; under 40
1.0. Sacred Rondache 45 4os 5.9, eth 45.7, superior 15% ED 114; 40-44 1.6.

## sellable

- 2026-10-17 11:25: "you can sell identified junk charms".
- 17:45: "we're storing every 3os dagger, while in reality we need something that is really good for void" (the
  appraisal prices sockets and Warlock skills: pricing/triage `void-three-socket`).
- 19:06: "actually, we can sell trash jewels/rings/amus".
- 2026-10-18 11:10: "we should sell junk rings and other junk items; imporant!: do not sell own equipment or valuable
  items". Never a charm of set/unique quality: the Sunders, Gheed's, Annihilus and the Torch are the loop's quarry
  whatever a price says.
- 2026-10-19 21:55: a magic Matriarchal Javelin the loot filter showed was appraised `vendor` at Cain, but `sellable`
  took magic and rare items only of the skill types, charms, jewels and jewelry, so it was stashed as a keeper (shared
  page 1) and not sold; the player: "we had put trash item for sale and forgot to pick it and sell". Every magic or
  rare item but a rune, gem or the Crafted Sunder Charm is now `sellable`; the appraisal's `vendor` decides.
