# Leveling, transcript and socket/runeword research — 2026-09-23

## Result

The supplied 46:53 MrLlamaSC transcript has been read in full. The companion `pricing/data/appraisal-leveling-candidates-2026-09-23.json` extracts 70 named positive or conditional candidates, 13 generic equipment patterns, four negative/out-of-scope mentions, and three additional candidates from the cached Maxroll general leveling guide. Each video candidate carries a timestamp, linked timestamp, slot, type, utility tags and contextual qualification. This is a demand/utility inventory, **not market evidence**. There are no invented prices or numeric item-stat records.

Source: `tmp/ieXIoBklqxo-best-items-to-pick-up-in-diablo-2-along/transcript.txt`, with `meta.json`, `segments.json`, `transcript.json`, `audio.json` and `audio.mp3` alongside. Video: <https://www.youtube.com/watch?v=ieXIoBklqxo>, published **2025-04-24**. A transcript SHA-256 is embedded in the JSON. The source predates RotW and expressly concentrates on progression through approximately level 60, not a complete equipment encyclopaedia.

## What the transcript adds

- Independently useful early set pieces and required pairings: Death's belt/gloves, Hsarus belt/boots, conditional Sigon's pieces, Sander pieces, Berserker headgear, Infernal Cranium, Vidala boots, Cow set, Telling of Beads, Iratha's Coil, Trang gloves, Tal belt.
- Small early uniques that endgame price databases miss: Biggin's Bonnet, Pelta Lunata, Bloodfist, Gorefoot, Nokozan Relic, Maelstrom, Tarnhelm, Eye of Etlich, Treads of Cthon, Duskdeep, Nightsmoke, and Nagelring.
- Later leveling and mercenary survival: Duriel's Shell, Rockstopper, String of Ears, resistance/block shields and caster breakpoint equipment.
- Explicitly conditional keep decisions: Death's Hand needs its belt pairing; Sigon bonuses require other pieces; Razorswitch, Spectral Shard and Suicide Branch compete with Spirit; staff recommendations do not imply every caster should replace a stronger one-handed setup.
- General affix families: movement boots, resistance/life gear, early magic find, cast-rate jewelry and crafted belts, crushing blow for attack builds or mercenaries, topaz armor, resistance rune helms and diamond shields. A named-item-only table cannot represent these adequately.
- Runewords explicitly mentioned: Rhyme, Lore, Strength, Black, Spirit, Ancient's Pledge, Stealth, Leaf and Smoke. Recipe legality must be imported from current game data rather than the spoken shorthand.

All canonical-looking names in the research JSON remain `normalized_from_context`. ASR corrupts names heavily (for example “triangles” → Trang-Oul's Claws; “nail striker” → Knell Striker; “ha” → Herald of Zakarum). These are sensible entity-resolution candidates, not verified game-data identities. Numeric requirements are deliberately null until authoritative catalog linking. Cow King loot behavior, potion critical mechanics, exact set bonus ordering, and the uncertain belt upgrade recipe must not be promoted from this transcript.

## Existing database coverage

| Source | Present coverage | Missing structural information |
|---|---|---|
| `pricing/data/wp-a-runewords.json` | 71 runewords; guide and mercenary demand; recommended bases and socket counts | Not an exhaustive legal base/type recipe catalog; no complete rune sequence/mode/required-level relation |
| `pricing/data/wp-a-bases.json` | 62 recommended bases; sockets by runeword; demand and eth discussion | Recommendations are not all legal bases; some facts are prose; item identities and source dates need normalization |
| `pricing/data/wp-g-bases.json` | 27 ranked base records; mechanics, asks, thresholds, source references | Explicitly excludes bases absent from WP-A/WP-B; cannot serve as complete eligibility database |
| `pricing/raw/d2data-armor.json` and `pricing/raw/d2data-weapons.json` | Base records with verified codes, type, requirements, level, `gemsockets`, stats | Need item type hierarchy, ilvl socket caps, rune recipes, unique/set definitions and localized names joined from matching game version |
| `pricing/raw/mr/resources__general-leveling.html` | General strategies; Raven Claw for Enchant leveling; cow Crystal Sword/Broadsword Spirit candidates | No exhaustive class leveling item lists; page links only seven legacy classes and does not cover Warlock |
| `pricing/raw/mr/items__runewords.html`, `items__runewords.fresh.html`, `items__base-items.html` | Cached recipe recommendations and base reference material | Must extract and validate structured complete relations |
| `pricing/data/wp-a-variants/` | Existing build variant demand, including mercenary contexts | Not substitutes for dedicated class leveling guides and all stage-specific progression choices |

There are no individual class leveling pages in the cached `pricing/raw/` file inventory. The cached general leveling page is dated February 11, 2026 and links individual guides with later update dates; its linked summaries do not contain their equipment lists.

## Socket and recipe modeling requirements

Keep separate relations for **legal recipe compatibility**, **recommended base choices**, **market evidence**, and **leveling utility**. They answer different questions. Base legality needs exact item type and inherited item type eligibility, required socket count, quality restrictions, version/mode, and rune order. Recommended bases additionally need player/mercenary context, strength and dexterity requirements, ethereal preference and staffmod/automod requirements.

For unsocketed items, store the base maximum plus ilvl brackets and acquisition provenance separately from currently open sockets. If screenshot lacks ilvl or drop location, produce conditional socket options instead of promising a Larzuk result. Distinguish natural drop caps by difficulty, Larzuk, and cube socketing. Superior quality and low quality change available methods; damaged-item repair can change ilvl. Staffmod and class automod value must survive the join.

The current ranked base prose demonstrates why mechanical rows need review: the Giant Thresher entry says “never 5 or 6 sockets” while immediately admitting five-socket Obedience; it also describes a six-socket bucket as “BotD/Obedience-class buyers” despite Obedience needing five. These are contradictory recommendations within the same row, not evidence that the base itself is illegal or worthless. Do not import prose gates as unconditional facts.

## Work needed for complete leveling coverage

1. Retrieve all eight current class leveling guides and their linked planner profiles/variants; include Warlock explicitly. Enumerate every equipment slot, suggested alternative, rune/gem craft ingredient, and mercenary loadout at each progression stage.
2. Resolve the 70 extracted names against a versioned unique/set/runeword catalog. Preserve transcript aliases separately and verify set combination sizes. Keep incidental/group mentions distinguishable from fully discussed recommendations.
3. Extract low-level utility patterns with explicit predicates and stage applicability, rather than a blanket rule that every magic or rare item with one helpful affix must be retained forever.
4. Set user-facing stash policy separately: “use now,” “save one for next character,” “conditional pairing,” “sell candidate,” and “unresearched” are different outcomes. No price evidence does not mean no utility.
5. Extend mercenary leveling coverage beyond the transcript. Speaker explicitly says at 27:29 that he is not covering all mercenary gear. Existing runeword demand includes Insight, Bulwark, Cure and others, but those omissions must not be attributed to the video.
6. Complete legal base/socket/runeword relations from game data, then materialize recommended/high-value configurations. Do not enumerate only fashionable elite bases: low requirement normal bases have distinct leveling uses.
7. Market observations may be refreshed separately for actual trading candidates. The leveling keep list remains usable with zero market calls and does not claim sale value for every entry.

## Acceptance checks for the eventual implementation

- Offline lookup of Pelta Lunata and Biggin's Bonnet returns leveling keep context even without a market quote.
- Death's Hand carries the Death's Guard dependency instead of inheriting belt utility unconditionally.
- A low requirement movement boot can match a generic leveling pattern independently of unique/set membership.
- Raven Claw returns the Enchant-leveling condition and Maxroll provenance.
- Spirit sword and Spirit shield are separate legal configurations; a four-socket non-sword weapon is not accepted merely because the video says “weapons.”
- An unsocketed Crystal Sword without ilvl/provenance gets conditional socket guidance.
- A six-socket Giant Thresher is never suggested for five-rune Obedience.
- Every entity can distinguish source utility, legality, price coverage and freshness. An empty market table yields “unpriced,” never “worthless.”
