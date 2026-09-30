# Reviewed +3 skill-tree amulets — 2026-09-27

User-authorized self-use exception to the shop checker's resale-pattern rules.
Win+D and the automatic shop watcher use these rules directly; the broad starter
catalog stays disabled. These labels do not establish a price or universal BiS.
No change to Alt+D's published knowledge-base assessments is implied.

## Evidence

Reviewed all 26 cached build lists; source research dates are 2026-09-18–20.
Live Maxroll access failed during the review, so no fresh guide verification is claimed.
The following local variant records explicitly support the listed amulets:

| Source under `pricing/data/wp-a-variants/` | Use |
| --- | --- |
| `enchant-sorceress.json` | Budget and Max Enchant: +3 Fire / 10 FCR |
| `meteor-sorceress.json` | Standard damage option: +3 Fire / 26–35 MF |
| `lightning-sorceress.json` | Starter: plain +3 Lightning |
| `poison-nova-necromancer.json` | Starter and planner-only Budget: plain +3 Poison and Bone |
| `abyss-warlock-build-guide.json` | Gear-table alternative: +3 Chaos / 10 FCR, not the selected Standard setup |

Other included uses are mechanical self-use inferences, not explicit BiS endorsements:
Necromancer Summoning, Druid Summoning, Warcries, Traps, Cold, Druid Elemental,
Paladin Combat, Shadow Disciplines buffing, and Eldritch for Echoing Strike.
The Necromancer guide's finished setups select Mara's or a crafted amulet.
+3 Summoning boosts the army, but not Corpse Explosion/curses; compare the whole
loadout. Likewise, Eldritch is a candidate rather than a proven Mara's replacement.
Trees outside this reviewed set do not get a new alert.

## Matching and display

Only identified magic amulets with a decoded +3 native stat188 in a reviewed tree
qualify. Class names distinguish Druid and Necromancer Summoning. Unknown payloads
cannot establish either the skill bonus or the suffix bonus.

- Plain +3: `Build use: +3 Necromancer Summoning Skills — Summon Necromancer`.
- With a reviewed suffix: `Build review: +3 Necromancer Summoning Skills / 10 FCR — Summon Necromancer`.
- Useful suffix bands: 10 FCR, 81–100 life, 26–35 MF; 41–80 gold find for Warcries.
  These are affix-tier review thresholds, not price thresholds. Lower suffix rolls
  retain the plain +3 build-use label.
- FCR is useful only when the complete setup benefits from it. These labels do not
  certify a breakpoint. No 20-FCR magic amulet target is introduced.

Affix eligibility/ranges were checked against pinned
`third-parties/d2data/json/magicprefix.json` and `magicsuffix.json`.
Suffixes are alternatives on an ordinary magic amulet, not a requested combination.
Matching does not attempt to replace the decoder with full item-generation validation.

Verification: `uv run --offline pytest tests/inventory_tracking/shop -q`.
Restart `make serve` for Python rule changes. Ordinary NPC-generated stock does
not supply amulets; these rules can match loaded sold/buyback amulets. They do not
add gambling or closed-stock capture support.
