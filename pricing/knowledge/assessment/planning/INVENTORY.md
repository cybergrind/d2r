# Assessment source inventory

Frozen 2026-09-24 for [the implementation plan](IMPLEMENTATION_PLAN.md). These are cached candidates and definitions, not assigned trade tiers or reviewed executable rules. Game availability, aliases and source endorsement must be reconciled in Step 1.

## Input sources

- `pricing/data/wp-a-builds.json` and every `wp-a-variants/*.json`
- `pricing/data/appraisal-demand.json` and `appraisal-demand-audit.json`
- `pricing/data/wp-a-bases.json`, `wp-g-bases.json`, `appraisal-utility.json`
- `pricing/data/appraisal-base-coverage.json` and bundled `inventory_tracking/items/data/item_metadata.json`
- `pricing/data/appraisal-item-facts.json`, `appraisal-definitions.json`, `appraisal-value-watch.json`
- `pricing/data/appraisal-recommendations.json` and `appraisal-leveling-candidates-2026-09-23.json`

## All cached builds and variant names

Union of main build records and dedicated variant files. Mercenary, alternative, swap and prebuff contents must be reviewed inside every variant; names alone do not establish coverage. Planner profiles are an additional input, including discovery-only profiles.

| Build | Cached variants |
|---|---|
| abyss-warlock-build-guide | Starter; Standard; Magic Find; Hardcore |
| berserk-barbarian | Starter; Standard; Budget; Hardcore; Chaos Prep; Max Mobility |
| blessed-hammer-paladin | Starter; Standard; Magic Find; Ubers; Hardcore |
| blizzard-sorceress | Starter; Standard; Magic Find; Set Build; Hardcore |
| double-throw-barbarian-guide | Starter; Standard; Magic Find; Hardcore |
| dragon-talon-assassin | Budget; Standard; Hardcore (Essentials > Hardcore tab) |
| dream-paladin | Standard; Hybrid; Ubers; Hardcore (Essentials > Hardcore tab; delta) |
| echoing-strike-warlock-guide | Starter; Standard; Magic Find; Ubers; Hardcore (Essentials > Hardcore tab; delta) |
| enchant-sorceress | Budget; Standard; Magic Find; Max Enchant; Hardcore (Essentials > Hardcore tab; delta) |
| fire-blast-assassin | Starter; Standard; Damage (planner profile only); Hardcore |
| fire-warlock-guide | Starter; Standard; Magic Find; Hardcore |
| fissure-druid | Starter; Standard; Magic Find; Ubers; Hardcore |
| fist-of-the-heavens-paladin | FoH Starter; Holy Bolt Starter; Standard; Tri-Brid; Holy Bolt Support |
| gold-find-barbarian | Budget; Standard; War Cry; Whirlwind; Leap Only |
| lightning-fury-amazon-guide | Starter; Standard; Magic Find; Ubers; Hardcore |
| lightning-sentry-assassin | Starter; Standard; Magic Find; Hardcore |
| lightning-sorceress | Starter; Standard; Magic Find; Ubers; Hardcore |
| lightning-strike-amazon | Starter; Standard; Ubers; Hardcore |
| meteor-sorceress | Starter; Standard; Magic Find; Set Build; Ubers; Hardcore |
| mirrored-blades-warlock-guide | Starter; Standard; Ubers; Hardcore |
| nova-sorceress-guide | Starter; Standard; Magic Find; Hydra Hybrid |
| poison-nova-necromancer | Starter; Standard; Magic Find; Hardcore (Essentials accordion; planner profile 'Hardcore' bv7710o1#5, not a tab); Budget (planner-only profile bv7710o1#4; referenced by stale text 'Starter or Budget Builds' in Summary); Max Damage (planner-only profile bv7710o1#2) |
| smite-paladin | Starter; Standard; High Investment |
| strafe-amazon | Starter; Standard; Magic Find |
| summoner-necromancer-guide | Starter; Standard; Damage / Ubers; Hardcore |
| wake-of-fire-assassin | Starter; Standard; Hardcore (Essentials accordion + planner profile #3, not a tab); Sunder Charm (planner-only profile #4) |

| blood-boil-warlock-guide | Guide mention (demand artifact; no main WP-A build record) |
| fire-wall-sorceress-guide | Damage; Guide mention; Hardcore; Skill Tree; Standard; Starter; Ubers; Unreferenced definitions (demand artifact; no main WP-A build record) |
| frozen-orb-meteor-sorceress | Damage; Guide mention; Hardcore; Magic Find; Set 9; Set Build; Skill Tree; Standard; Standard Chains of Honor; Starter; Unreferenced definitions (demand artifact; no main WP-A build record) |
| frozen-orb-sorceress | Damage; Guide mention; Hardcore; Hydra; Magic Find; Set Build; Skill; Skill Tree; Standard; Starter; Unreferenced definitions (demand artifact; no main WP-A build record) |
| hydra-sorceress | Guide mention; Magic Find; Skills; Standard; Starter; Unreferenced definitions (demand artifact; no main WP-A build record) |
| summoner-warlock-guide | Embeds; Guide mention; Magic Find; Skills; Standard; Starter; Unreferenced definitions (demand artifact; no main WP-A build record) |
| zeal-paladin | Attack Speed; Damage Ubers; Guide mention; Hardcore; Mobility; Mobility/Magic Find; Safe Ubers; Standard Jab-Fend Amazon; Standard Summon Druid; Standard Zeal Paladin; Starter; Sunder Charm; Sustain; Ubers; Unreferenced definitions; White Skills (demand artifact; no main WP-A build record) |

Shared planner profiles are an additional discovery collection, not a 34th build. Preserve their source associations and review endorsement before creating build roles.

## All 62 curated base seeds

| Base | Cached recipe associations (validate eligibility per version) |
|---|---|
| Archon Plate | Enigma, Chains of Honor, Fortitude, Dragon, Bramble |
| Archon Staff | Obsession, Breath of the Dying |
| Balrog Blade | Oath |
| Battle Staff | Memory |
| Berserker Axe | Fortitude, Breath of the Dying, Doom, Beast, Death |
| Bone Shield | Splendor, Rhyme |
| Bone Wand | White |
| Brandistock | Strength |
| Cap | Lore |
| Carnage Helm | Wisdom |
| Colossus Blade | Unbending Will, Death |
| Colossus Voulge | Insight |
| Crown | Wisdom |
| Cryptic Sword | Oath |
| Crystal Sword | Spirit, Plague, Call to Arms, Lawbringer, Crescent Moon |
| Diadem | Lore, Bulwark, Temper, Ground, Cure, Wisdom, Dream, Flickering Flame, Coven, Hearth |
| Double Axe | Doom |
| Dusk Shroud | Enigma, Chains of Honor, Fortitude, Dragon |
| Feral Claws | Mosaic |
| Flail | Heart of the Oak, Call to Arms, Black |
| Giant Thresher | Insight, Infinity, Pride, Obedience |
| Gothic Plate |  |
| Grand Crown | Cure |
| Grand Matron Bow | Faith, Mist |
| Greater Talons | Plague, Mosaic |
| Hard Leather Armor | Stealth |
| Highland Blade | Oath |
| Hunter's Bow | Harmony, Hustle, Mania |
| Hydra Bow | Breath of the Dying, Mist |
| Kite Shield | Ancient's Pledge, Sanctuary |
| Kris | Plague |
| Large Shield | Ancient's Pledge |
| Leather Armor | Stealth |
| Legend Spike | Void |
| Legend Sword | Lawbringer |
| Mage Plate | Enigma, Smoke, Lionheart, Treachery, Duress, Wealth, Hustle, Principle, Enlightenment, Rain, Hysteria, Peace, Bone |
| Maiden Spear | Infinity |
| Mancatcher | Infinity, Pride, Obedience |
| Mask | Wisdom |
| Matriarchal Bow | Insight, Harmony, Hustle, Faith, Mania, Mist |
| Matriarchal Spear | Infinity, Pride, Obedience |
| Monarch | Spirit, Phoenix |
| Partizan | Insight |
| Phase Blade | Plague, Grief, Unbending Will, Hustle, Phoenix, Lawbringer, Crescent Moon, Hand of Justice, Last Wish, Silence, Venom, Mania, Kingslayer |
| Preserved Head | Rhyme |
| Quilted Armor | Stealth |
| Sacred Armor | Fortitude, Bramble |
| Sacred Targe | Spirit, Phoenix, Sanctuary, Dream, Exile |
| Scimitar | Strength |
| Scythe | Infinity |
| Short Staff | Leaf |
| Slayer Guard |  |
| Studded Leather | Stealth, Smoke |
| Targe | Splendor, Ancient's Pledge, Rhyme |
| Thresher | Insight, Infinity, Pride, Obedience |
| Troll Nest | Sanctuary, Dream |
| Vortex Shield | Exile |
| War Pike | Breath of the Dying |
| War Scepter | Call to Arms |
| Ward | Venom |
| Wolf Head | Flickering Flame |
| Zweihander | Grief |

## Exhaustive weapon/armor base routing census

523 rows from the base coverage artifact. A family strategy plus base-specific data handles each row; this does not require one class per name. Quest/disabled entries must receive explicit exclusion dispositions. Curated seeds above do not bound coverage.

### abow

Ashwood Bow, Ceremonial Bow, Grand Matron Bow, Matriarchal Bow, Reflex Bow, Stag Bow.

### ajav

Ceremonial Javelin, Maiden Javelin, Matriarchal Javelin.

### ashd

Aerin Shield, Akaran Rondache, Akaran Targe, Ancient Shield, Crown Shield, Gilded Shield, Heraldic Shield, Protector Shield, Rondache, Royal Shield, Sacred Rondache, Sacred Targe, Targe, Vortex Shield, Zakarum Shield.

### aspe

Ceremonial Pike, Ceremonial Spear, Maiden Pike, Maiden Spear, Matriarchal Pike, Matriarchal Spear.

### axe

Ancient Axe, Axe, Battle Axe, Bearded Axe, Berserker Axe, Broad Axe, Champion Axe, Cleaver, Crowbill, Decapitator, Double Axe, Ettin Axe, Feral Axe, Giant Axe, Glorious Axe, Gothic Axe, Great Axe, Hand Axe, Hatchet, Large Axe, Military Axe, Military Pick, Naga, Silver-edged Axe, Small Crescent, Tabar, Tomahawk, Twin Axe, War Axe, War Spike.

### belt

Battle Belt, Belt, Colossus Girdle, Demonhide Sash, Heavy Belt, Light Belt, Mesh Belt, Mithril Coil, Plated Belt, Sash, Sharkskin Belt, Spiderweb Sash, Troll Belt, Vampirefang Belt, War Belt.

### boot

Battle Boots, Boneweave Boots, Boots, Chain Boots, Demonhide Boots, Greaves, Heavy Boots, Light Plated Boots, Mesh Boots, Mirrored Boots, Myrmidon Greaves, Scarabshell Boots, Sharkskin Boots, War Boots, Wyrmhide Boots.

### bow

Blade Bow, Cedar Bow, Composite Bow, Crusader Bow, Diamond Bow, Double Bow, Edge Bow, Gothic Bow, Great Bow, Hunter's Bow, Hydra Bow, Long Battle Bow, Long Bow, Long Siege Bow, Long War Bow, Razor Bow, Rune Bow, Shadow Bow, Short Battle Bow, Short Bow, Short Siege Bow, Short War Bow, Spider Bow, Ward Bow.

### circ

Circlet, Coronet, Diadem, Tiara.

### club

Barbed Club, Club, Cudgel, Spiked Club, Truncheon, Tyrant Club, Wirt's Leg.

### glov

Battle Gauntlets, Bramble Mitts, Chain Gloves, Crusader Gauntlets, Demonhide Gloves, Gauntlets, Heavy Bracers, Heavy Gloves, Leather Gloves, Light Gauntlets, Ogre Gauntlets, Sharkskin Gloves, Vambraces, Vampirebone Gloves, War Gauntlets.

### grim

Blasphemous Compendium, Blasphemous Grimoire, Burnt Text, Codex, Compendium, Dark Codex, Dark Tome, Forgotten Volume, Grimoire, Occult Codex, Occult Tome, Old Book, Possessed Compendium, Possessed Grimoire, Tome.

### h2h

Blade Talons, Cestus, Claws, Fascia, Hatchet Hands, Katar, Quhab, Scissors Katar, Wrist Blade, Wrist Spike.

### h2h2

Battle Cestus, Feral Claws, Greater Claws, Greater Talons, Hand Scythe, Runic Talons, Scissors Quhab, Scissors Suwayyah, Suwayyah, War Fist, Wrist Sword.

### hamm

Battle Hammer, Great Maul, Hellforge Hammer, Horadric Malus, Legendary Mallet, Martel de Fer, Maul, Ogre Maul, Thunder Maul, War Club, War Hammer.

### head

Bloodlord Skull, Cantor Trophy, Demon Head, Fetish Trophy, Gargoyle Head, Heirophant Trophy, Hellspawn Skull, Minion Skull, Mummified Trophy, Overseer Skull, Preserved Head, Sexton Trophy, Succubus Skull, Unraveller Head, Zombie Head.

### helm

Armet, Basinet, Bone Helm, Bone Visage, Cap, Casque, Corona, Crown, Death Mask, Demonhead, Full Helm, Giant Conch, Grand Crown, Great Helm, Grim Helm, Helm, Hydraskull, Mask, Sallet, Shako, Skull Cap, Spired Helm, War Hat, Winged Helm.

### jave

Balrog Spear, Ghost Glaive, Glaive, Great Pilum, Harpoon, Hyperion Javelin, Javelin, Pilum, Short Spear, Simbilan, Spiculum, Stygian Pilum, Throwing Spear, War Javelin, Winged Harpoon.

### knif

Blade, Bone Knife, Cinquedeas, Dagger, Decoy Gidbinn, Dirk, Fanged Knife, Kriss, Legend Spike, Mithral Point, Poignard, Rondel, Stilleto, The Gidbinn.

### mace

Devil Star, Flail, Flanged Mace, Jagged Star, Khalim's Flail, Khalim's Will, Knout, Mace, Morning Star, Reinforced Mace, Scourge.

### orb

Clasped Orb, Cloudy Sphere, Crystalline Globe, Demon Heart, Dimensional Shard, Eagle Orb, Eldritch Orb, Glowing Orb, Heavenly Stone, Jared's Stone, Sacred Globe, Smoked Sphere, Sparkling Ball, Swirling Crystal, Vortex Orb.

### pelt

Alpha Helm, Antlers, Blood Spirit, Dream Spirit, Earth Spirit, Falcon Mask, Griffon Headress, Hawk Helm, Hunter's Guise, Sacred Feathers, Sky Spirit, Spirit Mask, Sun Spirit, Totemic Mask, Wolf Head.

### phlm

Assault Helmet, Avenger Guard, Carnage Helm, Conqueror Crown, Destroyer Helm, Fanged Helm, Fury Visor, Guardian Crown, Horned Helm, Jawbone Cap, Jawbone Visor, Lion Helm, Rage Mask, Savage Helmet, Slayer Guard.

### pole

Bardiche, Battle Scythe, Bec-de-Corbin, Bill, Colossus Voulge, Cryptic Axe, Giant Thresher, Great Poleaxe, Grim Scythe, Halberd, Lochaber Axe, Ogre Axe, Partizan, Poleaxe, Scythe, Thresher, Voulge, War Scythe.

### scep

Caduceus, Divine Scepter, Grand Scepter, Holy Water Sprinkler, Mighty Scepter, Rune Scepter, Scepter, Seraph Rod, War Scepter.

### shie

Aegis, Ancient Shield, Barbed Shield, Blade Barrier, Bone Shield, Buckler, Defender, Dragon Shield, Gothic Shield, Grim Shield, Heater, Hyperion, Kite Shield, Large Shield, Luna, Monarch, Pavise, Round Shield, Scutum, Small Shield, Spiked Shield, Tower Shield, Troll Nest, Ward.

### spea

Brandistock, Fuscina, Ghost Spear, Hyperion Spear, Lance, Mancatcher, Pike, Spear, Spetum, Stygian Pike, Trident, War Fork, War Pike, War Spear, Yari.

### staf

Archon Staff, Battle Staff, Cedar Staff, Elder Staff, Gnarled Staff, Gothic Staff, Horadric Staff, Jo Staff, Long Staff, Quarterstaff, Rune Staff, Shillelagh, Short Staff, Staff of Kings, Stalagmite, Walking Stick, War Staff.

### swor

Ancient Sword, Ataghan, Balrog Blade, Bastard Sword, Battle Sword, Broad Sword, Champion Sword, Claymore, Colossal Sword, Colossus Blade, Conquest Sword, Cryptic Sword, Crystal Sword, Cutlass, Dacian Falx, Dimensional Blade, Elegant Blade, Espandon, Executioner Sword, Falcata, Falchion, Flamberge, Giant Sword, Gladius, Gothic Sword, Great Sword, Highland Blade, Hydra Edge, Legend Sword, Long Sword, Mythical Sword, Phase Blade, Rune Sword, Saber, Scimitar, Shamshir, Short Sword, Tulwar, Tusk Sword, Two-Handed Sword, War Sword, Zweihander.

### taxe

Balanced Axe, Flying Axe, Francisca, Hurlbat, Throwing Axe, Winged Axe.

### tkni

Balanced Knife, Battle Dart, Flying Knife, Throwing Knife, War Dart, Winged Knife.

### tors

Ancient Armor, Archon Plate, Balrog Skin, Boneweave, Breast Plate, Chain Mail, Chaos Armor, Cuirass, Demonhide Armor, Diamond Mail, Dusk Shroud, Embossed Plate, Field Plate, Full Plate Mail, Ghost Armor, Gothic Plate, Great Hauberk, Hard Leather Armor, Hellforge Plate, Kraken Shell, Lacquered Plate, Leather Armor, Light Plate, Linked Mail, Loricated Mail, Mage Plate, Mesh Armor, Ornate Armor, Plate Mail, Quilted Armor, Ring Mail, Russet Armor, Sacred Armor, Scale Mail, Scarab Husk, Serpentskin Armor, Shadow Plate, Sharktooth Armor, Splint Mail, Studded Leather, Templar Coat, Tigulated Mail, Trellised Armor, Wire Fleece, Wyrmhide.

### tpot

Choking Gas Potion, Exploding Potion, Fulminating Potion, Oil Potion, Rancid Gas Potion, Strangling Gas Potion.

### wand

Bone Wand, Burnt Wand, Ghost Wand, Grave Wand, Grim Wand, Lich Wand, Petrified Wand, Polished Wand, Tomb Wand, Unearthed Wand, Wand, Yew Wand.

### xbow

Arbalest, Ballista, Chu-Ko-Nu, Colossus Crossbow, Crossbow, Demon Crossbow, Gorgon Crossbow, Heavy Crossbow, Light Crossbow, Pellet Bow, Repeating Crossbow, Siege Crossbow.

## Named unique/set review inventory

573 prepared fact records, including identities whose availability or aliases need reconciliation. Every eligible identity needs a tier; none is assigned trash by omission. “Specialized review” below means existing watch evidence, not an automatic high tier. Unwatched items still require roll, ethereal, build and leveling review.

### Unique — specialized review queue (170)

| Identity | Base |
|---|---|
| Alma Negra | Sacred Rondache |
| Andariel's Visage | Demonhead |
| Annihilus | Small Charm |
| Arachnid Mesh | Spiderweb Sash |
| Arioc's Needle | Hyperion Spear |
| Arkaine's Valor | Balrog Skin |
| Arreat's Face | Slayer Guard |
| Ars Dul'Mephistos | Occult Tome |
| Ars Tor'Baalos | Blasphemous Compendium |
| Astreon's Iron Ward | Caduceus |
| Atma's Scarab | Amulet |
| Azurewrath | Crystal Sword |
| Azurewrath | Phase Blade |
| Bartuc's Cut-Throat | Greater Talons |
| Black Cleft | Grand Charm |
| Blade of Ali Baba | Tulwar |
| Bloodfist | Heavy Gloves |
| Bloodpact Shard | Mithril Point |
| Bone Break | Grand Charm |
| Bul-Kathos' Wedding Band | Ring |
| Buriza-Do Kyanon | Ballista |
| Butcher's Pupil | Cleaver |
| Chance Guards | Chain Gloves |
| Cold Rupture | Grand Charm |
| Crack of the Heavens | Grand Charm |
| Crafted Black Cleft | Grand Charm |
| Crafted Bone Break | Grand Charm |
| Crafted Crack of the Heavens | Grand Charm |
| Crafted Flame Rift | Grand Charm |
| Crescent Moon | Amulet |
| Crown of Ages | Corona |
| Crown of Thieves | Grand Crown |
| Darkforce Spawn | Bloodlord Skull |
| Death's Fathom | Dimensional Shard |
| Death's Web | Unearthed Wand |
| Deathbit | Battle Dart |
| Defender's Fire | Jewel |
| Demon Limb | Tyrant Club |
| Demon Machine | Chu-Ko-Nu |
| Demon's Arch | Balrog Spear |
| Dracul's Grasp | Vampirebone Gloves |
| Duriel's Shell | Cuirass |
| Dwarf Star | Ring |
| Eaglehorn | Crusader Bow |
| Earthshaker | Battle Hammer |
| Entropy Locket | Amulet |
| Eschuta's Temper | Eldritch Orb |
| Flame Rift | Grand Charm |
| Fleshripper | Fanged Knife |
| Frostburn | Gauntlets |
| Gargoyle's Bite | Winged Harpoon |
| Gerke's Sanctuary | Pavise |
| Gheed's Fortune | Grand Charm |
| Gheed's Wager | Troll Belt |
| Giant Skull | Bone Visage |
| Gimmershred | Flying Axe |
| Goblin Toe | Light Plated Boots |
| Goldskin | Full Plate Mail |
| Goldwrap | Heavy Belt |
| Gore Rider | War Boots |
| Griffon's Eye | Diadem |
| Guardian Angel | Templar Coat |
| Guardian's Light | Jewel |
| Guardian's Thunder | Jewel |
| Gull | Dagger |
| Hand of Blessed Light | Divine Scepter |
| Harlequin Crest | Shako |
| Heaven's Light | Mighty Scepter |
| Hellfire Torch | Large Charm |
| Herald of Zakarum | Gilded Shield |
| Hexfire | Shamshir |
| Highlord's Wrath | Amulet |
| Homunculus | Hierophant Trophy |
| Infernostride | Demonhide Boots |
| Kira's Guardian | Tiara |
| Kuko Shakaku | Cedar Bow |
| Lacerator | Winged Axe |
| Lava Gout | Battle Gauntlets |
| Leviathan | Kraken Shell |
| Lidless Wall | Grim Shield |
| Lightsabre | Phase Blade |
| Magefist | Light Gauntlets |
| Manald Heal | Ring |
| Mang Song's Lesson | Archon Staff |
| Mara's Kaleidoscope | Amulet |
| Marrowwalk | Boneweave Boots |
| Measured Wrath | Burnt Text |
| Metalgrid | Amulet |
| Moser's Blessed Circle | Round Shield |
| Nagelring | Ring |
| Nature's Peace | Ring |
| Nightsmoke | Belt |
| Nightwing's Veil | Spired Helm |
| Nosferatu's Coil | Vampirefang Belt |
| Ondal's Wisdom | Elder Staff |
| Opalvein | Ring |
| Ormus' Robes | Dusk Shroud |
| Peasant Crown | War Hat |
| Protector's Frost | Jewel |
| Protector's Stone | Jewel |
| Que-Hegan's Wisdom | Mage Plate |
| Rainbow Facet | Jewel |
| Rainbow Facet | Jewel |
| Rainbow Facet | Jewel |
| Rainbow Facet | Jewel |
| Rainbow Facet | Jewel |
| Rainbow Facet | Jewel |
| Rainbow Facet | Jewel |
| Rainbow Facet | Jewel |
| Raven Claw | Long Bow |
| Raven Frost | Ring |
| Ravenlore | Sky Spirit |
| Razor's Edge | Tomahawk |
| Razorswitch | Jo Staff |
| Razortail | Sharkskin Belt |
| Rockfleece | Field Plate |
| Rockstopper | Sallet |
| Rotting Fissure | Grand Charm |
| Rune Master | Ettin Axe |
| Sandstorm Trek | Scarabshell Boots |
| Seraph's Hymn | Amulet |
| Shadow Dancer | Myrmidon Greaves |
| Shaftstop | Mesh Armor |
| Silkweave | Mesh Boots |
| Skin of the Flayed One | Demonhide Armor |
| Skin of the Vipermagi | Serpentskin Armor |
| Skull Collector | Rune Staff |
| Skullder's Ire | Russet Armor |
| Sling | Ring |
| Snowclash | Battle Belt |
| Spectral Shard | Blade |
| Spellsteel | Bearded Axe |
| Stealskull | Casque |
| Steelrend | Ogre Gauntlets |
| Stormlash | Scourge |
| Stormshield | Monarch |
| String of Ears | Demonhide Sash |
| Suicide Branch | Burnt Wand |
| Tarnhelm | Skull Cap |
| The Cat's Eye | Amulet |
| The Face of Horror | Mask |
| The Gladiator's Bane | Wire Fleece |
| The Gnasher | Hand Axe |
| The Oculus | Swirling Crystal |
| The Reaper's Toll | Thresher |
| The Rising Sun | Amulet |
| The Scalper | Francisca |
| The Stone of Jordan | Ring |
| Thundergod's Vigor | War Belt |
| Thunderstroke | Matriarchal Javelin |
| Titan's Revenge | Ceremonial Javelin |
| Tomb Reaver | Cryptic Axe |
| Twitchthroe | Studded Leather |
| Tyrael's Might | Sacred Armor |
| Undead Crown | Crown |
| Valkyrie Wing | Winged Helm |
| Vampire Gaze | Grim Helm |
| Venom Ward | Breast Plate |
| Verdungo's Hearty Cord | Mithril Coil |
| War Traveler | Battle Boots |
| Warshrike | Winged Knife |
| Waterwalk | Sharkskin Boots |
| Widowmaker | Ward Bow |
| Windforce | Hydra Bow |
| Wisp Projector | Ring |
| Witchwild String | Short Siege Bow |
| Wizardspike | Bone Knife |
| Wormskull | Bone Helm |
| Wraith Flight | Ghost Glaive |
| Wraithstep | Mirrored Boots |

### Unique — remaining explicit tier review (263)

| Identity | Base |
|---|---|
| Amulet of the Viper | Top of the Horadric Staff |
| Arm of King Leoric | Tomb Wand |
| Ars Al'Diablolos | Blasphemous Grimoire |
| Athena's Wrath | Battle Scythe |
| Atma's Wail | Embossed Plate |
| Axe of Fechmar | Large Axe |
| Baezil's Vortex | Knout |
| Bane Ash | Short Staff |
| Baranar's Star | Devil Star |
| Biggin's Bonnet | Cap |
| Bing Sz Wang | Dacian Falx |
| Black Hades | Chaos Armor |
| Blackbog's Sharp | Cinquedeas |
| Blackhand Key | Grave Wand |
| Blackhorn's Face | Death Mask |
| Blackleach Blade | Bill |
| Blackoak Shield | Luna |
| Blacktongue | Bastard Sword |
| Bladebone | Double Axe |
| Bladebuckle | Plated Belt |
| Blastbark | Long War Bow |
| Blinkbat's Form | Leather Armor |
| Blood Crescent | Scimitar |
| Blood Raven's Charge | Matriarchal Bow |
| Bloodletter | Gladius |
| Bloodmoon | Elegant Blade |
| Bloodrise | Morning Star |
| Bloodthief | Brandistock |
| Bloodtree Stump | War Club |
| Boneflame | Succubus Skull |
| Boneflesh | Plate Mail |
| Bonehew | Ogre Axe |
| Boneshade | Lich Wand |
| Boneslayer Blade | Gothic Axe |
| Bonesnap | Maul |
| Brainhew | Great Axe |
| Bverrit Keep | Tower Shield |
| Carin Shard | Petrified Wand |
| Carrion Wind | Ring |
| Cerebus' Bite | Blood Spirit |
| Chromatic Ire | Cedar Staff |
| Cliffkiller | Large Siege Bow |
| Cloudcrack | Gothic Sword |
| Coif of Glory | Helm |
| Coldkill | Hatchet |
| Coldsteel Eye | Cutlass |
| Constricting Ring | Ring |
| Corpsemourn | Ornate Plate |
| Crafted Cold Rupture | Grand Charm |
| Crafted Rotting Fissure | Grand Charm |
| Crainte Vomir | Espandon |
| Cranebeak | War Spike |
| Crow Caw | Tigulated Mail |
| Crushflange | Mace |
| Culwen's Point | War Sword |
| Dark Clan Crusher | Cudgel |
| Darkfear | Armet |
| Darkglow | Ring Mail |
| Darksight Helm | Basinet |
| Death Cleaver | Berserker Axe |
| Deathspade | Axe |
| Defender's Bile | Jewel |
| Demonhorn's Edge | Destroyer Helm |
| Dimoak's Hew | Bardiche |
| Djinn Slayer | Ataghan |
| Doombringer | Champion Sword |
| Doomslinger | Repeating Crossbow |
| Dragonscale | Zakarum Shield |
| Dreadfang | Legend Sword |
| Duskdeep | Full Helm |
| Earth Shifter | Thunder Maul |
| Endlesshail | Double Bow |
| Ethereal Edge | Silver-edged Axe |
| Executioner's Justice | Glorious Axe |
| Felloak | Club |
| Firelizard's Talons | Feral Claws |
| Flamebellow | Balrog Blade |
| Fleshrender | Barbed Club |
| Frostwind | Cryptic Sword |
| Ghostflame | Legend Spike |
| Ghoulhide | Heavy Bracers |
| Giant Maimer | unresolved |
| Ginther's Rift | Dimensional Blade |
| Gleamscythe | Falchion |
| Gloom's Trap | Mesh Belt |
| Goldstrike Arch | Gothic Bow |
| Gore Ripper | unresolved |
| Gorefoot | Heavy Boots |
| Goreshovel | Broad Axe |
| Gravenspine | Bone Wand |
| Gravepalm | Sharkskin Gloves |
| Greyform | Quilted Armor |
| Grim's Burning Dead | Grim Scythe |
| Griswold's Edge | Broad Sword |
| Guardian Naga | Naga |
| Gut Siphon | Demon Crossbow |
| Halaberd's Reign | Conqueror Crown |
| Hawkmail | Scale Mail |
| Head Hunter's Glory | Troll Nest |
| Headstriker | Battle Sword |
| Heart Carver | Rondel |
| Heavenly Garb | Light Plate |
| Hell Forge Hammer | Hell Forge Hammer |
| Hellcast | Heavy Crossbow |
| Hellclap | Short War Bow |
| Hellmouth | War Gauntlets |
| Hellplague | Long Sword |
| Hellrack | Colossus Crossbow |
| Hellslayer | Decapitator |
| Hone Sundan | Yari |
| Horadric Staff | Horadric Staff |
| Horizon's Tornado | Scourge |
| Hotspur | Boots |
| Howltusk | Great Helm |
| Humongous | Giant Axe |
| Husoldal Evo | Bec-de-Corbin |
| Iceblink | Splint Mail |
| Ichorsting | Crossbow |
| Iron Pelt | Trellised Armor |
| Ironstone | War Hammer |
| Islestrike | Twin Axe |
| Jade Talon | Wrist Sword |
| Jalal's Mane | Totemic Mask |
| Kelpie Snare | Fuscina |
| Khalim's Flail | Khalim's Flail |
| Khalim's Will | Khalim's Will |
| Kinemil's Awl | Giant Sword |
| Knell Striker | Scepter |
| Lance Guard | Barbed Shield |
| Lance of Yaggai | Spetum |
| Langer Briser | Arbalest |
| Larzuk's Champion | unresolved |
| Leadcrow | Light Crossbow |
| Lenymo | Sash |
| Lycander's Aim | Ceremonial Bow |
| Lycander's Flank | Ceremonial Pike |
| Maelstrom | Yew Wand |
| Magewrath | Rune Bow |
| Medusa's Gaze | Aegis |
| Merman's Sprocket | unresolved |
| Messerschmidt's Reaver | Champion Axe |
| Moonfall | Jagged Star |
| Nethercrow | unresolved |
| Nokozan Relic | Amulet |
| Nord's Tenderizer | Truncheon |
| Odium | unresolved |
| Pelta Lunata | Buckler |
| Pierre Tombale Couant | Partizan |
| Plague Bearer | Rune Sword |
| Pluckeye | Short Bow |
| Pompeii's Wrath | Crowbill |
| PreCrafted Black Cleft | Grand Charm |
| PreCrafted Bone Break | Grand Charm |
| PreCrafted Cold Rupture | Grand Charm |
| PreCrafted Crack of the Heavens | Grand Charm |
| PreCrafted Flame Rift | Grand Charm |
| PreCrafted Rotting Fissure | Grand Charm |
| Pus Spitter | Siege Crossbow |
| Radament's Sphere | Ancient Shield |
| Rakescar | War Axe |
| Rattlecage | Gothic Plate |
| Razortine | Trident |
| Ribcracker | Quarterstaff |
| Riphook | Razor Bow |
| Ripsaw | Flamberge |
| Rixot's Keen | Short Sword |
| Rogue's Bow | Composite Bow |
| Rusthandle | Grand Scepter |
| Saracen's Chance | Amulet |
| Schaefer's Hammer | Legendary Mallet |
| Serpent Lord | Long Staff |
| Shadow Killer | Battle Cestus |
| Shadowfang | Two-Handed Sword |
| Siggard's Stealth | unresolved |
| Silks of the Victor | Ancient Armor |
| Skewer of Krintiz | Sabre |
| Skull Splitter | Military Pick |
| Skystrike | Edge Bow |
| Snakecord | Light Belt |
| Soul Drainer | Vambraces |
| Soul Harvest | Scythe |
| Soulfeast Tine | War Fork |
| Soulflay | Claymore |
| Sparking Mail | Chain Mail |
| Spike Thorn | Blade Barrier |
| Spineripper | Poignard |
| Spire of Honor | Lance |
| Spire of Lazarus | Gnarled Staff |
| Spirit Forge | Linked Mail |
| Spirit Keeper | Earth Spirit |
| Spirit Ward | Ward |
| Staff of Kings | Shaft of the Horadric Staff |
| Steel Carapace | Shadow Plate |
| Steel Pillar | War Pike |
| Steel Shade | Armet |
| Steelclash | Kite Shield |
| Steeldriver | Great Maul |
| Steelgoad | Voulge |
| Stone Crusher | Legendary Mallet |
| Stoneraven | Matriarchal Spear |
| Stormchaser | Scutum |
| Stormeye | War Scepter |
| Stormguild | Large Shield |
| Stormrider | Tabar |
| Stormspike | Stiletto |
| Stormspire | Giant Thresher |
| Stormstrike | Short Battle Bow |
| Stoutnail | Spiked Club |
| Sureshrill Frost | Flanged Mace |
| Swordback Hold | Spiked Shield |
| Swordguard | Executioner Sword |
| Tearhaunch | Greaves |
| Templar's Might | Sacred Armor |
| The Atlantean | Ancient Sword |
| The Battlebranch | Poleaxe |
| The Centurion | Hard Leather Armor |
| The Chieftain | Battle Axe |
| The Cranium Basher | Thunder Maul |
| The Diggler | Dirk |
| The Dragon Chang | Spear |
| The Eye of Etlich | Amulet |
| The Fetid Sprinkler | Holy Water Sprinkler |
| The Gavel of Pain | Martel de Fer |
| The General's Tan Do Li Ga | Flail |
| The Grandfather | Colossus Blade |
| The Grim Reaper | War Scythe |
| The Hand of Broc | Leather Gloves |
| The Impaler | War Spear |
| The Iron Jang Bong | War Staff |
| The Jade Tan Do | Kris |
| The Mahim-Oak Curio | Amulet |
| The Meat Scraper | Lochaber Axe |
| The Minotaur | Ancient Axe |
| The Patriarch | Great Sword |
| The Redeemer | Mighty Scepter |
| The Salamander | Battle Staff |
| The Spirit Shroud | Ghost Armor |
| The Tannr Gorerod | Pike |
| The Vile Husk | Tusk Sword |
| The Ward | Gothic Shield |
| Tiamat's Rebuke | Dragon Shield |
| Todesfaelle Flamme | Zweihander |
| Toothrow | Sharktooth Armor |
| Torch of Iro | Wand |
| Treads of Cthon | Chain Boots |
| Umbral Disk | Small Shield |
| Ume's Lament | Grim Wand |
| Unique Warlock Helm | Death Mask |
| Veil of Steel | Spired Helm |
| Venom Grip | Demonhide Gloves |
| Viperfork | Mancatcher |
| Visceratuant | Defender |
| Wall of the Eyeless | Bone Shield |
| Warlord's Trust | Military Axe |
| Warpspear | Gothic Staff |
| Warriv's Warder | unresolved |
| Windhammer | Ogre Maul |
| Witherstring | Hunter's Bow |
| Wizendraw | Long Battle Bow |
| Woestave | Halberd |
| Wolfhowl | Fury Visor |
| Zakarum's Hand | Rune Scepter |
| Zakarum's Salvation | unresolved |

### Set — specialized review queue (47)

| Identity | Base |
|---|---|
| Aldur's Advance | Battle Boots |
| Angelic Halo | Ring |
| Angelic Wings | Amulet |
| Credendum | Mithril Coil |
| Death's Guard | Sash |
| Death's Hand | Leather Gloves |
| Griswold's Honor | Vortex Shield |
| Griswold's Redemption | Caduceus |
| Guillaume's Face | Winged Helm |
| Horazon's Countenance | Demonhead |
| Horazon's Dominion | Russet Armor |
| Horazon's Legacy | Mirrored Boots |
| Horazon's Secrets | Occult Codex |
| Immortal King's Detail | War Belt |
| Immortal King's Forge | War Gauntlets |
| Immortal King's Pillar | War Boots |
| Immortal King's Soul Cage | Sacred Armor |
| Immortal King's Will | Avenger Guard |
| Laying of Hands | Bramble Mitts |
| M'avina's Caster | Grand Matron Bow |
| M'avina's Embrace | Kraken Shell |
| M'avina's Icy Clutch | Battle Gauntlets |
| M'avina's Tenet | Sharkskin Belt |
| M'avina's True Sight | Diadem |
| Magnus' Skin | Sharkskin Gloves |
| Naj's Puzzler | Elder Staff |
| Natalya's Soul | Mesh Boots |
| Sander's Riprap | Heavy Boots |
| Sander's Taboo | Heavy Gloves |
| Sazabi's Cobalt Redeemer | Cryptic Sword |
| Sazabi's Ghost Liberator | Balrog Skin |
| Sazabi's Mental Sheath | Basinet |
| Sigon's Gage | Gauntlets |
| Sigon's Sabot | Greaves |
| Sigon's Visor | Great Helm |
| Sigon's Wrap | Plated Belt |
| Tal Rasha's Adjudication | Amulet |
| Tal Rasha's Fine-Spun Cloth | Mesh Belt |
| Tal Rasha's Guardianship | Lacquered Plate |
| Tal Rasha's Horadric Crest | Death Mask |
| Tal Rasha's Lidless Eye | Swirling Crystal |
| Telling of Beads | Amulet |
| Trang-Oul's Claws | Heavy Bracers |
| Trang-Oul's Girth | Troll Belt |
| Trang-Oul's Guise | Bone Visage |
| Trang-Oul's Scales | Chaos Armor |
| Trang-Oul's Wing | Cantor Trophy |

### Set — remaining explicit tier review (93)

| Identity | Base |
|---|---|
| Aldur's Deception | Shadow Plate |
| Aldur's Rhythm | Jagged Star |
| Aldur's Stony Gaze | Hunter's Guise |
| Angelic Mantle | Ring Mail |
| Angelic Sickle | Sabre |
| Arcanna's Deathwand | War Staff |
| Arcanna's Flesh | Light Plate |
| Arcanna's Head | Skull Cap |
| Arcanna's Sign | Amulet |
| Arctic Binding | Light Belt |
| Arctic Furs | Quilted Armor |
| Arctic Horn | Short War Bow |
| Arctic Mitts | Light Gauntlets |
| Bane's Authority | Light Belt |
| Bane's Oathmaker | Kris |
| Bane's Wraithskin | Hard Leather Armor |
| Berserker's Hatchet | Double Axe |
| Berserker's Hauberk | Splint Mail |
| Berserker's Headgear | Helm |
| Bul-Kathos' Sacred Charge | Colossus Blade |
| Bul-Kathos' Tribal Guardian | Mythical Sword |
| Cathan's Mesh | Chain Mail |
| Cathan's Rule | Battle Staff |
| Cathan's Seal | Ring |
| Cathan's Sigil | Amulet |
| Cathan's Visage | Mask |
| Civerb's Cudgel | Grand Scepter |
| Civerb's Icon | Amulet |
| Civerb's Ward | Large Shield |
| Cleglaw's Claw | Small Shield |
| Cleglaw's Pincers | Chain Gloves |
| Cleglaw's Tooth | Long Sword |
| Cow King's Hide | Studded Leather |
| Cow King's Hooves | Heavy Boots |
| Cow King's Horns | War Hat |
| Dangoon's Teaching | Reinforced Mace |
| Dark Adherent | Dusk Shroud |
| Death's Touch | War Sword |
| Griswold's Heart | Ornate Plate |
| Griswold's Valor | Corona |
| Haemosu's Adamant | Cuirass |
| Horazon's Hold | Demonhide Gloves |
| Hsarus' Iron Fist | Buckler |
| Hsarus' Iron Heel | Chain Boots |
| Hsarus' Iron Stay | Belt |
| Hwanin's Blessing | Belt |
| Hwanin's Justice | Bill |
| Hwanin's Refuge | Tigulated Mail |
| Hwanin's Splendor | Grand Crown |
| Immortal King's Stone Crusher | Ogre Maul |
| Infernal Cranium | Cap |
| Infernal Sign | Heavy Belt |
| Infernal Torch | Grim Wand |
| Iratha's Coil | Crown |
| Iratha's Collar | Amulet |
| Iratha's Cord | Heavy Belt |
| Iratha's Cuff | Light Gauntlets |
| Isenhart's Case | Breast Plate |
| Isenhart's Horns | Full Helm |
| Isenhart's Lightbrand | Broad Sword |
| Isenhart's Parry | Gothic Shield |
| Milabrega's Diadem | Crown |
| Milabrega's Orb | Kite Shield |
| Milabrega's Robe | Ancient Armor |
| Milabrega's Rod | War Scepter |
| Naj's Circlet | Circlet |
| Naj's Light Plate | Hellforge Plate |
| Natalya's Mark | Scissors Suwayyah |
| Natalya's Shadow | Loricated Mail |
| Natalya's Totem | Grim Helm |
| Ondal's Almighty | Spired Helm |
| Rite of Passage | Demonhide Boots |
| Sander's Paragon | Cap |
| Sander's Superstition | Bone Wand |
| Sigon's Guard | Tower Shield |
| Sigon's Shelter | Gothic Plate |
| Taebaek's Glory | Ward |
| Tancred's Crowbill | Military Pick |
| Tancred's Hobnails | Boots |
| Tancred's Skull | Bone Helm |
| Tancred's Spine | Full Plate Mail |
| Tancred's Weird | Amulet |
| Vidala's Ambush | Leather Armor |
| Vidala's Barb | Long Battle Bow |
| Vidala's Fetlock | Light Plated Boots |
| Vidala's Snare | Amulet |
| Warlord's Authority | Plated Belt |
| Warlord's Conquest | Gauntlets |
| Warlord's Crushers | Greaves |
| Warlord's Lust | Great Helm |
| Warlord's Mantle | Full Plate Mail |
| Whitstan's Guard | Round Shield |
| Wilhelm's Pride | Battle Belt |

### Watch names requiring alias/identity reconciliation

None.

## Reviewed leveling seed inventory

Preserve source conditions, companion pieces, class/archetype, side and stage. Priority is an existing recommendation field, not an assigned new leveling tier.

| Item | Side | Context | Conditions |
|---|---|
| Death's Guard | player | Cannot be frozen for attack builds. | [] |
| Death's Hand | player | Attack speed and resistances with the paired belt. | ["Equip Death's Guard as the second Death's Disguise piece for the recommended attack-speed bonus."] |
| Hsarus' Iron Stay | player | Life and cold resistance for early survival. | [] |
| Hsarus' Iron Heel | player | Movement speed and fire resistance; attack-rating set bonus is conditional. | ["Attack-rating set bonus requires a second Hsarus piece (for example Hsarus' Iron Stay). Movement and fire resistance are standalone."] |
| Sigon's Visor | player | Conditional set attack rating for attack builds. | ["Equip at least one other Sigon's Complete Steel piece for the recommended attack-rating bonus."] |
| Sigon's Gage | player | Conditional set attack speed for attack builds. | ["Equip at least one other Sigon's Complete Steel piece for the recommended attack-speed bonus."] |
| Berserker's Headgear | player | Fire resistance for early survival. | [] |
| Infernal Cranium | player | All resistances for early survival. | [] |
| Sander's Paragon | player | Magic find for finding leveling equipment; a farming option. | [] |
| Sander's Taboo | player | Life for survival; attack speed helps attack builds only. | [] |
| Sander's Riprap | player | Fast movement and attributes; attack rating helps attacks only. | [] |
| Magnus' Skin | player | Attack speed, attack rating and fire resistance for attack builds. | [] |
| Vidala's Fetlock | player | Movement speed; weigh the strength investment. | [] |
| Cow King's Hooves | player | Movement speed, dexterity and magic find. | [] |
| Telling of Beads | player | Skills and resistances for progression. | [] |
| Iratha's Coil | player | Fire and lightning resistance for survival. | [] |
| Trang-Oul's Claws | player | Faster cast rate and cold resistance for caster progression. | [] |
| Tal Rasha's Fine-Spun Cloth | player | Mana and magic find for progression or farming. | [] |
| Crushflange | player | Crushing blow for attacking bosses. | [] |
| Knell Striker | player | Crushing blow for attacking bosses. | [] |
| Bul-Kathos' Wedding Band | player | Skills and life for later progression. | [] |
| The Cat's Eye | player | Attack speed, movement and dexterity for attack builds. | [] |
| Dwarf Star | player | Life and fire protection when cast rate is covered elsewhere. | ["Use when your required faster-cast-rate breakpoint is already covered."] |
| Raven Frost | player | Cannot be frozen, dexterity and attack rating for attack builds. | [] |
| The Oculus | player | Sorceress skills and caster utility; consider the teleport-on-hit effect. | [] |
| Arreat's Face | player | Barbarian skills and combat utility for progression. | [] |
| Homunculus | player | Necromancer skills and resistances for progression. | [] |
| Jalal's Mane | player | Druid skills and defensive utility for progression. | [] |
| Herald of Zakarum | player | Paladin skills and defensive utility for progression. | [] |
| Titan's Revenge | player | Amazon javelin skills for javelin progression. | [] |
| Duriel's Shell | player | Resistances, life and cannot be frozen for survival. | [] |
| Duriel's Shell | merc | Resistances, life and cannot be frozen for survival. | ["Check mercenary level, strength and equipment-slot compatibility."] |
| Lidless Wall | player | Skills, cast rate and mana after kills; cover resistances elsewhere. | ["Cover resistances in other equipment."] |
| Moser's Blessed Circle | player | Resistances and customizable sockets for survival. | [] |
| Suicide Branch | player | Cast rate, skills, life and resistances; compare your cast breakpoint. | [] |
| Rockstopper | player | Resistances, recovery and physical damage reduction. | [] |
| Rockstopper | merc | Resistances, recovery and physical damage reduction. | ["Check mercenary level, strength and equipment-slot compatibility."] |
| Infernostride | player | Movement and fire resistance for progression. | [] |
| The Stone of Jordan | player | Skills and mana for skill-based builds. | [] |
| String of Ears | player | Physical damage reduction for survival; life leech helps attacks only. | [] |
| Skin of the Vipermagi | player | Skills, cast rate and resistances for caster progression. | [] |
| Razorswitch | player | Caster skills, cast rate and defensive stats if better alternatives are unavailable. | ["Two-handed staff prevents equipping a shield; compare available alternatives."] |
| Peasant Crown | player | Skills, movement and attributes for leveling. | [] |
| Spectral Shard | player | Cast rate, mana and resistances; account for dexterity investment. | [] |
| Magefist | player | Faster cast rate for casters; fire-skill bonus only benefits relevant skills. | ["Fire-skill bonus is conditional on using fire skills; cast rate remains useful to other casters."] |
| Nightsmoke | player | Mana and resistances for progression. | [] |
| Duskdeep | player | Resistances and damage reduction for early survival. | [] |
| Duskdeep | merc | Resistances and damage reduction for early survival. | ["Check mercenary level, strength and equipment-slot compatibility."] |
| Treads of Cthon | player | Movement and life for early progression. | [] |
| The Eye of Etlich | player | All skills benefits casters too; leech and cold damage apply to attacks. | [] |
| Tarnhelm | player | All skills and magic find for early progression. | [] |
| Maelstrom | player | Early cast rate and lightning resistance; usable by casters beyond Necromancer. | [] |
| Nokozan Relic | player | Fire resistance and recovery for dangerous fire encounters. | [] |
| Gorefoot | player | Movement speed for early progression. | [] |
| Bloodfist | player | Life and hit recovery for early survival. | [] |
| Nagelring | player | Magic find for early farming; attack rating helps attacks only. | [] |
| Pelta Lunata | player | Early vitality, energy and strength with blocking. | [] |
| Biggin's Bonnet | player | Life and mana for very early progression. | [] |
| Skin of the Vipermagi | player | Skills, cast rate and resistances for caster progression. | [] |
| Magefist | player | Faster cast rate for casters; fire-skill bonus only benefits relevant skills. | ["Fire-skill bonus is conditional on using fire skills; cast rate remains useful to other casters."] |
| The Eye of Etlich | player | All skills benefits casters too; leech and cold damage apply to attacks. | [] |
| Hsarus' Iron Heel | player | Movement speed and fire resistance; attack-rating set bonus is conditional. | ["Attack-rating set bonus requires a second Hsarus piece (for example Hsarus' Iron Stay). Movement and fire resistance are standalone."] |
| Sander's Riprap | player | Fast movement and attributes; attack rating helps attacks only. | [] |
| The Stone of Jordan | player | Skills and mana for skill-based builds. | [] |
| Lidless Wall | player | Skills, cast rate and mana after kills; cover resistances elsewhere. | ["Cover resistances in other equipment."] |
| Skin of the Vipermagi | player | Skills, cast rate and resistances for caster progression. | [] |
| Magefist | player | Faster cast rate for casters; fire-skill bonus only benefits relevant skills. | ["Fire-skill bonus is conditional on using fire skills; cast rate remains useful to other casters."] |
| The Eye of Etlich | player | All skills benefits casters too; leech and cold damage apply to attacks. | [] |
| Hsarus' Iron Heel | player | Movement speed and fire resistance; attack-rating set bonus is conditional. | ["Attack-rating set bonus requires a second Hsarus piece (for example Hsarus' Iron Stay). Movement and fire resistance are standalone."] |
| Sander's Riprap | player | Fast movement and attributes; attack rating helps attacks only. | [] |
| The Stone of Jordan | player | Skills and mana for skill-based builds. | [] |
| Hsarus' Iron Heel | player | Movement speed and fire resistance; attack-rating set bonus is conditional. | ["Attack-rating set bonus requires a second Hsarus piece (for example Hsarus' Iron Stay). Movement and fire resistance are standalone."] |
| Sander's Riprap | player | Fast movement and attributes; attack rating helps attacks only. | [] |
| The Stone of Jordan | player | Skills and mana for skill-based builds. | [] |
| The Eye of Etlich | player | All skills benefits casters too; leech and cold damage apply to attacks. | [] |
