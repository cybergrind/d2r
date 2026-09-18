# WP-A — builds → runewords → bases (and blues)

Scope: the 26 S/A builds of the maxroll overall tier list (May 22, 2026; 15 S, 11 A; S=2, A=1 weight). Every guide page fetched 2026-09-18; tables parsed with a boundary-preserving parser (tables.py collapses the double spaces). Files: `wp-a-builds.json` (per build: gear table slots + mercenary table), `wp-a-bases.json` (62 bases), `wp-a-blues.json` (169 magic/rare/crafted/charm patterns), `wp-a-runewords.json` (71 runewords, extra hand-off). Classification of the 2730 item mentions: unique 1170 · runeword 744 · magic_rare 261 · set 228 · magic_charm 131 · crafted 69 · gemmed_base 60 · charm_base 51 · misc 6 · unresolved 4 · skip 3 · base 3 (unresolved = 3 distinct names, listed below). 24 guides have a mercenary table (15 "Slot|Early/Mid/End", 8 "Gear Level|…", 1 header-less); dragon-talon and smite have prose-only mercenary sections (added by hand, cited in the JSON).

## Top-20 bases by demand weight (weight = Σ build weights over builds naming a runeword that the runewords page recommends for the base, or naming the base explicitly)

| # | base | weight | builds char/merc | sockets needed (by runeword) | eth | runewords driving demand | other mentions (gemmed/plain) |
|--:|---|--:|---|---|---|---|--:|
| 1 | Archon Plate | 41 | 25/22 | Bramble 4, Chains of Honor 4, Fortitude 4, Dragon 3, Enigma 3 | mixed (char non-eth / merc eth) | Enigma, Chains of Honor, Fortitude, Dragon, Bramble | 0 |
| 2 | Crystal Sword | 41 | 26/5 | Call to Arms 5, Spirit 4, Crescent Moon 3, Lawbringer 3, Plague 3 | mixed (char non-eth / merc eth) | Spirit, Plague, Call to Arms, Lawbringer, Crescent Moon | 12 |
| 3 | Diadem | 41 | 24/24 | Bulwark 3, Coven 3, Cure 3, Dream 3, Flickering Flame 3, Ground 3, Hearth 3, Temper 3, Wisdom 3, Lore 2 | mixed (char non-eth / merc eth) | Lore, Bulwark, Temper, Ground, Cure, Wisdom, Dream, Flickering Flame… | 0 |
| 4 | Dusk Shroud | 41 | 25/22 | Chains of Honor 4, Fortitude 4, Dragon 3, Enigma 3 | mixed (char non-eth / merc eth) | Enigma, Chains of Honor, Fortitude, Dragon | 14 |
| 5 | Flail | 41 | 26/0 | Call to Arms 5, Heart of the Oak 4, Black 3 | non-eth | Heart of the Oak, Call to Arms, Black | 0 |
| 6 | Mage Plate | 41 | 19/25 | Bone 3, Duress 3, Enigma 3, Enlightenment 3, Hustle 3, Hysteria 3, Lionheart 3, Peace 3, Principle 3, Rain 3, Treachery 3, Wealth 3, Smoke 2 | mixed (char non-eth / merc eth) | Enigma, Smoke, Lionheart, Treachery, Duress, Wealth, Hustle, Principle… | 0 |
| 7 | Colossus Voulge | 40 | 3/25 | Insight 4 | eth | Insight | 0 |
| 8 | Giant Thresher | 40 | 5/25 | Obedience 5, Infinity 4, Insight 4, Pride 4 | eth | Insight, Infinity, Pride, Obedience | 0 |
| 9 | Matriarchal Bow | 40 | 12/25 | Mist 5, Faith 4, Harmony 4, Insight 4, Hustle 3, Mania 3 | mixed (char non-eth / merc eth) | Insight, Harmony, Hustle, Faith, Mania, Mist | 0 |
| 10 | Thresher | 40 | 5/25 | Obedience 5, Infinity 4, Insight 4, Pride 4 | eth | Insight, Infinity, Pride, Obedience | 0 |
| 11 | Berserker Axe | 39 | 9/21 | Breath of the Dying 6, Beast 5, Death 5, Doom 5, Fortitude 4 | mixed (char non-eth / merc eth) | Fortitude, Breath of the Dying, Doom, Beast, Death | 0 |
| 12 | Monarch | 39 | 25/2 | Phoenix 4, Spirit 4 | mixed (char non-eth / merc eth) | Spirit, Phoenix | 9 |
| 13 | Sacred Targe | 39 | 25/2 | Exile 4, Phoenix 4, Spirit 4, Dream 3, Sanctuary 3 | mixed (char non-eth / merc eth) | Spirit, Phoenix, Sanctuary, Dream, Exile | 0 |
| 14 | Phase Blade | 37 | 18/14 | Last Wish 6, Silence 6, Unbending Will 6, Grief 5, Hand of Justice 4, Kingslayer 4, Phoenix 4, Crescent Moon 3, Hustle 3, Lawbringer 3, Mania 3, Plague 3, Venom 3 | mixed (char non-eth / merc eth) | Plague, Grief, Unbending Will, Hustle, Phoenix, Lawbringer, Crescent Moon, Hand of Justice… | 3 |
| 15 | Bone Shield | 32 | 19/0 | Rhyme 2, Splendor 2 | non-eth | Splendor, Rhyme | 0 |
| 16 | Sacred Armor | 32 | 5/19 | Bramble 4, Fortitude 4 | eth | Fortitude, Bramble | 0 |
| 17 | Targe | 32 | 19/0 | Ancient's Pledge 3, Rhyme 2, Splendor 2 | non-eth | Splendor, Ancient's Pledge, Rhyme | 2 |
| 18 | Mask | 31 | 1/0 | Wisdom 3 | n/a | Wisdom | 19 |
| 19 | Preserved Head | 31 | 18/0 | Rhyme 2 | non-eth | Rhyme | 0 |
| 20 | Mancatcher | 27 | 2/17 | Obedience 5, Infinity 4, Pride 4 | eth | Infinity, Pride, Obedience | 0 |

Eth flags come from the runewords page wording ("Ethereal Superior Giant Thresher" → eth; "Superior Monarch" → non-eth; "Treachery: Superior Mage Plate (Character) / Ethereal Mage Plate (Mercenary)" → mixed) plus the sentence "Ethereal gear is preferred since it doesn't lose durability." that opens the Mercenary Gear Options section of 18/26 guides. Superior preference: the page writes "Superior" on every character weapon/armor/shield base above (Archon Plate, Dusk Shroud, Mage Plate, Monarch, Sacred Targe, Phase Blade, Berserker Axe) and on the merc polearms; plain "Crystal Sword", "Flail", "Diadem", "Bone Shield", "Targe", "Kite Shield" and the Stealth armors are written without it. Grimoires: no S/A build names Vigilance, so no grimoire base carries weight (see RotW below).

## Top blues (magic / rare / crafted patterns named in gear tables; weight as above)

| pattern | kind | weight | builds | slot(s) | affix words in the name / guide notes |
|---|---|--:|--:|---|---|
| Rare Ring | magic_rare | 37 | 23 | Rings |  |
| Caster Crafted Amulet | crafted | 30 | 18 | Amulets |  |
| Rare Boots | magic_rare | 29 | 17 | Boots |  |
| Staff of Teleportation | magic_rare | 18 | 11 | Weapon-Swap |  |
| Caster Crafted Belt | crafted | 16 | 10 | Belts |  |
| Fortuitous Ring of Fortune | magic_rare | 16 | 9 | Rings | Fortuitous, of Fortune |
| Rare Diadem | magic_rare | 16 | 9 | Helmets |  |
| Rare Gloves | magic_rare | 16 | 10 | Gloves |  |
| Shimmering Small Charm of Vita | magic_charm | 13 | 8 | Charms | Shimmering, of Vita |
| Blood Crafted Ring | crafted | 12 | 8 | Rings |  |
| Rare Belt | magic_rare | 12 | 7 | Belts |  |
| Jeweler's Monarch of Deflecting | magic_rare | 11 | 6 | Off-Hand, Off-Hand-Swap | Jeweler's, of Deflecting — (4x Rainbow Facet Jewel ) [blizzard-sorceress] |
| Resistance Small Charm | magic_charm | 11 | 7 | Charms | Resistance |
| Shimmering Small Charm | magic_charm | 11 | 7 | Charms | Shimmering |
| Shimmering Small Charm of Good Luck | magic_charm | 11 | 7 | Charms | Shimmering, of Good Luck |
| Small Charm of Good Luck | magic_charm | 11 | 7 | Charms |  |
| Small Charm of Vita | magic_charm | 11 | 7 | Charms |  |
| Caster Crafted Boots | crafted | 9 | 5 | Boots |  |
| Resistance Grand Charm | magic_charm | 9 | 6 | Charms | Resistance |

Each row's "Desirable Stats" text is kept per build in `desirable_stats_from_guides`. Named blue patterns that matter for Anya/pickup: Jeweler's Monarch of Deflecting (6 builds, 4× Rainbow Facet), Jeweler's Sacred Armor of Stability (merc, 3 builds), Jeweler's Dusk Shroud of Precision/Stability, Artisan's/Jeweler's Diadem of Speed/Nirvana/Luck, Cunning Greater Talons/Claws of Quickness (assassins), Lancer's Matriarchal Javelin of Quickness + Lancer's Chain Gloves of Alacrity (Lightning Fury/Strike), +Teleport/Lower Resist charge items (Staff/Amulet/Wand — 18/9 weight), Cobalt/Coral Gloves of Alacrity, Garnet/Coral Belt of the Squid, Ruby/Sapphire Boots of Acceleration, Fortuitous Ring of Fortune (9 builds, MF), Gaean/Forbidden/Glacial Diadem of the Magus, Powered Eldritch Orb of the Magus, Echoing Balanced Knife and Rare Kris (Warlock daggers), Venomous Demon Head, Gaean Antlers of the Colossus. Charms: class-prefix GCs (Sparking, Fungal, Harpoonist's, Natural, Entrapping, Sharp, Steel) with of Vita/Balance/Inertia; Shimmering/Resistance/Fine small charms of Vita/Good Luck.

## Mania / Hysteria — settled

* maxroll **New Items in Reign of the Warlock** (Last Updated February 19, 2026): "The Reign of the Warlock expansion features **5 new Runewords**: Authority (Body Armor, Hel-Shael-Ral), Coven (Helmets, Ist-Ral-Io), Void (Daggers, Thul-Zod-Ist), Vigilance (Grimoires/Shields/Voodoo Heads/Auric Shields, Dol-Gul), Ritual (Daggers, Amn-Shael-Ohm)". Mania and Hysteria are not on that page.
* maxroll **Runewords** page (Last Updated June 2, 2026, changelog ends Feb 2023; fresh fetch identical to cache) lists none of the seven; it still lists **Hustle** twice: Weapons (Shael-Ko-Eld, Socketed (3), bases Phase Blade / Matriarchal Bow / Hunter's Bow) and Body Armors (Shael-Ko-Eld, Socketed (3), base Superior Mage Plate).
* diablo2.io runeword pages (fetched 2026-09-18): Hustle — "Update on 11th February 2026 - after the release of Reign of the Warlock, Hustle can still only be crafted on ladder. **Hustle also got renamed to Hysteria for armor and Mania for weapons**." Mania — "Mania is the Weapons version of Hustle, as of the release of the Reign of the Warlock expansion. As of patch 3.3, Mania can be made in Non-Ladder on RotW." Hysteria — "Hysteria is the Body Armor version of Hustle …". Both tagged "Patch 3.0 Runeword · New in RotW", Shael Ko Eld, req 39, 3 sockets; their stat lines equal maxroll's two Hustle entries.
* Runeword tier list (Feb 18, 2026) ranks Mania A and Hysteria B; the Lightning Fury guide (S) names "Mania" (Weapon-Swap) and "Hysteria" (Body Armor) in its gear table, while 3 char + 8 merc tables in other guides still say "Hustle".
* **Answer:** 5 runewords are new item designs in RotW; Mania and Hysteria are the RotW names of the 2.6 Hustle (weapon / body-armor halves), so 7 names are "RotW-only" but only 5 are new. Bases: Mania = Phase Blade / Matriarchal Bow / Hunter's Bow (3 os), Hysteria = Superior Mage Plate (3 os), copied from the maxroll Hustle entries. RotW runeword base resolution: **Void** → Legend Spike (Echoing Strike Warlock guide, Aug 26, 2026: "Void Legend Spike is used for four reasons"; Abyss guide also lists a "Rare Kris"; dagger classes per maxroll base-items: Dagger/Poignard/Bone Knife, Dirk/Rondel/Mithril Point, Kris/Cinquedeas/Fanged Knife, Blade/Stiletto/Legend Spike), 3 sockets (3 runes; diablo2.io "3 socket"). **Coven** → Diadem (Fire Warlock guide "Coven Diadem"), 3 os. **Authority** → Body Armor, no base named by any guide, 3 os. **Ritual** → Daggers (same classes), 3 os, F tier, no S/A build. **Vigilance** → Grimoires (Grimoire/Compendium/Tome/Codex/Old Book · Possessed Grimoire/Possessed Compendium/Dark Tome/Dark Codex/Burnt Text · Blasphemous Grimoire/Blasphemous Compendium/Occult Tome/Occult Codex/Forgotten Volume), shields, voodoo heads, auric shields; 2 os; D tier, no S/A build.

## Unresolved / verify

* "Magic Find Monarch" (Blizzard & Meteor Sorc, Off-Hand-Swap) and "Resistance Mask" (Smite merc) — ambiguous d2planner labels (socketed base? magic item?); left unclassified.
* "Shadow Mark Amulet" (Fire Warlock, Amulets) — not on the maxroll new-items page nor in any unique/set id map; could be a RotW unique missing from the Feb-19 page. Verify.
* Socket counts for the 5 RotW runewords are the rune counts (maxroll new-items has no "Socketed (n)" line) confirmed by diablo2.io "N socket"; no maxroll "Recommended Base" exists for them.
* Whether "Hustle" can still be made under that name in NL RotW (diablo2.io: Hustle "can still only be crafted on ladder"; Mania/Hysteria "as of patch 3.3 … Non-Ladder on RotW"). diablo2.io says "patch 3.3" while plan.html says 3.1.x — patch numbering to verify in-game.
* Weight caveat: early-game merc helmets (Lore/Bulwark/Temper/Ground/Cure) resolve to "Diadem" because that is the page's recommended base; in practice any 3-socket helm works ("Any Barbarian Helmet or Druid Pelt with +x to Skills"). Same for Stealth armors and Rhyme (Bone Shield/Preserved Head/Targe). Treat those rows as low-value demand.
* Insight/Infinity appear as *character* weapons in the three Warlock guides and Nova/Lightning-Strike guides — as written in their gear tables; not a parser error.
* The maxroll base-items page (May 12, 2024) is pre-RotW; it was used only as a name list for pre-existing bases. Grimoire names come from the new-items page.
* "Ethereal for style" (CtA/HotO Flail, Crystal Sword) and "Ethereal Spirit Monarch" (Lightning Sorc char, Dragon Talon merc) are recorded verbatim; eth is not asserted as required.

## Sources used (all fetched 2026-09-18 via pricing/tools/fetch.sh; cached under pricing/raw/)

* maxroll overall tier list — https://maxroll.gg/d2/tierlists/overall-tier-list (Last Updated May 22, 2026); tiers re-extracted from the page (15 S / 11 A / 14 B / 11 C / 5 D / 2 F).
* 26 build guides https://maxroll.gg/d2/guides/<slug> — Last Updated: May 22, 2026: the other 21 guides; August 26, 2026: echoing-strike-warlock-guide; May 27, 2026: fire-warlock-guide; June 6, 2026: mirrored-blades-warlock-guide; July 9, 2026: smite-paladin; July 18, 2026: strafe-amazon.
* maxroll Runewords — https://maxroll.gg/d2/items/runewords (Last Updated June 2, 2026): 88 entries parsed (name, section, runes, "Socketed (n)", Recommended Base Item(s) with (Character)/(Mercenary)/(Ethereal for style) notes).
* maxroll New Items in RotW — https://maxroll.gg/d2/items/new-items-in-reign-of-the-warlock (Feb 19, 2026): 5 runewords, 15 grimoire bases, new uniques/sets (used for name resolution: Hellwarden's Will, Bloodpact Shard, Sling, Opalvein, Entropy Locket, Gheed's Wager, Wraithstep, Ars …, Horazon's …, Bane's …).
* maxroll Runeword tier list — https://maxroll.gg/d2/tierlists/runeword-tier-list (Feb 18, 2026): 97 runeword tiers stored in wp-a-runewords.json.
* maxroll Base Items — https://maxroll.gg/d2/items/base-items (May 12, 2024, pre-RotW; base-name list only). maxroll Unique Items / Sets pages (March 3, 2026) contributed nothing (item lists are JS-rendered); unique/set names were resolved from d2planner ids across 91 cached maxroll pages (373 uniques, 127 sets).
* diablo2.io — /runewords/ index, /runewords/hustle-t1282118.html, /runewords/mania-t1674022.html, /runewords/hysteria-t1674021.html (Mania/Hysteria = Hustle; "Patch 3.0" tags: Authority, Coven, Void, Vigilance, Ritual, Mania, Hysteria); /uniques/ index (Atma's Scarab, The Cat's Eye, Heaven's Light, Gull confirmed as uniques). Fetched 2026-09-18.
* d2runes.io /runewords/ (fetched 2026-09-18) — second opinion only: Authority Body Armor lvl 29, Coven Helms 51, Vigilance Shields 53.
