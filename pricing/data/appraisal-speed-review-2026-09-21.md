# Appraisal speed review — 2026-09-21

Scope: the screenshot of unsocketed, nonethereal Superior Greater Talons with
8 ED, 3 AR, +2 Shadow Master and +1 Lightning Sentry. Local SC/NL/PC/RotW
evidence only; no prices refreshed and no filter changes.

## Finding

The avoidable cost was retrieval volume and repeated reasoning, not Python execution.
The original `html2text.py ... '2 ·' 6000` search matched the contents and body,
producing overlapping text. Broad grep, the complete filter, and every normal/superior
claw bucket added irrelevant material.

Changed `.agents/skills/appraise/SKILL.md` to use distinctive short guide searches,
selected JSON buckets and candidate filter rules, verified d2data mappings, and batched
independent reads. Added schema discovery before nested JSON extraction and a roughly
2,000-token initial retrieval target per item, with expansion whenever evidence is incomplete.

## Measured replay

Five local subprocess replays of the original six evidence commands versus three
bounded commands. Skill loading, model reasoning, screenshot interpretation and
tool-service overhead were excluded. Original output was measured before tool truncation.

| Measurement | Original | Bounded |
|---|---:|---:|
| Evidence commands | 6 | 3 |
| Output bytes | 74,596 | 4,466 |
| Median local execution | 0.071 s | 0.066 s |

Output reduction: **94.0%**. This is not a measured 94% end-to-end latency reduction.
The bounded commands can share one tool round; no fixed round limit applies to unresolved items.

Bounded replay selections:

- `html2text.py guides/pricing.html 'Superior: only' 650`
- `html2text.py guides/warlock.html 'Plain Flails remain' 350`
- Python JSON selection of `greater-talons` buckets `0os/noneth/superior/affixed`
  and `3os/noneth/normal/affixed`, retaining their counts, affixes, dates and quantities;
  Greater Talons name lookup in `pricing/raw/d2data-weapons.json`; enabled filter rules
  with the verified code and superior rarity. For this item the candidate is
  `SHOW Bases WEAPONS`. Category-based items require their own applicable rule checks.

## Independent pressure testing

One sub-agent audited the old workflow and reviewed the changes. A second independently
applied the revised skill to eight cases without receiving expected verdicts. These are
manual behavioral tests, not automated assertions or validation of current market prices.
High-value live research was intentionally excluded from this local-only test.

| Case | Observed result |
|---|---|
| Pictured weak-skill claws | Likely vendor, no exact-roll band; ED alone is not rejection |
| 8 ED claws with +3 Lightning Sentry / +3 Mind Blast | Preserve value; further validation required |
| 3os claws with +3 Phoenix Strike / +1 Claws of Thunder | Preserve value; matched representative, not mixed median |
| Eth rare +2 Warlock Mithril Point | Keep for full appraisal; missing other rolls prevents exact price |
| Sazabi's Mental Sheath | Found mercenary demand and dated worked example |
| Plain demanded skiller without life | Sellable; identify tree before exact ask |
| Two priced observations with `thin:false` | Warn about sparse evidence; do not invent seller counts |
| Unknown item and missing cache | Unresolved; no invented zero or offline network fallback |

The batch test was **not an efficiency pass**: it used 17 shell calls across six tool
rounds and approximately 23,100 output tokens, including two broad JSON reads and a
repeated generic guide query. This prompted the schema-first and narrow-retry additions.
Eight successful routing decisions do not prove that future agents always retrieve efficiently.

A focused follow-up specified a plain +1 Javelin/Spear skiller. The agent retrieved
372 bytes of exact evidence (about 100 output tokens), with no truncation, and supported
a provisional dated Ist ask from one matching quantity-one representative. It correctly
refused to describe the mixed bucket's 17 priced observations as 17 plain-skiller sellers.
There was one syntax-error retry (48 output tokens), plus 519 tokens of instruction checks.
This confirms the narrower retrieval is usable, not that all execution friction is eliminated.

## Correctness improvements uncovered by the tests

- Below 15 ED removes the superior premium, not all item value. Plain skillers and
  imperfect facets also require their lower-roll branches.
- White/gray staff-mod claws need affixed-bucket checks before generic whitelist rejection.
- Worked examples must match deciding rolls and item properties, not just the base name.
- `pricecheck.py` aggregates by item name, not screenshot rolls; `--cache` still requests
  the catalog and can fetch missing listings. It is not an offline switch.
- Mixed-roll medians cannot supply exact-roll asks or fill estimates. Equipment listings
  with quantity greater than one are not verified single-item comparables.
- Fewer than five priced observations need a caveat even if `thin` is false. Listing
  counts are not automatically distinct seller counts.
- Expensive hypothetical upgrades do not trigger live research for a cheap pictured item.
- Missing evidence permits an unresolved price rather than forcing a fabricated rune ask.

Correction to the previous appraisal: its 2-Jah +3 Lightning Sentry/+3 Mind Blast example
had quantity two and should not have been presented as a single-claw comparable. The
single-claw Ber ask remains dated 2026-09-18 evidence; the pictured item's verdict is unchanged.

Validation: skill frontmatter validator and `git diff --check` passed. No executable
repository code changed, so the application test suite was not run.
