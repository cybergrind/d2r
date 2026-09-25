# Build-to-branch crosswalk

2026-09-24. Proposed role branches for [DECISION_TREE.md](DECISION_TREE.md). All 33 cached builds are assigned a review owner in the tree. Branch names here are design identifiers, not claims of implemented rules or approved numeric thresholds.

## All-build branch assignment

| Build | Proposed branches | Required distinction |
|---|---|---|
| abyss-warlock-build-guide | P1.magic.abyss; W.charges; M2.insight | Void staffmod dagger caster, starter progression and MF |
| berserk-barbarian | P2.berserk; F.magic_find; W.warcries; M2.insight; M4.lawbringer | Standard Grief vs Budget Oath; Chaos Prep changes mercenary subtype |
| blessed-hammer-paladin | P1.magic.hammer; P3.smite; F.magic_find; M2.insight | Caster variants and Grief Ubers must not share weapon priorities |
| blizzard-sorceress | P1.cold.blizzard; S.tal_rasha; F.magic_find; M2.infinity; M2.insight | Fathom vs Oculus vs set setup; planner/prose merc weapon conflict |
| blood-boil-warlock-guide | P1.warlock.blood_boil; M2.discovery | Guide-only; extract variant, skill-scaling and mercenary role evidence |
| double-throw-barbarian-guide | P2.throwing; F.magic_find; M1.faith | Lacerator/throwing sustain, ethereal and aura bow support |
| dragon-talon-assassin | P3.kick_martial; M3.fire.spell_support | Black Budget vs Mosaic Standard; Act 3 fire mercenary |
| dream-paladin | P4.dream; P2.melee; P3.smite; W.fade; M1.faith; M2.reaper | Dual Dream; Hybrid HoJ+Dragon; Ubers Last Wish; merc role changes |
| echoing-strike-warlock-guide | P3.echoing; F.magic_find; W.enchant; W.fade; M2.insight; M5.sazabi | Starter book/sword vs Void; Prayer/Cure; Ubers Sazabi+Malice |
| enchant-sorceress | P3.enchant.projectile; W.enchant.prebuff_orb; M1.insight; M2.infinity | Kuko Budget, Demon Machine Standard, distinct Max Enchant buff equipment |
| fire-blast-assassin | P3.trap.fire_blast; P1.caster_support; M2.infinity | Standard caster weapon; Damage claws are planner-only evidence |
| fire-wall-sorceress-guide | P1.fire.fire_wall; M2.discovery | Guide-only; exact variants and mercenary destinations pending extraction |
| fire-warlock-guide | P1.fire.warlock; F.magic_find; M2.infinity | Mang Song vs Obsession alternative and two-handed tradeoff |
| fissure-druid | P1.fire.fissure; A.pelt; F.magic_find; W.facets; W.charges; M2.infinity | Skill pelt, Phoenix and MF shield; Ubers facet sword; source merc conflicts |
| fist-of-the-heavens-paladin | P1.foh; P1.holy_bolt; P3.smite; M2.insight; M5.lawbringer_death | FoH/Holy Bolt starters, Tri-Brid and support are separate roles |
| frozen-orb-meteor-sorceress | P1.hybrid.cold_fire; M2.discovery | Guide-only; separate element benefits and variant evidence |
| frozen-orb-sorceress | P1.cold.frozen_orb; M2.discovery | Guide-only; Fathom/Doom/other alternatives require source-specific roles |
| gold-find-barbarian | P2.melee; P2.whirlwind; P1.war_cry; F.gold_find; M2.kill_engine | Budget/Standard/War Cry/Whirlwind/Leap Only alter who deals damage |
| hydra-sorceress | P1.fire.hydra; M2.discovery | Guide-only; distinguish from Nova Hydra Hybrid |
| lightning-fury-amazon-guide | P3.lightning_javelin; A.shield_platform; M2.infinity; M5.plague | Titan sustain vs Thunderstroke Ubers; facet shield and paired Plague |
| lightning-sentry-assassin | P3.trap.lightning_claw; P1.caster_support; F.magic_find; M2.infinity | Standard claw skills/IAS vs MF HotO; exact trap skill identities |
| lightning-sorceress | P1.lightning.spell; F.magic_find; M2.infinity | Lightning-specific damage and caster setup; inspect Ubers changes independently |
| lightning-strike-amazon | P3.lightning_spear; P3.lightning_javelin; M1.faith; M5.plague | Starter javelin vs player Infinity spear; Faith Standard vs Plague Ubers |
| meteor-sorceress | P1.fire.meteor; S.tal_rasha; F.magic_find; M2.infinity | Standard, MF, set and Ubers must preserve equipment alternatives |
| mirrored-blades-warlock-guide | P2.mirrored; A.grimoire; M2.pride | Starter Obedience; eth three-socket Tomb Reaver; Ubers BotD Thunder Maul |
| nova-sorceress-guide | P1.nova.infinity_self; P1.hybrid.nova_hydra; W.memory; M2.insight; M2.infinity | Infinity holder switches between Standard and Hydra Hybrid |
| poison-nova-necromancer | P1.poison; P4.corpse_support; F.magic_find; M2.infinity | Death's Web; merc first-corpse/CE job; planner-only Budget/Max Damage |
| smite-paladin | P3.smite; W.life_tap; W.fade; M2.reaper; M2.armor.shared_treachery | Grief vs Last Wish, non-ethereal shared mercenary Treachery |
| strafe-amazon | P2.physical_bow; F.magic_find; M2.pride | Windforce vs upgraded Witchwild String; aura vs merc survivability |
| summoner-necromancer-guide | P4.summon; P4.corpse_support; W.teleport; M2.infinity; M2.bramble | HotO vs Beast Damage/Ubers; Bramble supports minions |
| summoner-warlock-guide | P4.warlock_summon; M2.discovery | Guide-only; no copied Necromancer summon predicates |
| wake-of-fire-assassin | P3.trap.fire_claw; M2.infinity | Wake of Fire staffmods; Plague alternative; planner-only Sunder profile |
| zeal-paladin | P2.zeal; M2.discovery; M5.discovery | Guide-only; ethereal repair/indestructible physical weapon alternatives |

## Variant source ledger

Each entry below includes every structured variant from the dedicated JSON, plus any additional main WP-A variant name. Weapon alternatives are preserved verbatim as source evidence; they need legality, endorsement and conflict review. Full player/merc arrays at the cited pointer include **all armor/accessory, charm, filler, swap and prebuff slots**, which must also be expanded into role leaves. Do not restrict implementation to the weapon excerpts.

Source path + JSON pointer is the stable review locator. A missing array in a delta is not an empty equipped slot. Stage labels such as Starter are build progression, not automatically low-character-level advice.

### abyss-warlock-build-guide

#### Starter

Source: `pricing/data/wp-a-variants/abyss-warlock-build-guide.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Ancients' Pledge Kite Shield
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Partizan (ethereal)
- **Source context:** Build Variants tab (prose) + planner profile

#### Standard

Source: `pricing/data/wp-a-variants/abyss-warlock-build-guide.json` → `/variants/1`.

- **Player weapon:** Void Kris (Thul Zod Ist; +3 Abyss / +3 Miasma Chain / +3 Bind Demon staffmods)
- **Player offhand:** Ars Dul'Mephistos Occult Tome (Um Rune)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Call to Arms Crystal Sword + Spirit Monarch on swap: Battle Command x2, then Battle Orders
- **Source context:** Build Variants tab (prose) + planner profile

#### Magic Find

Source: `pricing/data/wp-a-variants/abyss-warlock-build-guide.json` → `/variants/2`.

- **Player weapon:** Void Kris (Thul Zod Ist)
- **Player offhand:** Ars Dul'Mephistos Occult Tome (Um Rune)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Call to Arms Crystal Sword + Spirit Monarch on swap
- **Source context:** Build Variants tab (prose) + planner profile

#### Hardcore

Source: `pricing/data/wp-a-variants/abyss-warlock-build-guide.json` → `/variants/3`.

- **Player offhand:** Ars Dul'Mephistos Occult Tome (Eld Rune) — allocate Dexterity for 75% Chance to Block
- **Mercenary:** Act 2 Might (unchanged)
- **Source context:** prose section only (no tab, no planner profile)

### berserk-barbarian

#### Starter

Source: `pricing/data/wp-a-variants/berserk-barbarian.json` → `/variants/0`.

- **Player weapon:** Unbending Will Phase Blade
- **Player offhand:** Rhyme Bone Shield
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Poleaxe
- **Source context:** Build Variants tab (prose) + planner profile

#### Standard

Source: `pricing/data/wp-a-variants/berserk-barbarian.json` → `/variants/1`.

- **Player weapon:** Grief Phase Blade
- **Player offhand:** Gemmed Phase Blade (6x Ist Runes)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Thresher (ethereal)
- **Prebuff:** Swap to + to Skills equipment (2x Suicide Branch): Battle Command x2, Battle Orders, Shout
- **Source context:** Build Variants tab (prose) + planner profile

#### Budget

Source: `pricing/data/wp-a-variants/berserk-barbarian.json` → `/variants/2`.

- **Player weapon:** Oath Highland Blade (ethereal)
- **Player offhand:** Gull Dagger (Ist Rune)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Colossus Voulge (ethereal)
- **Source context:** planner profile only (no tab; guide prose names no items for it)

#### Hardcore

Source: `pricing/data/wp-a-variants/berserk-barbarian.json` → `/variants/3`.

- **Player weapon:** Grief Phase Blade
- **Player offhand:** Stormshield (Ist Rune)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Thresher (ethereal)
- **Prebuff:** Wizardspike + Spirit Monarch swap for BC/BO/Shout and Resistances
- **Source context:** planner profile + prose section (no tab)

#### Chaos Prep

Source: `pricing/data/wp-a-variants/berserk-barbarian.json` → `/variants/4`.

- **Player weapon:** Grief Phase Blade
- **Player offhand:** Stormshield (Shael Rune)
- **Mercenary:** Act 5 Barbarian (planner merc id 28: Bash/Stun)
- **Mercenary weapon:** Lawbringer Legend Sword (ethereal)
- **Prebuff:** 2x Wizardspike swap for BC/BO/Shout
- **Source context:** planner profile only (no tab; guide prose names no items for it)

#### Max Mobility

Source: `pricing/data/wp-a-variants/berserk-barbarian.json` → `/variants/5`.

- **Player weapon:** Grief Phase Blade
- **Player offhand:** Gemmed Phase Blade (6x Ist Runes)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Thresher (ethereal)
- **Source context:** planner profile only (no tab; guide prose names no items for it)

### blessed-hammer-paladin

#### Starter

Source: `pricing/data/wp-a-variants/blessed-hammer-paladin.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Spirit Targe
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Insight Scythe (ethereal)
- **Source context:** Build Variants tab (prose) + planner profile

#### Standard

Source: `pricing/data/wp-a-variants/blessed-hammer-paladin.json` → `/variants/1`.

- **Player weapon:** Void Kris (Thul Zod Ist; +3 Abyss staffmod)
- **Player offhand:** Spirit Sacred Targe
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Call to Arms Double Axe + Spirit Sacred Targe on swap: Battle Command x2, Battle Orders; cast Holy Shield on the swap with higher Skill Level
- **Source context:** Build Variants tab (prose) + planner profile

#### Magic Find

Source: `pricing/data/wp-a-variants/blessed-hammer-paladin.json` → `/variants/2`.

- **Player weapon:** Void Kris (Thul Zod Ist)
- **Player offhand:** Spirit Sacred Targe
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Call to Arms Double Axe + Spirit Sacred Targe on swap
- **Source context:** Build Variants tab (prose) + planner profile

#### Ubers

Source: `pricing/data/wp-a-variants/blessed-hammer-paladin.json` → `/variants/3`.

- **Player weapon:** Grief Phase Blade
- **Player offhand:** Herald of Zakarum (Um Rune)
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Treachery: swap in and proc Fade (15% DR, +60 All Resist for 288 s) on the fire next to the River of Flame Waypoint; Call to Arms Double Axe + Spirit Sacred Targe swap: Battle Command x2, Battle Orders
- **Source context:** Build Variants tab (prose) + planner profile

#### Hardcore

Source: `pricing/data/wp-a-variants/blessed-hammer-paladin.json` → `/variants/4`.

- **Player weapon:** Heart of the Oak
- **Mercenary:** Act 2 Holy Freeze (unchanged)
- **Source context:** prose section only (no tab, no planner profile)

### blizzard-sorceress

#### Starter

Source: `pricing/data/wp-a-variants/blizzard-sorceress.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Ancients' Pledge Kite Shield
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Scythe
- **Source context:** Build Variants tab (prose) + planner profile

#### Standard

Source: `pricing/data/wp-a-variants/blizzard-sorceress.json` → `/variants/1`.

- **Player weapon:** Death's Fathom (ethereal; Rainbow Facet cold)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Giant Thresher (ethereal) [planner]; prose says Insight Giant Thresher
- **Source context:** Build Variants tab (prose) + planner profile

#### Magic Find

Source: `pricing/data/wp-a-variants/blizzard-sorceress.json` → `/variants/2`.

- **Player weapon:** The Oculus (ethereal, Ist Rune)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Call to Arms Crystal Sword on swap: Battle Command x2, Battle Orders
- **Source context:** Build Variants tab (prose) + planner profile

#### Set Build

Source: `pricing/data/wp-a-variants/blizzard-sorceress.json` → `/variants/3`.

- **Player weapon:** Tal Rasha's Lidless Eye (Ist Rune)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Giant Thresher (ethereal); Insight Giant Thresher instead if Cold Rupture is equipped (prose)
- **Prebuff:** Call to Arms Crystal Sword + Spirit Monarch on swap
- **Source context:** Build Variants tab (prose) + planner profile

#### Hardcore

Source: `pricing/data/wp-a-variants/blizzard-sorceress.json` → `/variants/4`.

- **Player weapon:** Death's Fathom (ethereal; Rainbow Facet cold)
- **Player offhand:** Stormshield (Eld Rune)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Call to Arms Crystal Sword + Spirit Monarch on swap
- **Source context:** planner profile + prose section (no tab)

### blood-boil-warlock-guide

Only guide-mention contexts currently imported. Extract variant prose and referenced planner associations before approving build-specific leaves. Existing source anchors:

- `pricing/raw/mr/guides__blood-boil-warlock-guide.html` → `/item-spans/7`
- `pricing/raw/mr/guides__blood-boil-warlock-guide.html` → `/item-spans/11`
- `pricing/raw/mr/guides__blood-boil-warlock-guide.html` → `/item-spans/15`

### double-throw-barbarian-guide

#### Starter

Source: `pricing/data/wp-a-variants/double-throw-barbarian-guide.json` → `/variants/0`.

- **Player weapon:** Blood Crafted Balanced Axe (+1 Barbarian Skills / 10% IAS / 80% ED / 4% Life Leech / +20 Life)
- **Player offhand:** Blood Crafted Balanced Axe (+1 Barbarian Skills / 10% IAS / 80% ED / 4% Life Leech / +20 Life)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Partizan (ethereal) [planner]; prose says Hustle
- **Prebuff:** 2x Hustle (Phase Blade) on Weapon-Swap to pre-buff Burst of Speed with Double Swing (prose; planner swap is 2x Spirit)
- **Source context:** Build Variants tab (prose) + planner profile

#### Standard

Source: `pricing/data/wp-a-variants/double-throw-barbarian-guide.json` → `/variants/1`.

- **Player weapon:** Lacerator (ethereal)
- **Player offhand:** Warshrike (ethereal)
- **Mercenary:** Act 1 Rogue (Fire Arrow / Exploding Arrow)
- **Mercenary weapon:** Faith Crusader Bow
- **Prebuff:** Demon Limb (Tyrant Club) (Hel Rune) in the cube — Enchant charges (planner cube only); Swap to + to Skills equipment (2x Heart of the Oak): Battle Command x2, Battle Orders, Shout
- **Source context:** Build Variants tab (prose) + planner profile

#### Magic Find

Source: `pricing/data/wp-a-variants/double-throw-barbarian-guide.json` → `/variants/2`.

- **Player weapon:** Lacerator (ethereal)
- **Player offhand:** Warshrike (ethereal)
- **Mercenary:** Act 1 Rogue (Fire Arrow / Exploding Arrow)
- **Mercenary weapon:** Faith Crusader Bow
- **Prebuff:** Demon Limb (Tyrant Club) (Hel Rune) in the cube — Enchant charges (planner cube only); 2x Suicide Branch swap: Battle Command x2, Battle Orders, Shout
- **Source context:** Build Variants tab (prose) + planner profile

#### Hardcore

Source: `pricing/data/wp-a-variants/double-throw-barbarian-guide.json` → `/variants/3`.

- **Mercenary:** Act 1 Rogue / Act 2 Might (unchanged)
- **Source context:** prose section only (no tab, no planner profile)

### dragon-talon-assassin

#### Budget

Source: `pricing/data/wp-a-variants/dragon-talon-assassin.json` → `/variants/0`.

- **Player weapon:** Black Flail (Thul-Io-Nef)
- **Player offhand:** Sanctuary Troll Nest (Ko-Ko-Mal)
- **Mercenary:** Act 3 Iron Wolf (Fire)
- **Mercenary weapon:** Hexfire Shamshir (ethereal; Fire Rainbow Facet)
- **Mercenary offhand:** Lidless Wall (Grim Shield; Fire Rainbow Facet) until enough Strength for an Ethereal Spirit Monarch
- **Source context:** prose + planner profile 'Budget' (xDo6ID0l); Black/Sanctuary/Duress/Goblin Toe/Guillaume's/Thundergod's/Blood gloves are planner-only

#### Standard

Source: `pricing/data/wp-a-variants/dragon-talon-assassin.json` → `/variants/1`.

- **Player weapon:** Mosaic Greater Talons (Mal-Gul-Amn)
- **Player offhand:** Mosaic Greater Talons
- **Mercenary:** Act 3 Iron Wolf (Fire)
- **Mercenary weapon:** Hexfire (Shamshir, ethereal; Fire Rainbow Facet)
- **Mercenary offhand:** Ethereal Spirit Monarch
- **Prebuff:** Optional: Arachnid Mesh, Magefist and a Faster Cast Rate Ring kept in the Horadric Cube for Teleporting
- **Source context:** prose + planner profile 'Standard' (dQu1lpcK)

#### Hardcore (Essentials > Hardcore tab)

Source: `pricing/data/wp-a-variants/dragon-talon-assassin.json` → `/variants/2`.

- **Mercenary:** Act 3 Iron Wolf (Fire) (unchanged)
- **Source context:** prose only; no item changes listed, no planner profile

### dream-paladin

#### Standard

Source: `pricing/data/wp-a-variants/dream-paladin.json` → `/variants/0`.

- **Player weapon:** Grief Phase Blade
- **Player offhand:** Dream Sacred Targe
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** The Reaper's Toll (Thresher, ethereal; 15 IAS / 15 All Res jewel)
- **Source context:** prose + planner profile 'Standard' (iW6ooOCM)

#### Hybrid

Source: `pricing/data/wp-a-variants/dream-paladin.json` → `/variants/1`.

- **Player weapon:** Hand of Justice Phase Blade
- **Player offhand:** Dream Sacred Targe
- **Mercenary:** Act 1 Cold (Rogue)
- **Mercenary weapon:** Faith Matriarchal Bow
- **Source context:** prose + planner profile 'Hybrid' (DFT6FkWt)

#### Ubers

Source: `pricing/data/wp-a-variants/dream-paladin.json` → `/variants/2`.

- **Player weapon:** Last Wish Phase Blade
- **Player offhand:** Dream Sacred Targe
- **Mercenary:** Act 1 Cold (Rogue)
- **Mercenary weapon:** Faith Matriarchal Bow
- **Prebuff:** Demon Limb (Enchant); Treachery (Fade) — per Gear Notes 3
- **Source context:** prose + planner profile 'Ubers' (R1nfYAMg); prose names Chains of Honor + Thundergod's Vigor while planner shows Duress Archon Plate + Verdungo's Hearty Cord

#### Hardcore (Essentials > Hardcore tab; delta)

Source: `pricing/data/wp-a-variants/dream-paladin.json` → `/variants/3`.

- **Mercenary:** Act 2 Might (unchanged)
- **Source context:** prose only

### echoing-strike-warlock-guide

#### Starter

Source: `pricing/data/wp-a-variants/echoing-strike-warlock-guide.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword; Bastard Sword (any 2-Handed Weapon wielded one-handed with a Book equipped, Item Level 26+)
- **Player offhand:** Rhyme Codex (Book: +1 Hex: Purge / +1 Consume / +1 Summon Defiler staffmods)
- **Mercenary:** Act 2 Blessed Aim
- **Mercenary weapon:** Insight Partizan (ethereal)
- **Source context:** prose + planner profile 'Starter' (ZWcxvtFt); Angelic set pieces are planner-only

#### Standard

Source: `pricing/data/wp-a-variants/echoing-strike-warlock-guide.json` → `/variants/1`.

- **Player weapon:** Void Legend Spike (ethereal; Thul-Zod-Ist)
- **Player offhand:** Ars Dul'Mephistos Occult Tome (Um Rune socketed)
- **Mercenary:** Act 2 Prayer
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Demon Limb (in Horadric Cube)
- **Source context:** prose + planner profile 'Standard' (LmIammQ8)

#### Magic Find

Source: `pricing/data/wp-a-variants/echoing-strike-warlock-guide.json` → `/variants/2`.

- **Player weapon:** Void Legend Spike (ethereal)
- **Player offhand:** Ars Dul'Mephistos Occult Tome (Um Rune socketed)
- **Mercenary:** Act 2 Prayer
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Source context:** prose + planner profile 'Magic Find' (1ikVhvXU); player items are planner-only (prose names none)

#### Ubers

Source: `pricing/data/wp-a-variants/echoing-strike-warlock-guide.json` → `/variants/3`.

- **Player weapon:** Void Legend Spike (ethereal)
- **Player offhand:** Ars Dul'Mephistos Occult Tome (Um Rune socketed)
- **Mercenary:** Act 5 Frenzy
- **Mercenary weapon:** Sazabi's Cobalt Redeemer [Sazabi's Grand Tribute set] (Cryptic Sword; Ber Rune socketed)
- **Mercenary offhand:** Malice Mythical Sword (ethereal; second weapon for Open Wounds) — 'or Crushing Blow with more expensive runeword options'
- **Prebuff:** Demon Limb (Enchant); Treachery Breast Plate (Fade)
- **Source context:** prose + planner profile 'Ubers' (Khw26jKQ; merc id 36 = Act 5 Frenzy/Iron Skin/Taunt, mercLevel 95)

#### Hardcore (Essentials > Hardcore tab; delta)

Source: `pricing/data/wp-a-variants/echoing-strike-warlock-guide.json` → `/variants/4`.

- **Player weapon:** Obsession Archon Staff (replaces Void Legend Spike to cap Resistances)
- **Player offhand:** Shield with Eld Rune for 75% Chance to Block
- **Mercenary:** Act 2 Prayer (unchanged)
- **Source context:** prose only; no planner profile

### enchant-sorceress

#### Budget

Source: `pricing/data/wp-a-variants/enchant-sorceress.json` → `/variants/0`.

- **Player weapon:** Kuko Shakaku (Cedar Bow; Shael Rune)
- **Player offhand:** Arrows
- **Mercenary:** Act 1 Fire Arrow (Rogue)
- **Mercenary weapon:** Insight Rune Bow
- **Source context:** planner profile 'Budget' (u2hhT7aS); prose names no items

#### Standard

Source: `pricing/data/wp-a-variants/enchant-sorceress.json` → `/variants/1`.

- **Player weapon:** Demon Machine Demon Crossbow (Upgraded; 15 IAS / 15 All Res jewel)
- **Player offhand:** Bolts
- **Mercenary:** Act 2 Prayer
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Eschuta's Temper (Fire Rainbow Facet) in Cube; Spirit Monarch in Cube; see Max Enchant variant
- **Source context:** prose + planner profile 'Standard' (hXwKDohh)

#### Magic Find

Source: `pricing/data/wp-a-variants/enchant-sorceress.json` → `/variants/2`.

- **Player weapon:** Demon Machine Demon Crossbow (15 IAS / 15 All Res jewel)
- **Player offhand:** Bolts
- **Mercenary:** Act 2 Prayer
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Eschuta's Temper in Cube; Spirit Monarch in Cube
- **Source context:** prose + planner profile 'Magic Find' (4OhRhfA6); no Ist Runes actually socketed in the planner profile

#### Max Enchant

Source: `pricing/data/wp-a-variants/enchant-sorceress.json` → `/variants/3`.

- **Player weapon:** Volcanic Eldritch Orb of the Magus (+3 Fire Skills / 20 FCR; +3 Fire Mastery / +3 Enchant staffmods; 2x Fire Rainbow Facet)
- **Player offhand:** Spirit Monarch
- **Mercenary:** none (planner profile has no mercenary); buff the Standard merc
- **Prebuff:** entire loadout is the prebuff set; swap back to Standard or Magic Find to farm
- **Source context:** planner profile 'Maximum Prebuff' (0V6UlvGv); prose names no items

#### Hardcore (Essentials > Hardcore tab; delta)

Source: `pricing/data/wp-a-variants/enchant-sorceress.json` → `/variants/4`.

- **Mercenary:** Act 2 Prayer
- **Source context:** prose only

### fire-blast-assassin

#### Starter

Source: `pricing/data/wp-a-variants/fire-blast-assassin.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword; Cunning Greater Claws (+3 Traps / +3 Fire Blast, shopped at Anya) x2 in inventory
- **Player offhand:** Rhyme Bone Shield
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Insight Partizan
- **Source context:** prose + planner profile 'Starter' (kNG46Gvn; merc id 10 = Act 2 Holy Freeze); planner merc helm is Undead Crown while prose names Bulwark

#### Standard

Source: `pricing/data/wp-a-variants/fire-blast-assassin.json` → `/variants/1`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Phoenix Monarch (or Spirit Monarch, freeing a ring slot for Nagelring)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Thresher (planner: Infinity Giant Thresher, ethereal)
- **Source context:** prose + planner profile 'Standard' (i9dgnI9K; merc id 11 = Act 2 Might)

#### Damage (planner profile only)

Source: `pricing/data/wp-a-variants/fire-blast-assassin.json` → `/variants/2`.

- **Player weapon:** Cunning Greater Claws of Quickness (2x Shael Rune)
- **Player offhand:** Cunning Greater Claws of Quickness (2x Fire Rainbow Facet)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Source context:** planner profile 'Damage' (xnSGzkV2); no prose tab

#### Hardcore

Source: `pricing/data/wp-a-variants/fire-blast-assassin.json` → `/variants/3`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Stormshield (Monarch; Eld Rune)
- **Mercenary:** Act 2 Holy Freeze (planner) / prose unchanged
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Source context:** Essentials > Hardcore prose + planner profile 'Hardcore' (RLMsdqrc; merc id 10 = Act 2 Holy Freeze)

### fire-wall-sorceress-guide

Only guide-mention contexts currently imported. Extract variant prose and referenced planner associations before approving build-specific leaves. Existing source anchors:

- `pricing/raw/mr/guides__fire-wall-sorceress-guide.html` → `/item-spans/0`
- `pricing/raw/mr/guides__fire-wall-sorceress-guide.html` → `/item-spans/1`
- `pricing/raw/mr/guides__fire-wall-sorceress-guide.html` → `/item-spans/2`

### fire-warlock-guide

#### Starter

Source: `pricing/data/wp-a-variants/fire-warlock-guide.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Rhyme Codex (planner set I4lKot5q; the older EMBEDS planner shows Ancients' Pledge Kite Shield here instead)
- **Mercenary:** Act 2 (planner mercType 11 = Might; prose only says 'Mercenary'). Prose: Insight in any Base, Treachery, Bulwark
- **Mercenary weapon:** Insight Partizan (ethereal); Insight in any Base (prose)

#### Standard

Source: `pricing/data/wp-a-variants/fire-warlock-guide.json` → `/variants/1`.

- **Player weapon:** Mang Song's Lesson Archon Staff (socketed Fire Rainbow Facet); Obsession (prose: 'much easier to gear with and to max Resistances'; Mang Song's Lesson 'is the strongest option but comes with higher gear requirements')
- **Player offhand:** Ars Al'Diabolos Blasphemous Grimoire (socketed Um Rune)
- **Mercenary:** Act 2 Might (planner mercType 11 = Desert Mercenary, Might)
- **Mercenary weapon:** Infinity Giant Thresher (ethereal; Ber Mal Ber Ist)
- **Prebuff:** Call to Arms (Battle Command x2, then Battle Orders; refresh every 2-3 minutes)

#### Magic Find

Source: `pricing/data/wp-a-variants/fire-warlock-guide.json` → `/variants/2`.

- **Player weapon:** Obsession Archon Staff
- **Player offhand:** Ars Al'Diabolos Blasphemous Grimoire (socketed Ist Rune)
- **Mercenary:** Act 2 Might (planner mercType 11 = Desert Mercenary, Might)
- **Mercenary weapon:** Infinity Giant Thresher (ethereal; Ber Mal Ber Ist)
- **Prebuff:** Call to Arms (Battle Command x2, then Battle Orders; refresh every 2-3 minutes)

#### Hardcore

Source: `pricing/data/wp-a-variants/fire-warlock-guide.json` → `/variants/3`.

- **Player offhand:** Gerke's Sanctuary Pavise (Eld Rune) or Stormshield (Eld Rune) instead of Ars Al'Diabolos; Ars Al'Diabolos (socketed with Eld Rune) if kept - allocate Dexterity for 75% Chance to Block
- **Mercenary:** unchanged (Act 2 Might)

### fissure-druid

#### Starter

Source: `pricing/data/wp-a-variants/fissure-druid.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Ancients' Pledge Kite Shield
- **Mercenary:** Act 2 (planner mercType 6 = Prayer; prose only says 'Insight in any Base'); merc table offers Act 2 Might or Act 5 Bash/Frenzy early
- **Mercenary weapon:** Insight Partizan (ethereal); Insight in any Base (prose)

#### Standard

Source: `pricing/data/wp-a-variants/fissure-druid.json` → `/variants/1`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Phoenix Monarch
- **Mercenary:** Act 2 Might per variant prose ('Act 2 Might Mercenary with Infinity'); planner set uses mercType 10 = Holy Freeze, and the guide's Mercenary section is headed 'Infinity, Holy Freeze'
- **Mercenary weapon:** Infinity Giant Thresher (ethereal; Ber Mal Ber Ist)
- **Prebuff:** Call to Arms (Battle Command, summons on the +skills loadout, then Battle Command again and Battle Orders; refresh every 2-3 minutes)

#### Magic Find

Source: `pricing/data/wp-a-variants/fissure-druid.json` → `/variants/2`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Gemmed Monarch (4x Ist Rune; planner: magic Monarch 30% FBR / 20% block = Jeweler's Monarch of Deflecting base)
- **Mercenary:** Act 2 Might per prose; planner mercType 10 = Holy Freeze
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Call to Arms (Battle Command, summons on the +skills loadout, then Battle Command again and Battle Orders; refresh every 2-3 minutes)

#### Ubers

Source: `pricing/data/wp-a-variants/fissure-druid.json` → `/variants/3`.

- **Player weapon:** Gemmed Crystal Sword (6x Fire Rainbow Facets; planner: 5x -5/+5 'die' + 1x 'up' facets)
- **Player offhand:** Phoenix Monarch
- **Mercenary:** Act 2 Might (prose and planner agree: mercType 11)
- **Mercenary weapon:** Infinity Thresher (ethereal)
- **Prebuff:** Treachery (Fade pre-buff for Resistances, Curse Length Reduction and Damage Reduction); Call to Arms (Battle Command / Battle Orders)

#### Hardcore

Source: `pricing/data/wp-a-variants/fissure-druid.json` → `/variants/4`.

- **Player weapon:** Phoenix Phase Blade instead of Phoenix Monarch (keeps Redemption and -28% Enemy Fire Res while using Stormshield)
- **Player offhand:** Stormshield (planner: Monarch, Shael Rune) - 'the surest way to keep a Hardcore Fissure Druid alive'; Phoenix Monarch over Stormshield 'is not recommended (dangerous)'
- **Mercenary:** Act 2 Might (2023 planner Hardcore set)
- **Mercenary weapon:** Infinity Thresher (ethereal)

### fist-of-the-heavens-paladin

#### FoH Starter

Source: `pricing/data/wp-a-variants/fist-of-the-heavens-paladin.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword (ethereal in planner)
- **Player offhand:** Spirit Targe
- **Mercenary:** Act 2 Holy Freeze per prose ('Hire the Holy Freeze Aura Mercenary'); planner sets 1-2 use mercType 11 = Might
- **Mercenary weapon:** Insight Poleaxe (ethereal)

#### Holy Bolt Starter

Source: `pricing/data/wp-a-variants/fist-of-the-heavens-paladin.json` → `/variants/1`.

- **Player weapon:** Spirit Crystal Sword (ethereal in planner)
- **Player offhand:** Spirit Targe
- **Mercenary:** Act 2 Holy Freeze per prose ('Hire the Holy Freeze Aura Mercenary'); planner sets 1-2 use mercType 11 = Might
- **Mercenary weapon:** Insight Poleaxe (ethereal)

#### Standard

Source: `pricing/data/wp-a-variants/fist-of-the-heavens-paladin.json` → `/variants/2`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Herald of Zakarum (Um Rune)
- **Mercenary:** Act 2 Might (Mercenary section 'Insight, Might'; planner mercType 11)
- **Mercenary weapon:** Insight Giant Thresher (prose; planner: Insight Thresher, ethereal)
- **Prebuff:** Call to Arms (battlecommand and battleorders before holyshield at the start of a session)

#### Tri-Brid

Source: `pricing/data/wp-a-variants/fist-of-the-heavens-paladin.json` → `/variants/3`.

- **Player weapon:** Heaven's Light Mighty Scepter (2x Shael Rune; table footnote 2 'Used exclusively on the Tri-Brid Variant'); Astreon's Iron Ward (Shael Rune) - table alternative, footnote 2
- **Player offhand:** Herald of Zakarum (Um Rune)
- **Mercenary:** Act 5 Barbarian, Frenzy (planner mercType 36 = Barbarian Frenzy hireling); prose does not state the Act - 'hand-tailored to apply decrepify ... and sanctuary' (both come from Lawbringer)
- **Mercenary weapon:** Lawbringer Phase Blade (Amn Lem Ko; Sanctuary aura + Decrepify on striking); Death Phase Blade (Hel El Vex Ort Gul) in the other hand
- **Mercenary offhand:** (second weapon: Death Phase Blade - Act 5 mercs dual-wield, no shield)
- **Prebuff:** Call to Arms (Battle Command / Battle Orders before Holy Shield)

#### Holy Bolt Support

Source: `pricing/data/wp-a-variants/fist-of-the-heavens-paladin.json` → `/variants/4`.

- **Player weapon:** Hand of Blessed Light Divine Scepter (ethereal; socketed rare Jewel 7% FHR / 40 Fire Res / 10 other res / 12% damage to mana)
- **Player offhand:** Spirit Sacred Targe
- **Mercenary:** Act 2 Holy Freeze (planner mercType 10)
- **Mercenary weapon:** Insight Thresher (ethereal)
- **Prebuff:** Call to Arms

### frozen-orb-meteor-sorceress

Only guide-mention contexts currently imported. Extract variant prose and referenced planner associations before approving build-specific leaves. Existing source anchors:

- `pricing/raw/mr/guides__frozen-orb-meteor-sorceress.html` → `/item-spans/0`
- `pricing/raw/mr/guides__frozen-orb-meteor-sorceress.html` → `/item-spans/1`
- `pricing/raw/mr/guides__frozen-orb-meteor-sorceress.html` → `/item-spans/2`

### frozen-orb-sorceress

Only guide-mention contexts currently imported. Extract variant prose and referenced planner associations before approving build-specific leaves. Existing source anchors:

- `pricing/raw/mr/guides__frozen-orb-sorceress.html` → `/item-spans/0`
- `pricing/raw/mr/guides__frozen-orb-sorceress.html` → `/item-spans/1`
- `pricing/raw/mr/guides__frozen-orb-sorceress.html` → `/item-spans/2`

### gold-find-barbarian

#### Budget

Source: `pricing/data/wp-a-variants/gold-find-barbarian.json` → `/variants/0`.

- **Player weapon:** Blade of Ali Baba Tulwar (2x magic Jewel 30% Extra Gold)
- **Player offhand:** Blade of Ali Baba Tulwar (2x magic Jewel 30% Extra Gold)
- **Mercenary:** Act 2 Might (prose: 'Hire the Might Aura Mercenary')
- **Mercenary weapon:** Insight Battle Scythe
- **Prebuff:** Battle Command x2, Battle Orders, Shout on the swap with more +Warcries

#### Standard

Source: `pricing/data/wp-a-variants/gold-find-barbarian.json` → `/variants/1`.

- **Player weapon:** Grief Phase Blade; Oath (prose alternative; table: Oath Balrog Blade)
- **Player offhand:** Gemmed Phase Blade (6x Lem Rune) - table lists 'Gemmed Crystal Sword'
- **Mercenary:** Act 2 Might (prose: 'Might Aura works great for the Mercenary'; planner mercType 11)
- **Mercenary weapon:** Breath of the Dying War Pike (ethereal)
- **Prebuff:** Battle Command x2, Battle Orders, Shout (swap to whichever weapon set gives more +Warcries)

#### War Cry

Source: `pricing/data/wp-a-variants/gold-find-barbarian.json` → `/variants/2`.

- **Player weapon:** Heart of the Oak Flail (ethereal)
- **Player offhand:** Suicide Branch Burnt Wand (ethereal; socketed Lem Rune) - not in the gear table
- **Mercenary:** Act 2 Might (prose: 'Might Aura works great for the Mercenary'; planner mercType 11)
- **Mercenary weapon:** Breath of the Dying War Pike (ethereal)
- **Prebuff:** Battle Command x2, Battle Orders, Shout

#### Whirlwind

Source: `pricing/data/wp-a-variants/gold-find-barbarian.json` → `/variants/3`.

- **Player weapon:** Grief Phase Blade; Oath (prose alternative)
- **Player offhand:** Grief Phase Blade (second one, for damage); Gemmed Crystal Sword (prose alternative for more Gold Find)
- **Mercenary:** Act 2 Might (prose: 'Might Aura works great for the Mercenary'; planner mercType 11)
- **Mercenary weapon:** Breath of the Dying War Pike (ethereal)
- **Prebuff:** Battle Command x2, Battle Orders, Shout

#### Leap Only

Source: `pricing/data/wp-a-variants/gold-find-barbarian.json` → `/variants/4`.

- **Player weapon:** Gemmed Crystal Sword (6x Lem Rune, ethereal)
- **Player offhand:** Gemmed Crystal Sword (6x Lem Rune, ethereal)
- **Mercenary:** Act 2 Might (prose: 'Might Aura works great for the Mercenary'; planner mercType 11)
- **Mercenary weapon:** Breath of the Dying War Pike (ethereal)
- **Prebuff:** Call to Arms Flail on swap (Battle Command / Battle Orders)

### hydra-sorceress

Only guide-mention contexts currently imported. Extract variant prose and referenced planner associations before approving build-specific leaves. Existing source anchors:

- `pricing/raw/mr/guides__hydra-sorceress.html` → `/item-spans/0`
- `pricing/raw/mr/guides__hydra-sorceress.html` → `/item-spans/1`
- `pricing/raw/mr/guides__hydra-sorceress.html` → `/item-spans/2`

### lightning-fury-amazon-guide

#### Starter

Source: `pricing/data/wp-a-variants/lightning-fury-amazon-guide.json` → `/variants/0`.

- **Player weapon:** Magic Javelin 40% IAS (table: 'Lancer's Matriarchal Javelin of Quickness')
- **Player offhand:** Rhyme Bone Shield
- **Mercenary:** Act 2 Might (prose: 'Act 2 Might Mercenary with Insight Poleaxe')
- **Mercenary weapon:** Insight Poleaxe

#### Standard

Source: `pricing/data/wp-a-variants/lightning-fury-amazon-guide.json` → `/variants/1`.

- **Player weapon:** Ethereal Titan's Revenge Matriarchal Javelin (table footnote 1: Ethereal Upgraded Titan's Revenge preferred if backed up by another Titan's Revenge or a Thunderstroke)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might (prose and planner mercType 11 agree)
- **Mercenary weapon:** Infinity Giant Thresher (ethereal; Ber Mal Ber Ist)
- **Prebuff:** Call to Arms Crystal Sword (Battle Command x2 then Battle Orders; refresh every 2-3 minutes)

#### Magic Find

Source: `pricing/data/wp-a-variants/lightning-fury-amazon-guide.json` → `/variants/2`.

- **Player weapon:** Ethereal Titan's Revenge Matriarchal Javelin; Thunderstroke (prose alternative setup vs Lightning Immunes)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might (prose and planner mercType 11 agree)
- **Mercenary weapon:** Infinity Giant Thresher (ethereal; Ber Mal Ber Ist)
- **Prebuff:** Call to Arms Crystal Sword (Battle Command x2 then Battle Orders; refresh every 2-3 minutes)

#### Ubers

Source: `pricing/data/wp-a-variants/lightning-fury-amazon-guide.json` → `/variants/3`.

- **Player weapon:** Thunderstroke Matriarchal Javelin
- **Player offhand:** Jeweler's Monarch of Deflecting (4x Lightning Rainbow Facets; planner: 1x -5/+5 'die' + 3x 'up'); Stormshield (prose: 'Use Stormshield if you have not acquired the ultra-rare Jeweler's Monarch of Deflecting')
- **Mercenary:** Act 5 Frenzy Barbarian (prose: 'Act 5 Frenzy Mercenary'; planner mercType 38 = Barbarian Frenzy, Hell)
- **Mercenary weapon:** Plague Phase Blade (Cham Shael Um) x2 - 'for their Lower Resist proc'
- **Mercenary offhand:** (second weapon: Plague Phase Blade)
- **Prebuff:** Treachery (Fade pre-buff for Resistances and Damage Reduction); Call to Arms Crystal Sword (Battle Command x2 then Battle Orders; refresh every 2-3 minutes)

#### Hardcore

Source: `pricing/data/wp-a-variants/lightning-fury-amazon-guide.json` → `/variants/4`.

- **Player weapon:** Ethereal Titan's Revenge Matriarchal Javelin (2023 planner)
- **Player offhand:** Stormshield instead of Spirit Monarch (socketed Ber Rune; with Enigma or Chains of Honor Dusk Shroud exceeds the 50% Damage Reduction cap; 32% FBR breakpoint)
- **Mercenary:** Act 2 Might (2023 planner Hardcore set)
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)

### lightning-sentry-assassin

#### Starter

Source: `pricing/data/wp-a-variants/lightning-sentry-assassin.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Rhyme Bone Shield
- **Mercenary:** Act 2 (planner: Holy Freeze, merc id 10; prose only says Insight Partizan)
- **Mercenary weapon:** Insight Partizan
- **Prebuff:** Burst of Speed

#### Standard

Source: `pricing/data/wp-a-variants/lightning-sentry-assassin.json` → `/variants/1`.

- **Player weapon:** Cunning Greater Talons of Quickness (+3 Trap Skills / 40% IAS / +3 Lightning Sentry / +3 Death Sentry / +3 Weapon Block; 2 sockets: 2x Rainbow Facet Lightning -5/+5)
- **Player offhand:** Cunning Greater Talons of Quickness (same claw, 2x Rainbow Facet Lightning -5/+5)
- **Mercenary:** Act 2 Holy Freeze (guide's Mercenary section: 'Use a Desert Mercenary with Holy Freeze Aura'; planner merc id 10)
- **Mercenary weapon:** Infinity Thresher (ethereal)
- **Prebuff:** Call to Arms Flail: Battle Command x2, Battle Orders; Burst of Speed (cast from the weapon swap with most +skills)

#### Magic Find

Source: `pricing/data/wp-a-variants/lightning-sentry-assassin.json` → `/variants/2`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Infinity Thresher (ethereal)
- **Prebuff:** Call to Arms Flail: Battle Command x2, Battle Orders; Burst of Speed

#### Hardcore

Source: `pricing/data/wp-a-variants/lightning-sentry-assassin.json` → `/variants/3`.

- **Player weapon:** Heart of the Oak Flail if no +6 Lightning Sentry claws (102% FCR)
- **Player offhand:** Stormshield socketed with Eld Rune (max block + DR)
- **Mercenary:** unchanged

### lightning-sorceress

#### Starter

Source: `pricing/data/wp-a-variants/lightning-sorceress.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Insight Partizan
- **Prebuff:** Frozen Armor; Thunder Storm

#### Standard

Source: `pricing/data/wp-a-variants/lightning-sorceress.json` → `/variants/1`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Frozen Armor; Thunder Storm

#### Magic Find

Source: `pricing/data/wp-a-variants/lightning-sorceress.json` → `/variants/2`.

- **Player weapon:** Eschuta's Temper socketed with Ist Rune
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Frozen Armor; Thunder Storm

#### Ubers

Source: `pricing/data/wp-a-variants/lightning-sorceress.json` → `/variants/3`.

- **Player weapon:** Crescent Moon Crystal Sword
- **Player offhand:** Stormshield socketed with Shael Rune
- **Mercenary:** Act 5 Frenzy (note: use the Standard Act 2 Might Infinity merc against every Uber except Uber Mephisto)
- **Mercenary weapon:** Plague Phase Blade (Cham Shael Um); Plague Phase Blade (Cham Shael Um)
- **Prebuff:** Fade from Treachery (pre-buff before engaging the Ubers); Call to Arms: Battle Command x2, Battle Orders; Lower Resist from the charge wand

#### Hardcore

Source: `pricing/data/wp-a-variants/lightning-sorceress.json` → `/variants/4`.

- **Player offhand:** Stormshield instead of Spirit (socketed with Ber Rune, or Shael Rune for 48% FBR)
- **Mercenary:** unchanged

### lightning-strike-amazon

#### Starter

Source: `pricing/data/wp-a-variants/lightning-strike-amazon.json` → `/variants/0`.

- **Player weapon:** Titan's Revenge; Thunderstroke (prose alternative)
- **Player offhand:** Rhyme Bone Shield
- **Mercenary:** Act 2 Holy Freeze
- **Mercenary weapon:** Insight Partizan; Hustle (prose alternative for its Fanaticism Aura)
- **Prebuff:** Valkyrie

#### Standard

Source: `pricing/data/wp-a-variants/lightning-strike-amazon.json` → `/variants/1`.

- **Player weapon:** Infinity Matriarchal Spear (+3 Javelin and Spear Skills)
- **Player offhand:** None
- **Mercenary:** Act 1 Cold (Freezing Arrow Rogue)
- **Mercenary weapon:** Faith Matriarchal Bow
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Valkyrie; Fade from Treachery (planner buff list shows level 15 Fade)

#### Ubers

Source: `pricing/data/wp-a-variants/lightning-strike-amazon.json` → `/variants/2`.

- **Player weapon:** Infinity Matriarchal Spear
- **Player offhand:** None
- **Mercenary:** Act 5 Frenzy ('notoriously hard to keep alive when facing Uber Bosses')
- **Mercenary weapon:** Plague Phase Blade (Cham Shael Um); Plague Phase Blade (Cham Shael Um)
- **Prebuff:** Fade from Treachery before engaging the Ubers; Call to Arms: Battle Command x2, Battle Orders; Valkyrie

#### Hardcore

Source: `pricing/data/wp-a-variants/lightning-strike-amazon.json` → `/variants/3`.

- **Mercenary:** unchanged

### meteor-sorceress

#### Starter

Source: `pricing/data/wp-a-variants/meteor-sorceress.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Ancients' Pledge Kite Shield
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Scythe
- **Prebuff:** Frozen Armor; Enchant (1 point in Starter skills)

#### Standard

Source: `pricing/data/wp-a-variants/meteor-sorceress.json` → `/variants/1`.

- **Player weapon:** The Oculus (ethereal) socketed with Ist Rune; Eschuta's Temper (damage option)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Frozen Armor

#### Magic Find

Source: `pricing/data/wp-a-variants/meteor-sorceress.json` → `/variants/2`.

- **Player weapon:** The Oculus (ethereal) socketed with Ist Rune
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might (MF variant: stack the merc's MF, or use the Standard merc)
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Frozen Armor

#### Set Build

Source: `pricing/data/wp-a-variants/meteor-sorceress.json` → `/variants/3`.

- **Player weapon:** Tal Rasha's Lidless Eye (Tal Rasha's Wrappings) socketed with Ist Rune
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Frozen Armor

#### Ubers

Source: `pricing/data/wp-a-variants/meteor-sorceress.json` → `/variants/4`.

- **Player weapon:** Eschuta's Temper (ethereal) socketed with Rainbow Facet (Fire, die -5/+5)
- **Player offhand:** Stormshield socketed with Um Rune
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Infinity Giant Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Frozen Armor; Lower Resist on bosses from the Wand of Lower Resistance; Enchant on the Mercenary for Attack Rating; Mercenary's Fade from Treachery Archon Plate (helps your own Resistance and Damage Reduction)

#### Hardcore

Source: `pricing/data/wp-a-variants/meteor-sorceress.json` → `/variants/5`.

- **Player weapon:** Eschuta's Temper or Heart of the Oak instead of The Oculus (its Teleport-when-struck is dangerous); Memory Battle Staff / Obsession Archon Staff for Energy Shield staff mods
- **Player offhand:** Stormshield (Dexterity for 50% Chance to Block)
- **Mercenary:** unchanged

### mirrored-blades-warlock-guide

#### Starter

Source: `pricing/data/wp-a-variants/mirrored-blades-warlock-guide.json` → `/variants/0`.

- **Player weapon:** Obedience Grim Scythe (Hel Ko Thul Eth Fal; +300 Def / 30 All Res roll)
- **Player offhand:** Rhyme Grimoire (Shael Eth; Grimoire automods +1 Mirrored Blades / +1 Hex: Purge / +1 Summon Defiler)
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Insight Partizan (ethereal)

#### Standard

Source: `pricing/data/wp-a-variants/mirrored-blades-warlock-guide.json` → `/variants/1`.

- **Player weapon:** Tomb Reaver (ethereal Cryptic Axe, 3 sockets: Protector's Stone Colossal Jewel + Ohm Rune + Zod Rune)
- **Player offhand:** Ars Dul'Mephistos (Occult Tome) socketed with a magic Jewel 30% ED / 60 AR / 7% FHR / 9 Str
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Pride Giant Thresher (ethereal)
- **Prebuff:** Call to Arms Crystal Sword: Battle Command x2 then Battle Orders; Hex: Purge; 2x Summon Defiler; Bind Demon with Fanaticism aura

#### Ubers

Source: `pricing/data/wp-a-variants/mirrored-blades-warlock-guide.json` → `/variants/2`.

- **Player weapon:** Breath of the Dying Thunder Maul (ethereal)
- **Player offhand:** Ars Dul'Mephistos (Occult Tome) socketed with Um Rune
- **Mercenary:** Act 2 Might
- **Mercenary weapon:** Pride Giant Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2, Battle Orders; Consume on a Summon Goatman (damage + life buff); Sigil: Lethargy laid on each boss, recast as needed; Bind Demon with Fanaticism

#### Hardcore

Source: `pricing/data/wp-a-variants/mirrored-blades-warlock-guide.json` → `/variants/3`.

- **Mercenary:** unchanged (Act 2 Might)

### nova-sorceress-guide

#### Starter

Source: `pricing/data/wp-a-variants/nova-sorceress-guide.json` → `/variants/0`.

- **Player weapon:** Spirit Sword (planner: Spirit Crystal Sword, ethereal)
- **Player offhand:** Splendor Shield (planner: Splendor Bone Shield, Eth Lum)
- **Mercenary:** Act 2 Holy Freeze (planner merc id 10)
- **Mercenary weapon:** Insight Partizan in an Exceptional Base (ethereal in planner)

#### Standard

Source: `pricing/data/wp-a-variants/nova-sorceress-guide.json` → `/variants/1`.

- **Player weapon:** Infinity Scythe (Ber Mal Ber Ist, ethereal in planner)
- **Player offhand:** (none — two-handed Infinity)
- **Mercenary:** Act 2 Might or Holy Freeze — 'Use the Might (Damage) or Holy Freeze (Crowd Control) version, depending on your preference' (planner: Holy Freeze, id 10)
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Memory (staff, kept in Horadric Cube) — 'Put Memory in your Horadric Cube to re-buff yourself whenever necessary' (Frozen Armor + Energy Shield); Call to Arms: Battle Command x2 then Battle Orders

#### Magic Find

Source: `pricing/data/wp-a-variants/nova-sorceress-guide.json` → `/variants/2`.

- **Player weapon:** Infinity Scythe (ethereal)
- **Mercenary:** Act 2 Might or Holy Freeze (planner: Holy Freeze)
- **Mercenary weapon:** Insight Giant Thresher (ethereal)
- **Prebuff:** Memory (Horadric Cube); Call to Arms

#### Hydra Hybrid

Source: `pricing/data/wp-a-variants/nova-sorceress-guide.json` → `/variants/3`.

- **Player weapon:** Eschuta's Temper (Ist rune) — planner; gear table alternatives Infinity Scythe / Crescent Moon / The Oculus / Heart of the Oak Flail
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might or Holy Freeze — 'The Mercenary is clear-cut across all variants' (planner: Holy Freeze)
- **Mercenary weapon:** Infinity Giant Thresher (ethereal) — merc holds Infinity since player uses Eschuta's
- **Prebuff:** Memory (Horadric Cube); Call to Arms

### poison-nova-necromancer

#### Starter

Source: `pricing/data/wp-a-variants/poison-nova-necromancer.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Rhyme (planner: Rhyme Fetish Trophy with +2 Poison Nova staffmod)
- **Mercenary:** Act 2 Might (planner merc id 11)
- **Mercenary weapon:** Insight (planner: Insight Poleaxe) — 'for Damage and Mana Regeneration'

#### Standard

Source: `pricing/data/wp-a-variants/poison-nova-necromancer.json` → `/variants/1`.

- **Player weapon:** Death's Web (planner bv7710o1: socketed Defender's Bile Colossal Jewel; older planner 7i9290oy: Rainbow Facet)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might (planner merc id 11) — 'to produce the first body for Corpse Explosion as fast as possible'
- **Mercenary weapon:** Infinity (planner: Infinity War Pike, ethereal) — 'for -85% to Enemy Fire Resistance (to boost Corpse Explosion)'
- **Prebuff:** Call to Arms: Battle Command x2 then Battle Orders; Insight Iron Golem — 'Create an Insight (base doesn't matter) in town, throw it on the ground, and cast Iron Golem on it' for Meditation

#### Magic Find

Source: `pricing/data/wp-a-variants/poison-nova-necromancer.json` → `/variants/2`.

- **Player weapon:** Death's Web (Ist Rune)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might (planner merc id 11) — 'to produce the first body for Corpse Explosion as fast as possible'
- **Mercenary weapon:** Infinity (planner: Infinity War Pike, ethereal) — 'for -85% to Enemy Fire Resistance (to boost Corpse Explosion)'
- **Prebuff:** Call to Arms; Insight Iron Golem

#### Hardcore (Essentials accordion; planner profile 'Hardcore' bv7710o1#5, not a tab)

Source: `pricing/data/wp-a-variants/poison-nova-necromancer.json` → `/variants/3`.

- **Player weapon:** Death's Web (Rainbow Facet)
- **Player offhand:** Homunculus socketed with a Ber Rune (alt: Stormshield with Ber Rune for 50% DR, or Shael Rune for FBR)
- **Mercenary:** Act 2 Might (planner merc id 11) — 'to produce the first body for Corpse Explosion as fast as possible'
- **Mercenary weapon:** Infinity (planner: Infinity War Pike, ethereal) — 'for -85% to Enemy Fire Resistance (to boost Corpse Explosion)'

#### Budget (planner-only profile bv7710o1#4; referenced by stale text 'Starter or Budget Builds' in Summary)

Source: `pricing/data/wp-a-variants/poison-nova-necromancer.json` → `/variants/4`.

- **Player weapon:** White Bone Wand (Dol Io, +3 Poison Nova staffmod)
- **Player offhand:** Trang-Oul's Wing (Um Rune)
- **Mercenary:** Act 2 Might (planner merc id 11)
- **Mercenary weapon:** Insight Colossus Voulge (ethereal)

#### Max Damage (planner-only profile bv7710o1#2)

Source: `pricing/data/wp-a-variants/poison-nova-necromancer.json` → `/variants/5`.

- **Player weapon:** Death's Web (Defender's Bile Colossal Jewel)
- **Player offhand:** Gemmed Monarch (4x Rainbow Facet Jewel)
- **Mercenary:** Act 2 Might (planner merc id 11) — 'to produce the first body for Corpse Explosion as fast as possible'
- **Mercenary weapon:** Infinity (planner: Infinity War Pike, ethereal) — 'for -85% to Enemy Fire Resistance (to boost Corpse Explosion)'

### smite-paladin

#### Starter

Source: `pricing/data/wp-a-variants/smite-paladin.json` → `/variants/0`.

- **Player weapon:** Black Flail (Thul Io Nef)
- **Player offhand:** Rhyme Targe (Shael Eth) — planner note '12 def 45@'
- **Mercenary:** Act 2 Holy Freeze (planner merc id 10; prose: 'Hire the Holy Freeze Aura Mercenary to gain extra Crowd Control'; Might also mentioned for basic farming)
- **Mercenary weapon:** Insight Scythe (Ral Tir Tal Sol)

#### Standard

Source: `pricing/data/wp-a-variants/smite-paladin.json` → `/variants/1`.

- **Player weapon:** Grief Phase Blade (Eth Tir Lo Mal Ral)
- **Player offhand:** Herald of Zakarum (socketed: Protector's Stone Colossal Jewel per planner)
- **Mercenary:** Act 2 Might (planner merc id 11) — 'Both Might Aura and Decrepify from The Reaper's Toll increase your Smite damage'
- **Mercenary weapon:** The Reaper's Toll Thresher (ethereal, socketed jewel)
- **Prebuff:** Call to Arms: Battle Command x2 then Battle Orders; Holy Shield cast on the swap with highest Skill Level; Treachery (on merc or self) to proc Fade: 'Proc Fade from Treachery on a Fire next to the River of Flame Waypoint'

#### High Investment

Source: `pricing/data/wp-a-variants/smite-paladin.json` → `/variants/2`.

- **Player weapon:** Last Wish Phase Blade (Jah Mal Jah Sur Jah Ber)
- **Player offhand:** Exile Vortex Shield (Vex Ohm Ist Dol, ethereal 45@ base, 'ebug')
- **Mercenary:** Act 2 Might (planner merc id 11)
- **Mercenary weapon:** The Reaper's Toll Thresher (ethereal)
- **Prebuff:** Call to Arms: Battle Command x2 + Battle Orders; Holy Shield; Treachery Fade proc

### strafe-amazon

#### Starter

Source: `pricing/data/wp-a-variants/strafe-amazon.json` → `/variants/0`.

- **Player weapon:** Buriza-Do Kyanon (Or Upgraded) — 'nearly irreplaceable in the early game'; planner: socketed jewel
- **Player offhand:** Bolts
- **Mercenary:** Act 2 Might (planner merc id 11)
- **Mercenary weapon:** Insight Partizan (ethereal) — 'for easy Mana management and a good base for him to deal damage'

#### Standard

Source: `pricing/data/wp-a-variants/strafe-amazon.json` → `/variants/1`.

- **Player weapon:** Windforce (planner: Windforce Hydra Bow socketed with Protector's Stone Colossal Jewel)
- **Player offhand:** Arrows
- **Mercenary:** Act 2 Might (planner merc id 11) — Pride: 'provides a huge amount of off-weapon Enhanced Damage. This Mercenary is squishy due to a lack of his own damage for Leeching life.'
- **Mercenary weapon:** Pride Great Poleaxe (ethereal) — 'Level 20 concentration aura'
- **Prebuff:** Demon Limb (Tyrant Club, Hel Rune) kept in Horadric Cube — cast Enchant: 'If not using Lava Gout swap to Demon Limb and cast Enchant on yourself'; Hustle Grand Matron Bow / Hunter's Bow — proc Burst of Speed; Call to Arms Crystal Sword (table option): Battle Command x2 then Battle Orders

#### Magic Find

Source: `pricing/data/wp-a-variants/strafe-amazon.json` → `/variants/2`.

- **Player weapon:** Witchwild String (planner: Diamond Bow, Protector's Stone Colossal Jewel + jewel) — prose does not name a bow change
- **Player offhand:** Arrows
- **Mercenary:** Act 2 Might (planner merc id 11) — Pride: 'provides a huge amount of off-weapon Enhanced Damage. This Mercenary is squishy due to a lack of his own damage for Leeching life.'
- **Mercenary weapon:** Pride Great Poleaxe (ethereal) — 'Level 20 concentration aura'
- **Prebuff:** Hustle Grand Matron Bow (Burst of Speed)

### summoner-necromancer-guide

#### Starter

Source: `pricing/data/wp-a-variants/summoner-necromancer-guide.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword
- **Player offhand:** Ancient's Pledge (planner: Kite Shield)
- **Mercenary:** Act 2 Desert Mercenary, 'a tank and Meditation source' — Insight (Meditation aura); planner #2 merc id 11 Might
- **Mercenary weapon:** Insight Partizan (ethereal, planner #2)

#### Standard

Source: `pricing/data/wp-a-variants/summoner-necromancer-guide.json` → `/variants/1`.

- **Player weapon:** Heart of the Oak Flail (ethereal in planner; table lists 'Heart of the Oak / Spirit Crystal Sword')
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might (planner merc id 11) — Infinity
- **Mercenary weapon:** Infinity (planner: Infinity Thresher, ethereal)
- **Prebuff:** Call to Arms — 'opens up your swap for Call to Arms to prebuff yourself and your Minions'

#### Damage / Ubers

Source: `pricing/data/wp-a-variants/summoner-necromancer-guide.json` → `/variants/2`.

- **Player weapon:** Beast (planner: Beast Berserker Axe)
- **Player offhand:** Spirit Monarch
- **Mercenary:** Act 2 Might (planner merc id 11) — Infinity
- **Mercenary weapon:** Infinity (planner: Infinity Thresher, ethereal)
- **Prebuff:** Call to Arms

#### Hardcore

Source: `pricing/data/wp-a-variants/summoner-necromancer-guide.json` → `/variants/3`.

- **Player weapon:** Heart of the Oak Flail
- **Player offhand:** Homunculus (Shael Rune in planner) — 'to maximize Chance to Block and Faster Block Rate'
- **Mercenary:** Act 2 Might (planner merc id 11) — Infinity
- **Mercenary weapon:** Infinity (planner: Infinity Thresher, ethereal)
- **Prebuff:** Call to Arms

### summoner-warlock-guide

Only guide-mention contexts currently imported. Extract variant prose and referenced planner associations before approving build-specific leaves. Existing source anchors:

- `pricing/raw/mr/guides__summoner-warlock-guide.html` → `/item-spans/2`
- `pricing/raw/mr/guides__summoner-warlock-guide.html` → `/item-spans/3`
- `pricing/raw/mr/guides__summoner-warlock-guide.html` → `/item-spans/4`

### wake-of-fire-assassin

#### Starter

Source: `pricing/data/wp-a-variants/wake-of-fire-assassin.json` → `/variants/0`.

- **Player weapon:** Spirit Crystal Sword (planner main hand); Cunning Greater Talons (shop Anya in Act 5; planner: 2x Cunning Greater Talons +3 Traps in inventory)
- **Player offhand:** Ancients' Pledge (planner: Kite Shield)
- **Mercenary:** Act 2 Might (planner merc id 11) — 'Hire the Might Aura Mercenary for extra damage against Fire Immunes'
- **Mercenary weapon:** Insight (planner: Insight Scythe) — 'an easy Runeword to make that gives a great amount of damage and Quality of Life with Meditation'

#### Standard

Source: `pricing/data/wp-a-variants/wake-of-fire-assassin.json` → `/variants/1`.

- **Player weapon:** Cunning Greater Talons of Quickness (+3 Traps, 40 IAS; staffmods +3 Wake of Fire / +3 Weapon Block / +3 Fire Blast; 2 sockets with jewels) — 'Plague Greater Talons is a great alternative to those expensive +6 Claws'
- **Player offhand:** Spirit Monarch — 'To maximize your damage, use a second Cunning Greater Talons of Quickness instead of Spirit Monarch'
- **Mercenary:** Act 2 Might (planner merc id 11) — 'Hire a Might Aura Mercenary for extra damage against Single Target and Fire Immunes'
- **Mercenary weapon:** Infinity Giant Thresher (ethereal) — 'pierces Resistances and even breaks some Immunities'
- **Prebuff:** Call to Arms (table swap option): Battle Command x2 then Battle Orders; Burst of Speed cast from the Weapon Swap with the most +x to Skills

#### Hardcore (Essentials accordion + planner profile #3, not a tab)

Source: `pricing/data/wp-a-variants/wake-of-fire-assassin.json` → `/variants/2`.

- **Player weapon:** Plague Greater Talons (Cham Shael Um; staffmods +3 Wake of Fire / +3 Fade / +3 Death Sentry) — alt: Heart of the Oak Flail 'to reach the Breakpoint at +102% FCR, if you don't have the recommended BIS Claws'
- **Player offhand:** Stormshield with an Eld Rune (planner: Stormshield Monarch base label) — 'for maximum Chance to Block and Reduced Damage by x%'
- **Mercenary:** Act 2 Might (planner merc id 11) — 'Hire a Might Aura Mercenary for extra damage against Single Target and Fire Immunes'
- **Mercenary weapon:** Infinity Giant Thresher (ethereal) — 'pierces Resistances and even breaks some Immunities'
- **Prebuff:** Fade instead of Burst of Speed

#### Sunder Charm (planner-only profile #4)

Source: `pricing/data/wp-a-variants/wake-of-fire-assassin.json` → `/variants/3`.

- **Player weapon:** Cunning Greater Talons of Quickness (+3 WoF/+3 WB/+3 Fire Blast, 2 jewels)
- **Player offhand:** Cunning Greater Talons of Quickness (second claw)
- **Mercenary:** Act 2 Might (planner merc id 11) — 'Hire a Might Aura Mercenary for extra damage against Single Target and Fire Immunes'
- **Mercenary weapon:** Infinity Giant Thresher (ethereal) — 'pierces Resistances and even breaks some Immunities'

### zeal-paladin

Only guide-mention contexts currently imported. Extract variant prose and referenced planner associations before approving build-specific leaves. Existing source anchors:

- `pricing/raw/mr/guides__zeal-paladin.html` → `/item-spans/0`
- `pricing/raw/mr/guides__zeal-paladin.html` → `/item-spans/1`
- `pricing/raw/mr/guides__zeal-paladin.html` → `/item-spans/2`

## Review expansion for every slot

For each source variant above, traverse every player and mercenary slot, not a hard-coded whitelist. Normalize aliases (Weapon-Swap/Off-Hand Swap, Helmet/Helmets), item collections and composite labels. Retain original text and array index. Assign each occurrence:

1. A mechanics policy: recipe, unique, set, base, or affixed family.
2. One or more role leaves from the main tree: P/M/W/F/L.
3. A reviewed minimum, preferred target, alternative, companion dependency, or discovery-only status.
4. A comparison segment only after relevant facets and legal modifiers are verified.

The compiler must also import generic slot alternatives and mercenary early/mid/end options outside variant arrays in `wp-a-builds.json`, and referenced planner-only profiles. This ledger is the initial structured-variant layer, not a claim that all 60,491 demand occurrences are resolved.
