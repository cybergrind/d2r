# Unique/set roll-range audit

Source date: 2026-09-23. 573 definitions checked.

Coverage is incomplete. This audits catalog mappings, not live capture of every item.
The JSON companion records every item, property slot, parameter and classification.

| Classification | Properties |
| --- | ---: |
| conditional_set_bonus_review | 173 |
| covered_scalar_range | 750 |
| damage_endpoints_not_roll_bounds | 166 |
| encoded_property_review | 149 |
| fixed_or_parameterized_review | 299 |
| fixed_scalar | 1770 |
| uncovered_variable_or_encoding | 64 |

Min/Max fields can describe damage endpoints, proc chance/skill level, or charge
encodings; unequal fields alone do not establish a variable roll. Review categories
remain explicit instead of claiming complete coverage. Conditional set bonuses need
active-set evidence. Base defense currently requires equal base/total captures and
non-ethereal armor with no intrinsic defense modifiers; enhanced/ethereal/upgraded
defense totals and base weapon damage rolls are not fully reconstructed.

## Uncovered variable properties or encodings

| Property | Items |
| --- | --- |
| *charged | Crow Caw |
| Gethit-skill | Defender's Bile, Defender's Fire, Guardian's Light, Guardian's Thunder, Protector's Frost, Protector's Stone |
| ama | Valkyrie Wing |
| att-skill | Hellslayer, Lightsabre, Opalvein, Todesfaelle Flamme |
| aura | Azurewrath |
| charged | Andariel's Visage, Arachnid Mesh, Baezil's Vortex, Blackhand Key, Blood Raven's Charge, Bloodmoon, Bonehew, Boneslayer Blade, Carrion Wind, Corpsemourn, Cranebeak, Darksight Helm, Demon Limb, Earth Shifter, Gargoyle's Bite, Hellfire Torch, Hellrack, Hexfire, Marrowwalk, Metalgrid, Moonfall, Naj's Puzzler, Nature's Peace, Nord's Tenderizer, Radament's Sphere, Spellsteel, Sureshrill Frost, The Gavel of Pain, Todesfaelle Flamme, Wisp Projector, Wolfhowl |
| death-skill | Medusa's Gaze, Rainbow Facet |
| dmg-max | Civerb's Cudgel, Cliffkiller, Humongous, Langer Briser |
| dmg-min | Cliffkiller |
| dru | Athena's Wrath, Spirit Keeper |
| gethit-skill | Andariel's Visage, Arm of King Leoric, Ars Al'Diablolos, Ars Dul'Mephistos, Ars Tor'Baalos, Blackoak Shield, Boneflame, Boneslayer Blade, Carrion Wind, Coldkill, Corpsemourn, Cow King's Hide, Dark Adherent, Darksight Helm, Hwanin's Refuge, Immortal King's Forge, Immortal King's Soul Cage, Infernostride, M'avina's Embrace, Measured Wrath, Medusa's Gaze, Naj's Circlet, Pus Spitter, Radament's Sphere, Saracen's Chance, Snowclash, Spirit Ward, Steel Carapace, Stormchaser, Stormrider, Stormspike, Stormspire, The Gavel of Pain, The Oculus, The Rising Sun, Thundergod's Vigor, Tiamat's Rebuke |
| hit-skill | Atma's Scarab, Baezil's Vortex, Bing Sz Wang, Blackleach Blade, Bonehew, Carrion Wind, Cloudcrack, Coldkill, Dangoon's Teaching, Doombringer, Dracul's Grasp, Dreadfang, Earth Shifter, Earthshaker, Entropy Locket, Flamebellow, Goldstrike Arch, Guardian Naga, Hand of Blessed Light, Hellfire Torch, Hellmouth, Horizon's Tornado, Hwanin's Justice, Lacerator, Lava Gout, Laying of Hands, Moonfall, Ondal's Almighty, Plague Bearer, Pompeii's Wrath, Pus Spitter, Schaefer's Hammer, Shadow Killer, Skystrike, Soul Drainer, Stormlash, Stormrider, The Cranium Basher, The Fetid Sprinkler, The Gavel of Pain, The Reaper's Toll, The Vile Husk, Thunderstroke, Viperfork, Warshrike, Windhammer, Wisp Projector, Witchwild String, Zakarum's Hand |
| kill-skill | Executioner's Justice |
| levelup-skill | Rainbow Facet |
| nec | Boneflame |
| oskill | Flamebellow, Frostwind, Widowmaker, Wolfhowl |
| pal | Alma Negra, Heaven's Light |
| randclassskill | Hellfire Torch |
| reanimate | Tomb Reaver |
| skill | Ars Al'Diablolos, Ars Tor'Baalos, Bloodletter, Bloodpact Shard, Boneshade, Cerebus' Bite, Endlesshail, Firelizard's Talons, Halaberd's Reign, Maelstrom, Marrowwalk, Measured Wrath, Rusthandle, Stormeye, Tal Rasha's Lidless Eye, The Redeemer |
| skill-rand | Ormus' Robes |
| sor | Eschuta's Temper |

Regenerate offline:
```sh
uv run --offline python -m pricing.knowledge.range_audit
```
