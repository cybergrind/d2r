# Magic shopping coverage — 2026-09-26

Generated offline with `uv run --offline python -m inventory_tracking.shop.build_catalog`.

26 builds; 5126 equipment-list entries; 200 named/generic magic labels; 529 compiled rules.

The JSON catalog preserves every source locator, source hash, item predicate, build association, and equipment-list entry. Names describe cited examples; equivalent compatible bases of the same item type also qualify. Monarch and elite throwing-base restrictions remain explicit.

Named affixes use their minimum legal rolls, summing prefix/suffix contributions to the same stat. Current expansion affixes are used; legacy version-0 records are excluded. The game-data spelling aliases are recorded in `build_catalog.py`.

These are candidates to inspect, not numerical prices or declarations of complete BiS gear. Starter candidates are included. Class/loadout prerequisites are retained as conditions rather than restricting shopping to the currently played class. Sockets, filler investments, staffmods, requirements and the complete loadout still need comparison with the cited setup.

Charms, jewels and other items not present in ordinary vendor stock are cataloged for completeness; the stock reader still only scans real loaded vendor items. No gamble identity is inferred.

## All builds

| Build | Equipment entries | Associated rules |
|---|---:|---:|
| abyss-warlock-build-guide | 146 | 28 |
| berserk-barbarian | 268 | 67 |
| blessed-hammer-paladin | 197 | 32 |
| blizzard-sorceress | 222 | 44 |
| double-throw-barbarian-guide | 268 | 66 |
| dragon-talon-assassin | 111 | 14 |
| dream-paladin | 173 | 36 |
| echoing-strike-warlock-guide | 189 | 29 |
| enchant-sorceress | 173 | 35 |
| fire-blast-assassin | 149 | 22 |
| fire-warlock-guide | 198 | 23 |
| fissure-druid | 248 | 63 |
| fist-of-the-heavens-paladin | 215 | 25 |
| gold-find-barbarian | 198 | 11 |
| lightning-fury-amazon-guide | 237 | 40 |
| lightning-sentry-assassin | 185 | 53 |
| lightning-sorceress | 243 | 64 |
| lightning-strike-amazon | 213 | 79 |
| meteor-sorceress | 241 | 34 |
| mirrored-blades-warlock-guide | 146 | 16 |
| nova-sorceress-guide | 165 | 31 |
| poison-nova-necromancer | 258 | 71 |
| smite-paladin | 159 | 33 |
| strafe-amazon | 169 | 31 |
| summoner-necromancer-guide | 169 | 31 |
| wake-of-fire-assassin | 186 | 52 |

## Every named magic label

| Label | Coverage | Rules |
|---|---|---:|
| Amber Grand Charm | compiled_affixes | 1 |
| Amber Grand Charm of Maiming | compiled_affixes | 1 |
| Amber Small Charm | compiled_affixes | 1 |
| Amber Small Charm of Good Luck | compiled_affixes | 1 |
| Amber Small Charm of Vita | compiled_affixes | 1 |
| Amulet of Teleportation | compiled_affixes | 1 |
| Arch-Devil's Amulet of the Apprentice | compiled_affixes | 1 |
| Arch-Devil's Kris of Lower Resistance | compiled_affixes | 1 |
| Archer's Gloves of Alacrity | compiled_affixes | 1 |
| Artisan's Crown | compiled_affixes | 1 |
| Artisan's Diadem of Luck | compiled_affixes | 1 |
| Artisan's Diadem of Nirvana | compiled_affixes | 1 |
| Artisan's Diadem of Speed | compiled_affixes | 1 |
| Artisan's Tiara of Luck | compiled_affixes | 1 |
| Battle Staff of Teleportation | compiled_affixes | 1 |
| Berserker's Diadem of the Magus | compiled_affixes | 1 |
| Bone Wand of Life Tap | compiled_affixes | 1 |
| Bone Wand of Lower Resistance | compiled_affixes | 1 |
| Burning Grand Charm | compiled_affixes | 1 |
| Burning Grand Charm of Balance | compiled_affixes | 1 |
| Burning Grand Charm of Vita | compiled_affixes | 3 |
| Chilling Grand Charm of Vita | compiled_affixes | 3 |
| Chromatic Amulet | compiled_affixes | 1 |
| Cobalt Demonhide Sash of the Whale | compiled_affixes | 1 |
| Cobalt Heavy Gloves of Alacrity | compiled_affixes | 1 |
| Cobalt Ring | compiled_affixes | 1 |
| Coral Belt of the Squid | compiled_affixes | 1 |
| Coral Gloves of Alacrity | compiled_affixes | 1 |
| Coral Grand Charm | compiled_affixes | 1 |
| Coral Heavy Gloves of Fortune | compiled_affixes | 1 |
| Coral Ring of the Sentinel | compiled_affixes | 1 |
| Cruel Elite Throwing Weapon | compiled_affixes | 1 |
| Cunning Amulet of the Apprentice | compiled_affixes | 1 |
| Cunning Amulet of the Whale | compiled_affixes | 1 |
| Cunning Circlet of the Magus | compiled_affixes | 1 |
| Cunning Greater Claws | compiled_affixes | 1 |
| Cunning Greater Claws of Quickness | compiled_affixes | 1 |
| Cunning Greater Talons | compiled_affixes | 1 |
| Cunning Greater Talons of Quickness | compiled_affixes | 1 |
| Devil's Amulet of the Apprentice | compiled_affixes | 1 |
| Devil's Kris of Lower Resistance | compiled_affixes | 1 |
| Echoing Balanced Knife | compiled_affixes | 1 |
| Emerald Grand Charm | compiled_affixes | 1 |
| Emerald Grand Charm of Maiming | compiled_affixes | 1 |
| Emerald Small Charm | compiled_affixes | 1 |
| Emerald Small Charm of Good Luck | compiled_affixes | 1 |
| Emerald Small Charm of Vita | compiled_affixes | 1 |
| Entrapping Amulet of the Colossus | compiled_affixes | 1 |
| Entrapping Grand Charm of Balance | compiled_affixes | 1 |
| Entrapping Grand Charm of Vita | compiled_affixes | 3 |
| Fine Small Charm | compiled_affixes | 1 |
| Fine Small Charm of Balance | compiled_affixes | 1 |
| Fine Small Charm of Good Luck | compiled_affixes | 1 |
| Fine Small Charm of Inertia | compiled_affixes | 1 |
| Fine Small Charm of Vita | compiled_affixes | 1 |
| Forbidden Amulet of the Apprentice | compiled_affixes | 1 |
| Forbidden Diadem of the Magus | compiled_affixes | 1 |
| Fortuitous Ring of Fortune | compiled_affixes | 1 |
| Fungal Grand Charm | compiled_affixes | 1 |
| Fungal Grand Charm of Balance | compiled_affixes | 1 |
| Fungal Grand Charm of Vita | compiled_affixes | 3 |
| Gaean Amulet | compiled_affixes | 1 |
| Gaean Amulet of Luck | compiled_affixes | 1 |
| Gaean Amulet of Teleportation | compiled_affixes | 1 |
| Gaean Amulet of the Apprentice | compiled_affixes | 1 |
| Gaean Amulet of the Whale | compiled_affixes | 1 |
| Gaean Antlers of the Colossus | compiled_affixes | 1 |
| Gaean Diadem of the Magus | compiled_affixes | 1 |
| Garnet Belt of the Squid | compiled_affixes | 1 |
| Garnet Demonhide Sash of Stability | compiled_affixes | 1 |
| Garnet Gloves of Fortune | compiled_affixes | 1 |
| Garnet Grand Charm | compiled_affixes | 1 |
| Garnet Leather Gloves of Fortune | compiled_affixes | 1 |
| Garnet Ring of Greed | compiled_affixes | 1 |
| Garnet Sharkskin Belt of the Squid | compiled_affixes | 1 |
| Garnet Sharkskin Gloves of Alacrity | compiled_affixes | 1 |
| Glacial Diadem of the Magus | compiled_affixes | 1 |
| Grand Charm | reviewed_generic_combinations | 54 |
| Graverobber's Grand Charm of Balance | compiled_affixes | 1 |
| Graverobber's Grand Charm of Vita | compiled_affixes | 3 |
| Harpoonist's Grand Charm | compiled_affixes | 1 |
| Harpoonist's Grand Charm of Balance | compiled_affixes | 1 |
| Harpoonist's Grand Charm of Inertia | compiled_affixes | 1 |
| Harpoonist's Grand Charm of Vita | compiled_affixes | 3 |
| Jade Grand Charm | compiled_affixes | 1 |
| Javelin of Quickness | compiled_affixes | 1 |
| Jeweler's Diadem of Nirvana | compiled_affixes | 1 |
| Jeweler's Diadem of Speed | compiled_affixes | 1 |
| Jeweler's Dusk Shroud of Precision | compiled_affixes | 1 |
| Jeweler's Dusk Shroud of Stability | compiled_affixes | 1 |
| Jeweler's Monarch of Deflecting | compiled_affixes | 1 |
| Jeweler's Sacred Armor of Stability | compiled_affixes | 1 |
| Lancer's Chain Gloves of Alacrity | compiled_affixes | 1 |
| Lancer's Gloves of Alacrity | compiled_affixes | 1 |
| Lancer's Heavy Gloves of Alacrity | compiled_affixes | 1 |
| Lancer's Matriarchal Javelin of Quickness | compiled_affixes | 1 |
| Lancer's Vampirebone Gloves of Alacrity | compiled_affixes | 1 |
| Lapis Grand Charm of Life | compiled_affixes | 3 |
| Large Charm | reviewed_generic_combinations | 4 |
| Large Charm of Vita | compiled_affixes | 2 |
| Lion Branded Grand Charm of Balance | compiled_affixes | 1 |
| Lion Branded Grand Charm of Vita | compiled_affixes | 3 |
| Long Staff of Teleportation | compiled_affixes | 1 |
| Lower Resist Charge Wand | charge_alias | 1 |
| Magic Amulet | reviewed_generic_combinations | 30 |
| Magic Belt | reviewed_generic_combinations | 9 |
| Magic Boots | reviewed_generic_combinations | 1 |
| Magic Diadem | reviewed_generic_combinations | 17 |
| Magic Gloves | reviewed_generic_combinations | 4 |
| Magic Ring | reviewed_generic_combinations | 6 |
| Natural Grand Charm | compiled_affixes | 1 |
| Natural Grand Charm of Balance | compiled_affixes | 1 |
| Natural Grand Charm of Inertia | compiled_affixes | 1 |
| Natural Grand Charm of Vita | compiled_affixes | 3 |
| Powered Amulet | compiled_affixes | 1 |
| Powered Amulet of the Apprentice | compiled_affixes | 1 |
| Powered Amulet of the Whale | compiled_affixes | 1 |
| Powered Eldritch Orb of the Magus | compiled_affixes | 1 |
| Prismatic Amulet | compiled_affixes | 1 |
| Resistance Grand Charm | reviewed_generic_combinations | 54 |
| Resistance Small Charm | reviewed_generic_combinations | 43 |
| Rose Branded War Scepter of the Apprentice | compiled_affixes | 1 |
| Ruby Boots of Acceleration | compiled_affixes | 1 |
| Ruby Chain Boots of Acceleration | compiled_affixes | 1 |
| Ruby Grand Charm | compiled_affixes | 1 |
| Ruby Grand Charm of Maiming | compiled_affixes | 1 |
| Ruby Heavy Boots of Acceleration | compiled_affixes | 1 |
| Ruby Heavy Boots of Speed | compiled_affixes | 1 |
| Ruby Jewel of Fervor | compiled_affixes | 2 |
| Ruby Large Charm | compiled_affixes | 1 |
| Ruby Small Charm | compiled_affixes | 1 |
| Ruby Small Charm of Good Luck | compiled_affixes | 1 |
| Ruby Small Charm of Vita | compiled_affixes | 1 |
| Russet Ring of the Apprentice | compiled_affixes | 1 |
| Sapphire Chain Boots of Acceleration | compiled_affixes | 1 |
| Sapphire Grand Charm | compiled_affixes | 1 |
| Sapphire Grand Charm of Balance | compiled_affixes | 1 |
| Sapphire Heavy Boots of Acceleration | compiled_affixes | 1 |
| Sapphire Large Charm of Vita | compiled_affixes | 2 |
| Sapphire Small Charm | compiled_affixes | 1 |
| Sapphire Small Charm of Good Luck | compiled_affixes | 1 |
| Scepter of the Apprentice | compiled_affixes | 1 |
| Scintillating Jewel of Fervor | compiled_affixes | 1 |
| Scintillating Ring of the Apprentice | compiled_affixes | 1 |
| Scintillating Ring of the Mammoth | compiled_affixes | 1 |
| Serpent's Small Charm of Good Luck | compiled_affixes | 1 |
| Serpent's Small Charm of Vita | compiled_affixes | 1 |
| Sharp Grand Charm | compiled_affixes | 1 |
| Sharp Grand Charm of Balance | compiled_affixes | 1 |
| Sharp Grand Charm of Dexterity | compiled_affixes | 2 |
| Sharp Grand Charm of Inertia | compiled_affixes | 1 |
| Sharp Grand Charm of Maiming | compiled_affixes | 1 |
| Sharp Grand Charm of Vita | compiled_affixes | 3 |
| Sharp Large Charm of Vita | compiled_affixes | 2 |
| Shimmering Grand Charm | compiled_affixes | 3 |
| Shimmering Grand Charm of Balance | compiled_affixes | 3 |
| Shimmering Grand Charm of Inertia | compiled_affixes | 3 |
| Shimmering Grand Charm of Vita | compiled_affixes | 9 |
| Shimmering Large Charm of Vita | compiled_affixes | 4 |
| Shimmering Small Charm | compiled_affixes | 1 |
| Shimmering Small Charm of Balance | compiled_affixes | 1 |
| Shimmering Small Charm of Good Luck | compiled_affixes | 1 |
| Shimmering Small Charm of Inertia | compiled_affixes | 1 |
| Shimmering Small Charm of Vita | compiled_affixes | 1 |
| Small Charm | reviewed_generic_combinations | 43 |
| Small Charm of Good Luck | compiled_affixes | 1 |
| Small Charm of Sustenance | compiled_affixes | 1 |
| Small Charm of Vita | compiled_affixes | 1 |
| Snake's Small Charm of Life | compiled_affixes | 1 |
| Sparking Amulet of the Apprentice | compiled_affixes | 1 |
| Sparking Grand Charm | compiled_affixes | 1 |
| Sparking Grand Charm of Balance | compiled_affixes | 1 |
| Sparking Grand Charm of Vita | compiled_affixes | 3 |
| Staff of Teleportation | compiled_affixes | 1 |
| Steel Grand Charm | compiled_affixes | 3 |
| Steel Grand Charm of Balance | compiled_affixes | 3 |
| Steel Grand Charm of Inertia | compiled_affixes | 3 |
| Steel Grand Charm of Vita | compiled_affixes | 9 |
| Steel Small Charm | compiled_affixes | 1 |
| Steel Small Charm of Good Luck | compiled_affixes | 1 |
| Steel Small Charm of Vita | compiled_affixes | 1 |
| Teleport Charge Amulet | charge_alias | 1 |
| Teleport Charge Staff | charge_alias | 1 |
| Torrid Amulet of the Apprentice | compiled_affixes | 1 |
| Venomous Amulet | compiled_affixes | 1 |
| Venomous Amulet of Teleportation | compiled_affixes | 1 |
| Venomous Amulet of the Apprentice | compiled_affixes | 1 |
| Venomous Circlet of the Magus | compiled_affixes | 1 |
| Venomous Demon Head | compiled_affixes | 1 |
| Vermilion Jewel | compiled_affixes | 1 |
| Volcanic Amulet | compiled_affixes | 1 |
| Volcanic Amulet of Luck | compiled_affixes | 1 |
| Volcanic Amulet of the Apprentice | compiled_affixes | 1 |
| Volcanic Circlet | compiled_affixes | 1 |
| Volcanic Diadem | compiled_affixes | 1 |
| Volcanic Diadem of Speed | compiled_affixes | 1 |
| Volcanic Eldritch Orb | compiled_affixes | 1 |
| Volcanic Eldritch Orb of the Magus | compiled_affixes | 1 |
| Wand of Life Tap | compiled_affixes | 1 |
| Wand of Lower Resistance | compiled_affixes | 1 |

## Source conflicts

These descriptions cannot be accepted as legal magic prefix/suffix bundles. They remain in the census; they do not create fabricated magic targets.

- Ars Dul'Mephistos (Occult Tome) socketed with a magic Jewel 30% ED / 60 AR / 7% FHR / 9 Str
- Forbidden Diadem of the Magus (+2 Warlock Skills / 20 FCR / 30 FRW / +30 Str / +20 All Res, socketed Ber Rune + Guardian's Light jewel)
- Guillaume's Face (Orphan's Call) socketed with a magic Jewel 30% ED / 60 AR / 9 Str / 9 Dex
- Magic Amulet (+1 Traps / +20 All Res / 25 MF)
- Magic Diadem (+2 Assassin Skills / 30 FRW / +30 Str / +20 All Res / Telekinesis charges; Defender's Fire jewel + Fire Rainbow Facet) — table: Flickering Flame / Harlequin Crest
- Magic Heavy Gloves +Attack Rating / +Dexterity / Resistances
- Magic Ring (+30 Cold Res / MF / +1 Mana after kill)
- Magic Ring of the Apprentice (10 FCR / 6 ML / +90 Mana / All Res / MF)
- Magic Ring of the Apprentice (10 FCR / 6 ML / Mana / All Res / MF)
- Magic Ring of the Apprentice (10 FCR / AR / ML / Life / Mana / All Res) x2

## Runtime and maintenance

The hotkey only loads the generated catalog once and evaluates rules indexed by item type. It does not parse guides, rebuild profiles, query prices or access the network.

Rebuild the catalog after changing build lists, reviewed profiles or item metadata; restart `make serve` after updating the Python code or generated catalog.
