# Goldwrap farming belt review — 2026-09-25

Second demand batch after the Cow King leveling tail; specialist/leveling work is
next. Reuses the existing engine and cached source extraction. No market collection,
new extractor or item evaluator. Review-effort estimate: 10 minutes for five uses
of one identity, including the cast-rate exception; not a measured speedup claim.

Evidence: `pricing/data/wp-a-builds.json`, SHA256
`8a9da0d8cdd38e74d5b03721f5cf9de78e63c17ce87170cb706a6acfa31d59a2`.
Each role retains the original guide date, URL, exact variant locator and quotes.
Native Goldwrap definition: `pricing/raw/d2data/uniqueitems.json`, ID115;
fixed30MF/10IAS, variable50–80gold/40–60enhanced defense. Native defense variation
does not establish desirability or a market premium.

## Explicit template membership

All members: identified unique Goldwrap, belt family, cited player class. Legal
upgrades retain utility; equip requirements and belt capacity remain separate.
Ethereal does not imply higher value; limited player durability is a qualification.
Observed properties alone receive annotations; absent stats are never synthesized.

| Role ID | Variant locator | Main priority | Supporting | Extra gate |
|---|---|---|---|---|
| berserk-barbarian-1-goldwrap | /berserk-barbarian/variants/1 | MF | Gold, IAS | Verify 105FCR on weapon swap separately |
| fire-warlock-guide-2-goldwrap | /fire-warlock-guide/variants/2 | MF | Gold | No IAS priority for spellcasting |
| gold-find-barbarian-1-goldwrap | /gold-find-barbarian/variants/1 | Gold | MF, IAS | Complete damage/survival setup |
| gold-find-barbarian-2-goldwrap | /gold-find-barbarian/variants/2 | Gold | MF | Typed total player FCR >=105 |
| gold-find-barbarian-3-goldwrap | /gold-find-barbarian/variants/3 | Gold | MF, IAS | Final attack breakpoint remains loadout-dependent |

80gold is an optional native maximum target for gold farming, not a required
minimum. Arachnid Mesh remains the War Cry source alternative, not equivalent gold
utility. Parent belt IAS is never treated as cast speed. Full equipment, kill
attribution, attack timing and survival are not proven by a belt component.

These are all five explicit non-planner-only, non-Hardcore Goldwrap player-belt
entries in the current consolidated variants. This does not close every raw guide
or planner lead. Reviewed demand is three builds (Pending, Med lower bound), not
five independent votes. Additional decorated/prose/planner contexts remain in the
full census queue. Named trade tiers and leveling remain independent reviews.

## Validation evidence

`tmp/goldwrap-red.txt`: five missing-role failures before implementation.
`tmp/goldwrap-green.txt`: five role branches plus two bundle checks pass.
`test_goldwrap_priorities.py` covers low gold rolls, missing observed stats, wrong
identity/rarity/class, unidentified items, legal upgrades, and missing/invalid/below
threshold cast context. Defense gets no farming annotation; IAS is absent from
spellcaster priorities. Tests use domain fixtures, not a new live capture.

`tmp/goldwrap-before.json` and `tmp/goldwrap-staged.json`: all18 saved report texts
and numerical prices unchanged. Regression/publication results are recorded in
STATUS.md after completion. Full inventory remains the denominator; this batch adds
one named identity/five reviewed uses, not all-item or market coverage closure.
