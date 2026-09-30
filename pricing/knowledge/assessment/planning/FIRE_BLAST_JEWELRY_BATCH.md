# Fire Blast affixed jewelry — 2026-09-25

First demand batch after Druid/Paladin caster leveling tail. Two reviewed patterns
reuse the existing predicate/stat engine and the equipped Phoenix check. No new
runtime evaluator. Estimated review effort:10minutes for same-item requirements,
illustrative-roll separation and companion constraints; no speedup claim.

Source: pricing/data/wp-a-builds.json#/fire-blast-assassin/variants/1, SHA256
8a9da0d8cdd38e74d5b03721f5cf9de78e63c17ce87170cb706a6acfa31d59a2.
Original source date/quotes retained in both roles.

## Explicit membership and required versus preferred properties

- `fire-blast-standard-crafted-amulet`: crafted identified nonethereal amulet with
  source12+FCR threshold. Assassin skills,20FCR,20allres and25MF are illustrated
  optional targets, not minima. Captured FCR/Assassin skills desirable, MF supporting;
  the source all-resistance support requires all four observed elements together.
- `fire-blast-standard-rare-ring`: rare identified nonethereal ring with10FCR.
 20strength/40life are optional source targets. Observed strength/life/resistances
  support the role; no fabricated skill/MF/attack-rating priority.

Both require Assassin, total102FCR for the assessed loadout and actual equipped
identified Phoenix Monarch. Missing/unverified companion facts remain unknown.
Each required modifier belongs to the captured jewelry, not another item or the
character total. These are candidate component uses, not proof of ownership of both
rings or the full defensive setup. The crafted amulet can enable a SoJ slot without
requiring that ring to be already equipped. The rare ring works in the normal rare
slot or as a replacement when that amulet is unavailable; no invented requirement
that a crafted amulet must be absent. Spirit/Nagelring alternatives remain separate.

## Native roll clarification

The guide's functional12+ threshold is not a possible natural12FCR craft roll.
Cached cubemain record88 grants5–10FCR; eligible Apprentice amulet suffix adds10.
Thus legal totals are5–10 or15–20, and the positive item fixture uses15. This role
predicate preserves the guide's functional threshold; full affix/recipe legality
belongs to the existing mechanics/range layer, not an invented continuous roll band.
Earlier generic predicate boundary tests using12 exercise numeric comparison only;
they are not evidence of a naturally spawned12FCR amulet.

Verified local native sources:
- `third-parties/d2data/json/cubemain.json` SHA256 `0b3deb18f4b1605e72a11a8d72e8ce73f1fbd662546d2a875d182be9b70b53e8`
- `third-parties/d2data/json/magicsuffix.json` SHA256 `d7060a8a19c2772747f0cd5d82b1571a774f953789d3ade1f7cac426df97e415`

## Verification and remaining work

Red: two missing configurations. Green:5 initial focused checks. Broader679-test
run had678pass and one stale amulet configuration-count assertion (18→19); updated
it for the new reviewed pattern and all6 affected jewelry/compiler/companion tests
pass. Ring count8→9 likewise reflects the new rare rule; old behavior assertions
remain unchanged. Ruff/format/diff checks pass. All18 saved reports/prices unchanged
in staging; publication results in STATUS.md. Domain fixtures, no new live capture.

Patterns retain separate one-build demand summaries, not named-item votes or numeric
trade prices. Full rare/magic/crafted combination coverage, exact scoped comparisons
and full guide/tier closure remain incomplete. Next another demand/family batch,
then scheduled specialist/leveling work. Evidence tmp/fire-jewelry-*.

Follow-up2026-09-25: The explicitly cited Spirit/Nagelring alternative is now
reviewed in NAGELRING_BATCH.md. Other Spirit jewelry permutations remain unreviewed.
