# Shop parser RCA and coverage — 2026-09-26

## Larzuk: 49 / 50 items at 14:06:11 Europe/Minsk

The rejected unit `3372686176` is a **magic Amulet**, class ID 535, in Larzuk's
fourth shop grid at zero-based `(9, 0)`. It passed stable unit identity, NPC grid
membership, owner sentinel, item mode and inventory-page checks. The failure is
an eligibility guard in `read_stock`, before `decode_items` or stat decoding.

The guard required `ItemData.flags & 0x2000`. This is not a universal shop-stock
invariant. Local D2MOO `source/D2Game/src/UNIT/SUnitNpc.cpp:664` handles resale by
calling `ITEMS_Duplicate`, placing the result in the NPC inventory, identifying
it, and setting the **separate unit vendor flag**. `source/D2Game/src/ITEMS/Items.cpp:1987`
explicitly clears `IFLAG_INSTORE` in that duplicate. These are legacy algorithm
references, not verified modern unit-flag offsets.

Additional supported-build evidence: the same unit ID and class appear earlier
in `runs/alt-d/20260926T104633Z-148d4cdf/request-3/frozen.json`, in a player-owned
stash (`owner_id=464459175`, page 3, cell `(2,2)`). The later shop snapshot places
it in Larzuk's inventory. A sold item is therefore the likely trigger. Unit-ID
reuse and the lost raw bytes prevent an absolute claim about this transition.

A second bug lost the evidence: the capture raised before appending the raw row.
`shop-diagnostics.json` retained its unit metadata but **not its ItemData or stat
arrays**. Also, one error string conflated a clear flag with unreadable or
quality-mismatched ItemData. The original amulet's exact flag bits and stats
cannot be reconstructed from these files. Do not invent a 50-item replay.

## Fix and affected population

- Stable, revalidated NPC grid membership is authoritative; a clear `0x2000`
  flag no longer rejects an item. This covers any resale item quality/base, not
  just amulets or Larzuk. The flag alone never proves NPC ownership.
- Invalid ItemData still fails with a distinct message. Failed rows now retain
  the unit, raw row when available, and error in `rejected_rows`.
- Unresolved-stat messages include vendor, item, unit ID, native stat ID, layer
  and raw value. Raw rows remain in automatic partial-result diagnostics.
- Tests exercise flag-free items across all four tabs through capture and
  decoding; malformed flags still fail. Grid/ownership/mode/page/identity and
  mutation guards remain enforced.

## Handling checklist

| Input / state | Required handling |
| --- | --- |
| Generated stock and player-sold buyback stock | Decode both from verified NPC grids; no mandatory item store bit |
| Player inventory / player trade | Never infer shop ownership from flags; require NPC grid membership |
| Unloaded stock | Explicit open-Trade instruction; zero stock is not a successful negative scan |
| Shop refresh, purchase/sale during capture, leaving town | Reject inconsistent scan and request another Win+D |
| Incomplete unit traversal / inaccessible memory / changed mappings | Fail closed; never claim complete stock |
| Missing or duplicated grid pointers, wrong mode/owner/page | Reject ownership ambiguity |
| Truncated or quality-mismatched ItemData | Preserve available bytes and reject identity ambiguity |
| Unidentified / gamble item | Explicit unsupported hidden affixes, never guess rolls |
| Unknown base class | Require supported metadata update; retain raw item |
| Missing/incomplete stat array | Preserve evidence; partial result |
| Duplicate stat ID/layer pairs | Remain unresolved rather than overwrite values |
| Ordinary scalars, signed values and fixed-point units | Decode using verified shift/semantics; no arbitrary boolean conversion |
| Skills, class skills, all 24 trees, auras, procs and charges | Preserve packed skill/level/layer and magnitude; validate payload |
| Stack bonus, regeneration, repair, flee and text-only effects | Dedicated numeric/rate/scale semantics |
| Base speed/movement, damage, defense, durability, quantity, sockets | Distinguish base totals from rolled modifiers; require context where needed |
| Local ED/defense modifier lists | Merge only when absent from aggregate list; preserve origin |
| Poison duration/rate/source count | Preserve components; combine only when justified |
| Per-level effects | Require viewer level; distinguish coefficient from evaluated bonus |
| Socket contents, set-state effects, superior/rare/unique/runeword identity | Keep identity and component validation; stat readability alone is not complete appraisal |
| Unknown/new/internal/legacy native stats | Keep raw values unresolved until their item semantics are demonstrated |
| Valid but unobserved encodings | Track explicitly; do not claim every possible item was tested |

## Reproducible offline census

Run from the repository root:

```sh
uv run --offline python -m inventory_tracking.shop.audit --output /tmp/shop-parser-audit.json
uv run --offline pytest tests/inventory_tracking/items tests/inventory_tracking/shop -q
```

The audit scans saved JSON recursively, deduplicates native item stat lists,
includes owned damage/defense modifiers, and checks bundled affix/item roll
endpoints, skill families, triggers and per-level effects. It reports malformed
input files separately rather than hiding them. Formula checks use reference
level 91: this is an **encoding audit**, not a historical tooltip replay.

The existing catalog tests additionally exercise level formulas at levels 1,
91 and 99, crafting triggers and every class skill/tree. Neither those tests nor
this census prove completeness of the source-to-metadata extraction or all
possible native item combinations.

Audit result: **2082 JSON files; 886 distinct captured stat lists;
1834 distinct roll endpoints; zero unresolved payloads and zero input errors**.
Metadata SHA256: `6dee4a03ecb8558fec6c563fe6500370c08ec20569b26b5e36f38fa3d6a6712d`.

Of 367 metadata stat IDs, 170 have evidence in this census and
197 have no captured/definition sample here. The latter are an explicit
evidence backlog, **not 197 proven decoder bugs**: the table includes actor-only,
internal and legacy mechanics. For each unexercised ID, establish active item
source, raw encoding/layer/unit, contextual prerequisites, reference semantics,
then add a real or source-backed regression before enabling it.

## Cross-check against raw property sources

A separate direct-property cross-check covered enabled/spawnable unique items,
set items and set bonuses, expansion affixes/automagic, completed runewords and
gems in the pinned d2data tables. Among the 197 IDs without census samples, six
have direct property references in those sources:

| ID | Sources | Source-backed payloads checked |
| --- | --- | --- |
| 219 | Hellslayer, Messerschmidt's Reaver, Eaglehorn | layer 0, coefficients 24 / 20 / 16 |
| 226 | Arctic Gear, Vidala's Rig | layer 0, coefficients 16 / 12 |
| 227 | Heaven's Brethren | layer 0, coefficient 24 |
| 228 | Milabrega's Regalia | layer 0, coefficient 16 |
| 98 | Full-set state bonuses, including Horazon | state layers 175 / 176, value 1 |
| 181 | Natalya's full-set Fade visual | layer 0, value 1 |

All ten payloads decode with the existing strategies. Set bonuses may live on
actor rather than item stat lists; this check does not reclassify them as innate
item affixes. The remaining 191 IDs have no direct references found by this
cross-check. Implicit property functions, skills, crafted recipes, engine-added
stats and future game data require separate evidence; absence of a direct
reference is not proof of impossibility.

## Complete native-stat evidence inventory

Counts refer to audit samples, not all possible values. “No sample” requires the
investigation above; it does not imply the stat is active on obtainable items.

| ID | Native name | Evidence |
| --- | --- | --- |
| 0 | strength | captured: 46, catalog_endpoint: 21 |
| 1 | energy | captured: 41, catalog_endpoint: 19 |
| 2 | dexterity | captured: 49, catalog_endpoint: 20 |
| 3 | vitality | captured: 14, catalog_endpoint: 14 |
| 4 | statpts | No sample |
| 5 | newskills | No sample |
| 6 | hitpoints | No sample |
| 7 | maxhp | captured: 88, catalog_endpoint: 34 |
| 8 | mana | No sample |
| 9 | maxmana | captured: 56, catalog_endpoint: 58 |
| 10 | stamina | No sample |
| 11 | maxstamina | captured: 18, catalog_endpoint: 25 |
| 12 | level | No sample |
| 13 | experience | No sample |
| 14 | gold | No sample |
| 15 | goldbank | No sample |
| 16 | item_armor_percent | captured: 78, catalog_endpoint: 39 |
| 17 | item_maxdamage_percent | captured: 85, catalog_endpoint: 67 |
| 18 | item_mindamage_percent | captured: 85, catalog_endpoint: 67 |
| 19 | tohit | captured: 75, catalog_endpoint: 74 |
| 20 | toblock | captured: 46, catalog_endpoint: 7 |
| 21 | mindamage | captured: 196 |
| 22 | maxdamage | captured: 199 |
| 23 | secondary_mindamage | captured: 134 |
| 24 | secondary_maxdamage | captured: 138 |
| 25 | damagepercent | No sample |
| 26 | manarecovery | No sample |
| 27 | manarecoverybonus | captured: 12, catalog_endpoint: 11 |
| 28 | staminarecoverybonus | captured: 4, catalog_endpoint: 6 |
| 29 | lastexp | No sample |
| 30 | nextexp | No sample |
| 31 | armorclass | captured: 274, catalog_endpoint: 66 |
| 32 | armorclass_vs_missile | captured: 7, catalog_endpoint: 13 |
| 33 | armorclass_vs_hth | captured: 1, catalog_endpoint: 3 |
| 34 | normal_damage_reduction | captured: 15, catalog_endpoint: 15 |
| 35 | magic_damage_reduction | captured: 28, catalog_endpoint: 18 |
| 36 | damageresist | captured: 8, catalog_endpoint: 9 |
| 37 | magicresist | captured: 1, catalog_endpoint: 4 |
| 38 | maxmagicresist | No sample |
| 39 | fireresist | captured: 98, catalog_endpoint: 36 |
| 40 | maxfireresist | captured: 3, catalog_endpoint: 3 |
| 41 | lightresist | captured: 86, catalog_endpoint: 31 |
| 42 | maxlightresist | captured: 4, catalog_endpoint: 3 |
| 43 | coldresist | captured: 87, catalog_endpoint: 33 |
| 44 | maxcoldresist | captured: 3, catalog_endpoint: 2 |
| 45 | poisonresist | captured: 86, catalog_endpoint: 34 |
| 46 | maxpoisonresist | captured: 3, catalog_endpoint: 4 |
| 47 | damageaura | No sample |
| 48 | firemindam | captured: 46, catalog_endpoint: 28 |
| 49 | firemaxdam | captured: 47, catalog_endpoint: 42 |
| 50 | lightmindam | captured: 34, catalog_endpoint: 2 |
| 51 | lightmaxdam | captured: 34, catalog_endpoint: 53 |
| 52 | magicmindam | captured: 2 |
| 53 | magicmaxdam | captured: 2 |
| 54 | coldmindam | captured: 22, catalog_endpoint: 17 |
| 55 | coldmaxdam | captured: 22, catalog_endpoint: 27 |
| 56 | coldlength | captured: 22, catalog_endpoint: 7 |
| 57 | poisonmindam | captured: 26, catalog_endpoint: 6 |
| 58 | poisonmaxdam | captured: 26, catalog_endpoint: 5 |
| 59 | poisonlength | captured: 26, catalog_endpoint: 3 |
| 60 | lifedrainmindam | captured: 34, catalog_endpoint: 14 |
| 61 | lifedrainmaxdam | No sample |
| 62 | manadrainmindam | captured: 35, catalog_endpoint: 14 |
| 63 | manadrainmaxdam | No sample |
| 64 | stamdrainmindam | No sample |
| 65 | stamdrainmaxdam | No sample |
| 66 | stunlength | No sample |
| 67 | velocitypercent | captured: 55 |
| 68 | attackrate | captured: 198 |
| 69 | other_animrate | No sample |
| 70 | quantity | captured: 43 |
| 71 | value | No sample |
| 72 | durability | captured: 537 |
| 73 | maxdurability | captured: 537, catalog_endpoint: 16 |
| 74 | hpregen | captured: 30, catalog_endpoint: 21 |
| 75 | item_maxdurability_percent | No sample |
| 76 | item_maxhp_percent | catalog_endpoint: 5 |
| 77 | item_maxmana_percent | captured: 7, catalog_endpoint: 6 |
| 78 | item_attackertakesdamage | captured: 22, catalog_endpoint: 19 |
| 79 | item_goldbonus | captured: 25, catalog_endpoint: 25 |
| 80 | item_magicbonus | captured: 31, catalog_endpoint: 26 |
| 81 | item_knockback | captured: 3, catalog_endpoint: 1 |
| 82 | item_timeduration | No sample |
| 83 | item_addclassskills | captured: 36, class_skill: 8 |
| 84 | unsentparam1 | No sample |
| 85 | item_addexperience | captured: 2, catalog_endpoint: 3 |
| 86 | item_healafterkill | captured: 1, catalog_endpoint: 11 |
| 87 | item_reducedprices | captured: 2, catalog_endpoint: 2 |
| 88 | item_doubleherbduration | No sample |
| 89 | item_lightradius | captured: 36, catalog_endpoint: 12 |
| 90 | item_lightcolor | No sample |
| 91 | item_req_percent | captured: 19, catalog_endpoint: 11 |
| 92 | item_levelreq | No sample |
| 93 | item_fasterattackrate | captured: 42, catalog_endpoint: 12 |
| 94 | item_levelreqpct | No sample |
| 95 | lastblockframe | No sample |
| 96 | item_fastermovevelocity | captured: 28, catalog_endpoint: 11 |
| 97 | item_nonclassskill | captured: 2, catalog_endpoint: 32 |
| 98 | state | No sample |
| 99 | item_fastergethitrate | captured: 29, catalog_endpoint: 15 |
| 100 | monster_playercount | No sample |
| 101 | skill_poison_override_length | No sample |
| 102 | item_fasterblockrate | captured: 7, catalog_endpoint: 9 |
| 103 | skill_bypass_undead | No sample |
| 104 | skill_bypass_demons | No sample |
| 105 | item_fastercastrate | captured: 53, catalog_endpoint: 11 |
| 106 | skill_bypass_beasts | No sample |
| 107 | item_singleskill | captured: 148, catalog_endpoint: 130, class_skill: 240 |
| 108 | item_restinpeace | catalog_endpoint: 1 |
| 109 | curse_resistance | No sample |
| 110 | item_poisonlengthresist | captured: 10, catalog_endpoint: 3 |
| 111 | item_normaldamage | catalog_endpoint: 8 |
| 112 | item_howl | captured: 3, catalog_endpoint: 7 |
| 113 | item_stupidity | captured: 1, catalog_endpoint: 5 |
| 114 | item_damagetomana | captured: 8, catalog_endpoint: 12 |
| 115 | item_ignoretargetac | captured: 6, catalog_endpoint: 1 |
| 116 | item_fractionaltargetac | captured: 4, catalog_endpoint: 4 |
| 117 | item_preventheal | captured: 3, catalog_endpoint: 1 |
| 118 | item_halffreezeduration | captured: 12, catalog_endpoint: 1 |
| 119 | item_tohit_percent | captured: 14, catalog_endpoint: 22 |
| 120 | item_damagetargetac | captured: 1, catalog_endpoint: 3 |
| 121 | item_demondamage_percent | captured: 6, catalog_endpoint: 24 |
| 122 | item_undeaddamage_percent | captured: 6, catalog_endpoint: 18 |
| 123 | item_demon_tohit | captured: 5, catalog_endpoint: 13 |
| 124 | item_undead_tohit | captured: 4, catalog_endpoint: 15 |
| 125 | item_throwable | No sample |
| 126 | item_elemskill | captured: 6, catalog_endpoint: 3 |
| 127 | item_allskills | captured: 31, catalog_endpoint: 5 |
| 128 | item_attackertakeslightdamage | captured: 2, catalog_endpoint: 11 |
| 129 | ironmaiden_level | No sample |
| 130 | lifetap_level | No sample |
| 131 | thorns_percent | No sample |
| 132 | bonearmor | No sample |
| 133 | bonearmormax | No sample |
| 134 | item_freeze | captured: 2, catalog_endpoint: 4 |
| 135 | item_openwounds | captured: 4, catalog_endpoint: 12 |
| 136 | item_crushingblow | captured: 8, catalog_endpoint: 12 |
| 137 | item_kickdamage | No sample |
| 138 | item_manaafterkill | captured: 19, catalog_endpoint: 11 |
| 139 | item_healafterdemonkill | captured: 2, catalog_endpoint: 4 |
| 140 | item_extrablood | captured: 1, catalog_endpoint: 2 |
| 141 | item_deadlystrike | captured: 8, catalog_endpoint: 11 |
| 142 | item_absorbfire_percent | catalog_endpoint: 4 |
| 143 | item_absorbfire | catalog_endpoint: 12 |
| 144 | item_absorblight_percent | catalog_endpoint: 4 |
| 145 | item_absorblight | catalog_endpoint: 11 |
| 146 | item_absorbmagic_percent | No sample |
| 147 | item_absorbmagic | captured: 2, catalog_endpoint: 6 |
| 148 | item_absorbcold_percent | captured: 3, catalog_endpoint: 6 |
| 149 | item_absorbcold | captured: 1, catalog_endpoint: 10 |
| 150 | item_slow | captured: 3, catalog_endpoint: 9 |
| 151 | item_aura | captured: 2, catalog_endpoint: 32 |
| 152 | item_indesctructible | captured: 9 |
| 153 | item_cannotbefrozen | captured: 4, catalog_endpoint: 1 |
| 154 | item_staminadrainpct | captured: 5, catalog_endpoint: 9 |
| 155 | item_reanimate | captured: 1 |
| 156 | item_pierce | captured: 3, catalog_endpoint: 6 |
| 157 | item_magicarrow | catalog_endpoint: 5 |
| 158 | item_explosivearrow | catalog_endpoint: 6 |
| 159 | item_throw_mindamage | captured: 24 |
| 160 | item_throw_maxdamage | captured: 27 |
| 161 | skill_handofathena | No sample |
| 162 | skill_staminapercent | No sample |
| 163 | skill_passive_staminapercent | No sample |
| 164 | skill_concentration | No sample |
| 165 | skill_enchant | No sample |
| 166 | skill_pierce | No sample |
| 167 | skill_conviction | No sample |
| 168 | skill_chillingarmor | No sample |
| 169 | skill_frenzy | No sample |
| 170 | skill_decrepify | No sample |
| 171 | skill_armor_percent | No sample |
| 172 | alignment | No sample |
| 173 | target0 | No sample |
| 174 | target1 | No sample |
| 175 | goldlost | No sample |
| 176 | conversion_level | No sample |
| 177 | conversion_maxhp | No sample |
| 178 | unit_dooverlay | No sample |
| 179 | attack_vs_montype | No sample |
| 180 | damage_vs_montype | No sample |
| 181 | fade | No sample |
| 182 | armor_override_percent | No sample |
| 183 | lasthitreactframe | No sample |
| 184 | create_season | No sample |
| 185 | bonus_mindamage | No sample |
| 186 | bonus_maxdamage | No sample |
| 187 | item_pierce_cold_immunity | catalog_endpoint: 1 |
| 188 | item_addskill_tab | captured: 41, catalog_endpoint: 78, class_skill: 24 |
| 189 | item_pierce_fire_immunity | catalog_endpoint: 1 |
| 190 | item_pierce_light_immunity | catalog_endpoint: 1 |
| 191 | item_pierce_poison_immunity | catalog_endpoint: 1 |
| 192 | item_pierce_damage_immunity | catalog_endpoint: 1 |
| 193 | item_pierce_magic_immunity | catalog_endpoint: 1 |
| 194 | item_numsockets | captured: 128, catalog_endpoint: 5 |
| 195 | item_skillonattack | captured: 4, trigger: 6 |
| 196 | item_skillonkill | trigger: 4 |
| 197 | item_skillondeath | trigger: 8 |
| 198 | item_skillonhit | captured: 13, trigger: 86 |
| 199 | item_skillonlevelup | trigger: 7 |
| 200 | item_charge_noconsume | catalog_endpoint: 1 |
| 201 | item_skillongethit | captured: 22, trigger: 61 |
| 202 | modifierlist_castid | No sample |
| 203 | passive_mastery_item_req_percent | No sample |
| 204 | item_charged_skill | captured: 40 |
| 205 | item_noconsume | No sample |
| 206 | passive_mastery_noconsume | No sample |
| 207 | passive_mastery_replenish_oncrit | No sample |
| 208 | missile_thorns_percent | No sample |
| 209 | passive_mastery_item_level_req_percent | No sample |
| 210 | ua_escalation | No sample |
| 211 | ua_defeated | No sample |
| 213 | passive_mastery_gethit_rate | No sample |
| 214 | item_armor_perlevel | captured: 7, level_formula: 10 |
| 215 | item_armorpercent_perlevel | No sample |
| 216 | item_hp_perlevel | captured: 7, level_formula: 15 |
| 217 | item_mana_perlevel | captured: 5, level_formula: 5 |
| 218 | item_maxdamage_perlevel | captured: 5, level_formula: 9 |
| 219 | item_maxdamage_percent_perlevel | No sample |
| 220 | item_strength_perlevel | level_formula: 3 |
| 221 | item_dexterity_perlevel | level_formula: 1 |
| 222 | item_energy_perlevel | No sample |
| 223 | item_vitality_perlevel | captured: 1, level_formula: 4 |
| 224 | item_tohit_perlevel | captured: 1, level_formula: 3 |
| 225 | item_tohitpercent_perlevel | captured: 1, level_formula: 1 |
| 226 | item_cold_damagemax_perlevel | No sample |
| 227 | item_fire_damagemax_perlevel | No sample |
| 228 | item_ltng_damagemax_perlevel | No sample |
| 229 | item_pois_damagemax_perlevel | No sample |
| 230 | item_resist_cold_perlevel | No sample |
| 231 | item_resist_fire_perlevel | No sample |
| 232 | item_resist_ltng_perlevel | level_formula: 1 |
| 233 | item_resist_pois_perlevel | No sample |
| 234 | item_absorb_cold_perlevel | level_formula: 2 |
| 235 | item_absorb_fire_perlevel | captured: 1, level_formula: 1 |
| 236 | item_absorb_ltng_perlevel | No sample |
| 237 | item_absorb_pois_perlevel | No sample |
| 238 | item_thorns_perlevel | captured: 1, level_formula: 2 |
| 239 | item_find_gold_perlevel | captured: 1, level_formula: 3 |
| 240 | item_find_magic_perlevel | captured: 1, level_formula: 5 |
| 241 | item_regenstamina_perlevel | captured: 1, level_formula: 1 |
| 242 | item_stamina_perlevel | level_formula: 1 |
| 243 | item_damage_demon_perlevel | level_formula: 3 |
| 244 | item_damage_undead_perlevel | level_formula: 3 |
| 245 | item_tohit_demon_perlevel | captured: 2, level_formula: 1 |
| 246 | item_tohit_undead_perlevel | level_formula: 3 |
| 247 | item_crushingblow_perlevel | No sample |
| 248 | item_openwounds_perlevel | No sample |
| 249 | item_kick_damage_perlevel | No sample |
| 250 | item_deadlystrike_perlevel | captured: 1, level_formula: 5 |
| 251 | item_find_gems_perlevel | No sample |
| 252 | item_replenish_durability | captured: 15 |
| 253 | item_replenish_quantity | captured: 2 |
| 254 | item_extra_stack | captured: 1, catalog_endpoint: 7 |
| 255 | item_find_item | No sample |
| 256 | item_slash_damage | No sample |
| 257 | item_slash_damage_percent | No sample |
| 258 | item_crush_damage | No sample |
| 259 | item_crush_damage_percent | No sample |
| 260 | item_thrust_damage | No sample |
| 261 | item_thrust_damage_percent | No sample |
| 262 | item_absorb_slash | No sample |
| 263 | item_absorb_crush | No sample |
| 264 | item_absorb_thrust | No sample |
| 265 | item_absorb_slash_percent | No sample |
| 266 | item_absorb_crush_percent | No sample |
| 267 | item_absorb_thrust_percent | No sample |
| 268 | item_armor_bytime | No sample |
| 269 | item_armorpercent_bytime | No sample |
| 270 | item_hp_bytime | No sample |
| 271 | item_mana_bytime | No sample |
| 272 | item_maxdamage_bytime | No sample |
| 273 | item_maxdamage_percent_bytime | No sample |
| 274 | item_strength_bytime | No sample |
| 275 | item_dexterity_bytime | No sample |
| 276 | item_energy_bytime | No sample |
| 277 | item_vitality_bytime | No sample |
| 278 | item_tohit_bytime | No sample |
| 279 | item_tohitpercent_bytime | No sample |
| 280 | item_cold_damagemax_bytime | No sample |
| 281 | item_fire_damagemax_bytime | No sample |
| 282 | item_ltng_damagemax_bytime | No sample |
| 283 | item_pois_damagemax_bytime | No sample |
| 284 | item_resist_cold_bytime | No sample |
| 285 | item_resist_fire_bytime | No sample |
| 286 | item_resist_ltng_bytime | No sample |
| 287 | item_resist_pois_bytime | No sample |
| 288 | item_absorb_cold_bytime | No sample |
| 289 | item_absorb_fire_bytime | No sample |
| 290 | item_absorb_ltng_bytime | No sample |
| 291 | item_absorb_pois_bytime | No sample |
| 292 | item_find_gold_bytime | No sample |
| 293 | item_find_magic_bytime | No sample |
| 294 | item_regenstamina_bytime | No sample |
| 295 | item_stamina_bytime | No sample |
| 296 | item_damage_demon_bytime | No sample |
| 297 | item_damage_undead_bytime | No sample |
| 298 | item_tohit_demon_bytime | No sample |
| 299 | item_tohit_undead_bytime | No sample |
| 300 | item_crushingblow_bytime | No sample |
| 301 | item_openwounds_bytime | No sample |
| 302 | item_kick_damage_bytime | No sample |
| 303 | item_deadlystrike_bytime | No sample |
| 304 | item_find_gems_bytime | No sample |
| 305 | item_pierce_cold | No sample |
| 306 | item_pierce_fire | No sample |
| 307 | item_pierce_ltng | No sample |
| 308 | item_pierce_pois | No sample |
| 309 | item_damage_vs_monster | No sample |
| 310 | item_damage_percent_vs_monster | No sample |
| 311 | item_tohit_vs_monster | No sample |
| 312 | item_tohit_percent_vs_monster | No sample |
| 313 | item_ac_vs_monster | No sample |
| 314 | item_ac_percent_vs_monster | No sample |
| 315 | firelength | No sample |
| 316 | burningmin | No sample |
| 317 | burningmax | No sample |
| 318 | progressive_damage | No sample |
| 319 | progressive_steal | No sample |
| 320 | progressive_other | No sample |
| 321 | progressive_fire | No sample |
| 322 | progressive_cold | No sample |
| 323 | progressive_lightning | No sample |
| 324 | item_extra_charges | No sample |
| 325 | progressive_tohit | No sample |
| 326 | poison_count | captured: 26 |
| 327 | damage_framerate | No sample |
| 328 | pierce_idx | No sample |
| 329 | passive_fire_mastery | catalog_endpoint: 7 |
| 330 | passive_ltng_mastery | catalog_endpoint: 6 |
| 331 | passive_cold_mastery | catalog_endpoint: 7 |
| 332 | passive_pois_mastery | captured: 3, catalog_endpoint: 5 |
| 333 | passive_fire_pierce | catalog_endpoint: 9 |
| 334 | passive_ltng_pierce | catalog_endpoint: 9 |
| 335 | passive_cold_pierce | catalog_endpoint: 10 |
| 336 | passive_pois_pierce | catalog_endpoint: 8 |
| 337 | passive_critical_strike | No sample |
| 338 | passive_dodge | No sample |
| 339 | passive_avoid | No sample |
| 340 | passive_evade | No sample |
| 341 | passive_warmth | No sample |
| 342 | passive_mastery_melee_th | No sample |
| 343 | passive_mastery_melee_dmg | No sample |
| 344 | passive_mastery_melee_crit | No sample |
| 345 | passive_mastery_throw_th | No sample |
| 346 | passive_mastery_throw_dmg | No sample |
| 347 | passive_mastery_throw_crit | No sample |
| 348 | passive_weaponblock | No sample |
| 349 | passive_summon_resist | No sample |
| 350 | modifierlist_skill | No sample |
| 351 | modifierlist_level | No sample |
| 352 | last_sent_hp_pct | No sample |
| 353 | source_unit_type | No sample |
| 354 | source_unit_id | No sample |
| 355 | shortparam1 | No sample |
| 356 | questitemdifficulty | captured: 2 |
| 357 | passive_mag_mastery | catalog_endpoint: 2 |
| 358 | passive_mag_pierce | catalog_endpoint: 6 |
| 359 | skill_cooldown | No sample |
| 360 | skill_missile_damage_scale | No sample |
| 361 | psychicward | No sample |
| 362 | psychicwardmax | No sample |
| 363 | skill_channeling_tick | No sample |
| 364 | customization_index | No sample |
| 365 | item_magic_damagemax_perlevel | No sample |
| 366 | passive_dmg_pierce | catalog_endpoint: 2 |
| 367 | heraldtier | No sample |


## Live confirmation

After restart, `runs/alt-d/20260926T111842Z-93b349a1/shop-latest.json`
at 2026-09-26 14:18:50 Europe/Minsk reports **complete: 46 / 46 Larzuk items,
zero issues**, capture 210.5 ms, total 363.6 ms. Stock changed from the original
50-item scan; this validates current live operation, not recovery of the lost
Amulet bytes. The user could not recall whether they had sold items beforehand.

## Validation

- 492 focused item/shop/appraisal tests pass; Ruff, formatting and Pyrefly pass.
- Full suite: 3776 passed, 3 skipped, 5 failed. One failure was the newly added
  test fixture missing `timing`, collected before that fixture was corrected;
  it passes in the final focused run and explicit failure rerun.
- Failure rerun: 18 passed, four pre-existing Fissure-pelt appraisal failures
  remain (`test_fissure_pelts.py` and `test_pelt_stat_priorities.py`, standard and
  magic-find variants). No pricing rules were changed to mask those failures.
