# Fire Blast magic amulet source conflict — 2026-09-25

Scheduled unresolved tail after magic and rare starter amulet batches. The cached
Fire Blast Starter Amulet states +1Traps/+20allres/25MF on a magic item. Native
Entrapping and Prismatic are both prefixes; Fortune supplies MF as a suffix.
Ordinary magic items allow at most one prefix and one suffix. This is not an
executable legal magic pattern as stated. Do not silently relabel it rare or delete
a property to create a rule. Review estimate: five minutes for the native crosscheck.

Exact source /fire-blast-assassin/variants/0/player/Amulet in wp-a-builds.json and
magicprefix/magicsuffix table hashes are pinned in rules/reviewed_source_issues.json.
The original source value is preserved. An independent review must reconcile the
original planner quality and affixes. This finding says the example is inconsistent,
not that real trap/MF or resistance/MF amulets are valueless.

New maintenance reviewed_source_issues evaluator checks source hash, exact JSON
pointer/value and mechanical-reference hashes. Changed/missing evidence returns
stale_review, retaining the issue for re-review. A matching snapshot returns
reviewed_conflict. The inventory and dossiers preserve these separate from missing
planner/set conflicts. This registry is a review aid, not an automatic compiler
ban on every configuration citing the parent build; partial valid configurations
still need explicit review before promotion. No runtime rules were changed.

Red: missing evaluator module. Green:19 inventory/dossier/issue tests; additional
pointer/value/missing mechanics checks pass. Regenerated inventory and dossiers
contain one reviewed conflict. Runtime generation, price policies and rule counts
unchanged. Saved-report comparison and final checkpoint recorded in STATUS.md.
Evidence tmp/source-issues-*. No online lookup or live probes.

Tail complete. Resume demand/family work; keep this issue visible while reviewing
Fire Blast starter jewelry. Other source conflicts, base desirability, named tiers,
rare/crafted families and exact scoped prices remain incomplete.

## Fire Blast starter amulet source reconciliation — 2026-09-25

Scheduled unresolved tail after Duress base and Meteor magic amulet batches.
Original cached planner pricing/raw/mr/planners/e113x0l4.json, dated
2026-02-17 23:58:03, resolves Starter profile kNG46Gvn neck to item34 Wraith Collar.
It has planner quality4=rare (quality3=magic), with the same +1Traps/20allres/25MF
modifiers. The extraction's Magic label is wrong; the original evidence is retained.
The registry now pins the full item, profile UID/name and neck link to the raw hash.
A separately reviewed rare configuration may use this correction; planner rolls
remain examples, not guide-required minima. No runtime role, tier or price changed.

Red: reconciliation was returned as reviewed_conflict. Green:27 issue/dossier/census/
build extraction tests; lint and diff checks pass. Missing or changed planner evidence,
wrong equipment link and empty reconciliation evidence reopen stale_review.
Inventory and dossiers regenerated with reconciled_source status. Review does not
close executable-rule coverage. Evidence tmp/fire-blast-source-reconciliation-*.

Tail complete. Next demand batches should use reusable combinations and include
this corrected rare amulet only after reviewing guide minima/preferences. Broad base
policies, named tiers, leveling and exact scoped market cohorts remain incomplete.
Runtime generation remains50599b8ea66face195d921e26191a073b4211e723e41d610af4934664acb6af0;
maintenance-only code needs no worker restart or runtime publication.
