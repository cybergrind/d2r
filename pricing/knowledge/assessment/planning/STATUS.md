> **FROZEN 2026-10-03 (user decision).** This document no longer drives work: its gates, queues and
> stopping rules are suspended. The active plan is [PLAN.md](PLAN.md). Kept as technical reference only.

## IK Forge low-value trade rule published; belt-defense RCA found — 2026-10-02

Selected453b58ec15501e09bf9a69e759b99828613d010d180feb2b797f3e3ca7ff1cad,
172 artifacts; previous47912 retained. Original IKForge nowlowtier and candidate,
with concise low-value/no-defense-premium/companion-pieces wording. Upgraded and
unknown variants don't borrow this original-base rule. Only Forge changed in
named_tiers versus tmp/ik-forge-named-tiers-before.json; proof tmp/ik-forge-policy-proof.json.

Three single-item independent sellers selected:
 1daaff53b47fc5faf2698025 total111, UmRune ask;
 c863d5b70766d6bd87bf712f total118, onePerfectAmethyst barter;
 abf7270a197be1b31f11c25b total115, fourRandomGems barter.
Rejected b30e283ee57748e10533eff1:amount4/unitambiguous. Initial rule construction
used that row and correctly failed scoped validation; replaced with the explicit
single-item row. No quantity division, gem conversion, sale guarantee or defense
premium. Source3-pieceIK demand from Berserk and DoubleThrow glove slots retained
in pricing/data/appraisal-ik-forge-trade-research-2026-10-02.json.

Validation:35policy/barter/original-set tests pass;13stagednativeForge cases pass;
128selected Forge/Shako/WarTraveler/JMOD cases pass60.08s.20savedreplays unchanged
(extraction,prices,text):tmp/ik-forge-selected-replay-proof.json. Lint/diff checks
pass. Bank inventory30993cases,4058targets,304missingtargets. All handles terminal.
No collection, worker restart, staging or commit. Runtime rule data is published;
formal Forge review integration still pending. Prior review receipts are stale
for the newgeneration/source fingerprint; don't rerunfullbank aftereachitem.

IMPORTANT next: IKDetail defense89 is NOT necessarily invalid. Initial mental
41..52base+36flat arithmetic missed dormant ac%100partial property. Native D2MOO
ITEMMODS_AssignProperty loops partial properties (ItemMods.cpp2407..2425);
ITEMMODS_PropertyFunc02 calls sub_6FD92CF0 unconditionally for items (2921..2936);
armorpercent setsbase max+1 (888..909), even though partialstatlistisn'tactiveyet.
Thus original IKDetail53+36=89. Forge onlyflatpartialac120 so108..118 remainsvalid.
Upgrade rerolls base, so don't transfer originalmax+1 to upgraded totals.

Saved source-pinned RCA:
 pricing/data/appraisal-ik-detail-defense-rca-2026-10-02.json.
Native setdefinitions with conditionalac%: IKDetail, IKSoulCage, MilabregaOrb,
MilabregaRobe. Audit compiler/report/comparisonrange handling before fixing;
shared mechanical coverage doesn't require generic leveling build expansion.
Source exact paths in RCA; local D2MOO already inspected. CodeGraph didn't locate
third-party symbols; used targeted rg --no-ignore afterCodeGraph attempt.

IKDetail research lookup tmp/ik-detail-current-lookup.json; rows
 tmp/ik-detail-roll-rows.json. Originalexplicitbase3sellers:
 5a644f59077b2f8c4615f195 total89 (and mislabeled39989), Ist1;
 c205a335f0621d16db9caf13 missingdefense, Lem/Fal/Hel askingalternatives;
 d968f466bab69c246dd3afa9 missingdefense, Hel/PerfectAmethyst alternatives.
Allsingleitem. Do not reject89based on oldformula; do not silently reinterpret399
as bonus/total for numerical comparisons. Upgraded knownbase rows are two sellers
only (three rows; two same seller). Missingbase/399only examples remain uncertain.
Review native conditionaldefense mechanics first, then reconsider belt qualification.

Goal remains active; last fullaggregate110676pendingstale. No completion claim.

## Shako formal underlying-item review closed — 2026-10-02

Selected runtime unchanged47912d1b6933757632329d5c16afc7f87361d5f366f92ef15824ef40abd5707e.
Added maintenance/trade_shako.py and scope native_unique_underlying_shako. Context
loads/validates shako_trade.json inside the selected snapshot and binds it to the
named policy fingerprint; baseline tiers alone cannot satisfy this review.
Native fixed benefits, defense98..141, socket/capture boundaries and rendered
reason/color are checked independently of the runtime result.

Shako bank10->35cases: empty0/1 sockets, missing/low/max/high defense, filled and
unknown/null inserts with higher total defense, unidentified/ethereal/unknown
facts, contradictory zero-filled and incomplete captures. Formal red caught the
old missing boundaries.35initial selected cases pass28.98s.34Shako/WarTraveler
maintenance regressions pass12.51s; lint/diff checks pass.

Fresh shared receipt pricing/data/report-receipts/named-equipment-trade.json:
101selected Shako+WarTraveler cases pass51.52s. Full39-row registry validation
accepts exactly these2current reviews; older37receipts stale after source changes.
Proof:tmp/named-equipment-trade-acceptance.json. Registry rows37WarTraveler and
38HarlequinCrest both point to the shared receipt. No whole-goal completion claim.
Bank inventory30980cases,4058requiredtargets,304targets missingcases.
All work/probe/test handles for this step are terminal. No runtime publication
needed for maintenance-only changes; no live collection/restart/staging/commit.

Next research:
-Vipermagi lookup tmp/vipermagi-roll-lookup.json;29scoped dated single-item rows,
 15sellers,0explicitlyempty. One LightningFacet-filled row only. Um helm/armor
 +15allres verified in nativegems:20intrinsic+15Um=35displayed. Unknown contents
 cannot establish35native premium. ED425values800/998 conflict with native120;
 Normal-tier selectors conflict with this exceptional unique. Preserve conflicts.
 Research pricing/data/appraisal-vipermagi-roll-research-2026-10-02.json. Existing
 qualitative policy explicitly requires empty contents, so no observed false
 perfect-roll promotion to fix. Native35trade qualification remains pending.
-Laying of Hands KB lookup tmp/laying-hands-roll-lookup.json; no market records,
 including case-insensitive name check. Don't treat missing data as worthless.
-Unreviewed clean named census tmp/unreviewed-clean-named-census.json finds only
 IKForge5rows/5sellers and IKDetail5rows/4sellers with known variants, numeric asks.
 These mix native/upgraded and some mislabeled399defense; don't infer cutoffs.
 IKForge fresh lookup tmp/ik-forge-current-lookup.json. Additional original rows
 have explicit barter asking terms (ask_istNone), potentially useful under the
 new reviewed barter mechanism. Inspect their actual prices before dismissing.
 Original xhg rows: fdaacc5a54b4e339ecda524c total115 ask1;
 1daaff53b47fc5faf2698025 total111 ask0.674;
 abf7270a197be1b31f11c25b total115 noIst;
 c863d5b70766d6bd87bf712f total118 noIst;
 b30e283ee57748e10533eff1 noTotal/noIst. Don't infer no price from no conversion.
 Guide demand exists: berserk-barbarian/slots/Gloves/2 and
 double-throw-barbarian-guide/slots/Gloves/4 explicitly3-pieceIK; corresponding
 qualified roles already reviewed. Zeal partial-set gloves/belt/boots roles also
 exist with exact source spans. Keep standalone item demand separate from having
 required companion pieces; fixed benefits may justify no arbitrary defensecutoff.

Continue all-item roll review and completion contract. Last full aggregate110676
pending remains stale; current scoped work is not a full gate refresh.

## War Traveler review and executed boundary proof — 2026-10-02

Runtime generation remains47912d1b6933757632329d5c16afc7f87361d5f366f92ef15824ef40abd5707e.
Added maintenance/trade_war_traveler.py and trade_war_traveler_evidence.py;
registered native_unique_mf_boots in trade_reviews.py. Native specification guards
identity/base/socket mechanics, material MF/ED/thorns ranges, stat scaling and the
50MF threshold. Review rejects changed semantics, omitted cases and wrong colors.

Expanded native WarTraveler bank10->66cases: original/upgraded roll endpoints,
49/50MF boundary, mixed secondary rolls, each missing/illegal material value,
unidentified/ethereal/unknownethereal/socket/unknowncontents/filled variants.
All66selected cases pass37.81s with current report receipt:
 pricing/data/report-receipts/war-traveler-trade.json.
54new/related maintenance regressions pass36.78s. Ruff/diff checks pass.
Bank inventory30955cases;4058requiredtargets,304targets missingcases.

Source census:3complete perfect-MF rows/3sellers (one explicit barter),0proved
lower-MF cohorts,55unproven rows/28sellers (one barter). Unproven is not worthless.
Census:pricing/data/appraisal-war-traveler-trade-census-2026-10-02.json.
Registered38th formal named trade review in rules/trade_qualification_reviews.json.
Current selected-generation receipt is accepted for WarTraveler; acceptance proof
 tmp/war-traveler-review-acceptance.json. Older receipts are invalidated by changed
verification sources; do not present all38 as currently attested. No full aggregate
refresh or all-bank run at this isolated edit; goal remains unfinished.

Next: integrate separate Shako underlying-item handler into formal named trade
review coverage with native defense/socket/capture/report boundaries. Its runtime
rule and10bankcases are already published and passing; named_tiers does not own
that rule, so load_context must bind the separate published rule explicitly rather
than pretending baseline tier rules establish trade qualification. Then continue
remaining item-by-item valuable roll reviews. No live collection/restart/commit.

## War Traveler perfect-MF trade candidate published — 2026-10-02

Selected47912d1b6933757632329d5c16afc7f87361d5f366f92ef15824ef40abd5707e,
172 artifacts; previous f76a75 retained. Only War Traveler changed in named_tiers
relative to that generation (tmp/war-traveler-policy-proof.json). Verified
nonethereal50MF is a candidate across legal ED150..190 and thorns5..10; no
perfect-ED requirement. Lower MF remains unresolved, not use-only/worthless.
Original and upgraded bases retain their identities; numeric pricing unchanged.

Native defense proves nonethereal for4scoped rows;3include all material rolls.
Two have Ist-convertible asks; the third explicitly requests3SmallCharms with
20life/20AR/3maxdamage each. It has no Ist conversion. New trade_barter validator
allows explicitly reviewed barter IDs for candidate interest only, not premium
or numeric valuation. Source payload and full market hash retained. Fourth row
missing ED/thorns remains context only. Tests reject absent/zero/bool quantities,
missing item identity and undeclared/premium use of barter evidence.

Mechanics: war_traveler_ethereal.py uses pinned native tables, original48baseAC
before ED; upgraded59..68. Legal total must also be below conservative ethereal
minimum. Unknown flags never default false;399never treated as1855.
Research:pricing/data/appraisal-war-traveler-trade-research-2026-10-02.json.

Validation:13inference cases red/green; trade/barter tests red/green;138combined
policy/mechanics regressions pass106.71s;59report/Shako/Arachnid regressions pass.
10staged WarTraveler cases pass;34selected WarTraveler/Shako/JMOD cases pass29.30s.
20saved replays unchanged vsShako publication (extraction,price,text):
 tmp/war-traveler-selected-replay-proof.json. Ruff and git diff --check pass.
Bank inventory regenerated30899cases,4058requiredtargets,304targets missingcases.
All recorded publication, selected bank, replay and coverage jobs are terminal0.
No collection, worker restart, staging or commit. Python requires worker restart.

Continue item-by-item roll work and completion-contract gates. Formal named trade
review registry/report receipts still need Shako/WarTraveler review integration;
scoped runtime success is not full goal completion. Last full aggregate110676
pending remains stale; don't claim a current total or rerun the whole bank after
every isolated edit. Goal stays active.

## Shako ordinary trade demand published — 2026-10-02

Selected f76a75ff4c61b5f3cc37d2cb049ed2ae5126febdf3dfce9ea734bf1581018731
(172 artifacts), previous be08b02 retained. Harlequin Crest now has a separate
underlying-item trade candidate outcome for verified nonethereal captures. Legal
98..141 empty defense rolls qualify; perfect defense is not automatically premium.
Filled/unknown inserts are valued separately. Ethereal/unknown identity/illegal
socket count/incomplete capture stay unresolved. No numeric pricing change.

Source review:29 explicit-total-defense asks/11 sellers prove nonethereal by native
bounds; five independent low-defense sellers selected, with exact build slots.
Unknown contents stay unknown, never empty. New rule shako_trade.json, mechanics
shako_shell.py; shared native hashes moved to socket_evidence.py (JMOD unchanged).
Research:pricing/data/appraisal-shako-trade-research-2026-10-02.json.

Red8failed/12passed before implementation;114 mechanics/policy regressions pass;
155 report/fixed-jewelry/coverage regressions pass.10 staged Shako cases and24
selected Shako/JMOD cases pass.20 saved replays preserve extraction/prices; only
Shako text changes (candidate line). Proof:tmp/shako-selected-replay-proof.json.
No all-bank final receipt refreshed. Aggregate completion remains incomplete;
last completed aggregate110676pending is stale after scoped changes.
Python changes require worker restart; no live restart/test, collection, staging
or commit performed.

Next: War Traveler explicit defense has two original and two upgraded nonethereal
proof candidates, all50MF. Three include ED and reflected-damage rolls. Check
native upgrade bounds before accepting evidence across variants; never convert
omitted ethereal to false or perfect-MF interest into a price for all rolls.

## Native blocking corrected across 30 magic-shield roles — 2026-10-02

Selected be08b02f46f4920c17334a9b665b2530c252022b1de429fa1abec1b9271e517a
(171 artifacts), previous b5b2f2 retained. All jobs from this repair are terminal.
Red/green reproduced insufficient native blocking accepted by Monarch and Sacred
Targe rules. Thresholds now include native base blocking: Monarch42=22+20,
Sacred Targe50=30+20. Thirty empty/filled Deflecting roles corrected; only must
predicates and review notes changed in profiles. Existing empty JMOD bank fixtures
already used42; filled fixtures and old unit fixtures were corrected. Eleven new
negative bank cases cover insufficient bonuses. No market threshold/price change.

Updated23+7 stat/guide reviews after verifying old pins and unchanged sources,
build/class/variant/slot/socket/payload conditions. Refreshed dependent source,
table, scope and collection pins only for these reviewed roles; proof files:
 tmp/jmod-blocking-change-proof.json, tmp/jmod-blocking-extra-proof.json,
 tmp/deflecting-review-pins-proof.json. Backup directories retain original inputs.
Mutation scripts partially ran before their checked finish scripts completed;
do NOT rerun tmp/fix-jmod-native-block.py or tmp/fix-other-deflecting-block.py.

Rebuilt profiles2695, guide inventory62891 occurrences/1951 configurations and
review dossiers2548 identities. Derived inventory had caused expected stale-data
regression failures; rebuilt before recheck. Final evidence:
-328 staged cases pass175.22s;328 selected cases pass132.46s.
-46scope regressions pass9.94s;52collection/table tests pass299.93s.
-Initial73JMOD/mechanics regressions pass; other related tests passed before
 the stale-scope recheck. Ruff and git diff --check pass.
-20saved replays preserve extraction/price/text; tmp/deflecting-selected-replay-proof.json.
-Research/RCA: pricing/data/appraisal-deflecting-blocking-rca-2026-10-02.json.

Bank inventory regenerated30879cases. These are affected-case executions, not a
fresh all-bank final receipt. Last complete aggregate remains WP-B110676pending;
full objective still active. No collection, worker restart, staging or commit.

Next offline roll research: Archon Plate magic has24dated scoped single-item asks
from7sellers, but22unknown contents and2filled, zero explicitlyempty. Concrete
counterexample:94total life can come from2PerfectRubies(38each)+18life Jewel of Hope,
with no Whale suffix. Thus unknown payload total-life cannot establish intrinsic
Whale81..100 or an empty-base price. Source-pinned note:
 pricing/data/appraisal-archon-whale-roll-research-2026-10-02.json.
Rare ethereal Matriarchal Javelin census is tmp/matriarchal-javelin-rare-rows.json:
23rows/9sellers, but only3listed IAS rows from2sellers (10/20IAS); omitted IAS is
unknown, not zero. No new rare-javelin cutoff inferred. Continue item-specific
roll qualification and the full completion contract; no blocker/complete claim.

## JMOD trade candidate published — 2026-10-02

Selected generation b5b2f259d637f18cc393cb18bf04e5a1cdb208b8489ef4b1cbf94514d9b3b72f
(171 artifacts). Previous 704528 retained. New Python modules/report behavior need
a worker restart for an already-running older process; no host restart or live
verification was performed. No fresh market collection, staging or commit.

The magic trade handler now recognizes a fully captured, identified nonethereal
four-socket Monarch with the native Deflecting bonus (20 block / 30 FBR). Native
blocking TOTAL is 42, not 20: use the existing base-block projection. Empty,
filled and unknown contents can retain the shell trade claim; payload valuation
stays separate. Report has a blue Trade: candidate line, no premium-defense claim
or invented empty-base price. Other/uncertain variants do not inherit this rule.

Evidence: four independent dated SC/NL/PC/RotW listings, from the 12-row mechanical
proof, plus hash-bound wp-a-blues guide demand. Entire reviewed native catalogs
are pinned; source/variant/scope/quantity/date/seller/definition failures reject
publication or the qualification. Sources join runtime snapshot/publication.
New files policies/magic_trade.py, rules/magic_trade.json; shell evidence module
moved from maintenance/jmod_shell_evidence.py to mechanics/jmod_shell.py.

Red/green: initial missing trade claim, then full capture exposed the native
base-block total; report-color red exposed a missing-tier fallback to white.
14 selected published native item scenarios now pass (19.83s), including color,
base defense endpoints, class independence, payload uncertainty, wrong variants,
bonus-as-total and incomplete captures. 186 policy/mechanics/coverage/publication
regressions pass (37.06s); 39 report regressions pass (17.50s). Ruff/diff checks pass.
20 saved replays preserve extraction, price_estimate and text; proof is
 tmp/jmod-selected-replay-proof.json. Research proof is
 pricing/data/appraisal-jmod-shell-evidence-2026-10-02.json.

Bank inventory now has a real trade:magic:jmod-shell target with positive,
negative and unknown scenarios; no JMOD orphan. This is inventory coverage, not
an all-bank execution receipt. The old 1988-case WP-B receipt is stale for this
new code/generation. Do not rerun that expensive bank after every isolated change;
refresh final aggregate verification at the next substantive closure checkpoint.
Last completed aggregate remains WP-B 110676 remaining, complete=false; the all-item
goal is active. No completion or new all-item coverage claim is made here.

Next useful review: existing JMOD build-role/annotation fixtures often supply raw
blocking 20 and incomplete captures; audit them against native total 42. The new
trade tests intentionally use real native totals and complete capture. Also
continue roll-sensitive magic/rare/base and named coverage from the full contract;
filled listing amounts remain unsuitable as an empty-base quote.

## JMOD shell evidence check implemented; runtime qualification pending — 2026-10-02

WP-B finalizer 52278 completed zero: 37 reviews accepted, matrix/scope/completion
rebuilt for 70452815826ecfd4f097d6ab04b988e5e61cd8dc8811723677ee0ab454f87a1e.
Scope verified; complete=false, remaining_tasks=110676. No live jobs remain.
The new maintenance code/tests below invalidate that prior executable-input
receipt; do not treat it as current after these edits.

Added maintenance/jmod_shell_evidence.py: a narrow non-mutating proof for magic
Monarch, four sockets, exactly 20 block / 30 FBR, explicit total defense 133..148.
It binds eight complete reviewed native catalogs, rejects conflicting flags and
ambiguous defense, and preserves socket contents. Result is recoverable-shell
only with price_eligible=false. It does not change runtime trade qualification,
market normalization, current-item pricing, or published generation.

Red reproduced missing module; 35 new tests plus 40 existing market-ethereal
regressions pass (75 in 0.62s). New tests include every native catalog changing,
base/quality/ethereal/socket/stat conflicts, unknown and ambiguous defense,
endpoints, and preservation of source data and unknown contents. Ruff passes.
Proof output pricing/data/appraisal-jmod-shell-evidence-2026-10-02.json: 12 dated
SC/NL/PC/RotW single-item asking records, four independent sellers. This proves
mechanical shell identity, not an empty-shell price or confirmed sale. Local
D2MOO SUnitNpc.cpp socket quest corroborates magic quest maximum two sockets;
current cube recipes only grant normal shields random sockets, not magic ones.

Next: design and test the magic-family trade rule using this shell evidence and
reviewed guide demand, keeping filled payload valuation separate. Do not reuse
filled listing amounts as an empty-base price. Continue full goal; no new live
collection, host restart, staging or commit.

## WP-B published bank passed; base qualification research — 2026-10-02

All 1,988 selected published item-bank cases passed in 779.15s. Original bank
53206 and prepare 49007 are terminal zero. Generation is 70452815826ecfd4f097d6ab04b988e5e61cd8dc8811723677ee0ab454f87a1e;
receipt exitstatus=0 and sources_unchanged=true. Finalizer 52278 has accepted all
37 named reviews and is rebuilding matrix/scope/completion; inspect its original
handle and tmp/wpb-finish.log before any executable input changes.

New offline research only (no runtime trade or price thresholds changed):
- pricing/data/appraisal-jmod-roll-research-2026-10-02.json: fixed native affixes,
  socket-clearing recipe, dated market census, and unresolved payload/ethereal
  proof requirements. Four sockets/30 FBR/20 increased block is a variant gate,
  not a percentile roll cutoff. Never infer total defense from property 399.
- pricing/data/appraisal-superior-base-roll-research-2026-10-02.json: explicit
  superior ethereal zero-socket three-seller groups for Great Poleaxe, Thresher
  and Wire Fleece. Sample minimum ED is not a demonstrated sellability cutoff.
  Intended runeword socket feasibility must precede a build-base claim.

Next promising implementation: prove recoverable JMOD shell eligibility separately
from inserted-payload price. Native Jeweler's is four sockets; Deflecting is
20 increased block/30 FBR. Eld adds seven block and Shael twenty FBR. Exactly
30 FBR cannot be synthesized from the other native shield suffix (15) by Shaels,
but validate complete socketable/affix catalogs and inheritance before runtime
inference. Total-defense 133..148 is a possible nonethereal proof only after
binding all nonnegative defense contributions; no such inference was implemented.
All-item goal remains active; no fresh collection, host restart, staging or commit.

## WP-B recovered-date generation published; full report receipt running — 2026-10-02

Selected70452815826ecfd4f097d6ab04b988e5e61cd8dc8811723677ee0ab454f87a1e,
169artifacts. Previousdd4c11 retained.7777recovered dates nowpublished; no freshfetch.
44trade owners changed onlymarket_snapshot; allcitednormalizedrowsunchanged.
37registered policy fingerprints updated after matchingpreviousfingerprints.
Seven partialcensuses (Mara,Nagel,Opalvein,Trek,Titan,Arachnid,Torch) reproduce old
fingerprints after replacing onlysnapshot; no changed thresholds/cohorts. Proof
 tmp/wpb-reviewed-market-rebind-proof.json. Script tmp/wpb-rebind-reviewed-market.py
ALREADYRAN; backupguardpreventsrepeat.76trade policy/maintenance tests passed134.88s.

Rebuilt profiles2695, basecoverage,runewords99 (67demand/98scopedlistings),watch/index.
PublicationfirstrejectedstaleEschuta baseline source because watchinputhash changed.
All228watch rows and allothernon-inputfields provedidentical. Six exact source
locators in named_baselines.json were refreshed; proof tmp/wpb-watch-source-rebind-proof.json.
Finalpublication68112terminal0. No blindlyrebound evidence or changed baseline tiers.
79date/import and21publicationtests alreadypassed in priorpass. No hostrestart.

All20selectedsavedreplays preserve extraction/price_estimate/text vspriorgeneration.
47973terminal0; tmp/wpb-selected-replay-proof.json. The new Python provenance
validator mayrequire workerrestart for an already-running oldPython process;
no livehostverification claimed. Selectedpublication itself isvalid.

LIVE53206: registered1969+Kingslayer19=1988reportcases, tmp/wpb-published-bank.log.
LIVE49007: sevenauditprepare, tmp/wpb-prepare.log, usesNEWselectedreplay.
LIVE52278: tmp/finish-wpb-when-ready.py -> tmp/wpb-finish.log; waits forNEWgeneration
ANDcurrentinputreceipt, then37reviewacceptance/matrix/scope/completion.
Freeze executable/test/rule inputs untilterminal. Re-polloriginalhandles, never
restartonobservationtimeout. Latestcompletedaggregate remainsKingslayer110676;
newgenerationcompletionnotyetcertified. Goalactive, notcomplete. No stage/commit.
Next use recovered WP-B rows for base/magic/rare roll-sensitive evidence review,
with originalvariant uncertainties preserved. Collectiondates are not new prices.

## Publication regression recheck passed after index rebuild — 2026-10-02

exec95424terminal0: both previously failing publication repository tests passed
(tmp/wpb-publication-recheck.log). Earlier other19 publication tests passed;
79date/import regressions pass. Index rebuild32368terminal0. All jobs from this
turn are terminal. WP-B7777date recovery is applied to working data and index,
but selected runtime remainsdd4c11... and named snapshot pins/derived artifacts,
publication/replay/receipts/completion still require follow-through. Do not claim
published prices or fullgoalcomplete. Application proof and source backups below.

## WP-B date recovery implemented and applied; publication unfinished — 2026-10-02

Kingslayer pass completed first:1988passed764.11s;23274/67844terminal0,37reviews
accepted, matrix/scope/completion successful. Scopeverified,completefalse,
110676required tasks. No jobs from that pass remain. New edits invalidate its
shared execution inputs; refresh receipts only after this maintenance stabilizes.

New production documented_base_dates.py validates WP-B raw/catalog/counts/version
distributions/log/day/ID-map hashes separately from existing WP-H validation.
documented_cache_dates.py dispatches and bundles WP-B provenance only for those
explicit source records.24 new integration cases (canonicalred confirmed); all45
new+WP-H tests passed, broader79date/import/reconciliation regressions passed0.44s.
Lint/format/diffcheck passed. Registered45 approved files in existing registry
(now68records), all source validationpassed. Backup tmp/wpb-date-before/.

Dry and --write date_recovery each terminal0:41135observations,7777date-only
changes;dated22276->30053. All7777formerlyundatedWP-B observations nowcarry documented
2026-09-18, whileprices/facets/scope unchanged. Independent full zipped comparison
and verify_policy_sources passed. Proof tmp/wpb-date-application-proof.json:
oldmarket57ad30f409ef5643fd48abc09095f125c48d4a831f1b138583f3ec336674b210,
newmarketf3e81392e606f45845bed7ba20fc370cde740c9b8e9181a120e1ae2fb1c5de9a.
Collectionproof pricing/data/appraisal-collection-date-recovery.json. No livefetch.

Publication tests19passed2failed67.49s: both failures are actual repository-index
sourcehash mismatch for changed appraisal-market.jsonl (not date-validator failure).
Index rebuild32368terminal0 (tmp/wpb-index-rebuild.log). Two failed publication
repository tests are now rerunning: exec95424, tmp/wpb-publication-recheck.log. Selected generation STILLdd4c11...; no new
publication or workerrestart. Need rebuilddependent evidence/index, revalidate
named market-snapshot pins (all referenced trade rows independentlyunchanged),
registry policyfingerprints if changed, compile/publish/replay, fullrequiredreceipt
andmatrix/scope/completion. Do not blindly rebind source hashes or claim completion.
New dated WP-B evidence should then feed separate base/magic/rare roll reviews;
date recovery alone is not a sellability threshold or completed all-item assessment.

## WP-B validator draft passes all45 real caches — 2026-10-02

Isolated implementation at tmp/documented_base_dates_draft.py now validates all45
real raw caches against pinned source/log/ID-map, collection day, catalog identity,
counts and version distributions. Rejects conflicting duplicate listing records;
identical Circlet duplicate passes while retaining historical raw count7778.
Creates reviewed registry PROPOSAL only: tmp/wpb-date-registry-proposal.json.
No production module/registry/import was changed during Kingslayer input freeze.
Draft16 integration tests remain tmp/test_documented_base_dates_draft.py; one
canonical red confirmed existing WPH-only registry rejection. Need install after
original jobs terminal, wire dispatch/parse/runtime provenance, run all draft
negative integration tests and existing WP-H/date/import/publication regressions.
Use source path as explicit adapter discriminator, not generic filename dates.
Potential follow-up strictness: preserve _read path/hash checks and typed count
checks; add raw/source/log/catalog-map tamper and conflicting-duplicate tests.

Kingslayer23274 still live at90%;67844finalizer pending receipt. Original prep5673
terminal0. Last authoritative completed count isFrost110676; do not overwrite it
with expectations. No runtime/network/publication/worker/stage/commit changes.

## WP-B recovery integration test reproduces missing support — 2026-10-02

While the original Kingslayer bank remains live, drafted16 integration scenarios
at tmp/test_documented_base_dates_draft.py without changing executable inputs.
Canonical positive test run red:1failed15deselected0.43s, log
 tmp/wpb-date-draft-red.log. Exact failure is documented_cache_dates.parse_reviews
rejecting non-WP-H path; not an import/setup failure. Draft covers actual ask
preservation/unknown ethereal, catalog/IDs/count/distribution/date/log/query/pointer
failures, historical unset-version scope remaining unknown, and identical raw
duplicate deduplication. Run via uv run --offline python -m pytest.
These drafts are not installed or implemented. Wait for existing23274/67844 to
finish, then add separate WP-B validator and copy/refine tests into tests/pricing/
knowledge/test_documented_base_dates.py. Do not make arbitrary paths dateable or
replace strict scope with WP-B's legacy unset-accepted filter.

## WP-B date provenance verified while Kingslayer tests run — 2026-10-02

Concrete offline progress: appraisal-wpb-date-recovery-research-2026-10-02.json
pins45 raw caches, WP-B JSON/log, IDs file and bucket script. All7778 raw rows
match documented catalogs, counts and game-version distributions; no updates
after documented2026-09-18 collection. Circlet has one identical repeated listing
1002446469140, already deduplicated in normalized market. All7777 normalized
observations are currently undated;4622 pass current strict SC/NL/PC/RotW scope.
This is a verified recovery lead, NOT an imported date or price change.
Research script: tmp/audit-wpb-documented-dates.py. Next implementation steps are
in the artifact. Existing documented_cache_dates.py only supports WP-H; use a
separate WP-B validator and preserve old behavior. Do not import legacy scope
("unset" versions were kept) or bucket prices. No global date-from-filename rule.

Crown follow-up artifact adds exact two-Ber source review:413 is labeled flat DR,
1865 percent DR, and one399 field contains399 (outside native flat100–150).
Cannot promote these three filled sellers to a clean intrinsic/premium cohort.
Ber helmet effect8% verified in gems.json. Cached valuable-items guide primarily
recommends Crown for Hardcore/early Ladder, not independent SC/NL demand proof.

Kingslayer bank23274 confirmed live this turn; input freeze still applies.
Prep5673 completed all seven audit steps. Finalizer67844 waits on current-input
receipt then37 reviews/matrix/scope/completion. Last terminal count stillFrost
110676 remaining. Check original handles; do not restart on an observation timeout.
No runtime/data import/publication/network/restart/staging/commit this turn.

## Kingslayer Smite report coverage added; broad receipt refresh running — 2026-10-02

Previous Frost pass is complete and verified (progress). Selected runtime remains
 dd4c11f4ae81c9fceaf85a2a4306b35fcd8c160af4dbdec2ff39fe3badd10425.
Added19 native cases in cases/smite_kingslayer.py, registered once. Source is
wp-a-builds.json:/smite-paladin/slots/Weapon/3 (Kingslayer Phase Blade), exact
native recipe MalUmGulFal and rune effects. All three base qualities; min/max
230–270ED have identical Smite utility. IAS30/CB33/OW50 desirable, Strength10
supporting; no ED/AR/target-defense/Vengeance/gold stat credit. Includes wrong
base/class, missing/reversed runes, unidentified, unknown class/ethereal/sockets,
and uncaptured IAS without fabricated annotation. Native rune contributions
include Um25OW plus recipe25OW. Partial captures remain partial.

19passed/30835deselected in19.58s; tmp/smite-kingslayer-bank.log (56673terminal0).
No runtime/rule changes were needed; this is required missing valuable-use bank
coverage, not a new sellability or price claim. Ruff format/check and diffcheck pass.
New test inputs invalidate older shared execution receipts, so refreshing the
registered1969 cases plus these19 together: exec23274 live,1988 cases, log
 tmp/smite-kingslayer-published-bank.log; script tmp/run-smite-kingslayer-published-bank.py.
Seven dependent audits exec5673 live, tmp/smite-kingslayer-prepare.log.
Finalizer exec67844 (tmp/finish-smite-kingslayer-when-ready.py) waits for selected generation
AND current input hashes, then37 review acceptance/matrix/scope/completion.
Freeze executable/test/rule inputs until all jobs finish. Do not restart on timeout.
No publication, live collection, worker restart, staging or commit. Goal active;
last completed aggregate110676remaining (Frost), not final completion.

## Frost verification and coverage refresh complete — 2026-10-02

Selected generation: dd4c11f4ae81c9fceaf85a2a4306b35fcd8c160af4dbdec2ff39fe3badd10425.
Full registered report selection: 1969 passed in 761.41s. Exec72496 terminal0.
Receipt independently checked: selected generation, exitstatus0,
sources_unchanged=true,1969 passing case IDs. Finalizer8445 terminal0 accepted
all37 registered reviews and refreshed matrix/scope/completion. Seven preparatory
audits also complete. No running jobs remain from this pass. Executable input
freeze lifted. Proof: tmp/frost-receipt-proof.json; logs tmp/frost-finish.log and
 tmp/frost-completion.log. Scope verified; complete=false. Counts:2548identities,
62891occurrences,3527reviewed,15229excluded,8770coverage rows,110676remaining
required tasks,8312trade-qualification gaps. These are obligations, not item counts.

Additional item-by-item research: Crown of Ages43 eligible dated single-item asks
from31 sellers,33 unknown socket contents and10 filled; zero explicit empty.
Ber-filled examples mix native/total DR conventions; several ED properties
contradict fixed native50%. No new trade threshold or numerical price inferred.
Artifact: pricing/data/appraisal-crown-ages-roll-research-2026-10-02.json.
ROLL_VALUE_REVIEW.md documents the gap and correct full-registry receipt selection.
Protector's Stone already reviewed; do not duplicate it. Trang-Oul's Wing lookup
has zero cached market observations; no qualification added.

Next: continue valuable-item reviews using audited evidence gaps. The prior named
inventory's only unregistered >=3 explicit-variant-seller leads are Crown of Ages,
Immortal King's Forge and Detail; all have documented cohort limitations. Do not
repeat their census, fabricate sample-minimum thresholds, or treat unknown demand
as worthless. Broader family/configuration work remains authorized. Fresh live
collection request is still unanswered. No worker restart, live collection,
staging or commit. Wider goal remains active and unfinished.

## Frost published; full selected-generation verification running — 2026-10-02

Supersedes priorpendingproposal/runningDwarf notes. Dwarf checkpointcomplete:
36reviews,1913passed738.62s, lastcompletedcounts110677remaining/completefalse.
Currentturnprogress: finalizedevidence-backedFrostpolicy,56nativecases,published.

Selected dd4c11f4ae81c9fceaf85a2a4306b35fcd8c160af4dbdec2ff39fe3badd10425 (121artifacts).
Frost ordinarycandidate over all legal5..10coldDamage/Pierce,XP3..5,MF15..35,GF25..50;
all5required,knownnoneth0emptysockets. No premium from1joint-perfectseller or
secondarymaxima. Demandbasisnowreviewed: cachednew-items guide explicitly says
ColossalJewel family improvesFacets,1percharacter; nativecorefloor5/5. Guide
modified2026-02-19, path/hash/excerpt/date in demand_source and researchartifact.
ThreecompleteSC/NL/PC/RotW mixedrolls supportordinarydemand, notnumericprice.
Minimumuse isindependentlysupported, notcutoffinferredfromsampleminimum8/9.
Rootparentvariant narrowedtolegalnative noneth0empty; invalidetherealnotatierclaim.

Red5canonicaltests; green6focused2.44s,65policy/source139.89s,
278relatedFrost/Colossalstagedappraisals106.77s; lint/format/diffgreen.
All20savedcaptures unchangedextraction/price/text vsDwarf; proof
 tmp/frost-selected-replay-proof.json. Registered37threview,1969requiredcases.
LIVE exec72496: tmp/run-facet-published-bank.py -> tmp/frost-published-bank.log.
LIVE exec68127: sevenauditprepare -> tmp/frost-prepare.log.
Queuedfinalizer tmp/finish-frost-when-receipt-ready.py -> tmp/frost-finish.log:
waitsfornewgeneration ANDcurrentexecutableinput receipt, thenrequires0/unchanged,
runs tmp/frost-finish.py expecting37acceptedreviews andmatrix/scope/completion.
Freeze executable/test/rule inputs untilterminal. Neverrestartonobservationtimeout.
No commit/stage, no workerrestart, no newlivecollection.

Additionalread-onlylead tmp/archon-staff-trade-research.json:4normaleth0socket
rows butONLY2sellers; differentSorceressstaffmods. Do notinfergeneralbasevalue
fromfourrows. PriorGriffon/Shako/WarTraveler andIK gaps documented; broadergoal
stillunfinished. Next explicitreadyaction verifyFrostreceipt/finalizer, then
continueitem-by-item supportedroll/use research withoutinventingmarketthresholds.

## Frost ordinary trade refinement implemented; staged bank green — 2026-10-02

Dwarf checkpointfullycomplete:finalizer35257terminal0,36reviewsaccepted,
1913passed738.62s, completion110677remaining/completefalse. Goalactive.

New semantic evidence resolves earlierFrostproposalhesitation:
pricing/raw/mr/items__new-items-in-reign-of-the-warlock.html, Colossal Ancient
Jewels introduction explicitly calls thisfamily facetupgrades with1percharacter
limit. Articlemodified2026-02-19 (actualdateModified); hash/excerpt/path/date
pinned in new trade.demand_source and researchartifact. Nativefloor5coldDamage/
5pierce plusMF15+ supports reviewedBlizzardcoldsocketordinaryutility; scoped
complete8/9,9/8,10/10asks from3sellerssupportordinarynameditemdemand. Only1complete
10/10seller, so nopremium. Historical5/7/partial6/9arecontextonly, notprices.

Applied Frostpolicy to named_tiers.json; legalnoneth/0emptyvariant required,
all5variable331/335/85/80/79known/bounded, allvalidrollscandidate, no secondary
perfectpromotion. New canonicaltest_frost_trade.py:5redthen6green2.44s (includes
actualguidehash/date/one-per-character sourcebinding). New56-case frost_trade.py
bankregistered; all278relatedfrost/colossalstagedappraisals passed106.77s. Native
scalarboundaryproof passedall56. Source-policy suite exec77379 stillRUNNING in
tmp/frost-policy-green.log; awaitterminal and investigatefailure ifany. Lint/diffgreen.
Researchartifact pricing/data/appraisal-frost-roll-review-2026-10-02.json.

NOT YET PUBLISHED: selectedstillDwarf6159fc0d4e556e5d22e018ffa755234225a396debb6fa1800636f17bf5539f91.
After source-suitegreen: publish, run tmp/register-frost-review.py (adds37th/56cases),
replay20captures to tmp/frost-selected-replay.json, compare extraction/price/text,
run tmp/frost-prepare.py audits. Then fullregistrybank tmp/run-facet-published-bank.py
(expected1969cases) withreceiptpathsame; freezeinputs until bankandfinalizerterminal.
Prepared tmp/frost-finish.py expects37acceptedreviews, writesmatrix/scope/completion.
Do not repeat appenders; checkexistingregistrybefore rerun.

## Dwarf complete published report bank passed — 2026-10-02

exec92001terminal0:1913passed738.62s. Receiptselected6159fc0d4e556e5d22e018ffa755234225a396debb6fa1800636f17bf5539f91,
exitstatus0,sources_unchangedtrue. Finalizer35257LIVE, tmp/dwarf-finish-final.log,
alreadyreports36reviewsaccepted. Keepinputs frozenuntilmatrix/scope/completion
terminal0. Old91533/97314interruptedruns are superseded; do not accepttheirpartialreceipts.

Currentturnprogress: persistedHarlequinrollresearch, actualsuccessfulfullbank;
notblocked/completed. Harlequin40eligibleasks/18sellers,alletherealunknown,
39socketcontentsunknown. pricingsnapshotsha pinned in
pricing/data/appraisal-harlequin-roll-research-2026-10-02.json. No guessedthreshold.

Concrete nextproposal TMPONLY tmp/frost-ordinary-proposal.json. Threecomplete
scopedmixedrolls (8/9,9/8,10/10) supportobserveddemand; only1completeperfectcore.
Lowerpartial6/9and10/7seller lacksGF; historicalanybucketincludes5/7 butscopelegacy.
Need FINALSEMANTICREVIEW beforeapply: genericBlizzard socket role already accepts
native5/5core plusMF15..35; compare reviewedcoldsocketalternatives, don't mechanically
inferfullminimuminterval fromthreehighrollasks or assertmarketdominance overFacets.
Source pstats331damage→747 and335pierce→609; XP85→776,MF80→461,GF79→460.
Proposalexplicitlymarkedpendingreview; notimplemented. Draftred
 tmp/test_frost_trade_draft.py (fiveordinary/min/core/secondary/perfectcases)
usesexistingnativejewel('cold') fixture withfixedcold/procstats andtable422.
If semanticreview cannot supportfulldomain, keepproposalpending and pickother
independentwork; no arbitrary sampleminimumcutoff, no automaticpremium.

## Named/affixed evidence follow-up during confirmed live verification — 2026-10-02

Previous turnprogress; currentturnverified live bank92001 and finalizer35257;
prep96458terminal0. Same1913-case bank still progressing without failures;
use tmp/dwarf-published-bank-final.log and tmp/dwarf-finish-final.log. No restart.
Inputs remainfrozen. Completionstillunproven; no blocking/completion claim.

New persisted research pricing/data/appraisal-crafted-ring-roll-research-2026-10-02.json:
157eligible craftedRing asks/17sellers but0matches for reviewedZeal highleech/life/
minDamage/AR combo;3matches for reviewedAbyssFCR+allres Bloodrecipe, allONEseller.
Builduse remains independent; no tradequalification inferred fromlargeglobalcount.
Read nativepropertymapping through metadata, canonicalizedallres beforematching.
Raw targetedcohorts/profiles under tmp/crafted-ring* and tmp/abyss-crafted-ring*.
WarTraveler followup persisted pricing/data/appraisal-war-traveler-roll-research-2026-10-02.json:
56eligibleasks/29sellers;55unknowneth;31unknownbase;only3explicit totaldefenserows.
Enhanceddefense%alonecannotinferethereal. No thresholds invented fromthoseasks.
Plan ROLL_VALUE_REVIEW.md currentheader/registry updated36identities1913cases;
last fully completed checkpoint remainsTorch35 whileDwarfverificationrunning.

## Dwarf full verification restarted after regression fixes — 2026-10-02

Supersedes all older running job notes. Previous partial bank91533 intentionally
interrupted (682passed/exit2) and finalizer97314 terminated. No partialreceipt accepted.
Complete Dwarf regression audit found6old farming-accessory expectations showing
a tier for impossible ethereal/socketed rings. Fixed sharedberserk_farming_accessories
fixtures to explicitly assert unresolvedqualification and no trade/tierline for
those variants; role assertions preserved. New perfect-MDR evidence regression
rejects a premium from2sellers without relying on an unrelateddefaultgroup failure.
Green:78relatedunittests93.07s;138relatedpublishedappraisals55.20s;5policytests0.66s;
lint/format/diffcheckgreen. No runtime/rulechanges; selectedgeneration unchanged
6159fc0d4e556e5d22e018ffa755234225a396debb6fa1800636f17bf5539f91.

LIVE exec92001 full1913publishedreportbank -> tmp/dwarf-published-bank-final.log.
LIVE exec96458 sevenauditrefresh -> tmp/dwarf-prepare-final.log.
Queued new finalizer logs tmp/dwarf-finish-final.log; helpernowpins CURRENT executable
inputs aswellas generation, so ignores interruptedoldreceipt withsamegeneration.
It requires terminalexit0/sourcesunchanged before dwarf-finish.py (36reviews).
Do NOT mutate executable/rule/test inputs until allterminal. No commit/stage/restart.
Currentturnprogress:actualregressionfixes, notonlywait.

Next evidence: pricing/data/appraisal-ik-armor-roll-research-2026-10-02.json and
 tmp/griffon-roll-followup-census.json. Griffon100rows,68eligibleasks/10sellers but
67unknownethereal,62unknownsocketcount,41filled/27unknowncontents. Do not infer
nonethereal or zero sockets, or treat total lightningrolls with fillers asnative.
No new threshold justified. IKnearmaxupgradedgloves don't establish lowercutoff.
No new livecollection authorization; otheroffline assessment work remains.

## Dwarf legacy regression correction — 2026-10-02

Previous turn is progress. On continuation found existing
policies/test_dwarf_trade_qualification.py still asserting no qualification for
all MDR rolls. Reproduced6red cases in tmp/dwarf-legacy-red.log. Intentionally
stopped bank91533 after682passed249.85s (exit2) and queuedfinalizer97314(exit143),
BEFORE modifying test. Do NOT call these live or accept partial receipt.
Replaced obsolete expectation with source-backed regression proving the current
TWOperfectsingleitemsellers cannot establish a premium. Defaultunresolvedempty
is used so rejection actually addresses the premiumcohort. Green5tests0.66s;
lintgreen. Runtime/rules/publication unchanged6159fc0d..., no republish needed.
Broader Dwarf regressions now RUNNING exec47838 tmp/dwarf-related-regressions.log
and related published bank exec97429 tmp/dwarf-related-bank.log. Await both;
fix realfailures, then rerun full1913 bank into NEWlog before finalizer. Old
finish-dwarf-when-receipt-ready.py currently sees failedsamegenerationreceipt;
do NOT relaunch unchanged until a new successfulreceipt exists (or gate freshlog).
Seven dependent preparationaudits already complete. Need refresh bankcoverage
if tests change affects inputfingerprint; usual dwarf-prepare.py beforefinalreceipt.

IKfollowupresearch saved pricing/data/appraisal-ik-armor-roll-research-2026-10-02.json.
No runtime rule: upgradedForge135/136/136doesn't establish lower-rollthreshold;
Detailupgraded3rows=2sellers. CachedBerserkguide proves threepiece utility, not
arbitrary upgradeddefense sellability. Don't infer135cutoff fromsampleminimum.

## Dwarf ordinary trade qualification implemented and published — 2026-10-02

Torch checkpoint fully finished: exec46377 terminal0,35reviews accepted,
1900passed728.56s, matrix/scope/completion refreshed. Last completed aggregate
110678remaining, complete:false. Goalactive, concrete progress this turn.

Dwarf published generation6159fc0d4e556e5d22e018ffa755234225a396debb6fa1800636f17bf5539f91
(121artifacts). Ordinary candidate for legal12–15MDR; fixed100%GF/15%absorb role
and3independent complete scoped single-item asks. Only2perfect sellers: no premium.
Original maximum-only withdrawal not reversed: this is reviewed ordinary demand.
Guide demand verified in cached gold-find-barbarian Rings section, hashed into
pricing/data/appraisal-dwarf-roll-review-2026-10-02.json. Native definition matches.
Canonical policy red4 then green4. Source suite62passed plus1obsolete expectation
fixed to still-unreviewed Nature'sPeace; targeted rerun5passed0.68s. 13staged bank
casespassed10.55s. Lint/format/diffcheckgreen. All20saved captures preserve
extraction/price/text (tmp/dwarf-selected-replay-proof.json).
Existing dwarf_trade.py was revised and its existing registry slot retained;
a duplicate registration added during editing was removed before verification.
36thtrade review registered with13cases; total1913cases.
RUNNING exec91533: full published report bank tmp/dwarf-published-bank.log.
RUNNING exec64998: seven dependent audits tmp/dwarf-prepare.log.
Queued finalizer via tmp/finish-dwarf-when-receipt-ready.py waits for this generation's
successful unchanged-source receipt, then runs tmp/dwarf-finish.py; log tmp/dwarf-finish.log.
DO NOT mutate executable/test/rule inputs or restart these jobs while running.
Verify terminal0 and36acceptedreviews; then update this header with currentcounts.

Next read-only research: tmp/ik-forge-roll-lookup.json and
 tmp/ik-armor-roll-candidates.json. Upgraded IKForge has3independent single-item
sellers (135/136/136totaldefense); original2sellers. IKDetail upgraded THREErows
are only TWOsellers, not3: cannotpool repeatedseller ororiginalbase. Original
lookup baseWarGauntlets, native setID73, fixed65defense/20str/20dex plusfixed
gethit-skill. Any roll-specific review must understand upgradedbase defense and
set-dependent IAS; no genericstarter/leveling expansion. Currentconstraints:
SC/NL/PC/RotW only, no live authorization, no commit/stage, no workerrestart.

## Torch published reports passed — 2026-10-02

exec74218 terminal0:1900passed728.56s; receipt confirms selected
fdfcd61b772fb5ac72055f85afd85ce0554c7e7441d9937cd9f57bf2c6f3efe7,
exitstatus0 and sources_unchanged:true. Finalizer exec46377 is LIVE:
tmp/finish-torch-when-receipt-ready.py -> tmp/torch-finish.py,
log tmp/torch-finish.log already reports35reviews accepted.
Keep executable/test/rule inputs frozen until finalizer terminal.
Dwarf13case bank draft tmp/dwarf_trade_cases.py passes native scalar boundary proof;
ready to move into canonical item bank only after finalization.

## Live verification checkpoint — 2026-10-02

Torch published bank exec74218 still running; no failures observed. Do not start
another bank or alter runtime/rules/tests before terminal and torch-finish.py.
Dwarf ordinary proposal additionally validated through validate_review and native
scalar specification (tmp/dwarf-ordinary-proposal-proof.json). Its four draft tests
are red on unchanged runtime and green with the proposed policy injected only in
a temporary test (tmp/dwarf-ordinary-proposal-green.log:4passed0.98s). This is not
yet an implemented/published Dwarf rule. Next turn finish Torch receipt first,
then apply/test/publish Dwarf ordinary demand. No completion or blocking claim.

## Torch refinement published; verification running — 2026-10-02

Supersedes previous running-state notes below. Guardian finalization completed:
34 reviews accepted; matrix/scope/completion refreshed. Goal remains incomplete.
Torch selected generation: fdfcd61b772fb5ac72055f85afd85ce0554c7e7441d9937cd9f57bf2c6f3efe7.
Implemented native exactly-one +3 class selection, separate compound roll validation,
Amazon ordinary demand only; other seven classes unresolved under the complete
scoped seller census. Preserved premium qualitative tiers independently. Native
coverage requires all 80 new item cases. Red27 tests; focused45 green; source97 green;
maintenance integration36 green. All20 saved captures preserve extraction/price/text.
Evidence: pricing/data/appraisal-torch-class-roll-review-2026-10-02.json.
35th review registered. All seven preparation audits finished (tmp/torch-prepare.log).
RUNNING exec74218: tmp/run-facet-published-bank.py, 1900 published report cases,
log tmp/torch-published-bank.log. Freeze executable/test/rule inputs until terminal
and finalizer: uv run --offline python tmp/torch-finish.py > tmp/torch-finish.log 2>&1.
After finalizer verify receipt sources_unchanged and all35 reviews, update this state.

Next concrete proposal ONLY in tmp/dwarf-ordinary-proposal.json: Dwarf Star ordinary
candidate for all legal12–15 MDR; fixed100% GF/15% absorb independently support its
role. Three complete scoped single-item sellers at13/15/15 support ordinary demand;
only two at15 means no premium. Earlier withdrawal addressed only maximum-MDR group,
not ordinary demand. tmp/test_dwarf_ordinary_draft.py reproduces missing ordinary
qualification (4 red tests). Do not mutate sources until Torch receipt/finalizer ends.
Need validate proposal, canonical tests + bank boundaries, register scalar review,
publish/replay/new receipt and refresh coverage. No fresh market collection authorized.
Crown of Ages/Andariel rows with sockets mostly unknown contents or filled: do not
reinterpret structural readiness as unsocketed/empty evidence.

## Guardian published report bank terminal green — 2026-10-02

Run51324 terminal0:1820passed658.67s; tmp/guardian-published-bank.log. Full34review
receipt sources unchanged on selected0ee2ed0f747f30ce2dd5c06786816bdcc3e0dbc80387fe98a4cb9ca750f6e0ba.
Guardian finalizer exec55067 is RUNNING (tmp/guardian-finish.py > tmp/guardian-finish.log),
so keep executable/test/rule inputs frozen until terminal. Previous currentturn
classified verified wait plus research progress; no blocker and no completionclaim.

Torch explicit final census tmp/verify-torch-class-census.py / torch-verified-class-census.json
rechecks native classproperties through market_projection, unique/base/ethereal/
empty-sockets, explicitSC/NL/PC/RotW, datedsinglepositiveasks, exactlyone+3class,
coherent compoundattributes/resists10..20. Use this census ratherthan exploratory
labelsearch counts. Includes normalizedrow hashes and currentmarkethash. Any-roll
Amazon demand context exists in WP-H CH-torch-amazon-all; unknownRotW10/16listing
muststayexcluded fromactualpricedcohort despite historicalbucketmention.
Draft27red tests and200tier-equivalence proof remain in tmp only, not implemented.
Goalactive/incomplete; do not mark allitems covered.

## Torch next-item investigation while Guardian receipt runs — 2026-10-02

Current turn: verified live Guardian bank51324 (do not restart); no source/rule/test
mutations while receipt/finalizer runs. Read-only research changed next action:

- tmp/torch-class-market-audit.json: dated, scoped single-item positive asks give
  Amazon3sellers (15/11,20/14,18/19), Warlock2, all otherclasses1 each. Source
  wph-hellfire-torch.json; must further verify explicit scope/native facets before
  final rule. Pooling allclasses would give a false breadth of evidence.
- Native unique400 randclassskill chooses class0..7; +3bonus. Stats allattributes
  and allresists are independent10..20 compoundrolls. Existing random_skills
  comparison_gaps verifies oneclassbonus in a complete capture. classfields:
  Amazon453, Sorceress514, Necromancer498, Paladin442, Barbarian403, Druid488,
  Assassin519, Warlock1862; verify via market_projection mapping/metadata in code.
- WP-H CH-torch-amazon-all has any-roll context, but historical figures/fills cannot
  become scopedprices. Its additional10/16 ask is normalized id5015f2537a7676754941be29
  with missingRotW1854 and scope_statusunknown; keep excluded (not fourthseller).
- tmp/test_torch_trade_draft.py is a TEMP draft with27 red tests2.28s: Amazon
  ordinarycandidate low/mixed/perfect (no premium from3mixed asks), otherclasses
  unresolved, missing/wrong/duplicateclass and compound/variant contradictions.
  No canonical test file or runtime rule yet. Re-evaluate expectations against
  native/source review before applying; classscope evidence remains essential.
- Torch rootnamedtier currently stores premium18+/18+ or20/20 in valid_if. That
  would wrongly restrict an ordinary trade rule inheriting parentvalidity.
  tmp/torch-tier-separation-proposal.json / proof.py moves premium clause tohigh
  override, defaultlow, leavesnativebounds/variantvalidity in valid_if. Shadow
  checkpreserved all200 tier outcomes (8classes x5attributepoints x5resistpoints).
  Nativeclassmissing/unknown variants and existingtier tests still required.

Suggested bounded implementation after Guardian finalizer: add separate reviewed
required-class guard for Torch (complete capture, exactlyone verified+3nativeclass;
no mixed/unknown advertisedclass, no crossclass sellerpool). Keep variablecompound
rolls separate fromfixed classselection; numerical NamedHandler remains strict.
Runtime/evidence should share nativeclass validation but not infer identity from
rolls. Maintenance needs class-aware compoundLargeCharm scope: independent scalar
boundaries plus all8class cases/unknown/incomplete/multipleclass cases and full
source-bound census of unreviewedclasses; existing genericcompoundscope supports
SmallCharm only. No falsecompletefamilyclaim fromonlyAmazonreview. Existinghigh
qualitativetiers preserved independently of actualtradequalification.

Frost currently has3completepricedhighrolltuples and1lower6/9seller missinggoldfind;
not enough to invent allminimum-roll demand or distinctperfect premium. The proper
next step there needs explicit separation of trade-driving and exact-price facets,
not arbitrary sample-minimum cutoffs or substitution ofperfectplannerexamples.
No newliveauthorization. Goalactive, broadcompletionstillunproven.

## Guardian premium publication selected; full report bank running — 2026-10-02

Publication80499 terminal0, selected0ee2ed0f747f30ce2dd5c06786816bdcc3e0dbc80387fe98a4cb9ca750f6e0ba
(121artifacts). Savedreplay29650 terminal0:all20extractions/prices/text unchanged
versus facet checkpoint;tmp/guardian-selected-replay-proof.json. Preparation85380
finished all seven dependent audits (tmp/guardian-prepare.log).

RUNNING: exec session51324, source-bound published item bank; tmp/guardian-published-bank.log.
Command uv run --offline python tmp/run-facet-published-bank.py dynamically selects
all34 registryreviews /1820 requiredcases and writes shared named-jewelry-trade
receipt. Do not edit executable/test/rule inputs during it or subsequent finalizer.
After terminal0 run uv run --offline python tmp/guardian-finish.py > tmp/guardian-finish.log 2>&1.
It requires34 acceptedreviews, rebuilds matrix/scope/completion. Goalunfinished;
last complete checkpointfacet110679remaining. No new live collection or permission.

Extra Frost research: tmp/protector-frost-roll-research.json / lookup.json. Offline
index has14demandrows, including Blizzard MF socketfiller planner with perfect
example, not a minimumtrade threshold. Additional priced6/9 listing omitsgoldfind;
three completefive-roll sellers are8/9,9/8,10/10. Missingsecondary is not a known
legalroll, and perfectplanner is not proof lowrolls unsellable. Nextreview should
consider separation of trade-driving facets and exact-price facets explicitly,
not generalize highrollcohort to allminimums or inferpremiumfromoneperfectseller.

## Guardian Light/Thunder roll refinement green, publication pending — 2026-10-02

Previous turn classified PROGRESS: eight facet variants implemented/published and
1740source-bound report cases passed. Finalizer66792 terminal0:34reviews accepted,
matrix/scope/completion finished. Selected facet01ce01a...; aggregate incomplete,
remaining110679, identities2548, occurrences62891, reviewed3527, excluded15229,
coverage8770. tmp/facet-completion.log. No blocker condition.

Now upgraded Guardian Light and Thunder from ordinary-all-rolls to joint10/10
premium. Four independent dated complete-five-roll perfect sellers each; separate
ordinarygroups19/13sellers. Secondary rolls remain required; no secondary-only
premium. Evidence artifact appraisal-guardian-core-roll-review-2026-10-02.json.
Native/evidence mapping unchanged; no new market fetch/import or snapshot change.
Updated two root trade policies and tests; review registry still34identities.

Redtmp/test_guardian_jewel_refinement.py:4failed34passed1.06s for both10/10 with
secondaryminimum/maximum. Moved exact tests to canonical tests/.../policies/
test_guardian_jewel_trade.py. Green policy+allsourceevidencetests95passed98.52s.
Expanded guardian_jewel_trade bank from106→186cases, includes9/10 and10/9 boundaries;
staged186passed68.42s. Native scalar completeness checker accepts all186 and
rejects removal of every individual case:tmp/guardian-native-boundary-proof.json.
Updated registry two policy fingerprints/reasons/casehashes; source/definition
hashes verified. Lint and diffclean. No other execution/rule changes.

Publication running; tmp/guardian-publication.log. Next: verify selected generation,
replay all20 saveditems vs facet checkpoint (price/extraction/text unaffected),
refresh dependent bank/observed/fixed/variable/material/potion/scroll audits before
source-bound final report run. Allregistryrequired cases now1820. Reuse
 tmp/run-facet-published-bank.py (reads currentregistrydynamically), but log under
 guardian prefix; then adjusted facet-finish.py (still34reviews), after terminal0.
Do not edit executable/test/rule inputs during final receipt/finalizer.

Protector Frost cache only complete8/9,9/8,10/10 from3sellers; do not infer demand
for allminimumrolls fromthese3highrolls. A future review needs conditional/partial
trade boundaries and source-bound low-roll evidence audit. Only1perfectseller,
so no distinctpremium supported. Stone perfectalso1seller. No live approval yet.
Goal active/incomplete. No commit or worker restart.

## Facet published bank green; completion finalizer running — 2026-10-02

Final report run7423 terminal0:1740passed623.32s. Receipt generation
01ce01a8018c17b28bf3dfa9e36a24201d9605250487c1d1df0934738584ec69,
exitstatus0,sources_unchanged=true. tmp/facet-published-bank.log.
Finalizer66792 RUNNING: tmp/facet-finish.py > tmp/facet-finish.log 2>&1.
It already accepted all34trade reviews, now rebuilding matrix/scope/completion.
No executable/test/rule changes until this completes. Previous running-session
notes below are historical. Next proposals tmp/guardian-premium-proposals.json
validated offline only, not yet applied. Goal active/incomplete; no live approval,
no commit/restart. All relevant details and red/green proof below.

Additional read-only checks during the receipt run: tmp/facet-fixed-listing-audit.json
found zero explicit fixed-stat conflicts in any reviewed facet listing. Next-item
research tmp/next-colossal-roll-audit.json: Guardian Light ordinary48rows/19sellers,
perfect15/4; Thunder ordinary35/13, perfect13/4. Every five-roll tuple complete,
dated and scoped. Perfect versus ordinary seller-min median asks182.736vs2.585
and188.4465vs6.638 respectively (dated2026-09-18, not price estimates). Secondary
rolls vary; no same-seller matched-secondary pairs, no separate secondary premium.
Two validated policy proposals saved ONLY in tmp/guardian-premium-proposals.json;
not applied. After facet checkpoint completes, implement with red/green tests and
expanded boundary/report bank. Protector Frost2ordinarysellers/1perfect, Stone
12ordinary/1perfect: do not promote a distinct premium from one seller.
Full structural audit tmp/facet-next-market-readiness.json is prerequisites only,
not actual price/roll coverage. IK Detail/Forge split original/upgraded bases and
Torch explicit class rolls must not be pooled. No live authorization received.

## Facet roll qualification published; final report receipt running — 2026-10-02

Selected generation: 01ce01a8018c17b28bf3dfa9e36a24201d9605250487c1d1df0934738584ec69
(121 artifacts). Eight native Rainbow Facet variants now have separate reviewed
trade_qualification records in variant_rules. Joint 5/5 is premium; other legal
complete rolls remain ordinary candidates. Evidence is dated SC/NL/PC/RotW asks,
not completed sales or exact prices. Each variant has >=4 independent sellers in
each segment. Lightning Level-up excluded one listing with a conflicting trigger.
Review artifact: pricing/data/appraisal-facet-trade-review-2026-10-02.json.

New policies/trade_facets.py validates native catalog/label, material axes, integer
rolls, and advertised trigger conflicts. Runtime selects only the verified native
variant, checks captured trigger and both legal rolls. Nested reviews must cover
all eight variants; no pooled root fallback. trade_evidence validates native
listing provenance; date_recovery.verify_policy_sources traverses nested reviews.

Red/green: initial94fail/1pass; fractional guard16fail/95pass; final facetpolicy
and maintenance122passed9.93s. Staged item bank192passed74.79s. Policy/regression
188passed101.44s. Broad policy run1027passed/14failed because sources/index were
being rebuilt concurrently; affected four modules rerun after stabilization:
69passed11.09s. Do not repeat tests during source mutations. Lint/diff clean.
Maintenance native_facet_variants scope independently verifies all roll boundaries
and missing/chance/cross-native trigger cases; omission tests10passed2.14s.

Market references rebound only after every old cited row fingerprint remained
unchanged. Five watch baseline rows unchanged, Torch row changed only verified
collection dates; tmp/facet-baseline-rebind-proof.json. Registry33 prior policy
hashes and6 unresolved-region hashes rebound after proving snapshot-only changes;
tmp/facet-review-rebind-proof.json. Added one complete native_facet_variants review
for Rainbow Facet: total34reviews,192facet cases,1740total required case IDs.

All20 saved published replays have identical extraction/text/price decisions;
only source generation provenance and policy date advanced. Proof:
 tmp/facet-selected-replay-proof.json. Rebuilds and dependent audits finished via
 tmp/facet-trade-rebuild.py and tmp/facet-prepare.py; logs adjacent.

RUNNING: exec session7423 runs tmp/run-facet-published-bank.py. It executes all1740
required registry cases against publication, writes source-bound receipt
 pricing/data/report-receipts/named-jewelry-trade.json. Log tmp/facet-published-bank.log.
DO NOT edit executable/test/rule inputs during this run. When terminal0, run
 uv run --offline python tmp/facet-finish.py > tmp/facet-finish.log 2>&1
This requires34 accepted reviews, then regenerates matrix/scope/completion.
If failures, inspect/fix specifically and rerun required checks; never weaken
receipt gates. Goal stays active/incomplete (last aggregate110680remaining).

Next offline research while receipt runs: tmp/audit-next-colossal-rolls.py (session54195)
reads newly dated Guardian Light/Thunder, Protector Frost/Stone groups, writes
 tmp/next-colossal-roll-audit.json. No new live collection authorized or received.
No commits, no worker restart. Python changes require host worker restart.

## Targeted facet cache reconciliation applied — 2026-10-02

Implemented CLI pricing.knowledge.facet_recovery with --write. It only reconciles
verified eight facet catalog/name pairs (including already canonical rows), checks
properties against raw listing fields, preserves non-derived evidence and every
unrelated row, and checks existing trade evidence hashes before writing. Proof:
 pricing/data/appraisal-facet-recovery.json. Tests5passed0.31s; lintclean.
 tests/pricing/knowledge/test_facet_recovery.py. Initial red was missingmodule;
normalizationbehavior already had separate38-case red/green proof.

Full dry1274 and apply43298 terminal0:800changed/40335unchanged of41135observations.
 tmp/facet-recovery-{dry,apply}.log. Follow-up15537 terminal0:zerochanges/all41135
unchanged, tmp/facet-recovery-idempotent.log. Current stagedmarketsha
57ad30f409ef5643fd48abc09095f125c48d4a831f1b138583f3ec336674b210.
No jobs running. Existing selected generation remains Bile2459615d..., not these
new facet code/cache changes. Rebuild/publication/replays/source rebind pending.

Reviewed pervariant asking groups after normalization: each ofeightfacetvariants
has>=4independent sellers in ordinary and joint-perfect groups. Seller-min median
perfect exceeds ordinary for each, but some ranges overlap; no salesguarantee or
exactprice fromtheseaggregates. Trigger/catalog variants mustremainseparate.
Earlier persisted cohortresearch points to pre-normalization proposedrows; use
currentmarketrecords andtheirnewfingerprints for actualtradeevidence.

NEXT implementation architecture: attach trade_qualification to each existing
RainbowFacet variant_rules record (each table_ids=[nativeID]); rootreview absent.
Require perreview facet_table_id matches its nativevariant, validateall eight via
sharedverifiedcatalog map. Extend named_tiers policy validation and trade_qualification
selection to resolve nativevariant before choosingreview. No mixedroot+variant
fallback. Materialkeys twoelementrolls; requirecorrectnativefixedtrigger (reuse
facet_trigger) before trade classification. Evidence rows now canonicalRainbowFacet
and retain catalog_name/catalog_id/nativeprovenance; validate matchingcatalog and
reject conflicting advertisedtrigger fields before providing nativeidentity to
trade_evidence ItemFacts. Missing listingfixedtrigger may use verifiedcatalog,
never invent nonexistent PoisonLevelup field. Unknown/crossvariant captures stay
unresolved. Thresholdjoint5/5premium, otherlegalrollscandidate onlywithseparately
validatedevidence pervariant. Native/crosscatalog/unknown/illegal/report tests.
Maintenance will need variant-aware scalarfacet scope; current scalarreviewrequires
one native definition and registryidentity is one RainbowFacet (all8variants under
onecomplete review), not8duplicateidentityrows. Keep pervariant source/roll tests.

Allstagedmarket snapshotrefs need rebinding onlyafter proof unchanged citedrows;
include six unresolved_evidence fingerprints BEFORE source-bound finalreportrun.
No livecollection/permission received; no commits. Goal active; turnprogress.

## Facet normalization and comparison code green; cache update pending — 2026-10-02

Finalizer30195 terminal0:33reviews,matrix,scope,completion finished on Bile selected
2459615d47f837c362fe6cd077f9c2e0c293eb7d894707513e7224e3dc6ef46c.
Complete=false; remaining_tasks110680 (from tmp/bile-completion.log).

Registered16additional documented collection dates, then CLI dry4325 and write25095
terminal0:41135observations,1600changed dates,20676→22276dated. Logs
 tmp/facet-date-recovery-{dry,apply}.log. validate_records passes allregistered
provenance. No market facets changed during date recovery. Nowmarketsha changed;
alloldwholemarketsnapshot references/audits need eventualverifiedrebind, including
six unresolved-evidence fingerprints. Do this BEFORE finalreportreceipt nexttime.

Implemented pricing/knowledge/market_facet_catalog.py:8exactID+label/native-table
mappings, native element/event/skill/chance/level verification, missing-definition
fallback, provenance retainingcataloglabel/nativeID. Genericcatalog staysunresolved.
Wired into market_named_aliases.py. Actual tests
 tests/pricing/knowledge/test_facet_catalog_aliases.py:38pass. Red32case phase
24fail/8pass; additionalnativechanged/missingdefinition5+1guardcases green.
Rootmarket regression118passed4.37s:tmp/facet-market-regressions.log.

Implemented namedcomparison:NamedHandler bindsall8catalogs via verifieddefinition;
verifiedfacettrigger fields become intrinsic optional listingfields, conflicting
values remainrejected. Removedoldsingle399 CATALOG_VARIANTS map. Added actual
nativecapture→normalization→contract→matching integration tests in
 tests/pricing/knowledge/assessment/test_facet_catalog_comparisons.py.
Correctlyformed red7fail/1pass (initialfixturecompleteness/pricebugs corrected
beforeproductionchange). Greenfocused16pass0.53s including existingtriggertests.
Broader42passed3.15s:tmp/facet-comparison-regressions.log. Ruff/diffclean.

Dry targeted facet re-normalization validated by tmp/facet-normalization-dry.py:
800matched observed rows,40335other rows unchanged;rawproperties,dates,ask,seller,
listing IDs unchanged; existingtradeevidencerowhashes preserved. Proof
 tmp/facet-normalization-dry-proof.json. Initially guessed1200count andcorrected
to actual800; no writes wereperformed. All eightWP-Hfiles have100rows; do not
assume additionalWPIrows. Dryprocess93158terminal0. No jobs running.

NEXT: implement reviewed, idempotent targetedfacet-normalization application (CLI
or guardedmaintenance), preserveproofraw/otherrows. Then rebuildKB consumers/index,
verify/rebind genuinelyunchangedcitedrows and market/unresolved-evidence snapshots,
publish,replay/checkprices and reports. Facettradevariant dispatch is STILLmissing:
roottradequalification cannot handleeightnameddefinitions/cataloglabels; add
pervariantreview isolation and fullnativevariant/report tests. Do not confuse
comparisonfix withfinishedfacettiering. Guardianpremiums/Frostreview alsoqueued.
CurrentPythoncode/facetdata changes NOTpublished; runtimeworkerrestart notperformed.
No commit/staging/livecollection. Sixitemlivepermission remainsunanswered.
Goalturnsubstantialprogress; activeoverallgoalunchanged.

## Bile dependent audits refreshed; aggregate retry running — 2026-10-02

Finalizer 91006 ended with status1 after all33trade reviews were accepted.
Matrix failed because fixed-jewelry market audit had become stale when the six
unresolved-evidence registry references changed. Report receipt itself remains
valid (1788pass, unchanged inputs). Do not repeat the report run without new need.

Prepare 56494 terminal0: tmp/bile-prepare-final.log. Bank coverage, observed,
fixed/variable jewelry and material/potion/scroll audits all regenerated against
current registry. Finalizer30195 LIVE:tmp/bile-finish-refreshed.log. It runs the
same tmp/bile-finish.py:33reviewacceptance, matrix, scope, completion. Inspect
terminal result before applying16new date records. No other job running.

Draft facet normalization regression at tmp/test_facet_catalog_aliases.py now
has32cases:8canonical mappings+8wronglabel/catalog rejection cases+16conflicting
advertised ethereal/socket cases. tmp/facet-catalog-aliases-red-complete.log:
24failed,8passed; intended missingproductionbehavior. Canonical mapping asserts
native table ID provenance, shared Jewel mechanics and repeated normalization
idempotence. Conflict cases require preserving given True/1 while recording
mechanics_conflicts. Wrongcatalog and genericcatalog must not canonicalize a
variant label. Tests remain outside registered tree pending date-only recovery.
Move to tests/pricing/knowledge/test_facet_catalog_aliases.py when implementing.
Previous genuinecomparisonred/diagnostic and8catalognative mapping remain in
pricing/data/appraisal-facet-identity-rca-2026-10-02.json. Use exactcatalog+name+
native record agreement; no generic prefix stripping. Apply1600date recovery
before normalization edits, then reconcile only the known facet observations.

Goalturnprogress:staleauditRCA/fix+strongerredcoverage. Goalactive/incomplete.
No live requests, authorization, commit or runtime changes this turn.

## Defender’s Bile: stable published report gate passed — 2026-10-02

Bank 16077 finished successfully: 1,788 passed, 28,639 deselected, 592.05s.
Log: tmp/bile-published-bank-final.log. The receipt confirms sources_unchanged=true
for selected generation 2459615d47f837c362fe6cd077f9c2e0c293eb7d894707513e7224e3dc6ef46c.

Finalizer 91006 is LIVE (tmp/bile-finish-final.log). It has accepted all 33 trade
reviews, including the six corrected unresolved-evidence references and Bile.
It is now rebuilding matrix/scope/completion. Do not restart it or change bound
runtime inputs until it exits. No other jobs are running. After terminal success,
inspect the actual completion totals; this is still far from the overall goal.

The next 1,600-row date recovery remains verified but unapplied. Proposed entries:
tmp/remaining-wph-date-candidates.json; proof: tmp/remaining-wph-date-dry-proof.json.
Apply those 16 reviews once this finalizer completes, then run date_recovery dry
and --write before changing facet normalization. That ordering preserves the
strict date-only reconciliation guarantee. Further normalization changes should
be targeted to the eight verified Facet catalogs, with unrelated rows preserved.

This turn also verified all eight native table/catalog mappings and persisted them
inside pricing/data/appraisal-facet-identity-rca-2026-10-02.json. There is a ninth
catalog, generic Rainbow Facet 2935638020, which does not establish element or
trigger; keep it unresolved instead of guessing a variant. The eight labels and
native properties are pinned to the catalog hash and definition generation.
Standalone source: tmp/facet-catalog-native-review.json.

Goal turn: progress plus verified waits. Stable report gate passed and all 33
reviews accepted; final aggregate audit still running. No live collection,
authorization, commit, worker restart or navigation changes. Goal remains active.

## Rainbow Facet comparison RCA reproduced — 2026-10-02

Previous turn progress:report1788green+six unresolvedevidence rebind. This turn
progress:read current nativefacet paths and reproduce a concrete comparison gap.
Bank16077stillLIVE (28% lastpoll),tmp/bile-published-bank-final.log. Do not change
bound production/tests/rules before terminal. Afterpass run tmp/bile-finish.py.

New persisted RCA:pricing/data/appraisal-facet-identity-rca-2026-10-02.json.
Actual complete LightningDeath native392capture via existing NamedHandler succeeds,
but real cached5/5 listing is rejected for name plus unknownbase/eth/sockets/contents
and omittedfixedtrigger. Script tmp/facet-identity-red.py now reaches intentional
AssertionError (initialdraftasdictmappingproxy error was fixed withto_dict).
 tmp/facet-identity-red.log/json. Expected spellingaliases are not canonicalized;
market_named_aliases currently only originalSunders. named_base cannot findfacet
labels; CATALOG_VARIANTS onlymapsPoisonLevelup399. Existingfacet_trigger has
strictnativeevent/skill/level/chance verification; reuseit.

Diagnostic shadowprojection (NOTproduction) exactcatalog2368934470+LightningDeath
name→nativeRainbowFacet, applycommonJewelmechanics, contractcatalogbinding, native
fixedchance780as intrinsic produceszero rejections. Wronglevelupcatalog and
conflictingchance99 remainrejected. tmp/facet-projection-diagnostic.py/json.
This establishes bounded fix notgenericnamestripping. Must supportall8 explicitly
and preservecapturednativeID+eventconflicts. No numericprice claim fromthisonecase.

Nextorder:finishBile, apply1600date-only recovery, thenfullfacetidentity normalization
andvarianttrade dispatch inonecoherent implementation. Do not change normalization
before date_recovery—it properly rejectsnondatefacetchanges. No mutation ofruntime
ornewnetwork thisturn. Pendingliveauthorization unchanged.

## Bile report green; unresolved evidence references corrected — 2026-10-02

Bank70247terminal0:1788passed596.93s,28639deselected; receipt sources_unchangedtrue
on generation2459615d47f837c362fe6cd077f9c2e0c293eb7d894707513e7224e3dc6ef46c.
Finalizer10331terminal1 BEFORE matrix: six old unresolved_evidence_fingerprint
values included preceding wholemarket hash. Allotherreviews includingBile reviewed.
No runtime/report failure. Six affected:Mara,Nagelring,Opalvein,Trek,Titan,Arachnid.

Rebind45787terminal0. Loaded current derivedevidence, replaced ONLYmarket_snapshot
with previous216534f0publishedpolicy snapshot, and verified exact old registered
fingerprint before writingnew. Allsix evidencebodies unchanged; proof
 tmp/bile-unresolved-rebind-proof.json; log tmp/bile-rebind-unresolved.log.
This changedregistryinput, so require fresh reportreceipt. Do not reuseoldreceipt
or weakeninputbinding. Do NOT rerun one-shot rebindscript afterthisapplication.

LIVE bank16077:tmp/bile-published-bank-final.log; same1788cases. No other jobs.
Afterterminal0, run tmp/bile-finish.py again; requires33reviewsaccepted then
matrix/scope/completion. Previouslyrefreshed audits/replays still current (no
runtimegeneration/datachange). Hold16verifieddate recovery untilgatecompleted.
This turnprogress:terminalreportpass+exactevidenceRCA+sourcecorrection. Goalactive.

## Recovered roll cohorts audited while Bile report runs — 2026-10-02

Goal turn classified progress: evaluated next usable cohorts; polled bank70247
confirmedLIVE (64% lastpoll). Keep bound runtime/test/rule inputs unchanged.
Prepare13372 and selectedreplay84093alreadyterminal0. After bank70247terminal0
run tmp/bile-finish.py for33review acceptance+matrix/scope/completion.

New persisted research:
 pricing/data/appraisal-recovered-roll-cohorts-2026-10-02.json.
Uses proposed16collection date recovery, not yet imported. Draft normalization
source tmp/remaining-wph-dated-draft-rows.json, script
 tmp/remaining-wph-date-cohorts.py; cohortscript tmp/remaining-wph-roll-cohorts.py.
Complete native scalar keys only, SC/NL/PC/RotW datedsingleasks. Jointperfect/other
seller counts:GuardianLight4/18,Thunder4/10; all8RainbowFacetvariants have>=4
sellers in eachgroup. DefenderFire7/8. This justifies focused premium review, not
a price claim; still check extra fields, native trigger/catalog identity, asks.
Some rows carry wrong elemental IDs (coldlisting poison783,etc) and are excluded
without automatic reinterpretation. Eightfacetgroups remain separated by catalog.

Concrete next architecture gap for facets: native identity RainbowFacet has
8variant_rules withtableIDs392..399; trade_qualification currently expects a
single rootreview and evidence row name equality. Listing labels are eight
RainbowFacet:ElementDeath/Level-up names, so cannot paste scalarjewel rules and
mergeelements/triggers. Need verifiednative/catalogvariant dispatch, separate
pervariantreviews and negativecrossvariant tests. Current scalarreview checker
requires len(variants)==1. Implement after16date recovery/verification or alongside
that next coherent change; do not weakeningidentity validation for pooleddata.
No production mutations/new live requests this turn; oldBilebehavior remains
published, finalreceipt stillrunning. No authorizations received.

## Bile verification running; next date recovery reviewed — 2026-10-02

Previous goal turn progressed through publication. This turn completed selected
replay verification and dependent audits, plus independently verified a larger
offline evidence recovery. No blocker streak; goal remains active.

Replay84093terminal0. All20saved extraction/price/text unchanged versus preceding
named-misc generation:tmp/bile-selected-replay-proof.json.
Prepare13372terminal0:bankcoverage,observed,fixed,variable,material,potion,scroll
refreshed. tmp/bile-prepare.log. No source mutations during report run.
Bank70247stillLIVE (24% last poll):tmp/bile-published-bank.log. After terminal
success execute tmp/bile-finish.py to require33reviews thenmatrix/scope/completion.
No other jobs live. Do not restart bank or mutate bound input until it finishes.

Next independently reviewed recovery, WITHOUT network:
 pricing/data/appraisal-remaining-wph-date-review-2026-10-02.json.
16bare WP-H collections:fourremainingColossal,eightRainbowFacetvariants,Gheed,
HellfireTorch,Fire/LightningbaseSunders. Exact original2026-09-18source/date/query,
rawhash,catalog,count/scopechecks pass. 63other candidate links rejected; no
weakened validator. Torch has32samecollectionlinks; selectedoneWarlock-all
source pointer does NOT imply all observed TorchclassesareWarlock. Listing facts
remain authoritative. tmp/remaining-wph-date-candidates.json has16proposedrows.
Dry current normalizer+recover_rows proves1600date-only changes and preservesall
existingtradeevidencerowhashes:tmp/remaining-wph-date-dry-proof.json.
No registry/market writes yet. Process72591terminal0. Candidate census script
 tmp/remaining-wph-date-census.py and dryscript tmp/remaining-wph-date-dry.py.

After Bile final acceptance, recover this whole verified set at once to avoid
repeatingpublication/marketrebuild peritem. Then refine remaining valuable items
using actual recovered cohorts. Offlineimport only date_recovery, not broad
refresh normalization; preserveotherfacets. Fresh source/citation references,
index/publication,replays/report gates required afterward. Previous source-stable
scripts guard their baselines; do not blindly rerun one-shot scripts against new
selectedgeneration. No liveauthorization received; sixitemrequest pending.

## Defender Bile published; final report gate running — 2026-10-02

Selected generation2459615d47f837c362fe6cd077f9c2e0c293eb7d894707513e7224e3dc6ef46c,
105artifacts. Publication76955terminal0:tmp/bile-publication.log.
Rebuild25023completed. Facts/recommendations semantically unchanged were retained
byte-for-byte; six baseline watch citations rebound only after exact-row equality.
 tmp/bile-source-rebind-proof.json. ProtectorFrost watch row changed only from
verified collection dates. Recovered200dates applied earlier; no livecollection.

Policy source regression initially31stale whole-market hashes. Updated32snapshot
references after validating every cited original listing row unchanged; updated
existing review policy fingerprints with canonical ensure_ascii=False fingerprint.
 tmp/bile-market-rebind-proof.json. Earlier attempts with wrong fingerprint then
syntax error made no edits; resulting intermediate red logs are superseded.
Corrected broad policy919passed/1newBiletest failed its missing expected-band clause.
Added independent (783,723)==(10,10) expectation; affected test1passed3.82s.
 tmp/bile-policy-regressions-rebound.log, tmp/bile-source-preservation-green.log.
Native boundary checker originally rejected inherited etherealTrue alternative;
Bile parent guard now explicitly nonethereal,sockets0,empty. All93cases independently
required (dropping any case fails): tmp/bile-native-boundary-proof.json.
Final staged93passed38.03s:tmp/bile-final-staged-bank.log. Ruff/diffclean.
Candidate20savedreplays extraction/price/text unchanged;proof
 tmp/bile-candidate-replay-proof.json. Candidate was before final snapshot-hash/guard
edits, so selected replay below remains required for final state.

Bile registration8103terminal0:33registryrows,93Bilecases scalar_colossal_jewel,
 tmp/register-bile-review.log. Do NOT rerun one-shot registration/implementation.
LIVE selected replay84093:tmp/bile-selected-replay.json/errors.log.
LIVE published bank70247: tmp/bile-published-bank.log,
 selection trade or wisp or arachnid (1788cases expected). Shared named-jewelryreceipt.
Do not mutate bound source/tests/rules until terminal. After selectedreplay compare
20outputs with preceding named-misc replay; regenerate observed review, fixed and
variable market audits, bankcoverage. Since market changed also refresh material,
potion,scroll pricing audits (see tmp/wisp-refresh-dependent-audits.py and prior
date-recovery maintenance). Then run tmp/bile-finish.py (prepared,notrun):requires
33accepted reviews, regenerates matrix/scope/completion. Fresh receipts not yet
accepted. Prior32checkpoint remains historical. Goal active; this turn progress.

## Defender's Bile qualification staged and green — 2026-10-02

Previous checkpoint finalizer6017 terminal0:32reviews accepted,matrix,scope,
completion all regenerated. Stable named-misc bank1695passed sources unchanged.
Goal remains incomplete; do not treat checkpoint as end goal.

Applied TWO documented collection-date reviews in
 pricing/knowledge/documented_collection_dates.json for WP-H DefenderBile and
ProtectorFrost. CLI dry and --write terminal0:41135rows,exactly200date-only changes,
dated20476→20676. Existing trade evidence hashes preserved; no live requests.
 tmp/colossal-date-recovery-{dry,apply}.log.
Date regression32passed0.10s: tmp/colossal-date-regressions.log.

DefenderBile qualification now STAGED in named_tiers.json, not published.
Allfive native rolls required:332poison damage,336pierce,85XP,80MF,79gold.
Both332/336=10 premium; other legal pairs candidate. Premium six complete asks /
four sellers; ordinary29/six sellers from verified2026-09-18WP-H collection.
Explicit market mapping783/723/776/461/460. Additional maximum rolls do not create
unsupported premiums. Exact numeric pricing still independent. Source evidence
retains row hashes and dates. Existing identity baseline low remains unchanged.
Initial three ordinary/premium/missing cases reproduced red in
 tmp/defender-bile-red.log. Registered93case item bank module
 tests/pricing/knowledge/assessment/item_bank/cases/defender_bile_trade.py.
STAGED93passed36.79s: tmp/defender-bile-green.log. Ruff check/fix importorder/format
clean. No receipt generated yet for new cases. Do NOT rerun one-shot
 tmp/implement-bile-qualification.py; already applied.

LIVE rebuild25023: tmp/colossal-date-rebuild.log. Script
 tmp/colossal-date-rebuild.py runs runewords,facts,recommendations,valuable,index,bases
sequentially (offline). Consumer logs tmp/colossal-date-rebuild-*.log.
After terminal inspect generated source fingerprint effects, follow prior date
recovery maintenance/rebind workflow deliberately, not blindly rerunning old
one-shot scripts. Existing market snapshot changed; audits/receipts must be
refreshed for new selected generation. Need publication + savedreplays + broad
report gate + register Bile scalar_colossal_jewel review with93case hashes and
independent native boundary checking, then33review acceptance and completion.
ProtectorFrost's recovered1perfect/2other sellers do not establish premium; no
new Frost qualification yet. Read current recovered evidence (old audit predates
recovery). Sixitem live authorization still pending, no fetch performed.

## Named misc report gate green; finalizer running — 2026-10-02

Bank57558 terminal0:1695passed,28639deselected,593.31s.
 tmp/named-misc-final-bank-corrected.log.
Shared named-jewelry receipt sources_unchangedtrue, generation216534f0e9aed6bd88b6d049093fddcbb11ab464c7036d9cd8f02e940db850c3.
Finalizer6017 LIVE: tmp/named-misc-finish.log. Already accepted all32trade reviews;
coverage_matrix child confirmed live. It will regenerate matrix,scope,completion.
Do not restart or mutate bound runtime/review inputs before it exits.

Next offline recovery remains prepared, not applied. See the following entry.
Recovered Bile complete-roll cohort:6joint-perfect rows/4sellers,29other rows/6sellers.
All from dated2026-09-18 scoped single asks. Premium is joint10poison damage and
10pierce, with all XP/MF/gold fields required and legal. MaxXP/MF/gold alone does
not establish an extra premium. Protector's Frost has1perfect seller and2other
sellers: insufficient separate premium evidence. Draft Bile93cases prepared at
 tmp/defender_bile_trade_cases.py, not registered or executed yet. This clones
DefenderFire boundary structure using verified native332/336; use red-green.

This goal turn completed a stable report gate and advanced roll evidence review.
No live collection or authorization received. Goal remains active/incomplete.

## Offline Colossal collection-date recovery prepared — 2026-10-02

Previous goal turn was progress (fixture correction + independent roll review);
this turn adds verified offline provenance and polls bank57558 live. It is still
running (50% at last poll); do not restart it or mutate bound inputs yet.

New authoritative research artifact:
 pricing/data/appraisal-colossal-date-recovery-review-2026-10-02.json.
Both raw WP-H files match dated per-item queries, exact hashes,100listings each,
catalog IDs, original SC/NL/PC counts and collection log/timestamp bounds.
Documented collection day2026-09-18 for Defender's Bile and Protector's Frost.
Existing documented_day validator accepts both proposed entries.
Dry recover_rows proves200date-only changes, preserving all existing trade policy
source fingerprints. No production registry/market writes yet. Candidates:
 tmp/colossal-date-review-candidates.json; dryproof tmp/colossal-date-dry-proof.json.
Draft normalized rows tmp/colossal-dated-draft-rows.json omit final date proof and
conversion snapshot fields; use date_recovery CLI after registering, not this draft
as an import. Recovered Bile40dated scoped single asks/12sellers; Frost3/3sellers.
Earlier audit's thin market count is true only before this provenance recovery.

After bank57558 succeeds, run tmp/named-misc-finish.py before next mutation.
Then append the two reviewed date records (not fabricated freshness), dry-run
pricing.knowledge.date_recovery; expect200changes only and preserved policies.
Apply/rebuild/verify/publish in sequence, then review material-roll segments.
No live permission received or fetch performed; six-item request remains pending.
This offline recovery may reduce that request's need; do not implicitly collect.

## Shared named misc legality fix — 2026-10-02 (verification running)

Previous Wisp work is fully verified: stable1695reports passed563.88s with
sources_unchangedtrue. Finalizer43721 terminal0 accepted32trade reviews and
regenerated matrix/scope/completion. Remaining110681required /8317trade tasks,
completefalse on generation216534f0e9aed6bd88b6d049093fddcbb11ab464c7036d9cd8f02e940db850c3.
Material/potion/scroll pricing audits were refreshed because Wisp changed the
shared comparables source. No further Wisp registration/publication needed.

Then implemented mechanics/named_variant_legality.py, shared by strict named_tiers
and composed named_baselines. Known impossible ethereal/socketed/filled misc
variants cannot regain identity baseline tiers. Uses the same reviewed CATALOGS
misc families as market mechanics plus native base/nondurability identity checks;
not a universal nodurability rule. Known ethereal sets remain rejected. Unknown
premium facts keep identity baseline; valid ethereal armor and upgraded ethereal
Ginther's Rift PhaseBlade remain allowed.

Draft red45fail/3pass (including rendered Nature report), then actual production
focused59pass2.28s including all8RainbowFacetIDs and CraftedSunderCharm.
Broader policy916passed131.96s (collected before three CraftedSunder parameters
were added; those3are covered by focused59). Ruff/format/diff clean. Expanded
catalog audit53identities:0strict/0composed impossible tiers,1ambiguousFacetfixture
excluded from diagnostic but covered by the eight explicit native tests. Artifacts:
 appraisal-named-misc-variant-audit{,-green}-2026-10-02.json.

Replay80943 terminal0: all20saved extraction/prices/text unchanged. Authority:
 tmp/named-misc-selected-replay.json; proof tmp/named-misc-replay-proof.json.
No rules/data publication change this pass; selected generation stays216534f0.
Python changes require worker restart (not performed/confirmed).

Bank4334 terminal1: 1691 passed and four stale report expectations failed for
impossible ethereal/socketed Wisp rings. Corrected shared defensive-accessory
fixtures to assert absence of Trade tier for those variants. Focused22 passed
18.45s; lint clean. No production change after the previous59/916 test passes.
Prepare73600 terminal0. Regenerated after fixture edits: prepare96665 terminal0,
 tmp/named-misc-prepare-corrected.log.
LIVE job, do not change code/tests/rules until terminal:
- bank57558: tmp/named-misc-final-bank-corrected.log;1695selected report cases,
  writes shared pricing/data/report-receipts/named-jewelry-trade.json.
After success run uv run --offline python tmp/named-misc-finish.py, redirect
 tmp/named-misc-finish.log; requires32reviews accepted then matrix/scope/completion.

Independent offline review artifact:
 pricing/data/appraisal-colossal-roll-review-2026-10-02.json.
Defender's Bile: three dated single asks/three sellers, but only two double-perfect
poison damage/pierce sellers and one nonperfect. Protector's Frost: two asks from
one seller; both missing gold find. Neither supports a new threshold/price.

Pending async user authorization (not answered): collect at most2pages each for
Griffon, Nature, Aldur, Dwarf Star, Defender's Bile, Protector's Frost,12requests.
 pricing/data/appraisal-roll-refinement-market-batch.json remains UNAPPROVED.
 tmp/collect_roll_refinement_batch.py syntaxchecked, NOT RUN. Do not infer consent.
No live fetch/import or publication occurred in this continuation.
Previous Wisp acceptance is the preceding checkpoint; fresh source-bound receipts
remain pending for this code change. Never run registration scripts again.

Goal active; this turn made concrete progress, no blocker streak. No livecollection,
staging, commit, workerrestart or navigation edits. Next after final checks:
continue valuable-item roll reviews; Griffon and Nature market gaps are documented.

## Named misc legality RCA while Wisp rerun runs — 2026-10-02

Goal turn is progress plus verified wait. Handle29046 remains LIVE; stable bank
log tmp/wisp-final-bank-stable.log was21% at last poll. Keep code/tests/rules
unchanged. After terminal success run tmp/wisp-finish.py and inspect source-bound
32-review acceptance, matrix/scope/completion. No other job is running.

New source-bound diagnostic:
 pricing/data/appraisal-named-misc-variant-audit-2026-10-02.json
47 catalog identities examined with ethereal=True/partial stats:20strict tiers,
45composed tiers, one ambiguous RainbowFacet fixture not assessed. Includes
seasonal/disabled identities; NOT a scoped completion count. Reproducer script:
 tmp/audit-named-misc-variants.py. No production edits were made.

RCA: qualitative named_tiers rules often allow either known ethereal flag.
More importantly named_baselines.assess_tier falls back to identity baseline when
strict tier is absent, and only rejects known ethereal sets. Changing Nature's
Peace's predicate alone would still leave its composed report tier low. Implement
a shared native variant-legality guard for known impossible misc variants in both
strict and composed paths; preserve existing identity baseline for genuinely
unknown premium facts. Avoid a universal nodurability rule (upgraded ethereal
PhaseBlades differ). Existing market_mechanics.CATALOGS/native misc mechanics
and D2MOO ITEMS_MakeEthereal lines228+ establish the narrow misc families.
Add red/green through actual composed report path, and explicit RainbowFacet
identity variants rather than silently skipping the ambiguous fixture. Check
sockets too where native misc mechanics establish impossibility. Do this AFTER
stable Wisp final gates so current source receipts are not invalidated again.

Nature's Peace audit now links this RCA. No cached listings, no new roll-price
claim. Current selected generation216534f0e9aed6bd88b6d049093fddcbb11ab464c7036d9cd8f02e940db850c3.
No live collection, restart, staging, commit or navigation edits.

## Wisp final receipt rerun — 2026-10-02

This turn made progress: all1695selected reports passed566.73s, but final review
check25918 failed correctly because registry registration completed after the
bank captured initial sources. The sole input difference was
pricing/knowledge/assessment/rules/trade_qualification_reviews.json.
No runtime test failed. The receipt has exitstatus0 but sources_unchangedfalse;
DO NOT accept it or rewrite its fingerprints. Registration is now terminal and
must never be rerun. Preparation and saved replay are terminal success.

A fresh identical bank run is LIVE as handle29046:
 tmp/wisp-final-bank-stable.log. Keep code, tests and rules
unchanged until it finishes. Then run tmp/wisp-finish.py (32-review acceptance,
matrix, scope and completion), record actual final counts and terminal status.
Published generation remains216534f0e9aed6bd88b6d049093fddcbb11ab464c7036d9cd8f02e940db850c3.
Goal active, not complete; no blocker streak.

Independent research: Griffon raw cache has no description fields. Twelve
25pierce/20damage Lightning Facet listings come from only two sellers. No direct
known nonethereal empty cohort; total/flat defense must remain distinct. Details
in appraisal-griffon-trade-audit-2026-10-02.{json,md}.
Nature's Peace audit saved in appraisal-natures-peace-trade-audit-2026-10-02.json:
zero cached market rows despite catalog/demand presence. Native variable rolls:
PDR7–11, poisonres20–30; fixed RIP/noheal and level5OakSage27charges. Actual strict
assess_tier reproduces an invalid ethereal ring as reviewed/low; unknowneth is
conditional. Fix this next with red/green after source-bound Wisp gates complete.
No runtime Nature policy or market inference edits yet. No livecollection,
worker restart, staging, commit or navigation edits.

## Wisp classification published; final gates running — 2026-10-02

Goal active, concrete progress, no blocker streak. New selected generation:
216534f0e9aed6bd88b6d049093fddcbb11ab464c7036d9cd8f02e940db850c3 (103 artifacts).
Previous bc27ce generation retained. Wisp now has ordinary/premium qualification:
premium requires both20%absorb and20%MF; single-perfect stays ordinary. Both legal
10–20 rolls and known nonethereal/zero sockets/empty contents required. Exact
pricing remains unavailable (121-grid audit), distinct from candidate status.
Source-bound26ask rows preserved; raw cache unchanged.

21 new item-bank cases: nine joint10/19/20points, six missing/outside points,
six unknown/illegal variants. Red21fail→green; native scalar proof passes all21
and rejects every single-case omission. 117 Wisp staged reports passed45.42s.
Policy suite865passed/one stale unreviewed-Wisp expectation. Updated it to Dwarf
Star and added Wisp source preservation; follow-up55passed/one new test branch
omission, then corrected Wisp independent expected segment; the two affected
tests pass. No production failure remains from those runs. Ruff/diff clean.

Publication36546 terminal0. Registration18523 terminal0 appended Wisp as row31
(32nd review), scalar_named_jewelry,21case fingerprints. DO NOT rerun either
registration or implementation one-shot script. Replay7884 terminal0: all20
extractions/prices/text unchanged, tmp/wisp-selected-replay.json and
 tmp/wisp-replay-proof.json.

LIVE jobs (poll authoritative handles):
- final bank65349: tmp/wisp-final-bank.log; selected trade or wisp or arachnid;
  writes pricing/data/report-receipts/named-jewelry-trade.json. Must finish and
  source bindings must validate before review acceptance is claimed.
- preparation52282 is terminal success: tmp/wisp-prepare.log; bank coverage,
  observed replay, fixed and variable jewelry audits all finished.
After both succeed run uv run --offline python tmp/wisp-finish.py, redirect to
 tmp/wisp-finish.log. It asserts all32reviews accepted, then writes matrix,
 scope manifest and ordinary completion. Inspect terminalcounts; overall goal
 still unfinished. Do not run finish early or report the prior acceptance as fresh.

Next item research: appraisal-griffon-trade-audit-2026-10-02.{json,md}. 68 scoped
single-item asks/10sellers, none known nonethereal; filled/unknown sockets dominate.
Need preserved raw variant evidence before new Griffon roll-price claims.
No live collection, worker restart, staging, commit or navigation edits.

## Wisp market projection in progress — 2026-10-02

Previous goal turn made progress (Arachnid final acceptance plus Wisp source
review). This turn implemented catalog/native-bound Wisp legacy absorb mapping
in mechanics/wisp.py, reused by comparables.py and policies/trade_evidence.py.
23 targeted tests passed red/green, including complete decoded fixed skills and
actual cached listings; lint and diff checks passed. Raw cache untouched.
All 121 legal pairs audited in appraisal-wisp-exact-grid-2026-10-02.json:
107 no matches, 14 thin, maximum two exact sellers. No numeric price claimed.

Regression handle4830 finished successfully: 239 passed in 276.57s,
tmp/wisp-regressions.log (named contracts, comparables, family contracts and
trade-policy suites). Grid handle6014 is terminal success. No running jobs.
Published generation remains bc27ce0399bc0dabb5edb9ca652da254c388afffe6c1c59b8844f6b9f62ab135.
Python/test edits invalidate previous report/source-bound receipts; Arachnid's
31-review acceptance below is the preceding checkpoint, not fresh proof.
Next: finish regressions, Wisp material threshold/item-bank/native maintenance
review and selected replay/report gates. Do not rerun the Arachnid registration
script. Full goal active; no live collection, staging, commit or worker restart.

## Arachnid native review accepted — 2026-10-02

All final jobs are terminal: 1,569 report cases passed; all 31 native trade
reviews are accepted. Matrix, scope and ordinary completion checks finished
successfully against generation bc27ce0399bc0dabb5edb9ca652da254c388afffe6c1c59b8844f6b9f62ab135.
The overall goal remains unfinished: 110,682 required tasks, including 8,318
trade-qualification tasks. The running-job notes below are historical.
Evidence: tmp/arachnid-native-final-bank.log, tmp/arachnid-native-finish.log,
tmp/arachnid-native-receipt-proof.json and tmp/arachnid-native-completion.log.
No new publication, live collection, staging, commit or worker restart.
Next: Wisp Projector's native percentage-absorb versus legacy listing field.

## Arachnid native maintenance review — 2026-10-02 (final verification running)

Goal active and unfinished; this and prior turns made concrete progress, no blocker
streak. Runtime data generation remainsbc27ce0399bc0dabb5edb9ca652da254c388afffe6c1c59b8844f6b9f62ab135.
No publication/data threshold change this pass. No livecollection/staging/commit/
workerrestart/navigation edits. Workerrestart previouslyrequested, notconfirmed.

New trade_arachnid.py checks exact native6properties, five roll definitions, EDop13
and maxmanaop11, fixedcasterstats, legalnative90..120/120premium boundary. Cases
retainformer109/110boundary, missing/outsideED,alluncertainvariants plusimpossible
0socket/filled. Capturestayspartial; completeclaimwithoutdefense/charges rejected.
Market helper now accepts an explicitselecteddefinition argument; nativechecker
andfullcacheloader don't accidentally read a different workingtree definition.
KnownFalseflag needs no totaldefense inference, but conflicting suppliedtotal still
fails; newtest wentredthen green. Missingflag stillrequiresconsistent total1855.

New trade_arachnid_evidence recomputes fullcurrentcache: perfect8rows/4sellers,
lower4/2,unproven27/24. Newthirdlower seller (including explicitFalsewithouttotal)
reopensreview; changedSHA/thinpositivecensus invalidates. Loader pinned to selected
native definition; testglobalcatalogempty stillusespasseddefinition. trade_reviews
adds native_unique_caster_belt scope and evidenceguard. Registryrow30 appended
(31st); DO NOT rerun tmp/register-arachnid-review.py.

Spec11passed; integrationred26fail/11pass→37pass30.33s. Evidence+inference50passed
before extra loader test. Final broader1428policy/maintenance tests passed242.16s
(tmp/arachnid-native-regressions.log,84373terminal0). Ruffcheck/format7files and
gitdiffcheckpassed. No code/rule/test edits since finalbanklaunch.
All20saved extraction/prices/text identical afterhelperchange; newauthority
 tmp/arachnid-native-selected-replay.json,93496terminal0; proof
 tmp/arachnid-native-replay-proof.json. Preparation42191terminal0.
Finalbank51379running: tmp/arachnid-native-final-bank.log (same1569case selection).
Afterterminalsuccess run tmp/arachnid-native-finish.py (asserts31acceptedreviews,
thenmatrix/scope/completion). Oldreceipt remainsstale untilbankcompletes.

Next useful item afterArachnid acceptance: Wisp Projector. New research
pricing/data/appraisal-wisp-trade-audit-2026-10-02.{json,md}:26scoped datedasks,
20sellers;7/7doubleperfect,19/14other,only2/2eachsingleperfect. Criticalaliasgap:
legacy689 is labelledflatabsorb; native144 percentage maps1866. Do notchangeglobal
mapping. Neednativeidentity-boundmarketprojection withdual-fieldconflict tests,
thenreviewordinarynativefloor beforecandidateclaims. NoWispcodechangesyet.
Harlequin rawcachehasno descriptions/socket clarification. Correctedpriorarmor
researchnote:65rowsallpassscope,25lackobservationdate→40dated; differencewasnot
scope rejection. Rawmarketcache unchanged; no blanketdate recovery performed.

## Arachnid publication verified — 2026-10-02

All jobs terminal. Finalbank37465 exited0:1569passed/28744deselected,529.31s.
Preparation44479 exited0. Finish7007 exited0:30existingreviewsaccepted;
matrix/scope/ordinarycompletion regenerated. Scopeverified,complete=false,
110683requiredtasks and8319tradequalifications remain. No blocker streak;
this and prior turn made concreteprogress. Goalactive, not completed.

Selectedruntime bc27ce0399bc0dabb5edb9ca652da254c388afffe6c1c59b8844f6b9f62ab135,
103artifacts; cab95retained. Onlynamed_tiers dataartifact changed, indexidentical.
Python market_ethereal_inference/trade_evidence changed: userwas told restart
appraisalworker; no restartperformed or confirmed. No livecollection/staging/
commit/navigationedits. New replayauthority tmp/arachnid-selected-replay.json.
20saved extraction/prices/text unchangedold/staged/selected, proof
 tmp/arachnid-replay-proof.json. All embeddedmarketrowSHA verified againstcache.
842policytests,535maintenance tradetests,63final inference/policyfocusedtests,
73stagedArachnidreports,1569selectedreportcases pass; Ruff/format/diffclean.
No code/rule/test edits sincefinalbanklaunch. Current sharedreceipt
pricing/data/report-receipts/named-jewelry-trade.json. Logs tmp/arachnid-{final-bank,
policy-suite-green,maintenance-green,finish,matrix,scope,completion}.log.

Next: dedicated native Arachnid maintenance proof/census and registry entry,
currentlypending (runtimepolicy is31st but only30acceptedreviews). Concrete plan
atend of pricing/data/appraisal-arachnid-trade-review-2026-10-02.md. Reuse exact
native verification with an explicitdefinitionargument; don't relax generic
scalar op13 guard. Recompute source-bound lower/premium cohorts and require
executed current nativeboundaryreports. Then continuevaluableitems (Harlequin,
Griffon,WarTraveler facet gaps remain). Do notrerun tmp/add-arachnid-trade.py.

## Arachnid roll refinement published — 2026-10-02 (verification running)

Previous goal turn and this turn made concrete progress; no blocker streak. Goal
active and unfinished. New selected generation
bc27ce0399bc0dabb5edb9ca652da254c388afffe6c1c59b8844f6b9f62ab135 (103artifacts).
Only named_tiers.json differs from cab95; index and all other artifacts identical.
Publication17438 terminal0; proof tmp/arachnid-publication-artifacts-proof.json.
This pass adds Python logic; user must restart appraisal worker. No hostrestart,
livecollection, staging, commit or navigation edits performed.

market_ethereal_inference.py opts in only Arachnid listing evidence using explicit
native-consistent total1855 plusED425. Verifies exact6nativeproperties andelite
Spiderwebbase55..62/0sockets; disjoint ethereal minimum. Missing flag alone is not
false; contradictoryflags, upgraded/wrongbase, invalidrolls/totals and ambiguous
sockets/contents are rejected. Does not alter raw rows or captured-item flags.
trade_evidence validates explicit inference mode; old policies unchanged.

New Arachnid trade qualification:120ED premium/high from8scoped single-item asks,
4independent sellers; lower rolls mid/unresolved (only2complete-facet sellers),
notworthless. Legacy110highoverride superseded. Fixedcasterutility remains.
All embedded row fingerprints independently checked against fullmarketcache.
Research pricing/data/appraisal-arachnid-trade-review-2026-10-02.md; earlier
priority-armor-facet audit supplies exact source rows/native mechanics references.

TDD: missingmodule red,37initialinference tests green;14policy red; expandedfocused
63passed0.88s. Oldselected14Arachnidreportcases correctlyred. Bank now15newcases;
all73stagedArachnid-related reports pass31.25s. Wrongbasebank fixture initially
failed because builder rejects impossibleidentity; moved to captured-facts policy
test. All842policy tests pass129.60s;535maintenance trade tests pass80.53s.
Broadpolicy run exposedpreexisting ProtectorStone baselineexpectation: before
andafter Arachnid it correctly refuses missingEDpair. Test now asserts missing
rejection then verified30/30pair plusoriginal variantchecks. No Protector rulechange.
Ruffcheck/format9files +gitdiffcheckpassed. No code/rule/test edits afterfinalbanklaunch.

All20saved extraction,prices,text identicalold/staged/newselected;
 tmp/arachnid-replay-proof.json. Newreplayauthority tmp/arachnid-selected-replay.json
(42748terminal0). Stagedreplay12255terminal0. Final selectedbank37465 running:
 tmp/arachnid-final-bank.log, alltradechecks plus Arachnid-related cases; writes
 sharedreceipt named-jewelry-trade.json. Preparation44479running:
 tmp/arachnid-prepare.log. Afterbothterminalsuccess run tmp/arachnid-finish.py:
 asserts30existingreviewsaccepted, atomicallywritesmatrix, scope andcompletion.
No Arachnid dedicatedmaintenance registry entry yet; that is the next missing
trade-review proof, not all-item completion. Do notrerun tmp/add-arachnid-trade.py
(one-shot alreadyapplied). Oldcab95 is retained. Allotherhandles terminal.

## Titan native proof finalized — 2026-10-02

All processes terminal. Fresh1496-case report bank43531 exited0 in501.61s;
28802deselected. Dwarf13stale expectations corrected (withdrawn15MDR claim stays
withdrawn), with separate13-case green15.28s.963maintenance/policy tests passed
196.85s; Ruffcheck/format/diffcheck passed. No code/rule/test edits since final
receipt launch. Preparation15735 exited0. Finish66752 exited0: all30registered
trade reviews accepted, matrix atomicallywritten, scope+ordinarycompletion rebuilt.
Scope verified; complete=false,110683required tasks and8319trade qualifications
remain. Goalactive, no blocker streak; every recent turn made concrete progress.
Runtimecab95unchanged; maintenance/test proof only. No livecollection, commit,
staging, workerrestart or navigation edits. Currentreplay tmp/titan-selected-replay.json.
Logs tmp/titan-native-final-bank-green.log, tmp/titan-native-final-maintenance.log,
tmp/titan-native-{finish,matrix,scope,completion}.log. Source proof
 tmp/titan-native-receipt-proof.json. No pending toolhandles; do not rerun one-shot
 tmp/register-titan-review.py. Sharedreceipt named-jewelry-trade.json is current.

Next concrete item: Arachnid Mesh. Read appraisal-priority-armor-facet-audit-2026-10-01.md
and companionJSON: exact native propertylist, scoped rows, defense-based candidate
nonethereal inference, current110ED legacytier concern, boundary/test plan. No
Arachnid code was changed yet. Work offline; evidence limitations on Harlequin,
Griffon and WarTraveler are captured too. Continue every required item;30reviews
is a maintenance milestone, not all-item completion or a sufficient stopping goal.

## Titan verification correction — 2026-10-02

Supersedes pending handles in the next entry. Broad bank15542 exited1:
13failed/1483passed in511.68s. All failures were stale Dwarf Star bank contracts
left behind when the insufficient-seller15MDR qualification was withdrawn.
Updated cases/dwarf_trade.py preserves all13 specimens and now asserts absence
of the trade_qualification field via dirty-equals negated IsPartialDict, and no
Trade lines. This follows the existing source review and policy tests; no runtime
qualification or threshold was restored. Focused13passed15.28s,33657terminal0.
Initial correction expected an empty object rather than omittedfield (13failed);
second used unavailable IsNot (collectionerror); both superseded by green3log.
Ruffcheck/formatpass. Noproduction code changed after963maintenance/policy pass.

Fresh all1496 bank43531 running: tmp/titan-native-final-bank-green.log; receipt
named-jewelry-trade.json remains invalid until this finishes successfully.
Preparation15735terminal0: tmp/titan-native-prepare-green.log. Do not run completion
against the failed receipt. After43531terminal0 run tmp/titan-native-finish.py.
No code/rule/test edits since freshbank launch. New research notes/JSON do not
change verification inputs. Goal active and incomplete; runtimecab95 unchanged.

## Titan native trade proof — 2026-10-01

Goal remains active and unfinished. Dedicated native checker now covers verified
Ceremonial/Matriarchal base codes, paired enhanced damage150–200, leech5–9,
fixed skill/replenishment/utility properties and original190/upgraded200 thresholds.
The shared evaluator accepts an explicitly verified base override; upgraded items
are no longer evaluated using the original code in the maintenance proof.

The full current market census is recomputed, snapshot-bound and fingerprinted:
original premium8rows/4sellers; upgraded6/4; explicit lower/nonethereal cohorts0;
original unknowneth4/4; unknownbase10/7. Unknowns are never reassigned. New sufficient
lower/nonethereal evidence, thin positive cohorts or changed source bytes reopen
review. Scope ethereal_unique_javelin is registered as row29 (30th).

Tests went red21fail/11pass to32pass; source census12pass; native report bank62pass.
The bank adds both ED mismatch directions and jointly illegal shared values perbase.
Trek shares identical ethereal variant constants; other review defaults unchanged.
Ruffcheck and formatcheck pass9affected files. Broader maintenance/policy963passed
196.85s. Final receipt and completion regeneration still pending at time of entry.
Runtime remains cab95c4ef40bdfe2d30f90aeeb942beb0896b3e56b08fc1193d6184080846f94;
this pass changes maintenance/test proofs only. Saved replay authority remains
 tmp/titan-selected-replay.json. No network/staging/commit/restart/navigation edits.

Current handles: finalbank15542 (tmp/titan-native-final-bank.log), maintenance21432
terminal0, preparation42984terminal0. Final bank includes1496trade-check cases
(previous receipt covered1436 before6new Titan cases; now includes older trade
regressions too). After terminalsuccess run tmp/titan-native-finish.py. Preparation
already regenerated bankcoverage, observed, fixed and variable market reviews.
Do not rerun tmp/register-titan-review.py; it has already appended the entry.
No code/rule/test changes since finalreceipt launch.

Next offline refinement: Arachnid Mesh, followed by Griffon/Harlequin/War Traveler
facet gaps. Research appraisal-priority-armor-facet-audit-2026-10-01.{json,md}
records exact scoped rows and native roll axes. Property1855 total defense may
support a tightly bounded nonethereal inference for Arachnid; property399 cannot.
Do not publish a threshold until native definitions, contradictions and report
boundaries are tested. Other cached armor variants retain unknown sockets/ethereal.

## 2026-09-30 — user-approved dormant planner definitions excluded

User approved cutting planner item definitions placed in no profile and linked by no
guide. `planner_source_audit.py` now blanks candidates only for guide/source issues, not
for the one unsupported planner (1r010653, "Profile not found"): 3,820 candidates. New
`maintenance/planner_definition_scope.py` (policy fingerprint) plus `planner_definitions`
approval in `rules/value_scope_reviews.json`; red/green audit tests updated (+2) and 9 new.
Rebuilt audit, bank coverage, jewelry reviews (rows identical), coverage matrix, manifest.
Completion: 7,426 occurrences excluded; source_review 55,149 → 47,723; remaining
110,240 → 102,814; manifest verified; complete=false. 2,481 "Unreferenced definitions"
stay pending (reachable roots or planners with issues). 595 scope/planner tests passed.

## 2026-09-30 — reviewed ordinary starter variants excluded from source review

New `maintenance/starter_scope.py` (in the completion-policy fingerprint) and a `variants`
section in `rules/value_scope_reviews.json`: 21 guide Starter variants reviewed from their
exact `purpose` quotes (wp-a-variants + wp-a-builds mirror), guide HTML and 39 guide-linked
planner profiles with the same name and a title for that build. Retained: Smite Starter
(Uber minimum), Holy Bolt Starter (merc Fanaticism setup), all Budget variants, planners
titled for other builds (Fury Druid, Frost Nova, Freezing Arrow, Blade Assassin) and the
1,008 shared-planner Starter mentions. Only unclaimed occurrences without a retained source
rule are excluded; identities, uses, configurations, tiers, pricing and bank obligations stay.

Red/green `tests/.../maintenance/test_starter_scope.py` (17). Rehashed dependents: item-bank
coverage, fixed/variable jewelry market reviews (`--as-of 2026-09-30`, rows identical),
coverage matrix, scope manifest. Completion: 2,579 occurrences excluded, source_review
57,728 → 55,149, remaining 112,821 → 110,240, manifest verified, complete=false,
migration_status still partial. Scope/completion suites 549 passed; Ruff clean.
One-shot `scratchpad add_starter_reviews.py` refuses to append twice.

Open migration decision: 8,008 candidate-only "Unreferenced definitions" planner rows
(reachability audit 2026-09-27, exclusions_approved=false) need user approval before any
source-only exclusion. A concurrent agent was adding item-bank cases during this run.

## 2026-09-28 — seven Abyss named mercenary socket configurations published

Added exact Abyss Act2Might rules and source links:
104 Shaftstop/Um (fc01065b79 upgraded Boneweave),105 Duriel/Um (80 GreatHauberk),
114 TalCrest/PerfectAmethyst (62),115 Guillaume/15IASjewel (63),116 Gaze/15IAS (65),
118 Stealskull/15IAS (110),119 Kira/Ral (72). Jewel child53 is verified pure15IAS.
Reviewed predicates/physical-bearer semantics reused from established Zeal named
configurations, but separately pinned to Abyss source and Warlock class. Native low
rolls and legal upgrades supported; actual socket content required, unknown fillers
remain unknown, set ethereal rejected. Mana/mana-leech not mercenary priorities.

New `cases/abyss_merc_named.py` uses existing independent native item fixtures with
Abyss-specific expectations: seven scenarios each =49cases. Red49failed; staged49
passed18.29s; selected49passed23.38s. Statbundle2passed9.53s; Ruffclean.
Full dependent+SQLite rebuild, staged20saved replays, publication, selected20replays
completed. All20 report texts and prices match exactly. New selected generation:
`95877b3bba7f895a081804f232397c5c84c070110c951cf1aac79cbffba5567b`
2467profiles/2459statconfigs; bank1923cases/3767targets/3395missingcases.
Completion reviewed1598/excluded4811/rows8066/remaining111873, complete=false.
New rule coverage dimensions still need review; no final-fullsuite/hostdelivery claim.
Logs `tmp/abyss-merc-named-*`; completion67334 exited0; all handles terminal.

Successful one-shots NEVER rerun: `tmp/add_abyss_merc_named.py`,
`tmp/link_abyss_merc_named.py`. Seven table references use guarded
mercenary_table_correction; source reviews now123rows.

Next remaining Abyss table gaps: Chains of Honor108, Undead Crown110, GemmedMask112,
CrownOfThieves117; existing-role source links98–103/106–107/109/111/113/120–121 also
need exact configurations reconciled. Existing roles are often sourced from WP-A
rather than HTML and may constrain a different base/ethereal/socket state:
Treachery existing requires eth MagePlate, table55 is noneth/missingeth; Fortitude
requires eth SacredArmor and table2 is eth superior15def; Andariel table66 includes
jewel67 and existing native-only role does not establish filler coverage. Do not
blindly close them by name. Generic existing-role templates may allow several merc
contexts and need reviewed subset/source association. Missing Meteor planner and
all other item/market/bank/final gates remain open. Goal stays active.

## 2026-09-28 — player-held Insight caster alternative implemented/published

New `abyss-warlock-player-insight-staff`, separate from mercenary role. Exact guide
span13 links x2cpo0l5/item10 Insight Archon Staff; staff has no staffmods. Native
weapons table supplies the nine legal4s staff bases, recipe/runes individually pinned.
Player priorities: Meditation,35FCR,+5attributes,2mana-after-kill,23MF. ED/AR/Critical
Strike are not credited as Abyss spell damage. Native-low rolls, normal/superior/
low-quality supported. Ethereal considered for casting-only use with durability
condition; no universal premium/best-base/equipment-breakpoint claim.

New bank file `cases/abyss_player_insight.py`: nine independently specified native
cases (lowroll,normalBattleStaff,superior,lowquality,ethereal,illegalShortStaff,
unknownclass,wrongclass,empty). Red9failed before implementation; staged17passed
23.53s and selected17passed28.92s including existing eight mercenary cases.
Statbundle2passed; Ruffclean. Source span13 linked via player_equipment review.

Full dependent rebuild + SQLite + staged20replays + publication + selected20replays
completed. All20 report texts/prices identical staged vs selected. New generation:
`33ec0ef27be5457d803e2ce2a1e6e06b015ed18f5677f9c60e561336da4a9fc8`
2460profiles/2452statconfigs; bank1874cases/3760targets/3395missingcases.
Completion: reviewed1591, excluded4811, rows8059, remaining111845, complete=false.
New role has coverage dimensions still needing review; no false all-item closure.
No host restart/fullfinalsuite claim. All handles terminal (completion48389 exited0).
Logs `tmp/abyss-player-insight-*`.

Successful one-shots NEVER rerun: `tmp/add_abyss_player_insight.py`,
`tmp/add_abyss_player_insight_binding.py`. First rebuild failed before publishing
because corroborating weapons/gems references had empty locators. Corrected to
specific base/rune records with refreshed role/use/stat fingerprints, then reran the
repeatable rebuild successfully. Initial script still contains those old locators;
do not use it to recreate the role.

Next: continue remaining source links/configurations (Abyss mercenary table has
other original-player attributions now reviewable with adjacent Might-table guard),
then all-item coverage/pricing/bank obligations. Missing Meteor planner remains
explicit. Reachability audit regenerated and planner note role dependency valid.

## 2026-09-28 — Abyss planner resource notes fully reviewed

Second row in `rules/planner_context_reviews.json`: `abyss-resource-planner-notes`.
Pinned exact gsg0p0l0 notes and four reviewed parts: Bind/Consume demon gameplay
instructions (native Warlock skills381/382), conditional Insight mana alternative
linked to `abyss-warlock-insight-act-2-might`, unspecific potion reminder linked to
implemented ordinary recovery policy, and author signature. No potion tier/quantity
or additional item recommendation is invented. Item definitions/configurations and
market coverage remain independently in scope.

`planner_resource_notes.py` requires exact note text/parts, native skill names/class,
pinned consumables/native evidence, and the exact semantic role fingerprint. It
adds the current role-file hash to audit dependencies without invalidating review
for unrelated roles added to that file; completion detects stale audit snapshots.
New helper included in completion-policy fingerprint. Five new tests plus existing
Valkyrie/audit/completion suites: **84 passed**, Ruff clean. Existing Valkyrie test
fixture now selects its own row instead of assuming all reviews belong to it.

Audit and completion regenerated: no remaining unreviewed notes/nested-equipment
contexts in available planners; missing `1r010653` still blocks source closure and
all unreachable-definition exclusion candidates remain unapproved. Completion
**111828 remaining**, complete=false. No runtime change/publication; selected
008b7a0ed7c3242e15d913ecf5a97639789476c73b26c73865ba0613dfcdf85e unchanged.
Logs `tmp/abyss-resource-notes-{red,tests,audit,completion}.log`.
Completion65812 exited0. Review-row appender succeeded; do not recreate/append twice.

Next independent work: Abyss player Insight alternative span13 (x2cpo0l5/item10)
is distinct from the mercenary role and still needs assessment; also broader pending
source/configuration coverage. Missing Meteor planner remains explicit, not a reason
to stop independent work. No full-final-gate or delivery completion claimed.

## 2026-09-28 — Abyss Insight source references linked

Closed exact guide spans94/95/96 against `abyss-warlock-insight-act-2-might`:
-94: explicit Desert Might mercenary + Insight Giant Thresher narrative, using
existing mercenary_prose_correction; preserve original player/unspecified fields.
-95: early-game table linked fc01065b/item30 = Insight Poleaxe, Ral/Tir/Tal/Sol.
-96: mid-game fc01065b/item88 = eth superior15ED Insight Thresher, total275ED.
Captured perfect rolls are not minimum requirements. Player weapon span13 remains
separate and open, as do planner notes.

New `mercenary_table_correction` kind requires original player/merc-equipment slot,
Warlock/player-class predicate, exact Act2Might predicate and same role slot. Raw
span must be inside the quoted table section. Adjacent previous section must have
exact full wearer quote with explicit Desert Mercenary with Might Aura / Equip him
with grammar, followed by Gear Progression and the exact Early/Mid/End table header.
Helper `mercenary_table_context.py` is in completion-policy fingerprint. No source
attribution rewritten; unrelated/nonadjacent/player-table contexts rejected.

74 affected source-context/policy tests passed in `tmp/abyss-insight-source-tests.log`;
Ruff clean. Completion regenerated: reviewed_occurrences1590, excluded4811,
remaining111829, complete=false. Selected runtime unchanged
008b7a0ed7c3242e15d913ecf5a97639789476c73b26c73865ba0613dfcdf85e.
Completion92559 exited0, log `tmp/abyss-insight-source-completion.log`.

Successful one-shots NEVER rerun:
`tmp/add_abyss_insight_prose_binding.py` (initial index206 error occurred before write,
then corrected94 and succeeded), `tmp/add_abyss_insight_table_binding.py`,
`tmp/add_abyss_insight_mid_table_binding.py`. Source reviews now115rows.
Continue note/configuration links and remaining all-item work; no completion claim.

## 2026-09-28 — Abyss Insight mercenary rule implemented and published

New `abyss-warlock-insight-act-2-might` role + stat review/guide use, sourced to
Abyss section39 (Desert Might mercenary, Insight Giant Thresher for Meditation)
and section40 Insight equipment choices; also pins planner gsg0p0l0 containing mana
notes. Role primary source span95 exact Insight; source date verified from raw HTML
May22,2026. This is a generic legal Act2 polearm alternative, not exact endorsement
of every linked base/roll or a universal best-base assertion. Requires Warlock,
Act2Might, identified completed word, filled4s and legal polearm code. Native low
rolls and normal/superior/low-quality, eth/noneth accepted; Meditation plus physical
mercenary stats highlighted; FCR/Energy/Vitality excluded as merc priorities.

Eight independently specified native item-bank cases in `cases/abyss_insight.py`:
low Partizan, eth GiantThresher, superior, low-quality, illegal-capacity Bardiche,
wrongmerc, unknownmerc, empty sockets. Red8failed before rule; staged8passed14.41s,
selected8passed19.98s. Statbundle2passed; lint clean. Logs `tmp/abyss-insight-*`.
One-shot `tmp/add_abyss_insight_role.py` succeeded: NEVER rerun. Source date was
corrected afterward to verified May22,2026 with role/stat/use fingerprints updated.

Full dependent artifact + SQLite rebuild, staged20saved replays, publication and
selected20replays succeeded. All20 report texts and price estimates exactly match.
New selected generation:
`008b7a0ed7c3242e15d913ecf5a97639789476c73b26c73865ba0613dfcdf85e`
2459profiles/2451statconfigs; bank1865cases/3757targets/3393missingcases.
Retain previous generations. No host restart or finalfullsuite claim.
Sourceaudit and completion regenerated; 111832remaining, complete=false. Increased
queue includes the new role's still-unreviewed coverage dimensions; no false closure.
All tool handles terminal (last completion36323 exit0).

Next: bind exact Abyss Insight occurrences and planner notes to this reviewed role;
notes also mention Bind Cursed Conviction Hephasto/Consume Defiler (skill context)
and potions. Do NOT close notes wholesale from Insight implementation alone. Existing
potion policy is implemented but exact source-note association needs review. Then
continue all other scoped items/source configurations. Missing Meteor planner
remains unresolved; final contract and runtime-delivery gates remain open.

## 2026-09-28 — generated Valkyrie gear context reviewed

Pinned `rules/planner_context_reviews.json` (one row) and added validator
`maintenance/planner_context_reviews.py`. Planner `0w0106ph` /summons/valkyrie
contains inline generated gear, not player/mercenary acquisition recommendations.
Native skills32 calc2 ln56 gives itemLevel109 at skillLevel29; native monequip
rows2–8 exactly match its seven rare equipment slots/bases. Legacy D2MOO SkillAma
summoning → SkillNec passive stats → SkillAss sub_6FCF9580 corroborates generation
on the pet inventory. Legacy code is supporting evidence, native tables and exact
cached summon snapshot are pinned. No broad exclusion of summon/player items.

The audit records the reviewed context and pins review/mechanics hashes in its
source hashes; completion revalidates these. Changed summon, source or mechanics,
unknown kinds, wrong slot/base/quality/itemlevel fail. Reachable definitions remain
retained; no occurrence/identity/market dispositions were removed. Root audit still
has the missing Meteor planner and Abyss meaningful notes. All candidate source
exclusions remain unapproved.

Audit + completion regenerated. Remaining tasks **111,814**, complete=false.
Selected runtime unchanged. Nine new tests; 79 affected tests pass in
`tmp/valkyrie-context-final-tests.log`; Ruff check/format pass. Red log
`tmp/valkyrie-context-red.log`; completion log `tmp/valkyrie-context-completion.log`.
Process83789 exited0. The review JSON creator was successful: do not rerun its
assert-not-exists creation; maintain the existing row normally.

Next: review Abyss planner notes against actual guide roles/configuration and
continue semantic source/item coverage. Missing Meteor exact planner remains a
source gap, not proof that all independent work is blocked. Goal stays active.

## 2026-09-27 — reachability is now a completion prerequisite

`completion.py` consumes `appraisal-planner-reachability.json`, verifies its canonical
inventory fingerprint and on-disk source hashes, and retains all audit issues in the
source-review queue. A real planner inventory without an audit, or an audit omitting
a scoped planner, cannot pass. Audit and graph implementation files are included in
the completion-policy fingerprint; final attestations cannot survive changes.

Latest completion regenerated successfully: **111,815 remaining tasks**, complete=false.
The four additional entries preserve the missing/unsupported `1r010653` source and
the previously untracked Abyss notes and generated Valkyrie gear. No source rows
were excluded. Selected runtime generation unchanged. Audit must be rerun after
any guide inventory rebuild, before completion:
`uv run --offline python -m pricing.knowledge.assessment.maintenance.planner_source_audit`
then `uv run --offline python -m pricing.knowledge.assessment.maintenance.completion`.

Meteor investigation: existing planner `8101064z` item13 is +1 Fire Skills/+45 Life
Grand Charm (ms339/mp442), used by Standard/Ubers/Set/Hardcore profiles. It does NOT
prove the contents of missing planner `1r010653` item13 referenced at guide spans10
and23. General guide prose and exact missing rolls must stay separate; no automatic
replacement performed. Existing planner_source_gaps already retains its 404.

Validation: 70 completion/evidence/policy/reachability tests pass in
`tmp/planner-completion-final-tests.log`; Ruff passes. Red evidence:
`tmp/planner-completion-red.log`, `tmp/planner-audit-omission-red.log`.
Completion log `tmp/planner-audit-completion.log`; process51984 exited0.
Continue reviewing substantive planner notes/extra equipment and semantic source
closure, then the full all-item contract. No goal completion or runtime deployment.

## 2026-09-27 — persistent reachability audit; remaining source gaps retained

Added repeatable `uv run --offline python -m
pricing.knowledge.assessment.maintenance.planner_source_audit`, writing
`pricing/data/appraisal-planner-reachability.json`. It checks inventory-pinned
source hashes and records guide-to-planner item references. Missing/drifted sources,
unresolved guide links and unsupported planner responses suppress all exclusion
candidates. It never approves exclusions or changes item/market coverage.

Resolved the two `crf088#amu` links using cached game-data `crafted.crf088` (Caster
Amulet), independently of numeric planner references. Three exact empty rich-text
editor shells no longer require note review. Regression discovery: planner
`0w0106ph` has generated Valkyrie gear under `/summons/valkyrie/items`; nested
metadata equipment now retains referenced definitions and requires explicit review.
Abyss `gsg0p0l0` still has meaningful Insight/potion notes, retained for review.

Remaining missing planner `1r010653.json` is the cached `Profile not found` response.
Meteor Sorceress guide links item 13, Burning Grand Charm of Vita, in the Flame Rift
replacement paragraph. No existing reviewed_source_issues entry resolves it. Seek
local pinned replacement/source reconciliation; do not assume an unrelated skiller
has the same exact configuration. No exclusions approved; the earlier 4,062/8,008
counts are preliminary diagnostics, not current approved candidates.

Red/green: `tmp/planner-nested-equipment-red.log`,
`tmp/planner-source-audit-red.log`, `tmp/planner-gap-locator-red.log`.
Affected suite: 30 passed (`tmp/planner-source-audit-final-tests.log`), Ruff clean.
Runtime/selected generation unchanged, completion still unfinished. Continue source
closure and all-item contract; do not mark goal complete.

## 2026-09-27 — planner reachability diagnostic (not exclusion approval)

Added `maintenance/planner_reachability.py` and 11 focused tests. Reads all profiles,
player/merc/inventory/cube roots, guide references on any HTML element, and recursive
socket children. Unknown structure, missing numeric definitions, cycles and planner
notes prevent candidate output for that planner. Catalog-only tooltip references
are separated from planner item references. No completion dispositions changed.

`uv run --offline python -m tmp.audit_planner_reachability` produced
`tmp/planner-reachability-audit.json` pinned to inventory/source hashes. Across 114
parsed planners: 4,062 definition candidates. Of 9,907 “Unreferenced definitions”
occurrences, 1,629 actually have reachable roots and MUST stay in review; 8,008 are
candidate-only and 270 remain uncertain. These are diagnostic counts, not approved
source exclusions, and never imply item/market worthlessness.

Outstanding audit questions: `1r010653.json` contains `Profile not found`; two
`crf088#amu` catalog links in Fire Blast guide remain unresolved; four planners have
notes (three empty rich-text shells, Abyss notes include Insight advice). Resolve
these with pinned source review before implementing any source-only exclusions.
Also review root metadata semantics and unknown item-reference forms before treating
this graph as exhaustive. Existing completion ledger remains 111,811 pending,
complete=false; selected generation unchanged. No runtime publication/restart.

Validation: red/green logs `tmp/planner-reachability-red.log`,
`tmp/planner-catalog-links-red.log`; affected build/slot/reachability suite 24 passed
in `tmp/planner-reachability-final-tests.log`; Ruff check/format pass. Continue audit,
then the remaining all-item completion contract; do not mark goal complete.

## Active continuation — Zeal HTML item-reference closure, 2026-09-27

Goal active, complete=false. Closed4 remaining Zeal HTML occurrences: BoneBreak0/27/32,
Butcher2. Current completion ledger has ZERO pending occurrences for source_id
pricing/raw/mr/guides__zeal-paladin.html. This is marked HTML reference closure only,
NOT all Zeal planner configurations or all-item assessment completion.
Source-context review document112rows; rewards11rows. Runtime artifacts unchanged,
selected generation4ffcfe435dcba03980346379deea696bc6c352fe6057f794e323e40756c78738
77artifacts,2458profiles/2450statconfigs. No publication needed for maintenance-only.

New qualified_named_prose validator uses explicit reviewed BoneBreak physical-use
or upgradedButcher instructions, exact unique identity, hard class, role slot and
same rawHTMLsection position. BoneBreak may correct a merc-tagged occurrence only
with explicit Uber paragraph clause; resulting role remains player inventory charm.
Never substitutes Renewed/Latent charm. Butcher requires primary source quote
“Butcher's Pupil (Upgraded)” and exact reviewed upgrade dependency; SmallCrescent
code resolved frommetadata in appender. Primary evidence must support nameduse.
Original occurrence labels/side remain unchanged. Helper named_prose_context.py
added to completion fingerprint/invalidation tests.

10new tests initially red; negative renamedcharm originally hit earlier guide-use
endorsement guard, fixture corrected to reach namedidentity check without relaxing
production validation.69affected source tests pass0.42s;6deliveryweapon runtime tests
pass17.82s. Ruff clean. Logs tmp/named-prose-{red,green,final-tests}.log (earlygreen
log superseded by finaltests), tmp/zeal-final-prose-runtime-tests.log.
Successful ONE-SHOT tmp/add_zeal_remaining_named_prose.py NEVER rerun.
All jobs terminal:18928appender,28954completion,61199runtime tests.
Finalledger tmp/zeal-final-prose-completion.log.
Scope d494da4cfdc08a53f9efbf47fe2d1b476cdfaa7979bd20765f883b0b0eb4f186
Counts {"coverage_rows": 8053, "excluded_occurrences": 4811, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111811, "reviewed_occurrences": 1587}.
Bank1857cases/3754targets/3391missing unchanged. Finalwholebank/fullsuite, pricing
reviews and runtime restart/delivery remain incomplete. No livecollection/hostprobe/
restart/staging/commit. Goal staysactive.

NEXT broaden source/configuration closure beyondZeal. Actual pending source variants:
Unreferenceddefinitions9907, Standard5931, Starter4939, Guidemention4796,
MagicFind3540, Ubers2271, Damage2124, SkillTree1689, SunderCharm1519,
Budget1416, WhiteSkills1232, Mainalternatives1228.
Do NOT blindly exclude Unreferenceddefinitions: audit full planner reference graph,
all profiles/variants, guide inline data-d2planner links (including references from
other guides), and recursive socket children first. Label is extractor output,
not proof of no use. Examples: k4x70lwx/items/87/socketedItems/1 PerfectTopaz;
3q1ia0lw/items/25/socketedItems/2 TalRune. Item identities and other occurrence/
market obligations stay in scope even after a justified source-only exclusion.
CodeGraph explored pricing/knowledge/builds.py: planner_rows tracks used references
through add(), ancestors guards cyclic socket refs; inspect complete profile roots
and unreferenced-definition emission next. Source audit is pending, not a decision.

## Active continuation — rare Zeal axe implemented and published, 2026-09-27

Goal active, complete=false. Implemented previously missing Ethereal Rare Weapon
span59 as zeal-paladin-ethereal-rare-axe. Selected new generation
4ffcfe435dcba03980346379deea696bc6c352fe6057f794e323e40756c78738
77artifacts,2458profiles/2450statconfigs. Retain all older generations.

Reviewed n8010616/item108 and native affixes/weapons/gems: ethereal rareBerserkerAxe,
Mechanist2sockets, Cruel201–300ED, per-leveldamage/AR prefix526(current native name
Trump; planner shorthand fools), SelfRepair402, fixed40IASQuickness169, Slaughter
15–20maxdamage, actual2Lo filled payload. Minimum native rolls accepted;300ED/20max
are preferences. Requires all6captured nativeaffixIDs to avoid mixing superficially
similar stats, plus identified/base/quality/class/eth/socket/actualchild requirements.
Important stats17/18/93/22/218/224/252/141; repair supportive rather than ranking
larger seconds as better. Selfrepair notindestructible; perlevelstats notflat and
full attack/survival/equip setup remains conditional. No numeric price invented.

Initial red missingprofile; first implementation exposed prefix source-row vs native
memory-ID mismatch. Corrected via decoder metadata record-key lookup: prefixIDs
1205/1454/1311 rather than420/669/526. Suffix IDs402/169/201 unchanged. Fixtures
independently specify source rows through native byte builder. Unit test now checks
required predicate truth=true and unmet perfectroll preference, rather than demanding
unconditional matched status despite runtime advisory checks.

12new item-bank cases: native-low/perfectED, missingrepairaffix, unknownaffixes,
noneth/unknowneth, wrong/unknownclass, empty/wrong/unknownfillers, onesocket.
All12passstaged6.46s andselected12.74s;3focused profile/statbundle tests pass13.84s.
Ruff clean. Saved20 reports and prices EXACTLY match staged vs selected (overall
assessment metadata differs by generation as expected). Native/published tier gate
rebuild succeeded; no finalfullsuite/currentwholebank claim.

Successful ONE-SHOT tmp/add_zeal_rare_axe.py NEVER rerun.
Repeatable correction tmp/refine_zeal_rare_axe_affix_ids.py resolves capturedprefixIDs
and updates role fingerprints; no need to rerun now. Existing all previous one-shots
retain prohibition. Addedcasesmodule zeal_rare_weapon.py registered in bankcases.
Statbundle expectedcount2450. Full dependent rebuild via final-charge-routing-
rebuild.py completed (51402), followedbySQLite rebuild(57529), staged tests/replay,
publication(40118), selectedtests(27946)/replay(21981), coverage, completion(39400).
All processes terminal. Source-context reviews108/rewardreviews11 unchanged.

Logs tmp/zeal-rare-axe-{red,green,unit,staged-bank,selected-bank,rebuild,index,
publication,coverage,completion}.log; staged/selected-replay.json. Green earlylog
contains a superseded status-assertion failure; final unit.log is passing evidence.
Bank1857cases/3754targets/3391missing. No livecollection, hostprobe/restart, staging
or commit. Prior Pythonhostrestart/delivery remains unverified; this newrole is data.
Scope 70651b868fd168b9194b259ff736095c1345a5f9fe463fcdb58ae25ef4a15afc
Counts {"coverage_rows": 8053, "excluded_occurrences": 4811, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111815, "reviewed_occurrences": 1583}.

NEXT4Zeal source references: BoneBreak0/27/32 (0/32no plannerID,27wrong mercside),
Butcher2(section32primary upgradedSmallCrescent). Remaining rare/base/price/etc scope
still substantial; completion ledger is authoritative and goal remainsactive.

## Active continuation — socket component source references, 2026-09-27

Goal active, complete=false. Closed11Zeal socket filler references:74/76/78/89/91/
93/95/108/110/111/112. Source-context reviews now108. Runtime artifacts unchanged;
no publication needed. Selected generation remains
b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc.

New maintenance socket_component_reference kind binds a filler to the reviewed
parent assembly quote instead of treating a rune/jewel as independently worn gear.
Helper socket_component_context.py checks role endorsement/fingerprint via shared
compiler, hard player class/slot, parent named identity or reviewed typed pattern,
exact assembly quote in role source, source cache/raw HTML hash/section position.
It independently parses raw span positions, requires the parent to be first item
inside same br/td/li/p-delimited HTML entry and exact normalized entry text. Adjacent
entries, wrongparent/index/count/class/role/review rejected. Preserves raw filler
occurrence. Helper included in completion policy fingerprint/invalidation test.

Linked reviewed completed 4Ruby/4Ist magic shields, 3IstGriswold, Cham/Ruby/Um/Ber
Guillaume, 3PerfectTopazMask and RalOrtThulMask. Empty preparation roles not used.
Runtime stat configurations already require actual child payloads, not parentstats.
Rechecked tests for missing/wrong/duplicate child payload, ED/IAS Ruby threshold,
wrongwearer/ethereal and wrongbase. No new price or roll assumptions.

8new source-link tests red→green;61affected tests pass37.49s, including runtime
sockethelm/specialistshield tests. Ruff clean. Logs tmp/socket-component-{red,green}.log,
tmp/zeal-socket-component-tests.log. Actual11data links compiled against rawHTML.
Successful ONE-SHOT tmp/add_zeal_socket_component_reviews.py NEVER rerun.
All jobs terminal:52153appender,75957tests,43634completion.
Completion log tmp/zeal-socket-component-completion.log.
Scope c5c7bd15aaa3218a80622af26714ca3a3cbf5011af0da283956e4d17526f4be5
Counts {"coverage_rows": 8052, "excluded_occurrences": 4811, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111811, "reviewed_occurrences": 1582}.
Bank1845cases/3753targets/3391missing unchanged. Finalwholebank/fullsuite, market
reviews and hostrestart/delivery remain unfinished. No livecollection/probe/restart/
staging/commit. Keep goal active.

NEXT5Zeal references: BoneBreak0/27/32 (0/32no plannerID,27wrong mercside),
Butcher2(section32primary upgradedSmallCrescent), EthRareWeapon59. Then continue
all other builds/families and completion-contract dimensions. Existing source-only
review counts do not establish completed runtime/market/item-bank coverage.

## Active continuation — boss farming targets, 2026-09-27

Goal active, complete=false. Closed3source-only farming-target occurrences:
Zeal37 HellfireTorch and38KeyofDestruction(section30); DreamPaladin44HellfireTorch
(section29). Reward review document now11rows. Source-context reviews97unchanged.
No runtime artifact/publication change; selected remains
b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc.

reward_mentions farming_target grammar now also permits explicit “defeating the
Uber Bosses and acquiring a Hellfire Torch” and Nihlathak “farming this Boss for
the Key of Destruction”. Context still exact uniqueTorch/miscKey, original name,
player/unspecified demand/GuideMention; raw HTML source position and hashes verified.
New guard requires only one occurrence of the item label in the evidence section,
so a mixed equip+farm paragraph cannot exclude an equipment mention by nearbytext.
Item identities, pricing and other equipment/inventory uses remain in scope.

Red-green tests add2positive and5negative scenarios: equip instruction, wrongitem
farming language, wrongcategory, repeatedequip/farmTorch and wrongboss.67affected
reward/completion/dependency tests pass0.25s; Ruff clean. Logs tmp/farming-prose-
{red,green}.log and tmp/boss-farming-final-tests.log. No new runtime or market claim.

Successful ONE-SHOT tmp/add_reviewed_boss_farming_targets.py NEVER rerun.
All jobs terminal:45950appender,57768completion. Final completion log
 tmp/boss-farming-completion.log.
Scope 8999eb163de32cb237f3b0e7c08c199c9201f94c9adfd7743208394d1565920f
Counts {"coverage_rows": 8052, "excluded_occurrences": 4811, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111822, "reviewed_occurrences": 1571}.
Bank1845cases/3753targets/3391missing unchanged. Finalwholebank/fullsuite, market
reviews and hostrestart/delivery remain unfinished. No livecollection/probe/restart/
staging/commit. Goal remains active, not complete.

NEXT16Zeal references: BoneBreak0/27/32 (0/32no plannerID,27wrong mercside);
Butcher2(section32primary upgradedSmallCrescent); EthRareWeapon59;
socketfillers74/76/78/89/91/93/95/108/110/111/112. Existing literal farming patterns
were scanned acrossall cachedguides; onlyDream29 andZeal30 new matches. Do not
exclude other farming prose without review. Continue source closure and all other
completion-contract dimensions afterZeal.

## Active continuation — mercenary support and two player repeats, 2026-09-27

Goal active, complete=false. Closed8Zeal references: mercenary support28/29/30/31/33/34,
Enigma1 and StandardBoneBreak10. Source-context reviews now97. No runtime artifacts
changed/publication needed; selected generation remains
b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc.

Added mercenary_support_reference review kind and narrow explicit grammar in
mercenary_source_context.py: “Mercenary to apply Decrepify from his The Reaper’s Toll
or Lawbringers” or “Use a Mercenary with ... for Decrepify”. Preserves original
player/unspecified labels; binds only reviewed merc Weapon configurations with
hard class/mercenary constraints, exact identity/quality/fingerprint and actual
raw-HTML section position. Names alone, wrong wearer/slot/class/merc or optional
mercenary condition rejected. Existing correction grammar unchanged. Helper already
part of completion policy fingerprint.11new tests red→green;75affected tests pass
6.46s (tmp/zeal-merc-support-tests.log). Ruff clean.

Source review: n8010616 Reaper21 repeats ruby role; independently inspected
dc01061x Reaper1 socketchild2: magic15IAS/40ED jewel, ethereal Reaper, same reviewed
filled configuration. Lawbringers n8010616/item174 PhaseBlade and dc01061x/item119
ethereal superiorCrypticSword both legal1H; preserve per-weapon and actual dual
mercenary-equipment requirements via existing two roles. No second weapon assumed
from one capture, no persistent proc or guaranteed immunity-removal claim.
Player exact-planner links preserve Enigma as alternative to Charge/Vigor and
BoneBreak original charm penalty/level/active-inventory context.

Successful ONE-SHOT appenders NEVER rerun:
- tmp/add_zeal_mobility_charm_repeats.py
- tmp/add_zeal_merc_support_references.py
Jobs all terminal:92931/9604appenders,69850tests,50086completion.
Final ledger log tmp/zeal-merc-support-completion.log.
Scope 1bdc5d2d5cc382fda5f1e9ec0c006aac07a5642eb3be7a6f7d70b7c18dd09ecb
Counts {"coverage_rows": 8052, "excluded_occurrences": 4808, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111825, "reviewed_occurrences": 1571}.
Bank1845cases/3753targets/3391missing unchanged. Final wholebank/fullsuite, pricing
reviews and runtime delivery remain pending. No live collection/hostprobe/restart/
staging/commit. Do not mark goal complete.

NEXT18Zeal references:
BoneBreak0/27/32 (0/32no planner ID,27 wrongly merc-tagged; original role is exact
item195 n8010616/item175); Butcher2; EthRareWeapon59; socket fillers74/76/78/89/91/
93/95/108/110/111/112; farmingTorch37 andDestructionKey38.
Section30 exact farming evidence read: Ubers paragraph “defeating the Uber Bosses
and acquiring a Hellfire Torch”; Nihlathak paragraph “farming this Boss for the
Key of Destruction”. These are farming-target occurrences, not equipped-item uses;
reward_mentions existing farming_target grammar currently covers only Summary275.
Any extension must preserve identity/source position and not exclude actual
inventory/equipment demand or item pricing review. Continue beyondZeal through all
remaining completion-contract scope.

## Active continuation — validated player prebuff/swap references, 2026-09-27

Goal active, complete=false. Added12 Zeal source links: DemonLimb20/45/47/86,
Treachery21/44/46/121, Wizardspike48/82, Naj50/83. Source-context reviews now89.
No runtime artifacts changed/publication needed. Selected generation remains
b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc.

New maintenance player_utility_reference kind validates a finite explicit-use grammar
in player_utility_context.py: Enchant prebuff, Fade prebuff, conditional Wizardspike
casting swap, or Naj Teleport only without Enigma. Requires exact original occurrence,
class, supported original slot, named identity/quality, player role slot, nonempty
review, same-guide/cache source, actual raw HTML section position, endorsed role and
fingerprint. Both occurrence evidence and primary role section quotes must support
that specific use. Existing exact-planner repeat rules remain unchanged. Prebuff
not added to ordinary PLAYER_SLOTS. No promotion of shared mercTreachery item29 to
player combat armor. Primary source could be section32 rather than an item span.

Red-green test: initially four positive utility-link cases failed unsupported kind;
implementation passed except Treachery fixture initially lacked runeword predicate.
Fixture corrected to represent an actual completed recipe, preserving quality guard.
12utility tests cover4uses and8rejections (combat slot, merc, purpose, class, missing
review, name only, wrong section, wrong primary). Helper included in completion
policy fingerprint with invalidation test.

Added15 independent full-pipeline item-bank cases for previously unbanked Wizardspike
casting swap and Treachery Fade prebuff. Positive, wrong/unknownclass, ethereal/
unknownethereal, missingstat, and Treachery empty/wrongsockets/unknownrecipe. Treachery
IAS/FHR/coldres not credited to prebuff stat configuration. All15 passed selected
(17.43s), log tmp/zeal-utility-new-bank.log.63affected tests pass4.25s,
tmp/zeal-utility-references-tests.log. Ruff clean. Full final suite/bank remain pending.
Bank1845cases/3753targets/3391targets missing; regenerated coverage.

Successful one-shot tmp/add_zeal_utility_role_references.py NEVER rerun.
All jobs terminal:53785 appender,7187 bank,57406 affectedtests,47101 completion.
Final completion log tmp/zeal-utility-final-completion.log.
Scope 355622a9179bc25dfdc3106d4453e6982b920a66d83faf5b316f41a14adc923b
Counts {"coverage_rows": 8052, "excluded_occurrences": 4808, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111833, "reviewed_occurrences": 1563}.
No live market activity/host probe/restart/staging/commit. Runtime delivery unverified.

NEXT26Zeal occurrences:
BoneBreak0/10/27/32 (27wrong merc side); Enigma1 inverse mobility advice; Butcher2
upgraded weapon with section32 primary; Reaper28/30/33 and Lawbringers29/31/34
misattributed player prose about merc support; Torch37/DestructionKey38 farming;
EthRareWeapon59; socket fillers74/76/78/89/91/93/95/108/110/111/112. Review exact
source meanings and preserve unknown/conditional facets. Continue beyond Zeal through
all remaining completion-contract families, dimensions and pricing dispositions.

## Active continuation — Standard/Ubers mercenary source links, 2026-09-27

Goal active, complete=false. Closed six exact Zeal guide occurrences:11/13/24/26
Reaper/Guillaume and12/25 Fortitude. Source-context reviews now77 rows. No runtime
artifact changes or publication; selected generation remains
b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc.

Reaper and Guillaume reference identical reviewed planner items (ED/IAS jewel and
Cham respectively). Preserved conditional proc/support and unreliable Uber merc
survival. Fortitude n8010616/item57 versus sj01061l/item21 explicitly compared:
same ethereal Sacred Armor/recipe/socket contents/word rolls, normal versus15%
superior defense. Existing role accepts both; superior and perfect rolls remain
preferences. No new price assertion. Appenders validate actual raw HTML section
positions; exact source cache and profile fingerprints validated by compiler.

Successful one-shot appenders NEVER rerun:
- tmp/add_zeal_standard_uber_merc_repeats.py
- tmp/add_zeal_standard_uber_fortitude_repeats.py

36 source-context regression tests pass;14 selected-generation Fortitude bank
cases pass (16.92s), covering low/superior, wrong/unknown wearer, sockets, ethereal,
and different base. Log tmp/zeal-standard-uber-fortitude-bank.log.
Final completion rebuild exited0: tmp/zeal-standard-uber-final-completion.log.
Counts: {"coverage_rows": 8052, "excluded_occurrences": 4808, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111845, "reviewed_occurrences": 1551}.
All jobs terminal (40488/13928 appenders,21463 bank,60148 completion).
No live collection, host restart/probe, staging or commit. Overall final full suite,
whole final bank, pricing evidence dispositions and runtime delivery remain pending.

NEXT38 Zeal occurrences remain. Prebuffs20/21/44–47/86/121 and swaps48/50/82/83
need source-context handling: existing Demon Limb, Treachery prebuff, Wizardspike,
Naj roles use section32 as primary source, so strict player_prose_repeat (requires
primary planner span) cannot be used unchanged. Prebuff is also intentionally not
in PLAYER_SLOTS. Add narrow tested semantic binding preserving temporary buff use,
charges/recharge/remaining buffs versus combat items; do not reuse mercTreachery
because planner item29 is shared. Butcher span2 also has section32 primary role.
BoneBreak0/10/27/32, corrected merc prose28–34, farming37/38 and fillers remain.

## Active continuation — early player and charged-pattern prose, 2026-09-27

Goal active, complete=false. Previous turn made source-review progress; this turn
adds21 exact source links. Selected generation remains
b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc
77artifacts,2457profiles/2449statconfigs. No runtime changes/publication/live activity,
staging or commit. Worker restart/delivery remains unverified. All jobs terminal:
60532namedappender,31467chargeappender,52560finaltests/completion. No known live process.

Fifteen named player prose repeats reviewed through the existing strict exact-planner
binding: spans3,15,16,17,18,22,23,35,36,39,41,42,43,49,53. Review reasons distinguish
Starter UnbendingWill, Uber Fortitude/CoH mobility tradeoff, conditional LifeTap,
Thundergod full lightning setup, LastWish proc/IAS limits, CTA buff swap versus FCR,
Enigma Teleport versus casting swap, Phoenix conditional corpse redemption, and
footnote alternatives. Same referenced planner item, source section and class are
verified; no new runtime threshold or price claim introduced.

New player_pattern_prose_repeat kind supports source labels differing from an
endorsed pattern label, but only for the SAME nonempty planner profile+item IDs.
Requires unresolved pattern occurrence, unnamed typed/quality-scoped role, exact
source_label, endorsed pattern_label, qualities, class, fingerprint and raw HTML
position inside the quoted section. Existing named/pattern validators unchanged
outside this additional kind. Rejected wrong alias, endorsement, qualities, class
or named role. An initial negative test saw the earlier guide-use rejection; its
fixture was corrected to reach the source-context guard without weakening checks.

Six charge prose links:4TeleportChargeStaff,14TeleportChargesAmulet,
19LifeTapChargesWand,40LifeTapChargeWand,51StaffofTeleportation,52TeleportChargeAmulet.
Existing rules preserve remaining charges, ethereal recharge limits, no-Enigma
context, and missing alternative LifeTap sources. Span14 is specifically the same
caster-crafted planner amulet; does not generalize craft bonuses to all amulets.
Source-context review document now71rows. No existing item configuration changed.

109 affected tests pass(0.33s), lint/format clean. Logs tmp/pattern-prose-repeat-
{red,green}.log and tmp/zeal-early-prose-final-{tests,completion}.log.
Successful ONE-SHOT scripts NEVER rerun:
tmp/add_zeal_early_player_repeats.py
tmp/add_zeal_charge_prose_reviews.py
All preceding successful one-shots retain the same restriction.

Completion scope 13d5c26907eebd0a6162a93ffedcee976ecb839a4d9467d8cb0ccce77fa9b880
Counts {"coverage_rows": 8052, "excluded_occurrences": 4808, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111851, "reviewed_occurrences": 1545}.
Bank1830cases/3753targets/3393missing unchanged; whole final suite/current entire bank,
actual market evidence dispositions and runtime delivery remain unfinished.

NEXT44 Zeal guide occurrences remain. Important groups:
- BoneBreak0/10/27/32: player inventory charm;27misattributed merc by section heading.
  Existingrole zeal-paladin-bone-break-gear-inventory-charm; original versusLatent/
  Renewed identity and player level75/physical resistance penalty remain important.
- Standard/Uber merc11–13/24–26, plus misattributed Reaper/Lawbringer prose28–34.
- Treachery/DemonLimb prebuffs20/21/44–47 and table121/86. Existing
  zeal-paladin-treachery-fade-prebuff correctly requires triggering Fade and changing
  back; armor IAS/FHR/coldres do not persist. Do not bind to mercTreachery just because
  the planner item is reused. DemonLimb charge availability/recharge needs review.
- Named swaps48/50/82/83, genericEthRareWeapon59, filler references and farming37/38.
Continue these and all other completion-contract scope, including consumable identity
and offline market reviews; source closure alone is not all-item assessment completion.

## Active continuation — repeated player prose and Torch farming, 2026-09-27

All-item goal active, incomplete. Previous132utility source bindings were progress;
this turn closes3 exact player prose repetitions and1 farming-target occurrence.
Selected generation unchanged b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc,
77artifacts,2457profiles/2449statconfigs. No runtime changes/publication/live probes/
collection/staging/commit. Host Python restart/delivery remains unverified.
All tasks terminal (playerappender45398, Torch4955, finalchain57879); no live job.

source_context_reviews.py newkind player_prose_repeat requires original player /
unspecified slot, explicit class requirement and real equipment slot on endorsed
role, exact profile fingerprint, same source/hash and SAME nonempty planner profile
and item IDs as the reviewed primary span. Same-name alone is rejected. Raw HTML
position must place the repeated span inside its quoted section. Original records
remain unchanged. Closed Zeal249Enigma(section46),273Oath and274Shaftstop(section53).
Enigma48FCR is a complete casting-swap target, not an armor stat. Oath is the same
planner ethereal CrypticSword, not an inference that all Oath bases are optimal.
Shaftstop is player armor, not the separate mercenary Um setup. No runtime rule
or stat-priority changes were needed; existing rules preserve these distinctions.

Shared position validation moved to maintenance/guide_positions.py, including
PositionedMentions. Utility and Hardcore validators reuse it; completion fingerprints
it. Initial import-cycle during extraction was fixed by moving the parser out of
hardcore_mentions, so guide_positions depends only on builds._Mentions. All tests green.

reward_mentions.py now has narrowly reviewed farming_target kind for the explicit
Farm Hellfire Torches summary instruction. Requires uniqueTorch, player/unspecified,
exact instruction and raw span within quoted section. Closes Zeal275 only; identity,
market and all equipped Torch use remain scoped. Equipment or ambiguous prose rejects.
Source-context rows50; reward rows8; utility rows132 unchanged.

154 affected regression tests passed(0.38s); lint/format clean.
Logs tmp/player-prose-repeat-{red,green}.log, tmp/farming-target-{red,green}.log,
tmp/zeal-prose-final-{tests,completion}.log. No full final suite claim.
Successful one-shot appenders NEVER rerun:
tmp/add_zeal_player_prose_reviews.py
tmp/add_zeal_torch_farming_review.py
All previous successful one-shots retain that rule.

Completion scope 6c4e0f44dcec4485494245caaded447b3a2ef419469964f44e723b3f1113ce03; counts {"coverage_rows": 8052, "excluded_occurrences": 4808, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111872, "reviewed_occurrences": 1524}.
Bank1830cases/3753targets/3393missing remains unchanged. Complete=false.

NEXT actual queue audit:65 Zeal guide occurrences still pending, including early
prose0–53, staff-charge/prebuff/swaps, filler references, genericEthRareWeapon59,
Treachery121 and named swap82/83/86. The new repeated-planner guard can safely reuse
reviewed rules only where source contexts/configurations truly agree; mercenary,
prebuff, negative/proc-conflict and farming advice still require separate reviews.
Beyond Zeal, source_review56571 tasks remain (before any later edits), including
9907 demand occurrences marked Unreferenced definitions. Audit their actual source
reference graphs before considering source-only exclusions; the label alone is NOT
proof and identities/other uses remain scoped. Do not hide missing source parsing.
Other large queues include market8052, report8052, stat_annotations8052, leveling7351.
Continue reusable family rules and exact source links, preserving every final gate.

## Active continuation — shared potion-use source closure, 2026-09-27

Goal active and incomplete. Previous potion expansion was progress. This turn closes
132 exact source uses across33 guides without marking their item/market work complete.
Selected generation unchanged: b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc
77 artifacts,2457profiles/2449statconfigs. No runtime code/artifacts changed here;
no new publication, host restart/probe, live market collection, staging or commit.
No known live processes; final completion chain28842 finished successfully.

New maintenance/utility_source_reviews.py and rules/utility_reviews.json:
- Exact expected occurrence, cache hash/span, same-guide quote, native definition
  hash/code/name, reviewed recipient and item-bank target checked.
- Utility bindings are distinct from equipped roles and preserve raw evidence.
- First4 Zeal spans245–248 individually linked to healing/thawing/antidote policy.
- The identical mercenary-care paragraph occurs in27 guides (108 occurrences).
  Its104 additional exact links reuse the reviewed policy but retain all provenance.
- Six more guides (Strafe,DragonTalon,and4Warlock) were extracted player/unspecified.
  Their24 bindings require explicit recipient_correction and exact feed-mercenary
  or mercenary-resistance wording. Strafe's small prose variant was reviewed.
- Crucially, raw HTML hash and original span position must place each occurrence
  inside the quoted section. Same-name mentions elsewhere cannot borrow its quote.
  PositionedMentions reuses the inventory extractor; raw/cached span sequences agree.
  This stronger check passed all132 actual rows, not just synthetic fixtures.

Completion now reads/pins utility_reviews and records utility_dispositions. Its scope
fingerprint includes the review document, validator and consumable policy code.
Conflicting reviewed/excluded source dispositions fail. Item market dimensions,
other source uses and final bank/delivery checks stay independent.
Red/green tests cover identity/recipient/native/cache/source/position conflicts,
changed raw HTML, preserved original attribution and narrow closure semantics.
113 final affected tests pass(0.24s), lint/format clean. Logs:
tmp/utility-context-final-tests.log, tmp/utility-position-completion.log,
tmp/utility-{context,attribution,position}-{red,green}.log.

Successful one-shot appenders, NEVER rerun:
tmp/add_zeal_utility_reviews.py
tmp/add_shared_mercenary_potion_reviews.py
tmp/add_corrected_mercenary_potion_reviews.py
All preceding successful one-shot appenders also remain NEVER-rerun.

Completion scope 4ea6ed0e15743ce14c104a7c9e7bb849aaba5a4df08e1677cde65fa44125e62f
Counts {"coverage_rows": 8052, "excluded_occurrences": 4807, "identities": 2570, "occurrences": 62891, "remaining_tasks": 111876, "reviewed_occurrences": 1521}; complete=false.
Bank remains1830cases/3753targets/3393missing. Whole final suite/current entire bank
and runtime delivery remain unverified. Do not claim completion or new price coverage.

Read-only offline Full Rejuvenation lookup retained in
 tmp/full-rejuvenation-market-lookup.json: known native/trade catalog identity,
zero normalized market observations. This is NOT a completed raw-cache/evidence
review or a zero-value verdict; no pricing disposition was forged from the miss.
NEXT: Zeal249 Enigma FCR-swap prose and273Oath/274Shaftstop summary advice remain
scoped;275Torch farming-summary prose needs precise disposition. Continue all-item
identity/variant/stat/pricing closure, including consumable identity dimensions and
actual offline market-evidence review, then all remaining contract gates.

## Active continuation — all ordinary potion types, 2026-09-27

Goal remains active and incomplete. Prior turn was progress (new consumable policy,
rendering and selected tests); this turn extends it to all15 reviewed ordinary
potions: five healing, five mana, two rejuvenation, Thawing, Antidote and Stamina.
Selected generation remains b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc
(77 artifacts); required native misc artifact unchanged, so no redundant publication.
Python worker restart/delivery remains unverified. No known live processes remain.

policies/consumables.py now exports REVIEWED_CODES and separates recipient effects.
Mana restores over time for player use; do not suggest mercenary mana recovery.
Rejuvenation instantly restores35% or100% of max life/mana, useful for player or
mercenary emergency healing. Stamina restores stamina and increases recovery for
30seconds, useful for player travel/early leveling; repeated doses extend duration.
Super Healing/Mana text explicitly identifies the highest ordinary grade.
Existing invalid-facet, exact-unit, mode and identity comparison guards apply.

Evidence: pinned native misc codes mp1–mp5, rvs/rvl, vps were verified locally.
Native itemtypes rpot Equiv1=hpot/Equiv2=mpot establishes mercenary healing eligibility.
D2MOO SkillItem.cpp pSpell03/pSpell05/pSpell09 and PlrMsg.cpp cursor potion branch
were inspected; these are legacy implementation corroboration, not new live probes.
The native frozen RotW data remains authoritative. No reference checkout modified.

Red8missingutility tests -> green.69 focused policy+staged bank tests passed;
45 selected potion bank cases passed (22.19s). After highest-grade wording refinement,
6 selected Super Healing/Mana cases passed again. Lint/format clean for5touchedfiles.
Bank1830cases/3753targets/3393missing. Existing20saved replay equivalence from prior
turn remains valid for unchanged non-potion behavior; not claimed as a new replay.
Logs tmp/potion-tail-{red,green,selected,coverage,completion}.log and
 tmp/potion-super-grade-selected.log. No market data or numerical prices invented.
Completion scope 50aaf62eb66bef124e86f94dc32ca49fc21fd775682cdd00fa1efb7230e8483b; counts {"coverage_rows": 8052, "excluded_occurrences": 4807, "identities": 2570, "occurrences": 62891, "remaining_tasks": 112008, "reviewed_occurrences": 1389}.
Complete=false; no source or pricing disposition was silently marked reviewed.

NEXT remains explicit utility-source binding for Zeal spans245/246HealingPotion,
247ThawingPotion,248AntidotePotion. They need a utility review mechanism distinct
from equipped build profiles, with exact source/occurrence/hash and applicable
policy identity checks plus positive/near-miss/unknown bank evidence. Then review
offline market evidence/dispositions and other utility families, preserving scope.
Zeal249 Enigma,273Oath/274Shaftstop,275Torch prose and the full contract remain queued.
All earlier successful one-shot appenders remain NEVER-rerun.

## Active continuation — first consumable family published, 2026-09-27

Goal active, completion false. Prior source-review turn made progress. This turn
adds executable potion assessment, comparison policy, rendered utility and native
item-bank cases. Selected generation:
b86ed99afc44c040a10b459f53a2502d8144df3cb09107a0f1681226d90a29fc
77 artifacts; unchanged 2457 profiles / 2449 stat configurations. Publication82269
and selected verification/completion chain50044 are finished; no known live job.

New policies/consumables.py uses the hash-pinned native misc.json from the published
artifact snapshot. Seven reviewed identities: all five healing grades, Thawing and
Antidote. Healing is life over time, recipient-dependent, not instant rejuvenation.
Thawing/Antidote: +50 resistance / +10 maximum resistance for30 seconds, remove
cold/freeze or poison. Player/mercenary use and fixed-roll/no socket premium advice
is shown in a new Consumable use section. Typed AssessmentResult.utility is frozen
and projected only when applicable, so other item reports remain unchanged.
Native spell implementation checked locally in D2MOO SkillItem.cpp (pSpell03 and
pSpell09_AntidoteThawingPotion); live reference checkouts were not changed/executed.

Registry routes hpot/apot/wpot to a separate consumable contract. Reviewed ordinary
potions require normal, noneth,0s/empty, complete identified capture and no modifiers,
runeword or socket children. Invalid/unknown input retains review status and no
contract. Exact comparisons require grade/base identity, mode, unit and properties;
no bulk or NPC-gold-to-Ist estimates. Synthetic tests establish matching behavior,
not actual potion market prices. Other consumables remain unreviewed, not worthless.

Tests: 158 affected regression tests pass; 27 staged bank/coverage tests pass,
including21 new independent positive/negative/unknown cases. All21 pass selected.
Bank1806 cases /3745 targets /3393 targets still missing cases. Native potion
identity targets are now tracked explicitly. All20 saved report texts and prices
match staging AND prior selected output. Lint/format clean for all15 touched files.
Logs tmp/consumables-{red,green,regression,bank-staged,bank-selected,publication,
staged-replay,selected-replay,completion}.*. No staging/commit/live collection/probe.
Host worker restart needed for these Python changes and remains unverified.

Completion scope e670f2e3ef614f3654e526ca88fd234b9a042f3f491f8a00ec26ca9f562888e9
Counts {"coverage_rows": 8052, "excluded_occurrences": 4807, "identities": 2570, "occurrences": 62891, "remaining_tasks": 112008, "reviewed_occurrences": 1389}.
Source occurrences245/246/247/248 remain pending: implementing utility does NOT
silently mark source/context or price-evidence review complete. No new source
appender ran this turn. Prior successful one-shot appenders remain NEVER-rerun.

NEXT: explicitly link/review Zeal healing/thawing/antidote mercenary prose against
this utility policy and bank cases; preserve the distinction from equipped roles.
Then extend to native mana/rejuvenation/stamina (not yet supported), review actual
offline potion market evidence/dispositions, and continue Zeal249 Enigma casting
prose/273 Oath/274 Shaftstop summary and275 farming Torch. Broad all-item scope,
full final suite/current whole bank and runtime delivery remain unfinished.

## Active continuation — mercenary context and Hardcore prose, 2026-09-27

The all-item goal remains active and incomplete. Previous turn was progress:
selected Sacred Rondache replay and four tests verified its Spirit/resistance/socket
advice; host Python restart/delivery remains unverified.

Current selected generation remains
45a7746e47b4b3682194aa8bd682ee6c6540f4afc68ac357f211b8dedff2e1d3
(76 artifacts; 2457 profiles / 2449 stat configurations). No runtime artifact
changes in this continuation; no publication, live collection, host probes,
restart, staging or commit. No known running process remains.

Source-context reviews now contain 47 rows:
- Cure span241 explicitly selects Act2Might from the existing role allowing
  Act2Might/Act5Frenzy. A source binding can narrow that set only by declaring the
  exact full role set separately; unsupported or stale sets fail validation.
- Reaper span206 is bound to zeal-paladin-reapers-general using section43's
  explicit Desert Mercenary/Might and Equip him wording. Original extracted
  player/unspecified evidence is preserved. New mercenary_prose_correction kind
  requires exact class, Might context, Weapon slot and configuration review.
- Insight span208 is bound to zeal-paladin-insight-act-2-might. The early table's
  Act5 alternative cannot equip this polearm. Existing legal-base/native-low-roll
  rule is reused, with no perfect planner thresholds added.

New maintenance/hardcore_mentions.py and rules/hardcore_reviews.json record 23
reviewed Zeal Hardcore Gear Changes occurrences, spans250–272. Raw HTML hash,
cache hash, exact span and occurrence, original HTML position and explicit
Hardcore-to-Summary bounds are validated. The inventory extractor is reused with
positions; raw and unescaped mention sequences must agree, while positions come
from original HTML to handle entities correctly. Summary cannot be swallowed by
widened bounds. This excludes source occurrences only, never their item identities,
prices or separate Softcore uses. Spans249 and273–275 explicitly remain in scope.
Completion reads/pins this document and fingerprints its validation helper. Tests
prove item market work and adjacent same-name Softcore mentions remain pending.

Red/green checks: 136 final affected tests passed (0.26s), lint clean.
Logs: tmp/zeal-context-final-tests.log, tmp/zeal-context-final-completion.log,
tmp/hardcore-{mentions,completion,position}-*.log.
Completion scope: 8dfa93b1d7247fae89de5b17bf536a79bfde7299d2e2c532fc994fdea58e7a97
2570 identities, 62891 occurrences, 1389 reviewed, 4807 excluded, 8052 coverage rows,
112008 remaining tasks. Complete=false. These are source-review gains, not new
numerical-price coverage. Final full suite/current whole bank/runtime delivery
still required by COMPLETION_CONTRACT.md.

Successful ONE-SHOT appenders, NEVER rerun:
tmp/add_zeal_cure_mid_binding.py
tmp/add_zeal_reapers_prose_binding.py
tmp/add_zeal_insight_table_binding.py
tmp/add_zeal_hardcore_prose_reviews.py
The Hardcore appender initially failed before writing because entity unescaping
changes offsets; after the tested original-position fix it succeeded.

NEXT: Zeal spans245/246 Healing Potion,247 Thawing Potion,248 Antidote Potion are
real mercenary utility advice, not reward exclusions. Implement/review this family
and its item-bank cases. Span249 Enigma FCR-swap prose and273 Oath/274 Shaftstop
summary advice remain scoped;275 Torch is farming-summary prose, requiring its
own evidence-backed disposition. Then continue all remaining contract work.

## Active continuation — completed armor words and reward reviews, 2026-09-27

Selectedgeneration45a7746e47b4b3682194aa8bd682ee6c6540f4afc68ac357f211b8dedff2e1d3,
76artifacts,2457profiles/2449statconfigs. Chain59070 FINISHED; finalbankchain26318
FINISHED; rewardcompletion4801 FINISHED. No live workers. All-item goalACTIVE/FALSE.

Five new source-specific completed armor examples in maintenance/zeal_merc_words.py:
zeal-paladin-merc-word-{treachery-mid,treachery-end,duress-mid,duress-end,fortitude-end}.
Exact linked bases: GreatHauberk/ArchonPlate/GreatHauberk/GreatHauberk/SacredArmor;
allAct2Might/Paladin, normal/superior, actual completedrecipe/filledcount/legalarmor.
Endexamplesrequireethereal; superior/perfectED is preference, not minimum. Other
legalbases are not declared worthless; existing generic utility/profile rules remain.
Top-levelbase_codes prevent irrelevant example recommendations on other legalbases.
NativeTreacheryVenom/Fade,DuressShaelFHR+cold,FortChillingArmor/life-per-level/SolDR/
Dolreplenish/LoMaxLR included. Assassin skills,FCR,damage-to-mana notmercbenefits.

Initial60bankcases:55RED+5already-correct base rejection ->60GREEN50.43sec;
selected60PASS57.88sec. Audit then exposed5 superior targets lacking negative/unknown
scenarios. Added10meaningful superior-context cases; selected70PASS63.92sec.
Bank now1785cases/3738targets/3393missing.20saved reports/prices unchanged and
staged=selected.7statbundle/bankchecks passed;Ruff/formatclean. Namedbaselinecomplete.
ONE-SHOT tmp/add_zeal_merc_words.py SUCCEEDED; NEVER rerun. Initial compilerfailed
because rootempty gems locator was invalid; repeatable tmp/fix_zeal_merc_word_sources.py
replaced only those5refs with actual individual native rune pointers and updated
use/stat fingerprints. Terminalfailed82977 notlive; retry56691 greencompleted.

Implemented source-only farming reward exclusions:
maintenance/reward_mentions.py, rules/reward_reviews.json; wired into completion.py.
Source/hash/span/wholeexpectedoccurrencefields/same-guidequote/Area+Rewards+boss+item
validated; equipment/unspecified slots cannot masquerade as rewards. Duplicate and
conflicting context dispositions rejected. Item identity/market/other occurrences
remain scoped. Policyfingerprint includeshelper; scopefingerprint includesdocument;
main reads/pins newrulesdoc.13reward/integration tests; combinedcompletion/dependency
suite56PASS0.13sec. Testsprove original itemmarket and equipment occurrence remain
pending and changingreview invalidatesfinalscope. No runtime appraisal-code change.

ONE-SHOT tmp/add_zeal_reward_reviews.py SUCCEEDED after fixing an initial prewrite
KeyError on kind-less inventoryrows; NEVER rerun. Seven reviewedsourceonly rows:
spans199(section34),200(35),201(38),202-205(39), keys/organs/Torch listed as bossdrops.
Completioncount1386reviewed,4784excluded(+7),8052rows,112034pending;scope
41842f8a3896547f8b5491caeb4415918dde817fc64ff37c28f3380c064758f2.
Latestlogs tmp/zeal-reward-completion-final.log and tmp/zeal-merc-word-bank-final.log.
Finalfullsuite/currentwholebank/hostPythonrestart-delivery STILLpending.

NEXT source closure findings from actual inventory/sections:
1. Reaper prose span206 is incorrectly labeled player/unspecified. Section43 explicitly
says equip the DesertMercenary with Might and Reaper. ExistinggeneralReaperrole is
merc; current mercenary_narrative reviewer requiresoriginalside merc. Need explicit,
source-bound wearer correction (or extractor fix with full pin audit), preserving
original evidence and rejecting unsupported player-to-merc reassignment.
2. Insight earlytable208/fc01065b item30 stillpending. Linked4s noneth Poleaxe (verified
sourcecodepax; resolve name via metadata ratherthanmemory), perfectplanner17aura/
260ED/250AR/6Critical. Existingzeal Insight Act2Might rule/source must be compared;
lowrolls shouldretainutility. Do not assume Act5 can wield the polearm merely because
header earlycolumnlists Act5Frenzy ORAct2Might.
3. Cure midtable241 stillpending; earlyrule supportsAct2Might ORAct5Frenzy. Source
midcolumn supportsAct2Might only. Existing source-context declaredtypes==roletypes
prevents narrowing a broad validatedrole to a specific supportedbranch; consider
explicit safe subset-link semantics/tests rather than duplicate unrelated logic.
4. Potion spans245/246Healing,247Thawing,248Antidote are actual mercenaryutility advice,
NOT farmingreward exclusions. Read exacttexts before implementing utility roles.
5. Many remaining unspecified spans are Hardcore prose. Section50 introducesHardcore;
section51 GearChanges discusses Crown/Cham/Ber/Enigma/HoZ/etc. Likelyspans250-272;
verify exactquote/source placement before source-mode exclusions. DO NOTexclude249
Enigma (section46FCR48 weapon-swap discussion), nor273Oath/274Shaftstop/275Torch in
section53Summary (SCadvice). Existing softcore_exclusions only catches explicit
Hardcore variants, so GuideMention prose is stillpending. Scope-source exclusions
must preserve itemidentity and allSCuses, as with rewardreviews.
All previous successfulone-shotadders remain NEVERrerun;retain generations.

## Active continuation — nine later mercenary configurations published, 2026-09-27

Selectedgeneration2cf5a2e792ea5f545f99f29f30696549908861d9495130d8ed6f7792567c8f04,
75artifacts,2452profiles/2444statconfigs. Chain45634 FINISHEDsuccess; no live workers.
97new item-bank cases in zeal_merc_named.py:97RED ->94PASS/3FAIL ->97GREEN33.94sec.
The3failures were a synthetic Duriel raw216 fixture mistake: native ValShift8 requires
8*256, not8; existing Shako capture tests and local D2MOO serialization confirm.
No production decoder weakening. Newpositive cases also require renderedTrade tier:
28selected staged checksPASS11.57sec. All97selected-generation casesPASS39.18sec.
Ruff/formatclean;7statbundle/bankchecksPASS11.11sec.20saved reports/prices unchanged,
and staged=selected. Namedbaseline gate remains complete (548/35sets/2958renders).

New maintenance/zeal_merc_named.py contains nine reviewed named socket templates:
zeal-paladin-later-merc-{shaftstop-um,duriel-um,tal-amethyst,guillaume-ias,gaze-ias,
stealskull-ias,kira-ral,guillaume-cham,gaze-scintillating}.
Source spans221,223,236,237,238,239,240,242,244; allZeal/Paladin/Act2Might.
Native/legalupgraded bases, native lowroll utility, actual1filledsocket checked.
Setitems require noneth; uniqueethallowed except endGaze explicitlyrequireseth.
TalPerfectAmethyst adds10Strength;Um15allres;Ral30fireres;ChamCBF. IASjewelsrequire
15IAS on actualchild. EndGaze requires15IAS+11allres on SAMEjewel (Scint11-15 from
nativeprefix337;15preferred), not pureIAS or lowerallres tiers. Mana/mana-leech
excluded;mercMFkill attribution,leech restrictions and no whole-loadout cap claims.
Duriel per-level bonuses note actualmercenary level; no player-level assumption.

ONE-SHOT tmp/add_zeal_merc_named.py SUCCEEDED; NEVER rerun.
Repeatable tmp/refine_zeal_merc_named.py updated existing9labels/conditions only,
and pinned secondaryfc planner for GuillaumeCham; no appendedrows/countchanges.
ONE-SHOT tmp/add_zeal_guillaume_repeat_binding.py SUCCEEDED; NEVER rerun.
Secondaryspan243/fc01065b item83 linked to primary242/n8010616 item2 Cham rule,
with bothplanner sourcepins. Exact duplicate context retained, not duplicatedrule.
Sourcecontext now44dispositions;completion1381reviewedoccurrences(+10),4777excluded,
8042coveragerows,111986pendingtasks. Newconfigs introduce dimensionwork; goalFALSE.
Bank1715cases/3728targets/3393missing. Finalcurrentfullsuite/combinedbank/hostPython
restart/delivery stillpending. Keep goalactive; allprior successfuladdersNEVERrerun.

NEXT: remaining Zeal merc completedwords. Exactsource cache tmp/zeal-later-merc-
planner-audit.json and earlier mid-merc audit. Treachery mid219(n8010616/item29,
nonethGreatHauberk example) vs end226(fc01065b/item54,ethsuperiorArchonPlate).
Duress mid220(fc/item77) vs end227(fc/item59,ethsuperiorGreatHauberk).
Fortitude end225(sj01061l/item21,ethsuperiorSacredArmor). Do not infer universalbest
base or require perfectplannerrolls; actualrequirements/fullsurvivalloadout matter.
Existing zeal-paladin-duress-merc-survival-gear can support the midgeneral recipe,
but endeth/superior distinction stillneeds explicitreview/config. Existing shared
armor templates elsewhere use fixed examplebases; reuse only justified predicates.

Verified localnative runes.json BYNAME; cachedplannerRunewordNNN identifiers DIFFER
from currentnative IDs! NativeTreachery Runeword148 (cached173), Fortitude41(cached67),
Duress30(cached56). Never map oldIDs directly. Rune sequences stillmatch.
NativeTreachery:25%lvl15Venom onhit,5%lvl15Fade whenstruck,45IAS,+2Assassin(nonbenefit);
Shaeladds20FHR,Thul30coldres,Lem50goldfind(killcredit). Fade201:17103,Venom198:17807.
NativeFortitude:200EDef,300offweaponED,25FCR(nonIAS),20%lvl15ChillingArmor,
life/lvl8-12 fixedpointcoefficient (raw8*256 to12*256),25-30allres. Runecontributions
must be readnative:El/Sol/Dol/Lo (avoid forgetting flatDR/replenish/maxlightres).
NativeDuress:10-20ED,150-200EDef,20nativeFHR+20Shael=40total,15CB,33OW,
37-133cold;Um15allres+Thul30cold =>45cold/15others. Nativeprocs not reversedplanner
chance/level fields. Core recipes in sourcecachecarry correctnames/rune sequences.

## Active continuation — Um mercenary variants published, 2026-09-27

Selected generation b53be10165a2c5cb18f559c88c88424cdb367f055fdf124209936493008f0afb,
75artifacts,2443profiles/2435statconfigs. Publication chain92097 FINISHEDsuccess;
policy follow-up51022 FINISHEDsuccess. No live processes to resume.

NEW35 independently authored item-bank cases zeal_merc_um.py: 35RED ->35GREEN
18.86sec(staged),35PASS26.04sec(selected). Registered total1618cases;3719targets,
3393missing. Native low rolls, both ethereal states/unknowneth, legal upgrades,
wrong/unknownmerc,wrongclass,unknownsockets,wrong/unreadfiller,empty/unsocketed.
Explicit beneficial stats and exclusion of GuardianPaladin/blocking and RockVitality.

Added expand_zeal_um_survival to EXISTING merc_survival_templates.py. Three profiles:
zeal-paladin-merc-um-{guardian-angel,gladiators-bane,rockstopper}. Exact1filledUm,
Act2Might/Paladin, native bases/legalupgrades; actual filler required. Um adds15allres
in armor/helmet (nativegems/r22), not shield22. General unsocketed rules unchanged.
Source spans224/222/235; nativeunique218/250/202. Rockstopper new advice distinguishes
unsocketed poison gap from Um-addedpoison. No perfect native roll/ethereal minimum.
ONE-SHOT tmp/add_zeal_merc_um.py SUCCEEDED: NEVER rerun.

Broader regression initially9FAILED25PASS:8obsolete tests still rejected Zeal's
previously reviewed Act5Frenzy early alternatives; one loose ID filter included
new unnamed/GuideMention patterns in the old early-family source-link test.
Corrected explicit eight-name Zeal exception and exact early variant selection.
Rerun34PASS72.31sec(tmp/zeal-merc-um-regression-green.log); Ruff/formatgreen.
7statbundle/bankchecks also pass during finishchain.

20saved captures/prices unchanged. Sole expected report text difference:
GuardianAngel Details22uses/1moregroups ->23uses/2moregroups. Reviewed new
Um-specific use accounts for increment. All20selected reports match staged.
Namedgate548eligible/35sets/2958rendercases complete. Latestcompletion stillFALSE:
1371reviewedoccurrences(+3),4777excluded,8033coveragerows,111951pendingtasks.
The extra three configurations add dimension work; do not conceal those gaps.

Also fixed completion-policy dependency hole: context_values.py and
mercenary_source_context.py now included in policy_fingerprint. TwoREDtests showed
editing either helper incorrectly preserved final attestation fingerprint;55GREEN
completion/context tests0.14sec afterfix; RuffPASS. Completion rerun after publication
at tmp/zeal-merc-um-completion-policy.log, scope
2fef33063f38ac0c9c78537360586b959bb83b983bfd75b1de228e495d798f6b.
This is maintenance attestation code, no runtime-rule change or extra publication.

NEXT source cache audit tmp/zeal-later-merc-planner-audit.json (alreadyread):
- Shaftstop span221/fc01065b item79, DurielShell span223/item80: upgraded,1Um.
- TalCrest span236/fc item62:1PerfectAmethyst (gpv; verify native mapping beforecode).
- Guillaume span237/item63, VampireGaze span238/item65, Stealskull span239/item110:
 1jewel child53 =15IAS only, not assumed ED/resistance.
- Kira span240/item72:1Ral.
- Guillaume end spans242/n8010616 item2 and243/fc item83: upgraded,1Cham.
- VampireGaze end span244/fc item69: ethupgraded,1jewel child70=15IAS+15allres;
  lower native jewel tiers need review, do not auto-require15allres or borrow pureIAS.
- Treachery mid219/n8010616 item29 vs end226/fc item54 eth/superior.
- Fortitude end225/sj01061l item21 eth/superiorSacredArmor example; not universalbestbase.
- Duress mid220/fc77 vs end227/fc59 eth/superior (priorauditfile).
All mid/end merc table branchesAct2Might, not Act5. Native proc semantics takeprecedence
over reversed oldplanner chance/skill-levelfields. Existing generic profiles can be
reused for general use, but exact sockets/eth/socketjewel properties need own checks.
All-item goalACTIVE/UNFINISHED; finalfullsuite/currentcombinedbank/runtimePython
restart/delivery stillpending. Preserve generations and all successfulone-shotadders.

## Active continuation — exact mercenary source reviews published, 2026-09-27

Selected generation: 5cd30c1f4149a0e7fca5efe008ab4962a37240541c2cc3839fd1507962abf650
(75 artifacts; 2440 profiles / 2432 stat configurations). Session40564 FINISHED
successfully; no live publication/test process remains. Previous44275 also finished,
publishing a266189d251cae594876826b49984c4658d0fb454c9c661d6fc68399f32cf861;
its selected45 merc-tail cases passed28.17sec. Do not restart either process.

Added additive mercenary_equipment source-review kind, using finite context_values
rather than weakening requires_eq or existing narrative/player guards. Explicit
row/branch mercenary_types, exact source/hash/class/slot/profile checks, union of
reviewed mercenary branches, and explicit pending alternatives prevent false
closure. New helper maintenance/mercenary_source_context.py; tests reject optional
context, wrong wearer/class/slot, duplicate/missing alternatives and incomplete
quotes. Separate existing Act2/Act5 rules may jointly satisfy the declared set.
65 context/regression tests PASS; Ruff PASS; 7 stat-bundle/bank coverage checks PASS.

ONE-SHOT tmp/add_zeal_merc_equipment_bindings.py SUCCEEDED: NEVER rerun.
10 exact early table bindings at spans215,218,216,214,231,212,233,234,211,228.
Last two reuse separate existing Smoke and Crown of Thieves Act2/Act5 profiles.
Actual full compiler validates all43 context dispositions; new10 are reviewed.
No profiles or stat configurations added in this batch.
Repeatable chain tmp/finish-zeal-merc-binding.sh completed rebuild/index/publication,
20 saved report/price comparisons unchanged, staged=selected, coverage and completion.
Logs tmp/zeal-merc-binding-*. Completion reviewed occurrences1358 ->1368, excluded
unchanged4777, remaining111949 ->111939. Bank1583cases/3716targets/3393missing.
All-item goal remains ACTIVE/UNFINISHED; no final full-suite/current combined-bank
or host Python restart/delivery evidence.

Sacred Rondache user report is covered by selected saved replay: +27 allres versus
preferred+45, Spirit Paladin caster use, nonethereal player suitability, needs4s,
unknown-ilvl Larzuk3/4, cube0%/50% for respective caps. Two targeted Paladin-shield
regressions PASS3.28sec. Matching market evidence still unknown, not zero value.

Concrete NEXT: later Zeal merc table uses Act2Might only. Inspected cached planner
payloads in tmp/zeal-mid-merc-source-audit.json. GuardianAngel span224/fc01065b item76,
GladiatorBane span222/fc01065b item81 and Rockstopper span235/n8010616 item98 each
have1 socket filledUm. Existing general roles do NOT check fillers; add separate
socket-specific variants with RED/GREEN item-bank cases, preserve general roles,
verify native stats and upgraded bases. Do not claim source occurrence fully closed
by the generic rule. Duress span220/fc item77 is noneth; span227/item59 is ethereal
superior endgame example, distinct from generic recipe. Mid/end table/source socket
review still pending. Reward-only spans199–205 and Reaper prose206 also pending.
All previous successful one-shot adders remain NEVER rerun; retain generations.

## Active continuation — cross-base report regression fixed, 2026-09-27

Merc-tail publication attempt92312 STOPPED before publishing: saved Authority
MagePlate report gained failed GemmedDuskShroud use. Selectedgeneration remains
339f8c83a8422fd3e79ba62888d4c5d6cc58a19483ffe280198a271cfdc77b28 until retry succeeds.
RCA: exact-base checks existed inside must but patterns lacked top-level base_codes
selectors; unrelated normal armor entered candidates and polluted independent-demand
reports. No need to weaken report comparison or hide all failures globally.

Added2 meaningful bank cases for other LEGAL bases (ArchonPlate vs DuskShroud,
DeathMask vs Mask), asserting ~Contains(the specific role) and no stat contribution.
2RED -> added base_codes selectors via verified metadata to zeal_merc_equipment
factory, regenerated ONLY its2existing pattern role rows and corresponding use/stat
fingerprints (counts unchanged2440profiles/2432configs). No one-shot adders rerun.
All45merc-tail cases GREEN24.74sec, tmp/zeal-merc-tail-green.log. Ruff/formatgreen.
Current bank total1583 (1538previous+45new), not yet final combined run.

CURRENT LIVE session44275: retry bash tmp/finish-zeal-merc-tail.sh. Poll this same
handle/logs; do not duplicate. It repeats7checks/rebuild/index, requires20replays
unchanged vs publishedearlymerc, thenpublication/selected45/replay/audits/completion.
Old92312 terminalfailed;25851 green-test session terminalsuccess. No other live work.

Independent concrete progress toward source bindings: NEW isolated module
pricing/knowledge/assessment/maintenance/context_values.py and tests/..../
maintenance/test_context_values.py. 11RED(missingmodule) ->11GREEN0.04sec.
context_values(predicate,field) derives finite equality alternatives: all intersects,
any unions; unbounded/optional OR ->None, contradictions ->empty set, negation of
that context field ->None. Other item/context predicates do not prove satisfiability;
positive item tests remain required. Not imported/wired into source validator yet.
This helper does NOT broaden existing requires_eq or change runtime behavior.

Next integration plan: additive source-context kind mercenary_equipment (side merc,
slotsWeapon/BodyArmor/Helmet, knownplayerclass), preserving old mercenary_narrative
and player guards. Explicit row mercenary_types declaration and per-branch types;
branch's finite role mercenary restriction must equal its declared set, all types
must appear in same-guide evidence quote, player class must remain required and
slot/build/identity/source hashes exact. Union of reviewed branches must cover all
row-declared types before complete; incomplete cases need explicit remainingbranches.
Reject optional unconstrained roles, extra types, duplicate lists, wrongclass/wearer,
wrongslot/stale evidence. Then bind8broadened early roles to exacttable spans, and
Smoke/Crown separate existing Act2/Act5 roles where appropriate. Do not silently
credit flattened-table stage assumptions. Tests/integration still required.

All-item goal remains active/unfinished. Final full repository suite, final combined
bank proof and host Python restart/delivery remain pending. Successful previous
one-shot adders remain NEVER-rerun; see notes below.

## Active continuation — early mercenary remainder green, publication running, 2026-09-27

Early-merc chain26643 FINISHED. Selectedgeneration339f8c83a8422fd3e79ba62888d4c5d6cc58a19483ffe280198a271cfdc77b28,
74artifacts,2435profiles/2427configs;selected54PASS33.17sec,20saved reports/prices
unchanged and staged=selected. Bank1538cases/3703targets/3385missing. All-item goal
unfinished; final full suite/combined final bank/host restart still pending.

New43registered cases zeal_merc_tail.py initially43RED against selectedruntime.
Implemented5source-specific early mercenary profiles in new maintenance helper
pricing/knowledge/assessment/maintenance/zeal_merc_equipment.py, compiled to role
JSON by successful ONE-SHOT tmp/add_zeal_merc_tail.py. NEVER rerun that adder.
Staged2440profiles/2432statconfigs; test_stat_bundle count updated accordingly.

Profiles zeal-paladin-early-merc-{hustle,bulwark,undead-crown,resistance-armor,
resistance-mask}. All Paladin + (Act2Might OR Act5Frenzy), early table branch.
Hustle armor source span213/n8010616item183: armor IAS40,movement65,FHR20,Dex10,
allres10; no mercEvade/weaponFanaticism/Burst proc. Bulwark span229/item182:
leech/flat+percentphysicalDR/FHR/replenish/EDef/maxlife%, not itemVitality.
UndeadCrown span230/fc01065bitem61/nativeunique77: Crown/legalupgrades, leech,
poisonres/half-freeze/undead-specificdmg+AR, not SkeletonMastery;0/1s.

GemmedDuskShroud span217/fcitem93 is EXACT4filled Ral/Ort/Thul/Tal runes, NOTgems:
30fire/lightning/cold/poison. Mask span232/fcitem71 is3filledRal/Ort/Tal; no coldres.
Native rune names verified from metadata (iterate values; keys are txtIDs notcodes).
Restrict these patterns to cited DuskShroud/Mask bases,normal/superior/low_quality,
exactsocketcount/fillers and observedres30. Empty/wrong/unread fillers distinct.
Completed recipes assess existingitems, not currentNonLaddercreation availability.

New43cases GREEN24.14sec, tmp/zeal-merc-tail-green.log. Includes both mercs,
ethereal, wrongmerc/class, unknownsockets, exactfillers/unknown/empty, wrongrecipe
socketcount. Explicit absent_stat_configurations verifies ignored skill/vitality
stats are not marked useful by these roles. Ruff/formatgreen. All source/profile
compiles and index build succeeded, no fixture errors in greenrun.

CURRENT LIVE session92312: bash tmp/finish-zeal-merc-tail.sh (repeatable chain).
7statbundle/coverage checks,full dependent rebuild/index,20saved replays vs
published early-merc,publication,selected43,replay/audits/completion. Poll SAME
handle/logs, do not duplicate. Until it publishes selected339f8c83 remains.

Remaining source work: exact earlymerc table bindings for broader8existingroles;
source_context validator lacks multi-merc table branch kind (do not weaken guards).
CrownThieves/Smoke already have source-specificStarterroles; link appropriate table
occurrences without duplicating semanticroles. Mid/end merc gear still queued:
Treachery,Duress,Shaftstop,Gladiator,Duriels,GuardianAngel,Fortitude; helmetsRockstopper,
Tal,Guillaume,VampireGaze,Stealskull,Kiras,Cure. Review existing roles and exact
planner socket variants before adding. Reaper prose206 wearer-context issue and
reward-only199–205 source dispositions remain. No final completion claim.

## Active continuation — early mercenary branches green, publication running, 2026-09-27

Reaper chain47189 FINISHED. Selectedgeneration8f8af97eb01f3842430eb7ab6e2ab3250eddd3a82aba519aaedaaac8bb9e9b99,
74artifacts,2435profiles/2427configs. Selected33PASS16.95sec,20saved captures/reports/
prices unchanged and selected=staged. Bank1484cases/3703targets/3394missing.
Completionfalse:1353reviewed/4777excluded occurrences,8017coverage rows,
111877remaining tasks. Final full suite/combined bank/host restart remain pending.

Reviewed original cached HTML table under mercenary-gear-options-header, not its
flattened text. Columns Early-Game/Mid-Game/End-Game; mercs early Act5Frenzy OR
Act2Might, later Act2Might only. Early armor:Smoke,Lionheart,Hustle,SkinFlayed,
Goldskin,Rockfleece,GemmedDuskShroud,VenomWard. Earlyhelm:CrownThieves,Bulwark,
UndeadCrown,FaceHorror,GemmedMask,Temper,Cure. Do not assign later-stage rows toFrenzy.

New registered bank cases zeal_early_merc.py:54 across9existing items. Initial
18red/36pass included false Smoke coverage assumption. Smoke ALREADY has separate
zeal-paladin-smoke-act-5-frenzy role, with correct useful stats; reused it in tests
instead of broadening Act2generic role and invalidating existing zeal-starter-smoke
source-context binding. Corrected red16failed/38pass. Eight REAL missing branches:
Goldskin,VenomWard,Rockfleece,SkinFlayed,FaceHorror,Lionheart,Temper,Cure.

Successfully broadened those8existing must-contexts to explicit any(Act2Might,
Act5Frenzy), preserving Paladin, identification, named/base/recipe/socket rules.
Updated source review/corroborating exact early span, conditions, guide-use/stat
fingerprints. Profile/config counts unchanged2435/2427. Native stat usefulness
unchanged (no vitality/energy/class skill benefits invented). Existing mid/end
roles remain untouched. Smoke generic Act2role unchanged.

One-shot tmp/expand_zeal_early_merc.py SUCCEEDED for8; NEVER rerun. First attempted
9row version failed pre-write on Smoke context-binding safety assertion; no partial
writes. Only after reusing existing Smoke rule did corrected8version run. New bank
54GREEN in28.28sec, tmp/zeal-early-merc-green.log; lint/formatgreen.

CURRENT LIVE session26643 runs bash tmp/finish-zeal-early-merc.sh:7statbundle/coverage
checks,dependent rebuild,index,20saved reports vs publishedReapers,publication,
selected54,replay,audits,completion. Poll same handle/logs; do not duplicate. Selected
8f8af97... until new publication succeeds. No other active process from this turn.

Next: exact mercenary-equipment source bindings must retain BOTH early-game branches;
existing source_context validator supports player equipment or merc narrative with
single required merc type, not multi-type merc table entries. Do not relax matching
or silently credit these source occurrences. Other early items need their own roles
or existing-role links (Hustle armor, Bulwark, Undead Crown, gemmed armor/helm), then
mid/end mercenary gear. Reaper prose span206 and reward-only spans199–205 remain
source-disposition tasks from earlier notes. Goal remains active and unfinished.

## Active continuation — Reaper configurations green, publication running, 2026-09-27

Unique-charm chain93466 FINISHED. Selected generation8a63045b9f19b3cd0c792b91681793c70c3cf20879369bc282f52bf1684bb2ff,
74artifacts,2432profiles/2424statconfigs; selected27pass20.08sec,20saved outputs
unchanged and staged=selected. Additional pattern-source-context9pass. Bank1451,
targets3700,missing3394;completionfalse with1350reviewed occurrences/4777excluded,
8014coverage rows,111865remaining tasks. Final full suite/host restart still pending.

Added ONE further exact BoneBreak source-context binding for span195 (its role
Gear alternatives variant differs from source Guide mention, so direct source
credit alone did not close it). tmp/add_zeal_bone_break_binding.py succeeded once;
NEVER rerun. This binding is staged for the Reaper publication, not in8a63045b.

New bank zeal_reapers.py registered33cases. Initial33RED proved missing Zeal roles.
Three profiles now implemented: zeal-paladin-reapers-general, -shael, -ruby.
General uses existing named-merc template with Paladin/Act2Might, valid Thresher,
identified,0/1s;eth preferred not mandatory. Section43 is source. Shael span209/
planner26 requires exact filled Shael and20IAS, both eth statuses useful. Ruby
span210/planner21 requires ethereal and one captured jewel ED31..40/IAS15;40 is
preference not minimum. Wrong Ruby fire-resist jewel fails; weapon totals alone
never prove filler. Native unique326 ED190..240/leech11..15, Decrepify33%level1.
Planner reverses proc fields; native tables govern. Stat priorities distinguish
mercenary weapon properties from conditional enemy Decrepify support.

One-shot tmp/add_zeal_reapers.py SUCCEEDED, NEVER rerun. Staged2435profiles/2427
statconfigs. First green run30pass/3fixture errors: impossible Reaper/GiantThresher
identity rejected by bank factory. Replaced with actual Stormspire/GiantThresher
(nativecode checked locally), asserting ~Contains(Reaper role), not merely lack
of annotations. Corrected33PASS in12.11sec, tmp/zeal-reapers-green.log. Ruffgreen.

CURRENT LIVE session47189: bash tmp/finish-zeal-reapers.sh. Repeatable publication
chain:7statbundle/coverage checks, full dependent rebuild,index,20saved reports
vs unique-charms published replay,publication,selected33,replay/audits/completion.
Poll same handle/logs; do not duplicate. Until it publishes selected8a63045b remains.

Next source review: remaining Zeal mercenary gear spans211–244. Several section44
merc-survival roles already exist; exact table contexts and socket variants still
need review/bindings/cases. Generic Reaper source section43 is implemented, but
prose span206 is mis-attributed player/unspecified by extraction and still needs
explicit wearer-context disposition; do not silently rewrite source or claim closure.
Farming reward spans199–205 are NOT equipment recommendations (keys/organs/Torch
rewards, sections34/35/38/39); source-only non-use review mechanism is still needed.
Do not exclude their item identities, prices or real inventory uses. Existing
source_context validator requires a role; current exclusion logic only handles
Hardcore. No automatic reward exclusions were added in this continuation.

## Active continuation — Zeal unique charms green, publication running, 2026-09-27

Whole-bank session4981 finished:1424passed in739.86seconds against generation
2a387dbf0afa21263dc2d572d3a0c8e717ce3eae4224c2a0147203a4c312624c.
Do not restart it. Log tmp/native-charms-whole-bank.log. Final full repository
suite and final same-generation expanded bank verification still remain pending.

New registered bank cases zeal_unique_charms.py:27 total. Initial9failed/18passed
reproduced missing BoneBreak role. BoneBreak now added using existing reviewed
original-sunder template: physical piercing300, wearer penalty-20..-10.
Three exact span196–198 bindings link existing Gheed/Torch/Anni roles, no duplicates.
Staged counts2432profiles/2424statconfigs. Both one-shot adders now SUCCEEDED:
tmp/add_zeal_bone_break.py and tmp/add_zeal_unique_charm_bindings.py. NEVER rerun.
Bone adder initially used pattern demand incorrectly for a named item; corrected
only its guide-use row to item='Bone Break' before successful profile compile.

Source-context validator needed explicit charm inventory support: PLAYER_SLOTS
adds Charms/Unique Charms; canonical slot Unique Charms->Charms. New6focused tests
4red/2pass ->green; all source/player/context regression32passed. Class/wearer and
noninventory slots remain checked. Binding script failed pre-write until this fix,
then succeeded once. No duplicate binding rows.

New bank staged27PASS (15.83sec), tmp/zeal-unique-charms-green.log. Malformed sunder
299/301 correctly decode UNRESOLVED, not known false; cases require unknown,
no stat contribution, estimateNone and Unreadable report. Other near-misses remain
negative. Complete native charmcaptures include Torch5%lvl10Firestorm/Hydra, rather
than copying the old planner reversed proc values. Ruff/formatgreen.

CURRENT LIVE: session93466 runs bash tmp/finish-zeal-unique-charms.sh. Poll same
handle/logs, do not duplicate. This repeatable chain validates statbundle/bank
coverage, rebuilds dependent artifacts/index, compares20 saved reports with
native-charms published replay, publishes, selected27/replay/audits/completion.
Until publication succeeds selectedgeneration remains2a387dbf... . After chain,
check tests/pricing/knowledge/assessment/maintenance/test_pattern_source_context.py
because charm slot support also affects explicit player_pattern context admission.
Update actual generation/counts and continue next unreviewed Zeal source, then
all remaining queues. Goal remains unfinished; no final full suite/host restart.

## Active continuation — unique charm tests prepared, 2026-09-27

Whole-bank session4981 remains LIVE: pytestPID250266 (uv250263), 7m20s elapsed,
99.4%CPU, past55% with no failures reported. Same selected generation2a387dbf...;
do not restart/duplicate or mutate its runtime/metadata/factory while running.
Log tmp/native-charms-whole-bank.log. Prior turn made progress (publication and
selected tests); this turn verified the live wait and prepared independent cases.

NEW unregistered file:
tests/pricing/knowledge/assessment/item_bank/cases/zeal_unique_charms.py
27 independently authored cases across Bone Break/Gheed/PaladinTorch/Annihilus:
native low rolls, wrong/unknown class, unidentified, unknown ethereal; missing vs
unread core stats for BoneBreak/Torch; sunder299/301 rejected; other-class Torch.
Positive cases require stat configuration contribution and rendered Trade tier.
Ruff/format pass. Not registered and NOT RUN RED YET. After current fullbank
terminal, import/expand CASES in cases/__init__.py and run its filtered selected
pipeline before implementing rules. BoneBreak should reproduce missing-role red;
repair any invalid fixtures independently, not expected semantic behavior.

Native Torch evidence: uniqueitems400 +properties hit-skill specify5% level10
Firestorm; old planner n8010616 item16 reverses chance/level. Test uses native
stats198 layer197*64+10 raw5. Hydra stat204 layer62*64+30 raw10*256+10;
light stat89 raw8. Complete Torch capture includes these so absence of other class
bonuses is proven. Unknown-core case sets completeFalse. Verified IDs locally.

Prepared but NEVER EXECUTED:
- tmp/add_zeal_bone_break.py: adds one Zeal original BoneBreak profile/statreview/use,
  source span195/planner175/native unique405. Physical piercing300; wearer penalty
  -20..-10, not a positive damage bonus. Counts2431/2423 ->2432/2424.
- tmp/add_zeal_unique_charm_bindings.py: binds exact spans196–198 to the three
  EXISTING section32 semantic roles via source_context_reviews. No duplicate roles.
  Must run after compiled profiles reflect BoneBreak; validates before writing.
Both are one-shot adders: run only after red, NEVER rerun after success.
No production roles/artifacts/publication changed in this continuation.

Next after red/implementation: build_profiles, new27 staged pipeline +source binding
checks/stat bundle/coverage, full artifact refresh, saved20 replay comparison,
publication, selected27 validation and audits. Preserve whole-bank terminal result;
adding27 afterward means final combined bank proof still needs a later fresh run.
All-item goal remains unfinished; no final full suite or host restart verified.

## Published native charm fixes — whole-bank verification running, 2026-09-27

Selected generation: 2a387dbf0afa21263dc2d572d3a0c8e717ce3eae4224c2a0147203a4c312624c
(74 artifacts, 2431 profiles / 2423 stat configurations). Publication chain48959
finished successfully. Selected159 charm cases passed in87.81seconds;20 saved
reports/prices unchanged and selected matches staged. Guardian Angel retains Trade
tier low and Enhanced Defense180–200. Universal tier gate:548items/35sets,
2958rendered cases, complete. Bank1424cases/3699targets/3397missing cases;
observed20captures/77gaps. Completionfalse:2570identities,62891occurrences,
1347reviewed/4777excluded,8013coverage rows,111863remaining tasks.

CURRENT LIVE RUN: session4981 runs all1424 constructed-item cases against selected
runtime, log tmp/native-charms-whole-bank.log. Poll the same handle/process; do
not restart or duplicate. No rule/metadata/factory mutations until it completes.
New Item.capture nested item.affixes affects every family; fix any real regression
without weakening expectations. This is not the final full repository suite.
Code restart on host and final delivery remain unverified.

Next reviewed sources: Zeal exact guide spans195–198, planner n8010616 items
175/18/16/17. Bone Break175 is original unique405, physical immunity stat300 and
wearer physical resistance-10; template already exists but no Zeal semantic role.
Gheed/Torch/Anni already have section32 profiles: bind spans to existing roles,
do not duplicate. Planner Torch is Paladin class3,20attributes/20res; these are
perfect examples, not minima. Existing role IDs end gear-inventory-charm.
Add meaningful positive/negative/unknown item-bank scenarios after current run.

## Active continuation — native charm identities and price facets, 2026-09-27

Goal remains active and unfinished. This entry supersedes the older live-process
notes below. The 386-test regression completed successfully (1226.69 seconds);
do not restart session44193. Native affix identity now travels through decoding,
normalization and the item bank. Sharp/Maiming requires both captured affixes;
its combined damage range is 10–14. Five existing charm configurations now accept
the lower native tiers of the same named affixes.

Staged profiles/configurations: 2431/2423. Native charm range tests:31 passed;
identity/definition integration:31 passed; corrected pricing/identity checks:26
passed; broader pricing contracts:21 passed. The 159 affected full-pipeline bank
cases passed after correcting Item.capture to use production item.affixes nesting.
Physical damage on non-weapons now contributes to exact price comparisons;
mirrored native rows are validated, never summed. Weapons retain separate handling.
Six baseline source pins were refreshed only after confirming every value-watch
row was unchanged, preserving Guardian Angel’s reviewed tier.

Publication chain currently runs as session48959, bash tmp/finish-native-charms.sh.
Poll this handle/logs; do not duplicate it. Until its publication succeeds the
selected generation is c1157002ddbeab8c1526ce2fd6028c889c4bcf385fb4e1750e07a1d97711bdf6.
The chain rebuilds artifacts, checks 20 saved reports, publishes, checks selected
159 cases, and refreshes coverage/completion. A whole-bank run remains necessary
because the factory facet-envelope correction affects every constructed item.
Final full suite and host Python restart/delivery remain pending.

Logs: tmp/native-charms-pricing-regression.log, native-charms-bank-corrected.log,
native-charms-broader-pricing.log; chain outputs use tmp/native-charms-*.
One-shot adders apply-native-charm-integration.py and add_zeal_maiming.py succeeded;
NEVER rerun. Existing successful earlier adders must also not be rerun.
Next source review after this validation: Zeal guide spans195–198 (Bone Break,
Gheed’s Fortune, Paladin Hellfire Torch, Annihilus) lack exact guide-span bindings;
check existing semantic profiles before adding rules. All-item completion remains
false; the selected-generation audit still has over111k required tasks.

## Active continuation — lower named charm tiers reproduced, 2026-09-27

GoalACTIVE. Nativeaffix regression STILL LIVE session44193,pytestPID242838/uv242823.
Latestverified elapsed15:43 CPU99.3%,235+passingdots/386 (past55%),no failures reported.
Poll samehandle/actualprocess/log, DO NOTrestart. Currentgenerationc1157002...unchanged.
No existing runtime/profile/metadata source usedbyrunningregression changed thisturn.

Newconcreteprogress: tests/pricing/knowledge/assessment/test_charm_lower_tiers.py
5RED tests, log tmp/charm-lower-tiers-red.log;2.34sec,ruff/formatgreen. These callnative
Item.capture ->assessmentengine anddirty-equals roletruth assertions. NotyetItemBank
coverage credit; fold equivalentcases intofullpipelinebank beforefinaldelivery.
Cases expectingknownuse withlower SAME-NAMED nativeaffixtier:
- zeal-paladin-charm-grand-steel: AR88 insteadcurrent118 threshold.
- grand-steel-vita: AR88,life36 instead118/41.
- grand-steel-balance: AR88,FHR12 instead118/12.
- grand-sharp-vita: AR49,max7,life36 instead41.
- sharp-large-vita: AR21,max4,life26 instead31.
These are sameguide namedaffixfamilies, nototheraffixnames or trade-premiumclaims.

Freshnative eligible can_generate metadata audit:
GrandSteel prefixrecords224(native1009) AR88–102,225(1010)103–117,226(1011)118–132.
GrandVita suffix338 life36–40,339life41–45,340life46–50.
LargeVita suffix345life26–30,346life31–35.
SmallSteelprefix237AR25–36;SmallVita349life16–20 (noadditionaltiers).
Existingpredicates >=41alreadyacceptnew46–50;missinglower36 remainsfalse.

After running386regression terminal, implementthe5thresholdbroadenings alongside
Maiming/nativeidentity/rangework queuedbelow. Refreshonlyaffectedexistingprofiles,
sourcecorroboration/rationale,guide-use/stat-use fingerprints; DON'Trerunone-shotadders.
Add lower native source locators, retainhigherplannercases. Countsunchanged forthese5;
Maimingnewprofile/statconfig increments2430/2422 ->2431/2423.
Then runexistingcharms+lowercases+Maiming fullpipeline tests, metadata/indexdependent
rebuilds, savedreplays/publication/audits. No narrowgreencompletionclaim.

## Active continuation — combined charm damage component, 2026-09-27

GoalACTIVE. Existing native-affix regression stillLIVE session44193,pytestPID242838
(uv242823). Last verified elapsed11:45 CPU99.3%,>=144passingdots/386,no failures.
Poll samehandle/actualprocess/log, DO NOTrestart. Selectedgeneration unchangedc1157002...
No existingruntime/profile/metadata files readbythatregression were edited thisturn.

Concreteprogress: NEW isolated inventory_tracking/items/combined_charm_damage.py
with combined_damage_ranges(entries,base,quality,pool). NOTimported/wired yet.
Works only magic4 +native charmtype +exactlyoneprefix/onesuffix contributor for each
flatdamage stat21/22/23/24/159/160. Requires distinctpositiveaffixgroups, matching
property/statIDs, validatednativebounds andpoolranges/tiers. Addsactualaffixbounds,
computeslegalcartesian tierbounds andglobalpoolbounds; preservesbothsourceIDs/names.
Rejects rares/weapons/thirdcontributors/sametable/samegroup/unverifiedproperties/no pools.
Tests NEW tests/inventory_tracking/items/test_combined_charm_damage.py:
9red(missingmodule) ->9green; Ruff/formatgreen. Logs tmp/combined-charm-damage-*.
The component doesn'tyetchangeapplication behavior orresolve4integrationredtests.

IMPORTANT correction to priorhand-off: combinedSharpMaiming total10 is NORMAL under
user-requestedglobaltierquality ranking, notbottom20%. Nativeeligiblegrandprefixdmgmax:
Fine1–3,Fine4–6,Sharp7–10(group111),Jagged1/Forked2/Serrated3(group104).
SuffixCraftsmanship1,Quality2,Maiming3–4(group14). Combinedglobalrange2–14,
currentSharpMaimingrange10–14. Globalfractionfor10=(10–2)/(14–2), so normal.
Corrected only test_charm_damage_ranges.py's expectedquality low->normal accordingly.
All4integration/compiler tests remainRED untilwireup/regenerate. SingleSharp10perfect,
combined14perfect. Native affixpools already separateprefix/suffix andbasecompatibility.

NEXT after current386regression terminal (fullpreviousnotesbelow):
- Inspectresults; adddraftnativeaffix integrationtest; ItemBank affix_records/helper;
 addSharpMaimingprofile withnativeprefix253/suffix678 gate andstats49AR/10max.
- scalar_ranges optinaffix_flat_damage mapsimplicitfunc5/6 onlyaffixdefinitions.
 wirecombined_damage_ranges intoaffixes.resolve_affix_ranges, skip genericduplicate
 warning onlyforhandledstats. Guard noncharmweapon primary/secondary/throw totalranges.
 May importCHARM_TYPES fromnewcomponent ratherthanduplicateconstant.
- Regenerate definitions/metadata/dependentKBindex andartifacts, run4rangeintegration
 tests plus relevantregressions, staged/selectedreplays, publication/audits.
- Existingbroadregression isn't finalfullsuite/wholebank/delivery. No completedgoalclaim.

## Active continuation — charm damage range RCA, 2026-09-27

Prior turnprogress confirmed; current native-affix regression stillLIVE session44193,
pytestPID242838 (uv242823). Last poll ~7minutes,114+passingdots of386,no failure output.
Do NOTrestart. No runtime/profile/metadata mutations made while it reads those files.
Selectedgeneration still c1157002ddbeab8c1526ce2fd6028c889c4bcf385fb4e1750e07a1d97711bdf6.
All uncompleted native-affix implementation steps in checkpoint below stillapply.

Concrete additionalprogress: new tests/inventory_tracking/items/test_charm_damage_ranges.py
has4RED tests, log tmp/charm-damage-ranges-red.log. Notpartof runningregression's already
collected386tests. Redtests use proposed scalar_ranges(...,affix_flat_damage=True), and
actual pinnedmetadata/nativebytes for plainSharp10 and Sharp+Maiming total10 or14.
Expect native range7–10 single,10–14 combined,highest-tier ceiling10/14respectively;
lowcombined10 islow,14perfect. Lint/formatgreen. No implementationyet.

RCA/evidence:
- definitions.scalar_ranges skips properties func5/6. Native properties dmg-min func5,
 dmg-max func6 haveimplicit statIDs (not stat1 fields).
- Local D2MOO/source/D2Common/src/Items/ItemMods.cpp funcs05 line3078 /06 line3200:
 chooses randommin..max, appliesprimary,secondary,throw damage according tobase.
 Fornonweapons thefunctions apply allthree. Currentmetadata statnames verified:
 21mindamage,22maxdamage,23secondary_mindamage,24secondary_maxdamage,
 159item_throw_mindamage,160item_throw_maxdamage.
- Plan explicitaffix-only compileroptin(defaultFalse preserves named/word handling)
 mapsdmg-min->21/23/159 anddmg-max->22/24/160. Passoptin at affixcompilationonly,
 definitions.py near388. Affixresolver alreadyexcludes primarydamage onnoncharms;
 ensurethrowIDs aren't accidentallytreated asrange ofweaponbase totals.
- definitions.add_charm_quality_ranges pools by(base,affix_table,stat,range_family).
 Thusprefix/suffix pools are correctlyseparate. For magiccharms withoneprefix+one
 suffix contributing sameflatdamagestat, combineactualbounds andcombinelegalpool
 tierpairs additively. PreservebothsourceIDs. DoNOTgenericallysumstatcontributions
 onrares/weapons/set/sockettotals. Existingresolve_affix_ranges suppresses ALL
 multiplecontributionranges (counts[stat]>1); needsreviewedcharm-onlyexception.
- Preserve qualityranking: loneSharp bound7–10, combinedSharpMaiming10–14. PoolT1
 derivespinnedeligibledefinitions, notcopyobservedroll. Testtitlevaluesindependent.
- Regenerated definitions+metadata anddependentindex/artifactpublication needed after
 compilerchange; keepdefinition/index fingerprints consistent. No generatededitsyet.

Next after386regression finishes: inspectresults, applynativeaffixintegrationtest+
ItemBankhelperdrafts, addMaimingprofile redgreen, thenfixrange4redtests; targeted
regression/rebuild/replay/publish/audits. Currentgoalremainsunfinished.

## Active work — native affix identity, regression RUNNING, 2026-09-27

Goal ACTIVE; unfinished. Previous turn was progress. Selected generation remains
`c1157002ddbeab8c1526ce2fd6028c889c4bcf385fb4e1750e07a1d97711bdf6`.
Current Python changes are NOT published; no metadata/profile additions this turn.

LIVE regression: tools exec session44193; shell uv PID242823, pytest PID242838.
Command: uv run --offline pytest tests/pricing/knowledge/assessment/roles
 tests/pricing/knowledge/assessment/adapters tests/inventory_tracking/items/test_affix_ranges.py
 tests/inventory_tracking/items/test_charm_ranges.py tests/inventory_tracking/items/test_decode.py
 -q --tb=short > tmp/native-affixes-regression.log
386 tests collected (tmp/native-affixes-regression-collection.log). Last verified CPU99%,
~4minutes,45+passingdots,no failures reported. DO NOT restart on timeout. Poll handle/
actualprocess/log. Keep runtime/profile/test mutations sequential after run terminates.
The broad role tests repeatedly rebuild profiles and are slow. Don't claim386passed yet.

Implemented so far:
- Existing affixes.resolve_affix_ranges already validates nativeIDs, bases, quality,
 identified flag, duplicates, extra magic affixes. Its result now includes
 native_affixes={prefix:[IDs],suffix:[IDs],auto:[IDs]}.
- decode_items carries that into source.native_affixes when available.
- New assessment/adapters/native_affixes.py validates source shape, positiveint IDs,
 base eligibility, magic/rare countlimits and rare eligibility. Empty/invalid/unidentified
 records remainunknown; this does NOT replace other stat/identity guards.
- ItemFacts has immutable optionalnative_affixes, omittedfromto_dict whenNone.
- capture.normalize populates it. New predicate affix_present(table,value) has explicit
 TRUE/FALSE/UNKNOWN. Capturedabsencefalse; missingidentityunknown. No title/statguessing.
- tests/.../roles/test_native_affixes.py:7red7existingpass ->14green; ruff/formatgreen.
 Uses native source record IDs to derive bundled combined IDs, nothardcodedoffsets.

Crucial finding: itemmetadata affixes ALREADY uses nativecombinedIDs. PrefixSharp
record253 is key1038; prefixJade403 key1188; suffix678Maiming key678. Do not regenerate
metadata merelyforoffset. Currentcanonical prefixoffset785 alreadyhandledbydefinitions.
Existing range resolver is reusable; no need duplicate rawbyteparser.

Prepared drafts ONLY in tmp (not applied/registered):
- tmp/zeal_maiming_bank.py seven fullpipeline cases using proposed Item.affix_records:
 lowAR49/max10 +nativeSharp253/Maiming678 positive; plainSharp same10negative;
 unreadidentity same10unknown; max9negative; unreaddamageunknown; wrong/unknownclass.
- tmp/native-affix-bank-helper.py helper to append to item_bank/ranges.py. Builds native
 ItemData from independently specified (table,source_record_id) usingpinnedmetadata,
 then calls productionresolve_affix_ranges/annotate_roll_ranges. Needsformat.
- tmp/native-affix-integration-test.py test to append after current regression finishes:
 fullsavedreplay decode ->source ->normalize ->immutablefacts. Verifyfixturepath exists
 and add match='...' for pytest.raises(TypeError) lint ifrequired.

NEXT after currentregression terminal:
1. Inspect/fix actualfailures, preserving scope. Add andrun integrationtest.
2. ItemBank Item optionalaffix_records tuple; usehelper in capture, addsource native_affixes.
 Register draftmaimingcases, redbeforeprofile. Publish nohalfverifiedgeneration.
3. Add SharpGrandCharmofMaiming span189/planner1w0106kl item138 toZeal template:
 native prefixrecord253 AND suffix678 viaaffix_present; AR>=49,totalmax>=10.
 Cannot substitute>=11 asuniversalMaiminggate or infer suffixfromtotal10.
 Source reviews/statconfig/manifest/fingerprints/count2422->2423. New one-shot needed;
 prior adders NEVER rerun. Conditions note prefix7–10+suffix3–4,total10–14.
4. Focusedbank/templatechecks, rebuild, staged/published20replays. Sourceextraction will
 legitimatelyaddnative_affixes for capturedmagic/rare items; inspect exactdeltas and
 preserve text/prices unless separately reviewed. Commit/staging/liveprobe notrequested.
5. Coverage/audit/handoff after publication. Broadfullsuite/wholebank/restart pending.

NEW explicit rangegap: metadata prefixSharp1038 roll_ranges ONLYstat19; suffix678
roll_ranges EMPTY. Physical maxdamage ranges aren't compiled for charms. Identity
fixalone doesNOT satisfy maxdamageintervalrequirement; inspect definitions.scalar_ranges
and base-sensitive physical modifier mapping beforeclosing this gap. Other native
Maiming sourcevariants/lowernamedaffixtiers and allotherbuilds stillpending.

## Latest active checkpoint — Zeal elemental resistance charms, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`c1157002ddbeab8c1526ce2fd6028c889c4bcf385fb4e1750e07a1d97711bdf6`,74artifacts,
2430profiles/2422statconfigs. No hostrestart/livecollection/staging/commit.
Added ResistanceSmallCharm/span183 and ResistanceGrandCharm/span194 in existing
zeal_charm_templates. AnyONE of fire/lightning/cold/poison at10small/26grand qualifies,
never sumdifferent elements or requireallfour. Specific observedstat priorities.
Guide section32 says XResist x%; cachedplanners fire-small/lightning-grand examples.
Nativeprefix IDs small349/369/388/408 each10–11,grand341/361/380/400 each26–30.
Single-res conditions distinguish them fromShimmering. Existingmember semanticsunchanged.
One-shot tmp/add_zeal_resistance_charms.py SUCCEEDED; NEVER rerun.
Bank cases/zeal_resistance_charms.py28cases: each4elementminimum andbelow,
wrong/unknownclass,missing/unreadstats,wrongsize,and4subthresholdresists notsummed.
26red2pass(typeexclusions) ->28stagedpass ->28selectedpass;7statbundle/coveragepass.
Ruff/checkformat/diffcheckpass;rebuildcompleted.20savedreports unchangedvsprior;
20selectedmatchstaged extraction/text/price. Allprocessesterminal.
Bank1407cases/3698targets/3397missingcases;observed20/77gaps.
Completionfalse:2570identities,62891occurrences,1346reviewed,4777excluded,
8012coveragerows,111859remainingtasks. Fullsuite/wholebank/hostdeliverypending.
Logs tmp/zeal-resistance-charms-*;finishscript tmp/finish-zeal-resistance-charms.sh.

NEXT SharpGrandCharmofMaiming span189 needs actualmagic-affix identity, nottotal10
which overlapsplainSharp. Newoffline evidence gathered (noimplementation yet):
- inventory_tracking/items/identity.py resolve_identity handlesrare6 andset/unique/
  runeword, notmagic4. RawItemData is96bytes and quality/identifiedguard alreadyexists.
- third-parties/d2go/pkg/memory/item.go lines139–145 reads3prefixUSHORTs at0x48,
  3suffixUSHORTs at0x4e; magicname handling lines208on. Differentgameversion reference.
- Savedfixtures large_charm_life20.json rawprefix1188,suffix343. Currentnative
  magicsuffix table has785rows;1188–785=403(Jade largepoison11–12), suffix343 life16–20.
  Exactly matches observed12poison/20life.
- large_charm_life35.json prefix1147,suffix346;1147–785=362(Crimson largeFR4–7),
  suffix346 life31–35. Matchesobserved6FR/35life.
- D2MOO/source/D2Common/src/DataTbls/ItemsTbls.cpp lines544–558 concatenates suffix,
  prefix,automagic tables; prefixoffset=nSuffixRecords. Derive pinnedtableoffset,
  don't hardcode785. Check tableID indexing/Expansion separator and currentnativebytes.
- Locald2go prefixdescriptionIDs useoldercombinedoffset: doNOTcopynameIDs blindly.
- Assessment ItemFacts/DSL currentlyhasno affixidentity field/predicate. Plan native
  identity provenance throughcapture/adapter/facts and tests, avoiding title/stat guesses.
  Need synthetic Sharp253+Maiming678 atlowestsum10 vsplainSharp10 and savedmagicreplays.
  Do not pretend highroll-only>=11 gate covers allMaiming.
Then loweraffixtiervariants and allotherbuild/family/contract work remain. Goalnotcomplete.

## Latest active checkpoint — eight Zeal grand-charm configurations, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`bb7f2f4b5a4406f103220649726841aace80fb13c822b40ab944124f54f937b6`,74artifacts,
2428profiles/2420statconfigs. No hostrestart/livecollection/staging/commit.
Expanded maintenance/zeal_charm_templates.py with grand Sharp/Steel +Vita/+Balance,
plainSharp/Steel, Shimmering+Balance/plainShimmering. Exactguide spans185–188,190–193.
Nativeprefix253 AR49–76/max7–10,226 AR118–132,319 allres13–15;
suffix339 life41–45,265 FHR12. Planner lower native rolls qualify. GrandFHR condition
says Twelve; smallFHR stillFive preserving previous generated source.
One-shot tmp/add_zeal_grand_charms.py SUCCEEDED; NEVER rerun.
48newbankscenarios; initial40failed8passed(wrongsize exclusion alreadyworks).
Then114allcharmstagedpass and114selectedpass;7statbundle/evidencecoveragepass.
Ruff/checkformat/diffcheckpass. Rebuild completed. All20savedreports unchanged vsprior;
20selectedmatchstaged extraction/text/price. Allprocessesterminal.
Bank1379cases/3696targets/3397missingcases;observed20/77gaps.
Completionfalse:2570identities,62891occurrences,1344reviewed,4777excluded,
8010coveragerows,111851remainingtasks. Fullsuite/wholebank/hostdeliverypending.
Logs tmp/zeal-grand-charms-*;repeatablefinish tmp/finish-zeal-grand-charms.sh.

NEXT: ResistanceSmallCharm span183 and ResistanceGrandCharm span194.
Read exactguide section32: Charms desirable properties include "X Resist x%";
thus native fourelement alternatives supported, not just planner FRsmall/LRgrand.
Verified nativeprefix IDs: small Cold349/Fire369/Lightning388/Poison408 each10–11;
grand Cold341/Fire361/Lightning380/Poison400 each26–30. Type scha/lcha respectively.
Implement any-one-resistance candidate plus specificstat priorities; do not require
allfour likeShimmering or sumdifferent elements. Positiveeach,belowthreshold,
missing/unread,wrongsize/class tests. Existingtemplate conditions assumeShimmering
when anyres key present; use dedicatedmember handling to avoid misleading labels.

SharpGrandCharmofMaiming span189 stillrequires ambiguity review: prefix253+suffix678
(max3–4) totals10–14, whereas plainSharp reaches10. ItemFacts does not yet expose
affixidentity; predicateDSL has fact_eq(name),stat_at_least etc, no affixpredicate.
Do not infer Maiming from total10. Lower namedVita/Steel tiers also remain variants
to review; rules addedsofar are source-planner-tier configurations, notuniversaluse.
Continue all other builds/families/contracts after these. No completionclaim.

## Latest active checkpoint — eleven Zeal charm combinations, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`a89b90cec4d9982968b90841d4abf7b01d531f03e2f76e9c51252afc5cadb6c0`,74artifacts,
2420profiles/2412statconfigs. No hostrestart/livecollection/staging/commit.

Added maintenance/zeal_charm_templates.py: exactguide spans173–182 and184.
Fine/Steel/Shimmering small combinations with MF/life/FHR, starter single-affix
small charms, Sharp Large Charm of Vita. Native low rolls, all required modifiers,
Paladin context, magic quality and exact charm size. Native prefixes256/237/322/255,
suffixes291/349/267/346. No perfect-planner requirement. One-shot
`tmp/add_zeal_charms.py` SUCCEEDED; NEVER rerun.
New item-bank cases/zeal_charms.py66cases: lowroll,wrong/unknownclass,missing/unread
modifier,wrongsize. 66red ->55pass11fail(test expected false trace for type-routed-out
roles) ->66stagedpass ->66selectedpass. Wrongsize now checks charm routing and absence
of the target stat configuration.7statbundle/evidencecoverage tests passed.

Replay exposed five useless all-failed-build lines on unrelated large charms.
Fixed build_use_summary: when ALL candidate roles fail and no independent guide demand,
compact lines empty; full details/clusters retain failures. Mixed/unknown/demand stays.
New red/green test;11summarytests and26presentation/text/role/overlaytests passed.
This also removes failed-only sections from Dread Edge, Greater Claws and Trainer
GrandCharm. Reviewed these exact3textdifferences vs prior; other17reports unchanged;
all20extraction/price outputs unchanged.20selected reports match staged.
Pythonreporting workerrestart remainsUNVERIFIED alongside prior socket-child/base fixes.
Ruff/checkformat/diffcheckpass. All processes terminal.
Bank1331cases/3688targets/3397missingcases.Observed20captures/77gaps.
Completionfalse:2570identities,62891occurrences,1336reviewed,4777excluded,
8002coveragerows,111819remainingtasks. Fullsuite/wholebank/hostdeliverypending.
Logs tmp/zeal-charms-*; repeatable finishing script tmp/finish-zeal-charms.sh.

NEXT Zeal grandcharms spans185–194 inspected (not implemented):
185SharpVita planner rk0106ln item72: prefix253 AR49–76/max7–10 +suffix339 life41–45.
186SteelVita n8010616 item123: prefix226 AR118–132 +339.
187SharpBalance rk0106ln item51:253 +suffix265 FHR12.
188SteelBalance rk0106ln item49:226 +265.
189SharpMaiming1w0106kl item138:253 +suffix678 max3–4; totalmax10–14 overlaps
plainSharp10, so do NOT infer both affixes from total10 alone; review ambiguity.
190Sharp1w0106kl item140:253;191Steel n8010616 item130:226.
192ShimmeringBalance1w0106kl item135:prefix319 allres13–15 +265.
193Shimmering n8010616 item122:319.
194ResistanceGC n8010616 item134:prefix380 LR26–30; genericlabel alternatives need review.
Also ResistanceSmallCharm span183 rk0106ln item67 prefix369 FR10–11 stillpending.
Native earlier Vitae/Steel tiers sharing names may need separate branches; current
source-specific rules match reviewed planner tiers only, not universal viability.
Continue other builds/families and every completion-contract gate after this queue.

## Latest active checkpoint — Zeal Blood crafted ring, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`a7b69596668743846c007594e3a145a1858455c0bb9a2d5cc4da7bfed5dcc6cd`, 73 artifacts,
2409 profiles / 2401 stat configurations. No host restart, live collection, staging or commit.
Sacred Rondache, Trainer charm and socket-child decoder host delivery remains unverified.

Added Blood Crafted Ring to maintenance/zeal_affixed_accessory_templates.py.
Exact Zeal source span168 uses planner1w0106kl item120 (not main planner n8010616).
Blood recipe cube80 plus native suffix357/331/230 and prefix243 establish minimum
LL8, life41, Strength1, min damage6, AR101. Planner maximum rolls are not required.
One-shot tmp/add_zeal_blood_ring.py SUCCEEDED; NEVER rerun.
Six new item-bank cases: positive low rolls, wrong/unknown class, absent/unread leech,
and recipe-only leech rejection. Six red -> six staged green -> six selected green.
Two stat-bundle tests passed; five coverage tests passed after correcting evidence
locator to /data because planner JSON stores its payload as an encoded string.
The first selected pytest selector matched no cases; corrected selector zeal/blood-ring
ran all six successfully. Ruff/format and diff checks passed.
Artifact rebuild completed; 20 prior reports unchanged; 20 selected reports match staged.
Bank:1265 cases /3677 required targets /3397 targets missing cases.
Observed replay:20 captures /79 gaps. Completion false:2570 identities,62891 occurrences,
1325 reviewed,4777 excluded,7991 coverage rows,111775 remaining tasks.
Full-suite / whole-bank / host-delivery checks remain pending. All processes terminal.
Logs tmp/zeal-blood-ring-*.

Next: Zeal charm configurations, source spans173–184 inspected, no changes yet.
Main planner n8010616:173 item19 Fine+GoodLuck(prefix256/suffix291);
174 item110 Steel+GoodLuck(prefix237/suffix291);175 item70 Fine+Vita(256/349);
176 item24 Fine+Balance(256/267);177 item20 Shimmering+GoodLuck(322/291);
178 item64 Shimmering+Vita(322/349).
Starter planner rk0106ln:179 item71 Fine256;180 item31 GoodLuck291;
181 item69 Vita349;182 item68 Shimmering322;183 item67 FireResistance369.
Planner1w0106kl:184 item134 Sharp Large Charm of Vita(prefix255/suffix346).
Native ranges and broad Resistance-label alternatives still require review before gates.
Continue other builds/families and all completion-contract requirements after these.

## Latest active checkpoint — three Zeal caster amulet branches, 2026-09-27

Goal ACTIVE,unfinished. Selected generation
`e9e51659976f7af3b141a51814283034ba08b414ce4aa63d9c12d6a2c8dea601`,72artifacts,
2408profiles/2400statconfigs. No livecollection/commit/staging/hostrestart. Prior
socket-child decoder/SacredRondache Pythonhostrestart remainsunverified.

Added maintenance/zeal_caster_amulet_templates.py with3distinct exactsource rules:
zeal-paladin-caster-amulet-teleport span154; resistance-mf155;fast-mf156.
Allcraftedamulet/noneth/zerosockets/Paladin,2Palskills,recipeFCR5/mana10/regen4 minima.
Teleport usescharge_skill54 nativepresence anddependsremainingcharge>=1 plusknown
player_items withoutEnigma. Life/leech supportingobservedaffixes, notcraftguarantees.
ResistanceMF needsnativePrismatic16allres andcombinedMF21minimum. FastMF accepts
15FCR(craft5+suffix10),prefers20,MF21. Maxplannerrolls notmandatory. FCR≠ZealIAS.
No genericnumericprice disclaimer addedtoreportconditions;equipmentrequirements noted.
One-shot tmp/add_zeal_caster_amulets.py SUCCEEDED; NEVER rerun. Initialbuild validation
rejectedcharge:54 inprofile important_stats(whichacceptsnativekeys only). Fixedtemplate
filtercharge markerfromimportant_stats butretainedsemanticchargepriority instatreview;
re-expandedonly3roles andrefreshedfingerprints/conditions; do notrerunadder.

Bank cases/zeal_caster_amulets.py18red ->18stagedpass ->18selectedpass.
Positive lowroll,wrong/unknownclass,completeabsent vsincompleteunreadFCR;Teleport
Enigma/unknownarmor/emptycharges allblockthatconfiguration. Skill54layer=(54<<6)|3,
rawcurrent1/max27. Regenstat27 verifiednative.18statbundle/charges/bankcoverage
regressionspass;ruff/checkformat/diffcheckpass. Repeatableartifactrebuildcompleted.
20savedreports unchangedvspriorgeneration and20selectedmatchstaged extraction/text/price.
Bank:{'cases': 1259, 'required_targets': 3676, 'targets_missing_cases': 3397}. Observed20/79gaps. Completioncounts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1324, 'excluded_occurrences': 4777, 'coverage_rows': 7990, 'remaining_tasks': 111771};completefalse.
Allprocesses terminal. Logs tmp/zeal-caster-amulets-*.
Fullsuite/wholebank/hostdelivery stillpending.

NEXT BloodCraftedRing Zealspan168 hasNOcraftedRingrole(compiledinspected).
IMPORTANT source profile_id is1w0106kl,NOTmainn8010616. Initiallycheckedwrongplanner
andreportedapparentconflict; correctedusercommentary afterreadingactualspan. There
isNOsourceconflict. pricing/raw/mr/planners/1w0106kl.json cacheditem120 iscrafted:
cube080[LL3,life20,Str5], suffix357LL8,prefix243AR120,suffix331life40,suffix230min9;
totals11LL/120AR/60life/9mindmg/5Str. Nativecube/affixlegality needreviewbeforegate.
Mainplanner n8010616 item120 isNagelring(span169); IDsareplanner-local, nevercrossjoin.
Afterring, Zealcharmpatterns173.. onward remainpending(Fine/Steel/Shimmering combinations,
Vita/Balance/MF etc); inspectexistingrules/bankcoverage beforeadding. Continueall
otherbuild/family/contractdimensions afterZeal. No intermediatebatchfinishclaim.

## Latest active checkpoint — Zeal Blood gloves and rare belt, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`bfc3e79e394f892a8d2c0ed2492f46c36d8f0196c333933ed13ceed215bb74e6`,72artifacts,
2405profiles/2397statconfigs. No livecollection/commit/staging/hostrestart. Previous
socket-child Pythonfix/SacredRondache report restart stillunverified.

Added maintenance/zeal_affixed_accessory_templates.py andtwoexactsource rules:
zeal-paladin-blood-gloves-alternative(span127/planner95): craftedHeavyGloves/
Sharkskin/Vampirebone family nativecube75,20IAS andrecipe minimum1LL/5CB/10life.
AdditionalStrength/lightningres/MF prioritizedwhenobserved, notguaranteedcraft.
zeal-paladin-rare-belt-alternative(span144/planner105): rarebelt branchcovering
Stability24FHR,AtlasStr21..30,Colossuslife41..60 andfire/lightning/cold21..30.
Allsixaffixes' lowerrolls qualify; plannerperfect30Str60life30res notminimum.
Doesnotclaimallotherbeltsworthless; source-specific branch, comparepotionrows,
fullres/FHRloadout andequipmentrequirements. Bothnoneth,zerosockets,Paladin.
Nativecube75,suffix170/287/386/264/377/318,prefix392/372/353 inspected.
One-shot tmp/add_zeal_affixed_accessories.py SUCCEEDED; NEVER rerun. Roles,
manifest,patternguideuses,statreviews,counttest2397updated. Adderadaptedhelm
script butnewtemplate separate; sourceusespattern_label exactspan label.

New bank cases/zeal_affixed_accessories.py10red ->10stagedpass ->10selectedpass.
Lowrollpositive,wrongclass,unknownclass,completeabsentcore vsincompleteunreadcore.
7statbundle/bankcoverage regressionspass;ruff/checkformat/diffcheckpass.
Repeatableartifactrebuildcompleted,20savedreports unchangedvspriorselected,
20newselected matchstaged extraction/text/price. Bank1241cases/3673targets/
3397missing;observed20/79gaps. Completion counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1321, 'excluded_occurrences': 4777, 'coverage_rows': 7987, 'remaining_tasks': 111759};completefalse.
Allprocesses terminal. Logs tmp/zeal-affixed-accessories-*.
No wholebank/freshfullsuite/hostdelivery claim.

NEXT implementthree Zeal casteramuletbranches154/155/156 (planner39/172/84),
perpreviouscheckpointexamples. Freshnativefacts: cube88regen4..10,mana10..20,
FCR5..10; suffix174adds10FCR. Teleportation suffix533 skill54,level48 affix,
parammin-20/max-3; sourceplanner39 level3Teleport27charges,6LL,Lamprey744fixed6,
60lifeColossus318,2Palprefix565. DoNOTtreatcharges aspassiveoskill; footnote4
onlywhen noEnigma. MFprefix281Felicitous5..10 plusFortune28716..25 yields21..35;
Prismatic331allres16..20. Planner172has2Pal10FCR20allres35MF;84has2Pal20FCR35MF.
Use existing charged/prebuff predicates/context forsourceconstraints. No source
variant collapsing justbecauseallthree labels areCasterCraftedAmulet. Thencontinue
allremainingZeal andallotherbuild/family/contractwork.

## Latest active checkpoint — Zeal named accessories linked, 2026-09-27

Goal ACTIVE,unfinished. Runtime unchanged:selected83be3e1c6e1994ec221cfee7da9ab2ad4022f92406a4a35dc9510c8634855f1c,
2403profiles/2395configs. No publication/livecollection/commit/staging/hostrestart.
Prior socketchild Pythonfix stillrequires unverifiedhostrestart.

Reviewed and linked8existingrules to exactsection32 spans:133Steelrend,
136MagnusSkin,138StringofEars,139NosferatuCoil,140Verdungo,148WarTraveler,
149GoreRider,150GoblinToe. Native/upgradedbase,noneth,non-socketability,
playerclass andstatrecipient restrictions unchanged. OffweaponED/IAS,
CrushingBlow/DS/OW,physicalvsflatmagicreduction,wearerkillcredit andMF separated.
One-shot tmp/add_zeal_accessory_bindings.py SUCCEEDED; NEVER rerun.
Allsource_context_reviews validated beforewrite; no productionrule changes.

Six accessories alreadyhad dynamicbankcases inzeal_melee.py; didnotduplicate.
Added cases/zeal_named_gloves.py6cases forSteelrend andMagnus usingverifiednative
unique391/set106. LowSteelrend30ED/10CB/15Str;Magnus20IAS/100AR/15FR/50EDef.
PositivePaladin/wrongclass/unknownclass statconfig checks.24new+existingaccessory
casespass (1207deselected). Ruff/checkformat/diffcheckpass.
Bank1231cases/3671targets/3397missing scenarios. Completion counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1319, 'excluded_occurrences': 4777, 'coverage_rows': 7985, 'remaining_tasks': 111751};
completefalse. Allprocesses terminal. Logs tmp/zeal-accessories-*.
No wholebank/fullsuite orhostdelivery claim.

NEXT genuine missing Zeal rules (compiledprofiles inspected):127BloodCraftedGloves,
144RareBelt,154/155/156CasterCraftedAmulet. Only existingamuletrole is magic/rare
TeleportChargeAmulet footnote, notcrafted. Freshlyinspectedn8010616 planner examples:
95(VampireboneGloves):cube075 blood3LL20life10CB +20IAS25MF15Str30LR.
105(VampirefangBelt rare):24FHR30Str60life30fire/lightning/coldres;native6affixes.
39(amulet crafted):cube08810FCR20mana10regen +2Pal,level3Teleport27charges,
6LL60life. Teleportfootnote4 applies onlywithoutEnigma; charge-use notpassiveoskill.
172(amulet crafted):10FCR20mana10regen +2Pal,35MF(prefix10+suffix25),20allres.
84(amulet crafted):20FCR(craft10+suffix10),20mana10regen,+2Pal35MF.
Preserve distinctsourcebranches; guide values areperfectexamples, notuniversally
requiredminimums. Readnativecube/affixdefinitions andrecipientsemantics before
thresholds; keep sourcevalues separatefromwholeloadoutbreakpoints. Source spans
pointtoitems95/105/39/172/84 respectively. Implement redgreen independentbankcases,
rebuild/publish/replay, thenremainingZeal andallothercontractwork.

## Latest active checkpoint — explicit player-pattern source bindings, 2026-09-27

Goal ACTIVE; unfinished. Runtime unchanged:selected83be3e1c6e1994ec221cfee7da9ab2ad4022f92406a4a35dc9510c8634855f1c,
2403profiles/2395configs/72artifacts. Maintenanceonly,no republication/commit/staging/
livecollection/hostrestart. Socket-child Pythonfix restart stillunverified.

Extended source_context_reviews with player_pattern for unresolvable short generic
source labels (categoryNone,identity_statusunresolved), retainingall existingnamed
rules. Requiresnativeplayerclass/explicitmatching slot, pinned exactspan/hash,
fullsameguidequote andoriginal label, reviewedendorsedpattern role/fingerprint,
nonemptytypes, supportednormal/superior/low_quality/magic/rare/crafted qualities
matchingexplicitbranch list, no namedidentity role, pattern_label matchesendorseduse.
Exactquotedlabels accepted. Explicit 'Empty preparation base for ' / 'Completed '
prefixes accepted onlywhen socket_contents empty/filled mandatoryoneverypath;
no arbitraryprefix stripping. Named/mixedquality orwrongpattern/class rejected.

New tests maintenance/test_pattern_source_context.py:initial1meaningfulred/6pass
(afterfixingfixturehelper'sdefaultitem);9patternchecks includingpendingbranches and
bothpreparationprefixguards. Combined70pattern/player/merc/completionchecks pass.
Ruff/checkformat/diffcheckpass. No runtime reportchanges.

Persisted4reviews forZeal73Rubyshield (both empty+filledbranches),75Istshield(both),
107TopazMask,109ResistanceMask. Fullquote distinguishes samebarelabels. Existing
payload/nativeaffix/core gates retained; no sourceorvariant rewriting.
One-shot tmp/add_zeal_pattern_bindings.py SUCCEEDED; NEVER rerun. Firstattempt failed
beforewrite because existing shieldpattern labels includepreparationprefixes;
handledstructurally above, thenvalidatedallreviews beforewrite.
Completion counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1311, 'excluded_occurrences': 4777, 'coverage_rows': 7985, 'remaining_tasks': 111759};completefalse. Allprocesses terminal.
Bank remains1225cases/3671targets/3399missing;20observed/79gaps. Fullsuite/wholebank
andhostdelivery remainpending. Logs tmp/pattern-source-*.

NEXT authoritativeZeal queue section32 spans125..165 stillpending:
127BloodCraftedGloves,133Steelrend,136MagnusSkin,138StringofEars,139NosferatuCoil,
140Verdungo,144RareBelt,148WarTraveler,149GoreRider,150GoblinToe,
154/155/156CasterCraftedAmulet. Determine existing reviewedrules versus genuine
missingconfigurations beforeadding. Named items mayneed exactplayerbinding like
previousbatches; craftedamulets have distinctplannerpayloads andmustnot collapse
samebarelabel. Inspect nativeitems/planners andensure independentbankcoverage.
Thencontinue allremainingbuilds/families/contractdimensions. Never stopatbatchgate.

## Latest active checkpoint — specialist shield bank and pattern-binding audit, 2026-09-27

Goal ACTIVE, unfinished. Same selected83be3e1c6e1994ec221cfee7da9ab2ad4022f92406a4a35dc9510c8634855f1c,
2403profiles/2395statconfigs. No runtime changes/republication/livecollection/commit/
staging/hostrestart. Previous socket-child Pythonfix stillrequires unverifiedrestart.

Added cases/zeal_specialist_shields.py20 independentpipeline cases for existing
ruby-empty/ruby-filled/ist-empty/ist-filled specialistshield roles. SacredTarge
magic4s20block30FBR with27allres (45 ispreference, notminimum). Rubyfilled4 actual
31ED15IAS jewels, parent124ED60IAS; Istfilled4Ist+100MF. Perrole positive,wrongclass,
unknownclass; filledwrongfourthEl andunreadchildren; empty3snear-miss/unknownsockets.
All20selectedpass (1205deselected). No earlier bankcovers foundprogrammatically.
Ruff/checkformat/diffcheckpass. Bank:{'cases': 1225, 'required_targets': 3671, 'targets_missing_cases': 3399}.
Completion counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1307, 'excluded_occurrences': 4777, 'coverage_rows': 7985, 'remaining_tasks': 111763};completefalse. Allprocesses terminal.
Logs tmp/zeal-specialist-shields-*. No fullsuite/wholebank claim.

AUDIT exactpending patternsource IDs:
73Ruby: b28f81ac73c3983570d3e3ed;75Ist:86dc102fd64c21470eae9be7;
107MaskTopaz:f13b435a5aba420eba2a74e3;109MaskRes:fb16209a5eb2fcf8315ec7af.
AllcategoryNone/identity_statusunresolved,variantGuide mention,sourceRuleIds[];
original_labels omitparenthesizedfillers. Existingroles variantGear alternatives,
sourcewhole section32; usepattern_labels includefullparentheses. Thus deliberately
notmatched by review_dossiers._pattern_bindings(exactlabel/source/variant/slot).
Do NOTstripfillerlabels globally orcreditbothsame-name variants blindly.

Planner n8010616 freshly inspected:146SacredTarge Jeweler422/Deflecting173,4s45allres,
children3,3,3,132 each40ED15IAS;144samebase/affixes4Ist;147Mask3PTopaz;
138MaskRalOrtThul. Sourcespans73/75/107/109 pointexactly tothoseitemIDs.
NEXT: extend source_context_reviews with explicit player_pattern kind orsimilarly
strict binder. Existingonly namedresolved unique/set/word eligibility; namedbinding
muststayunchanged. Patternbinding needs exactspan/hash/class/slot, fullsameguide
quotedconfiguration, endorsedpatternrole/fingerprint, branchpattern_label matching
thatquote, no names onrole, requiredplayerclass onEVERYsuccessfulpath; explicitall
branches (shieldempty+filled) andremainingbranches. Preserve separate sourcecontext
androlevariant. Current namedsourcecontext compiler/tests are suitable scaffold.
Test wrongfillerbranch/name-only/changedspanhash/missingbranch unknown cases redgreen.
Persist onlythese4reviewedsourceoccurrences onceverified, thenfollowrestofqueue.

## Latest active checkpoint — socket-child grouped stats and Zeal payload bank, 2026-09-27

Goal ACTIVE; unfinished. Selected runtime remains
`83be3e1c6e1994ec221cfee7da9ab2ad4022f92406a4a35dc9510c8634855f1c`,2403profiles/
2395statconfigs/72artifacts. Python decoder fixed; runtime artifacts unchanged so no
new publication. Hostworker restart REQUIRED and stillunverified. No hostaction,
livecollection,commit orstaging.

Added item_bank/cases/zeal_socketed.py27cases for7existing socketconfigurations:
GuillaumeCham/Um/Ber/RubyED31IAS15,Griswold3Ist,Mask3PTopaz andRalOrtThul
(normal+superior). Actualchildpositive,wrongElchildren withsameaggregatesnegative,
unknownchildren withsameaggregatesunknown. No previous bankcovers for theseids.
Initial26pass1fail exposed realdecoderbug: socket_payload.decode_payload processed
only memory_stat, dropping groupedED memory_stats while claimingstats_complete.
Rubyjewel child ED wasthus incorrectly treatedas0 evenwhen parentED31/IAS15matched.
Added lowlevel test includinggroupedED andpoison(native rates/duration/sourcecount):
redthenfixediterate allmemory_stats anduse native_values perkey withunits. Never
copy combinedpoison damage into individualcomponents. 29bank+decodertestspass.
67socketannotation/compoundjewel/counting/Zealhelm/sourcecontext regressionspass.
Ruffcheck/format/diffcheckpass.20savedcapture extraction/text/pricesunchanged.

Explicitplayer sourcebindings5 appended for77Griswold,88Cham,90Ruby,92Um,94Ber;
wholequotedconfig, exactsource fingerprint/class/slot and existingdependencies kept.
One-shot tmp/add_zeal_socket_bindings.py SUCCEEDED; NEVER rerun. Compiledallreviews
beforewrite. Sourcecontexts maintenanceonly. Maskgeneric bindingsstillneedaudit.
Bank1205cases/3671targets/3403missing fullscenarios (9fewer);observed20/79gaps.
Completion counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1307, 'excluded_occurrences': 4777, 'coverage_rows': 7985, 'remaining_tasks': 111763};completefalse. Allprocesses terminal.
Logs tmp/socket-grouped-*,tmp/zeal-socketed-bank.log(initialred).
Wholebank/freshfullsuite andhostdelivery remainpending.

NEXT sourceclosure: inspect actualcompletionqueue for exactZeal GemmedMask source
spans107/109 versus existingpattern_labels fullparentheses; do notinventnewprofiles.
Afterhelmet/socketbinds, continueotherZeal remainingguideuses thenallbuilds/families.
Potentialremaining JewelerSacredTarge spans73/75 (EDIAS vsIstpayloads) deserve same
fullpipeline bankcoverage; groupedEDfix now makes actualchildED available. Check
existingrules anddynamicallyconstructed bankcovers beforeadding. No intermediate
batchconstitutes completion.

## Latest active checkpoint — Zeal affixed helmet alternatives, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`83be3e1c6e1994ec221cfee7da9ab2ad4022f92406a4a35dc9510c8634855f1c`,72artifacts,
2403profiles/2395stat configs. No livecollection/commit/staging/hostrestart.

Reviewed section32 span98RareCirclet/planner99 and99BloodCraftedArmet/planner107.
Planner99:Diadem rare2Pal20FCR Visionary2,2s,40life25MF; prefix565/539/420,
suffix175/331/287 verified native legal3prefix3suffix. Planner107:Armet Blood craft,
cube73 nativeleech1..3/life10..20/DS5..10 plus2s,life40,Visionary2,EDef200;
prefix668Godly101..200. Both examples haveCham/Ber (native misc r32/r30verified).
No source's exact perfect roll or example filler treated as universal requirement.

Added maintenance/zeal_affixed_helm_templates.py two roles:
zeal-paladin-rare-circlet-alternative:rare circ type,2Pal20FCR core,Visionary/life/MF
andobservedsocketstat priorities; FCR is castingnotZealIAS.
zeal-paladin-blood-helm-alternative:crafted nativeHelm/Casque/Armet family frommetadata,
Visionary positive + nativeleech1/DS5/life10 core. BothPaladin/noneth/identified,0..2s,
2s preference for linkedpayload. No complete breakpoint, guaranteedUbersleech or
priceinferred. No seteffects. Bodydetails explain actualsocket bonuses.
One-shot tmp/add_zeal_affixed_helms.py SUCCEEDED; NEVER rerun. Initial guide-use item
binding rejected because affixed profiles have no names. Corrected newuses to
pattern/profileid + pattern_label + pattern_source_slot; no namedidentityfiction.
Initialrules omitted absent_is_zero: complete missingcore stayedunknown. Meaningful
red-green fixed muststatpredicates absent_is_zerotrue (stillunknown incomplete/gapped).
Re-expanded onlynewroles and updatedsource/stat fingerprints, notsuccessfuladder.

Itembank cases/zeal_affixed_helms.py10red ->8pass2fail ->10stagedpass ->10selectedpass.
Examplepositive,wrongclass,unknownclass,completeabsentcore,incompleteunreadcore forboth.
25statbundle/sourcecontext/bankcoverage checks pass; ruff/format/diffcheckpass.
Repeatable fullartifactrebuild completed.20saved reports unchangedvsTal generation,
20selected matchstaged extraction/text/price. Publishedgeneration above.
Bank1178cases/3671targets/3412missing;observed20captures/79gaps.
Completion counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1302, 'excluded_occurrences': 4777, 'coverage_rows': 7985, 'remaining_tasks': 111768};completefalse. All launchedprocesses terminal.
Logs tmp/zeal-affixed-helms-*. No wholebank/freshfullsuite claim. HostPythonrestart
stillunverified for priorSacredRondache/compactSocketreportchanges.

NEXT continue remainingZeal exactsource configuration closure: socketedGuillaume,
GriswoldHonor and gemmedMask profiles exist but their source occurrences may need
explicitpattern/source-context bindings and independently authored fullpayloadtests.
Inspect existing rules/bankcases beforeadding; no duplicateprofile creation based
on a failedliteralIDsearch. Follow actualcompletionqueue to source/unreviewedfamily
work afterward; all other contract dimensions still required.

## Latest active checkpoint — Tal helm Zeal alternative, 2026-09-27

Goal ACTIVE, unfinished. Published selected generation
`966b512f53b35d18a074454c5eb79d19a74840298ea1407218d413bbb40d8fca` (72artifacts),
2401profiles/2393stat configurations. No livecollection/commit/staging/hostrestart.

Added zeal-paladin-tal-rashas-horadric-crest-named-alternative from exactsection32
span105. Native setitems Tal Rasha's Horadric Crest row80: mana30/life60/flatdef45/
allres15/dual leech10. Linked n8010616 item141 nativeDeathMask andsocket28 jewel15IAS.
Template zeal_named_templates now accepts explicit member quality(defaultunique),
uses named_base_condition qualityset; originalDeathMask/upgradedDemonhead,noneth,
0/1socket,Paladin retained. No companions/complete set,IAS withoutobservation or
LifeTap healing assumed. Includes8native utilitystats plusobservedIAS annotation.
One-shot tmp/add_zeal_tal_helm.py SUCCEEDED; NEVER rerun. Roles,reviewedmanifest,
guide_use_reviews,stat_use_reviews and expectedstatbundle count updated.

Bank cases/zeal_tal_helm.py:6red then6stagedgreen and6publishedgreen. Native/upgraded,
actual15IASjewel,wrongclass,missingclass,unknownsockets. No Paladin skill/fullset bonus
asserted; native health/mana usefixedpoint256. Added lowerlevel downgradedMask
rejection;7template/statbundle tests,10upgrade/ethereal/bankcoverage regressionspass.
Ruff/format/diffcheckpass. Fullbank/fullsuite stillpending.
Rebuilt via tmp/final-charge-routing-rebuild.py (repeatable).20saved replays unchanged
vs previousselected for extraction/text/price;20newselected matchstaged. Bank1168cases,
3669targets,3412missing scenarios;observed20/79gaps. Completion initially correctly
rejected staleobserved-review hash incoveragematrix; regeneratedmatrix thencompletion
passed. Counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1300, 'excluded_occurrences': 4777, 'coverage_rows': 7983, 'remaining_tasks': 111760};completefalse. All launchedprocesses terminal.
Logs tmp/zeal-tal-*. SacredRondache/compactsocket Python hostrestart stillunverified.

NEXT actual unimplementedZeal helmet uses:section32 spans98RareCirclet/planner99,
99BloodCraftedArmet/planner107. CompiledZeal profiles have no magic/rare/crafted
Helmets role. Inspect exactplanner rolls, source text/native affix/craft legality,
review stat priorities and fullsetup thresholds; implement independent scenarios.
Guillaume socket variants/Griswoldshield sourcebinding audits remain; avoid duplicate
rules. Fiveunique helmet alternatives already sourcebound andbanktested in previous
checkpoint. Continue allremaining completioncontract work, notjustZeal.

## Latest active checkpoint — Zeal helmet verification, 2026-09-27

Goal ACTIVE, unfinished. Same selected runtime723bb142aefbf15cee3cf7a3f058904d634c8915b79718887eb483417525c328;
no production artifact changes or republication this turn. Previous turn was progress.

Added16 complementary item-bank cases in cases/zeal_helmets.py: Crown of Ages,
Vampire Gaze, Rockstopper, Crown of Thieves, Harlequin Crest. Independently native
low rolls verify every reviewed relevant stat, wrong player class and missing class;
Crown of Ages also verifies second socket. Existing zeal_melee.py dynamically builds
these role names, so plain full-id search missed its3cases/item. Removed overlapping
newethereal tests; kept complementary fullstats/class checks. Existing15 plus new16
pass (31passed,1131deselected). Initial Shako fixture failure was incorrect fixedpoint
raw hp/mana perlevel: nativeparam12 must become12*256 in memory. Decoder denominator
2048 confirmed; corrected fixture gives120life/mana atviewer80. No production bug.
Ruff/checkformat/diffcheck pass. Logs tmp/zeal-helmets-bank-final.log,
tmp/zeal-helmets-bank-coverage-final.log,tmp/zeal-helmets-completion-final.log.
Bank counts:{'cases': 1162, 'required_targets': 3668, 'targets_missing_cases': 3412}. Missing targets unchanged because these roles already had minimal
scenarios; new cases deepen verification, not new assessed identities.
Completion counts:{'identities': 2570, 'occurrences': 62891, 'reviewed_occurrences': 1299, 'excluded_occurrences': 4777, 'coverage_rows': 7982, 'remaining_tasks': 111756}; completefalse. All launched processes terminal.

NEXT actual source/configuration gap: Zeal section32 span105 Tal Rasha's Horadric
Crest has NO exact-name role in compiled profiles (checked allZeal roles). Inspect
native set definition, linked planner n8010616 item141, conditions and build wearer,
then implement with independent bankcases. Do not assume helm set effects beyond
native standalone bonuses. Existing helmets96/97/100/101/104 already sourcebound;
Griswold77,Guillaume88/90/92/94 and magic/gemmed remain audit leads from previous
checkpoint. Continue fullcontract; wholebank/freshfullsuite and hostrestart pending.

## Latest active checkpoint — explicit player source reviews and bank, 2026-09-27

Goal ACTIVE, unfinished. Runtime unchanged: selected generation
`723bb142aefbf15cee3cf7a3f058904d634c8915b79718887eb483417525c328`,
2400 profiles/2392 stat configurations. No live collection, host restart, staging or commit.

Extended maintenance/source_context_reviews.py with explicit player_equipment reviews.
Pins source span/hash, original context including class, same-guide quotation and role
fingerprint; requires matching native identity, rarity, build, side and explicit slot,
plus mandatory player_class on every successful predicate path. Only Body Armors/Body
Armor and Off-Hand Swap/Off-Hand-Swap aliases accepted. Nonempty configuration review
required; remaining branches remain pending. Existing mercenary behavior preserved.
Initial red1/pass7; then79 player/merc/completion/Hustle checks pass.

Added seven reviewed Zeal source bindings: Death Cleaver57, Razor's Edge65, upgraded
Butcher's Pupil66, Honor Naga67, Alma Negra72, Leviathan118, Stone119. Upgrade, exactbase,
Zod, durability and filled recipe constraints retained; no same-name blanket credit.
One-shot tmp/add_zeal_player_source_bindings.py SUCCEEDED; NEVER rerun.

New item_bank/cases/zeal_existing_alternatives.py supplies33 positive/negative/unknown
cases (including normal/superior/low_quality runewords). All33 pass against selected
runtime;1113 deselected, not wholebank. Native observed stats and specific configuration
annotations asserted. Bank now1146cases/3668targets/3412missing scenario sets (11 fewer).
Ruff check/format and git diff --check pass. Maintenance-only changes did not republish.
Completion refreshed:2570identities,62891occurrences,1299reviewed,4777excluded,
7982coverage rows,111756remaining tasks; completefalse. All processes terminal.
Logs tmp/player-source-context-*, tmp/player-source-bank-coverage.log,
tmp/zeal-existing-bank.log. Wholebank/freshfullsuite remain pending.

NEXT: continue exact Zeal source review. Spans73/75 magic Jeweler's Sacred Targe,
77Griswold's Honor,88/90/92/94Guillaume's Face socket variants,96Crown of Ages,
97Vampire Gaze,98rareCirclet,99craftedArmet,100Harlequin,101Rockstopper,
104Crown of Thieves,105TalRasha,106Sigon,107/109gemmedMask need inspected source
configuration/role matching; never infer filler from neighboring names alone. These
are candidate audit leads, not newly reviewed facts. Continue remaining contract
work; neither this batch nor universal named-tier baseline completes the goal.
Sacred Rondache base advice already published; active worker Python restart remains
unverified, as does compact socket-requirement reporting on host.

## Latest active checkpoint — Zeal named remainder and actionable sockets, 2026-09-27

Goal ACTIVE; unfinished. Selected generation `723bb142aefbf15cee3cf7a3f058904d634c8915b79718887eb483417525c328` (72 artifacts),
2400profiles /2392stat configurations. No live collection, commit, staging or host restart.

Closed Hustle audit alias gap first. source_matching.occurrence_name_matches accepts
bare Hustle only for reviewed armor/weapon names, exact source/role slot, explicit types
(armor tors; existing weapon abow/bow/pole/spea/swor), and a recipe equality mandatory
on every successful path. completion uses it alongside all existing exactsource/build/
variant/side checks; quality matching preserves exact-name behavior.6red/12negativepass
then71completion/context/alias tests pass. This closed24existing reviewed Hustle source
references (including Zeal64/122). No source rewriting or general parenthesis stripping.
Completion occurrence_dispositions excludes ordinary reviewed entries; use queue IDs
for pending checks, not absence from that list. Previous nine-role/eight-review mystery
was Hustle armor variant naming, not Temper's empty item_id.

Added source spans60ethRuneMaster,69HeraldZakarum,71Stormshield,116SkulldersIre via
maintenance/zeal_named_templates.py. Nativeunique rows313/285/253/217 verified; raw JSON
keys numeric and RuneMaster native index text Runemaster. catalog maps correct bases:
EttinAxe,GildedShield,Monarch,RussetArmor. Native upgrade chains preserved. Linked planner
n8010616 data/items115/52/89/148 reviewed: RuneMaster5s[Lo,Lo,Zod,jewel3,jewel3], jewel3
40ED/15IAS; Herald upgradedZakarumShield+jewel3; Stormshield+jewel3; Skullder+Um.
These are examples, not minimum roll gates. RuneMaster candidate requireseth+3..5s,
required_socket_itemZod, preference5s. HoZ eth needs observed152Indestructible; Skullder
eth needs observed252repair; Stormshield nonethnative. Player skills, block vs IAS,
level-scaled stats and observed socket effects separate. No price invented.
One-shot tmp/add_zeal_named_remainder.py SUCCEEDED; NEVER rerun.

Bank initially29red. Added3/4socket boundaries, moved4 impossible unique/base mismatches
to lower-level tests because native item-bank identity validation correctly rejects
constructing them. MissingZod correctly suppresses ready-use stat configs, remains
partial with explicit socket preparation. Final27staged/27selectedpass;4invalidbase
checks pass (wrongtype may be excluded before role trace).24related named/ethereal/
statbundle/coverage regressions pass. Additional preparation/presentation run28passed,
1invalidbase fixture expectation fixed;4template checks thenpassed. Socket summary
red-green separatelyverified. No wholebank/fullsuite claim.

Reporting fix: RoleAssessment now has optional structured socket_requirement with
item,confirmed,applicable. profiles supplies it using existing verified socket detection
and can_prepare. build_use_summary shows deduplicated applicable unconfirmed requirements,
strips Rune suffix, hides confirmed/unrelated cases. Example 'Socket requirement: Zod
(not confirmed)'. SavedSazabi now shows missingCham line; all20saved decodedstats/prices
unchanged and othertextunchanged.20selected matchesstaged. Python worker restart needed
for this change too; hostrestart unverified. Ruff/format/diffcheck pass.
Bank1113cases/3668targets/3423missing scenario sets; observed20captures/79gaps.
Completion counts:{"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1292, "excluded_occurrences": 4777, "coverage_rows": 7982, "remaining_tasks": 111763}; completefalse.

NEXT: audit exact source bindings for already-existing section32 Zeal rules, rather than
duplicate them. Compiled bundle (not only roles/zeal-paladin.json) contains DeathCleaver57,
RazorEdge65,ButchersPupil66,HonorNaga67,AlmaNegra72,Leviathan118,Stone119. Many socket/
set/affixed source configurations stillpending. source_context_reviews currently only
handles merc narrative bindings; a rigorously tested explicit player-binding extension
could close reviewed equivalent occurrences while retaining exactspan fingerprints,
sameguide quoted evidence, nativeidentity/quality, wearer and full branch review.
Do not blindly credit same-name mentions or incompatible sockets/upgrades. Continue
all remaining contract dimensions afterward; no intermediate batch completes the goal.
Logs tmp/hustle-source-* and tmp/zeal-named-*. All launched processes terminal.

## Latest active checkpoint — Zeal armor/helmet words, 2026-09-27

Goal ACTIVE; unfinished. Selected generation `91370f46e4e0a5ba78bebe3e666e98f184b7eee30245888c0c0b9412816c5682` (72 artifacts),
2396profiles /2388stat configurations. No live collection, commit, staging or host restart.

Added nine player alternatives from section32 exact spans: Enigma113,Fortitude114,
Chains of Honor115,Duress120,Hustle(armor)122,Lionheart124,Smoke125,Bulwark102,Temper103.
New maintenance/zeal_equipment_templates.py: native recipe/socket legality and noneth
sustained player durability; player attributes, offweapon physical damage, level scaling,
conditional procs, targets, casting vs IAS vs recovery, and armor vs weapon rune effects.
Smoke usable Weaken highlights only with remaining charges; losing charges does not
remove its armor utility, and applying Weaken can replace Life Tap. Treachery prebuff
remains separate. No price or current NL creation availability inferred.
One-shot tmp/add_zeal_armor_words.py SUCCEEDED; NEVER rerun. Initial build rejected
synthetic charge:72 in role important_stats. Corrected template+Smoke role to native
204:4614 and repinned that role's source/stat fingerprints; stat priority correctly
retains charge:72 with charge_skill activation. Rebuild then passed.

Bank195cases:168red/27already-correct routing exclusions; firstgreen192pass/3Fortitude
fixturefail. Fixed captured hp-per-level raw8->8*256 (nativeValShift8), then195staged
and195selected pass. Lowquality Enigma defense fixture870 vs regular1000, consistent
with lower base defense. Covers3qualities, lowrolls, wrongfamily/socketcount, empty,
eth/unknowneth/unknownclass; Smoke depleted/unknown charges remain armor-positive but
have no usable-charge annotation.64related regressions passed, 1Fortitude demand count
updated15->16 and recheckedgreen; 65combined.20saved extraction/text/prices unchanged;
selected matchesstaged. Ruff/format/diffcheck pass. No fullsuite/wholebank claim.
Bank1086cases/3664targets/3423missing scenario sets; observed20captures/79gaps.
Completion counts:{"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1264, "excluded_occurrences": 4777, "coverage_rows": 7978, "remaining_tasks": 111771}; completefalse.

NEXT: compiled bundle confirms NO Zeal roles for Rune Master(span60 ethereal), Herald
of Zakarum69,Stormshield71,Skullder's Ire116. Review these named alternatives, including
repair/Indestructible and socket dependencies. Do not assume names match uniqueitems
JSON top-level keys (simple lookup printed no records; inspect schema).
Other missing exactspan bindings already have compiled Zeal roles with section32 sources:
DeathCleaver57, Razor'sEdge65, Butcher'sPupil66, HonorNaga67, AlmaNegra72, Leviathan118,
Stone119. Audit exact source linkage instead of duplicating rules. More broad bindings
include sockets/companions and require semantic review, not automatic name credit.
Completion direct named matching currently requires exact occurrence_source plus same
build/variant/side/slot; source_context_reviews currently ONLY supports merc narrative
bindings. A rigorously tested player-binding extension may help existing named uses,
but never relax exactspan/sourcefingerprint/context/branch review gates.
Then all other contract scope. Runtime Python restart for SacredRondache/Trainer remains
unverified. Logs tmp/zeal-armor-words-*. All launched processes terminal at checkpoint.

Follow-up audit: nine new roles increased reviewed occurrence count by eight. Check which exact source remains uncredited (likely variant naming; not yet established). Temper span103 is resolved runeword with exact source_rule_id; do not assume its empty item_id is the cause. Completion occurrence_dispositions is not necessarily a full ID map (direct indexing raised KeyError); inspect semantics before interpreting absence.

## Latest active checkpoint — Zeal CTA and Spirit swaps, 2026-09-27

Goal ACTIVE; unfinished. Selected generation `b7cc293c29bccba9ea6e282a8be34d4c6d5dacabab9b1f464409becaa07449a2` (72 artifacts),
2387 profiles /2379 stat configurations. No live collection, commit, staging or host restart.

Added exact Zeal section32 spans81 Call to Arms Weapon-Swap and87 Spirit Off-Hand Swap,
with section29 corroborating prebuff/Teleport instructions. Reused core_caster_word_templates:
Zeal limited to these two recipe/slot pairs; normalized local slot for processing while
retaining source slot spelling. Spirit supports ordinary and Paladin shields; +fire resist
is inherent, not Spirit rune effect. CTA native minimums BC2/BO1, no attack-stat priority;
ethereal/twohanded prebuff accepted, no shield companion or active buff invented. Sustained
Spirit shield use noneth. Conditional CTA/Spirit/Enigma interplay and FCR vs IAS explicit.
One-shot tmp/add_zeal_swaps.py SUCCEEDED; NEVER rerun.

Bank60cases:57red/3already-correct sword exclusions ->60stagedgreen ->60selectedgreen.
Cases include3qualities, lowrolls, wrong/unknown class, empty/wrong sockets, eth/unknowneth,
CTA twohanded, unknown/knownabsentBO, below-nativeBC; Spirit sword exclusion and ordinary
shield (native35 res, no fabricated inherent27fire).16existing corecaster/Zealswap/statbundle/
coverage checks pass.20saved replay extraction/prices unchanged. SpiritMonarch text alone
adds one conditional Zeal build: at least13->14builds,10->11conditional,18->19uses/7->8groups.
Selected20replays match staged. Initial all-text-unchanged assertion caught this reviewed
expected change; publication shell proceeded, then explicit diff review/allowlist comparison
and selected verification passed. Use set-e before future comparison/publication sequences.
Ruff/format/diffcheck pass. No wholebank/fullsuite claim. Bank891cases/3637targets/
3423missing scenario sets. Observed20captures/79gaps. Completion counts:
{"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1256, "excluded_occurrences": 4777, "coverage_rows": 7951, "remaining_tasks": 111617}; completefalse.

NEXT: Zeal armor spans113Enigma,114Fortitude,115CoH,120Duress,122Hustle(armor),124Lionheart,
125Smoke; helms102Bulwark/103Temper. Span121Treachery has already-reviewed Fade-prebuff role
(section32); do not blindly convert prebuff to sustained-bodywear. Existing Smoke/Duress/
Lionheart roles in zeal-paladin.json are mercenary-only, not these player alternatives.
Armor spans slot label Body Armors; preserve source spelling/semantic matching. Native
recipe/rune stats and player-specific recipients must be reviewed, not copied from mercenary.
Then all other contract scope. Worker Python restart for SacredRondache/Trainer still
unverified. Logs tmp/zeal-swaps-*. All launched processes terminal at checkpoint.

## Latest active checkpoint — Zeal shield alternatives, 2026-09-27

Goal ACTIVE; unfinished. Selected generation `cd94952f1853210059a82acf1e3010c71b773dcfbf79dcefdb2f76d7f898647f` (72 artifacts),
2385 profiles /2377 stat configurations. No live collection, commit, staging or host restart.

Added exact Zeal section32 Off-Hand spans68 Phoenix,70 Exile,79 Sanctuary,80 Rhyme.
New maintenance/zeal_shield_templates.py separates physical off-weapon Phoenix ED from
caster-only roles; Exile Offensive Auras supports Fanaticism, not Combat Skills, and
ethereal requires observed repair. Sanctuary/Rhyme preserve native automods versus
recipe resistance, blocking/full-loadout requirements, FBR versus IAS, and conditional
charges/procs. No base is mandated by these guide spans. Legal recipe and filled
sockets are checked. Other player shields require nonethereal durability.
One-shot tmp/add_zeal_shields.py SUCCEEDED; NEVER rerun.

Item bank zeal_shields.py93cases initially red. First green78pass/15fail revealed
wrong-family candidates are excluded before role traces; corrected negative tests
assert family and absent stat configurations. Then93staged and93selected passed.
Covers all3 qualities, low rolls, wrong base/socket count, empty sockets, unknownclass/
ethereal; Exile adds noneth, unknown/knownabsent repair and nonPaladinshield exclusions.
32existing aura/Rhyme/specialist shield/statbundle/coverage regressions pass.
20saved extraction/text/price replays unchanged and selected matchesstaged. Ruff,
format and diffcheck pass. No fullsuite/wholebank claim. Bank831cases/3631targets/
3423missing scenario sets. Observed20captures/79gaps. Completion counts:
{"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1254, "excluded_occurrences": 4777, "coverage_rows": 7945, "remaining_tasks": 111583}; completefalse.

NEXT: Zeal swap CTA span81 and Spirit span87. Source section29 explicitly describes
BattleCommand twice thenBO, Teleport on FCR swap, then mainweaponZeal. Exact native
CTA: BC2–6, BO1–6, BattleCry1–4, +1allskills (verified runes.json); do not infer active
buffs. Existing core_caster_word_templates supports other caster builds but lacks
Paladin shield type and uses Off-Hand-Swap while source span says Off-Hand Swap;
preserve exact source slot mapping. CTA eth casting does not consume durability;
Spirit shield blocking and twohanded companion compatibility need explicit care.
Then armor/helm alternatives and all other contract work. Runtime Python restart
for SacredRondache/Trainer still unverified. Logs tmp/zeal-shields-*; all processes
terminal. No intermediate batch completes the goal.

## Latest active checkpoint — Zeal Unbending Will and Hustle, 2026-09-27

Goal ACTIVE; unfinished. Selected generation `9c20e64de42036a723bc195fad10692cbccfb7d80b737a306a463529d23c980b` (72 artifacts),
2381 profiles / 2373 stat configurations. No live collection, commit, staging or host restart.

Added exact Zeal Gear Options section32 spans63/64: Unbending Will Phase Blade and
Hustle (weapon) Phase Blade. BUILD_MEMBERS provides source-specific Paladin priorities.
Unbending Will excludes Barbarian Combat ranks; Hustle excludes additive credit for
level1 Fanaticism alongside stronger player Fanaticism. Temporary Burst of Speed,
full attack-speed context, leech and proc restrictions remain explicit. Weapon/armor
recipes are separate; completed Non-Ladder items do not prove creation availability.
One-shot tmp/add_zeal_budget_words.py SUCCEEDED; NEVER rerun.

Bank33 cases: initial30 failed/3 armor exclusions already passed; then33 staged and
33 selected passed. Covers3 qualities, low rolls, wrong base, ethereal, empty sockets,
unknown class and armor variant exclusions. Captured-total Unbending maximum damage
fixture corrected from bonus9 to149 (native Phase Blade35 *4 +Ith9).15 related
Hustle/combat/stat-bundle/coverage checks pass.20 saved extraction/text/price replays
unchanged; selected matches staged. Ruff/format/diff checks pass. No full suite or
whole-bank pass claimed. Bank738 cases /3619 targets /3423 missing scenario sets;
observed20 captures /79 gaps. Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1250, "excluded_occurrences": 4777, "coverage_rows": 7933, "remaining_tasks": 111515}.

Sacred Rondache screenshot fix remains published: Spirit potential,27 allres carryover,
45 preferred,4 sockets needed, item-level-dependent Larzuk/cube outcomes; no matched
price invented. Running worker still needs Python restart; host restart unverified.

NEXT: Zeal shield words Phoenix68/Exile70/Sanctuary79/Rhyme80; swap CTA81/Spirit87;
armor Enigma113/Fortitude114/CoH115/Duress120/Treachery121/Hustle122/Lionheart124/Smoke125;
helms Bulwark102/Temper103. Verify exact source/wearer context before crediting each.
Continue all other completion-contract work; no intermediate batch completes the goal.
Logs tmp/zeal-budget-words-*. All launched processes terminal at checkpoint.

## Latest active checkpoint — Zeal Death/BotD/Doom, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`fe7d9a7d2094c5bd074be865633bf223b750f35f095a7df6834608f16bb4825c`,72artifacts,
2379profiles/2371stat configurations. No live collection, commit, staging or hostrestart.

Added Zeal player Weapon alternatives, exact section32 spans56/58/61:
ethereal Death Berserker Axe,ethereal Breath of the Dying Berserker Axe,noneth Doom
Berserker Axe. Native recipe+rune+weapon hashes retained. Source-specific predicates
require exact base/ethereal,Paladin,legal filledrecipe; eth words need observed152
Indestructible. combat_weapon_templates.BUILD_MEMBERS isolates Zeal attack semantics
from existing Smite Death. Class guards support explicit Paladin modes; legacy
experimental Warlock modes retain their restriction. Old templates/profiles unchanged.
Death now prioritizes physicalED,CB,level-scaledDS,AR/mana leech and supportingGlacial
Spike proc. BotD player Str/Dex/Vit,ED/IAS/leech,targetdef/undead/PMH; Energy excluded.
Doom physicalED/IAS/skills/DS/OW,HolyFreeze with wielder-only coldpierce; no ethereal
repair inferred. Procs,leech,boss restrictions,fullspeed remain conditional.
One-shot tmp/add_zeal_axes.py SUCCEEDED; NEVER rerun.

Bank zeal_axes.py57cases red ->57stagedgreen ->57selectedgreen, across3qualities,
lowrolls,wrongbase/wrongeth/emptysockets/unknownclass and unknown/knownabsent
Indestructible onDeath/BotD.4newtemplate tests pass (initial fixture omittedvariant/
source,corrected; production untouched).13other combat/statbundle/coverage checks
pass, including existingSmite exclusions.20saved replay extraction/text/prices
unchanged vsprior and selected matchesstaged. Ruff/format/diffcheck pass.
Namedgate stillzero. Bank705cases/3613targets/3423missing scenario sets. Observed20/
79gaps. No freshwholebank/fullrepo pass claimed. Logs tmp/zeal-axes-*; ledger refreshed.
Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1249, "excluded_occurrences": 4777, "coverage_rows": 7927, "remaining_tasks": 111480}; completefalse.

NEXT: remaining explicit Zeal weapons UnbendingWillPhaseBlade(span63) and Hustle
PhaseBlade(span64), then shield/swap/armor/helmet words. UnbendingWill native recipe
read:6s sword,FalIoIthEldElHel,ED300–350,IAS20–30,BarbarianCombat+3,Taunt18%lvl18,
DR8,PMH,LL8–10 plusrunes. Existing template is Barbarian-specific: do not mark its
188:32 ranks as Zeal priority. Hustle exact native key is NOT simple "Hustle" in
runes.json; resolve weapon/armor variants from local definitions, never guess.
A low-level weapon Fanaticism aura must not be credited as additive with Zeal's
stronger active Fanaticism. Distinguish completed-item assessment from Non-Ladder
recipe creation availability; retain missing availability evidence where needed.
Then Phoenix68/Exile70/Sanctuary79/Rhyme80 and SpiritSwap87/CTA81, etc., plus all
other queued scope. Workerrestart for SacredRondache/Trainer remains unverified.
All processes terminal at checkpoint; no intermediate milestone is completion.

## Latest active checkpoint — Zeal Grief/Oath/Last Wish, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`e9fee25aafb33febe11ebc2b7f8c6eed483f5904c59f24b5d3b3011674ecfa86`,72artifacts,
2376profiles/2368stat configurations. No live collection, commit, staging or hostrestart.

Added zeal-paladin-{grief,oath,last-wish}-weapon-alternative. Exact Gear Options
section32 spans54/62/55: Grief Phase Blade, Ethereal Oath Cryptic Sword, Last Wish
Phase Blade. Reviewed local native recipe/rune/weapon evidence, exact base/ethereal,
classPaladin,3qualities,filledrecipe count/legalbase. Reused expand_combat_weapon but
explicitly wrote Zeal-specific conditions/priorities. Grief243demon/lvl and86lifeafterkill
included alongside111flatdamage/93IAS/attack effects. Oath ED/IAS desirable,absorb/
demon effects supporting; ethereal requires observed152Indestructible. LastWish ED,
CB,Might,LifeTap/Fade important but procs never assumed active. No numeric prices
invented. All source/rule fingerprints reviewed. One-shot tmp/add_zeal_combat_words.py
SUCCEEDED; NEVER rerun.

Bank zeal_combat_words.py adds48cases:3words/3qualities,lowrolls,wrongbutrecipelegal
BerserkerAxe,emptysockets,unknownclass; Oath extra noneth,missingIndestructible,
malformedzero flag,complete capture withoutIndestructible. Initial39red ->39staged
green; extra zero-flag test initially expectedfalse but raw0 flags are intentionally
UNRESOLVED in inventory_tracking/items/stats.py. Corrected that case to unknown and
added complete-absence case false. All48selected tests pass, including no unwanted
stat configurations. Production decoder not changed. First39 cases validated before
publication; boundary fixture expectations resolved afterward, then all48 verified
against that same selected generation.

60maintenance/statbundle/bankcoverage tests pass; ruff/format/diffcheck pass.
20savedreplay extraction/text/prices unchanged vsprior and selected matchesstaged.
Named tiergate stillzero. Bank648cases/3604targets/3423missing scenario sets.
Observed20captures/79gaps; matrices/completion refreshed. No freshwholebank/fullrepo
pass claimed. Logs tmp/zeal-combat-words-*.
Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1246, "excluded_occurrences": 4777, "coverage_rows": 7918, "remaining_tasks": 111429}; completefalse.

NEXT: Zeal remaining explicit Weapon alternatives Death(span56,ethBerserkerAxe),
Breath of the Dying(span58,ethBerserkerAxe),Doom(span61,BerserkerAxe). Native recipes
read locally: Death sword/axe5s,ED300–385,CB50,deadly/lvl,param4,GlacialSpike proc,
Indestructible,NOIAS; existing combat_weapon_templates Death is SMITE-SPECIFIC and
only prioritizesCB, so do not reuse unmodified for Zeal. BotD weapon6s,ED350–400,
IAS60,leech12–15,attributes30,ZodIndestructible; existing merc_weapon template cannot
blindly transfer bearer priorities to player. Doom axe/pole/hammer5s,ED280–320,IAS45,
HolyFreeze12,coldpierce40–60,allskills2,Volcano proc; no durability repair. Sourcegear
section32 explicitly lists those variants; pin native IDs via metadata, not memory.
Then UnbendingWill/Hustle availability distinctions, shield/swap/armor/helmet words
and all remaining scope. Sacred Rondache/Trainer workerrestart remains unverified.
All processes terminal at checkpoint. Do not treat this milestone as completion.

## Latest active checkpoint — Dual Lawbringer starter, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`20553bbb2e3f979809cc52130d9d24bfcc8db011a5fb84caab5ace0a49b2c93a`,72artifacts,
2373profiles/2365stat configurations. No live collection, commit, staging or hostrestart.

Added zeal-paladin-dual-lawbringer-starter, independently source-reviewed to Zeal
section13/item_spans5 (2x1H Lawbringers). Both explicit mercenary_equipment weapon
and off_hand must satisfy identified,eligiblequality,Lawbringer,3filledsockets,
native legalbase and1H predicates. Context retainsPaladin/Act5Frenzy. Missing slots
unknown,explicitnullfalse; duplicate mercenary_items names never prove equipment.
Single-sword profile remains unchanged and useful independently. Bearer stat priorities
preserved; no summed aura/proc uptime/fullloadout/price inferred. Source-context fifth
row binds exact canonicalized occurrence7761f452b12dd8aae0b56c19 to this configuration.

One-shot tmp/add_zeal_dual_lawbringer.py SUCCEEDED; NEVER rerun. Initial attempt
failed before any writes on contexts key (reviews vs rows); corrected successful
attempt wrote all data. The first rebuild before success was unchanged; final rebuild
and all listed validation below followed the successful mutation.

Bank zeal_dual_lawbringer.py adds15cases (3qualities x two,one/empty,unknownslot,
twohandedother,unknownloadout); everycase includes duplicate name-list decoy.
15red ->25stagedgreen including10existingstandalone;25selectedgreen;75maintenance/
equipment/statbundle checks.20savedreplay extraction/text/prices unchanged versus
prior generation and selected matchesstaged. Named tiergate remains548/35/2958,zero.
Ruff/format/diffcheck pass. No freshwhole600bank/fullrepo claim.
Bank600cases/3595targets/3423missing scenario sets. Observed20captures/79gaps.
Logs tmp/dual-lawbringer-*. Source/context/coverage dependencies rebuilt, ledger refreshed.
Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1243, "excluded_occurrences": 4777, "coverage_rows": 7909, "remaining_tasks": 111378}; completefalse.

NEXT: remaining Zeal player runewords and other source/configuration closure.
Authoritative inventory shows explicit gear Weapon Oath span62 with no named player
profile; also Death56,LastWish55,BreathoftheDying58,Doom61,Grief54,UnbendingWill63,
Hustle64; Spirit Off-HandSwap87/CTA Weapon-Swap81; shield Phoenix68/Exile70/
Sanctuary79/Rhyme80; armor/helmet alternatives. Review source context and existing
profiles/templates before adding rules; mode availability must preserve Non-Ladder.
Narrative mentions may be replacement/prebuff/other-wearer, never blindly endorse.
Use cache source appraisal-guide-sections.json Zeal itemspans/sections for provenance.
Scope inventory and bank/final gates remain incomplete. Sacred Rondache fix and
Trainer charm worker restart remain unverified. All processes terminal at checkpoint.

## Latest active checkpoint — Observation replay coverage, 2026-09-27

Goal ACTIVE; all-item work unfinished. Runtime generation unchanged:
`e809d80c446678f3bbe081e01b9181867cdacac841279d7f193cadf9f2f65e3b`.
Maintenance replay now registers sacred_rondache_res27 alongside19 raw snapshots.
OBSERVATION_STEMS is explicit; this capture reuses the actual decoded observation,
not a fabricated snapshot. Extracted decode_snapshot helper preserves existing native
modifier handling. Replay output records input_format; observed_review retains it.
New regressions check exact captured-fact preservation, Spirit advice, unchanged
fixture bytes and continued raw snapshot decoding. Initial2red ->8affected green;
final6replay/ledger tests pass, ruff/check-format/diff-check pass.

Selected-generation replay20captures passes; previous19 extraction/text/prices unchanged.
New replay tmp/observation-replay-published.json. Imported durable observed ledger:
20captures/79open gaps (Sacred Rondache coverage/market deficiencies remain pending).
Rebuilt coverage matrix and completion. No runtime artifact changes/publication needed.
Bank remains585cases; no new wholebank/fullrepo run. No hostrestart/live research,
commit or staging. Sacred Rondache Python fix still requires verified workerrestart.
Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1242, "excluded_occurrences": 4777, "coverage_rows": 7906, "remaining_tasks": 111361}; completefalse.

NEXT: Zeal source item_spans/5 (canonical Lawbringer, original Lawbringers) requires
2x1H on Act5Frenzy. Existing standalone role remains a useful single-sword candidate;
do not pretend it proves the pair. Existing equipped_item_matches supports explicit
mercenary_equipment weapon/off_hand snapshots, with omitted=unknown and null=empty.
Use those to validate both complete legal1H words; name-list multiplicity is not an
equipped configuration. Shared item-only conditions must exclude context predicates
(the equipment condition validator rejects those). Preserve original standalone role,
add separate source-reviewed Starter paired configuration and bank cases for two,
one/empty,unknown/wrongslot/twohanded. Bind exact section13/span5 through reviewed
source_context_reviews only after semantics and tests are complete. Existing source
profile is zeal-paladin-lawbringer-act-5-frenzy in rules/roles/zeal-paladin.json,
source gear span207; prior one-shot tmp/add_zeal_lawbringer.py MUST NOT rerun.
Then remaining player words/starter gear and all scope obligations. All processes
terminal at checkpoint. Goal remains active across this checkpoint.

## Latest active checkpoint — Sacred Rondache and Insight legality, 2026-09-27

Goal ACTIVE; unfinished. Selected generation
`e809d80c446678f3bbe081e01b9181867cdacac841279d7f193cadf9f2f65e3b`,72artifacts,
2372profiles/2364stat configurations. No live collection, commit, staging or hostrestart.

Latest user screenshot: Normal Sacred Rondache, noneth,0s,def160,27allres, no base advice.
Actual source inventory_tracking/runs/alt-d/20260927T114325Z-152b131a/request-2/frozen.json.
Saved observation tests/inventory_tracking/fixtures/sacred_rondache_res27.json.
Offline lookup first: tmp/sacred-rondache-lookup.json. RCA: base_use Spirit explicitly
limited Paladin shields to Sacred Targe. Extended to all15 native ashd shields,
subject to native recipe legality and existing socket preparation. Report shows27
allres carryover,45target,noneth suitability,needs4s,Larzuk3/4 conditional on missing
ilvl,cube probabilities. Price remains unknown from no matching comparisons.
Family test exposed decoder Ancient Shield/nativepad versus KB Kurast Shield. Added
RecipeIndex.by_code, used by base assessment. Recommendation-only rows join only
unambiguous KB-name native codes. No display-name fallback that could confuse shields.
40base/socket/report regressions plus5targeted index/capture tests pass; ruff passes.
Exact published Sacred Rondache report matches staging (tmp/sacred-rondache-published.json,
tmp/sacred-rondache-fixed.txt). WORKER RESTART REQUIRED for Python changes, not verified.
The new fixture is an observation, not legacy snapshot format: standalone pipeline
regression covers it; still needs inclusion in common replay/observed-review ledger.

Fixed12 older caster Insight merc roles: only native legal4s polearms, not spears or
Bardiche; accepts completed low_quality word. Merc contexts, existing priorities and
source variants preserved. Source corroborates native Insight recipe. Explicitly
reviewed changed fingerprints in guide/stat reviews; no other review resets.
One-shot tmp/fix_old_insight.py SUCCEEDED; never rerun.12red ->37role/stat green.
New insight_merc.py bank108cases:12variants x3qualities xpositive/negative/unknown.
108staged and108published cases pass. Initial stale-bundle bank run was deliberately
interrupted after54fail/44pass; superseded by rebuilt green, log preserved.
Bank585cases/3592targets/3423missing scenario sets.60maintenance tests pass.

19saved replays match staging in extraction/text/prices. Compared with prior generation,
all extraction/prices unchanged; two charm texts lose generic leveling lines due to
pre-existing separate worktree change in generic_leveling.py/sections.py. Preserved
that change; its18tests pass. No changes to its policy made here. Sacred Rondache
also verified separately. Named gate stillzero. No freshwhole-bank/fullrepo claim.
Reimported observed19captures/76gaps; rebuilt base matrix after code changes (first
matrix refresh correctly rejected stale base_use hash),then coverage/completion.
Logs tmp/old-insight-* and tmp/sacred-rondache-*.
Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1242, "excluded_occurrences": 4777, "coverage_rows": 7905, "remaining_tasks": 111352}; completefalse.

NEXT: include Sacred Rondache observation in common replay/observed-review coverage
without fabricating a raw snapshot. Preserve regression of native-name alias and
price independence. Then Zeal plural Lawbringers source span5 still needs dual1H
weapon semantics; one captured sword is not proof of owning two. Its canonical alias
is resolved but source configuration remains pending. Continue remaining player
words/starter gear and all scoped work; final full-suite/delivery still required.
All tool sessions terminal at checkpoint. No intermediate checkpoint is completion.

## Latest active checkpoint — Zeal Insight and Lawbringer aliases, 2026-09-27

Goal ACTIVE; all-item work unfinished. Selected generation:
`f7e337ae563ba14c358ca46ac615f3745dffd4bbb29aab6da49e619d4f9268f3`
2372 profiles /2364 stat configurations /72 artifacts.

Exact setup labels Lawbringers and Lawbringer(s) now resolve to native Lawbringer;
original labels remain intact, without inferring ownership or equipment count.
11 demand occurrences normalized; IDs unchanged. Demand/watch/index rebuilt offline.
Six named baseline source pins refreshed only after verifying full cited watch rows
unchanged. Completion policy fingerprint now includes builds.py. Alias tests14pass.

New zeal-paladin-insight-act-2-might role and15 pipeline bank cases: native legal
polearms, filled4s recipe, three qualities, ethereal, wrong/unknown merc, impossible
Bardiche capacity; bearer priorities distinguish Meditation from merc weapon stats.
Zeal section13/span9 explicitly bound through source_context_reviews (now4 rows).
One-shot tmp/add_zeal_insight.py and source-context append SUCCEEDED; never rerun.
Backups tmp/lawbringer-alias-before-* exist; do not overwrite/recreate them.

Red/green15 new cases;41 staged checks,76 maintenance tests,33 selected-runtime
cases (24Insight/Lawbringer plus9Trainer),14alias tests pass. Ruff check/format pass.
19 selected replays match staged extraction/text/prices. Relative to prior generation,
only Insight report adds one conditional Zeal build; extraction/prices unchanged.
Named gate remains548eligible/35sets/2958renderedcases,zero failures.
Logs tmp/lawbringer-insight-*, tmp/lawbringer-alias-*.

Bank477pipelinecases,3580targets,3447missing complete scenario sets. Observed review
19captures/76open gaps. Completion:2570identities,62891occurrences,1242reviewed,
4777HCexcluded,7893matrixrows,111280remaining tasks; completefalse.
No fresh whole-bank/full-repo pass claimed. No live collection, staging, commit or
host restart. Trainer charm worker restart still unverified.

NEXT: fix12 older Insight roles (rules/roles files, IDs in
roles/test_insight_mercenaries.py). They allow spea despite native Insight recipe
allowing pole/staf/miss, and lack native legal-base/capacity guards. Preserve existing
merc context, source variants and mana-priority decisions; test red/green illegal
spear/capacity/unknown bases and legal polearms. Evaluate low_quality deliberately.
After role edits refresh guide/stat fingerprints only with reviewed semantic changes.
Then Zeal plural Lawbringers span5 requires explicit dual-weapon meaning; singular
Frenzy sword candidate does not prove both owned. Alias normalization alone does not
close that source branch. Continue remaining player words, starter gear and all
scope obligations; final whole-suite/publication/delivery gates remain pending.

## Latest active checkpoint — Explicit source contexts, 2026-09-27

Goal ACTIVE; all-item work unfinished. Selected runtime generation:
`c83a53deb15498eab8b26f59b6682aafaefd913733ae3398142352f2a71bc4a3`
2371profiles /2363stat configurations /72artifacts.

Implemented maintenance/source_context_reviews.py and rules/source_context_reviews.json.
The validator binds exact, verified, resolved named/runeword narrative merc spans
(Guide mention /unspecified) to reviewed variants/slots without rewriting sources
or relaxing existing source_rule_ids gates. Pins span snapshot, same-guide passage,
profile fingerprints and explicit required mercenary predicates on all successful
paths. Stale evidence/profile/context, other wearer/item/slot/source, duplicates and
unreviewed branches fail closed. remaining_branches keeps source pending and can
reopen an older generic credit. Completion scope fingerprints review data and
relevant policy dependencies; output includes source_context_dispositions. Shared
predicate proof moved from completion.py to source_matching.py.

Three concrete bindings: Zeal raw narrative spans6/7/8, section13. Singular Bash
Lawbringer is separate from unresolved plural span5. Smoke binds both Act5 branches
plus existing Act2Might. Crown initially retained missing Act2Might, then we implemented
that role and its five bank cases, completing all three explicit source reviews.
New role zeal-paladin-crown-of-thieves-act-2-might preserves low leech, native/upgraded,
eth/noneth, merc kill-owner gold find and excludes mana. One-shot
`tmp/add_zeal_crown_might.py` SUCCEEDED; NEVER rerun. Earlier successful appenders
remain one-shot. Source-context JSON creation was also one-shot (file now exists).

Red-green:15missing binding-validator cases,2integration cases,5missing Crown cases
reproduced then fixed.144affected staged checks passed (59bank/stat/coverage,
85maintenance).52selected-runtime pipeline cases passed.19saved replays equal
staged extraction/text/prices and unchanged from previous generation. Named gate
stillzero:548eligible/35sets/2958rendercases. Ruff and diffchecks pass. No freshwhole
bank/fullrepo claim. Logs tmp/source-context-*, tmp/zeal-crown-might-red.log.
Bank462pipelinecases;3577targets;3447lackcomplete case sets.

Imported current published replay results with maintenance.observed_review: now19
observed captures including Trainer charm (previous ledger only18);76open captured
review gaps. Existing history retained.6observed/matrix tests passed. Rebuilt coverage
matrix and completion after import. Latest:2572identities,62891occurrences,
1237reviewed,4777HCexcluded,7892matrixrows,111287outstanding obligations,
56889source-review tasks; completefalse. All shell sessions terminal. No live
collection, staging, commit or hostrestart. Charm-worker restart still unverified.

NEXT concrete starter gaps found from authoritative inventory:
- Zeal /item-spans/5: id7761f452b12dd8aae0b56c19, name/original_label Lawbringers,
  categoryNone, unresolved, Guide mention/merc/unspecified. Existing Frenzy role
  zeal-paladin-lawbringer-act-5-frenzy is sourced to gear span207. Need reviewed
  plural identity normalization preserving original label and two-weapon meaning;
  do not infer ownership of two words from one captured sword. v1context bindings
  deliberately reject unresolved identities, so resolve provenance first.
- Zeal /item-spans/9: iddffa9dcf13e00e61157492a3, Insight, resolved runeword,
  Guide mention/merc/unspecified. No current Zeal profile names Insight. Section13
  endorses Act2Might Insight starter alternative. Reuse reviewed native merc-weapon
  mechanics, keep legal Act2 base types and mercenary stat recipients, add bank
  cases and explicit narrative context binding.
Then remaining Zeal player words/Act5 early table and all other scoped work. Known
source conflicts, market/stat/report coverage and final fullregression/delivery
remain pending. No checkpoint is completion or a reason to stop.

## Latest active checkpoint — Zeal Act 5 starter, 2026-09-27

Goal ACTIVE; not complete. Published generation:
`2997ba85a165a79a9e96b3d88f7efe126934fd6754696d2bbd14d2f0f33da2f5`
2370 profiles /2362 stat configurations /72 artifacts.

Added five independently source-reviewed Zeal starter roles: Smoke and Crown of
Thieves for each Act5 Frenzy/Bash, plus two-handed Lawbringer for Bash. Source
appraisal-guide-sections.json, Zeal section13 and exact narrative spans7/8/6.
Preserve explicit merc type and Paladin context. Crown allows native/upgraded,
eth/noneth and legal sockets; mana is not a merc priority, gold find is kill-owner
only, leech needs drainable physical hits. Smoke supports completed normal,
superior and low_quality words, filled2s, legal armor; energy/Weaken charges are
not merc benefits. Smoke missile defense captured280=word250+Nef30. Bash Lawbringer
intersects the existing legal recipe sword list with native2handed=1; Phase Blade
fails this specific source setup. Existing Frenzy one-hand behavior unchanged.
No new prices or whole-loadout guarantees.

One-shot `tmp/add_zeal_starter_merc.py` SUCCEEDED; NEVER rerun. Subsequent fixes:
replace invalid empty weapons.json locator with exact native sword locators;
new Smoke roles include low_quality (original inherited Act2 template omitted it).
All associated review fingerprints repaired; no shared-template broadening.

New bank module cases/zeal_starter_merc.py:37pipelinecases, positive/negative/unknown
for every new quality plus upgraded/noneth Crown, missing leech and excluded mana.
31initialcases red;48initialaffected green;6lowquality cases red; final54affected
staged checks green (47pipeline incl10existing Frenzy,5coverage,2statbundle).
47selected-runtime cases green. All19saved replays match staged extraction/text/
prices and prior runtime. Universal named gate stays zero across548eligible,
35complete sets,2958rendercases. Ruff/diffcheck pass. Logs tmp/zeal-starter-merc-*.
Bank now457pipelinecases;3576targets,3447still missing complete scenario sets.
Previous generation whole bank432passed; no whole457bank/fullrepo run claimed.

Also repaired completion.py quality comparison: occurrence category runeword is
not an ItemData quality. Credit normal/superior/low_quality only if exact recipe
identity is mandatory on every successful predicate path. Empty bases, a different
word, illegal quality and optional-word alternatives do not get credit. Existing
source/context gates retained.3red regression cases ->green;56affected maintenance
tests pass. This now recognizes268previously completed word-source occurrences.
No new runtime publication required for this later maintenance-only fix.

Latest completion:2572identities,62891occurrences,1234reviewed,4777HCexcluded,
7890matrixrows,111276outstanding obligations,56892source reviews, complete=false.
Persisted appraisal-completion.json and tmp/zeal-starter-merc-completion.json.
All processes terminal. No livecollection, staging, commit or hostrestart.
Trainer charm's worker restart remains unverified; selected generation includes fix.

NEXT: source-context linkage needs an explicit reviewed mapping. New roles use
variant Starter and actual Helmet/BodyArmor/Weapon slots, while raw narrative
occurrences are variant Guide mention /slot unspecified; therefore audit_occurrences
source_rule_ids are empty and completion correctly leaves them pending. Do NOT
rename or broadly relax variant/slot gates just to count them. Plan a pinned,
reviewed source-context binding that proves narrative setup/slot derivation while
preserving differing variant/wearer/slot restrictions, with near-miss tests. Existing
pattern_source_slot handles a narrower pattern case. Relevant modules inventory.py
(audit_occurrences indexes exact SCOPE), guide_spans.occurrence_source,
completion.py exact named source checks, guide_demand.compile_demand. Update policy
fingerprints for new semantics. Then finish other Zeal early Act5 gear /player words
and the full remaining scope. Source section44 table and prior handoff below retain
remaining names. No intermediate checkpoint is a stopping/completion condition.

## Latest active checkpoint — Runeword applicability ledger, 2026-09-27

Goal ACTIVE; all-item work remains unfinished. Runtime generation unchanged:
`acf60e184e6b1b48cac9ef7edb770aa358dc8f4dc57c3ad6ac173105c77a6512`
(2365 profiles / 2357 stat configurations / 72 artifacts).

Closed 2633 genuinely inapplicable runeword-creation checks without changing
pricing or desirability: 565 resolved named identities, 1777 named/affixed use
qualities, and 291 base-quality rows with no fitting completed native recipe.
`recipe_applicability.py` consumes reviewed `rules/recipe_applicability.json`,
pinning D2MOO Items.cpp:3251-3265 and D2Items.h:12-23. Magic/set/rare/unique/crafted
cannot form runewords. Missing review, unknown quality, unresolved identity and
completed words remain pending. Other cube recipes and socketing are not covered
by this exclusion. Existing base_matrix native type/capacity audit now closes only
its proven impossible recipe memberships; absent catalogs or absent cache links
cannot establish exclusion. Added policy modules to completion fingerprint and
transitive input validation for matrix source documents (list artifacts permitted).
README documents the precise dimension scope.

Red-green: 13 missing quality-rule failures, then green; two base applicability
failures, then green. 64 affected maintenance tests passed; Ruff/diff checks pass.
Fresh selected-generation whole item bank: **432 passed in 176.84s**, including
420 constructed pipeline cases, five coverage checks, seven range checks.
Log: `tmp/recipe-checkpoint-item-bank.log`. No fresh full-repository run claimed.
No runtime publication needed for maintenance-only changes. Previous 19 saved
replays remain validated against this unchanged runtime generation.

Rebuilt base matrix, coverage matrix and completion ledger. Latest completion:
2572 identities, 62891 occurrences, 966 reviewed, 4777 Hardcore exclusions,
7879 coverage rows, **111480 outstanding obligations**, recipe eligibility5246.
These are obligations, not item counts. Complete=false; item bank still lacks
complete scenario sets for3447/3565required targets. See
`tmp/recipe-applicability-completion.json` and persistent appraisal-completion.json.
All shell sessions terminal. No live collection, staging, commit or host restart.
Latest observed host request remains8 (Aldur's Advance); Trainer charm's worker
restart is unverified. The published fix flags Druid Summoning+30–45Life and its
saved capture is covered. User already told restart is needed.

NEXT: resume remaining Zeal words/Act5 early mercenary gear and full scope closure.
Source reviewed in this turn: appraisal-guide-sections.json key
pricing/raw/mr/guides__zeal-paladin.html, section13 explicitly supports Act5Frenzy
(two1H Lawbringers) or Act5Bash (one2H Lawbringer), Smoke+CrownofThieves; Act2Might
Insight is alternative. Section44 early table: Smoke/Lionheart/Hustle/Skin of the
Flayed One/Goldskin/Rockfleece/Gemmed Dusk Shroud/Venom Ward, CrownofThieves/Bulwark/
UndeadCrown/TheFaceofHorror/GemmedMask/Temper/Cure. Existing named/word survival
profiles intentionally restrict to Act2Might; add separately reviewed Act5 roles,
not broaden all stages blindly. Current Zeal Lawbringer only covers Act5Frenzy.
Source section32 retains remaining player words. Continue source conflict review,
pricing/stat/report dimensions and bank coverage; do not stop at this checkpoint.
Never rerun successful one-shot appenders listed below.

## Latest active checkpoint — Angelic pair and watch coverage, 2026-09-27

Goal ACTIVE. Added/published Zeal Angelic ring/amulet pair and 51 bank cases covering
that pair plus five existing builds (Berserk, Double Throw, Dragon Talon, Echoing
Strike, Strafe). Existing two-ring requirements retained; missing second ring,
unknown companions, wrong wearer, uncaptured AR/life and two rings not being three
distinct set pieces are tested. Ring owns native224 AR/level; Wings gets own
114 damage-taken-to-mana and observed75 life. No partner/full-set bonus invented.
Pinned native catalog has one eligible Halo/Wings variant each (table52/53); seasonal
spawn fields do not remove owned Non-Ladder specimens or prove another variant.
Exact Zeal source spans160/172, section32 and native set definitions pinned.

Selected generation acf60e184e6b1b48cac9ef7edb770aa358dc8f4dc57c3ad6ac173105c77a6512
2365 profiles /2357 stat configurations /72 artifacts. One-shot
`tmp/add_zeal_angelic.py` SUCCEEDED; NEVER rerun. Prior successful appenders remain
one-shot. Repeatable dependency rebuild completed; existing SQLite remains valid.

Bank coverage now includes valuable `affixed_value_watch` targets with required
positive/negative/unknown cases per rarity. Watch artifact hash is included in its
inputs. Trainer charm's nine cases registered; invalid-rarity case deliberately
cannot claim another quality's coverage. Red missing watches keyword -> green
coverage test. README documents watch:<watch_id> declarations.

Tests: seven Zeal cases initially red (missing rules);39existing Angelic cases green.
After rules and extra boundaries,58affected staged checks passed (51Angelic,
5coverage,2statbundle).60selected-runtime cases passed (51Angelic+9Trainer).
All19saved replays match staged extraction/text/prices, unchanged from prior runtime.
Ruff/diffcheck pass. No fresh whole-bank/full-repo run claimed this checkpoint.
Bank420pipelinecases,3447/3565requiredtargets still lack complete case sets.
Completion:2572identities,62891occurrences,966reviewed,4777Hardcoreexcluded,
7879coverage rows,114113outstanding obligations (not item count), completefalse.
Logs tmp/angelic-*; all sessions terminal. No live collection, staging, commit or
worker restart. Latest hostrequest observed was8 Aldur's Advance at09:55UTC using
previous generation23e79..., so charm-worker restart remains unverified.

NEXT: continue remaining Zeal words/Act5 early gear and full-source coverage. Also
inspect completion-matrix applicability: all7879rows are still pending for recipe
eligibility, report and market by default; most lack socket/stat annotation review.
coverage_matrix.py initializes every dimension pending and currently never resolves
recipe_eligibility. Known named/affixed qualities cannot be runeword bases; review
production/native mechanics and add source-bound, tested applicability dispositions
without removing identities or inferring prices. This is real remaining ledger
work, not evidence that every such item needs another item-specific recipe handler.
Source review remains57160+occurrences; retain unresolved planner conflicts and
future full-regression/delivery gates. Do not relax the completion contract.

## Latest active checkpoint — Trainer life skiller and Zeal sets, 2026-09-27

Goal ACTIVE. User interrupted the seven-piece Zeal set batch with a missed trade
highlight on Trainer's Grand Charm (+1 Druid Summoning, +37 Life). Completed both.
Selected generation: dde6c16d9197076082094307f2ba4de9f09afe832c4a446114679e83eb0b8d2c
(2363 profiles /2355 stat configurations /72 artifacts; rebuilt offline SQLite).

CHARM: actual saved scan is alt-d/20260927T092902Z-c4f4f20b/request-7/frozen.json.
Both stats decoded correctly. Trade watchlist only handled named items. Cached
items__valuable-magic-items.html explicitly says Trainer's +30–45 Life has solid
value (Medium qualitative guide tier). Added stat-qualified `affixed_value_watch`
row through pricing.knowledge.valuable, and policies/value_watch.py matcher via
pipeline.py. Exact native188:40=1 and life30–45, identified magic Grand Charm,
known nonethereal/zero sockets required. No current build dependency. Report gets
colored VALUABLE CANDIDATE and 'Druid Summoning skiller with 30-45 Life'. No matching
SC/NL/PC/RotW price exists; do not invent or quote historical bucket asks as estimate.
Older workers ignore the separate evidence kind safely (tested); **Alt+D worker
needs user restart for Python changes**. Not restarted by agent, fresh live request
not yet verified. User was told restart is needed. This delivery step remains pending.
Higher RotW life46–50 and other skill trees require separate reviewed watch rules;
current generic magic-watch item bank cases are not yet explicit coverage targets.

Saved capture added to replay STEMS as trainers_grand_charm_life37, built from actual
frozen sample/selected item/arrays and captured source.build_sha256. New fixture under
assessment/fixtures/replays. Report: tmp/trainers-grand-charm-report.txt.
Nine boundary/unknown magic-watch bank cases; saved-scan/color/legacy-worker tests in
tests/pricing/knowledge/test_magic_value_watch.py. Current KB watchlist228rows,
99valuable candidates. `valuable` regeneration changed six named-baseline source
hashes/row positions. Compared each cited old published row with new row; all six
exactly equal, then repaired only source locators/hashes in named_baselines.json.
Guardian Angel and other tiers restored. Never blindly repin changed evidence.

ZEAL: seven new roles <slug>-zeal-combination for Sigon's Visor/Gage/Wrap/Sabot and
Immortal King's Forge/Detail/Pillar. Exact spans106/137/147/152/130/145/151 andnative
set definitions. Group-limited distinct equipped player companions, Paladin, legal
native/upgraded nonethereal pieces. Sigon two-to-four pieces; boots MF needs3.
IK gloves/belt two or3; boots guide role needs3. Belt FHR needs3, glove IAS needs2.
Captured total defense supporting without claiming a distinct partial-defense roll.
Exclude Barbarian-only skills. Bank has39cases, including duplicate companions and
uncaptured bonuses. Corrected IKboots raw skill-tree layer from property-tableparam12
to native32 after decoder verification (+2 Combat Skills Barbarian); six cases pass.
One-shot tmp/add_zeal_sigon_ik.py SUCCEEDED: NEVER rerun. Earlier one-shot prohibition
continues. temp final-charge-routing-rebuild.py is repeatable dependency rebuild.

VERIFIED: 388combined staged checks passed in tmp/charm-and-sets-staged-fixed.log;
then six corrected native-layer IKcases passed (tmp/zeal-ik-native-layer.log).
48new cases passed against selected runtime. Eight pipeline/publication tests pass.
Named gate548eligible identities/35sets/2958renderedcases, all gateszero.
19selected replays match staged extraction/text/prices; prior18reports unchanged;
new charm is highlighted with unknown numeric price. Ruff/format/diff checks pass.
Bank369pipeline scenarios;3457/3562requiredtargets still missing complete cases.
Completion refreshed:2572identities,62891occurrences,964reviewed,4777Hardcoreexcluded,
7877coverage rows,114103rawobligations (not item count), completefalse. No full-repo
regression claimed. Logs prefixed tmp/charm-and-sets-*; all sessions terminal.

NEXT: verify live restarted worker when user scans again, while continuing all-item
work. Remaining Zeal companion target Angelic Wings/Halo (2pieces), then remaining
words and early Act5 gear. Angelic catalog default displayed legacy season15–16;
inspect all native variants/current identity before assumptions. Continue source,
pricing, report, leveling and bank gaps across full scope. No live collection,
git staging/commit or worker restart performed in this checkpoint.

## Latest active checkpoint — Zeal Death pair, 2026-09-27

Goal ACTIVE. Added and published two source-reviewed Zeal glove/belt pair roles:
`death-s-hand-zeal-pair` and `death-s-guard-zeal-pair`. Exact gear-table spans131/146
plus section32 and native set definitions. Require Paladin and opposite equipped
piece; native or legal upgraded bases, nonethereal, nonsocketable. Glove IAS30 and
belt all-res15 require both captured values and companion. Intrinsic survival
stats remain distinct. Guard upgrade is a preference (potion capacity), not a
minimum roll. Conditions distinguish the shared 8% set life-leech bonus from each
item and do not infer full-set benefits. No price invented.

Red: ten pipeline cases lacked roles. Implemented roles and exact stat reviews;
build validation caught/fixed preference base_name -> verified base_code and native
set JSON pointers (setitems uses names, uniqueitems uses numeric keys).
Then upgraded Guard cases exposed a bank factory provenance omission: native table
identity was resolved for ranges but discarded. Factory now returns that identity
in source.item_identity, matching real capture; production identity checks unchanged.
Earlier Tal bank native citations corrected to named keys. New coverage test resolves
all precise JSON citations (46 before this batch's generic Death references).

Validation: **332 staged bank checks passed** (`tmp/zeal-death-staged-full.log`),
10 selected-runtime Death cases passed (`tmp/zeal-death-published-bank.log`), four
coverage checks and two stat-bundle tests passed in the earlier targeted run.
18 selected/staged saved item extractions, reports and prices match and are unchanged
from the previous generation. Ruff and diff checks passed. Bank has321 pipeline
scenarios; 3457/3555 required targets still lack complete cases. Full repository
regression remains pending; this checkpoint does not establish all-item completion.

Selected generation: 23e79cb88c120b38da761ab13d5861575b03033bd863e6f6cc98d70dacf68adf
2356 profiles /2348 stat configurations /72 artifacts. Rebuilt full dependency chain
with tmp/final-charge-routing-rebuild.py; publication verified. Refreshed coverage
and completion: tmp/zeal-death-bank-coverage.json, tmp/zeal-death-completion.json.
One-shot tmp/add_zeal_death_pair.py SUCCEEDED; NEVER rerun it. Later corrections were
applied separately to JSON rules/fingerprints. No runtime Python change, restart,
live collection, staging or commit. No running processes remain.

Next continue Zeal companion sets: Sigon's Visor/Gage/Wrap/Sabot (2–4 pieces),
Immortal King's Forge/Detail (2 or3) and Pillar(3), Angelic Wings/Halo(2).
Native definitions were inspected. Sigon helm AR/lvl and belt defense/lvl use
parameter16; boots AR50 at2 and MF50 at3, gloves IAS30 at2. IK glove IAS25at2,
belt FHR25at3, boots MF25at2; Barbarian-only skill bonuses must not benefit Zeal.
Angelic catalog default displayed legacy firstLadderSeason15/last16 entries;
inspect all native variants/current table identity before new rules or fixtures.
Do not copy ambiguous default catalog entries into current-version expectations.
Remaining words, early Act5 gear, pricing/source closure and all other scoped items
remain pending. Continue until the completion contract is satisfied.

## Latest active checkpoint — Tal mercenary bank, 2026-09-27

Goal remains active. Full item bank: **321 passed in 120.64s**, including 311
pipeline scenarios and 10 coverage/range checks (`tmp/tal-bank-full.log`). Added
nine Tal Rasha mercenary cases after the 68 caster cases below. Gold-find Budget
and Summoner Starter roles verify Act 2 Might, life-leech utility, no mercenary
mana-leech priority, and unknown/wrong mercenary rejection. Gold-find requires
a decoded socket jewel: aggregate-only parent gold, non-gold jewel and incomplete
child capture cannot activate the role's stat contributions.

New `models.SocketItem` uses production `decode_payload` and explicit child
completeness, canonical metadata base identity, deterministic fixture IDs/positions.
Parent completeness stays independent. This bank still does not test native pointer
linkage. Red collection failure for absent SocketItem followed by nine green cases;
full-bank green after the shared factory extension. Ruff passed. README updated.
Runtime generation and production rules unchanged. Completion and bank coverage
refreshed (`tmp/tal-merc-bank-completion.json`, `tmp/tal-merc-bank-coverage.json`).

Next resume outstanding Zeal companion sets before broader bank expansion. Cached
Zeal gear table, appraisal-guide-sections.json source
pricing/raw/mr/guides__zeal-paladin.html section32, explicitly lists:
Sigon's Visor/Gage/Wrap/Sabot (2–4 pieces), Immortal King's Forge/Detail (2 or3)
and Pillar (3), Death's Hand/Guard upgraded DemonhideSash (2), Angelic Wings/Halo(2).
These are not present as Zeal profiles yet. Native partial bonuses and exact
companion/observed-stat gating need independent review; don't treat whole-set
ownership or parent totals as proof. Existing source text was inspected this turn.
Continue remaining words, early Act5 gear and all other scoped items afterward.
Do not rerun successful appenders. No running test session; maintenance completion
may need polling if interrupted. No stage/commit, live collection or host restart.

## Latest active checkpoint — Tal Rasha item bank, 2026-09-27

Goal remains active. Added 68 full-pipeline cases for 18 existing Tal Rasha caster
roles across six builds: armor, belt, helmet and orb alternatives. Tests distinguish
intrinsic stats from partial set bonuses; count distinct compatible companions;
exclude the Sorceress orb as a Warlock companion; withhold uncaptured bonuses;
and assign fire/cold mastery and resistance modifiers only to relevant builds.
Caster helmet cases do not credit life/mana leech as spell recovery.

Validation: 54 ordinary cases passed (`tmp/tal-caster-bank.log`), 14 missing-bonus
cases passed (`tmp/tal-caster-uncaptured-bank.log`), and coverage audit tests passed
(`tmp/tal-bank-audit.log`). Ruff and diff checks passed. No production rule change
was needed. Existing 244 checks passed before this batch; a fresh full-bank run
has not been claimed. Bank now contains 302 pipeline scenarios, with 3459 of 3553
required targets still lacking complete case sets. Coverage artifact refreshed.

Selected runtime remains 2f4fdfb04b5987e69dc7c10c3d07699deeb6ce32fa57f09444c8ffbe837fc65e
(2354 profiles / 2346 stat configurations). Completion refreshed in
`tmp/tal-bank-completion.json`: 2572 identities, 62891 occurrences, 955 reviewed
occurrences, 4777 excluded Hardcore occurrences, 114048 outstanding obligations.
Those obligations are not an item count. Final gates remain incomplete.

Next: mercenary item-bank cases, including Tal Rasha helmet leech and independently
verified socket fillers. Current Item factory has socket status but no socket-item
payload. Gold-find Tal mercenary role needs a decoded gold-find jewel; do not fake
that proof with aggregate stats. Existing targeted test is
`tests/pricing/knowledge/assessment/test_tal_merc_priorities.py`. Continue remaining
all-item review and bank work afterward. No publication, host restart, live collection,
staging or commit in this checkpoint; do not rerun successful one-shot appenders.

## Latest active checkpoint — source scope review, 2026-09-27

Goal ACTIVE; verified progress. Runtime stillselected2f4fdfb04b5987e69dc7c10c3d07699deeb6ce32fa57f09444c8ffbe837fc65e
(2354profiles/2346statconfigs). Bankunchanged234pipelinecases/244checks,lastfullpass.
New maintenance occurrence_scope.py supplies narrow Softcore scope dispositions:
476exact structured Hardcore variant occurrences +4301explicit Hardcore planner
profile occurrences =4777excluded configurations. Every2572itemidentity remains in
scope. No nameditem value, base, pricing, stat or report obligation was removed.
Matching requires verified occurrence source, exact source/path boundary and exact
variant title; structured variants additionally bind build and evidence.name with
excluded_hardcore eligibility. Planner bindings use exact /profiles/N locator and
native profile name beginningHardcore. Ambiguousduplicatecontexts never close work.
Unreferenced/shared/historical non-Hardcore planners still pending; no blanketclosure.

completion.py persists occurrence_dispositions and excluded_occurrences separately
from955reviewed occurrences. CLI summaries omit full disposition list. Scope hash now
includes hashes of completion.py/completion_evidence.py/occurrence_scope.py/
coverage_matrix.py/named_matrix.py, so changed reviewlogic invalidates old final
attestation. Red->green scope andpolicytests;38affectedtests pass; Ruff/diffcheckpass.
Artifact refreshed tmp/planner-hardcore-completion.json and persistent
pricing/data/appraisal-completion.json:114048rawtasks,notitemcount; completefalse.
No running sessions, publication, hostrestart, livecollection, gitstage/commit.

Next continue all-item work, including Zealcompanion sets/remainingwords/Act5early
armor/helm cases plus existingimportant item bank expansion. Sourceclosure backlog
stillneeds source-specific endorsed/planner/discovery review; preserve allnative
identities and unresolvedreferences.11plannerconflicts+1missingplanner remain.
No successful appenders rerun. Fullgoal/finalfullsuite still unfinished.

## Latest active checkpoint — Raven Frost bank, 2026-09-27

Goal ACTIVE; previous turn made verified progress, not completion. Runtime unchanged:
selected2f4fdfb04b5987e69dc7c10c3d07699deeb6ce32fa57f09444c8ffbe837fc65e,
2354profiles/2346statconfigs. Added57RavenFrost scenarios for19existing build/variant
uses; exactsource wp-a-builds variant membership checked. Native15Dex150AR20coldabsorb
40manaCBF partialfixture, full native property set not claimed. Low roll ranges and
midtier assertions. Correctclass, wrongclassDruid, unknownclass checked. Smite1/2
andHammerUbers3 forbid AR contribution for that configuration while preserving CBF
andDex. FoH3TriBrid attack phase retainsAR; other legitimatePaladin uses may still
annotate the same stat. New Case.absent_stat_configurations mapsstatkey to forbidden
configuration IDs. Shared runner implements it; README explains distinction.

Selected bank244passed78.52s (tmp/raven-bank-full.log), subset60passed (57new+3Zeal).
234pipeline scenarios+10coverage/rangechecks. Ruff anddiffcheckpass. No runtime
publication or hostrestart needed for test-onlychanges. Bankcoverage regenerated:
3553targets,3477missingcases. Completion regenerated tmp/raven-completion.json.
No running shellsessions. No staging/commits/livecollection. Fullgoalunfinished.

Next continue assessment queue and bankcoverage. Sourceclosure needs explicit
provenance review: inspected guideinventory shared-planner14009occurrences, among
62891total. _review_leads excludes discovery_only/historical/recommendedFalse/
shared-planner/hardcore from endorsed candidate leads, but completion retains them
for explicitdisposition. Example historical sharedplanneruf0106rb Andarielmerc
profile1 relatedFissure/Lightning, recommendedFalse; association is not endorsement.
Do NOT blanketexclude these or infer no-use/worthlessness. Need sourcebinding audit
against completecachedguide/variant refs before reviewing exclusion or reconciliation.
No source dispositions changed thisturn. Otherqueue: Zealcompanion sets, words,
Act5earlyarmor/helms; allotheridentities/pricing, sourceconflicts11+missingplanner1,
finalfullsuite. Do not rerun any successful adders listed below.

## Latest active checkpoint — 2026-09-27

Persistent all-item goal ACTIVE/unfinished; continue autonomously. Selected generation
`2f4fdfb04b5987e69dc7c10c3d07699deeb6ce32fa57f09444c8ffbe837fc65e`:
2354profiles/2346stat configurations/72artifacts. Zeal utility belts3 and Act5Frenzy
Lawbringer1 published; all18 staged/selected text/extraction/prices match and are
unchanged vs previous checkpoint. Item bank selected run187passed63.40s:
177pipeline scenarios+3coverage+7range-proof. Added45Mara cases across15existing
build variants; tests exact FCR, one below, unknown; generic guide paragraph differs
from variant prose, which is authoritative for these setups. Source/variant review
confirmed EchoingStandard/MF125, TrapsStandard65, Lightning117, SummonerDamage75.
Mara full native item20allres2skills5attrs; range20–30 and midtier assertions pass.
Lawbringer10bankcases cover normal/superior/low_quality, wronghandedness, unknown
mercenary and etherealCrypticSword. Role uses exactZeal gear span207/section44 and
existing reviewed native merc-sword predicates/stat semantics. No shared-template
code change. One sword never establishes dual wield/full setup or player Sanctuary
immunity bypass. Focusedmerc/stat5passed; sourcechecks passed. Beltsfocused5passed.

NEVER rerun successful one-shot adders: tmp/add_zeal_utility_belts.py and
 tmp/add_zeal_lawbringer.py (plus all previous successful adders below).
No live collection, host restart, git stage/commit. No shell tasks remain running.
Coverage pricing/data/appraisal-item-bank-coverage.json:3553targets;3496missingcases.
Latest completion tmp/zeal-lawbringer-maras-completion.json; source references and
universal baseline linkage are regenerated. Still false; rawtaskcounts are not items.

Next: keep expanding bank across important existing builds as assessment queue drains.
Prepared research for RavenFrost bank (NOT written yet):19existing '-N-raven-frost'
roles acrossBerserk1,Hammer3,DragonTalon0/1,Dream0/1/2,FoH3,LightningFury1/2/3,
LightningStrike1/2,MirroredBlades1/2,Smite1/2,Strafe1/2; Zeal already covered.
Native lowroll15Dex150AR,20coldabsorb40manaCBF; native cold15–45duration100frames.
Use explicit source variant locators in wp-a-builds.json; wrongclass and unknown
class conditions, exact role stat contributions. Smite1/2 andHammer3 excludeAR;
FoH3TriBrid includes attack-phaseAR but not FoH/Smite hit chance. To test per-stat
absence while otherPaladinroles legitimately annotateAR, extendCase assertions to
forbid a given configuration at a given stat (current absent_configurations forbids
it globally; absent_annotations forbids the entire stat acrossallroles). Do not make
globalARabsence assertions. Important further work: Zeal companion sets, remaining
words, Act5earlyarmor/helm alternatives, all other queuedidentities/sourceclosure,
pricing dispositions, finalfullsuite.11planner conflicts+1missingplanner remain;
absence cannot be excluded as no-demand. Do not stop at this checkpoint.

## Active checkpoint — item bank and completion evidence, 2026-09-27

Goal remains ACTIVE. Latest selected generation
`dbbb37a6e315268fbc2abd58d4ebafab54c0b3133058080f71beef1d55b334e2`:
2350 profiles,2342stat configurations,72artifacts. Jewelry7 and standalone gloves6
for Zeal published. Low native rolls and correct skill recipients; jewelry cannot
be ethereal/socketed, glove procs require percent-chance units. Native/set sources
verified. No inferred complete loadout, passive charged skills or numeric premium.
One-shot adders add_zeal_jewelry.py and add_zeal_gloves.py EXECUTED; NEVER rerun.

Item bank now113pipeline scenarios +3coverage +7range-proof tests =123passed
selected42.42s and staged37.14s. All18 saved staged/selected outputs identical
(text/extraction/prices), unchanged from87f44c checkpoint.15focused rules/stat
checks pass;48source/completion checks pass. New jewelry expectations corrected:
role is partial due advisory full-loadout uncertainty, but rule_trace must be true
and exact configuration contribution present. Wrong/unknown class stays strict.
Coverage3547targets,3511missing cases; sample success is NOT all-build coverage.

Completion now rejects unresolved reviewed-dimension artifact/JSON-pointer or
configuration-version citations. Test24+5pass. named_matrix links universal named
baseline/leveling reviews and excludes only known non-named qualities from named
tiers; no market/desirability/roll gaps closed by that linkage.40relatedchecks pass.
Latest completion tmp/named-baseline-completion.json:118792rawtasks (not items),
952reviewed exact occurrences;2572identities/62891occurrences. Scope still incomplete.
Further applicability/source closure and final full-suite/evidence gates remain.

Zeal utility belts3 adder tmp/add_zeal_utility_belts.py EXECUTED ONCE; NEVER rerun.
Red3 confirmed. Bank9 installed/registered;122pipelinecases plus10audit/rangechecks.
Initial chained run stopped at import-order lint after applying; fixed. Session50686
now focusedgreen, rebuild dependencies, staged bank/replay. Logs tmp/zeal-utility-belts-*.
Expected2353profiles/2345statconfigs. After green compare to selecteddbbb37,
publish, selected replay/bank, coverage then completion. Preserve all generations.
Continue remaining Zeal companions, completed words, Act5merc and full queue.
No runtime Python changes from these maintenance/test additions; no host restart,
live collection, staging or commits requested/performed. Continue full queue.

## Latest checkpoint — 2026-09-27

Selected87f44c282bc5d35a7f25654717777f79d7efc36ad223e17d27b040d545eed277;
2337profiles/2329stat configurations/72artifacts. Zeal melee/survival13 additions
published,18saved replay outputs match staged. Item bank uses dirty-equals,
74pipeline scenarios+3coverage tests pass;7range-proof checks also pass. Required
bank inventory3534targets;3511need cases. Full all-item goal remains ACTIVE.
Previous entries below are historical; do not rerun successful adders. See handoff.

## Current active goal — 2026-09-27

Persistent all-item goal is ACTIVE, not complete. Continue through all work; never
stop at batch publication. Latest selected generation:
`133f127b14d105c257cce388df25a5bf04b6ccaa89987d4d42d216e822682876`.
2324profiles/2316stat configurations/71artifacts. Published Zeal charge patterns3
and Naj Enigma context guard. All18 staged/published text/extraction/prices match;
all unchanged vs previous752fd998. Tier gate complete.17affected tests pass,
lint/diff clean. Full-suite final gate still pending. No processes remain at this
checkpoint. Completion ledger regenerated against current artifacts (not published
as runtime data): tmp/completion-after-zeal-charges.json summary and persistent
pricing/data/appraisal-completion.json queue. Exact occurrence links are conservative;
remaining raw task counts are NOT distinct item counts or trustworthy final closure.

Next prepared research: six Zeal melee boots/belts. NOT EXECUTED:
 tmp/add_zeal_melee_accessories.py. Draft tests (not yet copied/run):
 tmp/zeal_melee_accessory_tests.py. Copy into tests/pricing/knowledge/assessment/
 test_zeal_melee_accessories.py, run red, review adder and native stat recipients,
apply once, green, rebuild/publish/replay, continue queue. Names and native stats
verified; boot/belt base names in draft resolved via facts. Native dmg-norm maps to
mindamage/maxdamage (War Traveler); native IDs in earlier entry. Adder counts
expect2316stat configs, raises to2322. Avoid conflating Goblin Toe (CB only) with
Gore Rider's CB/OW/DS: draft shared prose says where applicable, better specialize.

Successful adders DO NOT RERUN: add_zeal_footnote_swaps.py, add_zeal_fade_prebuff.py,
add_zeal_charge_patterns.py. Naj native locator repair and Enigma guard are already
applied with fingerprints refreshed. Earlier publication/batch status entries below
are historical. Need full source/applicability/final-gate integration and all remaining
item assessment; current work is nowhere near final closure.

<!-- completion-contract-2026-09-27 -->
**Authoritative end goal and stopping rule:** [Completion contract](COMPLETION_CONTRACT.md).
The task is unfinished until all final gates pass for one scope manifest and
selected generation, with zero pending or blocked required work. Batches,
publications and milestones never stop execution. Next implementation priority:
make the completion ledger/gate trustworthy, then drain the entire remaining queue.
This planning update changes no runtime artifacts or published coverage claims.

## 2026-09-27 — All-item assessment continuation

User requests coverage of every item and known useful setup. Phase 1 is complete;
Phase 2 remains incomplete. Follow assessment/planning/GUIDE_FIRST.md. Offline only;
no staging, commits, host probes or worker restart in this continuation.

Latest publication: `519baede215d35e06dda726c80e1af3ef4187ea233dadc343373d0f2b6eaa0a0`.
2,317 profiles /2,309 stat configurations /71 artifacts. Tier gate complete.
All18 saved reports/extraction/prices unchanged from selected Zeal-ring generation;
all18 selected outputs match staged. Logs tmp/caster-armor-complete-{publication,
staged-replay,published-replay}.json. Phase1 complete; Phase2 NOT complete.

Published batches:
- Zeal rare-ring combinations6 and exact-span provenance linking: eight ring tests,
 34 source-link related tests, all6 source occurrences bind in inventory/dossiers.
- Enigma3/CoH6 caster armor uses: red2/green4.
- FOH Gheed farming use1 from explicit guide section34: red1, green in92.
- Caster armor remainder8: Que-Hegan2, Ormus4, Bone1, SpiritShroud1: red4/green6.
 Repairable player armor; legal native/upgraded bases. Ormus native random skills
 use IDs36–60: FireWall51/Meteor56 optional, Hydra/FrozenOrb impossible. Meteorb
 section9 supports both cold and fire damage. No15% native-roll preference inferred
 from socket-inflated totals; decoder owns ranges. Summoner Warlock excludes MAEK;
 Bone proc is not assumed active or credited as minion damage.

Full regression:4296 passed,76 failed,3 skipped in5311.71s. All76 failure tracebacks
were obsolete live-bundle demand totals/build lists or expanded selectors. Preserve
prior breadth plus unique-build counting; isolated-fixture exact tests unchanged.
Ground early test scopes its15 early profiles; Torch tests all classes/new profiles;
ring test allows new configurations; Trang lower-bound grade is nowHigh; Vipermagi
keeps Blizzard as an alternative without excluding the newly reviewed alternatives.
All source exclusions, matching/stat/companion/wearer constraints retained.
All76 failures plus new charm/armor/stat/source checks passed:92 tests in
 tmp/assessment-corrections-green.log. Later armor8 passed6 separately. Full log:
 tmp/all-assessment-regression.log. No fresh all-green full-suite run claimed.
Ruff and git diff --check passed. No active processes remain from this checkpoint.

EXECUTED ONCE: add_caster_armor_words.py, add_foh_gheeds.py,
add_remaining_caster_armor.py, fix_expanded_build_demand_tests.py and all prior
successful adders. Never rerun. Obsolete fix_breadth_regression_assertions.py was
NOT executed; do not use it. Armor research notes have now been implemented.

Next bounded batch: Zeal player gear in guide section32. Read its footnotes before
adding rules: Treachery/DemonLimb primarily prebuff Fade/Enchant; Wizardspike swap
before CTA or with party Barbarian BO; teleport-charge items only without Enigma.
Guillaume filled-socket variants and rare-ring six combinations already reviewed.
Remaining named standalone gear and set-dependent alternatives need explicit roles;
do not flatten prebuffs, swaps, companion sets or Act5 merc roles into generic fits.
Other section-sourced pattern bindings still need exact-occurrence review.

No host restart or live collection. Prior runtime socket predicate changes still
need host restart if its worker predates them; these maintenance/data additions
reload through publication generations. No git staging or commits performed.

Coverage: tmp/named-build-breadth-gaps.json lists142 named identities (850 item/build
pairs) with at least
one missing build lead. This is only breadth, not configuration/variant closure.
Dossier review_state is deliberately hardcoded pending; its283/153/1108/1028 queues
are discovery partitions, not counts that shrink after every reviewed use. Do not
claim completion from first-use named queue zero or reviewed role totals.
Next substantial gaps: remaining caster named armor/staves, Zeal player/Act5 merc
configurations, remaining Necromancer gear aliases, exact-source binding of older
section-sourced patterns, specialist/rare/base patterns and no-guide identities.
Source closure additionally has11 planner-reference conflicts and1 planner gap;
these must remain explicit until resolved, not be counted as complete coverage.

Previous selected491eb419754c82af967e573e4a27b765e6e5ab7f38cea00401d05cacd27e2d72:
1896/1888 Renewed Sunder27. All18 selected/staged exact matches verified.
Renewed uses cover Black9/Bone3/Cold2/Lightning11/Fire2; generated custom-affix
bounds remain unavailable. No original GrandCharm/unique CraftedSunder confusion.

Jewel54: Rainbow15, ProtectorStone12, GuardianThunder12, GuardianLight8,
DefenderFire4, ProtectorFrost2, DefenderBile1. Exact named recipient dependency,
matching native elemental keys and one-Colossal limit. Does not endorse host item
or assume full loadout. Berserk excludes unverified mastery357; SummonerStone
credits only Find/XP (physical-pierce CorpseExplosion remains unverified).
Source validator requires JSON locators: cached Colossal guide limit exported to
pricing/data/colossal-jewel-guide-evidence.json, exact sentence with raw SHA and
correct page date2026-02-19; source URL /d2/meta/colossal-ancients. Native definitions
supply jewel mechanics. Initial HTML-only corroboration failed validation; fixed.
Witchwild narrow MF planner source: upgraded DiamondBow, two distinct linkedjewels,
one named ProtectorStone with native MF minimum15. No unspecified secondjewel roll
requirement. Strafe excludes normal-attack MagicArrow effect; Amp procunit checked.

All adders through add_named_jewels.py and add_witchwild.py EXECUTED ONCE.
Also add_renewed_sunders.py EXECUTED. Never rerun. Jewel source repair and trim
scripts executed. No runtime engine changes. Data reload at request boundaries.
All adders through add_caster_core_guide.py EXECUTED ONCE, including
add_topaz_armor.py, add_inventory_charm_expansion.py, add_caster_guide_utility.py.
Tal adder and caster weapon adder EXECUTED ONCE; do not rerun. Live Tal module
includes a later source-footnote correction: Lidless Eye requires another compatible
Tal piece for all four Sorceress guides. Armor/helm/belt innate properties remain
independent; 2/3/5-piece partials require distinct compatible companions. Warlock
cannot count Sorceress-only orb. 4 guide source quotes and fingerprints updated.
Caster weapons18: Wizard6, SuicideBranch2, SpectralShard2, Oculus4, Eschuta2,
Fathom2. Relevant fire/cold properties only; casting-only ethereal allowed except
native nonethereal Wizardspike; no attack-only damage or minion MAEK assumptions.
Summoner Torch table correction remains pinned to Warlock planner evidence.
 Then remaining
named variants/base/affix/source gaps. No invented prices or guide recommendations.

Historical Steel Grand Charm fix: exactly4 of60491 demand rows changed (falseSteel
runewords); other demand rows and all tier/value-watch decisions unchanged. Source
fingerprints repaired, all tier gates and saved replays verified. Do not blindly repin.

Phase1:408 uniques +140 set pieces,35 complete sets;2958 rendered cases, all tier
counters zero. Leveling158 recommended/29 conditional/361 no-specific. Colors
high green/mid yellow/low blue/trash red. Numerical prices remain a separate gap.
Base audit431 unresearched/48 cached-only/44 historical. No invented estimates.
Dossier denominator2572 identities/62891 occurrences. Named-use expansions,
153 base/pattern leads,1106 unresolved identities and1027 without verified guide
leads remain. Missing guide evidence is not no demand or worthless.

Regression: full run at1706 profiles had4126 passed/3 skipped/1 stale glove-test
selector; corrected to rare/magic scope and29 affected tests passed. No full rerun
claimed. Subsequent batches use focused tests, Ruff, rebuild/publication validation
and all18 saved-item replays. Sources stayed stable during the full run.

Commands: uv run --offline python tmp/final-charge-routing-rebuild.py;
uv run --offline python -m pricing.knowledge.assessment.maintenance.replay;
uv run --offline python -m pricing.knowledge.publication; then replay with
--publication-store pricing/data/generations. Compare text/extraction/price_estimate.
Preserve generations. Runtime reloads data at request boundaries.

## Next planned work — offline guides first

[GUIDE_FIRST G1–G5](GUIDE_FIRST.md) is the next delivery order: every cached
build/variant/player/mercenary item → deduplicated per-item demand → reviewed guide
configurations → compact grouped Build use → offline regression/publication.
Reviewed demand batches and compact reports are implemented as recorded below;
this does not establish full guide or item coverage. Universal unique/set/piece tiers are complete as recorded above; remaining stat
combination coverage includes items absent from guides.

## G1 inventory checkpoint — 2026-09-25

`python -m pricing.knowledge.assessment.maintenance.guide_inventory` now builds
`pricing/data/appraisal-guide-inventory.json` from the existing structured ledger
and variant slots. It preserves every occurrence's details and provenance, seeds
unmentioned catalog identities, and links conservative semantic configurations.
Baseline: 62,891 occurrences; 33 cached guides (34 occurrence build labels including
shared-planner); 1,355 catalog identities; 2,887 total identity/review buckets;
19,311 unresolved occurrences; 297 reviewed profiles / 275 distinct configurations.
All sources registered and hashes verified. A deterministic repeat took 6.425s on
this workspace, with no raw guide/planner extraction; no speedup claim is made.

This is a 109 MB maintenance checkpoint, not a hot-path or published artifact.
G1 remains incomplete: source-slot completeness, set expansion, aliases and
recommendation strength need explicit auditing. G2 grades and G4 compact reporting
are not implemented by this inventory. Next work must use GUIDE_FIRST order rather
than returning to isolated per-build additions.

### Structured variant slot audit

The maintenance inventory now retains source-slot dispositions for the separate
`wp-a-variants` documents: 1,687 represented item slots, 434 empty slots and 116
mercenary context fields across 232 present sides. No missing/conflicting labels
were found in this subset. Original context (including delta/planner flags and
quotes) is preserved; representation does not establish endorsement or inheritance.
The consolidated `wp-a-builds` audit additionally accounts for 2,269 item slots,
441 empty slots and 132 context fields; all 5,510 source occurrences are linked,
with no missing/conflicting labels. It preserves legacy unescaped locators, staged
mercenary alternatives and prose-only entries. Eleven focused tests pass.
G1 still requires raw planner/source section accounting, explicit inheritance/aliases and set links;
these subset counts do not prove the global source-slot gate.

### Planner structure reconciliation

The maintenance audit now traverses cached planner profiles, inventory/cube,
mercenary equipment and socket children without repeating name extraction.
All 49,780 planner occurrences have matching source references; 8,945 empty slots,
740 empty containers and four absent containers remain explicit. No missing,
conflicting or unaccounted occurrences were found. The existing unavailable
planner `1r010653` remains a source gap. Thirteen focused tests pass, including
missing children, mismatched references and cycles. These are structural counts,
not endorsed build uses; raw guide sections and semantic relationships still need
G1 review. Runtime publication is unchanged.

### Set relationship inventory

Definition-backed relationships now retain 1,913 piece-membership references,
eight set-reference candidates and two explicit full-set candidates. Every link
retains the original occurrence/locator and complete canonical member list.
Partial-set wording does not require all pieces; none of these links establishes
standalone endorsement. Definition hash/date/input provenance is retained.
Fifteen focused tests pass. Alias resolution and semantic set-use review remain
pending, so these candidate links do not close G1 or increase demand votes.

### Canonical planner identity correction

The reverse index now uses explicit planner canonical IDs, checking category and
canonical/alias labels against the catalog and quality prefix against planner
quality. Conflicts stay unresolved without name fallback. This resolves 15,380
falsely unresolved affixed base occurrences: unresolved occurrences decrease from
19,311 to 3,931; total identity buckets decrease from 2,887 to 2,739. All 49,780
planner identities reconcile with zero conflicts. Rarity, original display labels,
stats and source details remain on the original occurrences; grouping by base
identity does not pool affix configurations or increase demand votes.
Twenty focused tests pass. Runtime publication is unchanged.

### Explicit variant context dispositions

The inventory now records 232 source variant contexts across consolidated and
separate documents (copies remain provenance, not independent votes): 42 explicitly
Hardcore contexts excluded from Softcore demand, 22 planner-only contexts requiring
endorsement review and 168 other contexts awaiting review. There are 34 delta-only
source records; none has a structured parent link, so no equipment inheritance is
inferred. Original purpose, notes, quotes and planner references remain attached.
Twenty-two focused tests pass. These source dispositions do not alter runtime roles
or establish completed G1/G2 review.

### Cached guide section inventory

All cached `guides__*.html` files are now independently enumerated: 33 pages,
2,015 text sections, zero pages outside the existing demand manifest. Section
heading, anchor, source position and full prose are retained in the maintenance-only
`appraisal-guide-sections.json`. Hash/extractor-version reuse avoids parsing unchanged
pages; repeat output is byte-identical. Script/style text is excluded; navigation
and other non-item prose remain pending relevance review. Twenty-four focused tests
pass. Section presence is not semantic completeness: span-to-ledger reconciliation
and section review remain next, before declaring G1 complete.

### Guide span reconciliation and embedded references

All 5,201 saved guide occurrences reconcile with cached extractor spans; no ledger
rows are unaccounted for. The audit additionally retains 271 empty unresolved spans
that the legacy extractor skipped. Inspection found planner tooltips encode
profile/set/item IDs rather than visible names. Section cache v3 now preserves all
397 embedded item references with source positions and section links; resolving these
against cached planner profiles is the next concrete gap. These references are not
yet endorsements or active rules. Twenty-six focused tests pass; runtime unchanged.

### Embedded tooltip resolution

The 397 guide references now resolve against exact cached planner UID/item IDs:
203 link to existing set occurrences, 107 identify definitions outside that set's
recorded loadout, 82 reference absent sets and five lack the referenced item.
Available item definitions are retained even when the set is absent; no other set
is substituted. These review links preserve section positions and item/profile
locators without promoting planner rolls to thresholds. Twenty-eight focused tests
pass. Runtime rules/reports remain unchanged. Next review these source conflicts
and guide prose together before producing endorsed G2 counts.

### Source conflict review queue

Inspection confirms the 82 absent-set references target six UIDs not present in
their cached planner profile lists. They are now six grouped source blockers,
alongside five missing-item blockers. Every affected guide position/section and
available set UID/name is retained; definition-only alternatives are not classified
as missing-source failures. Thirty focused tests pass. These blockers affect their
own uses; they do not prevent reviewed configurations elsewhere from progressing
through G2–G5 once the global inventory disposition gate is checked.

### First reviewed demand batch — Insight

Added maintenance.guide_demand and explicit guide_use_reviews.json decisions for
12 existing Insight profiles: 11 guide-backed preferred configurations, one
planner-only example excluded from votes. Five distinct builds support the identity;
summary stays Pending with High lower-bound breadth while corpus review is incomplete.
Variant/player/merc duplicates cannot inflate votes; historical, shared-planner,
Hardcore, examples and unreviewed evidence cannot vote. Source and complete profile
fingerprints invalidate stale reviews. Four red-green behavior tests cover counting,
grade boundaries, exclusions and invalidation. This is an unpublished maintenance
batch; G1 semantic gaps remain explicit and no captured-base fit is inferred.
Next connect the prepared summary to compact BuildUseSummary and validate Insight
alongside existing saved reports before runtime publication.

### Compact BuildUseSummary prototype

Added a pure immutable summary model with an eight-entry budget, three visible
clusters/build labels, shared roll targets, explicit failed/unknown counts and all
original role details retained. Duplicate role evidence is idempotent; conflicting
same-ID results fail. Conservative grouping preserves base/dependency/beneficiary
and variant distinctions. Three red-green tests pass. Saved Insight preview has
eight entries and all 12 role details, with five conditional builds distinct from
the reviewed identity-demand lower bound. Preview: tmp/insight-build-use-preview.txt.
Not wired into live reporting yet: grouping labels/progression need refinement,
and full-detail access plus terminal/OSD parity and publication integration remain.
No price/matching/roll behavior changed.

### Compact detail access and restrictions

The prototype now renders readable build names and surfaces a failed requirement
even when its group is omitted. Additional restriction counts route to full detail.
A saved-record CLI (`python -m inventory_tracking.appraisal.build_use_summary
RECORD --full`) exposes all uses, conditions, alternatives and source locators.
Five focused tests pass. Saved Insight compact/full commands verified eight compact
entries and all 12 source-backed detailed roles. Live terminal/OSD wiring, reviewed
role/progression grouping and pinned demand publication remain outstanding.

### Compact renderer enabled

The terminal and OSD now call the same compact BuildUseSummary through the shared
presentation model. The previous detailed formatter remains available, alongside
the saved-record `--full` CLI. Heading styling is preserved. Red parity test → green;
125 focused tests and full suite 2,622 passed / 3 skipped. All 18 published saved-item
replays retain identical assessment semantics and prices; five report texts change,
including Insight's eight-entry Build use. Historical artifact hashes differ but
all remaining assessment fields match. No artifact publication change was needed
for this Python presentation change; restart the worker. Prepared guide demand is
not yet published/wired, so live headings omit its count. Reviewed role/progression
aggregation and demand publication remain next; this does not close G4/G5 broadly.

### Reviewed demand published

Guide-use decisions and summaries are now embedded in the compiled profile bundle;
publication verifies role fingerprints and recomputed counts. Runtime uses the same
pinned profile bytes; legacy bundles omit demand rather than consulting working-tree
reviews. Insight now renders Pending / at least five builds independently of item
fit. Full suite: 2,624 passed / 3 skipped; additional pinned-legacy regression passes.
All 18 saved prices/role/fact/tier/leveling results unchanged; staged/published text
matches and only Insight's heading changes from the prior compact baseline.
Published generation `446e4de125a37891d674f924ed387234047b078e3c57bd558fd8ffa085552b25` (46 artifacts).
Restart worker for Python changes. Other identities and G1 semantic gaps remain
pending; next refine role/progression grouping and extend reviewed demand batches.

### Reviewed progression and grouping boundary fix

Compact grouping now includes evaluated rule and skill traces; previously different
rules could share a row if visible labels matched. Reviewed presentation stages
allow equivalent variants to merge, with original variants retained in full detail.
Insight Starter, Endgame (Standard/MF), and Ubers stages are explicit reviewed data;
no arbitrary unknown-variant stage inference. Actual Insight loadouts remain split
where dependencies/conditions differ. Starter contexts sort ahead of later stages.
121 focused tests; full 2,626 passed / 3 skipped. All 18 saved prices and evaluated
role/fact/tier/leveling results unchanged; staged/published text parity verified.
Published `59756e9538135c0fdb2c0ff8256487c23f59cbd9c6af70a555dad4ed4fa468a4`. Restart worker for Python changes.
Further role-summary refinement and additional reviewed demand batches remain.

### Second reviewed demand batch — Infinity and Sazabi

Added six source-reviewed identity uses: Infinity's three player/merc configurations
count as two distinct builds; Sazabi's three pieces each retain one conditional Ubers
build endorsement. The full-set, Act 5 Frenzy, rune and companion requirements remain
in their existing executable roles. All grades remain Pending because corpus review
is incomplete. Reviewed demand now covers five identities / 18 decisions (one excluded
planner-only Insight example). 29 focused tests pass, all 18 saved prices/assessments
unchanged; only Sazabi's saved heading changes. Staged/published replay parity passes.
Published `a67fb831e984375a5b1256f46e67bf962bcb3954b75f9fb078a73fd89469dd3a`. The next batch must serve the specialist/leveling
or unresolved tail after these two demand batches, per GUIDE_FIRST scheduling.

### Scheduled tail batch — Death's set early gear

Reviewed four explicit Starter/Budget uses for Death's Guard (three builds) and
Death's Hand (one build). Independent cached leveling evidence remains active;
Death's Hand's paired-belt condition and upgraded Death's Guard requirements remain
in the evaluator. One-build breadth does not remove conditional leveling usefulness.
Demand records now cover seven identities / 22 decisions, including the excluded
planner-only Insight example. 18 focused tests pass; all 18 saved reports, prices
and assessment semantics unchanged; staged/published parity verified.
Published `0dcd1656c164abfcf3eb80a250ce23b0e279e015108ee79e5a088d5be40824e1`. Tail scheduling obligation after two demand batches
is met; next demand batches should broaden identity coverage with source-backed
rules, while remaining tiers/market/source gaps stay explicit.

### Utility demand batch — Teleport swap and Enchant prebuff

Reviewed 18 existing source-backed utility roles: Naj's Puzzler has 13 distinct
endorsed-alternative builds; its planner-only Budget example is excluded. Demon Limb
has four prebuff contexts across three builds, with Strafe's Lava Gout alternative
kept separate from preferred uses. Charge availability, recharge/ethereal limits and
equipment requirements stay in the evaluator. Demand review now covers nine identities
and 40 decisions (two excluded planner examples), not nine priced identities.
36 focused tests pass; all 18 saved texts/prices/assessment semantics unchanged;
staged/published replay parity passes. Published `e742e521f6a2d4b2d5f9fc5eff787c852d43b4b44d14362222465734bcf31af1`.
Next one demand batch may precede the scheduled tail batch. Broad scope remains open.


## 2026-09-25 — mercenary gear demand batch

Reviewed 18 existing role records across seven additional identities. Distinct
endorsing builds: Vampire Gaze 4, Crown of Thieves 1, Stealskull 3, Duriel's Shell 2,
Kira's Guardian 1, Rockstopper 1 and Undead Crown 1. Crown's planner-only Leap example
is excluded. Cannot Be Frozen and Fissure starter alternatives remain alternatives;
mercenary/loadout/socket/ethereal conditions remain in the existing evaluator.
Demand review totals: 58 decisions, 16 identities, three excluded planner examples.
These are incomplete demand lower bounds, not new prices or completed named tiers.

Red: missing mercenary demand summary. Green: 11 demand tests and 28 affected role
tests; Ruff passes. All 18 saved texts, prices, roles, facts, tiers and leveling
results remain unchanged. Staged/published assessments agree apart from publication
provenance; text and price parity verified. Published generation:
`4547b5c945281cdf79167cbbfe6c31e026388c208d88f63e7d91492875fe3e79`.
Evidence: `tmp/merc-demand-*`; regression in
`tests/pricing/knowledge/assessment/test_guide_demand_runtime.py`.
Rebuild profiles and maintenance guide_demand, replay, publish, then replay with
`--publication-store pricing/data/generations` using the existing offline commands.

This completes the second demand-led batch since the Death's set tail review.
Next: a specialist/leveling/unresolved tail batch before another demand-led batch.
All-item rule, source review, named tier and market gaps remain open. No new market
collection or runtime Python changes in this batch.


## 2026-09-25 — Sigon's starter combination tail batch

Reused nine existing executable roles and reviewed their three unchanged source
variant records. Added four named demand identities: Sigon's Visor (two builds),
Gage and Sabot (three each), Wrap (one). Starter farming context is preserved; it
is not automatically low-character-level leveling evidence. Strafe/Double Throw
helm-gloves-boots and Berserk gloves-belt-boots remain distinct configurations.
Player companions, Ort versus IAS-jewel socket conditions and unknown loadout
states retain their existing behavior. No whole-set expansion to uncited pieces.

Red: missing Sigon's demand summary. Green: 33 demand, starter-set, socket-payload
and upgrade tests (1.29s), Ruff and diff checks. All 18 saved texts/prices and
role/fact/tier/leveling results unchanged. Published replay equals staged replay
except artifact provenance. Generation:
`9700486b59d4c64738410089bbe62d0bbcd19f56a5dedd8c7086084b873796ca`.
Logs and replays: `tmp/sigons-tail-*`. Review totals: 67 decisions, 20 identities,
three excluded planner examples. No new evaluator or price rule was inferred.

Scheduled tail batch complete; next demand batch should broaden configuration
coverage beyond named items, reviewing how base/affixed patterns connect prepared
demand to captured-item matches. Current demand lookup is identity-name based;
pattern coverage must not be claimed from named-item counts. Reuse source-backed
amulet/ring/base rules, preserving skill identities and required combinations.
All-item named tiers (472 pending at last audit), source review, market and
architecture gates remain open. No network, staging or commits in this batch.


## 2026-09-25 — prepared demand for exact affixed configurations

Added reviewed `pattern` records referencing exact non-named profile IDs, with
source and full profile fingerprint validation. Prepared summaries keep a separate
namespace. Runtime `demand_for_item` selects only true item predicates with
matched/partial outcomes, unions distinct builds and preserves named identity
semantics. Missing/false/unknown/null traces add no votes; duplicate evaluated
roles do not inflate counts. Common pure counting moved to `demand_counts.py`.
Compact report labels the selected scope as matching stat combinations.

First three configurations: Lightning Starter magic +3 Lightning amulet; Nova
Starter magic +1 Lightning / 10 FCR; Blizzard Starter magic +1 Cold / 10 FCR.
Reviewed exact cached slot locators and non-planner-only Starter contexts. +3
Lightning/10 FCR yields two builds; without FCR one; Cold uses remain separate.
Wrong rarity and incomplete modifiers supply no claim. No new price/fit rule or
inference from a rare item's generated title. Counts: 70 review decisions across
20 named identities and three exact patterns; three excluded planner examples.

Red: missing pattern selector; then full-suite null-trace regression reproduced
and fixed. Green: 2,634 tests passed, three skipped (90.06s); Ruff and diff checks.
All 18 saved reports/prices/roles/facts/tiers/leveling unchanged; staged/published
assessment parity apart from provenance. Published:
`5c6089e0e90d19f07b8a7a798ca676a276fa83684fdddc5561186118f84ad655`.
Logs: `tmp/pattern-demand-*`. Restart the Alt+D worker for these Python changes.

First demand-led batch after Sigon's tail. Next: review source-backed rare-ring
combinations and base configurations through the same exact-pattern path; after
one more demand-led batch reserve a specialist/leveling tail. No arbitrary pattern
pooling: shared templates and full coverage matrix remain unfinished. All-item
named tiers, market coverage, source review and architecture gates remain open.
No new market collection, staging or commits.


## 2026-09-25 — rare-ring pattern demand batch

Reviewed all six existing rare-ring configurations: Lightning Starter/Ubers,
Nova Starter, Blizzard Starter/Magic Find/Set Build. Exact source hashes, slot
records and non-planner-only variant contexts checked. Candidate requirements
stay distinct from secondary planner roll targets. Repeated rings and variants
count once per build. Retained native element identities, quality restrictions,
complete modifier combinations and conditional full-loadout evaluation.

Red: rare-ring candidate had no prepared demand. Green: 23 pattern-demand,
rare-ring role and demand compiler/runtime tests; Ruff and diff checks. A cast-rate,
mana, all-resistance and MF ring matches five configurations across three builds;
removing two resistance elements removes the Starter Lightning/Nova combinations.
Unknown capture does not prove the missing resistance. Blizzard's strength/life/
cold-resist Starter combination works separately without requiring cast rate.
No new evaluator, named tier or numerical price assumptions.

All 18 saved texts/prices/role/fact/tier/leveling results unchanged; staged/published
assessments agree apart from artifact provenance. Published `bc4e4c5ca6d38b6d05af244e4b5ce3daee6214049a6ef5d212d9469ae99c8421`.
Evidence: `tmp/ring-demand-*`. Review totals: 76 decisions across 20 named identities
and nine exact patterns, including three excluded planner examples.

Second demand-led batch after Sigon's tail is complete. Next reserved tail:
review specialized base uses (for example Gold Find socketed swords), first checking
whether existing evaluated outcomes expose complete item predicates for prepared
demand selection. Null traces must remain unverified, never promoted by role name.
All-item source/configuration, named tiers, mechanics and market gaps remain open.
No runtime Python change, network collection, staging or commits in this batch.


## 2026-09-25 — specialized six-Lem sword tail batch

Reviewed seven existing Gold Find sword records against their exact source slots
and variant flags: Standard off-hand and both War Cry/Whirlwind swap hands qualify;
two planner-only Leap examples do not vote. Five configurations still count as one
build. Total reviews: 83 across 20 named identities and 16 patterns; five excluded
examples. This is demand coverage, not additional priced identities.

Preserved exact base/quality/class/socket predicates and six linked rune dependency.
Empty or differently filled swords remain conditional preparation; only the exact
six-Lem payload satisfies the rune dependency. Known three sockets, magic quality,
wrong class and unknown class do not establish this pattern's applicability.
Unknown item-level socket outcome remains explicit preparation, never an assertion
of a guaranteed six-socket result. Existing ethereal non-attacking limitations stay.
Report heading generalized from matching stat combinations to matching configurations.

Red: missing base-pattern demand, then report scope wording. Green: 38 focused
pattern/compiler/runtime, rune-payload and formatter tests; Ruff/diff checks. All18
saved texts/prices/roles/facts/tiers/leveling unchanged; staged/published parity
apart from provenance. Published `064e8d435a884f0a90c9c6055be8eb4a98de227d1871b64934d0f65814326278`. Evidence `tmp/gold-tail-*`.
Restart worker for formatter wording; no evaluator behavior changed.

Scheduled tail complete. Next focus: reusable base eligibility and socket-outcome
coverage against native definitions (GUIDE_FIRST B/D/G3), with reviewed desirability
kept separate. More demand records alone cannot close mechanics, stat-desirability,
named-tier or numerical-price coverage. Audit the current base path for item-level,
quality, recipe and socket dependencies before extending family templates.
Full source review, all named tiers and architecture/market gates remain incomplete.
No network collection, staging or commits.


## 2026-09-25 — base socket mechanics audit and unknown-state fixes

Cross-checked every cached legal type/capacity edge against local native weapon,
armor and item-type tables: 5,092 edges / 426 base identities, zero socket-cap
mismatches. Source hashes and dated evidence: `tmp/socket-native-audit.json`.
This verifies capacity data, not complete family desirability or prices.

Found and fixed two missing-evidence paths. `utility.socket_options` treated an
explicit null current socket count as zero, and absent item-type limits could
produce zero-socket outcomes or TypeError. It now returns conditional/unverified
results with no proposed counts. Base capacity is validated separately; known
unsocketable bases do not produce a zero-socket action. `prepare_sockets` could
label absent caps impossible or fail during low-quality normalization; it now
returns unverified with no preparation requests before either route is planned.
Valid existing socket and recipe rules remain unchanged.

Red: six utility cases plus six preparation cases reproduced the failures.
Green: 30 focused tests; full suite 2,648 passed / three skipped (93.56s), Ruff and
diff checks. All18 published saved texts/prices/full assessments unchanged.
Publication revalidation retains `064e8d435a884f0a90c9c6055be8eb4a98de227d1871b64934d0f65814326278` (no data rebuild/change needed).
Logs/replay: `tmp/socket-audit-*`. Restart worker for Python mechanics changes.

Next: turn the verified mechanical denominator into the planned independent
coverage matrix, linking legal base eligibility to reviewed desirability policies,
stat annotations and market evidence without conflating those dimensions. Review
remaining unsupported base families/recipes from that matrix; do not infer demand
from legal compatibility. All-item named-tier, source review, price and architecture
gates remain open. This mechanics audit does not consume a demand-led review batch;
Gold Find was the last scheduled tail. No network, staging or commits.


## 2026-09-25 — independent base coverage matrix foundation

Added maintenance/base_matrix.py with a deterministic offline command:
`uv run --offline python -m pricing.knowledge.assessment.maintenance.base_matrix`
redirect to `pricing/data/appraisal-base-matrix.json`. Native catalog denominator:
523 bases / 1,569 normal-superior-low-quality rows, including unmentioned and
unsocketable bases. All native socket-cap checks agree with cached recipe edges;
426 bases have legal type/capacity links. 114 quality rows have candidate profile
links (type ancestry/quality only), explicitly not reviewed template membership.

Separate dimensions: discovery, socket mechanics, recipe eligibility, desirability,
stat annotations, named-tier applicability, report and market evidence. Every state
has a reason; sources retain file/hash provenance. All1,569 recipe/desirability/
annotation/report/market rows remain pending membership audits; this does not erase
existing runtime features or claim they are fully covered. Named tiers excluded
only because these are base-quality rows, not because named items leave scope.
Base-level market counts never become quality/ethereal/socket/roll-matched prices.

Red: missing matrix module. Green: 32 matrix, utility and preparation tests; Ruff,
diff check and byte-identical real-corpus regeneration. Tests verify full denominator,
unmentioned bases, duplicate edge idempotence, unsupported quality membership,
independence of market/desirability and conflicting/missing cap evidence. No runtime
code/artifact changes; selected generation remains the last published Gold Find
bundle. No new network, staging or commits.

Next: audit exact base/template membership and recipe availability into this matrix,
including reviewed mechanical exclusions where native socket/type rules prove them.
Do not leave every dimension permanently pending or mark type-name links reviewed.
Then integrate named/affixed configuration dimensions with existing audits; this
base-only matrix is not yet the required unified all-item matrix. Full all-item
pricing, tiers, useful modifiers and source/architecture gates remain incomplete.


## 2026-09-25 — native recipe membership closes mechanical matrix dimension

Added maintenance/recipe_eligibility.py and integrated it into base_matrix. It
independently enumerates completed native recipes using both type parents,
excluded types, base capacity, exact rune order/count and complete flags. Missing
or unexpected cached edges block review; duplicate edges are idempotent. Absent
catalogs remain pending; empty catalogs and incomplete ancestry block conclusions.
No use/value exclusion follows from missing or incompatible runeword recipes.

Actual corpus: 99 completed native recipes, 5,092 matching legal edges, 426 bases
verified and 97 mechanically excluded from runeword compatibility; zero conflicts.
Across quality rows: 1,278 reviewed / 291 excluded type-capacity entries. Full mode
availability and quality-specific preparation remain pending separately. No new
Non-Ladder availability claims, desired-base assignments or price assumptions.

Red: missing native membership module, then empty-catalog false exclusion.
Green: 35 distinct focused native/matrix/utility/preparation tests; Ruff and diff
checks. Real matrix regeneration byte-identical after validation. Native recipe
file/hash added to source manifest. Output pricing/data/appraisal-base-matrix.json;
command unchanged. Maintenance-only changes; no runtime behavior/artifact change
or need to republish the existing runtime generation.

Next: close recipe mode/quality-route evidence and exact reviewed template
membership using this matrix; integrate named and affixed configurations into the
unified all-item matrix. No source absence or mechanical exclusion substitutes for
reviewed demand/tier/price conclusions. All-item tier, market, annotation and
architecture gates remain incomplete. No network, staging or commits.


## 2026-09-25 — combination-aware stat evaluator foundation

Inspection confirmed that §8.1 desirability was not implemented: report colors
represent roll quality only. Added immutable StatConfiguration/StatPriority/
StatEvaluation and pure StatsEvaluator in assessment/stat_evaluation.py. It reuses
typed predicates, applies explicit quality/type filters and complete mandatory
combinations before activation, retains traces/provenance and merges strongest
positive annotations only across independently matched configurations. Source,
version, role linkage, review state and rationale are required. No conversion from
important_stats, no compensation by optional stats, no fake absent stat rows,
no default grey/trash and no inference of roll quality.

Red: evaluator import/contracts absent. Green: five evaluator tests plus five
existing pattern-demand tests; Ruff/diff checks. Cases cover X+Y, below/unknown Y,
quality mismatch, independent incomplete/complete uses, alternatives, exclusions,
context, identification/socket state, unknown review, inactive supporting stats,
duplicate/conflicting configs and immutable inputs/results. Roll channel remains
unassessed. No runtime integration/config publication or report change yet.

Next required step: reviewed configuration compiler with role fingerprint/source
validation, reuse existing role outcomes/dependencies (do not create another role
engine), indexed pinned artifact and shared result integration, then terminal/OSD
line mappings and independent dot/text colors. First real configurations should
use the already-reviewed amulet/ring combinations; priorities need explicit review,
not inferred importance lists. All-family migration, roll policy and coverage-aware
irrelevance remain required. No price behavior change, network, staging or commits.


## 2026-09-25 — stat compiler and linked-role gating

StatsEvaluator now consumes existing RoleAssessment outcomes or compatibility
mappings, defaults missing roles to unknown, and retains complete linked dependency/
preparation evidence. Conditional/failed/unknown roles cannot earn confirmed markers;
duplicate identical outcomes are stable and conflicting outcomes rejected. Standalone
combination tests explicitly supply matched role fixtures. No second role engine.

Added maintenance/stat_configurations.py: exact role fingerprint, source path within
root, source-file SHA256, review date, explicit scope/predicate and priority validation.
A changed role or source invalidates the review. No auto-conversion from important_stats.
Three explicit source-reviewed amulet priorities are in rules/stat_use_reviews.json:
Lightning Starter skill ranks, Nova Lightning+FCR, Blizzard Cold+FCR. Their full existing
role conditions remain conditional. Real typed-role regression proves these do not gain
confirmed markers merely because the item modifiers pass.

Red: missing role-outcome API and compiler module. Green: 13 focused evaluator,
compiler/real-role and pattern-demand tests; Ruff and diff checks. No runtime result
integration or publication yet; no report/price change. No network/staging/commits.

Next: embed compiled configurations in the pinned profile bundle with publication
validation, index selection, and immutable AssessmentResult field. Then implement
semantic stat-line mapping and terminal/OSD channels. Review generic role conditions
as mandatory versus advisory before promising confirmed green dots for local item
combinations; do not silently weaken existing dependency gates. All §8.1 roll-policy,
irrelevance, per-family coverage and full objective requirements remain outstanding.


## 2026-09-25 — published stat configurations and shared result integration

build_profiles now embeds explicit stat reviews and compiled configurations in the
existing profile artifact. stat_bundle.py serializes/deserializes immutable records
and validates semantic equivalence to embedded reviews/roles without source-file
reads. Offline compilation still verifies original source bytes; publication also
validates bundled profile sources. ProfileRepository validates configurations once
per generation and indexes quality/type applicability using existing CandidateIndex.
Runtime loads only prepared pinned data, never working-tree stat review files.

Engine passes existing typed roles to StatsEvaluator and stores its immutable result
in AssessmentResult.stat_evaluation. The compatibility JSON contains configurations,
traces and annotations when applicable. Explicit injected profiles do not inherit
bundled stat configurations. Legacy generations without the field make no claim;
a test proves an in-flight pinned snapshot stays unchanged across repository update.
Tampered priorities are rejected. Three reviewed amulet configurations remain
conditional under full-loadout requirements, with no confirmed positive annotations.

Red: absent bundle API, then integration fixture corrected to pin the complete
repository snapshot rather than supply an incomplete strict artifact bundle.
Green: full suite 2,663 passed / three skipped (89.79s), Ruff/diff checks. All18 saved
texts/prices/roles/facts/tiers/leveling unchanged; staged/published assessment parity
apart from provenance. Published `0097052e70bc61d8e7f86c46b322af917a4236219a7e2a9080e02d158340621f`. Evidence `tmp/stat-bundle-*`.
Restart Alt+D for Python integration. Terminal/OSD dot rendering is still pending.

Next: verified semantic-to-display stat attribution and independent desirability
marker/roll-text styling, with real conditional-use explanation and mandatory versus
advisory review. Preserve current role gates; do not force dots by erasing unmet
conditions. Then expand configurations/family coverage and remaining native/template,
named tier and scoped pricing gaps. No network, staging or commits.


## 2026-09-25 — independent stat marker and roll-text presentation

Added stat_markers.py, mapping prepared positive annotations to decoded display
lines with one unambiguous native StatKey. Green `● [desirable]` and readable blue
`● [supporting]` preserve plain-text meaning; stat text keeps its existing roll tone.
Combined lines with multiple keys and unreviewed/unsupported meanings remain
unmarked. No renderer evaluates role predicates or creates a grey/trash fallback.

StyledLine now supports immutable StyledSpan segments. Existing unsegmented payloads
retain their shape; segmented payloads validate that spans reproduce the literal
line. Rich and escaped GTK markup render the same independent colors. ItemAssessment
uses these lines for terminal and OSD. Current real amulet roles remain conditional,
so no positive marker is manufactured for them.

Red: missing marker renderer; integration fixture then supplied required decision
metadata. Green: 47 focused display/formatter checks; full suite 2,668 passed / three
skipped (92.45s), Ruff/diff checks. All18 published saved texts/prices/full assessments
unchanged. Evidence tmp/stat-markers-tests.log and tmp/stat-markers-published.json.
No data artifact change; generation remains 0097052e70bc61d8e7f86c46b322af917a4236219a7e2a9080e02d158340621f.
Restart worker and OSD process for Python mixed-span rendering support.

Next: review mandatory versus advisory conditions for real local stat combinations,
without weakening typed dependencies, and expand configuration coverage. Verify
combined/split line contribution attribution before marking those lines. Numeric-only
roll text styling, reviewed roll policies, coverage-aware irrelevant markers, all
base/magic/rare families and remaining tier/market/source/architecture gates are
still required. No network, staging or commits.


## 2026-09-25 — explicit advisory review enables local amulet markers

Reviewed the three cached Starter amulet slot requirements and their sole generic
full-loadout reminder. StatConfiguration now permits exact advisory_conditions;
compiler rejects text not present in the linked role conditions. Version2 amulet
reviews classify the whole-build breakpoint/resistance/resource reminder as advisory
for local skill/FCR usefulness only. Existing role outcomes remain partial and retain
their missing notes. No claim that the entire character build is ready.

Local annotations are allowed only when complete item predicates pass, remaining
missing notes are entirely the reviewed advisory set, and rule/skill/dependency/
equipment gates are true/met. Unknown/false dependencies, hypothetical preparation,
additional missing conditions or unreviewed notes still block markers. Empty advisory
fields are omitted when serializing, preserving prior published configuration shape.
Prior bundle semantic validation passes with the new implementation.

Red: absent advisory contract; then real amulet tests had no expected annotations.
Green: full suite 2,669 passed / three skipped (90.97s), Ruff/diff checks. End-to-end
example tmp/stat-advisory-example.txt shows two desirable markers while both relevant
build roles remain partial. All18 saved texts/prices/roles/facts/tiers/leveling unchanged;
staged/published parity apart from provenance. Published `1884b617e7a8d63b545acf48a183a795f61a6a242399d1c11ce1c148ef9dc9fe`.
Evidence tmp/stat-advisory-*. Restart worker for Python advisory gating changes.

Next: review explicit essential/supporting priorities for rare-ring configurations,
then further families, keeping whole-combination checks and exact advisory scope.
Combined/split stat attribution, numeric roll-only coloring, reviewed roll policies,
irrelevance coverage, full named tiers and market/source/architecture gates remain
required. No network, staging or commits.

## Rare-ring stat priorities — 2026-09-25

Six existing reviewed rare-ring roles now have explicit source-bound stat priorities:
Lightning Starter/Ubers, Nova Starter, Blizzard Starter/Magic Find/Set Build.
Together with the three amulet reviews, nine configurations are prepared. Cast
rate is desirable where required; source-listed resources, resistances and utility
are supporting only after the complete mandatory combination passes. The generic
loadout reminder is advisory for local markers; Nova resistance-mix and Uber gear
conditions still block confirmed markers. Role fit, roll quality and prices are
unchanged. No broad important_stats list was converted automatically.

Red/green: missing configurations failed first; 22 targeted tests now pass, with
positive, near-miss, incomplete-capture, wrong-quality and independent-use cases.
All 18 saved reports/prices/roles are unchanged; selected-generation replay matches
staged assessment output. Published generation:
`c218e03381259865c57d09ae988a998340b922d7a462e66fca72175de9490df7`.
This data-only annotation batch does not add demand votes or close all-family
annotation, unified coverage matrix, unique/set tier or market gaps. Next annotation
work should cover a reviewed base/specialist configuration and its boundary cases;
keep pending coverage dimensions explicit under GUIDE_FIRST.

## Six-Lem specialist stat annotations — 2026-09-25

Seven existing Gold Find Barbarian sword uses now have explicit source-bound gold
find priorities (16 total prepared stat configurations). A marker requires captured
450% gold find, exact six-Lem child linkage, eligible normal/superior base, known
Barbarian context and identification. It cannot come from the stat total alone.
Preparation and hand-use/durability notes are advisory only for this local marker
once payload validation passes; overall role fit remains conditional. Ethereal
status does not alter the gold-find marker or establish an ethereal premium.

Red/green: the new socket-stat test first failed on missing configurations. Thirty
affected tests pass, including wrong/missing rune links, duplicate child IDs, wrong
base/quality/socket count, unidentified items, insufficient gold find, unsocketed
bases and wrong/unknown class. All 18 saved reports, prices and role outcomes remain
unchanged; staged and selected-generation assessments agree. Publication:
`639c6e542b32a3cce3ad968ff83b05d0b3f3b1239f5c8a965879b82a607d8240`.
No new demand votes or market evidence. This specialist annotation batch still
leaves the unified identity/use coverage matrix, broader stat configurations,
unique/set tiers and price coverage unfinished. Next: unify the existing base
matrix and named/guide inventories so uncovered identities and configurations have
one explicit per-dimension denominator before further annotation batches.

## Unified coverage matrix foundation — 2026-09-25

`maintenance.coverage_matrix` joins the existing guide identity inventory, native
base-quality matrix, named tier audit and prepared use/stat configurations. Output:
`pricing/data/appraisal-coverage-matrix.json`. Each dimension retains state, reason
and source locator; independent row kinds have separate denominators. An existing
use rule never upgrades identity-wide desirability, leveling, report or price
coverage. Compiled stat priorities are separate from complete roll annotations.

Current counts: 2,739 identity/review rows (1,355 catalog-resolved, 1,384 unresolved),
1,569 base-quality rows, 368 use-quality assignments from 297 profiles. Named tier
joins retain 93 reviewed identities; 472 named identities remain pending. Sixteen
stat configurations cover 23 quality-specific uses. No total-row item-count claim.

Red/green checks cover omitted-from-guides identities, unresolved labels, independent
dimensions, stale tier sources, duplicate rows, dangling occurrence identities and
stale input snapshots. Seventeen affected tests pass; Ruff passes. Two complete
corpus builds are byte-identical. Base and guide inventories were refreshed offline
using existing extraction; 62,891 occurrences remain accounted for. Input hashes and
the guide profile fingerprint must match before the matrix is built.

This maintenance-only foundation is not the completed GUIDE_FIRST denominator:
separate leveling/valuable/observed-unsupported inputs still need an explicit union,
identity-to-template membership needs review, and known pattern applicability remains
unresolved. Next extend those missing input links and add actionable per-dimension
review queues. No runtime changes, market collection or new publication in this batch;
selected runtime generation remains `639c6e542b32a3cce3ad968ff83b05d0b3f3b1239f5c8a965879b82a607d8240`.

## Leveling and valuable-item coverage union — 2026-09-25

The maintenance matrix now retains all 75 prepared named leveling recommendations,
13 generic leveling patterns and 223 valuable-item records. All 298 named records
link by exact quality/name to one catalog identity; the 13 generic patterns stay
blocked for explicit identity/configuration review. Missing or ambiguous names are
never merged. Full evidence, dates, conditions and locators remain attached, with
reverse evidence links on identity rows. Reviewed explicit/inferred leveling uses
have their own reviewed dimension; they do not mark identity-wide review complete.
Watchlist tiers/asks do not become reviewed market tiers or exact prices.

Twenty affected tests pass after red/green cases for evidence union, ambiguity and
explicit source recommendations. Ruff passes; two complete matrix builds are
byte-identical. Source-input hashes from recommendations and watchlist are validated
alongside prior manifests. New denominator: 311 evidence records, separately from
2,739 identity/review, 1,569 base-quality and 368 use-quality rows.

Next: add durable observed-unsupported capture entries and actionable per-dimension
review queues, then close known pattern/template assignments. The 13 unlinked
leveling patterns are concrete tail candidates. No runtime change/publication or
live market collection; previous selected runtime generation remains active.

## Observed replay ledger and dimension queues — 2026-09-25

`maintenance.observed_review` imports saved replay results into the durable offline
`appraisal-observed-review.json` ledger. Capture path/content hash identifies each
record. Repeated imports are idempotent; changed assessments append history, retain
original facts/unknowns and replace only the current gap list. Unseen captures are
not dropped. Current corpus: 18 captures, 79 open gaps split into capture facts,
market mappings, reviewed-use coverage and market evidence. No gap implies zero
value, no demand or permission to collect live prices.

The unified matrix adds observed_capture rows and per-dimension review_queues with
row ID, reason and provenance. Independent dimensions remain pending unless their
own evidence is complete. Source hashes are checked before integration. Queue order
is deterministic by row ID; demand/effort scheduling is a later review step.

Red/green cases cover idempotence, resolution history, unseen capture retention and
queue separation. All 23 affected tests pass; Ruff/diff checks pass. Re-importing
the real ledger and rebuilding the matrix are byte-identical. Replayed all 18 saved
items against the selected generation: assessment, report and prices unchanged.
This is maintenance-only: no runtime publication or worker restart is required.

Next: use the queues to review generic leveling patterns and exact template
membership. The ledger currently covers imported saved replays only; automatic
worker capture ingestion and new unknown-item discovery remain separate work.
Full named tiers, family annotations and exact market coverage remain incomplete.

## Generic leveling audit and Topaz linkage fix — 2026-09-25

Audit correction: all 13 generic leveling patterns already have executable
conditional policies in policies/generic_leveling.py and policies/socket_leveling.py.
The matrix's 13 unlinked records indicate missing configuration links, not absent
runtime evaluators. Do not implement duplicate policies. Next maintenance work is
to link each source-indexed pattern to its exact policy applicability and tests.

The audit found a real false-positive path: Topaz armor accepted any positive MF
and a child with a Topaz base code without complete child linkage or sufficient
observed bonus. It now reuses complete_fillers to verify counts, unique unit IDs
and positions, then requires at least the sum of native Topaz MF bonuses (9/13/16/
20/24 by grade). One occupied and one empty socket remains valid; all sockets need
not be filled. Source values verified against pinned d2data gems.json. The positive
fixture now includes actual linked-child evidence instead of relying on incomplete
socket metadata. Regression cases failed before the fix and pass after it.

Full suite: 2,681 passed, 3 skipped in 89.35s. Ruff/diff checks pass. All 18 saved
published-generation replays are byte-equivalent as parsed JSON to the previous
run; no prices, roles or existing reports changed. This is a runtime Python fix:
restart the Alt+D worker to use it. Data generation is unchanged.

## Existing generic-leveling policy links — 2026-09-25

`maintenance.leveling_links` connects all 13 cached generic recommendations to
existing runtime policies. Affixed patterns retain exact quality/type/stat-group
applicability, archetypes and conditions; socket patterns retain the exact policy
symbol/source index. Each link carries the reviewed candidate-source fingerprint,
implementation hash and shared identified/non-ethereal guards. Both ring policies
remain distinct under their shared source pattern. Matching requires exact cached
name/timestamp/slots/context/market-evidence fields and source URL, not name alone.
Changed source fingerprints fail; changed recommendation text stays unlinked.

The matrix now has zero unlinked evidence rows in the current 311-record union:
298 named records and 13 linked patterns. Leveling coverage has 88 reviewed uses
(75 named plus 13 conditional patterns). This is not full identity coverage, stat
annotation support, report validation or market pricing; those dimensions stay
separate and pending. No new evaluator or runtime behavior was introduced.

Red/green link tests and the complete policy test directory pass: 275 tests.
Ruff/diff checks pass; two full matrix builds are byte-identical. Runtime generation
and saved-item behavior are unchanged from the previous validated Topaz fix.
Next use the matrix's remaining desirability/stat/tier queues for actual coverage
expansion; base template membership and 472 named tier reviews remain unfinished.

## Definition-backed named socket facets — 2026-09-25

The pending named-tier audit found explicit rune/gem payloads with missing socket
counts. Normalization now proves one filled socket only when every named unique/set
variant is socketable and lacks a native sock modifier, and property 934 identifies
one known rune/gem. Quest socketing is capped at one for these qualities (local
D2MOO SUnitNpc.cpp:2286). Native socket-roll items such as Tomb Reaver/Crown of Ages,
generic Jewel, blank/None and multiple-filler descriptions do not inherit a count.
Explicit conflicting counts are retained and rejected. Base upgrade and ethereal
facets remain independent unknowns. Source/definition generation is recorded.

Six scoped cached observations in the mercenary batch gain the count: Vampire Gaze
2, Shaftstop 2, Stealskull 1, Crown of Thieves 1. Across the full cache, named
structurally ready observations increase from 611 to 616 (7,089 scoped unchanged).
Readiness is not an exact modifier match or a three-seller cohort; no missing tier
was assigned from this change. Existing caches still lack other required facets.

Red/green regressions cover explicit proof, native sockets, ambiguous payloads and
contradictions. Full suite: 2,697 passed, 3 skipped in 94.81s; Ruff/diff checks pass.
Offline import, runewords, watchlist, bases and index rebuilt. All 18 saved reports
and prices are unchanged; selected-generation replay matches staged assessment.
Published `fd8f967470aec9ebf0ee4de9cc8a8f1528bafdc78234ffffd1664b4adfe57ff3`.
Tier/base/unified matrix and market readiness audits refreshed. No live requests.
Restart the Alt+D worker for the Python normalization change.

Next: continue source-backed rule/tier review with exact variants; missing seller
facets cannot be filled by assuming an unsocketed/non-ethereal default. The named
policy and all-family/stat coverage gates remain incomplete.

## Fixed native named sockets — 2026-09-25

Prepared definitions now retain conservative native_socket_range data, calculated
from property func14 min/max or positive parameter, inventory dimensions, base
capacity and all three native item-level brackets. Only the same count across every
bracket and same-name definition establishes a fixed listing count. Variable,
missing or unsupported encodings stay unknown. This uses the pinned local
ItemMods.cpp PropertyFunc14 and Items.cpp ITEMS_GetMaxSockets mechanics.

Sixteen identities have fixed counts, including Moser's, Ali Baba, Hone Sundan,
Witchwild, Bonehew, selected Griswold/Immortal King pieces and Spike Thorn. Market
normalization records definition-generation provenance, preserves omitted socket
contents as unknown, and rejects contradictory explicit counts. No empty-socket,
ethereal or upgrade defaults were added. Cached scoped count recovery: 309 rows
(Bonehew267, Ali Baba16, IK Stone Crusher18, IK Will8). Named structural readiness
remains616/7,089: other facets are still missing, so no new price is asserted.

Red/green tests cover parameter clamping, variable rolls, item-level ambiguity,
missing tables, definition-backed counts, unknown contents and explicit conflicts.
Full suite: 2,700 passed, 3 skipped in92.26s; Ruff/diff checks pass. Rebuilt definitions,
metadata, facts, recommendations, profiles, offline market and downstream data/index.
All18 saved reports/prices unchanged; staged and published assessments agree.
Published `0b0b4209ca4e5f1c1398d1f1c54b6a4cb085f94712cd7e6066beeea80e010c86`.
Updated replay ledger and guide/tier/base/unified coverage audits. No live requests.
Restart Alt+D for the Python change. Remaining work includes reviewed base-template
membership, guide-use/stat coverage and472 named identity tier policies.

## Runtime-equivalent base profile routing — 2026-09-25

The base matrix now reuses CandidateIndex and the typed predicate evaluator with
partial catalog facts instead of expanding type ancestry and ignoring must guards.
It records each assignment's exact profile fingerprint, source and guard trace.
A proven-false guard excludes an assignment; unknown rolls, ethereal/sockets,
identification and loadout remain unknown. No synthetic stat zero or current-item
fit is inferred. The unified matrix retains these traces and a separate reviewed
policy_routing dimension; desirability and prices remain pending.

Across 1,569 base-quality rows, broad profile candidates shrink from114 rows to6:
618 selector assignments contain600 proven-false guards and18 unknown candidates.
These are build-role-profile assignments only. Separate recipe mechanics and
base-use policy coverage are not removed or counted as failed by this result.
This makes the existing profile denominator honest; it does not fill every base's
reviewed usefulness/template gap.

Red/green tests reproduce the ancestor-selector mismatch and base-code pruning,
while retaining unknown modifier/ethereal candidates. Sixteen affected matrix,
recipe and link tests pass; Ruff/diff checks pass. Two corpus base-matrix builds
are byte-identical, and all assignment traces survive the unified matrix join.
Maintenance-only: runtime generation and saved-item behavior are unchanged.
Next review actual base-use policy assignments alongside these role profiles;
do not mistake the six candidate rows for all base assessment coverage.

## Base perfection evidence gates — 2026-09-25

The base-use audit found two false positives: perfect preferred base could be set
before checking capture completeness/identification, and roll strengths read raw
stats without the shared conflict check. Perfect status now requires complete,
identified capture. Superior ED/defense/AR claims additionally require superior
quality, and all roll reads respect typed native-stat conflict state. Independent
valid strengths remain available; conflicts do not turn the whole item worthless.

Red/green regressions reproduce incomplete/unidentified captures, normal quality
with superior-looking values and duplicate native damage/AR stats in both mercenary
and Grief paths. Full suite: 2,703 passed, 3 skipped in88.71s; Ruff/diff checks pass.
All18 published saved reports, prices and assessments are unchanged. No data
publication needed; restart the worker for the Python fix.

A separate read-only catalog audit of the actual base-use evaluator found438 routes
across183 base-quality rows (61 base identities). With item flags, sockets and rolls
unknown, all438 remain unverified and none claims perfection. This is separate from
the build-role profile matrix's six remaining candidate rows. The audit does not
prove full desirability coverage or price coverage. Next fold these actual base-use
routes into the matrix with source/version evidence and explicit remaining gates.

## Base-use routes integrated into coverage — 2026-09-25

The base matrix now invokes the existing base-use evaluator with shared partial
catalog facts, in addition to auditing build-role profiles. It retains runeword,
beneficiary, source locators, preparation state, strengths, missing requirements
and alternatives. The unified matrix preserves the complete routes. A separate
base_use_routing dimension distinguishes a performed audit from an omitted one;
desirability, actual item fit and market evidence remain separate pending dimensions.
Source manifests now include runtime base-use/preparation code and item metadata.

Corpus: 438 base-use routes across 183 base-quality rows, alongside 618 build-role
selector assignments. All 438 remain unverified with unknown item/socket evidence;
none claims a perfect base. Two complete base builds are byte-identical and all
routes survive the unified join. Nineteen affected tests pass after red/green
integration and omitted-audit cases; Ruff/diff checks pass. Maintenance-only change:
no runtime publication or additional worker restart is required.

Next extend actual reviewed base-use coverage from cached guides, beginning with
caster sword bases currently absent from the Spirit player-quality branches.
Preserve class, progression, ethereal durability and socket-preparation distinctions;
existing route counts do not establish complete all-base usefulness or prices.

## Spirit caster sword bases — 2026-09-25

Added reviewed caster-use routing for Crystal Sword, Broad Sword and Long Sword.
The utility KB explicitly recommends Crystal Sword for Spirit; the other two remain
legal alternatives, not promoted guide recommendations. All use existing socket
preparation, quality and captured-fact gates. Casting gets no superior physical-damage
premium or mercenary ethereal preference. Ethereal melee durability and unknown
ethereal status remain explicit; wearer/setup verification prevents perfect claims.
Source: appraisal-utility.json, Crystal Sword/sockets_by_runeword/Spirit plus native
runes/Spirit;weapons/{crs,bsd,lsd} legality edges. No new prices or build votes.

Red/green regression covers three bases, known/unknown ethereal state, unsocketed
preparation, wrong sockets and magic exclusion. All 18 saved published reports and
price estimates are unchanged. Evidence: tmp/spirit-sword-published.json;
full suite log: tmp/spirit-sword-full-tests.log. Restart Alt+D for Python changes.

## Call to Arms prebuff bases — 2026-09-25

Added reviewed prebuff routing for Crystal Sword, Flail and War Scepter using
appraisal-utility.json recommendation locators `<base>/sockets_by_runeword/Call to Arms`.
Native recipe edges gate legality. Prebuff skill utility does not inherit physical
ED/AR premiums or a mercenary ethereal preference. Ethereal melee durability remains
explicit; War Scepter staffmods and intended wearer/setup still need verification.
No named-tier, build-count or numerical-price changes. All use existing socket
preparation, including impossible high-ilvl superior Crystal Sword and low-ilvl
five-socket targets. Red/green tests cover these boundaries and filled sockets.
24 affected base/preparation tests and Ruff pass. Saved replay evidence:
`tmp/cta-base-published.json`; refreshed matrix: `tmp/cta-base-matrix.json`.
Restart Alt+D for this Python change. Broader template, annotation and price coverage
remains pending; these routes are not coverage closure.

## Shared caster/prebuff templates — 2026-09-25

Replaced growing Spirit-sword and Call to Arms branches with one evaluator in
caster_base_templates.py. Two versioned immutable configurations explicitly assign
six recipe/base pairs, source locators, role-specific advice and a War Scepter
staffmod exception. Compilation rejects overlapping memberships, missing provenance
and exceptions outside membership. Native recipe legality remains independently
gated, and all six assignments are tested against the prepared native recipe index.
Recommendations still determine preference separately; no additional build votes,
prices or generalized type-wide demand were introduced.

Red/green configuration validation plus existing behavior/preparation tests: 26 pass.
All 18 saved reports/prices and all 1,569 base-quality audit rows are unchanged.
Maintenance source hashes now include the template module, so edits invalidate the
base matrix. Refreshed unified matrix; evidence tmp/base-templates-{published,matrix,coverage}.json.
Ruff checks pass. Python-only refactor: no new runtime data generation; restart the
worker when adopting code changes. Remaining family templates and stat annotations
are not complete. Next scheduled tail batch should address a specialist/leveling
use from the unresolved queue, rather than adding another high-demand weapon slice.

## Tail batch: mercenary Crushing Blow leveling — 2026-09-25

Reviewed existing source appraisal-leveling-candidates-2026-09-23.json,
/generic_patterns/6 (17:42): explicitly includes Act 2 mercenary boss use. The
previous generic runtime policy emitted player use only and globally rejected
ethereal items. Added a separate conditional mercenary pattern for unique/set
polearms and spears with positive known Crushing Blow. Named definition validation
remains enforced by assess_leveling; conflicting stats, unidentified items and
impossible ethereal sets are excluded. No imaginary magic/rare Crushing Blow
polearm affixes were added. Damage, speed, survival and wearer requirements remain
conditional, with no price or named-tier inference.

Moved ethereal gates to side-specific pattern applicability; socket/player patterns
retain non-ethereal gating. Source deduplication includes beneficiary so player use
cannot erase mercenary use. Maintenance policy links preserve each side's guards.
Red/green Hone Sundan cases cover ethereal true/false/unknown, unidentified/conflicting
stats and wrong identity/base. 271 policy/link tests and 121 report/link tests pass;
Ruff passes. All 18 saved reports/prices unchanged in tmp/merc-leveling-published.json.
Unified coverage refreshed in tmp/merc-leveling-coverage.json. Python-only change;
restart Alt+D. The source fingerprint remains unchanged; no runtime data publication
or live collection required. This is the scheduled tail batch after the Spirit/CTA
base batches; remaining family, stat annotation, named-tier and market gaps persist.

Next resume a demand-led reusable family/configuration from the current coverage
queue, retaining GUIDE_FIRST separate usefulness/price dimensions and explicit
unknown facts. Do not count this conditional rule as complete unique/set coverage.

## Heart of the Oak caster base — 2026-09-25

Added Flail to the shared caster templates for Heart of the Oak, using the cached
explicit utility recommendation. Native recipe legality remains separate; no sword
compatibility or all-mace preference is inferred. The template preserves setup and
wearer requirements, separates physical damage from caster utility, and describes
Oak Sage/Raven charge use. Ethereal is not assigned a price premium: repeated charge
use favors non-ethereal, because ethereal equipment cannot be repaired/recharged.
Evidence: native runes Heart of the Oak charged properties, cubemain/139 `weap,noe`,
and D2MOO ITEMS_IsRepairable excluding ethereal before checking charged skills.

Red/green regression covers ethereal true/false/unknown, incompatible sword, and
high-ilvl superior versus normal Flail socket preparation. The former cannot reach
four sockets; the latter retains the cube's 1/6 chance. 25 focused tests and Ruff
pass. Full suite evidence: tmp/hoto-base-full-tests.log. Replay evidence:
tmp/hoto-base-published.json. Python-only change; restart Alt+D. No price/tier or
build-count evidence was added. All-family completion remains pending.

## Progression armor/shield/helm bases — 2026-09-25

Added four reviewed player-family configurations with eleven explicit assignments:
Stealth (Quilted, Leather, Hard Leather, Studded Leather), Smoke (Mage Plate,
Studded Leather), Rhyme (Bone Shield, Targe, Preserved Head), Lore (Cap, Diadem).
Each links the cached utility `<base>/sockets_by_runeword/<word>` recommendation;
native legality and existing socket preparation remain independent. Membership
validation rejects overlaps and orphan exceptions. All assigned recommendations
are tested against the prepared catalog. This does not add build votes or prices.

Rhyme preserves Paladin inherent-resistance and Necromancer staffmod checks. Lore
Diadem explicitly requires level 64 (native armor levelreq), avoiding an early-use
claim. Wearer requirements remain unverified; non-ethereal is preferred for player
repairability. No superior-defense premium or perfect-base claim is inferred.

Red/green behavior tests cover all eleven assignments, ethereal durability,
quality exclusion, unknown setup, and superior versus normal Mage Plate two-socket
preparation. Native Studded Leather supports two sockets (do not confuse its cap
with Mage Plate). 37 base/preparation tests passed, followed by 13 progression tests
including membership validation. Ruff passes. Replay and audit evidence:
tmp/progression-bases-{published,matrix}.json. The audit hashes the new module.
Python-only change; restart Alt+D. Remaining reviewed families, stat annotations,
named tiers and exact-market coverage are still incomplete.

## Specialist staffmod bases — 2026-09-25

Scheduled tail batch: added Leaf Short Staff, Memory Battle Staff and White Bone
Wand to the shared caster templates using existing explicit utility recommendation
locators. Native recipe legality remains separate. Each requires review of the
intended skill/staffmod setup and wearer requirements, without inventing skill
minima, physical-damage premiums or perfect-base claims. Leaf/Memory state the
two-handed weapon/shield tradeoff; White retains one-handed use and Necromancer
skill qualification. No market or build-count evidence was added.

Red/green tests verify ready items, quality exclusion and normalized low-quality
bases. All three can reach their target socket count after normalization; native
Battle Staff caps are 4/4/4, so do not assume a three-socket low-ilvl cap. Regenerated
staffmods and other properties are explicitly not inherited. The maintenance source
manifest now hashes mechanics/low_quality.py as a base-use dependency.
39 base/template/preparation tests and Ruff pass. Replay/audit evidence:
tmp/staffmod-bases-{published,matrix}.json. Python-only change; restart Alt+D.
Full objective remains incomplete: known family/configuration, annotations, named
tiers and exact-price gaps still require review. Resume demand-led batches after
this specialist batch; no live collection is required by these changes.

## Treachery Mage Plate: separate wearers — 2026-09-25

Added Mage Plate Treachery base assessment with independent player and mercenary
uses. Evidence is the explicit Character / Mercenary recommendation strings in
appraisal-utility.json Mage Plate/sockets_by_runeword/Treachery, not aggregate
per-base build lists. Player repairs favor non-ethereal; mercenary use prefers
ethereal. Missing ethereal status stays unknown. Both uses require actual defense
and wearer requirements to be checked; superior defense alone cannot establish
perfect suitability or a trade premium. Native Treachery gethit-skill Fade confirms
activation-dependent survival, kept in the tradeoff instead of assuming active Fade.

Red/green role tests cover all ethereal states and filled-socket clearing. Forty
base/template/preparation tests and Ruff pass. Evidence:
tmp/treachery-base-{published,matrix}.json. Python-only change; restart Alt+D.
No prices, tiers or build counts were added. Broad family/annotation/named-tier/
market coverage remains incomplete; next batch should return to reviewed affixed
item configurations, not infer completion from base-route growth.

## Amazon glove stat priorities — 2026-09-25

Reviewed the exact cached glove slots for Lightning Fury Standard/Magic Find/Ubers
and Lightning Strike Standard/boss swap. Added five stat-priority configurations
against unchanged source hashes and full role fingerprints. Required Javelin skills
and IAS are desirable only after the whole combination passes; the source-listed
secondary attributes/resists/MF/mana steal are supporting at positive observed rolls.
Planner maxima remain targets, not required minima or perfect-roll annotations.
The general breakpoint/loadout reminder is advisory only for present item markers;
overall build fit remains conditional. The boss-swap Arachnid Mesh dependency stays
mandatory and cannot be waived by the advisory-condition review.

Red/green tests cover rare 2/20, magic 3/20, incomplete/missing pair, wrong quality,
ethereal state and unmet boss companion. Eleven targeted stat/bundle tests pass;
Ruff passes. Prepared stat configurations increase from 16 to 21 without adding
role profiles (297 unchanged), named tiers or prices. Sources: wp-a-variants/
lightning-fury-amazon-guide.json /variants/{1,2,3}/player/Gloves and
lightning-strike-amazon.json /variants/1/player/Gloves. Full release evidence:
tmp/glove-stats-full-tests.log, tmp/glove-stats-{staged,published}.json.

## Crafted-glove stat combinations — 2026-09-25

Added three explicit stat reviews for Double Throw Standard Hit Power gloves,
Smite High Investment Blood gloves and Dragon Talon Budget Blood gloves. Exact
cached source slots and existing role fingerprints are retained. IAS/Knockback,
IAS/Crushing Blow, and Martial Arts/IAS/Crushing Blow/life-steal combinations stay
independent: missing or unknown mandatory stats block that configuration's markers.
The source-listed optional attributes, life and resistances are supporting at
positive observed rolls, not universal required maxima. Smite planner life/mana
steal is intentionally left unannotated; its utility to that role is not established
by this review. General loadout reminders are advisory only for item-stat markers;
no full-fit, crafting-recipe identity, or numerical price is inferred.

Red/green tests cover all three combinations, absent/unknown members, wrong quality
and ethereal exclusion. 263 role/stat/bundle/presentation tests pass; Ruff passes.
Prepared stat configurations: 24 (was 21); role profiles remain 297. Sources:
wp-a-variants/double-throw-barbarian-guide.json /variants/1/player/Gloves,
smite-paladin.json /variants/2/player/Gloves, dragon-talon-assassin.json
/variants/0/player/Gloves. Evidence tmp/crafted-gloves-{staged,published,publication}.json.
This is an offline reviewed-data change; existing current published workers adopt
it at request boundaries. Remaining all-family, named-tier and market requirements
are not complete.

## Circlet stat-use configurations — 2026-09-25

Added six source-reviewed stat configurations: Poison Nova Standard, FoH Tri-Brid,
Abyss Standard, Berserk Max Mobility rare circlets; Enchant Standard and Max Enchant
magic circlets. Exact cached Helmet slots and complete existing-role fingerprints
are preserved. Matching class skills/FCR form mandatory rare combinations; Enchant
requires its Fire skill tree. Source-reviewed life/dexterity/movement preferences
are supporting at positive observed rolls, not required maxima. Max Enchant does
not inherit Standard's movement-speed annotation. Socket/filler checks remain
conditions on overall fit, advisory only for these present item-stat markers.
Known non-ethereal status additionally gates player-helmet annotations. No socket
completion, ethereal exception, perfect-roll or price claim follows from markers.

Red/green tests cover all six role/quality/skill combinations, missing/unknown
mandatory skills, lower FCR, wrong quality and ethereal true/unknown. Fifteen focused
stat/bundle tests pass; Ruff passes. Prepared configurations: 30, roles: 297.
Sources are unchanged wp-a-variants Helmet locators in the six profiles; no raw
research repeated and no market collection. Evidence tmp/circlet-stats-*.json.
Remaining all-family configuration, named-tier and exact-market gaps stay pending.

## Rare boot stat configurations — 2026-09-25

Added ten exact-source boot stat reviews: Blizzard Standard, Lightning Sentry
Standard, Fire Warlock Standard/MF, Lightning Fury Ubers, Lightning Strike Ubers,
Fissure Ubers, Lightning Sorceress Ubers, Gold Find Budget and Nova Starter.
Required combinations remain distinct: movement plus fire/lightning/cold resistance,
movement/fire resistance/gold find, or Nova's movement/fire resistance pair. Positive
source-listed secondary recovery, dexterity, MF or poison-length reduction is
supporting; no universal tri-resist rule, minimum maximum-roll target or price is
introduced. Known non-ethereal status and entire role predicate remain mandatory.
Full-loadout comparison is advisory only for item-stat markers, not overall fit.
All source Boots locators were inspected; existing role fingerprints/hashes retained.

Red/green tests cover every configuration, zero and unknown mandatory modifiers,
quality/ethereal exclusions and independent roll-quality state. 260 affected
role/stat/bundle/presentation tests pass; Ruff passes. Prepared stat configurations
increase from 30 to 40, role profiles remain 297. Evidence tmp/boot-stats-*.json.
This is an offline prepared-data update. Overall family, named-tier, leveling and
exact-market completion remains pending under GUIDE_FIRST.

## Specialist IAS/resistance jewel stat reviews — 2026-09-25

Scheduled specialist batch: seven source-specific jewel configurations added for
Andariel's Visage mercenary fire-resistance setups (Lightning Standard/MF, Blizzard
Standard/Set, Hammer Standard/Ubers) and Guillaume's Face player lightning-resistance
setup (Hammer Ubers). Exact cached helmet payload locators were inspected. Both
modifiers are desirable only after the whole magic-jewel predicate and typed wearer/
recipient dependency pass. Fixed 15 IAS remains exact, not >=15 without an upper
bound. Resistance maximum stays a preference; no perfect-roll or price inference.

Socket availability and full breakpoint/resistance checks remain overall role
conditions, advisory only for recognizing useful jewel stats. Thus highlights do
not say ready-to-socket. Unknown/wrong recipient or wrong wearer prevents markers.
Tests also cover incomplete modifier capture, impossible 16 IAS and wrong quality.
Ten focused stat/bundle tests and Ruff pass. Prepared configurations: 47 (was 40),
297 role profiles unchanged. Full regression/replay/publication evidence:
tmp/jewel-stats-{full-tests.log,staged.json,published.json,publication.json}.
This is an offline prepared-data update; no live research or new prices. The full
GUIDE_FIRST denominator, named tiers and remaining configurations are incomplete.

## Sorceress amulet stat reviews — 2026-09-25

Added seven configurations for Enchant Budget/Max Enchant magic amulets and Nova
Standard/MF/Hydra plus Enchant Standard/MF crafted amulets. Exact cached Amulet slots
were inspected; existing source hashes and full-role fingerprints are preserved.
Matching Fire-tree versus Sorceress-class skills and variant-specific 10/15 FCR
remain mandatory combinations. Source-specific life/mana/regeneration/MF/strength
preferences are supporting at positive observed rolls. The Enchant all-resistance
preference stays grouped: one resistance does not satisfy it. Planner maxima are
targets, not generic required minima. Prebuff and loadout reminders are advisory
only for present item markers; overall fit remains conditional. No price, recipe
identity or roll-quality inference added.

Red/green tests cover all seven thresholds/qualities/skill identities, missing or
unknown skills, insufficient FCR and partial/full all-resistance groups. Sixteen
focused stat/bundle tests and Ruff pass. Prepared configurations: 54, roles: 297.
The pinned-bundle test now sees five magic amulet configurations, preserving
publication isolation and legacy behavior. Evidence tmp/amulet-stats-*.json.
All-item/price/named-tier and remaining reviewed-stat coverage remains incomplete.

## Class-specific magic amulet stats — 2026-09-25

Added six exact-source configurations: Lightning Sentry and Wake of Fire Cunning
Whale/Apprentice amulets; Poison Nova Starter/Budget Venomous amulets. Cached guide
slot identities inspected; existing native-affix predicates and full role/source
fingerprints preserved. Typed player class, skill tree, quality and suffix remain
mandatory; no cross-class or rare-item inheritance. Whale's 81-life lower bound
stays distinct from its 100-life preference. All highlighted stats participate in
the required combination; overall loadout fit remains conditional.

Red/green tests cover all six, wrong/unknown class, insufficient/missing/unknown
modifiers, rarity and ethereal exclusion. Five focused config/bundle tests and
Ruff pass. Prepared configurations: 60; role profiles unchanged at 297. Compiler
and pinned-bundle coverage assertions updated to 16 total amulet configurations
and 11 magic amulet candidates; behavioral and isolation assertions retained.
Evidence tmp/class-amulet-stats-*.json. No price or named-tier change. Teleport
charge amulets remain pending a separate charge-parameter annotation design.

## Specialist dynamic charge-stat targets — 2026-09-25

Added charge:<skill-id> annotation targets, resolved to actual native 204:<parameter>
rows by the existing charged-skill validator. Valid positive-charge rows for the
requested skill are selected across spell levels; exhausted, conflicting, malformed
or unrelated skill rows are never marked even if another row establishes availability.
Ordinary scalar target behavior and prior prepared schemas remain compatible.
Targets serialize through the existing validated configuration bundle. Shared
terminal/OSD stat formatting already accepts the resolved native keys.

Added two reviewed Teleport amulet configurations (Berserk and Poison Nova), using
exact cached gear-note alternatives. Typed class and available-charge dependencies
remain mandatory. Equipment/progression alternatives remain conditions on overall
fit, advisory only for recognizing an available Teleport property; this does not
recommend replacing Enigma. No numerical price or perfect-charge-roll inference.
Prepared configurations: 62; existing role profiles unchanged. Red/green tests cover
mixed charge levels, exhausted/duplicate/wrong-skill rows, malformed selectors,
bundle roundtrip, class/quality scope and shared rendered markers. Eighteen focused
stat/bundle/compiler tests and Ruff pass. Full evidence tmp/charge-stats-*.json/log.
Python change requires Alt+D restart. Full all-item/named-tier/market coverage remains
incomplete; this is the scheduled specialist batch after the two amulet batches.

## RCA: life bonuses incorrectly keyed as current HP — 2026-09-25

Belt-stat review found ten existing roles using native 6:0 (hitpoints) for item
+Life; native itemstatcost/decoder identifies 7:0 (maxhp) as the Life bonus. Six
belt roles (FoH/Holy Bolt/Fury/Poison starters, Summoner/Smite crafted starters) and
four small-charm roles (Lightning Ubers, Blizzard Standard life/all-res and life/cold,
Hammer Ubers) were affected. Exact source locators all describe +Life, not current HP.
Must predicates, preference predicates and important_stats now consistently use7:0.
Source values/thresholds, quality scopes and dependencies are unchanged.

Root cause: handwritten role JSON used the wrong adjacent native stat; handcrafted
role tests repeated it instead of crossing the decoder/normalizer boundary. Updated
those fixtures and added actual decode_stats→normalize→role regressions (fixed-point
life raw values). Nine cases failed before the fix; the initial24 affected tests
passed after it. Added coverage for all four small-charm roles and a negative check
that current HP cannot satisfy the item-life predicate. Full evidence:
tmp/life-stat-{red.log,full-tests.log,staged.json,published.json,publication.json}.
The intended belt annotation expansion is deferred until this correctness fix is
validated/published. No new prices or stat-review count claimed; configurations62,
roles297. This fixes matching prerequisites, not missing source or market coverage.

## Magic/rare belt stat annotations — 2026-09-25

Added eight reviewed configurations: Hammer/Blizzard/Wake Starter recovery+fire
resistance belts; FoH/Holy Bolt Starter life+cold resistance; Fury/Poison Starter
life+fire resistance; Gold Find Budget recovery+cold/lightning resistance+gold.
Exact source Belt slots inspected. Whole quality-specific combinations remain
mandatory; player-equipment annotations additionally require known non-ethereal
state. Corrected Life7:0 is used, never currentHP6:0. Source roll targets remain
preferences and no lower observed roll is falsely marked perfect.

Potion capacity, equipment, remaining survival/breakpoint and mercenary-kill setup
checks remain conditions on overall fit, advisory only for item-stat recognition.
No price or full-loadout claim follows from markers. Red/green tests cover all eight
combinations, missing/unknown modifiers, crafted exclusion, ethereal true/unknown,
and current-HP negative cases. Seventeen focused tests and Ruff pass. Prepared
configurations:70; roles297 unchanged. Evidence tmp/belt-stats-*.json. Crafted belt
annotations remain separate work; preserve the Smite Life Tap qualification.

## Verified current coverage

| Requirement | Current evidence | Remaining work |
|---|---|---|
| Build-aware routing | Eight family branches in `registry.py`; 297 reviewed profiles compiled from per-build rules | Remaining source-specific roles, variants and dependencies |
| Every source occurrence retained | Fresh occurrence audit: 62,891 occurrences, 34 builds, 591 build/variant pairs; 49,780 discovery-only, 3,929 identity-review and 9,182 rule-review records | Resolve required identities and semantic rule dispositions; direct source links are not proof of complete rules |
| Source-to-rule traceability | 857 occurrences have related rules; 273 have direct source rules | Review duplicates, alternatives, planner context and source-specific predicates |
| All unique/set tiers | 565 identities, 93 reviewed policies, 472 pending, zero invalid policy sources; 141 pending identities have build/leveling evidence | Source-backed defaults and conditional roll/ethereal/socket overrides; explicit reviewed exclusions where appropriate |
| Exact offline comparisons | Base, affixed, named and runeword policies; scoped seller/date/variant gates; typed current/prepared results | Remaining contribution mechanics and reviewed comparison bands; sufficient actual eligible observations |
| Saved-item behavior | Eighteen saved-item replays; Dread Edge now forms a current and upgrade contract | More representative item families and actual positive scoped cohorts; a contract does not itself establish price |

The named audit has two research-only records and 470 without a WP-I research
record. This does not mean those items lack all KB evidence. Disabled drop flags
also do not automatically establish an exclusion or a trash tier.

## Evidence that limits numerical coverage

The current all-market audit (as of 2026-09-25) reports:

| Policy | Scoped observations | Structurally ready observations |
|---|---:|---:|
| Affixed | 8,728 | 558 |
| Base | 3,209 | 20 |
| Named | 7,089 | 611 |
| Runeword | 4,391 | 130 |

These are observations, not independent sellers, matched cohorts or priced items.
Explicit collection days restored from 135 legacy cache wrappers on 2026-09-25;
9,405 observations (4,512 scoped) now retain dated file/hash provenance. No file
timestamp or listing-update date supplied freshness. Structural readiness does not
validate every modifier or meet the three-seller
gate. Dates, base identity, ethereal state, sockets and contents remain material
gaps. The approved six-item mercenary collection is complete; repeating the same
pages does not establish omitted facets. The named-priority batch resumed with
updated client access: 11 successful pages, 550 listings, 186 scoped observations.
The original 12-request cap includes the prior HTTP403. Five items have two pages;
Crack of the Heavens has one. Fresh original Sunder cohorts support exact penalty
variants Flame Rift -72/-75 and Crack of the Heavens -71 on 2026-09-25; other rolls
still require independent matching sellers and dispersion gates. All four newly
sampled armor/helmet identities lack explicit socket state, so none is structurally
ready for exact pricing. See appraisal-named-priority-market-batch.json.

## Next implementation/research priorities

1. Review the 141 pending named identities with actual build/leveling evidence.
   The source-ranked queue begins with Vampire Gaze, Rockstopper, Stealskull,
   Kira's Guardian, Rockfleece, Flame Rift and Undead Crown. Retain conditional
   utility even when tier evidence is insufficient. Cached listings for the first
   four currently lack necessary variant facets; inspect existing raw evidence
   before considering additional explicitly authorized collection.
2. Resolve required build-occurrence identities and executable rules across the
   full source census. Preserve alternatives, mercenaries and leveling. Do not
   count name overlap or a generic planner item as a reviewed role.
3. Continue family comparison gaps: crafted/socket elemental contributions,
   integer per-level listing conventions, ambiguous trigger identities and
   reviewed secondary-roll bands. Do not replace them with generic tolerances.
4. Reconcile architecture migration and compatibility boundaries against A1–A11
   in ARCHITECTURE.md before final rollout. This audit does not claim those gates
   complete merely because tests pass.

## Reproduce the coverage evidence

Run offline from the repository root:

```sh
uv run --offline python -m pricing.knowledge.assessment.coverage
uv run --offline python -m pricing.knowledge.assessment.maintenance.coverage --as-of 2026-09-25 > pricing/data/appraisal-tier-coverage.json
uv run --offline python -m pricing.knowledge.assessment.maintenance.inventory > pricing/data/appraisal-occurrence-coverage.json
uv run --offline python -m pricing.knowledge.assessment.maintenance.market_readiness --all-items --as-of 2026-09-25 > pricing/data/appraisal-all-market-readiness.json
```

The first command now reports named tier completeness separately from profile and
family counts. The other outputs retain the per-identity/per-occurrence details.
Do not declare the goal complete until the full plan's coverage and validation
requirements have current evidence.

### Belt publication verification — 2026-09-25

Revalidated the selected generation against `tmp/belt-stats-publication.json`:
`ce01ee72694fac2d681150aa1a097cdbb996d04bc91a76fcce38fc4d9b76ef33`.
All 18 saved staged and published reports and price results match the preceding
Life-stat generation. Re-ran the belt stat-priority and stat-bundle tests: 10 passed.
Copied the completed base matrix and regenerated the unified coverage matrix after
source-fingerprint validation (`tmp/belt-stats-coverage.json`). The use/quality
stat-desirability dimension now has 79 reviewed and 289 pending rows; 70 reviewed
configurations do not establish full report, market or family coverage.

Next: review crafted caster belt combinations using exact cached slot evidence;
keep Smite Life Tap dependencies explicit. Follow GUIDE_FIRST's specialist/leveling
tail scheduling and preserve separate coverage dimensions. No new market collection
or runtime code change was needed for this verification.

## Crafted caster belt stat annotations — 2026-09-25

Reviewed exact cached belt slots for Abyss, Echoing, Fire Warlock, Fissure,
Lightning Sorceress, Nova and Summoner starter configurations. Added seven
reviewed stat configurations, bringing the prepared total to 77 (297 roles).
Whole modifier combinations remain mandatory. Echoing/Fire resistance alternatives
are evaluated within their own configurations, without requiring every resistance.
Five explicit loadout FCR dependencies remain mandatory; missing/below-threshold
context cannot activate annotations. Known non-ethereal crafted equipment is
required. Source roll targets remain preferences, not perfect-roll claims.

Red: seven missing-configuration failures. Green: 268 affected role/stat/compiler/
presentation tests passed. Tests cover required-stat near misses, incomplete
captures, quality/ethereal exclusions, alternative resistance branches, FCR boundary
and unknown context, and Life7 versus currentHP6. Ruff and diff checks pass.
All 18 staged/published saved reports and price results are unchanged. No saved
crafted-belt capture exists; targeted fact-level tests cover the new configurations.

Published generation `5550361cf1bf7c54f6135c9e09ca7a8ca257ef17e8b85bd1fbccd277771b1ed6`. Refreshed guide inventory, base matrix and
unified coverage; stat desirability now records 86 reviewed and
282 pending use/quality rows. Evidence: `tmp/crafted-belt-stats-*`.
This is data-only; no additional worker restart is required.

Next is the GUIDE_FIRST specialist/leveling tail after the two belt batches:
review Smite Blood-belt sustain semantics (Life Leech is not Life Tap), preserving
its Ubers dependencies before enabling markers. Then resume unresolved family and
named-tier queues. Full coverage and all-item pricing remain incomplete; annotations
do not supply missing market evidence.

## Specialist tail: Smite Blood-belt review — 2026-09-25

Reviewed the cached Smite Starter purpose, Belt slot and variant quotes. Removed
Life Leech from important stats and better-roll preferences: the guide requires
Life Tap for sustain separately. Kept the complete cited crafted combination as
the candidate predicate; present leech is not promoted to a desirable modifier.
Added annotations for Open Wounds, recovery and Life, requiring known non-ethereal
crafted equipment. Overall role remains partial with Life Tap, CBF, Crushing Blow,
resistance, equipment and potion-capacity qualifications intact. Reviewing these
conditions as advisory for item-stat recognition does not satisfy the loadout.

Red regression reproduced the incorrect leech priority. Green: 262 affected tests;
Ruff and diff checks pass. Negative cases include missing/unknown required modifiers,
quality, ethereal, identification and currentHP6 versus Life7. Changing leech1→3
does not add a marker. All18 staged/published saved reports and price results remain
unchanged; the Smite belt itself is covered by domain tests, not a saved capture.
78 reviewed stat configurations;297 roles. Published `06fda35c6b7346894a0d4b842f949d551b00f357484b95ebc139c6e0cecf5a5d`.
Guide/base/unified maintenance refreshed: stat desirability 87 reviewed,
281 pending use/quality rows. Evidence `tmp/smite-belt-stats-*`.

This completes the scheduled specialist tail following the magic/rare and crafted
caster belt batches. Next demand-led batch: inspect the ten pending grand-charm
(`lcha`) configurations (life skillers, FHR skiller and starter skillers), preserving
exact class/tree identity and whole combinations. The25 small-charm configurations
are a subsequent family; do not pool incompatible survival/MF branches. Remaining
named tiers, source gaps and market evidence still prevent all-item completion.
Data-only publication; no new Python-worker restart required.

## Grand-charm stat configurations — 2026-09-25

Reviewed all ten existing Grand Charm role source slots: six Life skillers
(Blizzard/Fury/Hammer/Nova/Poison/Lightning), two FHR skillers (Hammer/Lightning),
and plain starter skillers (Poison/Lightning). Added exact skill-tree and suffix
annotations through the existing shared evaluator; source45-Life preferences are
not minimum requirements or perfect-roll claims. Plain starter roles do not inherit
Life/FHR priorities. Inventory allocation remains conditional on the full charm
setup, advisory only for recognizing this item's modifiers. Magic quality,
identification and known non-ethereal constraints remain active.

Red:10 missing-configuration failures. Green:271 affected tests; Ruff/diff checks
pass. Tests cover wrong skill tree, Life/FHR substitution, FHR11 versus12, current
HP versus Life, absent/unknown required modifiers and quality/ethereal/identification
exclusions. All18 staged/published saved reports and prices unchanged; no Grand
Charm saved capture is present, so new behavior is covered by targeted domain tests.
88 configurations,297 roles. Generation `c7ab0f1af827698659c4155dfcb634ea2ac9a827f7ab6cf3e90542b7ecf486f8` is selected. Guide inventory, base
matrix and unified coverage refreshed: 97 reviewed and 271
pending stat-desirability use/quality rows. Evidence `tmp/grand-charm-stats-*`.

Next: the25 small-charm configurations, reviewed in compatible combination groups
(life/resistance, MF/resistance, FHR/resistance and other source-specific branches).
After that second demand-led batch, schedule the GUIDE_FIRST specialist/leveling
tail. Named-tier closure and scoped market evidence remain independent unfinished
requirements. No additional Python-worker restart is needed for this data update.

## Small-charm combination annotations — 2026-09-25

Reviewed the25 existing Small Charm role slots, grouped into seven compatible
combinations: Life/all-resistance, Life/cold, MF/all-resistance, FHR/all-resistance,
lightning/MF, fire/MF and mana/MF. All four resistances are mandatory in all-resistance
configurations. Source counts remain inventory-allocation context; they do not
increase demand votes. Allocation conditions remain on overall fit, advisory only
for stat recognition. Known non-ethereal magic quality/identification is required.
Source maximum-roll targets are not annotation minima or perfect-roll claims.

Red: seven missing-configuration cases. Green:268 affected tests; Ruff/diff checks
pass. Tests cover every generated member, incomplete combinations, partial all-res,
wrong charm size/quality, ethereal/identification, Life versus currentHP, Mana versus
current mana and MF versus Gold Find. No pooled resistance or cross-family credit.
All18 staged/published saved reports and prices unchanged; these new Small Charm
combinations have domain tests, not saved capture fixtures. Prepared configurations
113; roles297. Generation `90cb517e7e4b4a258ebbe2b977a3029af6e1f71b07de5ac6eaaaba164b571c42` is selected.
Guide inventory/base/unified coverage refreshed: 122 reviewed and
246 pending stat-desirability use/quality rows. Evidence:
`tmp/small-charm-stats-*`. No new Python-worker restart required.

Next scheduled specialist tail: Life Tap charge wands, using existing dynamic
charge targets and exact skill/remaining-charge rules. Pending role IDs:
`smite-paladin-starter-charges-82`, `dragon-talon-assassin-budget-charges-82`,
`dream-paladin-ubers-charges-82`. Check exact source slot, recharge/ethereal caveats
and context before activating markers; a charged wand does not prove ongoing
sustain or complete Ubers fit. Full named-tier and market closure remain pending.

## Specialist tail: Life Tap charged wands — 2026-09-25

Reviewed exact Smite Starter, Dragon Talon Budget and Dream Ubers wand slots.
Added three dynamic charge:82 configurations using the existing resolver, preserving
magic/rare quality, player class and available-charge gates. Dream requires known
absence of both Last Wish and Dracul's Grasp; unknown companion context cannot
activate its marker. Corrected recharge wording to distinguish non-ethereal copies.
Ethereal copies retain usable remaining charges, with a finite-charge/no-repair
qualification. Charge presence does not prove the curse is applied or full Ubers
sustain. Equipment and remaining loadout conditions remain on overall partial fit,
advisory only for identifying the charge stat.

Red:3 missing-configuration failures. Green:271 affected tests; Ruff/diff checks
pass. Tests cover all three roles, magic/rare quality, empty/wrong-skill/malformed/
conflicting charges, wrong/unknown class, Dream companion presence/unknown state,
identification, wrong item type and terminal stat marker. All18 staged/published
saved reports and prices unchanged; new wand scenarios use domain/presentation
tests rather than saved captures.116 configurations,297 roles.
Generation `c8ad53accf57ab47e915b83840a9cec8ac1a12c6378c2235b7bdbadc016584bd` selected; guide/base/unified maintenance refreshed.
Stat-desirability use/quality rows: 128 reviewed,240 pending.
Evidence `tmp/life-tap-stats-*`; no Python-worker restart needed for this data update.

Next demand-led batches: review17 Teleport travel-staff configurations, then the
remaining9 Lower Resist wand configurations using exact source/loadout requirements.
Reuse charge targets; do not infer immunity breaks, applied curses or permanent
sustain from charges. Follow with another specialist/leveling tail. Named tiers,
full guide review and exact scoped market evidence remain incomplete.

## Teleport travel-staff annotations — 2026-09-25

Reviewed17 exact staff source slots across seven classes. Added dynamic charge:54
annotations with class, quality, identification and valid remaining-charge gates.
Converted explicit Berserk and Poison pre-Enigma/Bramble conditions into typed
absence-of-equipped-Enigma dependencies, alongside the existing Smite gate. Unknown
loadout cannot establish these alternatives; Bramble remains compatible. Other farm,
swap/inventory and equipment conditions remain on partial role fit, advisory only
for recognizing usable charges. Incidental planner resistances/charge counts were
not promoted to requirements. Recharge wording now distinguishes non-ethereal copies;
ethereal copies retain finite remaining travel utility, not rechargeability.

Red:17 missing-configuration failures. Green:285 affected tests; Ruff/diff checks
pass. Tests cover each role, magic/rare, unknown/wrong class, empty/malformed/wrong
skill/conflicting charges, ethereal finite use, wrong type, identification and
known/unknown Enigma alternatives. All18 staged/published reports and prices remain
unchanged; staff scenarios have domain tests, not saved capture fixtures.
133 stat configurations;297 roles. Generation `12f8623c8f58e59c61f61808d492af5951d5d3d9c69d80c139befcd4df70e2ef` selected.
Guide inventory/base/unified maintenance refreshed: 162 reviewed,
206 pending stat-desirability use/quality rows. Evidence:
`tmp/travel-staff-stats-*`. Data-only update; no new Python-worker restart required.

Next demand-led batch: the remaining9 Lower Resist wand configurations, retaining
class and exact gear/curse dependencies and not inferring immunity breaks from
charges. Then schedule a specialist/leveling tail. Full guide review, named tiers,
base desirability and exact market coverage remain independent unfinished gates.

## Lower Resist wand annotations — 2026-09-25

Reviewed nine exact cached wand slots. Added dynamic charge:91 configurations,
preserving class, valid remaining charges and the opposite Infinity dependencies:
Blizzard Starter requires known absence; Lightning Ubers requires known presence.
Unknown mercenary gear cannot establish either. Lightning Strike Ubers keeps its
manual-curse alternative even with Plague. Inventory/swap placement, equipment,
target effect and Uber Mephisto qualifications remain on partial role fit, advisory
only for recognizing usable charges. Recharge wording distinguishes non-ethereal
copies; ethereal charges provide finite utility. No immunity-break or applied-curse
claim follows from a marker.

Red:9 missing-configuration failures. Green:277 affected tests; Ruff/diff checks
pass. Tests cover all nine roles, magic/rare, charge state/skill/conflicts, class,
identification, ethereal finite utility and known/unknown/opposite Infinity gear.
All18 staged/published saved reports and price results unchanged; new wand scenarios
use domain tests, not saved captures.142 configurations;297 roles.
Generation `ddb0b28399f7535fe79f7276d22662bff2d266985e1ab094f203cd211e1aaf4a` selected. Guide inventory/base/unified audits refreshed:
180 reviewed,188 pending stat-desirability use/quality rows.
Evidence `tmp/lower-resist-stats-*`; no new Python-worker restart required.

Next scheduled specialist tail after the two charged-utility batches: review
`enchant-prebuff-orb-candidate`, preserving native staffmod versus affix skills and
prebuff-specific requirements. Then resume unreviewed circlet/claw/pelt/base-use
configurations. Full named tiers, guide review and exact scoped prices remain
independent unfinished requirements; configuration coverage is not market coverage.

## Specialist tail: Enchant prebuff orb — 2026-09-25

Reviewed the exact Max Enchant Weapon slot. Added one configuration requiring the
Fire skill-tree affix and native Enchant/Fire Mastery staffmods together. Class-wide
skills, another tree and oskill identities cannot substitute. Planner+3 maxima
remain preferences; lower positive values can establish the skill candidate.
FCR is not silently highlighted as necessary to prebuff. Socket/facet and equipment
checks remain on partial full-use fit, advisory only for skill recognition.
Ethereal state does not remove the captured prebuff skills or establish melee utility.

Red: missing configuration reproduced. Green:262 affected tests; Ruff/diff checks
pass (one test-comprehension lint fix). Tests cover each missing/unknown member,
wrong skill identities, conflicting native rows, magic-only applicability, item type,
identification, lower/max rolls and ethereal states. All18 staged/published saved
reports and prices unchanged. The saved orb captures remain regression controls;
this specific Enchant combination is tested at the domain boundary.
143 configurations;297 roles. Generation `e3d514ad573555bc7a508e731b733550d9a7c177ddc7875d8487b6f6db2d740d` selected.
Guide inventory/base/unified refreshed: 181 reviewed,187 pending
stat-desirability use/quality rows. Evidence `tmp/enchant-orb-stats-*`.
No new Python-worker restart required for this data-only change.

Next: source-specific trap-claw and Druid pelt skill combinations, preserving
quality, base, skill identity, socket and setup conditions. After two demand-led
batches return to specialist/leveling review. Named tiers, source completeness,
base desirability and exact scoped prices remain independent unfinished gates.

## Trap-claw skill annotations — 2026-09-25

Reviewed Wake of Fire and Lightning Sentry Standard Weapon slots. Added two
configurations requiring Traps plus the matching native trap staffmod. IAS, Weapon
Block and the source-specific Fire Blast/Death Sentry are supporting only after the
core pair matches. Verified native skill IDs against bundled metadata. Missing
supporting stats do not invalidate the core candidate. Planner+3/40IAS remain
targets, not annotation minima. Socket/payload, base-speed and remaining equipment
are still full-setup checks; no breakpoint, best-base or price claim follows.

Red:2 missing-configuration failures. Green:263 affected tests; Ruff/diff checks
pass. Tests cover exact tree/staffmod identities, cross-trap substitution, oskill/
class-skill substitution, missing/unknown core members, independent supporting
stats, quality/type/identification and conflicting capture rows. All18 staged and
published reports/prices unchanged, including existing claw captures. New complete
trap-pair combinations are covered by domain tests rather than saved captures.
145 configurations;297 roles. Generation `d4e81cc25b5715780ee865b352a0a4b4b4fca47618b3b123f74059c1f77676e1` selected.
Guide/base/unified maintenance refreshed: 183 reviewed,185
pending stat-desirability use/quality rows. Evidence `tmp/trap-claw-stats-*`.
No new Python-worker restart required for the data-only update.

Next demand-led batch: `fissure-standard-pelt` and `fissure-magic-find-pelt`; review
source-specific rare skill combinations and socket requirements. Then schedule a
specialist/leveling tail. Named tiers, complete source review, base desirability
and exact scoped market evidence remain independent unfinished gates.

## Fissure magic-pelt annotations — 2026-09-25

Reviewed exact Standard and Magic Find Helmet choices. Added two configurations
requiring Druid class, non-ethereal magic quality, +3 Elemental/+3 Fissure and the
existing verified two-socket Defender's Fire + Fire Rainbow Facet setup. Socket
dependencies were not waived for stat annotations: wrong elements, names-only,
parent-total substitution and missing Defender's Fire do not activate markers.
Standard Hurricane/Grizzly are supporting positive bonuses only; MF does not
inherit them. Equipment/preparation conditions remain on partial overall fit.
Earlier handoff wording describing these as rare was incorrect: both are magic.

Red:2 missing-configuration failures. Green:263 affected tests; Ruff/diff checks
pass. Tests cover core thresholds, absent/unknown skills, socket evidence, class,
quality, ethereal/identification and variant-specific supporting bonuses. All18
staged/published saved reports and prices unchanged. These pelt combinations use
domain fixtures, not captured live items.147 configurations;297 roles.
Generation `b88dcecefd3715b200bb45b17126c4af872f2043a17b30943ec1cc8df95ccdd1` selected. Guide/base/unified maintenance refreshed:
185 reviewed,183 pending stat-desirability use/quality rows.
Evidence `tmp/pelt-stats-*`; no new Python-worker restart required.

Next specialist/leveling tail: Double Throw starter magic Cruel throwing weapons
and crafted alternatives, preserving the documented attack/damage combination,
main-hand/off-hand contexts and ethereal/replenishment considerations. Do not infer
generic rare throwing-weapon prices. Remaining named tiers, guide completeness,
base desirability and exact scoped prices are separate unfinished requirements.

## Specialist tail: Double Throw starter weapons — 2026-09-25

Reviewed four exact main/off-hand source entries. Crafted Balanced Axe annotations
require the complete Barbarian skills/IAS/ED endpoints/leech/Life combination.
Cruel elite alternatives retain201..300ED on both endpoints and enumerated base
membership, with IAS supporting only. Source quality, Barbarian class, non-ethereal
state and no-cold-damage predicate remain mandatory; incomplete captures cannot
prove absence of cold. Full-gear corpse preservation, actual throwing damage,
breakpoints, equipment and quantity sustain remain conditions on partial overall
fit, advisory only for recognizing the captured modifiers. No generic rare-weapon
price or ethereal replenishment inference.

Red:4 missing-configuration failures. Green:265 affected tests; Ruff/diff checks
pass. Tests cover both hands, quality/base/class/ethereal, missing/unknown stats,
cold damage, ED boundaries, optional IAS and currentHP versus Life. All18 staged/
published reports and prices unchanged. New throwing combinations use domain tests,
not saved captures.151 configurations;297 roles.
Generation `ff92fdae976c94b32116a2b0a49d5fb31212bc69a147a5d39fe37adc46fa77a4` selected. Guide/base/unified maintenance refreshed:
189 reviewed,179 pending stat-desirability use/quality rows.
Evidence `tmp/throwing-stats-*`; no new Python-worker restart required.

Next: audit combined-stat presentation, particularly a single ED line representing
native17/18. Domain annotations alone do not prove a multi-key rendered line shows
a marker; current single-key rendering needs a conservative shared-configuration
rule and report regression before claiming this dimension complete. Then resume
remaining circlet and rare throwing-weapon configurations. Named tiers, full source
coverage, base desirability and exact scoped prices remain unfinished.

## Combined-stat report markers — 2026-09-25

Fixed the shared stat formatter dropping every multi-native-stat marker. Combined
lines now require a common (configuration ID, desirability) contribution across all
represented native keys. Missing/unreviewed components, disjoint configuration
votes or mixed meanings within the only shared role leave the line unmarked.
Aggregate desirable votes cannot pool unrelated roles; a shared supporting role
can produce a supporting marker. Desirability prefix and roll-quality text colors
remain independent. Unresolved lines retain their original presentation.

Red regression reproduced the missing ED marker. Five focused tests now pass,
including an actual Cruel configuration through the production ED combiner and
shared terminal/OSD report. All18 published saved reports and prices unchanged.
Full suite: 2,890 passed, 3 skipped in 140.51s. Ruff, format and diff checks pass.
No KB evidence or prices
changed; the selected data generation stays the throwing-stats publication.
Evidence `tmp/combined-markers-*`. Python formatter change requires restarting
the Alt+D worker to take effect.

Next: resume unreviewed circlet and rare throwing-weapon configurations, preserving
socket/payload and build conditions. Multi-key rendering support does not close
per-family report coverage or named-tier/market/source-review gaps.

## Magus circlet skill/FCR annotations — 2026-09-25

Reviewed four exact source entries: Double Throw/Berserk Berserker's Magus and
Wake/Lightning Sentry Cunning Magus. Added stat configurations preserving class,
non-ethereal state and complete2Barbarian/20FCR or3Traps/20FCR combinations.
Existing magic/rare Barbarian equivalence is retained; Cunning remains magic-only.
Socket payloads, equipment and full-loadout breakpoints remain conditions on partial
fit, advisory only for skill/FCR recognition. No completed-helmet or price claim.

Red:4 missing-configuration failures. Green:267 affected tests; Ruff/diff checks
pass. Tests cover each role, quality, thresholds, missing/unknown modifiers, class,
ethereal, identification and class-skill substitution for Traps. All18 staged and
published saved reports/prices unchanged; new combinations use domain fixtures.
155 configurations;297 roles. Generation `60ddf06bb2afb2b1b90a830a8c6aa0e3a6411c551e25f22daeb8753e5442526b` selected.
Guide/base/unified refreshed: 195 reviewed,173 pending
stat-desirability use/quality rows. Evidence `tmp/magus-stats-*`.
Data-only change; no further worker restart beyond the preceding formatter update.

Next demand-led batch: six empty-socket Diadem/Tiara suffix configurations, preserving
exact base, three empty sockets, class and FRW/Dex/MF thresholds. Then schedule a
specialist/leveling tail. Named tiers, complete source review, base desirability
and scoped exact-price evidence remain independent unfinished gates.

## Empty-socket circlet suffix annotations — 2026-09-25

Reviewed six Artisan/Jeweler source entries: Double Throw Speed/Nirvana/Luck
Diadems, Strafe Speed/Nirvana Diadems and Berserk Luck Tiara. Added suffix markers
only after exact base/class/magic non-ethereal quality/three-empty-socket predicates
pass. FRW30, Dex21 and MF26 lower thresholds retained. Filled/partial/unknown sockets
or fewer than three do not qualify. Empty sockets do not grant proposed jewels'
IAS or damage; socket investment and full-setup checks remain on partial fit.

Red:6 missing-configuration failures. Green:269 affected tests; Ruff/diff checks
pass. Tests cover all six roles, threshold near misses, unknown stats, socket count/
contents, Diadem versus Tiara, class, quality, ethereal and identification. All18
staged/published saved reports and prices unchanged; new combinations use domain
fixtures.161 configurations;297 roles. Generation `c6ea179117667e74d28069f40029c9f6003d9bb1734fb6d5e0f4c4e11a53fc7f` selected.
Guide/base/unified refreshed: 201 reviewed,167 pending
stat-desirability use/quality rows. Evidence `tmp/socket-circlet-stats-*`.
Data-only update; no further restart beyond the prior combined-stat formatter fix.

Next scheduled starter/specialist tail: `lightning-fury-starter-lancers-javelin`,
reviewing the inherent/affix skill combination and quality/base requirements before
claiming highlights. Then resume remaining rare-throwing and socket-base families.
Full named tiers, source completeness, base desirability and scoped prices remain
independent unfinished gates.

## Starter tail: Lancer javelin annotations — 2026-09-25

Reviewed Lightning Fury Starter Weapon. Added one configuration preserving Amazon
class, magic non-ethereal Matriarchal Javelin and captured4..6Javelin/Spear skills
with exactly40IAS. The observed total combines inherent/affix contributions; it does
not prove a specific prefix roll. Prefer6 without deriving perfect-roll status.
Full52IAS target, equipment and throwing quantity remain conditions on partial
fit, advisory only for recognizing the current skill/speed pair.

Red: missing configuration reproduced. Green:264 affected tests; Ruff/diff checks
pass. Tests cover skills4/5/6 and invalid3/7, exact IAS boundaries, unknown values,
wrong base/quality/class, ethereal/identification and conflicting capture rows.
All18 staged/published saved reports and prices unchanged; this javelin uses a
domain fixture, not a saved capture.162 configurations;297 roles.
Generation `85049fc7d24f8c3c1c673aa02a7148874d4621e6e2ab14dc1e5298d907df79f4` selected. Guide/base/unified refreshed:
202 reviewed,166 pending stat-desirability use/quality rows.
Evidence `tmp/javelin-stats-*`. Data-only update; no further worker restart beyond
the prior combined-stat formatter fix.

Next: rare throwing planner weapon/off-hand configurations, then remaining socket
base families. Preserve complete modifier/quantity-sustain conditions and exact
scope. Named tiers, source completeness, base desirability and matched price
evidence remain independent unfinished requirements.

## Rare throwing planner-target annotations — 2026-09-25

Reviewed decoded cached planner db0106mf items77/76/79, preserving their2023 source
date and high-roll example scope. Added separate main/off-hand configurations for
ethereal rare Ghost Glaive/Winged Axe/Flying Axe with the complete ED/AR/IAS/Combat
skills/replenishment/Amplify combination. Typed replenishment and chance units,
Barbarian class, zero sockets and cold exclusion remain mandatory. These exact
planner targets do not establish minimum viable rolls or market valuations.
Quantity sustain, actual damage/breakpoints and equipment remain on partial fit;
lower rolls retain the explicit separate-assessment qualification.

Red:2 missing-configuration failures. Green:265 affected tests; Ruff/diff checks
pass. Tests cover both roles and all3bases, required-stat near misses/unknowns,
wrong units, cold, incomplete capture, class, quality, ethereal and socket state.
All18 staged/published reports/prices unchanged; new rare throwing scenarios use
domain fixtures.164 configurations;297 roles. Generation `a5ecb0e9e7f2abe8559246a37952ed6b8c9a7f32abdd22a6c854edf2412226e3` selected.
Guide/base/unified refreshed: 204 reviewed,164 pending
stat-desirability use/quality rows. Evidence `tmp/rare-throwing-stats-*`.
Data-only update; no further worker restart beyond the prior formatter change.

Next: remaining socket-base families (JMOD shield configurations, Shroud suffixes,
Crown leveling variants), with exact base/quality/socket state preserved. Keep
preparation eligibility distinct from completed payload utility. Full named tiers,
source review, base desirability and exact scoped prices remain unfinished.

## JMOD preparation annotations — 2026-09-25

Reviewed12 exact cached JMOD source entries. Added class-specific blocking-pair
annotations requiring magic non-ethereal Monarch, four empty sockets,20block and
30FBR. Missing/unknown/filled/partial socket state does not qualify. Fissure MF
retains four-Ist preparation while the other configurations retain their Facet
requirements; empty sockets never supply future MF or elemental bonuses. Complete
block/cast-rate/equipment checks remain on partial fit, advisory only for present
base-modifier recognition.

Red:5 grouped missing-configuration failures. Green:268 affected tests; Ruff/diff
checks pass. Tests cover every role member, both blocking thresholds, unknown stats,
class, base/quality, ethereal/identification and socket count/contents. All18 staged/
published reports and prices unchanged; new JMOD scenarios use domain fixtures.
176 configurations;297 roles. Generation `c37c5b87e09279f110c34831da3adbaf8475d0d1f7c1f52687bbf113139b3964` selected.
Guide/base/unified refreshed: 216 reviewed,152 pending
stat-desirability use/quality rows. Evidence `tmp/jmod-stats-*`.
Data-only update; no further restart beyond the prior combined-stat formatter fix.

Next scheduled starter/leveling tail: the two Lightning Strike Crown socket-base
variants. These may have no captured stat priority on an empty base; review the
appropriate usefulness/preparation/report behavior rather than inventing a stat.
Then resume Strafe Shroud suffixes and remaining reviewed-rule coverage gaps.
Full named tiers, source review, base desirability and exact scoped prices remain
independent unfinished gates.

## Starter tail: Crown preparation review — 2026-09-25

Reviewed both exact Lightning Strike Artisan Crown source rows: three Perfect
Topazes versus Ral/Ort/Thul. Neither specifies a base-defense target. Removed
unsupported31:0 defense from important_stats, which previously leaked into the
role's important_rolls. Preserve magic Crown/Amazon/non-ethereal/three-empty-socket
eligibility and exact future filler guidance. The empty base has no stat priority;
no invented marker or future MF/resistance bonus was added.

Red:2 regressions reproduced inappropriate important-roll output. Green:265 affected
tests; Ruff/diff checks pass. Tests prove defense is not a requirement/priority,
preparation remains partial and unknown/filled sockets do not qualify. All18 staged/
published reports/prices unchanged; Crown scenarios use domain fixtures.
176 configurations;297 roles unchanged. Generation `caad2623e7d9a8a5fb6b374c7dcef9bf46566c1e9d5b6b5c7c845778c6f862ba` selected.
Guide/base/unified maintenance refreshed; stat-desirability counts do not increase.
The current matrix still leaves these rows pending because it lacks an explicit
source-reviewed no-stat-priority disposition. Do not fabricate empty configurations
to inflate coverage. Evidence `tmp/crown-review-*`.

Next: implement validated no-stat-priority review dispositions for the Crown pair
in coverage maintenance (source/profile fingerprints, reason and invalidation),
then resume Strafe Shroud suffixes. Full named tiers, source review, base desirability
and exact scoped prices remain unfinished. Data-only runtime change; no further
worker restart beyond the prior formatter fix.

## Reviewed no-stat-priority coverage dispositions — 2026-09-25

Added maintenance-only explicit dispositions for the two reviewed Lightning Strike
Crown preparation roles. Excludes only stat_desirability; stat annotations, report,
market and all other dimensions retain their prior states. No empty runtime stat
configuration and no no-use/vendor decision is introduced. Reviews bind exact role
fingerprints, source locators/hashes and review dates; stale evidence, duplicate
reviews, unsupported dispositions and conflicts with priorities fail validation.
Unreviewed roles with no important_stats remain pending.

Red:8 missing-interface failures. Green:89 maintenance/Crown tests;10 focused tests
rechecked after tightening exception assertions. Ruff and diff checks pass. Full
matrix comparison proves exactly two row/dimension changes: use-quality stat
coverage is216 reviewed,2 excluded,150 pending. Evidence:
`tmp/stat-dispositions-{red,green}.log`, `tmp/stat-dispositions-coverage.json`.
No runtime artifacts changed or publication required; selected generation remains
`caad2623e7d9a8a5fb6b374c7dcef9bf46566c1e9d5b6b5c7c845778c6f862ba`.
Next: resume Strafe Shroud suffix review with whole-item/socket conditions and
source-backed priorities. Full named tiers, source review, base desirability and
exact scoped prices remain unfinished independent gates.

## Strafe Shroud preparation stat priorities — 2026-09-25

Reviewed cached Strafe Body Armor alternatives1/2 and native expansion torso
suffix rows: Stability24FHR, Precision10–15Dexterity. Added two source-bound stat
configurations preserving Amazon/magic/non-ethereal/exact Dusk Shroud/four-empty-
socket gates. Removed unsupported defense priority from both roles. Precision15
remains a preference; no future socket bonus, breakpoint or price is inferred.
Complete socket payload and loadout guidance retain partial preparation status.

Red:2 missing-configuration failures. Green:340 affected role/stat/maintenance tests;
Ruff/format/diff checks pass. Domain fixtures cover suffix minima, absent/unknown
stats, no cross-suffix substitution, wrong base/quality/class, ethereal/identification
and socket count/contents. All18 staged and published reports and prices unchanged.
178stat configurations;297roles. Generation
`c63e6c44c48579b10a8cd4c935302c5f5bd3becc6cf11a0cb90089b47faad671`
selected. Guide/base/unified maintenance refreshed:218reviewed,2excluded,148pending
use-quality stat-desirability rows. Evidence `tmp/shroud-stats-*`. Data-only runtime
update; no additional worker restart required.

Next: Mirrored Blades Starter Rhyme Grimoire preparation (all three staffmods plus
exact two-empty-socket/base/class constraints), then remaining starter dagger and
imbued throwing configurations. Named tiers, exhaustive source review, base
usefulness and exact offline price coverage remain independent unfinished gates.

## Rhyme Grimoire preparation staffmods — 2026-09-25

Reviewed exact Mirrored Blades Starter offhand source and native Grimoire/skill
identities. Added one stat configuration for normal and superior non-ethereal
Grimoire with two empty sockets, Warlock context and all three positive staffmods:
Mirrored Blades392, Hex Purge389, Summon Defiler377. Stronger staffmods qualify
without inferred perfect-roll status. Shael/Eth insertion remains a partial-use
condition; empty bases receive no completed recipe bonuses or price claim.

Red:2 missing-configuration cases. Green:340 affected tests; Ruff/format/diff checks
pass. Fixtures cover both qualities, each missing/zero/unknown skill, Hex Purge
explosion404 and other skill-bonus substitutions, wrong base/class/quality,
identification/ethereal and socket count/contents. All18 staged and published saved
reports/prices unchanged.179configurations/297roles. Generation
`3f87e4ff3df597b5e629d4a6632133f314ae8f87080c8786153f283afd6648fc`
selected; guide/base/unified coverage refreshed:220reviewed,2excluded,146pending
use-quality stat-desirability rows. Evidence `tmp/grimoire-stats-*`. Data-only update.

Next: starter Echoing/Abyss dagger rules still use required_any_stats without an
explicit must predicate. Review exact source requirements and applicability before
adding stat configurations; keep FCR dependencies and alternative-weapon advice.
Then imbued throwing configurations. Named tiers, full guide/source review, base
utility and exact scoped market coverage remain independent unfinished gates.

## Abyss starter dagger priorities and duplicate-gate reporting — 2026-09-25

Reviewed exact cached Abyss Starter prose: check daggers for skill ranks before
Spirit; the75FCR target is a whole-loadout target. Added an explicit any-skill
predicate preserving existing alternatives and one stat configuration for magic,
rare and crafted daggers. Present relevant skill bonuses are desirable; FCR is
supporting only and cannot qualify a dagger alone. No ED/AR priority, socket or
ethereal premium inferred. Existing pre-runeword/loadout qualifications remain.

Saved Dread Edge replay exposed duplicated restriction text when the typed gate
exactly repeated required_any_stats. Role evaluation now reuses the identical
trace and reports the specific skill outcome once. Distinct compound requirements
retain their independent restrictions. Red3 configuration failures and3 duplicate
report cases; focused green, then full2974passed/3skipped(135.77s). The initial
artifact-equality failure was resolved by rebuilding profiles. Ruff/format/diff pass.
All18 final staged/published reports and prices equal the prior generation after
the duplicate-report fix. Evidence `tmp/abyss-dagger-*`.

180configurations/297roles. Generation
`148c6cc03f09cb1772616096873449c02786b584e03f027d810202c0d626f7d9`
selected and revalidated. Guide/base/unified refreshed:223reviewed,2excluded,
143pending use-quality stat rows. Restart Alt+D for the Python reporting change.

Source concern requiring next review: echoing-starter-dagger still has no stat
configuration. Direct cached HTML confirms its dagger passage concerns three-
socket future runeword bases, whereas the old role selects magic/rare/crafted.
General AR/skill advice alone does not prove that specific affixed-weapon role.
Correct that legacy role's source scope/coverage before adding annotations; do
not silently promote it as a reviewed affixed guide recommendation. Cached source:
pricing/raw/mr/guides__echoing-strike-warlock-guide.html, Starter Setup paragraph.
Then resume remaining imbued throwing configurations. Named tiers, source review,
base usefulness and exact price coverage remain unfinished independent gates.

## Corrected Echoing affixed-dagger source mapping — 2026-09-25

Retired echoing-starter-dagger from executable profiles: exact cached Starter prose
advises future three-socket runeword daggers, not magic/rare/crafted weapon use.
General attack-rating and skills advice across gear does not establish that role.
Retained original profile, source hash/locator, review rationale and pending base
replacement in planning/retired_role_reviews.json. No no-use/trash/price decision.
The passage does not name a recipe or required staffmod combination; native legal
socket eligibility alone must not be promoted to desirable-base coverage.

Red: saved Dread Edge incorrectly matched Echoing. Green:114 focused tests.
Broader assessment run1637passed/3failed because repository fixtures mutated the
first profile without renewing its now-present stat review. Fixed those fixtures
to compile a valid reviewed update; all8repository/stat-bundle rechecks pass.
Runtime stale-review validation remains intact. Ruff/format/diff checks pass.
Skill-evidence tests now use the retained Abyss role, preserving their original
unknown/conflict/absence semantics. Evidence `tmp/echoing-source-*`.

Published Dread Edge now shows0confirmed/0conditional builds instead of the false
Echoing candidate; other17report texts unchanged. All18prices unchanged. Generation
`d349958b5e98921a9d167712211935669cfa10d958e7301e97008eb932ce8fec`.
All62891source occurrences and2739identity IDs retained; direct rule links273→271.
296executable roles/180stat configurations. Use-quality rows368→365; stat states
223reviewed/2excluded/140pending. This reduction removes three invalid quality
assignments; it is NOT three newly completed reviews. Original base-source work
remains open. No additional Python runtime changes/restart beyond prior checkpoint.

Next: remaining five Double Throw imbued examples (axe/knife/harpoon). Preserve
slot-specific stat combinations and planner-example scope. Echoing runeword-base
replacement, full source review, named tiers, base usefulness and exact offline
price coverage remain unfinished gates.

## Double Throw imbued-example priorities — 2026-09-25

Reviewed cached db0106mf embedded items80/81/143: Flying Axe, Flying Knife and
Winged Harpoon, retaining2023source date and five guide hand placements. Added five
stat configurations requiring each complete rare/ethereal/Barbarian/zero-socket,
no-cold combination. Axe fire resistance/IAS, knife AR/Amplify/mana leech and
harpoon IAS/life leech stay separate alongside ED, Combat skills and typed quantity
replenishment. Match means the cited example, not a minimum viable roll, guaranteed
imbue, unlimited quantity, breakpoint or price. Preparation/loadout advice remains.

Red:5missing configurations. Green:349affected tests; Ruff/format/diff checks pass.
Fixtures cover all five roles, each missing/below-target modifier, typed units,
cold/incomplete captures, base/quality/class/ethereal/socket/identification gates,
and unrelated example modifiers do not inherit priorities. All18staged/published
report texts/prices unchanged.185configs/296roles. Generation
`e0d0b2c2655cd31d20f2ebd4601461d9230fbf6c1f262f02409f9b021220666f`.
Guide/base/unified refreshed:228reviewed,2excluded,135pending use-quality stat rows.
Evidence `tmp/imbue-stats-*`. Data-only, no additional worker restart.

Current executable non-named role priority queue is covered:185configurations plus
the2Crown dispositions. This is NOT all-item or all-guide completion, and does not
close roll/report/price dimensions. Remaining109role configurations are named items
and completed runewords (44set quality rows,39unique,26normal/26superior runeword).
Next: add explicit identity-safe stat-configuration support, starting with completed
Insight roles as GUIDE_FIRST's acceptance fixture. Current compiler rejects named
roles; some have typed must/base families (Insight), while others lack them (Sazabi).
Do not remove that guard without preserving exact identity, completed recipe/base,
companion/mercenary conditions and independently reviewed priorities. Continue
specialist/leveling tail scheduling and the outstanding named-tier/base/source/price
gates; Echoing base replacement remains pending documented source review.

## Identity-bound named stat configurations and Insight — 2026-09-25

Compiler now accepts reviewed named roles only with explicit base types and a must
predicate. It composes exact name selectors into the compiled required predicate;
identity remains enforced outside CandidateIndex and after serialization. No new
schema or inference from important_stats. Named roles lacking mechanical predicates
still fail compilation rather than receiving invented applicability.

Reviewed12 completed Insight mercenary configurations for Meditation mana support.
Require identity/runeword, polearm/spear, four filled sockets, native aura and exact
mercenary dependency. Remaining equipment advice stays partial. Only Meditation
gets desirability; ED/Critical Strike are not automatically imported from old
important_stats. Range/perfect-roll quality remains separate. Unknown context does
not gain a stat-match claim; exact prices and named tiers are unaffected.

Red: named compiler rejection plus12 missing-config cases.117focused tests pass.
Full suite2993passed/3skipped with1publication locator fixture failure: mutating the
first profile now hits its stat-review guard before locator validation. Renewed the
test's stat binding so the original source-locator rejection is actually exercised;
all11publication validation checks pass.13Insight tests pass including saved Bill
under explicit Act2Might context (level12Meditation highlighted). Ruff/format/diff
checks pass. All18default staged/published texts/prices unchanged. Evidence
`tmp/{named-stats,insight-stats}-*`.

197stat configurations/296roles. Generation
`b7f50bf926f71ed5e87d9685a197eba6fec90de21f52622dfa23c7e569c2c94c`.
Guide/base/unified refreshed:252reviewed,2excluded,111pending use-quality stat rows.
Restart Alt+D: runtime bundle validation imports the changed compiler, so an older
worker must load the new identity-binding implementation to accept named reviews.

Next: three existing Infinity roles (self-wield and mercenary) with beneficiary-
specific stat semantics; then reserve a specialist/leveling named-item batch.
97named/runeword role configs remain,37already have explicit types/must. Remaining
named profiles need reviewed mechanical requirements before annotation. Broad
source census review, unique/set tiers, base utility, roll/report coverage and
matched offline prices remain independent unfinished gates.

## Infinity beneficiary-specific priorities — 2026-09-25

Reviewed cached Nova Standard/Hydra Hybrid and Lightning Strike Standard sources.
Added three identity-bound stat configurations: Nova self-wield highlights wearer
lightning pierce; mercenary highlights Conviction with paired ED as physical support;
Amazon self-wield highlights pierce with paired ED as physical support. No Nova
spell-damage claim from ED; mercenary weapon pierce does not transfer to player.
ED annotations require both decoded components. Range quality remains separate.

Made Nova Hydra Hybrid's source-specific Might/Holy Freeze mercenary choice a typed
dependency (previously prose only); renewed that role's guide-use fingerprint.
Recipe/four-filled-socket/aura and exact weapon family gates remain required. Source
base preferences, Amazon staffmods/Faith, equipment and full loadout stay partial;
none become universal best-base, ethereal, breakpoint or price claims.

Red:3missing configs. Green:348affected tests; Ruff/format/diff pass. Cases cover
both qualities, identity/recipe/socket/type/identification, aura, missing ED pair,
unknown pierce and missing/wrong/supported mercenary contexts. All18staged/published
reports and prices unchanged; Infinity cases use domain fixtures.200configs/296roles.
Generation `77b452b2a15148898ea116f0d27addf5a0115a070c22a6c96626cef5139ffd08`.
Guide/base/unified refreshed:258reviewed/2excluded/105pending use-quality stat rows.
Evidence `tmp/infinity-stats-*`. Data-only; no additional restart beyond prior
named-stat compiler update.

Next scheduled specialist/budget tail: Dragon Talon Kira's Guardian and Duriel's
Shell Cannot Be Frozen alternatives, preserving resistance combination, non-ethereal
player use and the slot/complete-Uber-loadout qualifications.94named/runeword roles
remain without stat configs. All-item named tiers, base/source review, roll/report
coverage and exact scoped price evidence remain independent unfinished gates.

## Specialist budget tail: Kira/Duriel CBF alternatives — 2026-09-25

Reviewed exact Dragon Talon Budget quote naming Kira's Guardian/Duriel's Shell as
Cannot Be Frozen alternatives. Added two named stat configurations: CBF desirable,
all four elemental resistances supporting. Preserve unique identity/base family,
Assassin/non-ethereal and complete native CBF/resistance combination. Slot tradeoffs,
Crushing Blow/AR/full resistance, equipment and level90/Uber readiness stay partial;
no defense/life priority, resistance-cap or market claim inferred. Added the cached
May22,2026source date to both role and guide-use records and renewed fingerprints.

Red:2missing configurations. Green:347affected tests; Ruff/format/diff pass. Cases
cover each absent/zero/unknown modifier, name/type/quality/class/ethereal and
identification; unrelated defense/life do not become priorities. Both alternatives
retain their own slot and full-loadout qualifications. All18staged/published report
texts/prices unchanged; new cases use domain fixtures.202configs/296roles.
Generation `c4da29605e77bbafdc67f583e96df09d2d924345516bb3422fac9483bdec66e0`.
Guide/base/unified refreshed:260reviewed/2excluded/103pending use-quality stat rows.
Evidence `tmp/budget-cbf-stats-*`. Data-only; no additional restart beyond the prior
named-stat compiler update.

Next demand batch: three Stealskull MF mercenary and four Crown of Thieves GF
mercenary configurations. Review socket payload, ethereal/upgrade and exact setup
requirements; no universal farming-helm premium or priority from mere mention.
92named/runeword configs remain. Named tiers, source/base/roll/report coverage and
matched offline prices remain independent unfinished gates.

## Farming mercenary helmets: Stealskull/Crown priorities — 2026-09-25

Reviewed seven exact cached MF/GF helmet entries: three Stealskull/Ist variants and
four upgraded Crown of Thieves/Lem variants. Added source-bound configs with MF/GF
desirable and life leech/Stealskull IAS supporting. Exact unique/type, complete
modifier combination, verified socket rune and mercenary remain mandatory; Crown's
Corona upgrade dependency is retained. Ethereal remains a preference (including
unknown/non-ethereal cases), not a price multiplier or stat-annotation requirement.
No defense priority or native-perfect-roll claim is inferred from socket totals;
full equip/breakpoint/survival and kill attribution remain separate.

Added cached May22,2026source dates to the seven role/guide-use records and renewed
fingerprints. Red:7missing configs. Green:352affected tests; Ruff/format/diff pass.
Tests cover every member, modifiers absent/zero/unknown, required child rune versus
empty/wrong/unknown socket state, missing/wrong mercenary, identity/quality and
unupgraded Grand Crown. All18staged/published report texts/prices unchanged; new
helmet combinations use domain fixtures.209configs/296roles. Generation
`40b5c78ccbc7e541822e40b10f1622a66319cd10c68753fae6c809129be695c2`.
Guide/base/unified refreshed:267reviewed/2excluded/96pending use-quality stat rows.
Evidence `tmp/farming-helm-stats-*`. Data-only; no additional restart beyond the
named-stat compiler update.

Next: six Vampire Gaze mercenary roles, preserving compound IAS/resistance jewels,
Um alternatives and the Mephisto activity restriction. After that demand batch,
reserve the next specialist/leveling tail.85named/runeword configurations remain;
all-item tiers, source/base/roll/report coverage and scoped exact price evidence
remain independent unfinished gates.

## Vampire Gaze setup priorities and explicit activity — 2026-09-25

Reviewed six cached Gaze setups. Life leech/physical reduction are desirable only
with the complete native pair, correct identity and source mercenary/socket setup.
Three Rogue sources retain a single compound15IAS/all-resistance jewel; captured
parent IAS/resistance totals also receive priorities only after that child proof.
Two Frenzy sources require Um; Lightning Strike Ubers has no invented socket gate.
No defense/MDR priority, guaranteed survival or ethereal requirement inferred.

Added nullable explicit AssessmentContext.activity and a typed Uber Mephisto
requirement to Lightning Sorceress's Act5role. Missing/malformed/other-boss/ordinary
Mephisto contexts cannot activate its priorities. The source's other-Ubers Act2
alternative remains in conditional advice. Added cached source dates and renewed
role/guide fingerprints. Restart Alt+D for the context schema used by validation.

Red:6missing configs, then3missing parent-jewel annotations. Initial focused run
also exposed an overly strict test assumption: fully captured child jewels can
prove an existential match with an unknown parent summary. Kept that valid proof;
empty contradiction, missing children, parent totals alone and split jewels fail.
Full3013passed/3skipped(161.43s), then final parent-priority data update verified with
105affected checks. Ruff/format/diff pass. All18default staged/published texts/prices
unchanged; Gaze-specific cases use domain fixtures. Evidence `tmp/gaze-*`.

215configs/296roles; generation
`750aac3177396602a102b5a6071b5ed994d99f0ff732ea07b715d9bf4e9277ce`.
Guide/base/unified refreshed:273reviewed/2excluded/90pending use-quality stat rows.
79named/runeword configs remain. Next scheduled starter tail: Fissure Lore pelt;
review whether +3Fissure is a planner target versus a minimum before compiling.
All-item named tiers, source/base/roll/report coverage and exact scoped prices remain
independent unfinished gates.

## Fissure Starter Lore: planner preference correction — 2026-09-25

Cached Starter prose prioritizes +skills without a numeric Fissure minimum. The
pictured +3 Fissure Lore Antlers is now a preference; positive +1/+2 staffmods also
qualify as skill-support candidates. This reviewed inference does not establish
farming readiness. Exact Lore identity/recipe, pelt, normal/superior quality, Druid,
non-ethereal and two filled sockets remain required. Captured Fissure and all-skills
are desirable; a missing all-skills line is never fabricated from the recipe.
Source review and guide-use fingerprints renewed; one stat configuration added.

Red: five failures (missing configuration and former +3 minimum). Green: 348 affected
checks, Ruff/format and diff check pass. All 18 staged and published saved reports
and prices match the prior generation. No saved Lore capture exists in this replay
set; specific +1/+2/+3, preference, near-miss and unknown behavior uses domain tests.
Published generation d7aff9647e8493f758ee5a1d942a73b123021a940d4ebe994cb6aff233913102.
216 configs / 296 roles; use-quality stat coverage 275 reviewed, 2 excluded,
88 pending. Guide inventory and base/coverage matrices refreshed offline.
Evidence: tmp/lore-stats-*. Data-only; no additional restart beyond Gaze context.

The scheduled starter tail is complete. Next demand batch should be selected from
remaining named-role dossiers by distinct-build breadth and new use coverage,
checking source-required versus planner-target semantics before adding priorities.
78 named/runeword role configurations remain; this finite queue does not close
all-item coverage. Named tiers (93 reviewed / 472 pending), guide semantics,
base/roll/report coverage and exact scoped market evidence remain unfinished.

## Naj Teleport-swap stat priorities — 2026-09-25

Demand-led batch selected from the remaining named queue: 13 distinct cached build
lists share Naj's Puzzler as a weapon-swap alternative. Reused exact source locators,
May 22 source dates, existing class/native base/charge/equipment predicates and
conditional advice. Added verified staff type selectors and renewed guide-use
fingerprints, then 13 explicit charge-priority reviews. No guide re-extraction or
market collection. Available Teleport charges are desirable only after the full
existing role gates and charge payload validation; missing charges are not invented.
Roll quality remains independent. This does not claim current loadout need, main
weapon suitability, perfect rolls or price. The planner-only Fal variant remains
separate and unreviewed for stat priorities.

Red: 13 missing-config failures. Green: 110 affected tests; Ruff/format/diff checks
pass. Cases cover every role plus empty/malformed/wrong-level/duplicate charges,
wrong identity/type/quality/class, unknown ethereal/equipment facts, level shortfall
and socket-modified equipment uncertainty. No saved Naj capture exists; domain
fixtures prove its new behavior. All 18 existing saved reports/prices match before
and after publication. Evidence tmp/naj-stats-*. Data-only; no new restart required.
Generation 49cb4e3e3b76b89afd69a778eda881f48a18682fe285e54ab748ae1963051923.
229 configs / 296 roles; use-quality stat coverage 288 reviewed / 2 excluded /
75 pending. Guide inventory/base/coverage matrices refreshed. 65 named/runeword
role configs remain; global guide semantics, named tiers, base/roll/report and
scoped exact-price coverage are still incomplete.

Next demand batch: four Demon Limb prebuff configurations across Echoing, Strafe
and Dream, preserving available Enchant charges and the Lava Gout alternative.
Then reserve a specialist/leveling tail (including the separate Fal Naj planner
source review). This is batch one of two since the Lore starter tail.

## Demon Limb prebuff priorities — 2026-09-25

Second demand-led batch since the Lore tail: four configurations across three
builds (Echoing Standard/Ubers, Strafe Standard, Dream Ubers). Reused cached variant
sources and dates, confirmed prebuff prose, and added verified club applicability
plus source-bound Enchant-charge priorities. Strafe's absence-of-Lava-Gout dependency
remains mandatory; missing loadout is unknown. Only valid available Enchant charge
rows receive markers. Damage does not become desirable for a prebuff role. Ethereal
copies with charges retain temporary utility and the existing recharge limitation;
unknown ethereal status does not invent repairability. Equipment advice and buff
activity remain conditional, not proof of a currently active buff or combat use.

Red: four missing configuration failures. Green: 349 affected maintenance/role/stat
checks plus nine existing Demon Limb/demand tests. Ruff/format/diff checks pass.
Every configuration exercises identity, type, quality, class, empty/malformed/wrong
skill/duplicate charge failures, all ethereal states, and the Strafe alternative.
All 18 staged/published saved report texts and prices unchanged. No saved Demon Limb
capture exists in that set; new behavior uses domain fixtures. Evidence tmp/demon-stats-*.
Generation 2f96e99e51af41b3067a913646c0661e3bdf6edfae260ce7791cda97bd7d790c.
233 configs / 296 roles; use-quality stat coverage 292 reviewed / 2 excluded /
71 pending. Guide inventory and base/coverage matrices refreshed offline. Data-only;
no new worker restart beyond previously documented context changes.

Next scheduled specialist/leveling tail: review the separate Poison Nova Fal Naj
planner source and its equipment/endorsement limitations before deciding whether
stat priorities are justified. Keep planner-only discovery separate from confirmed
build demand. 61 named/runeword configurations remain, with global guide semantics,
named tiers (93 reviewed / 472 pending), base/roll/report coverage and scoped prices
still incomplete. Do not treat this role queue as the all-item denominator.

## Fal Naj planner example retired from executable roles — 2026-09-25

Scheduled specialist tail found a source-strength inconsistency: the existing
Poison Nova Fal-socketed Naj review says example, not separate guide endorsement,
but an executable candidate role still emitted it. Removed that one runtime role
and guide-use link; preserved full previous profile, example review and source in
planning/retired_role_reviews.json. Original source/occurrence data stays intact.
Exact variant endorsement and socket-modified equipment readiness remain pending.
The independently endorsed Poison Nova Naj swap remains, as do all 13 reviewed Naj
build alternatives. No no-use/trash disposition or negative price claim follows.

Red: one incorrect role-presence test failure. Green: 110 focused checks and all
1,699 assessment tests (119.41s); Ruff/format/diff pass. All 18 staged/published
report texts and price estimates unchanged. Naj demand still counts 13 distinct
builds. Published generation 51e071b02b2ee3ea1320ce54076421d54b9e9b4559c5b408ae3b9309f1376563.
233 stat configs / 295 executable roles. Use-quality rows 365 → 364; stat states
292 reviewed / 2 excluded / 70 pending. This pending decrease is removal of an
unsupported executable assignment, not completion of a stat review. Guide inventory
and base/coverage matrices refreshed; source occurrences retained. Evidence
 tmp/fal-source-*. Data-only; prior Python restart guidance remains.

Next demand batch: Angelic ring/amulet combinations across five builds. Review
piece versus active set-bonus priorities and required companions; do not annotate
an amulet with a bonus belonging only to the ring or imply a whole set is equipped.
60 named/runeword configs remain; global source/tier/base/roll/report/market gates
remain unfinished. Tail complete; demand-batch scheduling restarts at zero.

## Angelic piece-specific stat priorities — 2026-09-25

Demand batch one after the Fal source tail: ten ring/amulet roles across five builds.
Reused reviewed pairing sources and native setitems: Halo aprop1a att/lvl maps to
native 224, while Wings has no such property. Five ring configurations mark only
captured positive 224:0 desirable after exact class/player companion/multiplicity
checks. Flat attack rating cannot substitute, missing set bonuses are not fabricated,
and no perfect-roll/price claim follows. Existing readiness advice stays conditional.

Five source-bound no-stat-priority dispositions cover the enabling amulet roles:
these sources establish the pair's attack-rating use, not an independent priority
for the amulet's captured stats. This is not no-use, trash or a ban on future reviewed
amulet priorities. Existing Build use and companion conditions remain intact.

Red: five missing configurations. Green: 107 affected checks after updating the
explicit exclusion inventory test from two Crowns to two Crowns plus five amulets.
Ruff/format/diff pass. Cases cover every build, ring counts, unknown/merc-only/wrong
companions, absent/zero/duplicate/wrong stat, identity/class/type/quality. No saved
Angelic capture exists; domain fixtures verify new behavior. All 18 saved staged
and published report texts/prices unchanged. Evidence tmp/angelic-stats-*.
Generation 379f5e805c0447897849b432133fbb803c45cb49ee0b24d20ee70bffd4951579. 238 configs / 295 roles;
stat-use 297 reviewed / 7 excluded / 60 pending. Guide/base/coverage refreshed.
Data-only; no new restart. Five exclusions are explicit per-use reviews, not a
universal amulet rule or new completed market coverage.

Next demand batch: Sigon/Death's starter set combinations, preserving distinct
piece bonuses and partial-set requirements; then scheduled specialist/leveling tail.
50 named/runeword roles still lack a stat configuration or reviewed disposition.
Global guide semantics, named tiers, base/roll/report and exact scoped prices remain
unfinished; this finite role queue is not the all-item denominator.

## Starter set glove/belt priorities — 2026-09-25

Second demand batch after the Fal tail: seven configurations, covering three Sigon
Gage combinations, Enchant Death's Hand/Guard, and two upgraded Guard setups.
Native piece definitions confirm IAS on Gage/Hand and CBF on Guard. Reviewed
inference from these attack-oriented combinations marks only captured relevant
stats, after exact player/class/companion or upgraded-base gates. Never transfer
other-piece bonuses or fabricate a set bonus on an unequipped hover. The generic
source conditions still qualify equipment, breakpoints and full build readiness.
Normal Death's Guard retains its true item predicate/CBF utility, but cannot satisfy
the cited upgraded potion-capacity configuration. No market premium inferred.

Red: seven missing configs. Initial green run exposed two test-only mapping-access
errors; corrected rule_trace['truth'] access. Final 112 affected checks pass;
Ruff/format/diff pass. Every role checks identity/type/quality/class, missing/zero/
duplicate stats, absent/unknown/merc-only companions, plus normal-versus-upgraded
belts. All 18 staged/published saved report texts/prices unchanged; these seven
set configurations use domain fixtures, not new live captures. Evidence
 tmp/starter-set-stats-*. Generation 9e70df3914cd602162e796597dc8cc164931e72098e400484b10f847c3ae6112.
245 configs / 295 roles; stat-use 304 reviewed / 7 excluded / 53 pending.
Guide/base/coverage refreshed offline. Data-only; no additional worker restart.

Next scheduled specialist/leveling tail: remaining six starter Sigon helmet/boot/
Wrap uses, including source-specific Ort/IAS-jewel conditions and the distinction
between a piece bonus and a set-enabling role. Do not mark all native properties
valuable merely because the named combination is useful. 43 named/runeword roles
still need stat review/disposition; all-item guide/tier/base/roll/report/market
coverage remains incomplete.

## Remaining Sigon starter stat reviews — 2026-09-25

Scheduled specialist/leveling tail covered two Visor and three Sabot uses plus
Berserk Wrap. Five configs prioritize captured piece-owned AR (Visor native224,
Sabot native19) within exact reviewed player combinations. Strafe's explicit AR
benefit and native definitions support this; Double Throw/Berserk are documented
inferences from their attack-oriented combinations. No manufactured bonus from
identity alone, no automatic MF/defense priority. Visor still needs its verified
Ort or15IAS-jewel child; parent IAS totals cannot replace child proof.
Wrap has a source-bound no-stat-priority disposition for this enabling use; no
other-piece bonus is transferred and useful Build use remains.

Red: six missing configs/disposition failures. Green:111affected checks; Ruff/format/
diff pass. Every build tests absent/unknown/merc-only companions, identity/quality/
type/class, missing/zero/duplicate stat and helmet payload failures. No saved Sigon
capture; domain fixtures verify new behavior. All18staged/published report texts
and prices unchanged. Evidence tmp/sigon-stats-*.
Generation 1e0375608f60407eb811e4085b05c89b1d2f19dc52b04dc1bae4890d34a82061.250configs/295roles;
stat-use309reviewed/8excluded/47pending. Guide/base/coverage refreshed offline.
Data-only; prior Python restart instructions remain. Tail complete.

Next: review three Tal Rasha Magic Find roles as one set-dependent configuration
family, followed by Sazabi piece-specific roles; then reserve the specialist tail.
37named/runeword roles still need stat review/disposition. Global source semantics,
named tiers, base/roll/report coverage and scoped exact prices remain incomplete.
Before claiming this finite role queue finished, audit GUIDE_FIRST obligations
against the full coverage denominator, not just executable roles.

## Tal Rasha MF piece priorities — 2026-09-25

First demand batch after Sigon tail: three named roles from cached Lightning MF
source, which explicitly values MF/FCR/resistances. Native piece definitions limit
priorities: armor MF/FCR/fire/cold/lightning resist; belt MF/FCR; amulet lightning
resist. Amulet FCR needs more than the cited three pieces and shared set MF is not
copied onto every piece. Mark only captured positive values. Exact name/type,
Sorceress, other two player pieces,117total FCR and armor Ist remain mandatory.
Added explicit identity predicates to formerly selector-only roles, preserving
runtime identity selection; no new gear minima, stat fabrication or prices.

Red: three missing configs. Initial green found an old magic/rare/crafted amulet
test counting all amulet configurations; narrowed its fixture selection to its
actual affixed-quality scope. Final107affected tests pass, including existing Tal
roles and loadout-breakpoint checks; Ruff/format/diff pass. New cases cover every
piece, missing stats, no transferred bonuses, wrong identity/type/quality/class,
missing/merc-only companions, unknown/below117FCR, and armor socket failures.
No saved Tal capture exists; domain fixtures verify its new behavior. All18staged/
published saved report texts/prices unchanged. Evidence tmp/tal-stats-*.
Generation e0477e85495fe62fd3a4afc691bded6228f08c8991762687bff6d09aa3295707.253configs/295roles;
stat-use312reviewed/8excluded/44pending. Guide/base/coverage refreshed offline.
Data-only; no new restart.34named roles still need stat review/disposition.
Next: three Sazabi roles with piece-specific priorities and full mercenary/socket
conditions; then reserve the specialist tail. All-item guide/tier/base/roll/report/
market coverage remains incomplete.

## Sazabi piece and socket priorities — 2026-09-25

Second demand batch: three Echoing Uber mercenary roles. Corrected their previously
identical important-stat lists to piece-owned properties: sword IAS/CB, armor
life/FHR/physical reduction, helm skills/fire/lightning resistance/CBF. Source
survival and OW/CB delivery rationale plus native pieces and verified Ber/Cham
effects support these reviewed inferences. IAS/skills are supporting; the remaining
selected stats desirable. Capture must contain the stat; no set/socket effect is
invented. Exact rune, companion set pieces on mercenary and Act5Frenzy remain
mandatory. Prebuff/other-weapon advice stays conditional; no survival guarantee,
perfect-roll or price inferred. Added explicit identity/type prerequisites and
renewed source review fingerprints.

Red: three missing configs. Green:348affected checks. Full suite:3055passed,
3skipped,2older fixture-selection failures (rare rings/boots counted new set configs).
Narrowed those fixtures to their intended magic/rare/crafted quality scope, then
all7rechecks passed including both failures and Sazabi/stat bundle. Ruff/format/diff
pass. No production fix was needed for the two test assumptions. Evidence
 tmp/sazabi-stats-*. All18staged/published saved report texts and prices unchanged,
including the real Sazabi helm with unconfirmed full setup; positive socket/setup
cases use domain fixtures. No new live evidence or market collection.
Generation 97a1665c71c239fceb024369f24231b5c82559d29e0daf6835b3ffc912b94448.256configs/295roles;
stat-use315reviewed/8excluded/41pending. Guide/base/coverage refreshed offline.
Data-only; no new restart.

Next scheduled specialist tail: Hydra fire Rainbow Facet, preserving recipient,
3/3 acceptance versus5/5 preference and whole-loadout conditions.31named/runeword
roles still need stat review/disposition. Broader guide/tier/base/roll/report/market
gates remain incomplete; finite role coverage is not all-item completion.

## Hydra fire Facet priorities — 2026-09-25

Scheduled specialist tail adds one source-bound configuration for the existing
Hydra Standard role. Cached prose explicitly accepts3/3fire facets; both captured
fire damage and pierce are desirable within native3–5bounds.5/5 remains a preference,
not a minimum or an automatically assigned perfect-roll marker. Full105FCR context
remains mandatory; eligible recipient/survivability stays conditional. No proc-event
preference, equipped socket fit or price inferred. Existing role/source unchanged.

Red: four missing-config parameter cases. Green:98affected checks; Ruff/format/diff
pass. Tests cover3/3,3/5,5/3,5/5, both below/above bounds, missing/duplicate modifier,
wrong element/identity/type/quality/class and unknown/below105FCR. Recipient advice
and exact preference status remain asserted. No saved Facet capture; domain
fixtures verify new behavior. All18staged/published saved report texts/prices
unchanged. Evidence tmp/facet-stats-*.
Generation 312f15341ce9d9c68a11e38618e722e0bfdc02ab1eb443de0fba2e6171263f77.257configs/295roles;
stat-use316reviewed/8excluded/40pending. Guide/base/coverage refreshed offline.
Data-only; no new restart. Tail complete; demand scheduling restarts at zero.

Next demand batch: Fire Warlock Ars Al'Diabolos Standard/MF roles, preserving
separate Um/Ist sockets and native skill identities. Then review Fissure repeated
player gear; reserve the next specialist tail after two demand batches.30named
roles remain without stat review/disposition. Global guide semantics, named tiers,
base/roll/report coverage and exact scoped market evidence remain incomplete.

## Ars Al'Diabolos variant priorities — 2026-09-25

First demand batch after Facet tail: Standard/MF Fire Warlock off-hand. Cached
May27,2026source dates/URL added to role/guide-use records with renewed fingerprints.
Two configs require complete native Chaos/FCR/fire/Apocalypse functionality, correct
Warlock/non-ethereal identity and exact Um/Ist socket. Core stats desirable; captured
mana after kill/fire resistance supporting. Only MF/Ist marks captured MF. Minimum
native rolls remain accepted and maximum fire/Apocalypse rolls preferences; no
substitute skill tab, fabricated optional/socket effect, full-loadout readiness,
perfect-roll judgement or numerical price. Advisory equipment/breakpoint/resistance
conditions retained. Native definitions verified; no fresh research.

Red: two missing configurations. Green:96affected checks; Ruff/format/diff pass.
Tests cover each required modifier missing/below minimum, optional lines absent,
wrong skill tab/class/type/quality/identity, unknown/true ethereal and wrong/empty/
unknown rune state, duplicate Apocalypse and minimum versus maximum preferences.
No saved Ars capture; domain fixtures validate new behavior. All18staged/published
saved report texts/prices unchanged. Evidence tmp/ars-stats-*.
Generation f014ae5a4bd3d7199efe9531d93a58f8c9e8ec36fcbd220e7d45e94b01a24988.259configs/295roles;
stat-use318reviewed/8excluded/38pending. Guide/base/coverage refreshed offline.
Data-only; no new restart.28named roles remain without stat review/disposition.
Next demand batch: repeated Fissure player gear (Magefist/War Traveler and helmet
alternatives), then scheduled specialist tail. Broader guide/tier/base/roll/report/
market coverage is still incomplete.

## Fissure Magefist/War Traveler priorities — 2026-09-25

Second demand batch after Facet tail: five repeated named player uses. Reviewed
cached source/native definitions; Magefist fire skills/FCR desirable and mana regen
supporting, War Traveler MF desirable and movement/attributes supporting. Captured
lines independent; missing lines not fabricated and added weapon damage not treated
as spell damage. No defense premium or50MF minimum. Existing legal upgrade bases,
nonethereal Druid gates and explicit Ubers Crusader Gauntlets dependency preserved.
Equipment/full-loadout advice remains conditional; no complete breakpoint or price
claim. Role/source predicates unchanged.

Red: five missing configs. Green:350affected checks; Ruff/format/diff pass.
Tests cover all supported base upgrades, unupgraded Ubers mismatch,30and50MF,
correct native fire skill parameter, missing lines, identity/class/type/quality/
ethereal uncertainty. No saved accessory capture; new behavior verified with domain
fixtures. All18staged/published saved report texts/prices unchanged. Evidence
 tmp/fissure-accessory-stats-*. Generation 0ba10e15e638ae8b8c27f23b5202cbcb3ab50393c43cdccbca04cca127d9fe0c.
264configs/295roles; stat-use323reviewed/8excluded/33pending. Guide/base/coverage
refreshed offline; data-only, no new restart.23named roles still need review.

Next scheduled specialist tail: completed Mirrored Blades Rhyme Grimoire, preserving
recipe versus empty preparation and all three required staffmods. Fissure Ravenlore/
Flickering Flame and mercenary families remain next demand candidates, not covered
by these accessory reviews. Global guide/tier/base/roll/report/market gates remain
unfinished.

## Completed Rhyme Grimoire priorities — 2026-09-25

Scheduled starter tail adds one configuration for completed Mirrored Blades Rhyme.
Cached source explicitly lists the three staffmods. Exact Rhyme name/recipe, two
filled sockets, native Grimoire, normal/superior, nonethereal Warlock and all three
positive native skill rows remain mandatory. Mark only captured staffmods; Hex
Purge389 cannot be replaced by explosion404. Empty two-socket preparation retains
its distinct configuration; no completed/preparation contribution pooling. Other
recipe bonuses are not invented; equipment/full-starter advice remains conditional.

Red: two missing-config cases. Green:96affected checks; Ruff/format/diff pass.
Both qualities test native skill loss/misidentity, wrong recipe/name/socket state,
ethereal/class/type uncertainty, and exact role attribution when switching to
empty preparation. No saved Rhyme capture; domain fixtures verify new behavior.
All18staged/published report texts and prices unchanged. Evidence tmp/rhyme-stats-*.
Generation 1a525fbddb818215501542617f48714fc07c8cd1db814ab759ab7bcf2a847408.265configs/295roles;
stat-use325reviewed/8excluded/31pending (two quality rows newly reviewed).
Guide/base/coverage refreshed offline; data-only, no new restart. Tail complete.
22named roles remain without stat review/disposition.

Next demand batch: Fissure Ravenlore/Flickering Flame player alternatives; then
remaining Fissure mercenary cases before another specialist tail. Global guide
semantics, named tiers, base/roll/report coverage and exact scoped market evidence
remain incomplete. Existing finite role coverage does not satisfy all-item scope.

## Fissure player helmet priorities — 2026-09-25

First demand batch after Rhyme tail: three Flickering Flame/Ravenlore roles.
Corrected important stats to include native fire skills126:1 / Elemental skills188:42
and removed unsupported automatic defense priority. Fire skills/pierce desirable;
aura/resistances/resources supporting. Optional captured Fissure gets a priority
only on pelt Flickering Flame; no ideal-base threshold. Ubers Ravenlore adds captured
fire damage only under its existing verified fire Facet gate, while Standard does
not inherit that requirement. Existing recipe/class/quality/nonethereal gates remain;
no missing stat, full-build readiness, perfect roll or price invented.

Red: five missing-config fixture cases. Green:116affected checks; Ruff/format/diff
pass. Tests cover helmet/pelt/circlet bases, no required Fissure, missing optional
stats, wrong identity/type/class/quality/ethereal/recipe, and Ubers wrong-element/
missing/contradictory socket payload. No saved helmet captures in this replay set;
domain fixtures validate new behavior. All18staged/published saved report texts/
prices unchanged. Evidence tmp/fissure-helmet-stats-*.
Generation 68b06d9ac03df73379971fdd46d3c2ffd0a3f55be943ee0c4448a03fd8d8ba70.268configs/295roles;
stat-use329reviewed/8excluded/27pending (four use-quality rows). Guide/base/coverage
refreshed offline; data-only, no new restart.19named roles remain without stat review.
Next demand batch: remaining Fissure mercenary armor/helmet cases, then specialist
tail. All-item guide/tier/base/roll/report/market coverage remains incomplete.

## Fissure mercenary runeword priorities — 2026-09-25

Second demand batch: two Fortitude variants, Uber Chains of Honor and mercenary
Flickering Flame. Cached prose distinguishes physical damage/survival, life leech,
and Resist Fire aura. Fortitude paired captured ED desirable with defense/resists
supporting; CoH captured leech desirable/resists supporting; FF only captured aura
for this role. Wearer fire skills/pierce do not transfer to Druid. Exact recipe,
class, sockets, mercenary alternatives and companion dependencies retained.
Ethereal remains a preference including unknown/nonethereal cases; no price premium,
missing stat, full survival/readiness or roll-quality judgement invented.

Red: four missing configs. Green:349affected checks; Ruff/format/diff pass after
list-construction lint cleanup. Both qualities/all ethereal states tested, both
Fortitude aura alternatives, paired ED component loss, other modifiers absent,
wrong context/recipe/type/identity/socket, player-only or missing companions.
No saved examples of these exact setups; domain fixtures validate new behavior.
All18staged/published report texts/prices unchanged. Evidence tmp/fissure-merc-stats-*.
Generation 81b746d2587e3bca8cbc6cb8d2612b715804efea5336d48a149dead252ff3be7.272configs/295roles;
stat-use337reviewed/8excluded/19pending (eight use-quality rows added).
Guide/base/coverage refreshed offline; data-only, no new restart.

Next scheduled specialist tail: two Andariel helmet/jewel configurations, reviewing
Standard planner40ED target versus required minimum and Magic Find Ruby prefix
ambiguity before assigning priorities. Starter six mercenary alternatives remain
separate pending rules.15named roles still need stat review/disposition; global
source/tier/base/roll/report/market coverage remains incomplete.

## Andariel jewel target and priorities — 2026-09-25

Scheduled specialist tail reviewed both Fissure Andariel variants. Standard40ED
was a planner target, without prose numeric minimum. Accepting the same native
31–40damage Ruby family is explicitly a reviewed inference;40remains preferred.
MF still requires the damage Ruby family rather than fire-resistance Ruby. Both
require IAS15and both ED components on one actual jewel; no pooling children or
parent-total substitution. Existing Infinity/Fortitude, Act2Might/HolyFreeze and
player-class dependencies retained. Ethereal remains preferred only.

Two configs mark captured leech/IAS/pairedED desirable, strength supporting; removed
automatic defense priority. Missing parent effects are not invented. Fire penalty,
equipment/breakpoints and full survival remain conditional. Source review and guide
fingerprints renewed. No perfect-roll or price judgement added.
Red: missing configs and planner preference/minimum behavior. Green:105affected
checks; Ruff/format/diff pass. Tests include31/40rolls, invalid affix bounds, split
jewels, missing payload, incomplete modifiers, wrong class/type/quality/mercenary,
missing or player-only companions and all ethereal states. No saved Andariel capture;
domain fixtures verify new behavior. All18saved staged/published texts/prices
unchanged. Evidence tmp/andariel-stats-*.
Generation 5d2d422e363e997d25613d0660961fe096d89aea0dff79069df72fce994fa467.274configs/295roles;
stat-use339reviewed/8excluded/17pending. Guide/base/coverage refreshed offline;
data-only, no new restart. Tail complete.

Next demand batch: six Fissure starter mercenary alternatives, keeping their native
use and recipe/owner distinctions.13named roles remain without stat review. Global
guide/tier/base/roll/report/market gates are still incomplete; do not equate current
role queue closure with all-item completion.

## GUIDE_FIRST full-inventory review dossiers — 2026-09-25

Added maintenance.review_dossiers to reuse the existing census and semantic
configuration groups. The index retains all 2,739 identity buckets, 62,891
occurrences and 273 distinct existing configurations. Exact-name expansion includes
original occurrence details/locators and configuration source excerpts/dates.
Source links remain review leads, distinct from reviewed named endorsements;
pattern reviews never become blanket named-item demand. Category/quality separation
prevents same-name identities inheriting each other's endorsements. Review effort
is explicitly unestimated; this index is not an automatic batch scheduler.

The command rejects changed/missing/conflicting source hashes, stale configuration
snapshots and stale guide-use fingerprints. It retains source blockers, unmentioned
catalog entries and unresolved identities without adding requirements, tiers,
prices or no-use dispositions. No raw extraction or network collection occurs.

Red: missing dossier module. Green: seven new behavioral tests; all 97 maintenance
tests pass, Ruff/format and git diff --check pass. Actual corpus index and expanded
Insight/Spirit dossiers generated offline. Evidence: tmp/dossier-red.txt,
tmp/dossier-maintenance-tests.txt, tmp/dossier-generation.txt,
tmp/insight-review-dossier.json and tmp/spirit-review-dossier.json. This is a
maintenance-only addition; runtime generation and report/price behavior unchanged.

Current index diagnostics: 808 identity buckets have no occurrences; 2,558 have no
source-linked configuration; 1,384 buckets remain unresolved. These are different
dimensions, not sums or assertions of no demand. Only 20 identities have explicit
named guide-use review records. Spirit has 1,027 cached occurrences but no named
review or source-linked configuration. Occurrence count is not endorsement breadth.

Next: inspect Spirit dossiers across player/mercenary, sword/shield, progression
and build contexts; review reusable complete-use requirements before publishing
new guide-demand votes. Use existing extraction and native legality. Do not merely
resume the 13-role stat-priority tail as though it covers the full guide corpus.
The tail remains required, as do all-item tiers, leveling, base/roll/report and
scoped market gates. GUIDE_FIRST G1 semantic completeness remains unproven.

## Spirit Starter demand and separate sword/shield rules — 2026-09-25

First full-census-led demand batch after the dossier checkpoint: four reviewed
Starter uses from cached wp-a-builds variants. Blizzard, Lightning and Fissure
Crystal Swords remain distinct from Lightning's Monarch. Exact named completed
recipe, four filled sockets, base, quality and player class are required. Lightning
retains its source-backed117% total-loadout FCR dependency;25% item FCR is accepted
when that loadout condition is satisfied. No planner maximum becomes a minimum,
and no other sword/shield base inherits reviewed fit. Ethereal is not a universal
caster exclusion; equipment/repairability remain explicit conditions.

Captured all-skills/FCR receive desirable markers; FHR/mana/vitality supporting.
Only the shield configuration annotates captured cold/lightning/poison resistance.
No missing bonus, spell benefit from weapon damage/leech, perfect-roll judgement or
price is inferred. Four uses produce three distinct recommending builds, Pending
with Med lower-bound breadth. The saved Monarch has one conditional Lightning use,
not confirmed fit for all three identity-level builds.

Red: four missing role configurations and missing Spirit demand. Green: focused
cases pass. Broader assessment run:1,758passed and one old magic-jewel selector
failure (it selected the unique Facet configuration added earlier). Restricted that
fixture to magic quality;10targeted jewel/Facet/Spirit tests pass. Ruff and diff checks
pass. All18saved price estimates unchanged; only Spirit report text changes.
Published18texts/prices match staging. Generation
c6676007479c3fe6cf961d57d06894cff35b95f14619f9442af54f0eca37b1ec.
299roles/278stat configurations; use-quality stat states347reviewed/8excluded/17pending.
Census, base matrix, independent coverage matrix and dossier index refreshed offline.
Evidence tmp/spirit-starter-*, tmp/spirit-assessment-tests.txt, tmp/spirit-before.json,
tmp/spirit-staged.json and tmp/spirit-published.json. Data-only runtime update.

Next demand batch: Paladin Spirit shield configurations, separating Starter Targe,
endgame Sacred Targe, native resistance alternatives and swap companions. Then
reserve the scheduled specialist/leveling tail. Blizzard full-Tal's Spirit remains
set-dependent; Double Throw dual-Spirit swap has prose/planner conflict and must not
be promoted from planner counts. Other Spirit variants,13previous named stat cases,
all-item tiers/leveling and scoped price gaps remain pending. No completion claim.

## Paladin Spirit main-loadout configurations — 2026-09-25

Second census-led demand batch: six source-reviewed uses. Hammerdin Starter sword
and Targe; FoH/Holy Bolt Starter Targes; Hammerdin Standard/MF Sacred Targes.
Native base codes/types verified. Standard keeps Sling/Hellwarden's Will; MF keeps
Void/Sling/Arachnid Mesh on the player, with125%totalFCR required in both. Missing
context remains conditional. No swap use, other shield base, perfect resistance
minimum or perfect FCR minimum is inferred. Ethereal/equip/repair constraints remain
conditional rather than a universal exclusion. Starter variants need no invented
endgame breakpoint. Captured fire resistance joins the supporting shield stats;
no absent stat or perfect inherent roll is inferred from a captured total.

Six uses add two distinct builds: Spirit now Pending with High lower-bound breadth
from five builds. Holy Bolt/FoH and Hammerdin hands/variants do not inflate counts.
Saved Monarch keeps its single conditional Lightning fit; Paladin base rules do not
apply to it. All18prices unchanged; only the Spirit identity-demand heading changes.

Red: six missing roles and missing demand votes (after correcting a test import typo).
Green:366affected role/maintenance/stat-bundle/publication tests pass. Ruff/format and
diff checks pass. Native/domain fixtures verify Paladin bases; no Paladin shield
capture is claimed. All18published report texts/prices match staging. Generation
ab4ec7062ac346c304ca38d28e9fa4eaef744825aed28882cdf18cbc11f3c34d.
305roles/284stat configurations; use-quality states359reviewed/8excluded/17pending.
Census, base/coverage matrices and dossiers refreshed offline. Evidence
 tmp/spirit-paladin-red.txt, tmp/spirit-paladin-green.txt and tmp/paladin-spirit-*.
Data-only runtime update; no new market prices.

Two demand batches complete. Next scheduled leveling/specialist tail: six Fissure
Starter mercenary armor/helmet alternatives. Keep native leech/resistance/proc
semantics distinct and avoid claiming active Fade or a full surviving loadout.
Remaining Spirit swaps, full-set uses and planner conflicts stay pending alongside
all-item tier/leveling/source/base/roll/report/market closure.

## Scheduled Starter mercenary survival tail — 2026-09-25

Six Fissure Starter alternatives now have explicit stat reviews and named guide
alternative endorsements: Rockstopper, Undead Crown, Duriel's Shell, Bulwark, Smoke
and Treachery. Native modifiers distinguish leech, resistances, physical reduction,
CBF, life-per-level and recovery. Treachery IAS and the exact skill267/level15 struck
Fade trigger are desirable; Venom is not a substitute and active Fade is never
asserted. Native decoder confirms key201:17103 as5%level15Fade when struck. Captured
rune recovery/resistance bonuses remain supporting, not synthesized. No automatic
EDef premium or player skill transfer from mercenary equipment.

Added explicit mercenary-compatible types and identified status. Runeword recipe/
filled sockets remain mandatory; normal/superior and ethereal/nonethereal/unknown
cases retain existing policy. Only Bulwark/Treachery preserve planner ethereal
preferences. Complete mercenary equip/survival remains conditional, without a
fabricated mercenary subtype or mandatory companion setup. Lower native rolls
remain candidates. Six source-backed alternatives add demand without claiming
universal tier/price coverage.

Red: six missing configurations. Green:370affected role/maintenance/stat tests;
Ruff/format/diff pass. Domain fixtures verify new items (none in saved capture set).
All18saved report texts and prices unchanged, and published output matches staging.
Generation9cdc430a9ac9a074ad2669352cc7c805f5764c2e2a960534ad37834a2752995e.
305roles/290stat configurations;368reviewed/8excluded/8pending use-quality stat rows.
Census, base/coverage matrices and dossiers refreshed offline. Evidence
 tmp/starter-merc-*. Data-only runtime update. Scheduled tail complete.

Next demand work: Blizzard full-set Spirit with actual Tal Rasha piece dependencies
and source-backed total breakpoints. Other Spirit swaps/planner conflicts remain
pending. Seven existing named stat cases remain: smite-shared-treachery,
echoing-ubers-hellwarden, dragon-talon-budget-guillaume/goblin-toe/hexfire-merc/
ormus-merc/lidless-merc. This finite list is not the full guide/all-item denominator;
all required source, tier, leveling, base/roll/report and market gates remain open.

## Blizzard full-set Spirit and explicit FHR context — 2026-09-25

First demand batch after the Starter mercenary tail: active full-Tal-Rasha Spirit
Monarch. All five named pieces must be on the player;105%totalFCR and86%totalFHR
are explicit dependencies. Added optional player_total_fhr to AssessmentContext,
using the same strict nonnegative integer validation as FCR. Missing/malformed
values remain unknown. Hovered item recovery cannot supply the total. Kept Spirit
caster/stat priorities behind the full combination without adding perfect-roll
minimums. Swap use and farming every monster remain separate.

Source discrepancy retained: prose requests additional6FHR, whereas the cached
planner lists one5FHR charm. Neither planner text nor inferred gear sums establishes
the stated86total; the actual total must be supplied. Blizzard Starter/Set variants
remain one demand vote. Saved Monarch now has separate conditional Lightning
Starter and Blizzard full-set uses; identity breadth stays at five builds.

Red: missing FHR context support and missing full-set role. Green:22focused checks;
full suite3,109passed/3skipped in212.12s. Ruff/format/diff checks pass. All18prices
unchanged; only Spirit report text changes. Published18texts/prices match staging.
Generation7c6d26428b7de09c901cfdc6c405e0c770386986fd2a3c9d63d4f678e1760125.
306roles/291stat configurations;370reviewed/8excluded/8pending use-quality stat rows.
Coverage/census/dossiers refreshed offline. Evidence tmp/blizzard-set-*.
Restart the worker for the Python context change; no live market collection.

Next demand batch: remaining source-backed active Spirit shield variants across
caster builds, retaining loadout/variant differences and separating swaps. Then
schedule a specialist/leveling tail. Seven old named stat cases, full named tiers,
all-item guide semantics and scoped market/report/base/roll coverage remain open.

## Meteor Spirit variants and accurate preference heading — 2026-09-25

Second demand batch after the Starter mercenary tail: three Meteor active Monarch
uses. Standard accepts 63% FCR and 60% FHR with Oculus OR Eschuta; exposing 105% FCR
as an optional higher target is a reviewed presentation choice. MF preserves
Oculus plus the three Tal armor/belt/amulet pieces and 105% FCR / 60% FHR. Full-set
preserves all five pieces and 105% FCR / 86% FHR. All totals are actual loadout facts;
no perfect item minimum or swap fit inferred. Captured native skill/cast/recovery/
resource/resistance priorities remain conditional on these combinations.

All three variants add one recommending build: Spirit has six reviewed builds,
still Pending/High lower-bound demand. The maintenance configuration grouper reuses
the identical Blizzard/Meteor full-set rule while retaining both source records.
The saved Monarch has three conditional builds over five uses, within the compact
report budget. A known 63% Standard context exposed the inaccurate "Better rolls"
heading for a loadout target; compact presentation now says "Targets". Matching
and price semantics are unchanged. Detailed preferences retain their labels/status.

Red: three missing configurations; separately, loadout target heading regression.
Green: 368 role/maintenance/stat checks and 123 appraisal/report checks pass.
Ruff/format/diff pass. All 18 saved prices unchanged. Spirit report gains Meteor
uses; Insight changes only the heading (verified exact replacement). Published
texts/prices match staging for all 18 captures. Generation
 d651ca248a933a2e419bb970db47bd595b0ae20c9914b770e26df1a74e66593e.
309 roles / 294 stat configs; use-quality states 376 reviewed / 8 excluded / 8 pending.
Census, base/coverage matrices and dossiers refreshed offline. Evidence
 tmp/meteor-spirit-*, tmp/meteor-target-heading-red.txt, tmp/meteor-report-tests.txt.
Restart worker for the compact-heading Python change (and prior FHR support if not
already restarted). No new market collection or numerical estimates.

Two demand batches complete. Next scheduled specialist tail: five Dragon Talon
Budget player/mercenary cases, preserving wearer, socket payload and skill semantics.
Remaining active Spirit variants and swap provenance, two other old named stat
cases, all named tiers/leveling and broad all-item evidence gates remain pending.

## Dragon Talon Budget specialist stat reviews — 2026-09-25

Scheduled tail adds five native stat configurations and source-bound named-use
reviews. Guillaume's Face prioritizes Crushing Blow and its same-jewel IAS/lightning
resistance, with recovery/strength supporting. Goblin Toe marks Crushing Blow only
under the existing elite-upgrade/nonethereal setup gate. Fire Iron Wolf Hexfire
marks fire skills; Lidless marks all skills; Ormus marks fire skill damage. Captured
socket fire damage supports the Enchant damage component; wearer fire pierce, weapon
physical damage, Deadly Strike and mana properties do not acquire these priorities.
No claim that the mercenary survives Ubers or that a prebuff is active.

Added explicit types/identified facts required by the stat compiler. All existing
same-child jewel, Fire Facet, mercenary type, upgrade and wearer restrictions remain.
Parent totals cannot substitute for socket evidence, and missing observed modifiers
are not synthesized. Other uncertain/native skill variants remain unreviewed rather
than receiving an automatic positive score. No trade price or defense premium added.

Red: five missing configurations. Green: 11 initial focused checks; broader run had
372 passes and one outdated "Better rolls" assertion from the previous heading
change. Updated that assertion to "Targets" while preserving its concrete Lightning
Sentry target and lower-candidate test; 16 targeted checks pass. Ruff/format/diff pass.
All 18 saved texts/prices unchanged; published output matches staging. New named
items use domain fixtures, not new live captures. Generation
77111bf336761475719c3a87eeff15194d442561d2d10c7e757d03fca17b8c85.
309 roles / 299 stat configs; 381 reviewed / 8 excluded / 3 pending stat-use rows.
Coverage/census/dossiers refreshed offline. Evidence tmp/dragon-talon-stats-*.
This update changes runtime data only; earlier report/context Python changes still
require a worker restart if not already done. Scheduled tail complete.

Next demand candidate: Call to Arms prebuff uses, reusing cached source and existing
base-policy evidence to broaden identity coverage beyond Spirit. Preserve native
skill rolls, actual base/equip and swap conditions; planner mentions alone cannot
vote. Remaining active Spirit variants/swaps stay pending. The old named stat tail
now has smite-shared-treachery and echoing-ubers-hellwarden (three quality rows).
Full inventory/source, named tiers, leveling, base/roll/report and market coverage
remain separate unfinished gates; this finite role queue is not all-item closure.

## Call to Arms prebuff and separate swap-equipment context — 2026-09-25

First demand batch after Dragon Talon tail: seven explicit Sorceress Crystal Sword
prebuff uses across Blizzard MF/Set, Meteor Standard/MF/Set and Lightning Standard/MF.
Both native shouts are required (Battle Orders >=1, Battle Command >=2), with BO6
as a useful maximum-roll target, not an entry requirement. Observed shout/all-skill
bonuses are annotated; damage, IAS and Battle Cry receive no prebuff priority.
Normal/superior and all ethereal states remain candidates; no price premium inferred.
Seven uses reduce to four semantic configurations, retaining every source. Three
recommending builds produce Pending/Med lower-bound identity demand.

Added player_swap_items to typed context and one shared collection-field registry
for normalization, membership, counts and equality rejection. Main-set and mercenary
Spirit possession cannot prove the source-specific swap pairing. Missing/malformed
swap evidence remains unknown; explicit empty lists prove absence; copied sequences
preserve counts, sets establish membership only. Five roles require Spirit on swap.
The two MF roles assess the weapon's prebuff function; their four-Ist loot shield
is separate evidence, not a dependency enabling the shouts. Exact Crystal Sword,
completed five-socket recipe and Sorceress context remain mandatory. Equipment and
cast sequence remain conditional; no active buff/full buff level asserted.

Red: missing roles and unsupported swap field, including the predicate validator's
old collection allowlist. Green: 19 focused tests; full suite 3,125 passed / 3 skipped
in 202.50s. Ruff/format/diff checks pass. No saved CTA capture: new behavior uses
fixtures. All 18 existing report texts/prices unchanged; published output matches
staging. Generation
2fab2778e70f6a17c1f53920309fc139ebbcbbceb3a62e9b76db612b6d494cfa.
316 roles / 306 stat configs; use-quality states 395 reviewed / 8 excluded / 3 pending.
Census, base/coverage matrices and dossiers refreshed offline. Evidence tmp/cta-prebuff-*.
Restart worker for context/predicate Python changes. No live collection or new prices.

Next demand work: review other class-specific CTA uses, especially Warlock and
Paladin bases/staffmods, preserving actual swap partners and native skill identities.
Do not copy Sorceress rules to Barbarian oskill semantics. Then schedule a specialist
or leveling tail. Existing two named stat gaps and broad source/tier/leveling/base/
roll/report/market coverage remain unfinished; current role coverage is not closure.

## Warlock Call to Arms reusable prebuff batch — 2026-09-25

Nine explicit cached uses: Echoing Strike Standard/MF/Ubers, Abyss Standard/MF,
Mirrored Blades Standard/Ubers and Fire Standard/MF. Reused the reviewed CTA template
with Warlock context, exact Crystal Sword, five filled sockets, both native shouts
and actual Spirit swap membership. Main-set/mercenary Spirit is insufficient.
Minimum native rolls qualify; BO6 remains a target. Ethereal examples do not become
universal requirements or price premiums. Other prebuffs retained in source excerpts
are not weapon requirements. No new runtime engine or raw extraction.

Four newly reviewed recommending builds bring CTA to seven (Pending/High lower
bound). Nine source uses share mechanics; all dates/locators/quotes remain linked.
325 roles / 315 stat configs. Stat-use rows: 413 reviewed / 8 excluded / 3 pending.
Red: 16 failures (nine missing rules and updated breadth expectations). Green:
384 affected role/maintenance/stat tests in 81.14s, Ruff/format/diff checks passed.
All 18 saved texts and prices unchanged; published/staged parity verified. New CTA
behavior uses domain fixtures; there is no saved live CTA capture. Publication:
e192f5286e451cc1d28d84c16a813a55c3a2c1d7248098f930bc92a7fbf54d41.
Census, dossiers and coverage matrices refreshed; evidence tmp/warlock-cta-*.
No new market estimates or collection. This batch changes runtime data only;
previous Python changes still require worker restart if not already performed.

Two demand batches complete: next reserve the specialist/leveling tail. Existing
named stat gaps: smite-shared-treachery and echoing-ubers-hellwarden (three quality
rows); inspect cached evidence before selecting their reviewed semantics. Remaining
CTA classes/bases, Spirit variants, full named tiers/leveling, base desirability and
market coverage remain pending. This finite role queue is not all-item completion.

## Specialist tail: shared Treachery and Uber Hellwarden — 2026-09-25

Reviewed two existing source-backed roles using cached variant excerpts. Shared
nonethereal Treachery marks Fade proc and wearer IAS, with recovery/cold resistance
supporting. It retains the Act 2 Might dependency and player equip caveat; wearing
or owning it never proves active Fade, and armor modifiers do not transfer after
swapping. Hellwarden marks native magic pierce/skills and speed contribution under
Warlock + Sling + Renewed Black Cleft + Guardian's Light socket requirements.
Defense receives no inferred roll premium. Full breakpoint, survival and bound-demon
state remain outside item proof. Added identified guards and explicit stat reviews;
no new evaluator or online research. Existing source dates and hashes preserved.

Two missing configurations reproduced red; six focused tests then 388 affected
role/maintenance/stat tests pass (53.22s). Ruff/format/diff pass. All 18 saved reports
and prices unchanged, with published/staged parity. These two items use domain
fixtures rather than new live captures. Publication:
6eb2a31acb70a9835b9770990350f218e73b81d8326ba54693053a1219edc65f.
325 roles / 317 stat configs. Current use-quality stat queue: 416 reviewed / 8
excluded / zero pending. This closes only the existing role stat queue, NOT the
full-inventory denominator. Census, dossiers, base/coverage matrices refreshed.
Evidence: tmp/specialist-tail-*. Runtime data only; earlier Python changes still
need worker restart if not already done. No market estimates added.

Scheduled specialist tail complete. Next use the full review dossiers to choose
reusable demand configurations, considering new identity coverage and review effort
alongside build count. Remaining CTA classes/bases, active Spirit variants,
base desirability, named tiers and leveling, unresolved identities and scoped market
coverage remain separate unfinished gates. Do not interpret the closed stat queue
as completion of guide or all-item assessment coverage.

## Annihilus inventory support template — 2026-09-25

First demand batch after the specialist tail. Full-census inspection found
Annihilus across 33 build labels outside discovery-only occurrences, with zero
reviewed named-use profiles. That discovery count is not endorsed demand. Reviewed
ten explicit softcore gear-list uses: Blizzard Standard/MF/Set, Meteor
Standard/MF/Set/Ubers, Lightning Standard/MF/Ubers. Reused one predicate pattern:
identified unique Small Charm, exact Annihilus identity and Sorceress context.
Native all skills is desirable; observed attributes, resistances and experience
support the wearer/progression. No planner maximum is a required minimum. No
missing stat synthesis, MF priority, duplicate stacking, active inventory location,
full-loadout success or numerical price is inferred. Active inventory/level
requirements remain explicit conditions. No raw extraction or new runtime code.

Adds one previously unreviewed named identity, ten source uses, three distinct
recommending builds (Pending/Med lower bound). Chosen for broad discovery and low
predicate novelty versus further same-identity CTA expansion; review effort was
not prospectively timed, so no speedup claim. Source dates/hashes/locators retained.
Native ranges verified in bundled metadata: attributes/resists 10–20, experience
5–10, all skills1. Tests use minimum rolls and missing/wrong-identity/context cases.

Red: ten missing roles. Green: 12 focused checks, then 394 affected tests in55.64s.
Ruff/format/diff pass. All18 saved reports/prices unchanged; published/staged parity
verified. Annihilus uses synthetic domain fixtures, not a saved live capture.
Publication2530e5416404caa75a35b86761218ae2e44358b91c689454c8ce3eef8b3dac6c.
335roles /327stat configs;426reviewed /8excluded stat-use rows. Census, dossiers,
base/coverage matrices refreshed. Evidence tmp/annihilus-*. Runtime data only;
prior Python changes still require restart if not yet done. No market collection.

Next demand batch should broaden another unreviewed named identity or affixed
family from the full census, then reserve a specialist/leveling batch. Remaining
Annihilus builds, all named tiers/leveling, base rules and scoped market evidence
remain independent unfinished gates. Discovery/build-label counts never substitute
for reviewed endorsement or exact pricing.

## Full-census review queues — 2026-09-25

Found a planning bias: dossiers sorted by already-reviewed demand, favoring repeated
expansion over new identities. Added independent review_leads (verified candidate
build labels plus exact occurrence IDs) and five disjoint queues. New named items
are separate from existing-use expansion; bases/patterns, unresolved identities
and no-verified-guide-lead cases stay visible. Duplicate source occurrences from
one build count once. Historical/discovery-only/shared-planner/Hardcore/unverified
records remain retained but cannot increase candidate breadth. No new endorsement,
trade tier, price or runtime rule follows from this ordering.

Red: two missing review-lead/queue behavior tests. Green: 9 dossier tests and all99
maintenance tests (2.07s), Ruff/format/diff. Rebuilt the offline dossier index and
verified every one of2739 identities appears exactly once:247 new named candidates,
32 named expansion,44 bases/patterns,1384 unresolved,1032 no verified guide leads.
Leading new candidates include Duress, Tal Rasha's Horadric Crest, Arachnid Mesh,
Temper, Chains of Honor, Goldwrap, Shaftstop and War Traveler. Their review-lead
counts are NOT reviewed demand. Full occurrences and source blockers remain intact.
Evidence tmp/review-queues-*. Maintenance-only code; no runtime publication or
worker restart needed. Existing published assessment/price behavior remains unchanged.

Annihilus was the first demand batch after the tail. The next actual demand batch
should choose one of the new-identity/family candidates by source complexity and
coverage gained, then schedule specialist/leveling work. This maintenance change
does not consume a demand batch. All-item tiers, leveling, unresolved identities,
base desirability and scoped market evidence remain unfinished.

## Arachnid Mesh Standard caster uses — 2026-09-25

Second demand batch after the specialist tail. Selected a new named identity from
the full-census queue, with three explicit Standard gear-list uses and three known
breakpoint configurations: Blizzard105 total FCR, Meteor63 FCR/60FHR (105FCR optional),
Lightning117FCR. Exact unique Spiderweb Sash identity and identified Sorceress use
required. Captured skills/cast rate are desirable; maximum mana supporting. Defense
and slows-target receive no caster priority; no ethereal premium or numerical price.
Character totals require typed context; the belt's own FCR cannot prove them.
Equip/full setup remain advisory. Native fixed stats and base verified in metadata.

Adds one named identity and three reviewed recommending builds (Pending/Med lower
bound). Existing interpreter reused, no raw extraction or new runtime code.
Lightning Ubers remains pending: Arachnid/Thundergod belt swapping is encounter
specific and cannot inherit Standard fit. Other classes/variants stay unreviewed.
Red:3 missing roles. Green:5 focused checks and389 affected checks in54.64s;
Ruff/format/diff pass. All18 saved reports/prices unchanged, published/staged parity.
New belt behavior uses domain fixtures, not live captures. Publication:
e08131c348792f2cd91b984c0dc4a0a850d8f06d5c026929fc1411d800e604b6.
338roles /330stat configs;429 reviewed /8excluded stat-use rows. Census/dossiers and
base/coverage matrices refreshed. Evidence tmp/arachnid-*. Runtime data only;
previous Python changes still need restart if not already done. No live collection.

Two demand batches complete (Annihilus, Arachnid): reserve specialist/leveling work
next. Choose a new leveling/specialist identity from the full denominator, not only
existing role gaps. Remaining named tiers/leveling, base desirability, unresolved
patterns and scoped market prices remain separate incomplete requirements.

## Amazon leveling essentials and guide-only recommendations — 2026-09-25

Scheduled leveling tail adds five reviewed optional Amazon uses from exact cached
Essentials locators: Death's Hand/Guard (paired), Hsarus' Iron Heel, Sander's Riprap,
and Twitchthroe. Sources remain dated to the cached guide; review dated today.
Twitchthroe exposed an adapter gap: guide advice previously required a preexisting
transcript recommendation. Added explicit GUIDE_ONLY_BENEFITS keyed by class/item,
still requiring the exact reviewed locator and unambiguous item-facts identity.
No transcript/all-class endorsement is synthesized. Twitchthroe receives qualitative
high leveling priority for IAS, recovery and shield blocking, with equip and full
setup conditions. This is not a trade tier or numerical estimate.

Red: missing five explicit guide rows; intermediate test exposed Twitchthroe's
missing transcript seed. Index validation rejected an unsupported 'attack' archetype;
corrected to existing 'general' while retaining attack-specific benefit text.
Interrupted the affected regression run, rebuilt recommendations and SQLite, then
reran. Green:277 initial policy/adapter tests, final2349 passed/2 skipped in211.32s.
New runtime fixture confirms Twitchthroe remains useful when level requirements are
unmet and retains shield condition. Ruff/format/diff pass. All18 saved report texts
and prices unchanged; published output matches staging. No saved Twitchthroe live
capture. Generation 9b5158f376c96a9c84feb48ac2c8669ec8948632fa80785b6130de976e2dbb11.
Census, review dossiers and coverage matrix refreshed. Evidence tmp/amazon-leveling-*.
Maintenance adapter change only; new runtime data loads at request boundaries, no
additional worker restart required beyond earlier pending Python changes.

Leveling tail complete. Next choose demand/family work from the full review queues.
Other Amazon essentials (Titan's Revenge requirements/IAS tradeoff, Cow King set,
runewords, jewels and amulets), other class leveling guides, full named tiers,
base desirability and scoped prices remain incomplete. Current reviewed rows do
not close the all-item denominator. No live collection or new market estimates.

## War Traveler and Chance Guards farming components — 2026-09-25

First demand batch after Amazon leveling tail. Two new named identities, six explicit
MF variant uses across Blizzard/Meteor/Lightning. Each identity has three reviewed
builds (Pending/Med lower bound). Preserve player three-piece Tal Rasha membership,
105FCR for Blizzard/Meteor,117FCR for Lightning and60FHR for Meteor. Unknown character
totals or mercenary possession cannot satisfy these dependencies. Native minimum MF
qualifies (War Traveler30, Chance Guards25);50/40 maxima remain optional targets.
Boot movement/strength/vitality supporting; physical attack, defense and gold rolls
receive no spell-farming priority. Upgraded Chance Guards remain valid subject to
equip requirements; the planner Vambraces example is not an upgrade requirement.
No universal ethereal premium, whole-loadout success or numerical price inferred.

Red:6 missing rules. Green:8 focused checks then392 affected checks in56.74s.
Ruff/format/diff pass. All18 saved report texts/prices unchanged; published/staged
parity verified. New items use domain fixtures, not saved live captures. Generation
235d4b92d5a3dd7340239acf8c6c0d363071355889b3ba7f32c5da231af467d8.
344roles /336stat configs;435reviewed /8excluded stat-use rows. Census, dossiers,
base/coverage matrices refreshed. Evidence tmp/farming-gear-*. Runtime data only.
No network collection or new market estimate. Earlier Python restart requirement
remains if not already handled.

Next demand batch can cover another full-queue family/identity, then reserve the
specialist/leveling tail. Remaining classes/variants, trade tiers, leveling, base
rules and scoped market evidence remain incomplete; new guide votes do not close
these independent dimensions or imply prices.

## Quality-specific farming ring combinations — 2026-09-25

Second demand batch after Amazon leveling tail. Meteor MF rare ring requires10FCR
and positive MF together on this item, with observed life/resistances supporting.
Lightning MF magic ring requires positive MF; the source40MF is a target rather
than a minimum. This is a reviewed functional candidate threshold, not a claim of
exact Fortuitous/of Fortune affix identity. Lightning ring FCR is not required when
117 character FCR is independently established; Meteor retains105FCR/60FHR.
Both retain player three-piece Tal Rasha dependencies. Missing affixes cannot be
borrowed across items, rarity is exact, and planner maxima remain preferences.
No complete two-ring loadout or exact price inferred. Pattern guide-use reviews
remain distinct from named-identity breadth; existing ring combinations unchanged.

Red:2 missing configurations. Green:5 focused checks then389 affected tests in59.42s.
Ruff/format/diff pass. All18 saved reports/prices unchanged; published/staged parity.
New combinations use domain fixtures rather than live captures. Generation
d1163ecb36fdd4b226422de91135c5d144b0ef91f8fb3e4236ba2f7b7bb01bf4.
346roles /338stat configs;437reviewed /8excluded stat-use rows. Census/dossiers and
base/coverage matrices refreshed. Evidence tmp/farming-rings-*. Runtime data only;
no new market collection or numerical estimate.

Two demand batches complete: reserve specialist/leveling work next. Existing role
queue coverage does not resolve all bases, rare/magic combinations, named tiers,
leveling or scoped market evidence. Full identity/configuration denominator remains
the completion criterion.

## Leveling guide source binding — 2026-09-25

Maintenance correctness audit during the scheduled specialist/leveling turn found
that exact guide locators could produce explicit recommendations despite missing
or changed source metadata. Bound all four reviewed leveling guides (Amazon,
Sorceress, Necromancer, Warlock) to pinned cached SHA256 snapshots. Missing, ambiguous
or changed source records now yield a reasoned guide-review gap, not advice. This
applies to both transcript-backed and guide-only recommendations. Unreviewed guide
mentions remain ineligible. Updating a source hash requires a new excerpt review.

Red: missing/changed source cases incorrectly accepted Twitchthroe. Added duplicate
source case and updated positive source fixtures to carry reviewed hashes. Green:
380 recommendation/policy/maintenance checks pass in3.88s; Ruff/format/diff pass.
Independently verified all four actual cached guide files against their pinned
hashes. Offline recommendation rebuild is byte-identical to the prior artifact,
so no index rebuild or runtime publication is needed; existing reports/prices and
selected generation remain unchanged. Evidence tmp/leveling-source-*.
No worker restart for this maintenance-only change.

This is source-integrity work, not new leveling coverage. The scheduled specialist/
leveling expansion still remains next; do not count this as a completed tail batch.
Full named tiers/leveling, base desirability, affixed combinations and scoped market
coverage remain unfinished. Do not claim all-item completion from existing role
or stat-configuration counts.

## Titan's Revenge source-specific leveling tradeoffs — 2026-09-25

Scheduled leveling tail adds explicit Amazon Essentials recommendation for Titan's
Revenge at exact locator item106@(78,2053), retaining the pinned source snapshot.
High qualitative leveling value preserves early dexterity-versus-vitality cost
and replacing attack speed lost from the prior weapon. Runtime fixture checks
level42/dexterity109 from verified ordinary-base facts, unmet level41, and unknown
variant requirements for ethereal. No trade tier or numerical price is inferred.

Integration test exposed an adapter inheritance bug: the existing transcript row
was copied ahead of explicit guide-specific benefits, dropping conditions. Renamed
GUIDE_ONLY_BENEFITS to GUIDE_BENEFITS and made explicit class/item reviews override
transcript defaults. Both recommendations retain their own source/reason/conditions;
no synthetic transcript advice or changed transcript scope. Missing/ambiguous
identity and source snapshot guards remain. Existing transcript utility still exists.

Red: missing guide-only fixture; runtime fixture then caught copied defaults and
source deduplication. Green:382 recommendation/policy/maintenance tests in4.05s,
Ruff/diff pass. All18 saved report texts/prices unchanged; published/staged parity.
Titan's uses domain fixtures, not a saved live capture. Rebuilt recommendations and
SQLite before publication; census/dossiers/coverage matrix refreshed. Evidence
rows316→317; role/stat counts unchanged. Generation
2c9879f08f5528ad27df7e7030f98faf661018e2807a85fd12413f1fc35d2fd6.
Evidence tmp/titan-leveling-*. Maintenance adapter change and runtime data only;
no new worker restart required, no live collection or market estimate added.

Scheduled leveling tail complete. Next resume demand/family work from the full
queues. Other class-specific leveling, named tiers, base desirability, unresolved
magic/rare combinations and scoped pricing remain incomplete. This update does
not make all Titan's variants priced or fully assessed.

## Gheed's Fortune inventory utility across cached builds — 2026-09-25

First demand batch after Titan leveling tail. Reviewed all43 explicit positive
player Charms labels beginning Gheed's Fortune in non-hardcore, non-planner-only
cached variants (23distinct builds). Shared applicability: identified unique Grand
Charm with exact identity; active inventory/level/space remain advisory. Native MF,
gold and vendor discount are useful at minimum rolls; gold-find variants prioritize
gold, other variants mark it supporting.40MF/160gold optional targets, not minima.
No class-specific combat or loadout claim; this is intrinsic farming utility only.
Summoner Damage/Ubers retains its explicit inventory entry but gains no boss-damage
claim. Echoing Ubers replacement prose cannot create a positive Gheed's use.

Two priority variants reuse one applicability predicate; source membership retained
in43 role/review IDs and tmp/gheeds-membership.json. Native ranges verified in bundled
metadata:20–40MF,80–160gold,10–15vendor discount. Demand Pending/High lower bound23.
No duplicate-build inflation, active inventory state, duplicate stacking, gambling
profit or market price inferred. No raw re-extraction or new runtime evaluator.
Red:2 representative missing-branch tests. Green:4 focused then388 affected tests
in64.43s; Ruff/format/diff pass. Full compiled membership and source fingerprints
validated. All18 saved texts/prices unchanged, published/staged parity. Gheed's
itself uses domain fixtures, not a saved live capture. Publication:
02bd71fcab70033615da7fbae2e2a22b32740d3fa3e50f20495c311cad9ed41a.
389roles /381stat configs;480reviewed /8excluded stat-use rows. Census/dossiers and
base/coverage matrices refreshed. Evidence tmp/gheeds-*. Runtime data only; no live
collection or price estimates added. No new worker restart requirement.

One demand batch complete. Next choose another reusable family/identity from the
full queues, then reserve specialist/leveling work. Full named tiers, other guide
uses, base desirability, affix configurations and scoped market evidence remain
independent unfinished requirements; reviewed role queue is not all-item closure.

## Annihilus shared template across remaining explicit uses — 2026-09-25

Second demand batch after Titan leveling tail. Reviewed remaining48 exact positive
Annihilus player Charms entries in non-hardcore/non-planner-only cached variants,
reusing10 prior Sorceress uses.58 total uses across26 builds, all eight classes.
Class context, identified unique Small Charm and native-stat priorities preserved;
no planner maximum minima. Source dates/locators and exact membership retained.
Inventory activation/level caveat remains; role is charm support, not full build fit
or duplicate stacking. No new runtime interpreter, raw extraction or price inference.
Demand is Pending/High lower bound26, not completion of the full source denominator.

Red: updated breadth plus missing class-specific roles. Green:19 focused tests,
403 affected tests in76.98s. Every class has positive/wrong-class and missing-stat
fixtures; full compiled58-use membership and exclusion of Hardcore validated.
Ruff/format/diff pass. All18 saved report texts/prices unchanged; published/staged
parity. Annihilus uses domain fixtures, not saved live captures. Generation:
67d3e8366a4fdac4a1ac61a6d0a27916b1928e85f22501b651999cb6b6769876.
437roles /429stat configs;528reviewed /8excluded stat-use rows. Census/dossiers and
base/coverage matrices refreshed. Evidence tmp/annihilus-expansion-*, including
explicit new membership. Runtime data only; no new worker restart requirement.
No market collection or numerical estimate added.

Two demand batches complete (Gheed's, Annihilus). Reserve specialist/leveling work
next. Named trade tiers, remaining guide configurations, base desirability,
unresolved affix combinations and scoped market evidence remain separate unfinished
requirements. Do not infer all-item closure from the now-expanded stat queue.

## Cow King set combination in Amazon leveling — 2026-09-25

Scheduled specialist/leveling tail adds three explicit optional guide recommendations
at Amazon Essentials locators112/113/114: Cow King's Hooves, Hide and Horns. Shared
benefit template preserves all three pieces, Death's Hand/Guard and Ancient's Pledge.
Combined attack-speed/resistance benefits are not assigned to a single piece.
Qualitative priority3/med is an optional-combination design choice, not a trade tier.
Existing standalone Hooves transcript utility remains separate. Hide/Horns now gain
reviewed guide-specific use without changing the transcript's earlier review gaps.

GUIDE_PRIORITY provides explicit per-guide overrides rather than automatically
assigning high priority to every guide-specific benefit. All advice remains
conditional; each piece's own requirements are not full-combination equip proof.
Runtime fixtures verify native levels13/18/25, conditional status, identified facts
and rejection of ethereal set items. Source hashes, exact locators and identity
validation retained. No set-bonus stat synthesis or automatic complete-loadout claim.

Red: missing three guide recommendations. Green:384 recommendation/policy/maintenance
checks in4.42s, Ruff/format/diff pass. All18 saved reports/prices unchanged, published
output matches staging. New cases use domain fixtures rather than live captures.
Rebuilt recommendations/SQLite and refreshed census/dossiers/coverage. Evidence
rows317→320, role/stat counts unchanged. Generation:
ce9eff5e573da9e8331c52789722f91584bcf2f0b45e2c78a525a414bd506b7a.
Evidence tmp/cow-leveling-*. Maintenance adapter/data only; no additional worker
restart. No market collection or numerical price added.

Scheduled tail complete. Next resume demand/family work from full queues. Remaining
named tiers, class leveling, base desirability, affix combinations and scoped market
evidence remain independent unfinished requirements; partial-set recommendation
coverage does not close all item assessment or pricing.

## Tal Rasha helm mercenary configurations — 2026-09-25

First demand batch after Cow King leveling tail. Added Gold Find Budget and Summoner
Starter uses of Tal Rasha's Horadric Crest. Life leech desirable; observed life and
resistances supporting. Mana/mana leech/defense receive no mercenary priority.
Nonethereal set identity and cited Act2 Might context retained; other aura setups
are pending, not asserted impossible. Summoner source prose names Tal while planner
shows ethereal Bulwark Mask; preserve this alternative/conflict rather than silently
substituting. Gold Budget requires positive gold on a socket jewel; source30gold is
an optional target, not a minimum. Parent totals alone cannot prove that socket.
Mercenary kill attribution, leech target effectiveness and full survival remain
independent conditions. No automatic gold income, defense premium or market price.

Red:2 missing configurations. Green:4 focused checks then388 affected tests in74.92s;
Ruff/format/diff pass. Tests reject caster/unknown mercenary, impossible ethereal set,
missing socket evidence and fabricated observed properties. All18 saved reports and
prices unchanged; published/staged parity. Tal helm uses domain fixtures, not a new
live capture. Generation:
100ffba79d6ea678df0e2a0e978ce4eb15b9317eb391e70ac53dad9c8654dd84.
439roles /431stat configs;530reviewed /8excluded stat-use rows. Census/dossiers and
base/coverage matrices refreshed. Demand two reviewed builds, Pending/Med lower bound.
Evidence tmp/tal-merc-*. Runtime data only; no new worker restart requirement.

One demand batch complete. Next pick another family/identity from the full queues,
then reserve specialist/leveling work. Remaining Tal aura variants, broader named
trade tiers/leveling, base desirability, affixed combinations and scoped prices
remain unfinished. No live collection or numerical estimate added.

## Offline market prerequisite audit by policy — 2026-09-25

Audited the pricing side rather than inferring price readiness from guide coverage.
Added per-policy blocked_observations and blocker_counts to market_readiness.
Overlapping gaps never inflate the blocked-row denominator; duplicate/superseded
snapshots and foreign scope remain excluded. Ready does not mean priced: exact
modifiers, seller independence, socket contributions and dispersion still apply.
Red: missing per-policy blocker fields. Green:100 maintenance checks in2.32s,
Ruff/format/diff pass. Real-corpus arithmetic validated for every policy route.

24,178 scoped rows:1,324 structurally ready,22,854 blocked. Affixed558/8728 ready,
base20/3209, named616/7089, runeword130/4391, unclassified0/761. Dates dominate
many affixed/named gaps; bases need explicit sockets/contents; runewords largely
lack base rarity. These are evidence prerequisites, not proof every modifier policy
is implemented or that all remaining gaps require network collection. No missing
facets/date guesses were introduced, no numerical price or runtime publication changed.

Durable report: planning/MARKET_READINESS.md with input SHA256 and reproduce command.
Evidence tmp/market-blockers-* and tmp/current-pricing-coverage.txt. No worker restart.
This maintenance audit does not consume a demand batch; Tal helm was the first
since Cow King tail. Next inspect explicit cached evidence for a bounded repair or
continue the second demand/family batch. Full tiers, guide configurations, bases,
leveling and scoped exact price evidence remain unfinished.

## Goldwrap farming belt template — 2026-09-25

Second demand batch after Cow King tail: five explicit player-belt uses across
Berserk, Fire Warlock and Gold Find Barbarian. Three reviewed builds, Pending/Med
lower bound; variants are not extra votes. MF/gold priority differs by farming role;
IAS supports attacks only. War Cry needs typed total player FCR105. Native80gold is
an optional target; low50gold qualifies. Legal upgrades retain utility but do not
prove requirements, capacity, full setup or value. Ethereal durability remains a
player-use qualification; no ethereal/defense/upgrade premium or numeric price.

Explicit membership, source hash and exceptions: planning/GOLDWRAP_BATCH.md.
Reused cached extraction; one newly reviewed named identity/five uses. Rules439→444,
stat configs431→436, stat-use rows535reviewed/8excluded. Full62891 occurrences and
2739identity denominator unchanged; 1384 unresolved identities remain. Base1569 and
evidence320 unchanged. Census/dossiers/base/coverage matrices refreshed.

Red: five missing rules. Green: seven focused checks. Broad assessment/report suite:
1851 passed and one old glove-test selector failed in233.88s; it included the prior
Lightning Sorceress Chance Guards rule in a javelin-only test. Narrowed selection to
Lightning Fury/Strike; all12 affected glove/farming/Goldwrap checks pass in3.16s.
No runtime fix or blanket count increase. Ruff/format/diff pass. All18 saved reports
and prices unchanged; published output matches staging. New cases use domain
fixtures rather than live captures. Evidence tmp/goldwrap-*.

Published generation:
a6de96fdfa14820542708401fb03fcf076b57fbdbec69e61fa0bca331ae8f5d9.
Runtime data only, no additional worker restart. Next batch must cover specialist,
leveling or unresolved cases. Broad named tiers, class leveling, base desirability,
affixed combinations and scoped exact pricing remain unfinished. No live collection.

## Movement boots leveling template — 2026-09-25

Scheduled specialist/leveling tail after Tal helm and Goldwrap demand batches.
Reviewed Hsarus Iron Heel and Sander Riprap movement advice across all eight cached
class guides: eight added guide recommendations and eight existing entries given
explicit standalone movement benefits. Guide Hsarus advice no longer inherits the
transcript two-piece attack-rating gate; that separate transcript advice remains
conditional. Barbarian after-level31-respec and Paladin after-level18-respec source
contexts preserved independently of native equip levels3/20. Qualitative priority
unchanged (Hsarus3/med, Sander1/high); no trade tier or numerical price inferred.

Added four reviewed source hashes/exact locator pairs; all eight guide hashes match
cached files. Reused source extraction, no online collection. Reviewed dates use
2026-09-25; original guide dates preserved (May22, WarlockJuly14). Explicit membership
and exceptions: planning/MOVEMENT_BOOTS_BATCH.md. Recommendations84→92; coverage
evidence320→328. Roles444/stat configs436 and535reviewed/8excluded stat-use rows
unchanged. Full2739identities/62891occurrences and base1569 denominator retained.

Red: eight adapter and one runtime case. Green:394 recommendation/policy/maintenance
checks in5.57s; Ruff/format/diff pass. Native requirements, impossible ethereal set,
unidentified facts and changed source gates verified. All18 saved report texts and
prices unchanged; published/staged parity. Domain fixtures, no new live capture.
Generation2930567b42fd66d0ac51a2d182e6844d448812719f3458d3dd84ca9614a5b7fa.
Rebuilt recommendations/index, census/dossiers/base/coverage matrices. Evidence
 tmp/boots-leveling-*. Maintenance adapter/data only, no additional worker restart.

Tail complete; resume demand/family review. Additional class-specific leveling,
named tiers, unresolved guide identities, base desirability, rare/magic combinations
and scoped exact price evidence remain unfinished. This batch closes movement-boot
guide membership, not all-item assessment or pricing coverage.

## Stone of Jordan skills/mana template — 2026-09-25

First demand batch after movement-boots leveling tail. Added14 reviewed variant
uses across8 distinct builds. Shared unique-ring applicability; observed skills
are desirable and mana/maximum mana supporting. Added lightning attack damage does
not become spell damage. Fixed modifiers have no roll target. Explicit per-variant
main-loadout FCR retained; unknown thresholds are not inherited from other variants.
Enchant swap105FCR and Nova life-based Hydra/mana-management qualifications retained.
Duplicate ring slots do not inflate demand or prove ownership of a second ring.

Source membership/conditions and pending companion cases: planning/SOJ_BATCH.md.
Fire Blast requires crafted amulet12+FCR plus total102 and Phoenix/Spirit alternatives;
Tri-Brid requires75main/125swapFCR,48FHR and encounter-dependent Cannot Be Frozen.
These two exact uses remain unreviewed by this template. Decorated/prose/planner
leads remain in the full census. Demand Pending/High lower bound8 is not a trade tier.

Red:14 missing-role cases. Green:16 focused checks;413 affected stat/ring/context,
policy/maintenance/report checks in8.66s. Initial test expected9builds; actual member
IDs verified8 and the expectation corrected. Ruff/format/diff pass. All18 saved
report texts and numerical prices unchanged; published/staged parity. Domain
fixtures, no new live captures or market collection.

Published8a53839ca5f3db8ccf828d16dea1a4c381383f8725e2d120b26eaf462f5b13b1.
Roles444→458; stat configs436→450;549reviewed/8excluded stat-use rows. Semantic
configurations350→362. Full2739identities/62891occurrences, evidence328 and base1569
retained. Census/dossiers/base/coverage matrices refreshed. Evidence tmp/soj-*.
Runtime data only, no additional worker restart. No numeric price/tier changed.

One demand batch complete. Next address another family/companion configuration, then
reserve the specialist/leveling tail. Named trade tiers, full guide-use closure,
base desirability, affixed combinations and scoped exact prices remain unfinished.

## Equipped companion predicates / Fire Blast SoJ — 2026-09-25

Second demand batch after movement-boots tail. Added reusable equipped_item_matches:
explicit player/mercenary/swap slot maps, ItemFacts or serialized facts, immutable
snapshots. Missing slot/malformed input unknown; explicit null empty. One item's
facts/stats satisfy a complete combination; no pooling, no inferred equipment from
hover/name-list/character-total. Nested predicates limited to fact/stat logical
combinations; native keys remain covered by publication validation. Context copy
retains facts. API documented in assessment/README.md; automatic live equipment
collection remains unimplemented, so callers must supply verified loadout facts.

New fire-blast-standard-soj-phoenix: Assassin/identified nonethereal SoJ, total102FCR,
actual equipped crafted identified nonethereal amulet12+FCR and identified Phoenix
Monarch. Source20FCR/+2skills are illustrative, not minima. Skills/mana priorities
activate only after mandatory companions pass. Spirit/Nagelring branch remains
pending, as does Tri-Brid encounter/CBF/swap logic. Membership/source/exceptions:
planning/FIRE_BLAST_COMPANION_BATCH.md. SoJ breadth8→9builds,15uses, Pending/High lower
bound; no numerical price or trade tier claim.

Red: missing operation, context-copy loss, missing Fire Blast profile reproduced.
Green:29 initial focused checks, then1992 assessment/report checks in246.99s. Final
11 equipment tests pass after lint-only raw-regex correction. Ruff/format/diff pass.
All18 saved reports and prices unchanged; published/staged parity. Domain fixtures,
no live probes or market collection. Evidence tmp/equipment-* and
 tmp/fire-blast-companion-*.

Published614736b2d028dbc3f4f4add8bbd7382d4efe654bb96f7b3dfb6cc20f0631cea0.
Roles458→459/stat configs450→451;550reviewed/8excluded stat-use rows. Full2739identity,
62891occurrence,1569base-quality and328evidence denominators retained. Census/dossiers
and base/coverage matrices refreshed. Restart Alt+D worker for Python context and
predicate changes. Next scheduled batch is specialist/leveling/unresolved work;
all-item tiers, base desirability, affixed combinations, source closure and exact
scoped prices remain unfinished.

## Druid/Paladin caster leveling package — 2026-09-25

Scheduled tail after SoJ family and Fire Blast companion batches. Eight explicit
recommendations: Spectral Shard, Suicide Branch, Vipermagi and Magefist for Druid
and Paladin. Reviewed caster archetypes now explicit for these guide benefits;
weapon alternatives retain priority3/med, armor/gloves1/high. Spirit remains an
alternative comparison, not an inferior item by default. Paladin post-level18
respec context does not override native item levels25/33/29/23. Spectral dexterity
investment, whole-loadout cast breakpoints and Magefist fire-skill exceptions kept:
Fissure benefits; Tornado/Blessed Hammer do not gain that fire-skill level.

Exact membership/hash/conditions: planning/CASTER_LEVELING_BATCH.md. Cached source
hashes verified; May22 guide dates retained. No extraction or online collection.
The Spirit Shroud/incidental source gaps remain pending rather than becoming no-use.
Recommendations92→100; coverage evidence328→336. Roles459/stat configs451 and
550reviewed/8excluded stat-use rows unchanged. Full2739identity/62891occurrence and
1569base-quality denominator retained. Rebuilt recommendations/index, refreshed
census/dossiers and base/coverage matrices.

Red:8 adapter and1 runtime case. Green:403 recommendation/policy/maintenance tests
in6.91s; Ruff/format/diff pass. Native equip requirements, source locator changes,
caster scope, fire-skill exceptions and ethereal variant uncertainty verified.
All18 saved report texts and prices unchanged; published/staged parity. Domain
fixtures, no new live probes or numerical market prices. Evidence tmp/caster-leveling-*.
Published805bdb16ce58608a25d727069b805bb830870dff7f88d8dfbb209dd79346d078.
Maintenance adapter/data only; no additional worker restart beyond prior companion
predicate Python update.

Tail complete; resume demand/family work. Other class/item leveling, all named trade
tiers, base desirability, affixed combinations, source identity closure and exact
scoped price coverage remain unfinished.

## Fire Blast affixed jewelry — 2026-09-25

First demand batch after caster-leveling tail. Added crafted amulet and rare ring
patterns for the Phoenix branch. Captured jewelry must have source12+FCR (crafted
amulet) or10FCR (rare ring), with Assassin/102totalFCR/actual Phoenix Monarch context.
Illustrated2skills/20FCR/20allres/25MF amulet and20str/40life ring values are targets,
not minima. All-resistance support on the amulet requires all four observed stats;
ring resistance properties independently support the role. No fabricated observed
stats or blanket affix weights. Source-only pattern demand stays separate from
named-item votes; no numerical price or market tier inferred.

Native tables clarify the functional12+amulet threshold: caster recipe5–10FCR plus
optional10FCR affix yields5–10 or15–20. Positive item fixture uses15;12-boundary
predicate fixtures are not proof of a naturally spawned12FCR craft. Existing role
threshold remains the guide requirement; full affix legality remains a separate
mechanics/range responsibility. Verified table hashes and membership documented in
planning/FIRE_BLAST_JEWELRY_BATCH.md. Spirit/Nagelring remains separate/pending.

Red:2 missing rules. Green:5 initial focused checks. Broad679-test run:678passed and
one stale amulet-count assertion; updated18→19 for the new pattern, then6 affected
jewelry/compiler/companion tests pass in1.80s. Ring-count8→9 reflects the new rare
configuration; old behavior assertions unchanged. Ruff/format/diff pass. All18 saved
reports/prices unchanged, published/staged parity. Domain fixtures, no live probes
or market collection. Evidence tmp/fire-jewelry-*.

Publishedcfc9e67b5a16d2e081e00379deee39c7a4877a48f9e59442358da01923cf2c77.
Roles459→461/stat configs451→453;552reviewed/8excluded stat-use rows. Full2739identity,
62891occurrence,1569base-quality and336evidence denominators retained. Refreshed
census/dossiers/base/coverage matrices. Runtime data only; no additional worker
restart beyond previous equipped-companion Python update.

One demand batch complete. Next another family/companion batch, then reserve tail
work. Broad base desirability, magic/rare/crafted combinations, all named tiers,
source closure, leveling and exact scoped prices remain unfinished.

## Nagelring MF / Spirit alternative — 2026-09-25

Second demand batch after caster-leveling tail. Added Fire Blast Standard Spirit
alternative and Enchant MF Nagelring uses. Native15MF qualifies;30MF optional target.
Observed MF desirable; other native properties are outside this farming-utility
review, not declared useless. Fire Blast requires actual equipped identified
normal/superior Spirit Monarch and102totalFCR; Phoenix, Spirit sword, missing facts,
name-only or mercenary evidence cannot satisfy it. No Phoenix crafted-amulet gate
is imported. Enchant keeps its separate source conditions without inventing a main
FCR threshold or Spirit requirement. Two builds, Pending/Med lower bound: Enchant
preferred, Fire Blast alternative. No ring-count or complete-loadout claim.

Source membership/exceptions: planning/NAGELRING_BATCH.md. Follow-up notes added to
prior Fire Blast documents: explicit Nagelring alternative now covered, other Spirit
jewelry permutations pending. Berserk, Lightning Strike and Strafe uses remain in
full queues; Strafe requires its companion/leech/IAS-jewel review. Prior Fire Blast
SoJ item fixture now uses legal15FCR amulet; numeric predicate boundary tests are
not assertions of naturally spawned12FCR crafts.

Red:2 missing roles. Green:5 focused then390 affected tests in7.27s; Ruff/format/diff
pass. All18 saved reports and numerical prices unchanged; published/staged parity.
Domain fixtures, no live capture/market collection. Evidence tmp/nagelring-*.
Publisheddd033510938f92a804c4f4ca004e3bc8c62e4595bae81f02191ad5b7590e7219.
Roles461→463/stat configs453→455;554reviewed/8excluded stat-use rows. Full2739identity,
62891occurrence,1569base-quality and336evidence denominators retained. Refreshed
census/dossiers/base/coverage matrices. Runtime data only; no additional restart
beyond earlier equipped-item predicate code.

Two demand batches complete; next scheduled batch must cover specialist, leveling
or unresolved cases. All named tiers, broad base desirability, affixed configurations,
source closure and exact scoped prices remain unfinished.

## Assassin leveling pair/armor — 2026-09-25

Scheduled tail completed after Fire Blast affixed jewelry and Nagelring. Added three
explicit Assassin recommendations: Death's Hand, Death's Guard and Twitchthroe.
Pair IAS/all-resistances remain conditional; Cannot Be Frozen belongs to the belt
itself. Ancient's Pledge remains companion advice. Twitchthroe blocking requires a
shield. High leveling priority does not establish a market tier or price.
Source date/hash, exact locators and native definitions documented in
planning/ASSASSIN_LEVELING_BATCH.md. No source re-extraction or market collection.

Red: three missing recommendations. Green: 50 affected adapter/runtime/coverage
checks in4.21s, then three post-lint focused checks in1.36s. Ruff/format/diff pass.
All18 saved report texts and numerical prices unchanged; published/staged parity.
Published4856a57aa35ce1b231bb566ae5f2856fbda4542d4caf34d5ff01118f48c0a0a4.
Recommendations100→103, evidence336→339; 2739identity and1569base-quality denominator
retained. Roles463/stat configurations455 unchanged;554reviewed/8excluded stat-use
rows. Census/dossiers/base/coverage matrices refreshed. Evidence tmp/assassin-leveling-*.
Maintenance Python change only: runtime consumes prepared recommendation data at
request boundaries. Earlier equipped-context runtime update still needs restart if
not already applied.

Next: resume demand/family review from the full dossiers, prioritizing newly covered
identities and reusable configurations. Berserk/Lightning Strike Nagelring uses and
Strafe's leech/IAS-jewel companion branch remain queued. Other leveling, universal
named tiers, base desirability, affixed combinations, unresolved identities and
exact scoped prices remain incomplete. Do not infer closure from this tail batch.

## Nagelring attack-build expansion — 2026-09-25

First demand batch after Assassin leveling tail. Added Berserk Starter/Standard
and Lightning Strike Starter magic-find ring components. Source-specific Angelic
pair,105swapFCR and50minimum/95targetIAS qualifications stay partial. No main FCR
inferred from swap, no captured stats synthesized, no complete-loadout claim.
MF15 useful/30optional target. Four distinct builds/five reviewed uses; Berserk's
two variants count once. Pending/Med lower bound, not a price or named trade tier.
Membership/exclusions: planning/NAGELRING_EXPANSION_BATCH.md.

Red: three missing configurations. Green:381 tests6.35s plus five post-lint checks
1.51s; lint/format/diff pass. All18 saved reports/prices unchanged, published parity.
Published3d779445f8b432272375ef9644e79a64a82509162209dd56ec70200ee65ee5cf.
Roles463→466/stat configs455→458;557reviewed/8excluded stat-use rows. Census/dossiers
and matrices refreshed. Coverage refresh first rejected the old base-matrix source
snapshot; installed rebuilt base matrix then successfully rebuilt coverage. Retains
2739identities,1569base-quality rows,339evidence and103recommendations.
Evidence tmp/nagelring-expansion-*. No live collection; runtime data-only update.

Next demand batch should address a new identity/family or the unresolved Strafe
Stealskull/dual-leech/helmet-IAS companion rule, then schedule another tail batch.
Planner-only and Hardcore Nagelring uses were not promoted. Broad base desirability,
all named tiers, affixed combinations, source closure and scoped prices unfinished.

## Strafe MF Nagelring companion — 2026-09-25

Second demand batch after Assassin leveling tail. Added prose-specific Strafe MF
Nagelring rule: actual equipped identified unique Stealskull with linked15IAS jewel.
Native dual leech supports the substitution; planner Harlequin Crest/glove conflict
retained explicitly. Complete breakpoint/glove/sustain setup stays conditional.
No aggregate IAS, other slot, mercenary, inventory name or missing identity bypass.
ObservedMF15useful/30optional target; no price inferred. Nagelring5builds/6uses,
Pending/High lower bound. See planning/STRAFE_NAGELRING_BATCH.md.

Runtime equipped_item_matches now accepts socket_jewel_stat_at_least in item-local
conditions. Existing socket evaluator and key traversal reused. Malformed equipped
socket stats previously could crash; snapshot validation now returns unknown.
Python worker restart required. No automatic loadout collection was added.

Red: unsupported socket dependency, missing role, malformed child crash. Green:
683affected tests90.31s,31focused after snapshot fix2.02s; lint/format/diff pass.
All18 saved reports/prices unchanged; published/staged parity.
Publishedba59e0120d5bcbb0909f2bcc41697834771e72253f08524cbb8a11b3261b79ae.
Roles466→467/stat configs458→459;558reviewed/8excluded stat-use rows.
Evidence tmp/strafe-nagelring-* and tmp/equipment-sockets-*.

Next must be a specialist/leveling/unresolved tail batch. Other class leveling,
all named tiers, broad base desirability, affixed combinations, source closure and
exact scoped prices remain unfinished. This companion check does not complete
Stealskull's own item assessment or solve conflicting planner setups.

Census/dossiers/base/coverage matrices refreshed successfully; denominator remains
2739identities,1569base-quality rows,339evidence and103recommendations.

## Assassin skill leveling — 2026-09-25

Scheduled tail complete after Nagelring expansion and Strafe companion. Added
SoJ, Eye of Etlich, Vipermagi and Magefist Assassin guide recommendations. General
skill/resistance utility remains distinct from caster advice; Magefist follows the
guide's Fire Traps/Death Sentry recommendation, not Lightning Sentry. Trap-placement
attack speed remains qualified. Native equip levels29/15/29/23 verified in runtime.
Source/locators/remaining aliases: planning/ASSASSIN_SKILLS_LEVELING_BATCH.md.

Red: four missing recommendations. Green:55 affected tests4.76s; lint/format/diff
pass. All18 saved reports/prices unchanged, published/staged parity. No live probes
or market requests. Published86933b34dfdc2826e0605ef7f60f1a3de097466620de291381c514a3b293f633.
Recommendations103→107/evidence339→343. Roles467/stat configs459 unchanged;
558reviewed/8excluded stat-use rows. Census/dossiers/base/coverage matrices refreshed;
2739identities/1569base-quality denominator retained. Evidence tmp/assassin-skills-*.
Maintenance adapter changes only; no additional runtime restart beyond equipped
socket-predicate update from the previous batch.

Next demand/family review should cover new identities or reusable configurations
from full dossiers. Alias-specific Ravenfrost/Maras leveling, runeword alternatives,
all named trade tiers, broad bases/affixed patterns and exact prices remain pending.

## Mara's Kaleidoscope shared skill/resistance template — 2026-09-25

First demand batch after Assassin skill-leveling tail. Selected a new named identity
from full dossiers. Added11variant rules across8builds, preserving explicit main
FCR thresholds125/117/105/75/65 and unspecified Ubers thresholds. Minimum20res useful;
30allres optional. Skills desirable, complete observed all-res group supporting.
Attributes outside narrow template are not worthless. Whole-loadout resistance,
Ubers preparation and equip qualifications retain partial fit. Eight builds count
once each despite repeated variants; Pending/High lower bound, no price inference.
Exact membership/source exceptions: planning/MARAS_BATCH.md.

Red:11missing rules and missing demand summary. Green:12focused then389affected
checks8.71s; lint/format/diff pass. All18 saved reports/prices unchanged and published
parity. No market collection or live capture. Runtime data only, no new restart.
Publishededa2f49d30e29b3dc22bd481834166fd3c7873cee1761eb2b9eecb959d95ec30.
Roles467→478/stat configs459→470;569reviewed/8excluded stat-use rows.
Evidence tmp/maras-*. Existing runtime socket-predicate restart remains required
if not already done.

Next another demand/family batch, preferably another new identity or reusable
base/affixed configuration, then scheduled tail. Remaining Mara uses, all named
trade tiers, broad base desirability, affixed combinations and exact scoped prices
remain unfinished; guide utility is not price coverage.

Census/dossiers/base/coverage matrices refreshed; retained2739identities,1569base-quality
rows,343evidence and107recommendations.

## Duress budget kicker armor — 2026-09-25

Second demand batch after Assassin skill-leveling tail. New named identity with
Dragon Talon Budget Duress Dusk Shroud configuration. Completed3filled sockets,
identified normal/superior nonethereal player armor; observed Crushing Blow desirable
and resistances supporting. Level90, boots, AR, CBF and complete setup remain
qualified. Other bases and Dream Paladin's planner/prose conflict do not inherit fit
or demand. No best-base or price claim. See planning/DURESS_BATCH.md.

Red: missing rule. First positive test used base title instead of captured runeword
title; corrected to match existing runeword fixture convention. Green:378affected
checks6.19s; lint/format/diff pass. All18 saved reports/prices unchanged, publication
parity. Published1ca6f155586c8f948e5964421e028829dac3d30390aa2b884a24628926c2b273.
Roles478→479/stat configs470→471;571reviewed/8excluded stat-use rows (normal and superior).
Evidence tmp/duress-*. Runtime data-only change; no new restart, probes or collection.

Next must be specialist/leveling/unresolved tail. Dream Duress/Chains of Honor conflict,
remaining aliases, named trade tiers, broad base desirability, affixed combinations
and exact scoped prices remain incomplete. Guide use remains separate from pricing.

Census/dossiers/base/coverage matrices refreshed;2739identities,1569base-quality rows,
343evidence and107recommendations retained.

## Exact leveling source aliases — 2026-09-25

Scheduled unresolved tail complete after Mara and Duress. Added canonical Raven Frost
and Mara's Kaleidoscope Assassin recommendations from reviewed Ravenfrost/Maras
Kaleidoscope occurrences. GUIDE_SOURCE_NAMES binds each mapping to class, canonical
name and exact locator; source_label preserves original wording. No fuzzy global
normalization or source mutation. Ambiguous canonical facts, changed label/locator
or unverified snapshot cannot produce a recommendation. Native levels45/67 and
alternative/late-leveling qualifications retained; no price synthesis.
See planning/LEVELING_SOURCE_ALIASES_BATCH.md.

Red: two missing recommendations. Green:58affected checks5.29s; lint/format/diff
pass. All18 saved reports/prices unchanged, published parity.
Publishedf524c6a4ac8b58dcb22b28e097549e0002acb205a15d8e2858ebbc05d31961aa.
Recommendations107→109/evidence343→345. Roles479/stat configs471 unchanged;
571reviewed/8excluded stat-use rows. Evidence tmp/leveling-alias-*.
No live probes/collection. Maintenance adapter only; no new runtime restart beyond
previous equipment/socket changes if still unapplied.

Next resume demand/family work, prioritizing new identities or reusable base/affixed
configurations. Runeword leveling alternatives, other aliases, universal named tiers,
base desirability, affixed combinations and exact prices remain unfinished. This
bounded alias review does not establish global identity closure.

Census/dossiers/base/coverage matrices refreshed;2739identities and1569base-quality
rows retained alongside345evidence and109recommendations.

## Starter magic skill/FCR amulet family — 2026-09-25

First demand batch after exact leveling aliases. Added Fire Warlock, Fissure Druid
and FoH/Holy Bolt Starter configurations: one observed skill plus10FCR on the same
identified nonethereal magic Amulet. Class/tree exact, no pooled gear or total-FCR
substitution. Fissure illustrated+2target does not reject useful+1. Historical Fire
Warlock craft and Holy Bolt activity exceptions stay explicit. Rare/crafted siblings
remain separate review. No price or blanket affix weights.
Membership: planning/STARTER_SKILL_AMULETS_BATCH.md.

Red:four missing configurations. Broad run380passed/two stale count assertions;
updated magic-applicable13→17 and all-affixed-amulet19→23, then all8affected tests pass
4.10s. Behavior assertions unchanged. Ruff/format/diff pass. All18 saved reports and
prices unchanged; published parity. No live collection/probes or runtime Python edit.
Published78d39b5aaac6f849602087a31ff0aa9ecfb452848d0ce4956ea017ac64d3c496.
Roles479→483/stat configs471→475;575reviewed/8excluded stat-use rows.
Evidence tmp/starter-amulet-*.

Next another demand/family batch, then scheduled tail. Rare/crafted siblings, other
skills/combination patterns, broad base desirability, named tiers and exact scoped
prices remain incomplete. Earlier runtime equipped-socket restart still required
if not already applied.

Census/dossiers/base/coverage matrices refreshed;2739identities,1569base-quality rows,
345evidence and109recommendations retained.

## Rare starter amulet combinations — 2026-09-25

Second demand batch after exact leveling aliases. Added Hammer/Summoner rare
skill/FCR core patterns: identified nonethereal rare Amulet, exact class/tree,
positive skills plus10FCR on same item. Secondary mana/life/resistances optional;
Summoner all-res group requires all four observed stats. Summoner75totalFCR explicit;
+4total skills/overcap and separate swap staff qualified. Hammer core utility neither
requires nor claims example teleport-charge function. Other qualities excluded from
these specific configurations. No numerical prices or arbitrary affix weights.
Membership: planning/STARTER_RARE_AMULETS_BATCH.md.

Red:two missing roles. Broad379passed/one stale count; affixed amulet23→25, then all
six affected checks pass3.37s, including partial-resistance behavior. Ruff/format/diff
pass. All18 saved reports/prices unchanged and published parity. No live collection.
Published5b0f05b68f401857043406a92622edea5246e61ffa1c11a14a40c6ffd092db2c.
Roles483→485/stat configs475→477;577reviewed/8excluded stat-use rows.
Evidence tmp/rare-starter-amulet-*. Data-only update, no new worker restart.

Next scheduled batch must cover specialist/leveling/unresolved cases. Broader rare
and crafted configurations, base desirability, universal named tiers, source closure
and exact scoped market estimates remain unfinished. Earlier equipped-socket Python
restart is still needed if not already done.

Census/dossiers/base/coverage matrices refreshed;2739identities,1569base-quality rows,
345evidence and109recommendations retained.

## Reviewed source-conflict tracking — 2026-09-25

Scheduled unresolved tail complete after magic/rare starter amulet batches. Audited
Fire Blast Starter magic Amulet +1Traps/+20allres/25MF: Traps and allres both require
prefixes, so the quoted normal magic combination is impossible. Do not relabel rare
or discard properties automatically. Added pinned issue with exact source pointer,
original value, wp-a-builds and native prefix/suffix hashes; reconcile planner quality
before promoting a configuration. See planning/MAGIC_AMULET_SOURCE_ISSUE.md.

New maintenance reviewed_source_issues evaluator returns reviewed_conflict only for
matching source/value/mechanics snapshots; stale/missing evidence stays stale_review.
Inventory and dossiers retain the issue separately from missing planner links. This
is a review aid, not a global compiler ban for parent-build references. No runtime
assessment rule or price change; no worker restart/publication needed for this batch.

Red:missing evaluator. Green:19 inventory/dossier/issue checks plus focused exact
pointer/value checks; lint/format/diff pass. Generated inventory/dossiers verified
one reviewed conflict. Coverage matrix refreshed. All18 saved report texts/prices
unchanged against last published replay. Runtime generation remains
5b0f05b68f401857043406a92622edea5246e61ffa1c11a14a40c6ffd092db2c.
Roles485/stat configs477;577reviewed/8excluded stat-use rows unchanged.
2739identities,1569base-quality rows,345evidence and109recommendations retained.
Evidence tmp/source-issues-*. No live collection or probes.

Next resume demand/family work. Keep the Fire Blast source conflict in its dossier;
remaining source closure, broad base/rare/crafted configurations, named trade tiers
and exact scoped prices remain unfinished.

## Duress Dusk Shroud base preparation — 2026-09-25

First demand/base batch after source-conflict tail. Base matrix already retains
partial uses; pending dimensions were conservative, not absent links. Actual gap:
completed Dragon Talon Duress reviewed but no empty-base use. Added explicit Dusk
Shroud/Duress progression template with cached guide locator, propagated into base
report sources. Three empty sockets = usable alternative, not best/priced base.
Unsocketed high-ilvl normal armor retains16.7% cube odds for3; four sockets rejected.
Player ethereal/equip/Ubers conditions remain. See planning/DURESS_BASE_BATCH.md.

Red:missing base use. Green:33base/routing/matrix tests2.50s, then14progression tests
1.41s including preparation/ethereal boundaries. Source locator resolves to actual
cached equipment value; lint/format/diff pass. All18 saved reports/prices unchanged
against pre-change replay and published/staged parity. Runtime Python changed:
worker restart required. No new runtime artifacts/prices or market collection;
published data generation remains5b0f05b68f401857043406a92622edea5246e61ffa1c11a14a40c6ffd092db2c.

Base matrix still234rows with uses;507→510use entries (three quality states), not
three confirmed item matches. Full1569base-quality and2739identity denominator
unchanged. Roles485/stat configs477 and named-price coverage unchanged. Evidence
 tmp/duress-base-*. Initial matrix read raced unfinished generation; no invalid file
installed. Refreshed base matrix after completion before rerunning dependent coverage.

Next another demand/family batch, then tail. Other bases, named trade tiers,
rare/crafted combinations and exact scoped prices remain unfinished. Legal eligibility
and a reviewed base candidate still do not prove maximum quality or market premium.

## Nested cache collection date recovery — 2026-09-25

Offline market maintenance after Duress base batch; does not consume demand/tail
slots. Found200Razortail rows with explicit _meta.pulled2026-09-20; listing update
range validates that day. Importer now accepts exact top-level/nested collection
dates, retains actual field provenance and rejects invalid/conflicting metadata.
No filename/mtime/listing-date fallback. Four red failures;22initial then46market/
refresh/comparison/publication tests pass8.11s; lint/format/diff pass.

Offline refresh/runewords/valuable/index/base rebuild retained41135observations;
dated19776→19976. All200rows preserve identical seller,scope,item facets and prices.
Scope unchanged:54verified,139rejected,7unknown. Named-readiness audit now reports
2structurally-ready Razortail observations,52stillblocked (ethereal52,base36; gaps
overlap). Not enough for three independent comparable sellers; no price inferred.
Durable audit pricing/data/market-date-recovery-2026-09-25.json; source/evidence notes
planning/NESTED_CACHE_DATE_BATCH.md. Most undated caches lack any collection evidence.

Published6a28e579ff28ffb0b03de2c8e4607cc4e94a4bc30715b494a21c7900aa64c937.
All18saved report texts/prices unchanged; published/staged parity. Base/coverage
matrices refreshed against new market/index inputs. No live requests. Maintenance
importer change needs no extra runtime restart; prior base-template restart still
needed if unapplied. Roles485/stat configs477 and109recommendations unchanged.

Next resume the second demand/family batch after Duress base, then tail. All named
tiers, broader base/affixed configurations and exact market cohorts remain unfinished.

## Meteor Volcanic/Luck magic amulet — 2026-09-25

Second demand batch after source-conflict tail. Added exact3FireSkills/26–35MF magic
amulet alternative; native26Luckminimum useful,35optional target. Required main
63FCR/60FHR totals;105FCR higher option. Fire skills desirable, MF supporting. Full
setup partial; other suffix tiers/qualities remain separate, not worthless.
Source membership: planning/METEOR_MAGIC_AMULET_BATCH.md.

Red:missing rule. Green:380affected tests6.69s; lint/format/diff pass. All18saved
reports/prices unchanged; published parity. No probes or online collection.
Published50599b8ea66face195d921e26191a073b4211e723e41d610af4934664acb6af0.
Roles485→486/statconfigs477→478;578reviewed/8excluded stat-use rows. One new magic
configuration:18magic-applicable and26all-affixed amuletconfigs. Data-only update;
no additional runtime restart beyond prior Duress base/template change if unapplied.
Evidence tmp/meteor-magic-amulet-*.

Next scheduled batch must be specialist/leveling/unresolved. Date-recovery maintenance
did not consume a demand slot. Other source conflicts, broad bases/rare/crafted
families, named trade tiers and exact scoped market comparisons remain unfinished.

Census/dossiers/base/coverage matrices refreshed;2739identities,1569base-quality rows,
345evidence and109recommendations retained.

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

## Fire Blast rare starter amulet — 2026-09-25

First demand batch after planner reconciliation tail. Added
fire-blast-starter-rare-amulet: identified nonethereal rare Amulet, Assassin,
positive Traps (native188:48) and all four resistances on the same item. Skills are
desirable, resistance/MF supporting; MF optional. Illustrated20res/25MF are not
minimums. Other combinations are unreviewed, not worthless. Full equip/speed/
survival readiness remains qualified. Source WP-A Starter plus corroborating cached
planner e113x0l4, item34 Wraith Collar, resolves the incorrect Magic label.

Source validation/publication now includes source.corroborating path/hash/JSON
pointer references. A missing or changed planner cannot silently retain its role.
Sources are bundled with the runtime generation. Primary source remains the guide;
planner quality encoding is distinct from game native quality encoding.

Red: missing role and missing planner publication dependency. Green:31 affected
role/stat/source/publication tests36.44s; lint/format/diff pass. Native Traps mapping
verified against stat_constants and existing Lightning Sentry rule; wrong Martial
Arts188:50 explicitly rejected. All18 saved texts/prices unchanged, staged/published
parity. No online requests. Evidence tmp/fire-blast-rare-*.

Published c7b5ee38512890ad0519d516b62d6d6e19f3b9ad2bfb84990bd55164e68959fa.
487roles/479stat configurations;27affixed amulet configurations. Next one demand
batch then specialist/leveling/unresolved tail. Broad named tiers, base preference
policies, affixed configurations and exact scoped prices remain incomplete.
Source validator Python changes require a worker restart to enforce the new
corroborating-source validation in running processes; the compiled rule data is
selected at request boundaries by an already published worker.

Coverage matrices refreshed:579reviewed/8excluded stat-use quality rows;
2739identities,1569base-quality rows,345evidence records retained.

## Harlequin Crest shared farming family — 2026-09-25

Second demand batch after source reconciliation tail. Added10explicit build/variant
helmet configurations, native2allskills/50MF utility; source-specific mainFCR/FHR,
Weapon-Swap distinctions, socket and full-loadout qualifications preserved.
Reviewed breadth10builds, Pending with High lower bound; not a market price.
Membership/source decisions: planning/HARLEQUIN_BATCH.md.

Red11missing role/demand tests. Green313role/stat/demand/publication regression
checks104.61s; lint/format/diff pass. Only saved Harlequin report text changes:
seven logical Build-use lines with10conditional uses and full detail references.
All18saved prices and17other texts unchanged; defense ranges unchanged.
Published 39fe11a840d09903c00d4c680031e90058194583e2a5a5f25a7ef69472264044.
497roles/489stat configurations. This is data-only, no additional worker restart
beyond prior corroborating-source validator code if unapplied. No online collection.
Evidence tmp/harlequin-*.

Next batch must be specialist/leveling/unresolved. Remaining named tiers, broader
base/affixed rules, guide identity closure and exact scoped prices remain incomplete.

Published replay parity verified. Census/dossiers/base/coverage refreshed:
589reviewed/8excluded stat-use quality rows;2739identities,1569base-quality rows,
345evidence records retained.

## Fire Blast ring/diadem quality audit — 2026-09-25

Scheduled unresolved tail after rare starter amulet and Harlequin farming batches.
Original cached e113x0l4 planner: Starter right ring44 Stone Finger is quality4 rare,
with30coldres/15MF/1manaafterkill; left ring43 Cobalt is quality3 magic and remains
unchanged. Standard head61 Eagle Visage is quality4 rare, with three prefixes/three
suffixes and two filled sockets. The WP-A Magic labels are extraction errors.
Starter gloves, boots, belt and teleport staff checked as quality3 magic too.

Added two pinned reviewed_source_issues records, including exact item, profile UID/
name, equipment reference and native rare-eligible affix rows. Registry now has
three reconciled source issues including the earlier Wraith Collar amulet.
Changed sources/mechanics reopen review. No global quality relabeling and no rewrite
of the shared WP-A file. Original labels preserved for audit.

Eagle Visage's conflict with prose/table Flickering Flame or Harlequin Crest is NOT
resolved by correcting rarity. No guide endorsement, required planner roll, executable
role, trade tier or price is inferred for either new correction. These remain
source-reviewed inputs for a subsequent configuration review.

Red: ring correction absent. Green:27 source-review/dossier/census/build checks;
all three actual registry records validate against source snapshots. No runtime
changes/publication or worker restart. Current generation remains
39fe11a840d09903c00d4c680031e90058194583e2a5a5f25a7ef69472264044.
Evidence tmp/fire-blast-quality-tail-*. Inventory/dossiers refreshed separately.

Tail complete. Resume two demand/family batches before the next tail. Remaining
named tiers, bases, affixed rules, leveling and exact scoped market cohorts remain
incomplete. Keep the diadem prose/planner conflict explicit.

## Trang-Oul's Claws caster family — 2026-09-25

First demand batch after the ring/diadem quality tail. Nine source-specific uses
across four builds: Blizzard Standard; Echoing Standard/MF/Ubers; Summoner
Standard/Damage-Ubers; Poison Nova Starter/Standard/MF. Explicit membership in
 test_trang_glove_priorities.MEMBERS. Review estimate ten minutes; reuse existing
identity/predicate/stat evaluator rather than introducing a glove-specific evaluator.

Identified nonethereal set Heavy Bracers. Cast rate desirable; cold resistance
supporting. Curses native188:16 supporting only for the Necromancer uses. Observed
poison skill damage332:0 desirable only for Poison Nova. No full/partial set bonus
synthesized; other properties/combinations unreviewed, not useless. Source125/105/
75FCR gates retained, Echoing Ubers unspecifiedFCR not invented. Whole-loadout
survival, resistances, sustain and Uber preparations remain qualifications. Summoner
Uber Life Tap and120res-overcap Standard needs kept distinct.

Native setitems/properties/itemstatcost and skill-tab encoding checked locally.
WP-A exact source locators/hashes/quotes retained. Reviewed demand4distinctbuilds,
Pending with Med lower bound. Guide utility is separate from trade tier or price.
No new market collection. Broader gloves, other variants and whole-set configurations
remain pending.

Red10missing role/demand cases. Green21affected glove/stat/demand/publication checks
5.39s; lint/format/diff pass. All18saved texts and numerical estimates unchanged.
Published c31e0a8658fd44446a6bcc0b6c1f8d0e6a772927b5e07e2358c73296c484103b.
506roles/498stat configurations. Data-only change; no additional worker restart.
Evidence tmp/trang-glove-*; final published replay and coverage checkpoint follows.

Next one demand/family batch, then specialist/leveling/unresolved tail. Required
named trade tiers, preferred bases, more affixed rules, leveling and exact scoped
price cohorts remain incomplete.

Published parity verified. Census/dossiers/base/coverage refreshed:
598reviewed/8excluded stat-use quality rows;2739identities,1569base-quality rows,
345evidence records retained.

## Laying of Hands attacking-glove family — 2026-09-25

Second demand batch after the quality-correction tail. Six uses/four builds:
Berserk Chaos Prep, Dream Standard/Hybrid, Mirrored Blades Standard/Ubers, Strafe
Standard. Membership in test_laying_hands_priorities.MEMBERS. Review estimate ten
minutes; existing identity, predicate and stat evaluator reused. Dream Ubers remains
outside this batch because of the unresolved armor prose/planner conflict.

Exact identified nonethereal set Bramble Mitts. Native20IAS and350damage against
demons desirable,50fire resistance supporting. Demon damage121:0 remains separate
from generic Enhanced Damage17:0; do not treat it as elemental aura damage. No
set-completion bonus or numerical price inferred. Native setitems/itemstatcost
checked locally. WP-A exact variant sources/hashes/quotes retained.

Full weapon/aura attack-speed qualifications kept: Strafe Level12Fanaticism/active
Hustle/setup for4/2/6 frames; Dream48FCR is Weapon-Swap and75IAS belongs to mercenary;
Hybrid Faith support remains separate. Mirrored Uber OW/CB/CBF/resistance preparation
and Standard3000life target not established by gloves. Chaos Prep prose reference
retained despite absent tab. Four reviewed builds gives Pending/Med lower bound.

Red7missing rule/demand cases. Green28glove/stat/demand/publication checks7.44s;
lint/format/diff pass. All18saved texts/prices unchanged. Published
9043ea4828481b458140401c0d6d7aa3061a38c4ad4a6bd29256daa1ea2a6088.
512roles/504stat configurations. Data-only, no additional worker restart.
Evidence tmp/laying-hands-*; final publication parity and coverage checkpoint follows.

Next batch must be specialist/leveling/unresolved. Required named tiers, bases,
remaining affixed configurations, leveling and exact scoped prices remain incomplete.

Final checkpoint2026-09-26: published parity verified; census/dossiers/base/coverage
refreshed.604reviewed/8excluded stat-use quality rows;2739identities,1569base-quality
rows,345evidence records retained.

## Before-respec melee and Bloodfist leveling — 2026-09-26

Scheduled leveling tail after Trang gloves and Laying of Hands demand batches.
Added six explicit source recommendations: Death's Hand/Guard and Bloodfist for
Barbarian and Paladin. Their pair advice belongs before level31/18 respec
respectively and is tagged melee.30IAS/15allres require both pieces; CBF belongs
to the belt itself. Bloodfist is explicitly recommended for the entire leveling
process; life/recovery remain useful after respec, while IAS is for attacks rather
than casting. Preserve this exception despite the before-respec section heading.

Exact cached leveling source locators and existing source hashes validated;
unchanged utility extraction reused. Review estimate ten minutes. Added per-item
review-date overrides so new rows say2026-09-26 without redating older reviews.
Native equip requirements6for both Death pieces and9for Bloodfist preserved.

Red6missing recommendations and1missing runtime artifact test. Green61recommendation/
leveling runtime checks7.35s; lint/format/diff pass after readability fixes.
Rebuilt recommendations and index offline.115recommendations(previous109);
no new executable role/stat configurations or numerical prices. All18saved reports
and prices unchanged. Published c34dc67561bb4328890e7b2192bde74feb524729c14f1c3e7c7fc727fe317dcc.
Maintenance adapter changes need no runtime worker restart. Evidence
 tmp/early-melee-leveling-*. Source pages retain their original dates.

Tail complete; resume two demand/family batches before next specialist/leveling/
unresolved batch. Named tiers, more bases/affixed rules, guide closure and exact
scoped prices remain incomplete. Final publication parity/matrices checkpoint follows.

Published replay parity verified. Census/dossiers/base/coverage refreshed:
351evidence records(previous345),115recommendations;512roles/504stat configurations
and604reviewed/8excluded stat-use quality rows unchanged.2739identities and
1569base-quality rows retained.

## Magefist shared caster family — 2026-09-26

First demand batch after early-melee leveling tail. Sixteen explicit variants
across nine builds; membership in test_magefist_priorities.MEMBERS. Review estimate
fifteen minutes; shared predicate/stat evaluator reused. Cast rate desirable,
mana regeneration supporting. Fire126:1 desirable only in the reviewed fire uses,
not FoH/Lightning Sentry/pure Nova. No attack-fire-damage or all-class-skill inference.

Generic Magefist mentions accept the native Light/Battle/Crusader Gauntlets chain;
Fissure Ubers is restricted to explicitly cited Crusader Gauntlets. Pinned native
armor row is corroborating evidence, validated and bundled during publication.
Actual base-tier equip requirements remain qualified; no automatic upgrade premium.
Native uniqueitems/itemstatcost checked for20FCR/25mana-regeneration/1fire skill.

Main/swap cast thresholds preserved, including Enchant's105swap and FoH Tri-Brid's
75main/125swap plus48FHR. Meteor63or105/60FHR Standard,105/86 Set and Ubers are
separate. Fire Blast/Wake102, Lightning Sentry65, Fissure99Standard and Nova105
Standard retained. Unspecified thresholds not inherited. Fire traps use attack
speed for placement, not FCR. Tal set completion, Hydra life-based versus Nova ES,
full companion setup and Uber preparations remain qualifications. Prebuff-only
Enchant and conflicting starter examples remain outside this batch.

Red17missing role/demand cases. Green35role/stat/source/demand/publication checks
10.83s; lint/format/diff pass. All18saved texts/prices unchanged. Published
f9f96a6bf6002925677314b6663054720a9611705ab23dbd69f32169b8766d73.
528roles/520stat configurations. Reviewed demand9builds, Pending/High lower bound.
Data-only, no additional worker restart; no online research. Evidence tmp/magefist-*.

Next one demand/family batch then specialist/leveling/unresolved tail. Required
named tiers, preferred bases, remaining affixed and leveling uses, guide identity
closure and exact scoped market comparisons remain incomplete. Final parity and
coverage checkpoint follows.

Published parity verified. Census/dossiers/base/coverage refreshed:
620reviewed/8excluded stat-use quality rows;2739identities,1569base-quality rows,
351evidence records and115leveling recommendations retained.

## Offline jewelry cohort audit and seller examples — 2026-09-26

Maintenance batch, not a demand/tail scheduling slot. Audited existing scoped
jewelry evidence and eleven reference Mara's Kaleidoscope resistance contracts,
20 through30, without network collection or treating references as captured items.
Durable audit: pricing/data/appraisal-jewelry-price-audit-2026-09-26.json, with input
hashes, contracts, listing/seller IDs, publication gates and exact price results.

30res: six matching listings from three sellers,9.32Ist ask estimate based on
2026-09-18 observations/conversion, low confidence.26/27/28/29res have1/5/17/22matched
listings but only1/1/2/1sellers respectively, so remain thin.20-25have no eligible
matches.232scoped Atma observations are undated; no date recovered. Appearance1265
remains an exact-comparison facet, not discarded to manufacture a larger cohort.
These are cache/reference results, not a new item appraisal or current sale price.

Found/fixed example selection bug: summary counted independent sellers correctly
but selected its first three examples from arbitrary listing order, allowing two
examples from one seller. Representatives now use each seller's actual minimum
eligible ask, with deterministic ordering. Numeric votes, matching, dates, scope,
unit and seller-count gates are unchanged. Full accepted listings remain diagnostics.

Red: repeated seller in published price examples. Green28market/valuable/refresh/
comparison tests7.96s; lint/format/diff pass. All11reference numeric estimates/seller
counts unchanged; examples now distinct. All18saved reports/prices unchanged from
the prior Magefist generation. Rebuilt valuable/index offline and published
b4fe1a9e6186750c5e98f3a9fd0fa110623b9969157f974d8c161c100f78716c.
Runtime market.py changed: restart worker to load this fix. No new role/stat/tier
coverage;528roles/520stat configurations,115leveling recommendations retained.
Evidence tmp/jewelry-examples-*; final parity/coverage checkpoint follows.

Scheduling unchanged: one more demand/family batch after Magefist, then tail.
Missing dates/appearance and independent sellers remain specific research gaps;
broader base, named-tier and affixed coverage is still incomplete.

Published parity verified; census/dossiers/base/coverage refreshed.620reviewed/
8excluded stat-use quality rows,2739identities,1569base-quality rows and351evidence
records retained. No new price cohort was manufactured or market evidence fetched.

## Fire Blast starter rings — 2026-09-26

Second demand batch after Magefist; the jewelry market audit was maintenance and
used no scheduling slot. Added two reviewed configurations: a magic cold-resistance
ring and a rare cold-resistance/mana-after-kill ring with optional magic find.
The original planner identifies left item 43 as magic Cobalt and right item 44 as
rare Stone Finger. Both share the pinned planner evidence with the source correction.

The guide's instruction to fill remaining gear with resistances supports positive
cold resistance; the example's 30 is not a required minimum. The rare configuration
requires cold resistance and mana after kill on the same item. Mana regeneration
and a different equipped ring cannot substitute. The example's 15 MF is optional.
These are supporting Starter properties, not a numerical trade valuation. Actual
kill credit, complete resource/resistance coverage and equip requirements remain
qualifications. Other qualities and combinations remain separate reviews.

Red: two missing configurations. Green: 21 ring/stat/source/demand/publication
checks in 5.76 seconds; lint, format and diff checks pass. Updated the affixed-ring
configuration count from 9 to 11; the existing magic-amulet count remains 18.
All 18 saved report texts and price results are unchanged.
Published generation: 375f2c48135dae5754ec52f7d256c7762f6db24c68a585e3883a4573384641c3.
530 roles and 522 stat configurations. Data-only update; no additional restart.
Source correction now links both profile IDs. Evidence: tmp/starter-rings-*.

Next batch must cover specialist, leveling or unresolved cases. Required named
tiers, preferred bases, more affixed configurations, leveling uses and exact scoped
market comparisons remain incomplete. Final parity and coverage checkpoint follows.

Published parity verified. Census, dossiers and coverage matrices refreshed:
622 reviewed / 8 excluded stat-use quality rows; 2,739 identities, 1,569 base-quality
rows, 351 evidence records and 115 leveling recommendations retained.

## Caster leveling tail — 2026-09-26

Added eleven reviewed leveling uses across seven unique identities: Barbarian
Vipermagi, Magefist, Etlich, SoJ and Arreat’s; Paladin Etlich/SoJ; Druid Etlich/SoJ,
Lidless and Jalal’s. Exact cached locators and source hashes retained. Respec stage
is advice, not a replacement equip level. Magefist fire skills and Arreat’s attack
rating do not improve War Cry. Jalal’s native bonus is Druid skills, correcting the
guide’s all-skills wording. Lidless retains external-resistance coverage conditions.
No guide-based price was invented.

Red: three missing class recommendation groups and missing runtime test. Green:
65 recommendation/leveling-policy tests in 7.27s, lint/format/diff pass. Rebuilt
recommendations and index offline; 126 leveling recommendations (previously 115).
All 18 saved report texts and price results unchanged before/staged/published.
Published 01012c886719ec11380a6a6ed040bcc68941b5010f1318226511fe129855f103.
Maintenance adapter/data only; no new worker restart. No live collection.

Census, dossiers and matrices refreshed: 62,891 occurrences / 2,739 identities,
1,569 base-quality rows, 530 roles / 522 stat configurations, 622 reviewed / 8
excluded stat-use quality rows. Batch detail: planning/CASTER_LEVELING_BATCH.md.
Commands: uv run --offline pytest tests/pricing/knowledge/test_recommendations.py
 tests/pricing/knowledge/assessment/policies/test_leveling.py -q (one command).
Artifacts and replay comparisons: tmp/caster-leveling-*.

Tail completed. Next demand-family candidate: Skin of the Vipermagi, identity
73d0a4a687cc4efbb8285593dac0c4d9053c5f02beec9454b7b2a12806204d3b.
Current dossier has 20 distinct-build review leads but zero reviewed build-use
votes; this is a source review opportunity, not confirmed fit for twenty builds.
Review shared 30 FCR/skills/resistance configuration with explicit variant/full-gear
qualifications and upgrade/socket exceptions. Resume two demand batches before
next specialist/leveling/unresolved tail. Named tiers, preferred bases, remaining
known affixed combinations, leveling/source closure and exact price cohorts remain
incomplete; the overall goal remains active.

## Vipermagi build-use family — 2026-09-26

First demand batch after caster-leveling tail. Seven reviewed roles across five
builds: Blizzard Standard alternative, Enchant Standard/MF, Holy Bolt Support,
Meteor Ubers and Nova Standard/MF. Minimum resistance rolls remain useful. Cast
rate/all skills desirable, resistances supporting, poison desirable for Nova ES.
Blizzard requires actual Nightwing's Veil equipment; no pooling with Glacial/Ormus.
Enchant main/swap distinction preserved; Meteor105FCR/86FHR and Nova105FCR total
setup gates retained. Exact Serpentskin citations retain original base scope;
generic names allow verified Serpentskin/Wyrmhide upgrade chain. Socket choices
remain full-setup qualifications rather than inferred contents. Hardcore and stale
Poison Nova Budget remain outside these reviewed uses.

Red8missing-role/demand tests. Green24family/stat/source/demand/publication checks
(18in6.84s +6in0.07s), lint/format/diff passed. All18saved reports and prices
unchanged before/staged/published. Published f457b593a0fd23c990d0da7191350d7cd7a93b86479262bd067945d1bcf9d048.
537roles /529stat configurations;126leveling recommendations retained. Data-only;
no additional worker restart or live collection. Details: planning/VIPERMAGI_BATCH.md.
Reproduce: uv run --offline pytest tests/pricing/knowledge/assessment/test_vipermagi_priorities.py
 tests/pricing/knowledge/assessment/test_stat_bundle.py
 tests/pricing/knowledge/assessment/test_profile_sources.py
 tests/pricing/knowledge/assessment/maintenance/test_guide_demand.py
 tests/pricing/knowledge/assessment/test_profile_publication.py -q (one command).
Evidence tmp/vipermagi-*. Census/dossiers updated; final matrix counts follow.

Next candidate: Chains of Honor completed-runeword family, identity
9a55b2bd8647dbf1060a5ac211c28138f83fdee58260dde1a2d5962c5aef28b0.
Current dossier has30distinct-build review leads but zero reviewed guide votes.
Review reusable player versus mercenary use separately, especially ethereal/base,
leech/skills/resistances and actual companion/setup dependencies. This does not
establish all30uses or prices. One more demand batch then scheduled specialist/
leveling/unresolved tail. All-item tier/desirability and exact-price coverage remain
incomplete; goal active.

Published parity and matrix refresh complete:629reviewed /8excluded stat-use quality
rows;2739identities,1569base-quality rows,362evidence records retained.

## Chains of Honor role family — 2026-09-26

Second demand batch after the caster-leveling tail (first: Vipermagi). Added 21
reviewed uses across 13 builds, separating player and mercenary beneficiaries.
Completed recipe, exact base, four filled sockets and known ethereal/identification
status required. Player armor is nonethereal; cited mercenary armor is ethereal.
Mercenary types and player casting/recovery totals are source-specific gates.
Ordinary leech is annotated only for physical mercenary use, not Smite or spells.
Native-skill benefits do not raise fixed item-granted aura levels. Full companion,
prebuff, equipment and encounter dependencies remain qualifications.

Source conflicts remain explicit: Hammer MF Archon/Sacred Armor, Double Throw
CoH/Shaftstop, Dream Ubers CoH/Duress, Mirrored Ubers CoH/Fortitude. Hardcore-only
references and gear-table discovery mentions do not add reviewed Softcore demand.
Detailed membership and locators: planning/CHAINS_HONOR_BATCH.md.

Red: 22 missing-role/demand failures. Green: 32 family/stat/source checks in 11.14s,
plus six demand/publication checks in 0.07s. Lint, format and diff checks passed.
All 18 saved report texts and price results unchanged before/staged/published.
Published generation: 1ca3fa379934d025f154ea584fab7c0a0303ad22265b8ab05f2dfb11308d3c9c.
558 roles / 550 stat configurations; 126 leveling recommendations retained.
Data-only update; no new worker restart, market collection or live capture.
Evidence: tmp/chains-honor-*.

Reproduce with one command:
uv run --offline pytest tests/pricing/knowledge/assessment/test_chains_honor_priorities.py tests/pricing/knowledge/assessment/test_stat_bundle.py tests/pricing/knowledge/assessment/test_profile_sources.py tests/pricing/knowledge/assessment/maintenance/test_guide_demand.py tests/pricing/knowledge/assessment/test_profile_publication.py -q

Next must be a specialist/leveling/unresolved tail. Candidate: reconcile
/blessed-hammer-paladin/variants/2 mercenary Chains of Honor Archon Plate (planner)
versus Sacred Armor (prose), using the pinned original planner and guide context.
Determine whether these are legitimate base alternatives or contradictory evidence;
do not silently label one wrong or universalize all armor bases. Keep originals,
exact source locators/hashes and a durable disposition. Other conflicts are listed
in the batch document. Full named tiers, base desirability, affixed configurations,
leveling/source closure and exact scoped prices remain incomplete. Goal active.

Published parity and coverage refresh complete: 671 reviewed / 8 excluded stat-use
quality rows (21 new configurations each cover normal and superior quality);
2,739 identities, 1,569 base-quality rows and 362 evidence records retained.
No changed/missing census source hashes.

## Hammerdin MF armor reconciliation — 2026-09-26

Scheduled unresolved-source tail after Vipermagi and Chains of Honor demand batches.
Original planner f80206a8 / profile2 SOPaTLww / mercItems.tors24 confirms ethereal
Archon Plate CoH. Original guide MF prose explicitly names Sacred Armor. Retained
both as source-backed examples; no transcription-error claim or universal best base.
Sacred prose has no ethereal condition, so accepts both known statuses; unknown
remains unresolved. Exact requirements and mercenary kill credit remain qualifications.

Added blessed-hammer-paladin-2-merc-chains-honor with native MF priority and completed
recipe/base/mercenary predicates. Source registry now pins original item/profile link,
prose and mechanics as hammer-mf-chains-honor-base-examples. Changed planner link
reopens review. Runtime pins structured WP-A/planner/armor; original HTML hash stays
in maintenance registry. Chains of Honor still has 13 reviewed builds (no inflation).

Red: two missing rule/reconciliation failures. Green: 36 role/stat/source/registry
checks in 12.07s plus six demand/publication checks in 0.07s; lint/format/diff pass.
All 18 saved reports/prices unchanged before/staged/published. Published:
2bc73f6e41a8c4e06f021e2237c10ad4517247af9c8a1c75633fcd915bbaffb6.
559 roles / 551 stat configurations; 126 leveling recommendations retained.
Data-only update; no new worker restart, collection or live capture.
Details: planning/HAMMER_MF_COH_RECONCILIATION.md. Evidence: tmp/hammer-coh-*.

Reproduce: uv run --offline pytest tests/pricing/knowledge/assessment/test_hammer_mf_chains_honor.py tests/pricing/knowledge/assessment/test_chains_honor_priorities.py tests/pricing/knowledge/assessment/test_stat_bundle.py tests/pricing/knowledge/assessment/test_profile_sources.py tests/pricing/knowledge/assessment/maintenance/test_reviewed_source_issues.py tests/pricing/knowledge/assessment/maintenance/test_guide_demand.py tests/pricing/knowledge/assessment/test_profile_publication.py -q

Tail completed; resume two demand/family batches before the next tail. Candidate:
Shaftstop family, identity d7d03c00906ff0580834748d2fa6cecbf5c563a8d4e2b56472cf2bee9f4c1f8b.
Review mercenary damage-reduction/life utility and explicit base/ethereal/upgraded
branches using current dossiers; preserve Double Throw CoH/planner conflict and
Strafe alternative context rather than blindly inheriting named gear. Other source
conflicts, full named tiers, base/affixed/leveling closure and exact prices remain
unfinished. Goal active; final matrix checkpoint follows.

Published parity and coverage refresh complete: 673 reviewed / 8 excluded stat-use
quality rows; 2,739 identities, 1,569 base-quality rows and 362 evidence records.
Four source issues reconciled; broader source closure remains incomplete.

## Shaftstop survival family — 2026-09-26

First demand batch after Hammerdin MF reconciliation. Added five reviewed uses:
Dream Hybrid/Ubers, Lightning Strike Standard, Strafe Standard/MF. Three distinct
builds; Strafe is an alternative, not primary armor. Native 30% physical reduction
is desirable and 60 life supporting. Helmet leech and socket IAS are not attributed
to the armor. Strafe does not inherit primary CoH ethereal status; other cited
uses require ethereal. Explicit Mesh citations retain original base scope; generic
identity uses accept the verified Mesh Armor/Boneweave upgrade chain.

The initial Shadow Plate assumption failed the native mapping assertion before
rule writes. Corrected to Boneweave and added a Shadow Plate rejection regression.
No perfect ED requirement or upgrade price premium. Double Throw's CoH/planner
versus Shaftstop/prose conflict and other guide-table leads remain unresolved.

Red: six missing-role/demand failures. Green: 22 family/stat/source/demand/publication
checks in 6.82s, lint/format/diff passed. All 18 saved report texts and prices unchanged
before/staged/published. Published f56c4ec12a75dbe0c71de90b767583afaf122867320d494577b7570e1d7017f6.
564 roles / 556 stat configurations; 126 leveling recommendations retained.
Data-only; no new worker restart, market collection or live capture.
Details: planning/SHAFTSTOP_BATCH.md. Evidence: tmp/shaftstop-*.

Reproduce: uv run --offline pytest tests/pricing/knowledge/assessment/test_shaftstop_priorities.py tests/pricing/knowledge/assessment/test_stat_bundle.py tests/pricing/knowledge/assessment/test_profile_sources.py tests/pricing/knowledge/assessment/maintenance/test_guide_demand.py tests/pricing/knowledge/assessment/test_profile_publication.py -q

Next candidate: Fortitude family, identity
b70b3ee02dbddba0708dfb1b974b085aa0c78b69556d575e95a9f2e087ff6f71.
Review physical player/mercenary use separately, including armor versus weapon,
base/ethereal/equip requirements, and whether enhanced damage benefits the relevant
attack. Do not promote old ebug descriptions to current mechanics or prices.
One more demand batch, then specialist/leveling/unresolved tail. Full named tiers,
base desirability, affixed patterns, leveling/source closure and exact market prices
remain incomplete. Goal active; final coverage checkpoint follows.

Published parity and matrix refresh complete: 678 reviewed / 8 excluded stat-use
quality rows; 2,739 identities, 1,569 base-quality rows and 362 evidence records.

## Fortitude armor family — 2026-09-26

Second demand batch after Hammerdin MF reconciliation (first: Shaftstop). Added
25 reviewed armor uses across 14 builds, with exact player/mercenary bases and
ethereal scope. Physical ED is desirable; defense/resistances supporting. Armor
ED does not improve spell/trap damage, armor FCR is not attack speed, and the
weapon recipe is a separate use. Native minimum resistance rolls remain useful.
Historical ebug labels cannot establish extra defense or prices.

Full weapon/helmet/equip/IAS/leech requirements remain qualifications. Blizzard's
weapon conflict and Cold Rupture/Insight alternative remain explicit. Fissure
mercenary-type and Mirrored Ubers armor conflicts, unendorsed planner-only variants
and Hardcore-only references remain outside these rules. No global best-base claim.
Details: planning/FORTITUDE_BATCH.md; membership and source locators retained.

Red: 26 missing-role/demand failures. Green: 42 family/stat/source/demand/publication
checks in 14.30s, lint/format/diff pass. All 18 saved report texts and prices unchanged
before/staged/published. Published f1f147f0dcb84b2f1376657fefa6e478024c49a4b83b8893d154002a6a89283a.
589 roles / 581 stat configurations; 126 leveling recommendations retained.
Data-only update; no additional worker restart, collection or live capture.
Evidence: tmp/fortitude-*.

Reproduce: uv run --offline pytest tests/pricing/knowledge/assessment/test_fortitude_priorities.py tests/pricing/knowledge/assessment/test_stat_bundle.py tests/pricing/knowledge/assessment/test_profile_sources.py tests/pricing/knowledge/assessment/maintenance/test_guide_demand.py tests/pricing/knowledge/assessment/test_profile_publication.py -q

Next must be specialist/leveling/unresolved tail. Candidate: Fissure Standard/MF
mercenary type, /fissure-druid/variants/1 and /2. Prose says Might while the planner
uses Holy Freeze, and a separate mercenary section is headed Infinity/Holy Freeze.
Inspect original cached guide and planner dates/links; determine what is actually
endorsed before broadening the type predicate. Preserve alternative/context/source
conflict distinctions rather than silently choosing one. Named tiers, base/affixed/
leveling closure and sufficiently matched market prices remain unfinished. Goal
active; final matrix checkpoint follows.

Published parity and coverage refresh complete: 728 reviewed / 8 excluded stat-use
quality rows (25 new configurations each cover normal/superior); 2,739 identities,
1,569 base-quality rows and 362 evidence records retained.

## Fissure Fortitude aura reconciliation — 2026-09-26

Scheduled source-review tail after Shaftstop/Fortitude. Standard/MF prose supports
Might; original guide mercenary prose supports Holy Freeze for slowing enemies in
area damage. Linked 2026 planner tt9vl0l2 profiles1/2 (QaIr2BVm/Ldr3qiiX) use merc10,
armor23 ethereal Sacred Armor Fortitude. The 2023 vf0106vk profile serves other
contexts and must not supply these links. Preserve both supported aura choices for
the armor component, without claiming identical full loadouts or source typo.

Added fissure-druid-1-merc-fortitude and fissure-druid-2-merc-fortitude. Native
physical ED/defense/resistance priorities reused; no perfect planner roll gate.
Wrong aura/base/ethereal/unknown context rejected. MF helmet jewel discrepancy
remains separate. Registry fissure-standard-mf-mercenary-aura pins original notes,
HTML and current planner item/profile/merc/slot links; modified links reopen review.
Fortitude now has15distinct reviewed builds despite two Fissure uses.

Red:3missing rule/source failures. Green:41family/stat/source/registry tests15.40s
plus6demand/publication checks0.08s; lint/format/diff passed. All18saved report texts
and price results unchanged before/staged/published. Published 3d828011214230bf0ae5eae630dc7aac2ecc0e85e72367f715e33b0724a7f66a.
591roles/583stat configurations;126leveling recommendations retained. Data-only;
no new worker restart, collection or capture. Details:
planning/FISSURE_FORTITUDE_RECONCILIATION.md. Evidence tmp/fissure-fortitude-*.

Reproduce: uv run --offline pytest tests/pricing/knowledge/assessment/test_fissure_fortitude_sources.py tests/pricing/knowledge/assessment/test_fortitude_priorities.py tests/pricing/knowledge/assessment/test_stat_bundle.py tests/pricing/knowledge/assessment/test_profile_sources.py tests/pricing/knowledge/assessment/maintenance/test_reviewed_source_issues.py tests/pricing/knowledge/assessment/maintenance/test_guide_demand.py tests/pricing/knowledge/assessment/test_profile_publication.py -q

Tail complete; resume two demand batches. Next candidate: Andariel's Visage,
identity1540bd6eeed8ba6b9f388f0453286a040eda999b33d23a3673fe30f3c6a347b2.
Current dossier has27distinct-build review leads, zero reviewed guide profile IDs.
Inspect existing Andariel stat/role configurations first to reuse reviewed work;
review exact mercenary/base/ethereal/IAS-jewel branches and fire-resistance penalty.
Do not attribute socket properties to the helmet or boost item-granted aura levels
with all skills. Preserve source conflicts and partial guide coverage. Remaining
named tiers, base/affixed/leveling closure and exact scoped prices unfinished.
Goal active; final coverage checkpoint follows.

Published parity and matrix refresh complete: 732 reviewed / 8 excluded stat-use
quality rows; 2,739 identities, 1,569 base-quality rows and 362 evidence records.
Five source issues reconciled; broader source closure remains incomplete.

## Andariel’s Visage guide family — 2026-09-26

Completed the first demand batch after the Fissure aura reconciliation. Added 30
native helmet configurations and reused both existing Fissure configurations:
32 guide uses across 17 distinct builds. Native IAS and life leech are desirable;
strength and all skills support the mercenary. The fire-resistance penalty, actual
socket contents, full gear breakpoints and equipment requirements remain explicit.
Socket jewel ED is not attributed to the helmet. Existing Fissure jewel and
companion gates remain unchanged. Conflicting armor/weapon branches stay qualified.

Red: 31 missing-role/demand failures. Green: 60 targeted family, existing Fissure,
stat/source/demand/publication tests passed in 23.17 seconds; lint/format/diff passed.
All 18 saved report texts and price outcomes remain unchanged. The initial replay
used September 25; the final run advanced only the price-policy as-of date to
September 26. Replaying staged and published data on the same date confirmed exact
text and complete price-object parity.

Published generation:
3a4a478975fe30e681a3f752fc1e5ec9120a0b77941f375fdf5e3e4b368aec1c.
621 roles / 613 stat configurations; 762 reviewed / 8 excluded stat-use quality
rows. Retained 126 leveling recommendations, 362 evidence records, 2,739 identity
buckets and 1,569 base-quality rows. Five source issues reconciled. Inventory,
dossiers, base matrix and coverage matrix refreshed. No new market collection,
live capture or additional worker restart. Details:
pricing/knowledge/assessment/planning/ANDARIEL_GUIDE_BATCH.md.
Evidence: tmp/andariel-family-*.

Reproduce: uv run --offline pytest tests/pricing/knowledge/assessment/test_andariel_guide_family.py tests/pricing/knowledge/assessment/test_andariel_stat_priorities.py tests/pricing/knowledge/assessment/roles/test_fissure_andariel.py tests/pricing/knowledge/assessment/test_stat_bundle.py tests/pricing/knowledge/assessment/test_profile_sources.py tests/pricing/knowledge/assessment/maintenance/test_guide_demand.py tests/pricing/knowledge/assessment/test_profile_publication.py -q

Next: one more demand/family batch, then a specialist/leveling/unresolved tail.
Vampire Gaze is a candidate: inspect its current dossier and reusable configurations
before selecting exact mercenary variants, survival alternatives and base upgrades.
Do not rank solely by mention count or turn guide demand into numerical prices.
Full named tiers, base/affixed/leveling coverage, unresolved identities and exact
scoped market cohorts remain incomplete; this is an incremental M1 checkpoint.

## Vampire Gaze expansion — 2026-09-26

Second demand batch after the Fissure tail: four native configurations for Smiter
Standard/High Investment and Strafe Standard/MF. Existing six Gaze configurations
and their socket requirements retained. Six distinct reviewed builds; Strafe is
an explicit survival alternative. Leech and physical DR desirable, magic DR
supporting; mercenary mana leech and unverified jewel IAS not promoted. Grim Helm
only in these source-specific uses; Smiter ethereal, Strafe alternative accepts
known ethereal/non-ethereal. Pride leech limitations and Smite/Life Tap versus
ordinary leech remain explicit. Native uniqueitems /208 verifies stats.

Red: 5 failures. Green: 38 tests in 12.94 seconds, lint/diff passed. All 18 saved
report texts and complete price results unchanged before/staged/published.
Published 2b058eab9fba417ff57fc247b6b64c5e9f8b86dfeecc9904d589520b13ed2db5.
625 roles / 617 stat configurations; 126 leveling recommendations retained.
Evidence tmp/gaze-*. Next scheduled leveling tail is already in progress: missing
class-specific jewelry and Homunculus recommendations, including exact source
aliases and native requirement levels. Full coverage remains incomplete.

## Leveling jewelry and Homunculus tail — 2026-09-26

Completed scheduled tail after Andariel/Gaze. Eleven new exact guide recommendations:
Mara's Kaleidoscope for Barbarian, Druid, Necromancer, Paladin and Sorceress;
Homunculus for Necromancer; Raven Frost, SoJ, Etlich, Cat's Eye and Highlord's for
Amazon. Exact Maras aliases retained with original source locators. Native equip
levels retained (Mara67, Homunculus42, Raven45, SoJ29, Etlich15, Cat50, Highlord65).
Homunculus source all-skills wording corrected to Necromancer skills. Highlord's
Deadly Strike does not increase Lightning Fury lightning damage. Respec scopes,
shield/CBF tradeoffs and optional late-level availability retained.

Red:11missing recommendation failures. Green:94 recommendation/runtime tests in
6.98seconds; lint/diff passed. All18saved report texts and complete price results
unchanged before/staged/published. Published 26969dd9f8c2becf607caf5dac8266e9bb9da46db9953b9afe3bd4f2fa771a2c.
137leveling recommendations,625roles/617stat configurations at publication.
No market collection or new hot-path Python changes. Evidence tmp/leveling-jewelry-*.
Tail complete. Treachery family is the first next demand batch and is in progress.
All-item pricing/tier/base/affixed and remaining source coverage still unfinished.

## Treachery mercenary family — 2026-09-26

First demand batch after leveling jewelry tail: fourteen new exact mercenary
configurations; existing Fissure and shared Smiter rules retained. Sixteen distinct
reviewed builds. Native Fade when struck supports survival after activation;
ordinary mercenary roles also prioritize IAS. Dual-Plague Uber roles do not promote
IAS or defense maximization; Lightning Sorceress is restricted to Uber Mephisto.
Full base/ethereal/recipe/equip and wearer qualifications retained. Source LFury
"avoiding high Attack Speed" conflicts with native IAS and remains qualified;
Double Throw armor, Summoner helmet and linked-planner aura distinctions preserved.
Native source: runes.json /Treachery; exact membership in test_treachery_guide_family.py.

Red:15missing rules/demand failures. Green:33family/source/publication checks11.55s
plus12existing Fissure/specialist checks5.34s; lint/diff pass. All18saved reports and
complete price results unchanged before/staged/published.
Published 3b6199f3899b6708f7111d082f280662ec87dc5a757c1d33418d88cd66370cdc.
639roles/631stat configurations;137leveling recommendations retained.
Evidence tmp/treachery-*. Bulwark is the second demand batch, already in progress;
then perform specialist/leveling/unresolved tail. Full coverage remains incomplete.

## Bulwark mercenary family — 2026-09-26

Second demand batch after jewelry leveling tail. Seventeen new exact starter/budget
mercenary configurations; existing Fissure role retained. Eighteen distinct builds
at publication. Native Non-Ladder leech/physical reduction desirable; maximum life
and recovery supporting. Minimum rolls accepted. Exact base/ethereal/recipe/context
conditions retained; no jewel IAS or perfect defense inference. Double Throw armor
conflict does not discard its supported helmet. FoH aura and Summoner/Fire Blast
helmet source differences were deferred for separate review. Full member list in
test_bulwark_guide_family.py; native runes.json /Bulwark. No Ladder revision imported.

Red:18missing role/demand failures. Green:40tests16.10seconds; lint/diff pass.
All18saved texts and complete price outcomes unchanged before/staged/published.
Published 667936b4cc7dec6b038c5390b3a25814971e9d94c34b37cc167f7aeae7e3216b. 656roles/648stat configurations;137leveling recommendations.
Evidence tmp/bulwark-*. Scheduled FoH aura reconciliation tail is now implemented
and under broader verification. Remaining all-item coverage is incomplete.

## Named tiering priority and verification — 2026-09-26

User priority: complete tiers for all unique/set identities before further particular
item handlers. GUIDE_FIRST.md and NAMED_TIER_ROLLOUT.md now specify this ordering.
Generated appraisal-tier-inventory.json: 565 identities, 93 reviewed, 472 pending.
Retains census evidence, separate historical guide grade, native set membership and
exact-identity leveling references. Missing evidence never assigns trash. Red import
failure followed by 2 passing tests; lint/format clean. No new tiers claimed yet.
Prepared Crown of Ages/counted socket-jewel work remains deferred in tmp.

FoH aura reconciliation finished: two starter Bulwark roles accept the documented
Might/Holy Freeze source alternatives; source mismatch remains explicit. Published
c96abceeeb3622b0a4dbc9608938741b1e1cdc23d0a2ab66234a489e01fc59c0.
All 18 staged/published saved report texts and price outcomes match. Runtime total
658 roles / 650 stat configurations; 137 leveling recommendations. Guide inventory
refreshed; broader dossier/base/coverage matrices still need refresh after tier work.
Full-suite run: 3497 passed, 3 skipped, one source-fixture failure. Fixed the fixture
to pin all corroborating references to its temporary source; the affected repository
and profile-source suites then passed (14 tests). Production validation unchanged.
Do not describe this as a full-suite rerun. Evidence: tmp/foh-bulwark-*,
tmp/assessment-continuation-full-tests.txt and tmp/tier-inventory-red.txt.

## Published named-tier baseline — 2026-09-26

Completed the user's broad unique/set baseline priority before resuming detailed
item handlers. 548 explicit policies: 140 set pieces and 408 uniques. All original
93 policies are unchanged. Defaults: high19/med38/low394/trash97; overrides can
change a captured variant's tier. Full table:
pricing/knowledge/assessment/planning/NAMED_TIERS.md.
Seventeen native records have explicit non-tier dispositions (6quest,10unfinished
placeholders,1disabled Constricting Ring), preserved in the 565-identity census.
The inventory has zero unexplained pending identities; ordinary tier-policy coverage
remains548/565. Neither measure claims complete variant or numerical-price coverage.

New rules reference rules/named_tier_reviews.json (native facts, historical guide
rows, current build IDs, leveling IDs, pinned inputs). Guide dated2024-03-06 is
historical early-ladder demand/utility evidence, not NL prices. Qualitative baseline
priorities are labeled guide/native review in reports. Strong exactly matched dated
market evidence can refine them; stale/thin/wrong-variant asks retain the baseline.
Shared variant_rules require exhaustive disjoint native table IDs (Rainbow Facet).

Validation: set rollout red8 -> green8; unique/variant and report-label red-green;
full suite3606passed/3skipped/1outdated Atma baseline expectation. Corrected that
expectation (initial low remains immutable while exact asks resolve med), then309
policy/priced-result/inventory tests pass. No second full-suite claim. Lint/format
and diff checks pass. All18 saved price objects unchanged; published report text
matches staged text. Four saved reports gain tier lines. Source-aware labels do
not call qualitative opinions cached asks.

Published generation e8157a20366d9342a94d677a31f7e9f43fa965450b85ce5bec9d46293444a6de (54artifacts).
Restart Alt+D worker once for Python variant/precedence/report changes. Future
ordinary data publications are selected at request boundaries. No live collection,
new host probe, staging or commit. Guide inventory, review dossiers, base matrix,
coverage matrix, tier census and readable inventory refreshed. A premature matrix
attempt was discarded after stale-source validation; dependencies rebuilt before
successful refresh and publication.

Next: detailed item/variant work. Renewed sunder generated-affix premiums and
collector/perfect-defense premiums are not covered by identity baselines. Warlord
availability is explicitly unverified; its tiers are conditional native-utility
judgments, not drop-location claims. Prepared Crown of Ages/counted-jewel work is
still in tmp pending files; it was not applied by this tier rollout. Numerical
SC/NL/PC/RotW estimates still require actual sufficiently matched cached evidence.
Evidence: tmp/named-tier-*. Rebuild tier inventory with
uv run --offline python -m pricing.knowledge.assessment.maintenance.tier_inventory.

## Tier visibility and queued defensive items — 2026-09-26

Published 666e92f5fc7a7059377f300e0e9e94a8a51e3691d582b98d6566856539a2d298. Trade and leveling colors high green / med yellow /
low blue / trash red. Socketed nonethereal Shako now keeps its underlying med tier;
socket additions excluded and native defense segment withheld when filled.
Griswold’s Heart already had low trade tier; the missing highlight was the issue.

Crown of Ages adds two exact setups and a counted compound-jewel predicate.
Stormshield adds four Softcore configurations (one explicit Amazon alternative).
Spirit Shroud gains conditional leveling advice from transcript15:56, native
level28/Strength38; original source2025-04-24 retained. Runtime664roles /656stat
configurations;138recommendation rows (151linked leveling evidence rows).
Full suite3649passed/3skipped in544.39s; final targeted58pass. All18 staged price
objects unchanged. Published replay verification in tmp/tier-crown-stormshield-*.
Worker restart required for renderer/predicate code; no live collection or commit.

Continuing by explicit user request until all queued work is handled. Enigma35
source configurations and Raven Frost19 have red tests prepared and are currently
being implemented; Sigon boots/belt conditional leveling tail follows. Remaining
all-item coverage remains open; do not describe identity tiers as full guide/price
closure. See CROWN_STORMSHIELD_BATCH.md and tmp/enigma-raven-* for current work.

## Enigma/Raven and Sigon tail published — 2026-09-26

Generation c99da49b9295c5d23ed3687dc4d6ac52f0c8a2337eb0ae153acdf9197510e613,54artifacts.718roles/710stat configurations,
140leveling recommendation rows. Enigma35configurations/20builds and Raven
Frost19/10builds added. Sigon boots/belt conditional recommendations retain
2pieceAR/3pieceMF and70/60Strength costs. Sources pinned and prior rows preserved.
56red ->56green; affected suite428pass; Sigon/recommendation50pass; lint/format
pass. All18 staged/published report texts and prices match; numeric prices unchanged
from previous generation. See ENIGMA_RAVEN_BATCH.md.

Continuing: Heart of the Oak11caster/swap uses across8builds (12new tests pass),
Griffon’s Eye14uses across6builds (15new tests pass). Socket matcher now accepts
Colossal Jewels (native cjwl Equiv1 jewl), red/green17socket tests. These latest
changes are being rebuilt/validated, not yet published. Working scripts/evidence
are tmp/add_hoto.py,tmp/add_griffon.py,tmp/hoto-*,tmp/griffon-*. Next required
tail: Rhyme Starter use coverage; only Mirrored Grimoire currently reviewed.
Do not stop after publication: user explicitly requests continuing all queued items.

## User-requested pause: universal tiers first — 2026-09-26

Stop unrelated implementation. The latest Guardian Angel capture at
inventory_tracking/runs/alt-d/20260926T102641Z-b5aa4b20/latest.json is nonethereal
and has pending_review/tier=null. Its policy only covers ethereal200ED. This proves
the earlier548-policy completion claim was insufficient; the missing tier remains
unfixed at this checkpoint. The user requested a plan update, not more coding.

Authoritative next plan: pricing/knowledge/assessment/planning/NAMED_TIER_ROLLOUT.md.
Scan all gathered builds/variants/mercenary gear/alternatives. Assign baseline trade
tiers high/mid/low/trash to EVERY eligible unique, set piece and complete set;
review separate leveling tiers for valuable leveling items and combinations.
Keep premiums separate: failed/unknown roll, ethereal or socket-premium conditions
must not erase the baseline. Verify actual rendered coverage, not policy presence.
Only resume other queued work after the universal tier gates pass and are published.

Current published generation:
c99da49b9295c5d23ed3687dc4d6ac52f0c8a2337eb0ae153acdf9197510e613.
Hoto11, Griffon14, Rhyme14new+1updated role and Colossal Jewel matching correction
are staged, not published. Local bundle757roles/749stat configurations. Preserve
those edits and their tests; do not continue them while this priority is paused.
No Guardian Angel code fix, new publication, live collection or commit in this
planning update. The earlier “continue until all queued items” instruction is now
subordinate to the user's explicit universal-tier gate and pause.

## Phase1 published; phase2 active — 2026-09-26

Selected generation: `39ee03c46fb5d42f6ab70d1b8a5484e80d23ce87113478f660c82174bdc6cfe9`
(58artifacts). Universal tier gate passes:408uniques +140set pieces,35parent sets,
17explicit native exclusions,2958rendered cases, zero missing baselines or leveling
review dispositions. Existing63 leveling identities plus124 supplemental uses/
combinations are retained. All gathered34builds/591variants/62891occurrences remain
accounted for; shared-planner ambiguities stay explicit in the guide inventory.

Full run:3813passed/3skipped/4failed in987.55s. All four failures were the same
pre-existing interaction between Colossal Jewel support and unscoped Rainbow Facet
upper bounds. Scoped the bounds to Rainbow Facet in three Fissure roles and renewed
their stat/guide review fingerprints. Final affected suite:408passed/30.92s,
including all four failures and an additional10%-Colossal +3%-Facet regression.
All18published saved-item replays match staged output and numeric prices; only
published artifact provenance contains the additional complete-bundle pins.
Actual Guardian/Griswold/socketed Shako captures also pass through the selected bundle.

Tier suffixes `(cached asks, DATE)` and `(guide/native review, DATE)` are removed;
JSON provenance remains. Restart the host worker for these Python changes; the
agent does not start/stop it (see working-process rule below). No new live probes,
market fetches, staging or commits were done.

Phase2 now resumes the entire assessment queue, not just top items. The previously
staged Hoto/Griffon/Rhyme work is included in this publication (757profiles/749stat
configurations). Next review the broad unique-charm family (Annihilus/Torch), then
continue demand and specialist/base/pattern batches without declaring catalog or
routing coverage to be complete assessment. Numeric price gaps remain explicit.

Evidence: tmp/phase1-{full-suite,final-tests,publication,published-replay,
published-captures}.*, pricing/data/appraisal-named-gate.json.


## Phase2 family rollout — 2026-09-26

Published unique-charm and mercenary/Lionheart batches: generation
`39e6008533b1bf57fda9b435aaac94d56e5389bc3bcaf9de8e91af8cd71be7b0`,
925 profiles /917 stat configurations. Universal named tiers remain complete.
67 Torch uses plus8 Annihilus variants,85 early mercenary alternatives,7 Cure
specialist setups and Strafe Lionheart player/base utility are reviewed.
37 Torch aliases resolved without changing prices or original labels. Pinned
source reviews reconcile Mirrored's class label and Nova's unsupported healing wording.
All18 saved report prices/extractions/text remain unchanged. No live collection.
The next50 footwear alternatives are staged, pending broad validation/publication.
This closes these rules, not all item, guide-variant or market-evidence coverage.


## Embedded evidence validator — 2026-09-28

Implemented maintenance/embedded_evidence.py after the seven failing tests in
maintenance/test_embedded_evidence.py. It pins raw guide/planner hashes, verifies
exact tooltip context and set identity, fingerprints the parent definition and
resolves socket children without converting evidence resolution into semantic approval.
Five further graph tests reject missing children, cycles, malformed references and
ambiguous sets. The combined embedded/completion suite passes: 57 tests; Ruff and
format checks pass. Actual Abyss helmet items 143,144,140,141,142 validate, preserving
jewel135 references in143/144. Durable evidence is ABYSS_EMBEDDED_EVIDENCE.json in this
planning directory. It is explicitly pending semantic review, not completion credit.

Next: integrate a reviewed embedded-use disposition compiler into completion with
exact role/use fingerprints, identity and wearer/slot constraints; add its code/data
to completion fingerprints. Then implement/review the five helmet uses and their
independently authored item-bank scenarios. Do not discharge all397 embedded links
on source resolution alone. No publication/runtime behavior changed in this pass.
The universal all-item goal remains active and incomplete. Sacred Rondache saved
replay again shows Spirit/+27 vs45/socket preparation; two tests passed, but host
Python delivery remains unverified. No live collection, restart, staging or commit.


## Embedded semantic review ledger — 2026-09-28

Added maintenance/embedded_reviews.py and rules/embedded_reviews.json; completion.py
now compiles those reviews, fingerprints their data and validation dependencies,
and publishes embedded_dispositions. Exact raw guide/planner evidence, role/use
fingerprints, reviewed SC endorsement, primary span, embedded corroborating pointer,
and compatible wearer/slot/build are mandatory. Supported equipment-table slot
contexts are explicit; unsupported contexts stay pending. No blanket source credit.
Three previously reviewed Abyss daggers (Void, Rare Kriss, Arch-Devil Kriss) are
bound to exact refs1/120/226. Their existing runtime rules were not changed.

Red:9 missing-compiler failures. Green:84 related tests, then10 embedded-review
tests including scope-fingerprint invalidation; Ruff passes. Real completion CLI
finished successfully:112735 remaining,3 reviewed embedded refs,394 pending.
Verified reviewed ids are absent from queue and all other embedded tasks remain.
Sources retain1643 reviewed occurrences; embedded review does not silently discharge
planner inventory occurrences. Current selected generation unchanged.

Next concrete work: implement/review Abyss embedded Helmets143/144/140/141/142,
using planning/ABYSS_EMBEDDED_EVIDENCE.json (source proof only) and
ABYSS_EMBEDDED_CONTEXT.md. Add exact embedded review rows only after their role/use
and native-decoding item-bank tests exist. Check magic tab normalization and jewel135
before stat policies. Pending worker delivery and missing Meteor planner remain;
independent all-item work continues. No live collection, restart, staging or commit.


## Abyss embedded helmet rules published — 2026-09-28

Added five roles abyss-warlock-table-embedded-helmet-{rare,magic,coven,hellwarden,horazon}
and five stat reviews;2517profiles/2509statconfigs. Native source check: magic Diadem
mp705 is Torrid +3Chaos, native188:58. Guardian'sLight child135 is unique425/cjw
(Colossal Jewel), not a generic resistance jewel. Coven baseuh9=BoneVisage;
Horazon baseusk=Demonhead (earlier handoff description was wrong).
Rare2class/20FCR and magic3Chaos/20FCR are caster alternatives; sockets optional.
Coven exact BoneVisage3s plus actual rune stats; all3ordinaryqualities. Hellwarden
minimum magicpierce5/skill/FCR no inherited EchoingUbers companion/jewel dependencies;
IAS/firepierce excluded from Abyss priority. Horazon standalone skill/str/MDR only.

54 independent native-decoding bankcases red missingroles; then54staged/selectedgreen.
One test corrected to use wrongsamefamilyDemonhead, since circlet is excluded by
candidate routing before predicate tracing.2statbundle tests,55embedded/completion
tests,lint pass. 20staged/selected saved reports+prices match exactly.
Selected generation16eab754bbda8bbab51c9c8eb2cb154b182219bcba06921b990bd0138cc8eef4
(79artifacts). Rebuilt index,sourceaudit,bankcoverage,matrix and completion.
Completion112770remaining,8161coverage rows;6embeddedreviewed/391pending. Additional
quality rows add real unresolved obligations; no closure claim. Raw occurrence review
count1643 unchanged. Three named embedded refs140/141/142 received validated reviews.
Rare/magic refs143/144 still pending actual socket-payload cases and stat review.

NEVER rerun successful tmp/add_abyss_embedded_helmets.py. Logs tmp/abyss-embedded-helmets-*.
Next: add independent actual143/144 examples with Guardian'sLight+Ist/Um, native
357magicmastery/358magicpierce contributions, actualcharges and resistances; ensure
empty/unknown contents cannot invent jewel bonuses. Then finish their embedded
reviews and remaining source occurrence links. Continue all other contract queues.
No livecollection,restart,staging,commit. Host delivery remainsunverified.


## Actual Diadem payloads published — 2026-09-28

Updated rare/magic Abyss embedded helmet stat priorities for observed357magicmastery
and358magicpierce. Pinned Guardian'sLight unique425 and actual Ist/Um rune definitions.
Flat magic attack damage, when-struck trigger and Telekinesis charges do not receive
passive Abyss spell credit. Unknown children do not erase known parent totals;
missing parent bonuses are never synthesized from child data.

Added item_bank/cases/abyss_diadem_payloads.py:10 independent cases (actual,unknownchild
withobservedtotals,empty,unknowncontents,childonly) for both qualities. Parent socket
stat194 now explicit. Shared bank SocketItem supports exact unique name and native
child ItemData; Item.capture invokes live annotate_sockets, so report names are
verified through production identity decoding. New raw identity helper validates
unique name/base. Only16bankcases have194;10new+6Talmerc cases were exercised.
Red4missingstatpriorities/6pass; then2reportfailures uncovered missing test-harness
socketannotation. Final10casesgreen +60helmet/Talregressionsgreen;70selectedgreen.
4statbundle/socketpayload tests and13embeddedreview tests pass;Ruff passes.

Selected generationfb3bad564274c4d9334ae1539c8523b42b151e8ea724d767b04bd342b57c7074,
79artifacts.20saved selectedreports/prices exactlymatch staged. Completion112768
remaining,8embeddedreviews/389pending;2517roles/2509statconfigs. No completion claim.
NEVER rerun successful tmp/review_abyss_diadem_payloads.py or
 tmp/link_abyss_diadem_payloads.py. Logs tmp/abyss-diadem-payloads-*.

Next Abyss BodyArmors embedded refs145(span45),146(span51),sameplanner/setdm4EcrJ5:
145 Authority MagePlate(xtp),HelShaelRal3s,2Warlock,ED60. Planner encodes
item_skillongethit#387#2=10 and item_skillonhit#399#10=15; verify chance/level semantics
against native Authority and saved screenshot before assigning trigger use.
146 Horazon'sDominion RussetArmor(xpl),set136,2DemonSkills (planner tab21=>native188:56,
NOT Eldritch/Chaos),EDef100,mana100,cold/fire/light25. Native lowrollsEDef75,mana75,res15;
conditionalset poison25/vit15/DR15 require companions. Demon skills don't directly
add Abyss ranks; separate summon/Bind support must be reviewed. Also link source
occurrences explicitly (embedded reviews do not autoapprove inventory occurrences).
Continue all contract queues; missingMeteor1r010653 and runtimehostrestart unresolved.
No livecollection,restart,staging,commit.


## Abyss Authority/Dominion published — 2026-09-28

Added abyss-warlock-table-embedded-armor-{authority,dominion},2statreviews;
2519profiles/2511statconfigs. Authority exactMagePlate3sHelShaelRal/all3ordinaryqualities,
nonethplayer;Warlockskills/FHR/fire resistance highlighted;ED/procs not passiveAbyss.
Dominion RussetArmor or upgradedBalrogSkin,0/1socket/noneth,lowestEDef75/mana75/res15
retained;188:56DemonSkills supporting BindDemon utility separately from Abyss ranks.
Pinned exactguideSkillssection14 as evidence for BindDemon. Setcombo extras conditional.

Confirmed cachedplanner reverses chance/level for Authority AND Guardian'sLight:
Authority savednativecapture2%lvl10PsychicWard(201:24778),10%lvl15Miasma(198:25551).
Guardian nativeunique425/function11:1%lvl25PsychicWard(201:24793),not cached25%lvl1.
Corrected independentdiadem payloadcases and source-reviewnotes/fingerprints forrare/magic
helmets;rawsource untouched. No inference from triggers into passivecasterdamage.
33newarmorcased red;43armor+diadem staged/selected green;24decoder/statbundle tests;
30embedded-evidence/trigger tests;Ruffpass. BodyArmors slot alias red1→green now supported.

Selected86c9a05d4e3a74978819951dc140bf9ff458aafb7386e44cbbd483a5c5cc4f5b,
80artifacts (Authoritysavedcapture is now pinned evidence).20saved reports/prices
exactlymatch staging. Rebuilt alldependencies,index,sourceaudit,bankcoverage,completion.
10embeddedreviews/387pending. Completion112789remaining/8165rows,occurrencereview1643.
Newrolequalityrows carry real unresolved obligations; no all-item completion claim.
NEVER rerun successful tmp/add_abyss_embedded_armors.py or tmp/link_abyss_embedded_armors.py.
Logs tmp/abyss-embedded-armors-*.

Next: explicit remaining Abyss BodyArmors table spans44Enigma,46Stealth,47ChainsHonor,
48QueHegan,49Vipermagi,50Skullder,52TalArmor. Some wp-a slots already have reviewed
roles (Stealth,Skullder,Tal,QueHegan),so inspect equivalence/source links before
adding duplicate rules. Enigma existingStandard/MFvariants may differ from general
alternative. ChainsHonor existingAbyss role is MERC only; don't reuse wearer blindly.
Vipermagi no currentAbyssnamedrole found. Then remainingtable/sourceoccurrences and
allothercontractqueues. Hostdelivery and missingMeteor1r010653 unresolved;independent
work continues. No livecollection,restart,staging,commit.


## Reused Abyss armor rules with exact table links — 2026-09-28

Added maintenance/table_equivalence.py and rules/table_equivalence_reviews.json,
wired into completion inputs/policy/scope fingerprints and table_dispositions.
Exact named Mainalternatives/player/slot/build/class rule, reviewed endorsement,
primarywp-a slot string, rawHTML/cache equality and pinned occurrence/rule/use/source
fingerprints required. Different variants, wearer, slot, name, source or duplicates
fail closed. Native corroborating sources validated. No duplicate runtime rule.
Four raw Abyss BodyArmors spans46Stealth,48QueHegan,50Skullder,52TalArmor now reviewed
through their existing wp-a slot rules. Completion source-review count1647 (was1643),
remaining112785. Fourexact ids removed from queue; role/stat counts2519/2511 unchanged.

Added39 independent selected-generation bankcases for those4existingroles: all3Stealth
qualities, wrong/unknownclass and ethereal facts, empty/unknownsockets, native/upgraded
armor, Skullderethereal observed/missing/unknownrepair and MF100atlevel80, Talstandalone
bonuses without setFCR. All39 pass. Sourcecompiler9redmissing→green;54combined source/
completion tests pass (includes source-hash and scope invalidation). Ruffpass.
Bankcoverage regenerated. No runtime rule or artifact change, so no republish required;
selected86c9a05d4e3a74978819951dc140bf9ff458aafb7386e44cbbd483a5c5cc4f5b retained.
Logs tmp/table-equivalence-red.log and tmp/abyss-existing-armors-*.

Next: Abyss remaining BodyArmors44Enigma,47playerChainsHonor,49Vipermagi. Enigmaexisting
Standard/MFcontexts may carry extra requirements; inspect before reusing. Existing
Abyss ChainsHonor is merc-only. Vipermagi lacks currentAbyssnamedrole. Then all other
contract queues, including sourceoccurrences, variants, market/reports and finalgates.
MissingMeteor and hostdelivery still unresolved;independentwork continues. No live
collection,restart,staging,commit. Goal remains active;this is not completion.

## Remaining Abyss armor alternatives and named glove/belt links — 2026-09-28

Published generation cfec4864ea55441011abde40a459f4ee076a1ef9b41b1e35c75cbe0ae2ba2295
(80 artifacts). Added source-reviewed player rules abyss-warlock-table-armor-
{enigma,coh,vipermagi}, exact raw guide spans44/47/49. Enigma supports legal armor
bases, all ordinary qualities, three filled sockets and nonethereal player use;
the existing Standard/MF Mage Plate configurations remain separate. Player CoH
supports legal four-socket armor and credits skills/resists, not leech/demon/undead
attack bonuses as Abyss damage. Vipermagi supports minimum rolls, original and
upgraded bases,0/1socket. Role/stat counts now2522/2514.

Independent remaining-armors item bank:68red before rules,68green staged,68green
selected. Fourteen stat-bundle/table-equivalence tests pass; Ruff passes. All20
saved reports AND price estimates exactly match staged/selected. Planner source
audit, bank coverage and completion regenerated. Existing named glove/belt rules
were independently checked in54selected bankcases (original and both upgraded
bases, minimum utility, wrong/unknownclass/ethereal, impossible sockets, no attack
properties credited as Abyss cast damage). Three exact table links added for
Magefist54,ChanceGuards56,Goldwrap59 via table_equivalence; no duplicate runtime
rules. Seven table-equivalence reviews total. Completion reviewed occurrences1653,
remaining112820: newly enumerated role/quality obligations increase the queue; this
is not a final gate pass. No full-suite or whole-bank run claimed.

Successful one-shots NEVER rerun: tmp/add_abyss_remaining_armors.py,
tmp/link_abyss_remaining_armors.py,tmp/link_abyss_existing_gloves_belts.py.
Logs tmp/abyss-remaining-armors-* and tmp/abyss-existing-gloves-belts-*.

Next source queue: Abyss gloves53TrangClaws,55embedded,57crafted; belts58Arachnid,
60crafted,61/62embedded. BloodBoil generic profiles can inform new rules but inspect
semantics independently. In particular the BloodBoil TrangClaws template currently
accepts only native HeavyBracers; review legal set upgrade to Vambraces before
reusing (do not silently inherit a potential missing upgrade). Arachnid native
SpiderwebSash,20FCR/1skill/5percentmaxmana; slow/chargedVenom are not Abyss spell
bonuses. All broader contract queues still apply. Missing Meteor source and host
runtime delivery still unresolved; independent work remains. No live collection,
restart,staging or commit. Goal stays active and unfinished.

## Abyss Trang gloves and Arachnid belt — 2026-09-28

Published1b2259d701b1f3daf736dad4550de7219342dbbfcc70b83567d045bc4920c003
(80artifacts). Added abyss-warlock-table-trang and abyss-warlock-table-arachnid,
exact named player spans53/58. Trang supports native HeavyBracers and upgraded
Vambraces (native cube154 pinned),20FCR/30coldres/defense; Necromancer Curses do
not become Warlock skill ranks. Arachnid supports native SpiderwebSash,minimum
90EDef,1skill/20FCR/5percentmaxmana. Native slow is10percent and Venom is level3,
11charges (not the20slow/30charges previously guessed in notes). Neither is an
Abyss passive damage bonus. Nonethereal sustained player rules and0sockets.

21bankcases red before rules,green staged andselected (original/upgradedTrang,
minimumroll,wrong/unknownclass,ethereal/unknownethereal,invalid/unknownsockets).
2statbundle tests andRuffpass. All20saved reporttexts andpriceestimates exactly
match staged/selected. Source audit,bankcoverage,completion rebuilt.2524profiles,
2516statconfigs.1655reviewed sourceoccurrences,112828remainingtasks: newquality/
pricing obligations remain; no final gate/fullsuite/wholebank success claimed.
Never rerun successful one-shots tmp/add_abyss_named_glove_belt.py or
 tmp/link_abyss_named_glove_belt.py. Logs tmp/abyss-named-glove-belt-*.

Pinned4new embedded source definitions into planning/ABYSS_GLOVE_BELT_EVIDENCE.json
with validate_embedded_evidence. This is discovery only, no semantic completion.
Exact contexts: span55item147HorazonHold(set137,DemonhideGloves),span57item92caster
BrambleMitts,span61item152GheedWager(unique418,TrollBelt),span62item148BaneAuthority
(set134,LightBelt). Allplanner gsg0p0l0; item92setdGH5vCiB,othersdm4EcrJ5.
Next review those4 plus legacy span60CasterCraftedBelt x2cpo0l5/item28. Embedded
semanticcompiler still needs explicit Gloves/Belts slot support with tests when
adding reviews. HorazonHold native10CB/95–150AR/10–15dex/140–270fire/30–40life;
onlylife/dex obvious standalonecasterutility; do not assume setcompanions.
Bane belt10FCR/20life;15energy requires setpieces. GheedWager10–20FCR/FHR/FRW,
90–150EDef,3–7magicpierce,5–15allres,44–75gold. CraftedBrambles actual30fire/light/
coldres,25MF,10manaregen,20mana,3MAEK; noFCR. Check requiredaffix thresholds rather
than requiring everyperfectexample roll.

Additional discovered obligation:6older generic Trangcasterprofiles restrict
base to xmg only (frozen-orb-sorceress,blood-boil-warlock-guide,hydra-sorceress,
fire-wall-sorceress-guide,frozen-orb-meteor-sorceress,summoner-warlock-guide).
Review/fix upgradedVambraces across these with their exactsource/use/stat/context
fingerprints and independentbank cases. Do not blindly alter exactloadout rules.
Broadergoal andmissingMeteor/hostdelivery remain unresolved. No livecollection,
restart,staging orcommit. Continue independentwork;goal remainsactive.

## Trang caster upgrades across six builds — 2026-09-28

Fixed the six older standalone caster Trang profiles noted above. They now accept
Heavy Bracers and upgraded Vambraces; wearer class, nonethereal status, zero sockets,
and intrinsic FCR/cold resistance/defense priorities remain intact. These are generic
Gear alternatives, not exact loadout base substitutions. Native cube recipe 154 is
pinned in every affected source review. Updated each guide-use and stat-review
fingerprint and review rationale; no other source-context records referenced them.
Do not rerun the successful one-shot tmp/fix_trang_caster_upgrades.py.

The independent bank has 72 native/upgraded scenarios across Blood Boil, Summoner,
Fire Wall, Frozen Orb/Meteor, Frozen Orb and Hydra. Before the fix: 18 failures,
54 passes; after: all 72 pass both staged and selected. The failures were upgraded
positive and unknown-fact cases, confirming the old base restriction. Six stat/
demand tests pass. Embedded semantic reviews now support exact Gloves and Belt/
Belts slots: three new tests failed before the mapping and pass after it; cross-slot
rebinding remains rejected. All 29 embedded review/evidence tests and Ruff pass.

Selected generation: 0cb296e0120acd89d0e2f825a7a7a43d97d9d987b2ab8df62b83fdde60bd2508
(80 artifacts). All 20 saved report texts AND price estimates match staging.
Source audit, bank coverage and completion regenerated. Counts remain 2524 profiles,
2516 stat configurations, 1655 reviewed occurrences, 112828 remaining tasks. This
fix improves variant correctness without creating duplicate profiles or claiming
new source occurrences. No full suite/whole bank/final completion claim.
Logs: tmp/trang-caster-upgrades-* and tmp/embedded-gloves-belts-*.

Next: the four pinned Abyss embedded glove/belt definitions in
ABYSS_GLOVE_BELT_EVIDENCE.json, plus legacy span 60 crafted belt. Its local planner
pricing/raw/mr/planners/x2cpo0l5.json exists: item 28 is crafted Sharkskin Belt
(base zvb), crf085 [10,20,10], 30 fire/light/cold resistance, 24 FHR, 10 mana regen,
20 mana and 10 FCR. The planner has one profile named Set 1, no uid; preserve its
legacy source format rather than inventing a modern set_id. No assessment review
has been approved for these five items yet. Horazon Hold/Bane Authority have no
existing named player role; Gheed Wager has Hammerdin and Fire Warlock alternatives
that may inform (but do not automatically cover) Abyss. All broader contract work,
missing Meteor source and host delivery remain pending. No live collection,
restart, staging or commit. Goal remains active.

## Abyss embedded gloves and belts — 2026-09-28

Published generation f60182050fbebf57b8f46cbf451927fa273c81c1b84396c113ccc74ee4e74109
(80 artifacts). Added five roles with prefix abyss-warlock-table-glove-belt-:
horazon, gheed, bane, crafted-gloves, crafted-belt. Native minimums, original and
legal upgraded/recipe bases, nonethereal player status and zero sockets reviewed.
Horazon Hold credits life/Dexterity, not attack damage/CB/AR or companion-gated
IAS/leech as Abyss bonuses. Bane Authority credits standalone FCR/life, not set
Energy. Gheed Wager credits magic piercing for Abyss alongside casting/survival.
Caster gloves use native recipe84 (4–10 mana regeneration,10–20 mana,1–3MAEK),
not FCR. Caster belt uses recipe85 (5–10FCR,4–10 mana regeneration,10–20mana).
Optional resistance/MF/FHR affixes are evaluated when observed, not required at
planner maxima. Minimum utility does not imply premium price or full breakpoint.

90 independent bank cases failed before the rules and pass both staged and
selected. They include all legal bases, minimum and affixed examples, wrong/
unknown class, ethereal/unknown state, impossible sockets, and missing/unknown
recipe stats.28 stat/embedded/pattern-review checks and Ruff pass. All20 saved
report texts AND price estimates match staging. Source audit, bank coverage and
completion regenerated.2529 profiles,2521 stat configurations. Completion has
1657 reviewed occurrences,14 embedded semantic reviews,112847 remaining tasks.
The count rises with newly enumerated obligations; no full suite, whole bank,
pricing completeness or final completion claim.

Four modern embedded reviews added for items147,152,148,92. Legacy span60 belt
is reviewed through exact source_context player_pattern and pinned x2cpo0l5 data.
The named crafted glove span57 also has its own source_context pattern review,
so its labeled occurrence is preserved in addition to the modern embedded link.
Legacy link's initial failure was a full-section quote versus exact pattern label;
fixed the quote to Caster Crafted Belt, preserving section/source validation.
No compiler weakening. The discovery artifact remains source-only documentation;
semantic approval is in rules/embedded_reviews.json and source_context_reviews.json.

Successful one-shots NEVER rerun: tmp/add_abyss_embedded_gloves_belts.py,
tmp/link_abyss_embedded_gloves_belts.py,tmp/link_abyss_legacy_crafted_belt.py,
tmp/link_abyss_crafted_glove_pattern.py. Logs tmp/abyss-embedded-gloves-belts-*.

Next: Abyss Boots table63/64 modern embedded references,65Waterwalk,66Sandstorm
Trek,67WarTraveler,68AldurAdvance,69Silkweave,70legacycraftedboots(item29/x2cpo0l5).
Existing exact Main alternatives roles cover Waterwalk/Trek/Aldur/Silkweave;
inspect boundaries and independently test before table-equivalence reuse.
No existing named Abyss WarTraveler role found in Boots slot. Then amulets onward,
all other source/configuration/pricing/report queues and final gates. A report
polish pass should expand cramped number/unit wording in recently authored role
conditions; do it with the next artifact rebuild and preserve fingerprints.
Missing Meteor source and live worker delivery still pending. No live collection,
restart, staging or commit. The all-item goal remains active and unfinished.

## Abyss Boots table completed at source level — 2026-09-28

Selected generation: 5588590ad1b860796f136d80691ee1566a208ccf4a2fdc27277fd83af22e9d6d
(80 artifacts). Added four roles abyss-warlock-table-boots-{wraithstep,legacy,
traveler,crafted}. Wraithstep's exact example requires observed +1 Chaos Skills
(native188:58, planner tab23), preserving unknown and wrong-tab boundaries.
Horazon Legacy credits magic resistance37 rather than flat magic reduction35;
negative requirements91 use a negative-value activation, not a positive bonus.
War Traveler supports minimum30MF and native/upgraded bases; attack damage is not
Abyss damage. Caster boots use native cube83:4–10 mana regeneration,10–20 mana,
2–5percent max mana, with observed movement/FHR/resistance/MF affixes separately.
No recipe FCR or planner-maximum prerequisite. All new player boots are nonethereal
and zero-socket. Original and legal upgraded/recipe bases tested.

Reused existing Waterwalk, Sandstorm Trek, Aldur and Silkweave Main alternatives
through four validated table-equivalence links (spans65/66/68/69). Wraithstep63
and Horazon64 have exact embedded semantic reviews (items154/153,dm4EcrJ5),
WarTraveler67 a named source-context link, crafted70 a legacy pattern link to
x2cpo0l5/item29. Embedded review compiler gained tested Boots slot support.
All eight table entries now have reviewed source links. Their other occurrences,
pricing/report/variant obligations are not automatically closed.

Added97 independent boot cases. Before implementation:53 fail(new roles),44 pass
(existing rules). After: all97 pass. Re-ran90 preceding glove/belt cases because
public conditions were spaced for readability, with role/use/stat/embedded/context
fingerprints updated. All187 pass staged and selected;32 stat/embedded/table tests
and Ruff pass. Boots slot test failed before support and passes after it. All20
saved report texts and price estimates match staging. Source audit, bank coverage
and completion regenerated:2533 profiles,2525 stat configurations,1663 reviewed
occurrences,16 embedded reviews,11 table-equivalence reviews,112859 remaining tasks.
No full suite/whole bank/final gate claim. Logs tmp/abyss-boots-* and
 tmp/embedded-boots-red.log.

Successful one-shots NEVER rerun: tmp/add_abyss_boots.py,
tmp/link_abyss_embedded_boots.py,tmp/link_abyss_legacy_crafted_boots.py,
tmp/link_abyss_traveler.py,tmp/link_abyss_existing_boots.py.

Next: Abyss amulet spans71–76. Modern gsg0p0l0 embedded definitions inspected:
71item84 crafted Entropy Gorget:2Warlock,15FCR (10affix+5recipe),20allres,25MF,
10mana regen,20mana.73item157 rare:2Warlock,10FCR,20allres,30str,10MF,Teleport
level3/27charges.74item158 magic:3Chaos/10FCR.75item11 Entropy Locket(unique417):
magic mastery5–10,FCR5–10,lightres25–40,maxmana10–15,MDR8–12. Native hit-skill
min4/max19 means4percent level19 Miasma Chains (cached planner reverses chance
and level again; verify using the established propertyfunc11 decoder).76item156
Telling of Beads(set95):1skill,18coldres,35–50poisonres,8–10thorns.72Mara named;
existing Abyss role abyss-warlock-build-guide-1-maras is Standard, so inspect its
conditions before table reuse. These amulets have not yet been semantically
reviewed for this source. Preserve exact profile/set refs when extracting evidence.
All broader contract work, missing Meteor source and runtime delivery remain
pending. No live collection, restart, staging or commit. Goal remains active.

## Abyss amulet table — 2026-09-28

Published bf08dba33cdcc2ed4f7e212e5fb144b3a405238ff475867807151c74ec18fd28
(80 artifacts). Added six roles abyss-warlock-table-amulet-{crafted,rare,magic,
entropy,beads,maras}. Crafted candidate is the cited +2 Warlock /15–20 FCR
combination (10 FCR suffix plus5–10 recipe), with native recipe mana/regen minima;
optional resists/MF are not prerequisites. Rare core is +2 Warlock/10FCR; optional
Teleport uses charge:54 annotation targeting and does not gate core casting use.
Depleted charges are not usable Teleport or a permanent oskill. Magic is +3 Chaos/
10FCR, not another tab. Native prefix713,prefix705,suffix174,suffix533 and recipe88
are pinned. Mara's standalone table role does not inherit Standard125FCR; minimum
resists and attributes are included while existing Standard configuration remains.
Telling of Beads uses native skills/cold/poison resistance, not thorns as spell damage.

Entropy Locket is unique417 (not Bitterfall): native hit-skill function11 confirms
4percent chance to cast level19 Miasma Chain on striking. Cached planner swaps
chance/level (19percent/level4); raw evidence retained and review records correction.
Fixture uses native198:25555 raw4 and verifies actual report wording. Magic mastery,
FCR, lightning resistance, max mana and flat MDR support Abyss; trigger is not
passive spell damage. Five modern embedded reviews and two named/pattern occurrence
links added for spans71–76; crafted span71 keeps both its embedded and labeled
pattern occurrence. Embedded compiler now supports tested Amulet/Amulets role slots.

49 independent cases red before rules,green staged andselected. Available/depleted
Teleport, wrong skill/tab, below-FCR thresholds, unknown class/skills/ethereal,
impossible sockets, minimum named rolls and Mara without full FCR tested.25 final
stat-bundle/embedded/charge checks pass; Ruff passes. The pinned-bundle test's
magic-amulet candidate count was updated26→27 for the new candidate; snapshot
isolation/annotation/status assertions remain unchanged. All20 saved reporttexts
and price estimates match staging. Source audit, bankcoverage and completion
regenerated:2539 profiles,2531 stat configurations,1665 reviewed occurrences,
21 embedded reviews,112882 remaining tasks. No full suite/whole bank/final gate claim.
Logs tmp/abyss-amulets-* and tmp/embedded-amulets-red.log.

Successful one-shots NEVER rerun: tmp/add_abyss_amulets.py,
tmp/link_abyss_embedded_amulets.py,tmp/link_abyss_maras_table.py,
tmp/link_abyss_crafted_amulet_pattern.py. Crafted item84's exact set uid is wNE5FX6D;
other amulet embedded references use dm4EcrJ5. Raw reference contexts validated.

Next: Abyss Rings spans77SoJ,78BK,79embeddedOpalvein(item160,unique416),
80embeddedSling(item161,unique415),81legacyBloodCraftedRing(item30/x2cpo0l5),
82legacyRareRing(item31/x2cpo0l5),83magicFCR/resist ring(item159). Actual planner
examples: Opalvein magic mastery5/FCR10/allres8/LAEK3/MAEK3 and attack trigger
skill398 (cached chance/level likely swapped; verify native before using).
Sling has oskill411/10FCR/magicpierce5/15energy/15slow/20MF; verify exact skill
semantics and do not inherit an unrelated Echoing Ubers dependency. Magic ring is
10FCR/15allres. Blood crafted ring10FCR/11allres/25MF/3leech/20life/5str; native
recipe must be checked. Rare ring10FCR/11allres+30lightres/20str/10MF and level5
Telekinesis32charges, not Teleport. Raw ring definitions inspected only; no reviews
approved yet. Then charms and remaining guide/source/configuration/pricing/report
queues. Missing Meteor and runtime delivery still pending. No live collection,
restart, staging or commit. Goal stays active and unfinished.

2026-09-28: Abyss rings published as 86ffe71bf4997d05fedc88ac483a8c545afc578c018e5e53e771a6f08f7331f1.
Six new roles plus independently checked BK table reuse;60 bankcases staged/selected,
24 related checks,Ruff and20saved-report/price parity pass.24embeddedreviews and
12tableequivalences;112905completion tasks remain. Opalvein random modifier bounds
remain required work (OPALVEIN_RANDOM_MODIFIER_GAP.md). Continue charm table; no
full-bank/full-suite/final/runtime-delivery claim. Full objective stays active.

2026-09-28: Published corrected Abyss charms as
1e7afd6ae0385304088491d4fe250100f8414f808690e29bc2aef307b48c3426.
Seven charm roles;133combined new ring/charm scenarios pass selected,20saved
report/price outputs match corrected staging. Removed accidentally imported
Hardcore life priority; Grand Charm life grounded in the Standard source instead.
Strict typed charm source reviews,Mechanics-ending Hardcore bounds,andCTA prebuff
prose links tested. Ordinary labeled Abyss guide occurrences now reviewed/excluded;
13modern embedded refs still need semantic review or bounded HC exclusion.
2552profiles/2544statconfigs;112927remainingcompletion tasks. Full all-item goal,
fullbank/finalgates,missingMeteor andliveworker delivery remain unfinished.
See handoff.md for evidence,source gaps,andone-shots that must never rerun.


2026-09-28: Selected6e3c2c1cdbbc724267f94cfbf24cc900ed1657df93ff3d3fe93a2ff0b4cee809:
2554profiles/2546statconfigs; two Abyss grimoire roles,22selected bank cases;
2exact embedded Hardcore exclusions,29totalembeddeddispositions. Runtime/report
watch projection now removes explicit Hardcore advice while retaining independent
value rank.36relatedtests plus6selectedscope checks pass;20saved report/price
outputs match staging. New nine-reference source packet
ABYSS_EMBEDDED_RECIPE_REVIEW.json corrects earlier recipe-name confusion;
semantic equivalence still pending.112933completiontasks remain; fullgoalactive.
HostPythonrestart and missingMeteor remain unverified/unresolved. See handoff.


2026-09-28: Nine Abyss embedded recipe uses now reuse five verified existing rules
through a tested exact-context validator; zero pending Abyss embedded refs. Added
seven independent Echoing Hardcore source exclusions. Found missingqJ8YXfFZset
in37Echoingrefs; preserved pending, documented ECHOING_PLANNER_SET_GAP.md.
Completion112917pendingtasks,40embeddeddispositions; selectedgenerationunchanged.
60embeddedchecks,57completionchecks,newpolicy mutation,27HCchecks,Ruffpass.
All-itemgoalactive; Echoing valid-setreferences next; no runtime delivery claim.


2026-09-28: Selected3f798f6f3bd30b335d086b48c083b159c000cfd99569c6df20ec05e6aaa817e3.
Strengthened three Echoing Ubers Sazabi roles with explicit wearer/class/identified/
nonethereal gates.30newbankcases red18→green30, selected30pass;20savedreport/price
outputs match staged. Corrected4pre-existing stale demandcounttests,all8pass.
3257bankcases,3370targets stillmissingcases;112917completiontasks remain.
No all-itemclosure/hostdeliveryclaim. Echoingvalid-source configuration work next.


2026-09-28: Selected815c2d36bd94131ee5ab803e1d33303152657a0cd09ef05f85cedabd3d31628b.
Two Echoing Ubers temporaryFade roles (player/Act5Frenzy),72stagedcases;105selected
Fade/Sazabi/DemonLimb cases pass.20savedreport/priceoutputs match staging.
2556profiles/2548statconfigs,3329bankcases,3370missingtargets;112953completiontasks.
Next: renderedreport shows oldsmite-shared-treachery lacks classgate, leaking
Smiteconditionaladvice intoWarlockcontext; thenEchoing exact source links. Fullgoal
remainsactive,hostdelivery and requiredsourceconflicts unverified/unresolved.


2026-09-28: Selecteddf7fd87c8bb842e3b1065e3bbd57901e2bd709a6d1e941cb1314f50b692c49b4.
Smite sharedTreachery classgate fixed:14newcases,86selectedSmite/EchoingFadecases
pass;20savedreports/prices matchstaging. PublishedknownWarlock report no longer
listsSmiteconditionaluse;Paladinretainsit. TwoexactEchoingFadeembeddedrefsreviewed
throughboundedsourcevalidator,54source/policychecks pass.3343bankcases,
3368targetsmissingcases;112951completiontasks. All-itemgoalactive;nohostdeliveryclaim.


2026-09-28: Validated two Fade visible-label links; added exact player Demon Limb
Enchant native/source review plus its visible label.43 embedded reviews,3linked
labels.80 source/completion checks and16 label checks pass after red regressions;
Ruff/format pass. No runtime generation changes. Mercenary Enchant recipient
remains distinct/pending; all-item goal and delivery remain unfinished. See handoff.

Completion after source links: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1679, "excluded_occurrences": 4821, "coverage_rows": 8210, "remaining_tasks": 112947}; complete=false.


2026-09-28: Published80fd69f956a73db37c243bdc4d3574c11b529787dc49e1e13c22ff21a4adbb15.
Player-cast mercenary Enchant role with9newbankcases;22staged and124selected
relatedcases pass.20savedoutputs match.44embeddedreviews/4label links;3352bank
cases,3368targets missingcases;112950completiontasks. Sling review packet prepared
for next missing Echoing pairing. All-itemgoalactive; delivery/finalgates incomplete.


2026-09-28: Publisheddaba38e154608719afd41b4b71cf009d688b3526edf3b68883163303e3260afa.
EchoingUbers Sling pairing added,14bankcases;125selectedrelatedcases pass.
Companionreporting Setup/Needs/Check fixes hiddenrequirements;129appraisaltests pass.
20savedoutputs matchstaging. CompleteSlingcapture exposes missing358:0->1877
marketprojection; next implementationgap, not missinglistings.3366bankcases,
112955completiontasks. ExactSling sourcelinks,hostrestart andall-itemgates pending.


2026-09-28: Published90c90ab2726de046051852457713d55942fee6d78d32d9f0979ca1fb82163f46.
Magicpierce358:0->1877 andexactTownPortaloskill97:411->1878 nowpricedthroughnative
contracts.27regressions/25selectedbankcasespass;20savedoutputs matchstaging.
Slingminimumroll1seller(thin),maximum0matches; no inventedestimate. Pricingreview
packet saved, exactSling sourcelinks stillpending. Bankfingerprint refreshed;
all-itemcompletionfalse,hostPythonrestart unverified.


2026-09-28: ExactEchoingUbers Slingtooltip/label linked throughnative/contextvalidator.
92source/completion/policychecks passafterRED;45embeddedreviews/5labeldispositions.
112953tasksremain. Selected90c90ab unchanged; nextHellwarden/Gheedremoval/Malice
sourcecontexts; all-itemgoal andhostdeliveryremainunfinished.


2026-09-28: Published dd011f5c323e8f6eabc19062cd91af7552324c1997b936d3b24e9bfb283aa4ef.
Hellwarden perfect-roll preference no longer counts socket bonus as helmet roll.
32 predicate/role and35selected bank checks pass;20savedoutputs match staging.
3376bankcases/3367missingtargets;112953completiontasks. ExactHellwarden source
link remains pending after fixing runtime bug. Full goal and delivery unfinished.


2026-09-28: ExactHellwarden/jeweltooltip andlabel reviewed after native-rollfix.
109source/completionchecks pass;46embeddedreviews/6label links;112951tasksremain.
Runtime dd011f5c unchanged. NextpinnedGheedremoval andMalice refs stillpending.
All-itemgoal andhostdelivery unfinished.


## Active checkpoint — Gheed negative Ubers reference, 2026-09-28

Published f703eb7fafb4231c29777742c1a4b5c8dd057d487011e90bb2caa2b190038f39,
80 artifacts;2558profiles/2550statconfigs unchanged. Completed exact span11 negative
Ubers tooltip and visible-label review. Native359/cm3 Gheed, pinned guide sentence
explicitly says replace it; tooltip happens to point to Magic Find. Exclusion applies
only to this reference, not Gheed identity, Standard/Magic Find uses or trade tier.

New maintenance/embedded_negative.py validates exact guide/span/section/identity,
raw removal sentence, native source, absence of positive role endorsement. Visible
label closure requires corrected recommended=false in actual occurrence. Importer
negative_mentions.py pins exact source hash + ordinal + label/side/slot, rejects
changed evidence instead of silently restoring recommendation. build_dataset replay
proved exactly ONE existing record changed: cc6e26196a4e047f39245526, recommended
true->false. Other 62k+ occurrences preserved. completion policy fingerprints both
new helpers; final attestations invalidate on their changes.

Source tests8red->green; label4red/9pass->13green. Importer3red->14combinedgreen.
109source/completion/watch regressions,23baseline/negative checks,17policydependency
checks pass. Final selected66Guardian/Gheed bank cases pass;20saved staged/selected
reports/prices/extractions match. Ruff/format clean. Source audit114planners with
no guide/source issues; Meteor remains unsupported. Bank3376cases/3913targets,
3367targets missing scenarios.47embedded reviews/7visible dispositions.

IMPORTANT rebuild incident resolved: valuable regenerated watch artifact hash and
invalidated six baseline pins. cfcaa3b710e1296b901a2d7a5e5eb0ed77cd5e6df17c0bf1e304292a4ac063c3
was briefly selected with6missing baselines; now SUPERSEDED. Compared exact cited
watch rows against retained dd011 generation: all6identical. Revalidated only their
pins, rebuilt, verified namedgate548eligible/35sets/2958rendered, all gates0, then
published f703 above. Selected artifact hash+pointer checks prove all6valid. Final
completion restores prior dimensions; two source tasks closed,112949pending.

Successful one-shots NEVER rerun: tmp/link_echoing_gheed_negative.py,
tmp/link_echoing_gheed_label.py (first attempt failed KeyError before writes; corrected
run succeeded), tmp/review_gheed_watch_fingerprints.py. Rebuild script remains safe
rerunnable. Logs tmp/gheed-*. All handles completed. No live collection/hostprobe,
restart,commit orstaging. Hostdelivery/fullbank/fullregression/finalgates unfinished.

Next: Malice span14/section25. ECHOING_UBERS_REMAINING_SOURCES.json records Gheed
closure and pending Malice. Existing role echoing-strike-warlock-guide-malice-ubers-
source-recipe is Warlock/Act5Frenzy/eth7wd/3filled and ignores mercPMH, but source
explicitly describes fullSazabi while role only mentions companions in prose, no
depends_on. Review whether exact Ubers role needs companion predicates before
source closure. Existing must has broad swordlist AND exact7wd, not broad eligibility.
Parent planner recipe stats are separate from childrunes; don't sum as captured total.
Keep Enchant/Fade prebuff availability separate from activebuff inference.
All-item goal ACTIVE, unfinished; independent work remains despite qJ8YXfFZ/Meteor gaps.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1682, "excluded_occurrences": 4822, "coverage_rows": 8212, "remaining_tasks": 112949}; complete=false.


## Active checkpoint — Malice Ubers companions and source closure, 2026-09-28

Published8370632a2f856d4e4a464d9952022fbe7b2e2b11c6163c7b929539c3aac3d58d,
80artifacts;2558profiles/2550statconfigs unchanged. Exact Malice Ubers profile had
fullSazabi only in prose. Added3depends_on context_contains mercenary_items for
CobaltRedeemer,GhostLiberator,MentalSheath. Missing/unknown/player-only companions
remain partial and do not qualify this setup's statannotations. Retained
Warlock/Act5Frenzy/eth7wd/identified/3filled. PMH and activeEnchantment/Fade not
credited; companions only prove names, not rolls or activeeffects.

New independent echoing_malice bank15cases includes normal/superior/low_quality,
complete/missing/unknown/player-onlycompanions,wrongclass/merc/base,ethstatus and
identification.6red/6pass before rule;15staged and15selected pass after correction.
Fixture explicitlypartial totals includesElAR50/Ethtargetdef25 and recipeprops;
no invented physicalweapon damage or light (-1recipe+1El cancels). Source recipe
unit context updated with actual companions;9role regressions pass.

New embedded_echoing_malice validates span14/section25, guidewearer/contribution,
sourceprimary+nativecorroboration, exacteth7wd3runes/order,100OWparent, nativeOW
recipe100, exactpriorities excludingPMH, class/merc/base/fill and all3companions.
12sourceRED then50source/pairing/policy GREEN (includes18policydependencies).
8Malice visible-label/closure tests pass. Added exacttooltip+label;48embeddedreviews,
8visible dispositions.20selected savedreports/prices/extractions match staged.
Universalnamedgate548eligible/35sets/2958rendered,allgates0. Ruff/formatclean.
Sourceaudit114planners/0newguide/sourceissues; Meteor unresolved unchanged.
Bank3391cases/3913targets/3366targets missing cases. Fullbank/fullsuite/finalgates
and hostdelivery remainunfinished; no livecollection/probe/restart/commit/staging.

Successful one-shots NEVER rerun: tmp/fix_malice_sazabi_dependencies.py,
tmp/link_echoing_malice_source.py. First rebuild failed staleguidefp becauseMalice
is a source_recipe TEMPLATE, not a literalrule. Corrected review fingerprints to
compile_profiles(load_rule_bundle(...)) result, sourcefp never rawtemplaterow.
The correction was applied once separately; appendermutator must not rerun.
Subsequent fullrebuild,index,replay,pub all succeeded. Old failure logs superseded.
Allprocess handles terminal. Logs tmp/malice-*. ECHOING_UBERS_REMAINING_SOURCES.json
now records bothGheed andMalice closures.

NEXT: ECHOING_MERC_RECIPE_REVIEW.json pins sevenpendingexactrefs andsections.
Starter section13/span1native9paInsight,span2xtpTreachery,span3crnBulwark,all eth,
Act2BlessedAim. Later sections17/21 spans6/8 Insight7wc eth,Act2Prayer+Cure synergy;
span127section42 generalPrayerInsight;span130section43 progressiontable.
Do not replace BlessedAim with Prayer/Might or credit triplehealing without
Cure/Prayer setup. Nativeparent tables distinctfrom rune socketcontributions.
Blankvisibletooltip labels can still be reviewed as embeddedrefs with nativeproof;
no invented visible-label alias. MoreEchoing refs remain; missingqJ8YXfFZ andMeteor
are unresolved source gaps, not grounds to stop independent work. Goal ACTIVE.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1683, "excluded_occurrences": 4822, "coverage_rows": 8212, "remaining_tasks": 112947}; complete=false.


## Active checkpoint — Echoing Insight variants and report ordering, 2026-09-28

Published36439601d229641bacebb023e4856674c54a4bf44b590c0e259d545a883006fb,
80artifacts,2561profiles/2553statconfigs. Found no prior reviewed Echoing Insight
roles. Added echoing-{0,1,2}-insight-merc: Starter ethPartizan/Act2BlessedAim;
Standard+MagicFind ethGiantThresher/Act2Prayer with Cure in mercenary_items.
ExactclassWarlock/base/eth/identified4filled; normal/superior/low_quality supported.
Priorities Meditation151:120,ED17/18,CriticalStrike97:9,bonusAR119. Minimumrolls
useful; no activeaura,tripledhealingrate,ownlifeleech or numericalprice inferred.
Sourcewp variants0/1/2 pinned + nativeInsight recipe. Cure requires mercside;
unknown/missing companions keep exactlaterconfiguration partial.

Independent bank echoing_insight:9positiveRED/27negativepass initially. Rulefixed
assessment, but6positivecases still failed visible Cure requirement: reportbounded
3groups sorted Starter before Standard, hiding valid setup behind knownwrong
mercenarydependencies. Added dependency_rank inside status sort: satisfied then
unknown thenfailed typeddependencies before stage/id. No statuspromotion, no
match changes, full details preserved, same3groupbudget. UnitRED->130reporttests
GREEN.36staged/36selectedbankpass, then extended everynegative/unknown across all
3qualities:90selectedpass(111s).3481totalbankcases/3922targets/3366missing targets.
2statbundlechecks pass(2553);40source/Malice/policy regressions +8Insight visible
label tests pass. Ruff/format clean.20savedstaged/selected reports/prices/extractions
match. Universalnamedgate548eligible/35sets/2958rendered allgates0. Sourceaudit114
planners/0guide/sourceissues;Meteor remainsunsupported. Fullbank/fullsuite/final
attestations and hostPythonrestart remainunfinished.

New embedded_echoing_insight validates spans1/6/8 sections13/17/21, distinctvariants
and mercauras, exactnativebase/eth4runes/order, Meditation12-17 native, source
primary/corroboration, exactstatpriorities (rejectsintrinsicleech), and Cure only
forlaterPrayerroles. Threeexactrefs +two visiblelabels closed. Blankstartertooltip
has no invented visible alias.51embeddedreviews/10visible dispositions.

Successful one-shots NEVER rerun: tmp/add_echoing_insight_roles.py,
tmp/link_echoing_insight_sources.py. All handles terminal. Logs tmp/echoing-insight-*.
Currentcompletion1685reviewed/4822excluded; scopeidentities/occurrences unchanged.
Coverage rows grew9 for explicit3rolesx3qualities; requiredpending count112996,
not a claimof broadcompletion. All-item goal ACTIVE, incomplete. No livecollection,
probe,restart,commit orstaging.

NEXT ECHOING_MERC_RECIPE_REVIEW.json: spans1/6/8 closed; starterblankspan2Treachery
MagePlate andspan3BulwarkCrown stillpending. Existingroles
 echoing-strike-warlock-guide-0-merc-treachery-native
 echoing-strike-warlock-guide-0-merc-bulwark-native
already specify Warlock/Act2BlessedAim/exactethbases/3filled but qualities only
normal/superior. Verify low_quality completedrecipes and add independent native
bankscenarios before sourceclosure. No existingbankfile matches theirIDs.
GeneralInsight span127section42 andprogression span130section43 remain separate
contexts; do not blindlyalias Standard/Cure if source advice is moregeneral.
OtherEchoing refs (Void, gearalternatives, etc), missingqJ8YXfFZ andMeteor remain.
ReportPython change requires hostrestart; not performed/verified this turn.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1685, "excluded_occurrences": 4822, "coverage_rows": 8221, "remaining_tasks": 112996}; complete=false.


## Active checkpoint — Echoing starter armor quality and blank tooltips, 2026-09-28

Published8df2dd6ecc9c551b0bac06fa4675570b3e03780038fb32516d853456d8a81dff,
80artifacts,2561profiles/2553configs unchanged. Two existing starter rules only
allowed normal/superior; completed low_quality Treachery andBulwark now supported.
Exact ethMagePlate/ethCrown,Warlock,Act2BlessedAim,identified3filled retained.
Source guide/stat review fingerprints updated for those literal profiles only.
No itemstats/price multipliers or activebuff claims added.

New independent echoing_starter_armor bank42cases:2words x3qualities x7scenarios
(positive,wrong/unknownmerc,wrongclass,unknown/noneth,wrongbase). RED2lowquality
positives/40pass ->42stagedgreen and42selectedgreen. Nativepartialstat arrays;
Treachery IAS/Fade/FHR/coldres andBulwarkNL4lifeleech/10physicalreduction/maxlife/FHR
assert their correct desirable/supporting config annotations. Rune names resolve
through metadata; fullphysicaldefense and unknownstats not fabricated.

New embedded_echoing_starter validates blankspans2/3 section13, exactwearer and
nativebase/eth3runeorder,primarywp variant0/nativecorroboration,all3qualities and
priorities. Native Fade5%lvl15whenstruck and NL Bulwark4-6leech/10-15DR checked.
7semanticRED then33semantic/policy GREEN (includes20policydependency cases).
Recorded2embeddedrefs;53embeddedreviews/10visiblealiases unchanged because both
labelsblank. ECHOING_MERC_RECIPE_REVIEW.json marks those2closed. No inventedaliases.

20savedstaged/selected reports/prices/extractions match. Universalnamedgate548
eligible/35sets/2958rendered,allgates0. Ruff/formatclean. Sourceaudit114planners
no newguide/sourceissues; Meteor remainsunsupported. Bank3523cases/3924targets,
3362targets stillmissingcases. Coverage8223rows includes2newqualitytargets;
completion113006pending, not broadclosure. All-item goalACTIVE, unfinished.
Fullbank/fullsuite/finalgates andhostdelivery/Pythonrestart stillpending.
No livecollection/probe/restart/commit/staging. Alltoolhandles terminal.

Successful one-shots NEVER rerun: tmp/fix_echoing_starter_qualities.py,
tmp/link_echoing_starter_sources.py. Logs tmp/echoing-starter-*.

NEXT GeneralInsight span127section42 ('Insight, Prayer') explicitly says Prayer
for life regen and InsightGiantThresher for mana; does NOT require Cure. Existing
EchoingStandard/MF roles intentionally model fullCurehealing setup. Need separate
reviewed generalmana use (do not silentlyalias strongerCuredependency), independent
positive/near-miss/unknownbank, and exactsource review. Generalprogression span130
section43 remainsseparate. Source packet alreadypins both; laterCure refs5/7 and
manyequipment references also remainpending. MissingqJ8YXfFZ/Meteor are separate
sourcegaps and do not block this independent work.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1685, "excluded_occurrences": 4822, "coverage_rows": 8223, "remaining_tasks": 113006}; complete=false.


## Active checkpoint — General Prayer/Insight use and progression ownership, 2026-09-28

Publishedf9adba7872a9cc7d84b24061822dab07ffb132dfdca980a3294615eb8759c46d,
80artifacts,2562profiles/2554statconfigs. New echoing-overview-insight-merc reviews
section42 generalPrayer/Insight mana advice. Native legal4socket Act2polearms
via legal_base_condition (not spears orBardiche); Warlock/Prayer/identified/4filled.
No Cure or ethereal gate: nativeMeditation effect survives noneth/unknowneth and
legalalternativeBill. Guide's ethGiantThresher is an example, not a universalbest
base. Priority only151:120Meditation; Prayer is mercenary ability, not itemstat;
no intrinsic lifeleech,activeaura,triplehealingrate or price inferred. Narrower
Standard/MF Cure combo roles retained separately. Primarypinnedcachedsection42,
nativeInsight corroboration; conditions keep activation/equipment caveats separate.

Independent echoing_insight_overview bank36cases (3qualitiesx12): without/with/
unknownCure,noneth/unknowneth,Billalternative,wrong/unknownmerc,wrongclass,
illegalBardiche/spear,unidentified.18positiveRED/18negativepass ->36staged and
36selectedgreen.3559bankcases/3927targets/3362missingtargets. Added1profile/config;
statcount2554 updated,23stat/policychecks pass (includes21policydependencycases).

Extended embedded_echoing_insight spans127section42 and130section43. Generalmust
is exact canonicalclass/Prayer/identifiedword/fill/nativelegalbase set: reject
extraCure/eth/fixedbasegates and falsely annotatingPrayer. Source overviewRED1 then
14green. Progression rawtable parser says side=player despite immediatelypreceding
Insight,Prayer section and explicit Mercenary tableprose; boundedsemantic review
corrects to mercenary role, retains rawprovenance. Parentheading/Prayertext/table
heading/weaponexample all required. Tests source+3Insightlabelbranches:39pass and
one ineffective mutation initially (rawHTML splits 'Prayer Aura'); fixed mutation
to actually replacePrayer, isolatedtest passes. Thus all40 source/labelchecks pass;
no productionchange needed for testmutation. Added2embeddedrefs+2visiblealiases:
55embeddedreviews/12visible dispositions. ECHOING_MERC_RECIPE_REVIEW.json allits
7specificrows reviewed; does not mean wholeEchoingguide complete.

20savedpublishedreports/prices/extractions match staged. Universalnamedgate548
eligible/35sets/2958rendered allgates0. Ruff/formatclean. Sourceaudit114planners,
0guide/sourceissues, Meteor unsupported unchanged. Fullbank/fullregression/final
gates/hostdelivery stillunfinished. Source-policy fingerprint now also covers
merc_survival_templates.py used to validate legalpolearmconditions.

Successful one-shots NEVER rerun: tmp/add_insight_overview.py,
tmp/link_insight_overview.py. First appendattempt hadSyntaxError before anywrites;
corrected run succeeded once. An inadvertentlystarted rebuild againstoldprofiles
then failedreview_dossiers; it was verifiedterminal, then fullrebuild rerun after
correction and succeeded. No overlapping rebuild left. Alltoolhandles terminal.
Logs tmp/insight-overview-*. No livecollection/hostprobe/restart/commit/staging.
Goal ACTIVE, unfinished; sourceconflictsqJ8YXfFZ/Meteor stilloutstanding.

NEXT ECHOING_CURE_REVIEW.json pins refs5/7 blankCure and155CureGrandCrown progression.
Existing echoing-strike-warlock-guide-{1,2}-merc-cure specify Warlock/Prayer/exact
ethGrandCrown3filled, but qualitiesnormal/superior only, no depends_on. Priorities
151:109Cleansing,45poisonres,110poisonlength,76maxlife,99FHR. Review standalone
Cleansing usefulness vs fullPrayer+Insight healing dependency; do not blockvalid
standaloneaura or infer fullhealing from names alone. Addlowquality/nativebank
boundaries. Progressionref155 again rawparser sideplayer needs boundedmerccontext.
Otherguidegear references remainpending; ownership correction here is ONLY scoped
Insight references, not a global rawparser fix.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1687, "excluded_occurrences": 4822, "coverage_rows": 8226, "remaining_tasks": 113020}; complete=false.


## 2026-09-28 — Cure family quality and exact Echoing component review

Selected runtime dcc3427ed436e927c450336697cf0b35dc312e7565a02d7fcd7d9dc8e1adc7bd
(80 artifacts; 2562 profiles / 2554 stat configurations). Previous f9ad generation retained.
All31 reviewed Cure roles now accept completed low_quality alongside normal/superior;
CURE_QUALITY_REVIEW.json proves each compiled role differs only in qualities. Bearer,
base, companions, source and native stat priorities unchanged. Family RED9 -> GREEN25;
Echoing native full-pipeline RED6 -> staged54 and selected54 pass. New bank cases cover
Standard/MF, all3qualities, without/with/unknownInsight and wrong/unknown bearer, eth
and base. Cleansing component usefulness remains independent of full Prayer/Insight
healing; neither active aura nor fixed healing rate inferred.

Added embedded_echoing_cure validation and source refs5/7: blank labels resolved by
pinned native recipe/planner, no invented visible aliases. Native parent poisonres
10–30 is distinct from captured total including Tal. Source+policy tests31 pass;
57 embedded reviews now. Two Zeal source-context pins needed quality-only migration:
reconstructed old role exactly equals prior fingerprint before updating; 18 context
tests pass. Completion audit initially failed on those pins, then succeeded unfinished.

Bank3613 cases /3958 requiredtargets /3387 missingcases. Namedbaseline548 identities,
35 fullsets,2958 renderedcases: all gates0. Twenty saved selected reports, price_estimate
and extraction fields match staged. Ruff clean,8 files formatclean. Source audit114
planners; unsupported Meteor and missing qJ8YXfFZ source conflicts remain outstanding.
Fullbank/fullrepo/finalgates and hostrestart/delivery are still unverified.

Successful one-shots NEVER rerun tmp/fix_cure_quality_family.py,
tmp/link_echoing_cure_sources.py or the inline two-Zeal-pin migration. All process
handles terminal. Logs tmp/cure-*. No live collection/probe/restart/commit/staging.

NEXT: ECHOING_CURE_REVIEW.json span155 Cure Grand Crown in section43 progression.
Exact source context: immediately follows section42 Insight, Prayer; table explicitly
says Mercenary. Raw parser sideplayer must remain provenance but must not determine
runtime wearer. Add separately sourced progression role/native bank and semantic
source validation; do not relabel Standard/MF roles. Review exact Grand Crown example
versus general legal helm contribution, then close embedded and visible source refs.
Other source/configuration/pricing/itembank queues remain required; goal ACTIVE.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1687, "excluded_occurrences": 4822, "coverage_rows": 8257, "remaining_tasks": 113204}; complete=false. Expanded quality targets and changed fingerprints expose additional required work; pending totals are not a completion claim.


## 2026-09-28 — Cure mercenary progression

Selected generation b4425bf0ed8ab6063441a1e1939cf58a179897ffa9d5567a3c6494337b7960d7
(80artifacts;2563profiles/2555statconfigs). Added echoing-progression-cure-merc,
a separately sourced section43 Gear Progression role under section42 Insight/Prayer.
Warlock, Act2Prayer, identified Cure,3filled, native legal helm/circlet bases, all3
completed nonmagical qualities. Standalone Cleansing priority151:109; no Insight,
ethereal or fixed GrandCrown gate. No whole healing multiplier/active aura claim.
GrandCrown remains pinned guide example; different legal bases can supply same aura.

Native independent bank36:18RED+18negativepass ->36staged and36selectedGREEN;
without/with/unknownInsight,noneth/unknowneth,BoneVisagealternative,wrong/unknownmerc,
wrongclass,illegalCap/Monarch,unidentified across3qualities. Bank3649cases,
3961targets,3387missingtargets. Statbundle count2555;24stat/policychecks pass.
Source validator extended exactspan155 with Prayer parent, Mercenary table and
CureGrandCrown example;14semanticchecks pass including mutatedparent/example and
forbiddeneth/fixedbasegates. Source label support echoing_cure added;8labelchecks
pass (positive was RED unsupportedkind). Embedded ref155+visiblealias closed;
58embeddedreviews/13visiblealiases. Raw parser sideplayer retained as provenance,
corrected only for boundedvalidated mercenary use. ECHOING_CURE_REVIEW.json closes
its3specificrefs, not wholeguide. No runtime use is inferred from raw table owner.

20selectedreport texts/price_estimate/extractions match staged. Namedtiergate548
eligible,35fullsets,2958renders,allgates0. Ruff/7formatfilesclean. Completion first
failed stale planner reachability after addedprofile; regenerated planner_source_audit
and completion succeeded unfinished. Sourceaudit114planners,0guide/sourceissues,
Meteorunsupported and qJ8YXfFZ missing source conflicts still unresolved. Fullbank,
fullregression,finalgates,hostrestart/delivery remain unfinished.

Successful one-shots NEVER rerun tmp/add_cure_progression.py and
 tmp/link_cure_progression.py. Link script first failed beforewrite on unsupported
occurrence kind; after RED/GREENfix it succeeded once. All processhandles terminal.
Logs tmp/cure-progression-*. No livecollection/probe/restart/commit/staging.

NEXT ECHOING_ENIGMA_REVIEW.json pins span18/section30Late-Game, planneritem321.
Guide says replaceBladeWarp with Teleport upon acquiring EnigmaMagePlate. Existing
Standard/MF/Ubers Enigma roles do not automatically review this distinct proseuse.
Review genericTeleportutility vs exactbase/durability, independentnativebank, role
and exact source link. Scope all remaining configurations, pricing and itembank
obligations remains unchanged; goal ACTIVE.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1688, "excluded_occurrences": 4822, "coverage_rows": 8260, "remaining_tasks": 113220}; complete=false.


## 2026-09-28 — Enigma late-game mobility and 35-role quality correction

Selected generation75e01d7bd96ed3f80b4e18c9ce4f6b3a7c4757c20e8a77da97924ffd1dc38db9
(80artifacts;2564profiles/2556statconfigs). Earlier cde9c24db59038d66b5ae9ff3fb0788828d921dfa38d50e5c42cbbdf3a59f3bf
published late-game role alone and remains retained, as do prior generations.

Added echoing-late-game-enigma-player: section30 explicitly replaces BladeWarp with
Teleport. PlayerWarlock,identifiedEnigma,3filled,nativelegaltors,all3completedqualities,
nonethereal for durableplayeruse; no fixedMagePlategate or CTAcompanion. Only native
97:54Teleport contribution; no FCRbreakpoint/selfequip/fullbuild/priceclaim. Ethereal
still grantsTeleport but cannot normallyrepair, statedinconditions. Native24bankcases
6RED18pass ->24staged/selectedgreen: all3qualitiesMagePlate/DuskShroud,eth/unknowneth,
wrong/unknownclass,illegalhelm,unidentified. ECHOING_ENIGMA_REVIEW.json reviewedexact
span18/section30/player. Newembedded_echoing_enigma.py validates exact prose/native
JahIthBer/oskill54+1 and legal-roleboundaries.10semanticchecks,23policydependencychecks,
2statbundlechecks,8visiblelabelchecks pass; REDunsupportedsemantic/label first.
Source58->59embeddedreviews;13->14visiblealiases. Count2556 updated. No whole-guide
completion inferred. Late24 remains valid but finalselectedfamily420 does not rerun
that24 after familyqualitychange; it passed immediatepreviouspublishedgeneration.

Then reviewed35existingEnigma variantroles (of41total) omitting completedlow_quality.
Independent test_enigma_priorities MEMBERS explicitly lists35build/base variants.
35RED+1pass ->36GREEN. NativeEchoing representativebank3RED15pass. Migration proves
allcompiledfields exceptqualities identical and everyotherprofile unchanged; guide/
statpins updated against exactoldfp. No embedded/sourcecontextpins referred to those
35roles. ENIGMA_QUALITY_REVIEW.json holds nativepin,before/afterfps and verification.
Nativebank enigma_quality.py uses independently authoredtestMEMBERS (notproduction
profiles), all35 x3qualities x4scenarios =420. Positives and ethereal/unknowneth/wrong
class boundaries; Sorceress supportingTeleport retained by familyunitassertion.
First210stagedgreen, added210normal/superiornegative/unknown stagedgreen; full420
selectedgreen226sec. Initial bankcollection error missingCase.expected corrected
before REDbehavior run, not counted as behavioralRED. Bank4093cases/3999targets/
3317missingtargets; no missingcasecategories for the35Enigma variants. Casecoverage
is not fullrepo verification; native bank is partialcapture, not fullpriceevidence.

20finalselectedreporttexts/price_estimate/extractions equal staged. Namedbaseline548
eligible/35fullsets/2958renders allgates0. Ruff10filesclean/formatted. Sourceaudit114
planners,0guide/sourceissues; unsupportedMeteor and missingqJ8YXfFZ unchanged. Final
completionaudit succeeds unfinished. Fullbank/fullrepo/finalgates and hostdelivery
remainpending. Allprocesshandles terminal. No livecollection/probe/restart/commit/
staging. Successfulone-shots NEVERrerun tmp/add_enigma_late.py,
tmp/link_enigma_late.py,tmp/fix_enigma_quality_family.py. Logs tmp/enigma-late-* and
 tmp/enigma-quality-* (allselected/staged/test/replay/completion evidence).

NEXT: COMPLETED_WORD_QUALITY_AUDIT.json records326remaining completedword roles
across19words omittinglow_quality;201literal,125merc_survivaltemplates. Audit only,
no authorization to blindlybroadenpreparation/creation rules. LargestDuress39,
Smoke31,Fortitude30,Temper30,Lionheart27,ChainsHonor24,Ground21,Bulwark19,Treachery17,
CTA16,Rhyme15,Spirit14,Hustleweapon12,HOTO11,Hustlearmor8,Wealth6,Infinity3,Flickering2,
Lore1.7source_context reviewrows referenceaffectedroles;0embeddedreviews. Group by
sharednativebehavior,RED/GREENexistingindependentfamilytests + nativebank, preserve
allothercompiledfields, updatepinsONLYafterexactdiffaudit, thenpublish/replay.
Other source/config/stat/pricing queues still required; this is not a replacement
for original all-item goal. Goal ACTIVE, unfinished.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1689, "excluded_occurrences": 4822, "coverage_rows": 8298, "remaining_tasks": 113446}; complete=false. Expanded quality scope creates additional obligations; count is not a completion claim.


## 2026-09-28 — Seven completed-word quality families

Selected generation: 910c5eb35a4c60feb3544a228dfd26a447b619dd3e0c2758d35b62c6738ed504
(80 artifacts; 2564 profiles /2556 stat configurations). Previous75e01d retained.

Corrected completed low_quality eligibility for162 roles:125 shared merc_survival
profiles and37 literals. Words: Duress39,Smoke31,Temper30,Lionheart27,Ground21,
Hustle(armor)8,Wealth6. The compiled before/after audit proves only qualities changed;
all other fields and all other profiles are unchanged. No unsocketed preparation,
recipe creation availability, wearer/base/ethereal/stat/companion policy changed.
MERC_WORD_QUALITY_REVIEW.json preserves native pin,162 before/after fingerprints,
source pin migrations and validation. Four source_context reviews updated after
exact old fingerprint checks: zeal-starter-smoke,zeal-early-merc-equipment spans
212/233/211. No embedded review referred to these roles.

RED:12 family test failures,25 passes;105 native cases had14 failures/91passes.
GREEN:55 family/source-context tests, plus separate Ground runtime test checking
all15early merc roles retain defenses without Vitality.105native cases pass both
staged and selected: seven independently authored examples x3qualities x5scenarios
(nonethereal,ethereal,wrongclass,illegalbase,unknownidentified). These are recipe
representatives, not a claim of native bank coverage for all162build roles. Native
rune sequences verified locally; Lionheart raw life12800 decodes50. CompletedHustle
armor is distinct from weapon; player versus merc durability/benefits remain intact.

Bank4198cases/4161targets/3458missingtargets. Expanding162 quality targets introduces
new required native build cases; seven examples close21quality targets. Twenty saved
selected text/price_estimate/extraction outputs match staged. Namedbaseline548eligible,
35fullsets,2958rendered allgates0. Ruff/9formatfilesclean. Sourceaudit114planners,
0guide/sourceissues; unsupportedMeteor and missingqJ8YXfFZ source conflicts unchanged.
Completion audit succeeded unfinished. Fullbank/fullrepo/final gates and hostdelivery
remain pending. All process handles terminal. No livecollection/probe/restart/commit/
staging. Successful one-shot tmp/fix_merc_word_quality.py MUST NOT be rerun.
Logs tmp/merc-word-quality-* include RED/GREEN, staged/selected, publication,replay,
coverage,audit andcompletion. Goal ACTIVE, not complete.

NEXT: COMPLETED_WORD_QUALITY_AUDIT.json retains original326 reviewed candidates,
marks162 quality_corrected_verified, leaves164pending across12words. All164 are
literal role definitions. Fortitude30,ChainsHonor24,Bulwark19,Treachery17,CTA16,
Rhyme15,Spirit14,Hustleweapon12,HOTO11,Infinity3,Flickering2,Lore1. Three source-context
pins remain relevant: two zeal Fortitude repeats and abyss-named-merc-table-span108
ChainsHonor. No embedded reviews. next_test_leads lists independent existing tests;
read their assertions, extend completed-quality boundaries and add nativebank cases.
Preserve exact compiled behavior except justified quality eligibility, verify all
pins before migration, then publish/replay. All original source/pricing/item-bank
closure requirements remain; finishing this quality audit is not the all-item goal.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1689, "excluded_occurrences": 4822, "coverage_rows": 8460, "remaining_tasks": 114418}; complete=false.


## 2026-09-28 — Remaining 164 completed-word quality corrections

Selected generation: 61a3fb086a7d0dd5c584a23bc94dc501700f4651eb32aab60790a0ba18c7b39b
(80 artifacts; 2564 profiles /2556 stat configurations). Previous910c5eb retained.

All164 remaining literal roles now accept completed low_quality: Fortitude30,
ChainsHonor24,Bulwark19,Treachery17,CTA16,Rhyme15,Spirit14,Hustleweapon12,HOTO11,
Infinity3,Flickering2,Lore1. Whole compiled-diff audit proves only qualities changed;
all other profiles and fields unchanged. No base-preparation or creation rule changed.
COMPLETED_WORD_QUALITY_AUDIT.json marks its original326 quality gaps corrected, with
zero pending in that bounded audit. This does NOT close all-item work or source,
pricing, variant, class, or native bank obligations.

Recovery: tmp/fix_remaining_word_quality.py changed164 raw roles, proved exactdiff,
then stopped BEFORE any review writes because six pre-existing Fissure roles have
no explicit guide_use_reviews rows. Do NOT rerun. Recovery script
 tmp/finalize_remaining_word_quality.py revalidated exact old/new diff, migrated158
existing guide pins and164stat pins, and recorded the exact6missing without inventing
endorsements. Source-context3pins updated: Zeal Fortitude repeats12/25, Abyss merc
ChainsHonor span108. No embedded pins affected. REMAINING_WORD_QUALITY_REVIEW.json
contains before/after hashes, sourcepins, recovery explanation and validation.
Both scripts are one-shots; recovery SUCCEEDED, never rerun either.

RED: first Fortitude unit test failed low_quality (maxfail1); specialist tests6failed/
2passed for Infinity3 and playerFlickering3bases. Native12recipes x3qualities x3cases
=108:12lowqualitypositives failed,96passed. GREEN native108staged +108selected.
Cases preserve real rune payloads, independent native benefits, wearer/base/ethereal,
and identified/unidentified/unknown states. Representatives are NOT native coverage
of all164build roles. Bank4306cases/4325targets/3586missingtargets.

Broader green run:124passed and1 stale Bulwark test failure. Oldselected910c5eb
already contained20Bulwarkbuilds, but test expected19. Corrected expectation to exact
MEMBERS build set plus Fissure/FOH/Zeal; isolated test passes. Thus all125 affected
checks pass across full+isolated runs; no runtime change for stale expectation.
Logs tmp/remaining-word-quality-green.log and -bulwark-green.log retain that history.
Ruff/11formatfiles clean. Namedbaseline548eligible/35sets/2958renders allgates0.
Twenty selected text/price_estimate/extraction replays match staged. Sourceaudit114
planners,0guide/sourceissues; unsupportedMeteor and missingqJ8YXfFZ remain. Completion
succeeds unfinished. Fullbank/fullrepo/finalgates/hostdelivery still pending.
All process handles terminal. No livecollection/probe/restart/commit/staging.

NEXT PRIORITY: INFINITY_CLASS_REVIEW.json records a reproduced runtime bug. Native
remaining-word-quality/Infinity/normal/native gives nova-standard-infinity-player-stats
for player_class Sorceress, Paladin AND None. This predates quality edits (must
unchanged); source-specific Nova demand must not establish applicability for the
wrong or unknown class. Audit all3 old Infinity roles (Nova player/merc, Lightning
Strike player), independently test class boundaries while retaining wearer-only
pierce and merc aura/weapon semantics. Add class guards only after reviewing sources;
update existing unit contexts currently omit class. Then native cases, pins,
publication/replays/completion. Do not replace native generic utility with a Nova
recommendation for unrelated classes.

SECOND: FISSURE_GUIDE_USE_REVIEW.json captures6old roles lacking guide endorsements,
exact sourceequipment/quotes and variant flags. Allvariants planner_only=false and
delta_only=false. Standard/MF Fortitude prose says Might, plannerHolyFreeze: preserve
conflict. Four mercenary roles currently have no mercenary_type guard; review scoped
component utility versus exact setup advice before endorsing. PlayerLore and
playerFlickering require source/context/bank review too. Never append endorsements
merely because profiles exist. All original queues remain required; goal ACTIVE.

Completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1689, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 115402}; complete=false.

## Infinity class guards verified and Sacred Rondache replay, 2026-09-28

Selected generation 8d57f6ff033bce603e2b8ce34fe13cd17dd6b8c013f0c2f5866ec100038edee6 (80 artifacts). Three Infinity roles now require their source-confirmed beneficiary class: Nova Standard/player and Hybrid/merc Sorceress; Lightning Strike/player Amazon. Whole compiled diff only adds class guards. Existing guide/stat fingerprints updated. Native red18fail/9pass -> staged27pass; selected36pass including existing quality cases; role/stat tests5pass. Four test files lint/format clean. Twenty saved replays match text, price_estimate and extraction; named gate548/35sets/2958renders, all error counts zero. Bank4333cases/4325targets/3580missing. All-item goal remains ACTIVE and incomplete.

Sacred Rondache saved replay and both tests pass: Spirit/Paladin caster, +27 vs preferred +45allres, noneth player use, socket preparation conditional on item level. No matching offline price. Python worker restart/live delivery still unverified; no host launch performed.

Next: FISSURE_GUIDE_USE_REVIEW.json six source endorsements, player Lore/Flickering first, Ubers merc next, preserve Standard/MF Might-versus-HolyFreeze source conflict. No one-shot mutation scripts may be rerun. Completion evidence: tmp/infinity-class-completion.json. No commit, staging or live collection.

## Fissure six demand endorsements verified, 2026-09-28

Selected generation 877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec,80artifacts; prior c93157fce099f6c62f72511465826a0c8ead72d9c4d5f9b0e11fa1e923281847 retained. Six existing roles now have explicit guide-use endorsements: Starter player Lore preferred, Standard player Flickering Flame alternative, Standard/MF merc Fortitude preferred, Ubers merc CoH/Flickering preferred. Sourceclass Druid and exact variant slots/prose verified. All2564 profiles remain byte-equivalent; no matching gate changed. Contrary to earlier concern, four mercenary roles already have typed depends_on mercenary and companion predicates. Might/HolyFreeze disagreement is preserved for Standard/MF; Ubers requires Might.

Corrected Flickering merc Resist Fire explanation: aura supports nearby Druid while active; fire skills/pierce remain wearer-only. Native skills.json /100 supports targeted resistance aura and range; guide explicitly counters Flame Rift. Audit other aura explanations found no same generic erroneous wording. Compiled diff tmp/fissure-compiled-diff.json: six guide uses added, one stat-review text changed only.

Red2 player demand checks ->26 focused pass; red5 merc checks ->5pass. New native bank69player+108merc cases; staged pass individually, selected177pass.20saved reports match text/price_estimate/extraction. Named gate548eligible/35sets/2958renders allerrorcounts0. Bank4510cases/4325targets/3568missing. Fullbank/fullrepo/finalgates/hostdelivery remain unverified. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1689, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 115402}; complete=false. Goal remains ACTIVE.

Next: FISSURE_SOURCE_LINK_REVIEW.json inventories55 exact source occurrence candidates. Review actual sections/wearer/variant/native children; do not map old shared planner setups to current variants automatically. Fissure has0 entries in embedded_item_links (legacy guide format), so use appropriate exact context/table/slot review. These endorsements do not close all source occurrences. All original market/roll/report/leveling queues remain required.

One-shot tmp/add_fissure_player_endorsements.py and tmp/add_fissure_merc_endorsements.py succeeded; NEVERrerun. Processes84329,53278 completed successfully; no active task process remains. Logs tmp/fissure-player-*,tmp/fissure-merc-*,tmp/fissure-all-bank-selected.log. No live collection/hostrestart/commit/staging.

## Fissure exact table source closure, 2026-09-28

30general player-table occurrences now have validated equivalence links to existing source-bound roles. Two are Lore/Flickering general helmet alternatives, distinct from Starter staffmod-specific Lore.27other named/word entries preserve exact slots including Phoenix weapon versus shield, Naj/Harmony weapon swaps and Lidless off-hand swap. Original Flame Rift table span162 references decoded vf0106vk item149:quality6/unique402,300immunitypierce,-70fireres,noneth,0s; catalog confirms original, not current crafted variant. Planner and game-data witness hashes are now validated as optional corroborating inputs by table_equivalence compiler. Red stale-witness test failed before fix; rejects changed planner afterward.

Validation:15maintenance tests pass including exactFissure source mapping and existing wrong-context/stale-source cases.36new native LoreCap/FlickeringBoneVisage cases pass staged and selected over all3qualities, wrong/unknownclass, ethereal/unknownethereal and unmade boundaries. Bank {"cases": 4546, "required_targets": 4325, "targets_missing_cases": 3562}. Publication reproduced unchanged runtime877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec (80artifacts); no appraisal matching/rendering/data changes. Runtime saved replay20match evidence from prior turn remains applicable; no repeat runtime changes to validate. Lint clean5files.

Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1719, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 115372}; complete=false. These30source links do not certify other item-bank/market/roll/report dimensions. Fullgoal ACTIVE. Next review remainingFissure rawprose/merc/variant/planner contexts in FISSURE_SOURCE_LINK_REVIEW.json; tablelinker accepts playerMainalternatives only and must not be relaxed to swallow narrative or mercenary uses. Existing known Meteor/missingEchoingset source blockers remain; independent work continues.

Successful one-shot scripts NEVERrerun:tmp/link_fissure_helmet_tables.py, tmp/link_fissure_other_tables.py, tmp/link_fissure_original_rift_table.py. Logs tmp/fissure-table-*,tmp/fissure-rift-link-red.log. All process handles terminal, including39470completion. No live collection/hostrestart/commit/staging.

## Fissure Ubers narrative source links, 2026-09-28

Three more exact raw-guide occurrences reviewed:section25 Chains of Honor span36 and Flickering Flame spans34/37. New variant_mercenary_narrative kind reuses existing WP variant roles only when exact same-section raw passage equals a quote in exact primary variant; source hash, build/class, variant, merc equipment slot/name, and mandatory typed mercenary condition (must or required dependency) validate. Ubers remains Druid/Act2Might plus Infinity and complementary CoH/Flickering. No source context, profile matching or report data rewritten. Preferred endorsements are now consistently accepted by source-context compiler. New helper variant_mercenary_context.py included in completion policy fingerprint.

Red1positive/6negative ->25source-context checks pass; persisted links red1 ->26pass combined. Completion42tests pass. Final recognized-class guard recheck8pass;lintclean. Existing108native merc cases cover unchanged actual item rules. Selected runtime remains 877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec; no runtime artifacts/code changed so no host restart or new publication needed for maintenance-only linking.

Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1722, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 115369}; complete=false. All-item goal ACTIVE. Native bankcoverage unchanged4546cases/4325targets/3562missing (regeneratedfornewtestfiles). Remaining rawFissure Standard playerFlickering span19/section16 could use exact variant-player link; intro span1 is broader, not interchangeable. Fortitude23/26 need explicit Might/HolyFreeze conflict preservation; general mercenary table section46 has multi-bearer branches. See FISSURE_SOURCE_LINK_REVIEW.json updated evidence.

One-shot tmp/link_fissure_ubers_narrative.py SUCCESS, NEVERrerun. All handles terminal including27215; logs tmp/fissure-variant-*. No live collection/hostrestart/commit/staging. Broader source, market, variant/range, report, leveling, fullbank/fullrepo and delivery gates remain unfinished.

## Fissure Standard player narrative verified, 2026-09-28

Raw span19/Setup section16 now links exact Standard player Flickering Flame alternative. Primary variant1 quote is a verbatim substring of that raw section; slot/class/source/variant and same-section checks hold. No mandatory ideal-base staffmod,99FCR complete-loadout guarantee, intro-span1 or mercenary equivalence inferred.

Maintenance helper renamed variant_mercenary_context.py -> variant_prose_context.py and generalized to explicit player/merc kinds with side-specific matching. Mercenary typed-context requirement remains unchanged. Completion policy hashes new helper. Red player proof1failed5pass ->32combined contextchecks pass; persisted linkred1 then final75source-context/completion tests pass. Lint and format5files clean. No appraisal runtime changes; selected generation 877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec unchanged, previous native69player/108merc runs remain applicable. Bankcoverage regenerated4546cases/4325targets/3562missing.

Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 1723, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 115368}; complete=false. Goal ACTIVE. Next exact Fissure Fortitude spans23(section17)/26(section21): explicit Might prose/HolyFreeze planner conflict, existing mercenary dependency is disjunction. Do not force singleton proof or eraseconflict. Standard player introspan1 remains broader. General merc table section46 preserves multiplebearer branches. FISSURE_SOURCE_LINK_REVIEW.json records details.

For wider closure, audit exact table-equivalence family across guides; ensure enclosing PLAYER Gear Options section is independently validated before broad joins (raw parser side agreement alone is insufficient for known misclassified merc tables). Then apply reviewed family links to already source-bound profiles without reclassifying items or merging contexts. Keep item-bank,pricing,range/report gates separate.

One-shot tmp/link_fissure_standard_player_narrative.py SUCCESS; NEVERrerun. Firstpipeline77392 stopped onlint after mutation; continuation5635 completed successfully. All handles terminal. Logs tmp/fissure-player-prose-*,tmp/fissure-player-link-*,tmp/fissure-player-final-green.log. No live collection,hostrestart,commit or staging.

## Plain player-table family closure, 2026-09-28

Closed554new exact plain player-table links across24guides, reusing existing reviewed rules. pre-existing42table links plus554new =596total. Mandatory independent rawHTML boundary added: actual table membership AND enclosing Gear Options heading from all heading levels; raw sections and cached sections must agree. New player_table_context.py in completion policy fingerprint. Red4falseaccepts (mercenary h4ignoredbyoldextractor,othersection,outside-table,forgedsectioncache) ->green. Per-validation pinned source/JSON/guide caches avoid repeated hashing/parsing; caches reset each call and stale witness tests still pass.

Audit initially585mechanicallyvalid candidates from25guides after14qualified-label rejections.14original-sunder references deferred for native identity witness. Initial571appended passed structuralvalidator, but completion rejected17overlapping Abyss dedicated contextreviews. Those17newduplicates removed; original contextreviews retained. Added red-green overlap regression. Final554new links do not change any profile predicates or establish item-bank/price/range completion. PLAYER_TABLE_LINK_AUDIT.json preserves exact members,rejections,priorcontexts,linkedcounts and evidence.

Final63tests pass (tableboundary/existingproofs,24buildsamples,overlap and completion). Lintclean. Coverage regenerated4546cases/4325targets/3562missing. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2277, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 114814}; complete=false. Selected runtime877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec unchanged; maintenance-only changes, previous runtime replay evidence still applies. All-item goal ACTIVE.

Next:14qualified set/upgrade source rows and14sunder original-vs-crafted witnesses in PLAYER_TABLE_LINK_AUDIT.json. Read actual complete labels/companions/upgrades/native references; do not relax plain equality to substringmatching. Fissure Fortitude23/26 still pending: reconciledissue approves narrower etherealSacredArmor roles, broaderbase/nonethroles need independent disjunction scopeproof. Remaining source/market/variant/report/fullbank/delivery queues all required.

One-shot tmp/link_plain_player_tables.py SUCCEEDED then17duplicates removed once; NEVERrerun. tmp/audit_player_table_links.py overwrites the durable audit and must not rerun after endorsement without a new output path. Allprocesshandles terminal including63465completion. Logs tmp/player-table-*,tmp/plain-player-table-*. No live collection,hostrestart,commit/staging.

## Original sunder table witnesses, 2026-09-28

Nine deferred table references resolve to original unique forms via actual referenced planner item and catalog: DreamFlame/Bone/Crack; LightningSorcCrack; PoisonNovaBone/Flame/Rotting; DoubleThrowBone; LightningStrikeCrack. Maxroll quality6, catalog unique IDs and fixed native immunity300 checked; separate planner/catalog hashes now validated as corroborating table proof. No crafted/Latent/Renewed equivalence inferred. Five remaining labels have no planner/itemID or embedded ref: BlizzardCold,StrafeBone,LightningSentryCrack,MeteorFlame,WakeFireFlame. Preserve explicit identity-form gap.

54new native-bank cases verify class/unknownclass, native300 versus299/unknown, and crafted-form rejection.54staged and54selected pass;60source/completion tests pass. Lintclean3testfiles. Bank {"cases": 4600, "required_targets": 4325, "targets_missing_cases": 3553}. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2286, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 114805}; complete=false. Selected runtime877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec unchanged, maintenance provenance/test changes only. Fullgoal ACTIVE.

Next14qualifiedtable entries in QUALIFIED_TABLE_LINK_REVIEW.json include2pieceAngelic,3pieceIK/Trang,2DeathbitUpgradedslots,Stormlash(Shael),RuneMaster(5Ist). ActualHTML places qualifiers immediately after namedspan, sometimes nested itemspans. Must validate entire qualifier plus actual rule companion/upgrade/socket conditions; no plain substring shortcut. Their native snapshots/labels retained for review. Fortitude conflict and other queues staypending.

One-shot tmp/link_original_sunder_tables.py SUCCESS NEVERrerun. Earlier readonlynativeaudit failed afterfirstrow dueblankplanner IDs, then corrected complete14audit; no partialmutation. Allprocesshandles terminal including48440. Logs tmp/original-sunder-table-*. No livecollection,hostrestart,commit/staging.

## Qualified table source closure, 2026-09-28

All14 formerly deferred qualified table occurrences now have validated links:5Angelic jewelry,4IK pieces,Stormlash(Shael),RuneMaster(5Ist),TrangWing(3pieces),DeathbitUpgraded weapon/offhand. New qualified_table_context validates exact approved primary label AND required dependency, or mandatory native elite Deathbit base. TableMentions now captures the complete entry including nested rune/set markup through the next br/cell boundary. Plain-label validator remains strict; no arbitrary substring equivalence. New helper and dependent templates included in completion policy fingerprint. QUALIFIED_TABLE_LINK_REVIEW.json retains exact rows and validations; original PLAYER_TABLE_LINK_AUDIT label rejections are historical, now annotated with links.

Red5 missing parser/qualification tests ->green; upgradedDeathbit red1 ->green.55native item-bank cases pass staged and selected: distinct/missing/unknown/self/duplicate companions, exact/wrong/empty fillers, native upgraded/original Deathbit in both slots.69source/completion tests pass; lint clean7files. Runtime profiles and artifacts unchanged; selected877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec, previous20replay equality still applicable. Bank {"cases": 4655, "required_targets": 4325, "targets_missing_cases": 3543}. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2300, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 114791}; complete=false. Fullgoal ACTIVE; fullbank/fullrepo/finaldelivery remain unverified.

Next: broad Fissure Standard/MF Fortitude source disjunction proof (existing reviewed issue covers narrower ethSacredArmor roles only); five sunder table labels have no native pointer and remain pending. Continue other item-bank/market/roll/report/leveling queues; all14 qualified rows are done. No livecollection/hostrestart/commit/staging. Python hostdelivery gap remains.

Successful one-shots tmp/link_qualified_equipment_tables.py (11links) and tmp/link_qualified_upgrade_trang_tables.py (3links) MUST NOT rerun. All processes terminal including82601,58105,60412,96697,11609,81813. Logs tmp/qualified-table-*. Scope e347abb999001e58f673d8cfb5903ac9265748bcf5d6f17f9934e103bf00220f.

## Fissure Fortitude broader source choices, 2026-09-28

Two variant mercenary prose occurrences (rawspans23/26) now link to existing broader Standard/MF Fortitude component roles. New variant_mercenary_choices.py validates explicit required Might/HolyFreeze disjunction, independently scoped component review, exact WP variant snapshot and current tt9vl0l2 planner profile/item23 witnesses. Keeps Infinity dependency and ethereal preference. Does not reuse or modify narrower reviewed_source_issues SacredArmor proof. Unverified/missing/stale choice reviews, changed aura, missing armor witness or wrong variant rejected. Optional dependencies no longer establish required variant bearer. No runtime profile/artifact changes; selected877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec unchanged.

18added bank scenarios cover ArchonPlate, nonethHolyFreeze, unknownInfinity equipment across both variants/all3qualities.126staged and126selected Fissuremerc bank pass.12choice-proof tests pass; combined source/completion suite initially88pass2fail due obsolete global Fortitude buildcount15 (actual16alreadyinpublishedbundle). Replaced unrelated globalcount with exact Fissure variant preferred endorsement;3narrow-source tests pass preserving both originalethSacredArmor boundaries. Lintclean7files. Bank {"cases": 4673, "required_targets": 4325, "targets_missing_cases": 3543}. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2302, "excluded_occurrences": 4822, "coverage_rows": 8624, "remaining_tasks": 114789}; complete=false; allgoal ACTIVE. No claim fullrepo/fullbank/finalgates complete.

FISSURE_SOURCE_LINK_REVIEW now records39remaining candidate occurrence IDs. Concrete nextgap: Fissure player Mainalternatives Chains of Honor table span110 + WPslotBodyArmor/5 have no general role, only narrow Ubers DuskShroud role. Implement actual general guide alternative and nativecases; do not reuse Ubersbase/setup constraints as universal. Other mercenary table contexts, old planner variants, market/roll/report queues remain required.

One-shot tmp/link_fissure_fortitude_choices.py SUCCEEDED(2links), NEVERrerun. Allprocesses terminal57452,25135,1417,81222,2513,1873,31608. Logs tmp/fissure-choice-*. Previous runtime20replay equality evidence remains applicable. No livecollection/hostrestart/commit/staging. HostPythondelivery still unverified.

## Fissure general Chains of Honor published, 2026-09-28

New role fissure-druid-chains-of-honor-general-armor binds primary BodyArmor/5 and rawtable span110. Source_recipe template bounded to FissureDruid/player/bodyarmor; legal4socketnoneth completed armor all3qualities, no arbitrary DuskShroud or Ubers setup restriction. Skills/resistances/physicalDR desirable; Strength/ReplenishLife/MF/EDef supporting. Weapon leech and demon/undead damage receive no Fissure spell credit; missingTeleport/FCR tradeoff explicit. Native recipe+runes corroborated. Existing2564 profile dicts byte-equivalent; one newrole plus alternative demand/stat review. General table link and primary occurrence now reviewed.

Red nativeArchon case missingannotations ->27staged and27selected cases pass: Archon/Dusk/Sacred across3qualities, eth/unknowneth, wrong/unknownclass, unmadeword, illegalshield.59maintenance tests pass; lint clean3files.20saved replays identical staged/selected for text,price_estimate,extraction. Report inspected tmp/fissure-coh-example.txt: expected10statannotations, weapon-only bonuses neutral. Namedgate548eligible/35sets/2958renders allerrorcounts0. Planner audit114,0newguide/sourceissues; unsupportedMeteor1r010653 remains unresolved.

Selected generation d2d3523681af701e4f4374fb223b1ace0c6702289e81201b0164e2a922653496 (80artifacts), prior877e3ed2a29137d54773f713e84185a9bcea19a542c957af63e34e40c4c161ec retained.2565profiles/2557statconfigs. Bank {"cases": 4700, "required_targets": 4328, "targets_missing_cases": 3543}. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2304, "excluded_occurrences": 4822, "coverage_rows": 8627, "remaining_tasks": 114805}; complete=false, goalACTIVE. New known configuration adds3coverage rows, so remaining taskcount grows despite2source closures; no fullcoverage claim. Fullbank/fullrepo/finalgates/hostdelivery unverified.

FISSURE_SOURCE_LINK_REVIEW records current pendingcandidate IDs and next actual armor gaps: Smoke,Treachery,Skin of Vipermagi,4PerfectTopaz DuskShroud. Current generalFissurebodyroles cover Skullder/Wealth/Rain/newCoH plus separate Enigma/UbersCoH variants. Verify exact source and caster contributions, Fadeproc is not automatically active. Other original queues stayrequired.

One-shots tmp/add_fissure_general_coh.py and tmp/link_fissure_general_coh_table.py SUCCEEDED, NEVERrerun. First rebuild failed because manifest profile_order omitted newID; one recovery appended ID and set coverage count2565, subsequent fullrebuild succeeded. Allprocesses terminal89380,73720,12135,53338,71556,91081,79123,8776,20764,52583,49270,3521. Logs tmp/fissure-coh-*; standard rebuild logs tmp/final-charge-routing-*. No livecollection/hostrestart/commit/staging.

## Fissure armor tail and mercenary IAS delivered, 2026-09-28

Four new general player armor assessments: Smoke legalbodyarmor, Treachery conditionalFade/FHR/coldres, Vipermagi nativeupgradechain, DuskShroud4verifiedPerfectTopazes for96MF. Nonethereal playerdurability, all3basequalities, minimumVipermagirolls and actuallinkedgem payload tested. New source_recipe Smoke/Treachery memberships boundedFissure; caster_core addsFissure onlyforVipermagi. Topaz uses reviewedpattern source with exactquoted WPslot and nativegemsource.3rawtable links forSmoke112,Treachery113,Vipermagi109; Topazraw107/108 stillpending specializedpatternproof. WPprimarysources and3tablelinks close7occurrences. All2565previousprofiledicts unchanged;4rolesadded.

Humanrender inspection caught IAS markeddesirable by older fissure-starter-merc-treachery evenwithunknownmerc. Redunit provedbug. Updatedonlyits93:0priority activation to knownInsight-compatible attacking Act1/Act2 types (nativeThorns verified); unknown andAct3caster stayneutral. No profile predicate changed.3extra nativeknownPrayer cases verifyIASgreen foractualmerc; castercases assertIASnotannotated. Otheroldstatreviews unchanged. OthergenericStartermerc attackproperties (lifeleechetc) need same beneficiaryaudit, not assumedcomplete.

Validation: initial6red absentrole cases ->65stagedpass; afterIASfix final68staged and68selectedpass.15sharedtemplate tests,59maintenance tests,1focusedIASred-green pass. Lintclean5files.20savedreplays matchtext/price_estimate/extraction. Examples regenerated tmp/fissure-armor-example-*.txt: Smoke8keys,Treachery3(noIAS),Vipermagi8,Topaz1. Namedgate548eligible/35sets/2958renders allerrors0. Planner114,0newguide/sourceissues; unsupportedMeteor1r010653 stillpending.

Selected2856b37a1b9a62d4ef47231bba57c0760b88da1e192a5cf66f8b0ece8c500933 (80artifacts); prior d2d3523681af701e4f4374fb223b1ace0c6702289e81201b0164e2a922653496 retained.2569profiles/2561statconfigs. Bank{"cases": 4768, "required_targets": 4338, "targets_missing_cases": 3543}. Completion{"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2311, "excluded_occurrences": 4822, "coverage_rows": 8637, "remaining_tasks": 114857}; complete=false. Newknownconfigurations add10coverage rows so remainingcountgrew despite7sourceclosures. GoalACTIVE; fullbank/fullrepo/finalgates/hostdelivery unverified.

Nextactualgaps recorded in FISSURE_SOURCE_LINK_REVIEW: qualified Topazrawsource proof (parent107/filler108), generalEnigma base support (only specificStandard/MF ArchonPlate profiles), olderStartermerc attack-stat beneficiary audit. Allothermarket/roll/report/leveling/sourcequeues stayrequired.

One-shot tmp/add_fissure_armor_tail.py SUCCEEDED; NEVERrerun. Firsttwoattempts failed beforeanyfilewrites (templatekey caster_core vs actualcaster_core_gear; Topaz neededpattern endorsement). Third succeeded. tmp/link_fissure_armor_tail_tables.py SUCCEEDED3links; NEVERrerun. IASinlineprioritypatch alsoSUCCEEDEDonce; do notnestagain. Rebuild repeatedonlyafterrealIASdatachange; final68case logs supersedeinitial65. Allprocesses terminal including49400,63719,92280,1427,87977,75620,13701,79042,15766,84489,2021,81658,89958,43946,87007,95711,20334,21205,65068,24440,17949,94445,15238. Logs tmp/fissure-armor-tail-*,tmp/fissure-armor-ias-*. No livecollection/hostrestart/commit/staging.

## Fissure four-Topaz source proof, 2026-09-28

Parentraw107 ee4737fc39641c54a19681b0 andnestedgem108 8ff3e7f18db075fe8cd1b1ce now linked to fissure-druid-perfect-topaz-general-armor. New socketed_table_pattern.py validates exact bounded full HTML label, primary WPpattern endorsement, required DuskShroud/4s/noneth/identified predicates andmandatorylinked4Topaz+96MF dependency. Native referenced vf0106vk item82 verifies base,quality1,4s and4gemcodes; pinnednativegem armor effect24MF. Missingethflag inplanner is not treated as observedethstate. Component must lie withinparententryend beforebr/cell boundary. TableMentions recordsentry_ends without changing legacymentions. Namedtable checks remainstrict; onlyexplicitreviewedpattern mode bypasses namedidentity requirement, then usesboundednativeproof. Parentcanonical identity remains unresolvedpattern globally; sourceclosure is not discoveryclosure.

Red2missingproof/bounds ->72source/completion checks pass;4focused tests pass including8wrongscope/payload/nativeeffect mutations and2stale-witness hashes. Lintclean5files. Completion input pins rehashed current afterbankcoverage refresh. Bankunchanged4768cases/4338targets/3543missing. Runtimeunchanged selected2856b37a1b9a62d4ef47231bba57c0760b88da1e192a5cf66f8b0ece8c500933 (80artifacts,2569profiles/2561configs); prior68selecteditemcases/20replay equality remainapplicable. No runtimepublicationneeded forprovenance-onlychange.

Completion{"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2313, "excluded_occurrences": 4822, "coverage_rows": 8637, "remaining_tasks": 114855}; complete=false. GoalACTIVE; fullbank/fullrepo/finalgates/hostdelivery remainunverified. NextgeneralEnigma base support andolderStartermerc lifeleech/attack-only beneficiary gates; globalpatternidentitydiscovery separate. FISSURE_SOURCE_LINK_REVIEW updated, rawTopaz107/108 no longerpending.

Successful one-shot tmp/link_fissure_topaz_pattern.py appended2links; NEVERrerun. Allhandles terminal15939,16725,65848,49895,76317. Logs tmp/socketed-table-*. No livecollection/hostrestart/commit/staging.

## Fissure general Enigma published, 2026-09-28

Added fissure-druid-enigma-general-armor for general Body Armor/0 and raw table104. Legal nonethereal completed three-socket body armor alternatives across normal/superior/low_quality; no Archon Plate restriction inherited from Standard/MF. Ten native skill/mobility/survival/recovery priorities; character scaling, no self-equipping Strength assumption, full FCR and base requirements remain separate. All previous2569 profiles unchanged. New source/use/stat review validated.

Red missing native MagePlate annotations ->33 staged and33 selected bank cases pass;44 maintenance tests pass; lint clean3files.20 saved replays match text/price_estimate/extraction. Example inspected tmp/fissure-enigma-example.txt. Namedgate548identities/35sets/2958renders allerrors0. Planner114,0newsourceissues; unsupportedMeteor remains. Selected e4820a20cb59eca54703f012fc4e7472d29cdfb39e136017b103250f92a04786,80artifacts,2570profiles/2562configs; prior2856 retained. Bank4801cases/4341requiredtargets/3543missing. Completion2315reviewedof62891occurrences,4822excluded,8640coverage rows,114871remaining; complete=false. Newconfiguration adds3rows; no fullcoverage claim. Host Python delivery remains unverified.

Successful one-shots tmp/add_fissure_general_enigma.py and tmp/link_fissure_general_enigma_table.py MUST NOT rerun. Recovered original rebuild handle20132 completed; all publication/bank/replay/completion handles terminal. Logs tmp/fissure-enigma-*. Next older Startermerc lifeleech beneficiary gates, then globalpatternidentity and fullremaining queue. GoalACTIVE; no livecollection/hostrestart/commit/staging.

## Starter mercenary life-leech beneficiary correction, 2026-09-28

Undead Crown and Bulwark stat60 priority now requires a known Act1/Act2 attacking bearer in the Fissure Starter Insight context. Unknown bearer/Act3 caster retains plain observed leech and independently highlighted defensive stats. Roles themselves unchanged; all2570 profiles identical to previous generation and only these two stat configurations differ. Two red regressions ->6unit tests green;32newnative bank cases staged and32selected pass (allBulwarkbasequalities; positive/zero/unknown/wrongclass/unidentified). Report examples inspected tmp/fissure-leech-*-example.txt.20savedreports unchanged fromprior and staged/selected text,price_estimate,extraction equal. Lintclean3files; namedgate548/35/2958errors0.

Selected7fdd3afaf2dc607c096585f8d50742df713e561c1a06d0be23a573b3398c8ced,80artifacts,2570profiles/2562configs; previouse482retained. Bank4833cases/4341targets/3539missing. Completion refreshed after firstattempt correctly rejected staleplannerreachability; planner_source_audit regenerated thencompletion passed. Complete=false, fullgoalACTIVE. No livecollection/hostrestart/commit/staging. Logs tmp/fissure-leech-*. Allhandles terminal81975,89476,74161,43205,70458,1138,32197,53380,19187,33538,52786,42701; failedcompletion39863 superseded.

Next audit found one merc Vitality priority: fissure-starter-merc-rockstopper. Local D2MOO D2StatList.cpp case9 (lines377-403) converts Vitality into Life only for UNIT_PLAYER; native itemstatcost must corroborate operator9 before changing it. Do not conflate maxLifepercent (operator may applyto monsters) with Vitality. Other pendingCBF/requirements, globalGemmedDuskShroudpatternidentity, andallremainingcontractqueues remain.

Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2315, "excluded_occurrences": 4822, "coverage_rows": 8640, "remaining_tasks": 114871}

## Mercenary Vitality corrected; socketed armor family audited, 2026-09-28

Native itemstatcost Vitality op9 plus D2MOO D2StatList.cpp UNIT_PLAYER guard corroborates no hireling Life from Vitality. Removed stat3priority and important_stats entry ONLY from fissure-starter-merc-rockstopper; updated exact guide/stat review fingerprints. Raw Vitality remains visible. No other mercenary Vitality or Energy configurations exist. MaximumLifepercent is op11 and accepts UNIT_MONSTER;105merc configs preserved. MERCENARY_ATTRIBUTE_REVIEW.json records source hashes and legacy-runtime limitation. No liveprobe.

One red Rockstopper assertion ->6unit tests green;6new nativebank cases staged/selectedpass, include known/unknownbearer,Act3,ethereal,wrong/unknownclass,visibleVitality. Only Rockstopper profilepriority changed; all other2570profile predicates retained.20savedreplays match text/price_estimate/extraction. Lintclean3files; namedgate548/35/2958errors0. Selected66abc4ae2b669c3ddf0586e3d0c72f05f461eab946b7a9d2f3a2698dc76b5076 (80artifacts,2570profiles/2562configs), prior7fddretained. Bank4839cases/4341targets/3538missing. Completion refreshed complete=false.

Next family source audit in GEMMED_DUSK_SHROUD_REVIEW.json:25occurrences,11rawmerc tables reference fc01065b item93 DuskShroud4s containing Ral/Ort/Thul/Tal (native armor effects30fire/light/cold/poisonres respectively),10structuredmerc entries,4rawplayer4PerfectTopaz entries. Fissureplayer alreadylinked. Others await exactcontext/payload handlers and sourceproof. This label cannot be universally mapped to one configuration or given one desirability. No ethstate inferred from missing plannerfield. Implement shared mercresistancepayload family, preserve class/bearer/source conditions; add positive/missing/wrongchild/unknowncases per reviewedbuild.

Allhandles terminal85906,5799,37556,33717,98032,45077,26888,72049,96850,69434,15695. Logs tmp/fissure-vitality-*. No one-shot appenders run; raw correction script succeeded once, do not repeat. No livecollection/hostrestart/commit/staging. GoalACTIVE; fullbank/fullrepo/finalgates andPythonhostdelivery remainunverified.

Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2315, "excluded_occurrences": 4822, "coverage_rows": 8640, "remaining_tasks": 114871}

## Eleven mercenary resistance-armor assessments published, 2026-09-28

Implemented shared resistance_rune_armor template in maintenance/resistance_armor_templates.py, registered in profile_templates.py. Eleven explicit build memberships retain their source-specific player classes and early mercenary choices: Might/Holy Freeze alternatives for Lightning Fury and Lightning Sorceress; Holy Freeze for Lightning Strike; Prayer for Enchant; Might/Act5 Frenzy for Double Throw and Zeal; Might/Act5 Bash/Frenzy for Fissure; Might for Poison Nova, Summoner, Berserk and Dream. Requires identified Dusk Shroud,4filled sockets, exact linked Ral/Ort/Thul/Tal and observed30fire/lightning/cold/poison resistance, across normal/superior/low_quality. Ethereal preferred, not required; unknown ethereal does not block these resistance benefits or establish a premium. Dusk requirements, lack of leech/DR, destruction of fillers on clearing and separate player Topaz use are explicit.

Primary sources are exact cached Mercenary Gear Options sections. Native fc01065b item93 and four exact gems.json rune records corroborate socket payload/effects. New11 profile/use/stat reviews; previous2570profiles unchanged. Native red Fissure example failed missing annotations, then381 staged and381 selected cases pass. Four shared maintenance tests pass. Example inspected tmp/merc-resistance-example.txt. Namedgate548eligible/35sets/2958renders allerrors0. Planner114/0newissues; unsupportedMeteor remains. Twenty saved replays match text/price_estimate/extraction. Selected0a7413a5dd78b148f316ba66060a189fa48b986fb7f91b0ab379027fe6f80886,80artifacts,2581profiles/2573configs; prior66abc retained. Bank5220cases/4374targets/3538missing. Completion remains false; added33configuration-quality rows increase remaining work count despite new executable coverage.

GEMMED_DUSK_SHROUD_REVIEW.json records all25 occurrences and new11 profile links. Exact completion source links are still pending for11rawmerc and10structured entries. Their native witnesses all agree, but do not mark these21 occurrences reviewed until the compiler validates each complete context. Added table_cells.py CellMentions and require_early_armor_cell as a tested prerequisite: preserves table/row/cell per mention and rejects wrong/outside/late/other-table/spanning layouts. Initial missing-module red plus spanning-layout red;7cell tests and4existing socketed-pattern tests pass (11total). All11real merc guide references verified at exact Early-Game Body Armor coordinates after final guard. This helper is not yet wired into completion.

NEXT: implement dedicated resistance-armor source-link validator, binding role/use fingerprints, exact cached section and raw guide hashes, typed bearer membership, early table cell, native planner93/rune effects. Link raw11 and structured10 only after positive and stale/wrong-context/payload tests. Preserve unresolved global Gemmed Dusk Shroud identity and three remaining player Topaz references; Fissureplayer already validated. Continue all other completion-contract dimensions afterward.

One-shot tmp/add_merc_resistance_armor.py SUCCEEDED; NEVER rerun. First build failed because profile corroboration cannot resolve HTML /html or JSON root /; fixed11sources to exact planner /data and four rune JSON pointers, updated use/stat fingerprints, then full rebuild passed. All process handles terminal10267,19253,73321,93132,33554,76410,69507,77521,41197,52802,99806,56974,68244. Logs tmp/merc-resistance-*. Lint clean template/registry/bank/cell helper/tests. No live collection, host restart, commit or staging. Goal remains ACTIVE; full-bank/full-repo/final gates and prior Python worker delivery unverified.

Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2315, "excluded_occurrences": 4822, "coverage_rows": 8673, "remaining_tasks": 115069}

## Resistance armor source closure and duplicate correction, 2026-09-28

Added resistance_armor_links.py, dispatched only explicit merc_resistance_armor reviews from table_equivalence. Validates exact reviewed template/role/use fingerprints, class/side/slot, affirmative occurrence recommendation, raw/cache hashes and extraction equality, complete Mercenary Gear Options section, Early-Game Body Armor cell, exact fc01065b item93 and four native rune effects. Structured entries additionally require exact pinned WP early armor index/class/label. Policy fingerprint includes new validator, template and table_cells. Wrong re-fingerprinted bearer/payload/class/side/span, changed native item/effect, stale source hashes and wrong structured progression are tested. An explicit negative recommendation initially slipped through; red test proved it and the affirmative recommendation guard fixed it.

Initial21link append succeeded, but completion correctly found a duplicate ownership: Zeal span217 was already reviewed by zeal-paladin-early-merc-resistance-armor. Inspected old role and source; same four-rune setup and Might/Frenzy bearer choices. Removed only new zeal-paladin-merc-resistance-rune-armor profile/use/stat review and membership plus its redundant new tablelink. Redirected36newbank Zeal cases to the established role. All remaining2580profiles unchanged; no weakening of completion conflict detection. There are20newtable links plus1existing Zeal source, covering all21merc references.

84final source/table/completion tests pass;36Zeal staged and36selected cases pass. Other345family cases passed prior selected0a7413 with unchanged retained profiles.20savedreplays match text/price_estimate/extraction. Lintclean6files. Namedgate548eligible/35sets/2958renders errors0; planner114/0newissues, unsupportedMeteor stillpending. Selectedb960ef15e555829009a214157415b921e0db4b730f7d335c46ae05e8093ce3c5,80artifacts,2580profiles/2572configs, prior0a7413retained. Bank5220cases/4371targets/3536missing. Completion2335reviewed,4822excluded,8670rows,115031remaining; complete=false. GoalACTIVE; fullbank/fullrepo/finalgates and prior Python hostdelivery remainunverified.

Next actual missing player configurations confirmed from inventory and profile audit: Berserk raw87 native rk0106ln item92; Double Throw raw143 db0106mf item92; Lightning Strike raw107 vc0106wm item94. All three native bodies are DuskShroud4PerfectTopaz; Fissure alreadyhandled. Add these three player memberships and item-bank cases, extend bounded player-pattern proof with exact variant labels (Berserk singular Topaz, others Topazes), and link parent/nested gem and primary occurrences. Then resolve the global Gemmed Dusk Shroud identity as a reviewed collection of distinct configurations, not one named item. Keep all remaining contract work.

One-shot tmp/link_merc_resistance_armor.py SUCCEEDED then its Zeal row was deliberately removed; NEVERrerun. Duplicate-removal inline script SUCCEEDED; do not repeat. Initialcompletion5294 failed conflict and was superseded by successful76991. Allhandles terminal84081,90731,49209,25879,27474,75711,3197,36214,54516,17206,41598,10921,62242,5001,14078,76991. Logs tmp/merc-resistance-links-*. No livecollection/hostrestart/commit/staging.

Completion counts: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2335, "excluded_occurrences": 4822, "coverage_rows": 8670, "remaining_tasks": 115031}

## Player four-Topaz armor alternatives published, 2026-09-28

Added Berserk Barbarian, Double Throw Barbarian and Lightning Strike Amazon general Dusk Shroud / four Perfect Topaz armor uses. Required linked payload and96MF, identified nonethereal player armor, three base qualities. Exact raw parent/child links and primary guide uses validated separately. Existing Fissure handling kept. No defense premium or numerical price inferred. All25 plain Gemmed Dusk Shroud source contexts have reviewed dispositions; global pattern discovery remains open.

Red missing assessment and three source links ->81staged and81selected bank cases pass;66maintenance checks pass.20saved replays match text,price_estimate,extraction. Selected 9dde192ebd2918190fcccf970b5eb7e99c22b27a433037d942075ec4b51bd6a6;80artifacts,2583profiles,2575statconfigs. Bank5301cases/4380targets/3536missing. Completion2344reviewed,4822excluded,8679rows,115076remaining;false. Final handles49721/43598/10404 exited0. Logs tmp/player-topaz-*. Successful tmp/add_player_topaz_armor.py and tmp/link_player_topaz_armor.py MUST NOT rerun. No livecollection/hostrestart/commit/staging. Goalactive; fullbank/fullrepo/finalgates/hostdelivery remain unverified.

## Reviewed pattern collection discovery, 2026-09-28

New maintenance/pattern_collections.py and rules/pattern_collection_reviews.json
validate complete occurrence membership and exact source-role links before closing
discovery. Compilation independently revalidates guide uses/dossiers and bounded
table equivalence; review pins identity, each occurrence and each profile. Missing,
new, duplicate, stale or wrong-role members reject closure. Coverage matrix keeps
collection identities distinct and closes only discovery, leaving all other
dimensions unchanged. Completion policy fingerprint includes the validator.

Three reviewed Dusk Shroud label collections cover29occurrences (25plain and4
decorated primary mentions). No variant/price/tier/report promotion. Red9missing
validator and red integration, then2missing decorated reviews ->58maintenance tests
pass43.29s. Ruffcheck/format clean4files. Matrix diff verified exactly3rows changed,
only discovery. Rebuilt completion: {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2344, "excluded_occurrences": 4822, "coverage_rows": 8679, "remaining_tasks": 115073},
complete=false. Selected runtime unchanged9dde192ebd2918190fcccf970b5eb7e99c22b27a433037d942075ec4b51bd6a6;
no publication or runtime testing needed for this maintenance-only change. Prior81
selected bank and20saved replay evidence retained, not reclassified as full gates.
All handles terminal76962/59065/96197/91560/91628/46262/1702/85435. Logs
tmp/pattern-collections-* and tmp/pattern-decorated-red.log. The inline creation of
pattern_collection_reviews and append of its two decorated records SUCCEEDED; do
not rerun. No live collection, host restart, commit or staging. Goalactive.

Next exact gap: two Berserk Starter variant occurrences with label
Gemmed Dusk Shroud (4x Perfect Topaz), no space before closing parenthesis, at
wp-a-variants/berserk-barbarian.json /variants/0/player/Body Armor/0 and
wp-a-builds.json /berserk-barbarian/variants/0/player/Body Armor/0. Starter source
references r2Hsc2Mk #6 level75. General alternatives use rk0106ln item92; never
substitute that witness for Starter without checking. Additional fully source-
reviewed unresolved labels include JMoD payload collections and Artisan diadems;
each still needs explicit semantic discovery review, not automated blanket closure.

## Berserk Starter Topaz armor and helmet published, 2026-09-28

Explicit guide Starter labels now supported: DuskShroud/fourPerfectTopaz96MF and
Crown/threePerfectTopaz72MF. Native armor/gem tables pinned; all3base qualities,
nonethereal identified player items, full linked payload and observedMF required.
Whole combat setup and base requirements remain conditional. Old r2Hsc2Mk planner
is not cached; no substitute planner, defense roll or native eth state inferred.
See planning/BERSERK_STARTER_TOPAZ_REVIEW.json. Two exact primary WPsource contexts
closed; their wp-a-variants mirror occurrences remain pending, along with collection
discovery for these exact spellings. Missing planner remains explicit research gap.

Red missing native armor annotation ->60staged and60selected item-bank cases pass.
20saved replays match text/price_estimate/extraction.12pattern maintenance tests
and2statbundle tests pass; lint/format clean3files. Statbundle stale hardcoded2556
count failed; replaced with exact equality against all reviewed configuration IDs,
duplicate/count checks and existing tamper rejection preserved. No fixed count bump.
Namedgate548/35/2958 allerrors0; planner114,0newissues, unsupportedMeteor remains.
All previous2583profiles unchanged. Selected 51aedd0bfd9142b5fabf43759ab68dd603604423030dc37568799c503713b81f
80artifacts,2585profiles/2577statconfigs; prior9dde retained. Bank5361cases/4386targets/
3536missing. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2346, "excluded_occurrences": 4822, "coverage_rows": 8685, "remaining_tasks": 115107};false.
Fullbank/fullrepo/finalgates/hostdelivery unverified; overall goalactive.

Successful one-shot tmp/add_berserk_starter_topaz.py MUST NOT rerun. All handles
terminal27906/18859/92266/69257/24498/11485/89715/13114/6371/41010/18898/80314/41383/61115.
Logs tmp/berserk-topaz-*. No livecollection/hostrestart/commit/staging.

Next: exact structured-source mirror linkage for armor0ff7e7f10298bff5d49f444d and
helmet7d927db7b5a0268e002a7463 (same Starter labels in wp-a-variants). Current
compile_demand requires use.source == role.source, so do not add another use with
a different source or duplicate runtime role. A reviewed structured-equipment
equivalence validator can pin both source documents and exact variant/player/slot
labels, preserving native payload predicates and independent missing-planner gap.
Then close only discovery for these labels once all occurrences validated. Continue
remaining family/source/market/report/bank completion work.

## Structured Starter source mirrors and discovery validated, 2026-09-28

New structured_variant_mirrors.py dispatched only explicit
structured_player_variant_mirror table reviews. Requires exact primary and mirror
variant/slot/index, full variant document equality (including companions), cached
class/build/url, positive source recommendation and unchanged reviewed role/use.
Revalidates native/profile sources. Supports missing redundant occurrence.class
only when both pinned source documents agree with the role class predicate. No
new runtime rule or missing-planner substitution. Two Berserk Starter mirrors
linked; two exact label collection discovery records now cover all4references.

Red2unimplemented and1unregistered ->92tests pass98.20s (source/table/collection/
completion). Mutations cover side,slot,class,label,index,hash,role,endorsement and
complete variant gear/mercenary changes. Ruffclean5files. Matrix diff exactly2
rows and only discovery changed. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2348, "excluded_occurrences": 4822, "coverage_rows": 8685, "remaining_tasks": 115103};false.
Selected51aedd0bfd9142b5fabf43759ab68dd603604423030dc37568799c503713b81f
unchanged; maintenance-only, no runtime publication/replays repeated. Prior60
selected bank and20replays still apply; no final/fullsuite claim. Goalactive.
Successful tmp/link_berserk_topaz_mirrors.py appended2table and2collectionrecords,
NEVERrerun. Handles82388/29687/97492/50779/47471/87964/89414 allterminal.
Logs tmp/variant-mirror-*. No livecollection/hostrestart/commit/staging.

NEXT IMPORTANT RCA: preparation rules were found satisfying full pattern source
coverage. Confirmed JMoD lightning-fury-main-shield source lists4RainbowFacets but
role accepts only empty sockets; LightningStrike ArtisanTopazCrown similarly only
empty while source lists3Topazes. Existing _pattern_bindings/compile_dossiers
classify these occurrences reviewed. Do not blanket-close other collections based
on those links. New PREPARATION_SOURCE_COVERAGE_AUDIT.json inventories all empty-
socket pattern uses as candidates; each needs review, not automatic classification.
Preserve legitimate empty-base runtime assessments, but record explicit partial
source coverage/remaining filled branches and keep completion + collection
discovery honest. Actual empty-base source labels can remain complete. Then
implement the missing filled-item configurations with native payload bank cases.

## Preparation source coverage corrected and published, 2026-09-28

Seventeen guide labels explicitly describing inserted facets/jewels/gems/runes
were incorrectly considered source-complete by empty-base-only rules. Added
validated use.source_coverage kind preparation_only + explicit remaining_branches.
Only17reviewed candidates changed;61other empty-socket patterns not automatically
reclassified (many are unsocketable items or explicit preparation labels).
Runtime base demand/conditions remain intact. _pattern_bindings excludes partial
reviews from complete bindings by default; dossiers preserve their demand and
partial_pattern_reviews separately. Completion records exact remaining branches;
collection discovery cannot borrow these incomplete links. Table/mirror
equivalence refuses partial endorsements. Repeated source-context reviews inherit
remaining branches so they cannot silently erase incomplete payload work.

Red regressions covered false complete binding, invalid partial metadata, repeated
source erasure and explicit null metadata.90focused tests pass;7runtime demand/
statbundle tests pass. Ruffcheck/format clean7files. All2585runtime profiles, all
statconfigs and demand summaries equal prior generation; only17use metadata
records changed.20saved replays match prior/staged/selected text,price,extraction.
Fulldependent/index rebuild and publication complete. Selected
45f1d9a2457179315bb92bf75c4a8e350019b5350a453205b2b1064c1a4d3c4d (80artifacts), prior51aedd retained.
Bank5361cases/4386targets/3536missing, unchanged. Namedgate548/35/2958 errors0;
planner114/0newissues, unsupportedMeteor remains. Completion
{"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2331, "excluded_occurrences": 4822, "coverage_rows": 8685, "remaining_tasks": 115120};false. Exactly17occurrence tasks reopened
with explicit payload reasons. This corrects overclaimed coverage; it does not
implement the missing finished-item assessments. Goalactive, final/fullsuite and
hostdelivery remain unverified.

Successful one-shot tmp/mark_preparation_source_branches.py MUST NOT rerun.
Handles98337/54267/41088/85907/41667/11773/87772/35601/37823/49084 allterminal.
The first completion37823 was valid before the final null-field guard;49084
regenerated scope after that policy change. No runtime artifact bytes changed from
that final guard. Logs tmp/partial-pattern-*. No livecollection/hostrestart/commit/staging.

Next executable targets: LightningStrike magic Crown filled alternatives, primary
slots/Helmets/12 threeTopaz72MF and /13 Ral/Ort/Thul30fire/lightning/cold. These
need separate filled rules and native item-bank cases; preserve existing empty
preparation rules and partial metadata. Closing a new complete binding may satisfy
the same source occurrence without pretending the empty rule covers filled items.
Then remaining diadem/JMoD finished payloads and fullglobalcompletion queue.
See PREPARATION_SOURCE_COVERAGE_AUDIT.json for17partial source IDs and78original
audit candidates.

## Lightning Strike completed magic Crowns published, 2026-09-28

Added topaz-crown-filled (threeTopaz72MF) and resist-crown-filled (Ral/Ort/Thul
30fire/lightning/cold) to LightningStrike, only magic Crown/noneth/identified/3s.
Actual linked payload and native effects required; no poison resistance inferred.
Native gems pinned, original empty preparation rules and partial source metadata
retained. Exact primary Helmets12/13 sources now fully bound through new filled
rules. Added two collection discovery records; no other dimensions promoted.

Red2missing native annotations ->initial32staged passed, but report inspection
found wrong payload reported conditional because checks were in depends_on. Added
red opposite-role status assertions, moved captured payload into must for these
two new rules, refreshed use/stat fingerprints, rebuilt. Final32staged and32selected
pass; each valid Crown makes other payload's role failed. Extra-modifier fixture
corrected from inappropriate CrownFRW to verified +20Life (native suffix ofWolf
entry329);2changed cases rerun staged andselected pass. No runtime change from
fixture correction. Fifteenfocused statbundle/source tests and2discovery tests
pass. Ruffcheck/format clean4files.20savedreplays equal staged/selected text,price,
extraction. Final examples tmp/ls-filled-crown-*-final-example.txt inspected.

Selected 459b8c239f6d63daf4dda898e4f73085a11b8a77ec3536dd3d296edf670e567a (80artifacts),
2587profiles/2579statconfigs; all prior2585profiles unchanged. Bank5393cases/4388
targets/3536missing. Namedgate548/35/2958 errors0; planner114/0newissues, unsupported
Meteor remains. Completion {"identities": 2570, "occurrences": 62891, "reviewed_occurrences": 2333, "excluded_occurrences": 4822, "coverage_rows": 8687, "remaining_tasks": 115126};false. Fifteen
explicit unfinished payload occurrence tasks remain from preparation audit.
No fullbank/fullrepo/finalgates/hostdelivery claim; goalactive.

Successful one-shots NEVER rerun: tmp/add_ls_filled_crowns.py, inline move-two-
payload-checks-to-must fixer, tmp/link_ls_filled_crown_collections.py. Initial
bank collection error was fixed (Item field rarity, not quality) before meaningful
red2. Initial discovery red2 then validated records. Logs tmp/ls-filled-crown-*.
All handles terminal53097/4332/52331/35342/52929/81732/43347/36882/52906/41278/54300/
90794/18286/49631/38995/33545/96597/14631/57544/15872/66994/40265/48985/9113/74510/
51568/54439/88446/64244/68382/27287. First lint run flagged an en dash in new test
comment; corrected and regenerated bank coverage + completion27287 after prior
completion68382 terminated. No livecollection/hostrestart/commit/staging.

Next important fit audit: CAPTURED_PAYLOAD_FIT_AUDIT.json inventories27other roles
with socket_gems_equal/socket_runes_equal inside depends_on. Actual wrong captured
contents can appear conditional instead of failed. Review mandatory completed
configurations versus legitimate optional/external setup requirements, with bank
role-status assertions in addition to stat-marker checks. Candidates include
Topaz armor/helm families, sixLem gold-find swords, Ist shields and socketed named
items. Do not blanket-move all dependencies. Then finish remaining15filled-source
branches (diadems/JMoD etc.) and all other global completion queues.

## Unconditional set effects repaired — 2026-10-01

Published0f605fe633e9aeda365f96e587498d13d11df8432ec74d0ecc0cbb5743b5f951
imports only addfunc0/absent extra properties as ordinary modifiers. Claws gains
fixed poison skill damage25; Civerb gains the fixed8/8 per-level max-damage
coefficient. Conditional set properties retain their previous semantics. No
trade premium or numerical price was added. Red/green native/compiler cases,
993 final selected item-bank cases,78 planner regressions, and20 saved replay
comparisons passed. Full-file provenance refresh preserved exact reviewed records.

Continue Claws fixed-armor trade proof: native67–74 defense, skilltab layer16,
fixed poison, original/upgrade boundaries and rendered qualification checks.
Current cache supports ordinary candidacy, not a perfect-defense premium (only
two independent perfect-defense sellers). See
pricing/data/appraisal-claws-trade-review-2026-10-01.md.
Civerb variable flat max-damage remains separate; all-item completion remains open.

## Claws original-base trade qualification reviewed — 2026-10-01

The authoritative matrix now marks Claws identity trade_qualification reviewed
(trade_reviews /rows/23). Its separate native proof validates fixed caster stats,
parameter-to-property-slot binding, unconditional poison bonus, original67–74
armor and native Vambraces exclusion. Legal test cases include the complete fixed
functional stat set; missing/wrong native evidence cannot certify the review.
72 maintenance regressions and1003 final selected item-bank cases passed.24 trade
reviews accepted. Runtime generation remains0f605fe633e9aeda365f96e587498d13d11df8432ec74d0ecc0cbb5743b5f951;
no tier/premium/price behavior changed. No perfect-defense premium established.

Next is Tal Rasha's Fine-Spun Cloth variable MF and original-base proof; source
findings and narrow scope requirements are in
pricing/data/appraisal-tal-belt-trade-review-2026-10-01.md. All-item work remains
unfinished; identity trade review does not close set/build fit or numerical price.

## Tal belt original-base trade qualification reviewed — 2026-10-01

New original_set_mf maintenance scope verifies the native variable MF interval,
fixed modifiers (including shifted mana), ordered partial set activation and
original/upgraded bases.46 native cases cover every MF roll10–15 in ordinary,
partial-defense and partial-defense-plus-FCR states, plus missing/invalid rolls
and identification/ethereal/socket/content boundaries.141 maintenance regressions
and1049 selected bank cases passed; all25 registered reviews accepted. The matrix
marks this identity's trade qualification reviewed at trade_reviews /rows/24.
Runtime generation remains0f605fe633e9aeda365f96e587498d13d11df8432ec74d0ecc0cbb5743b5f951.
No runtime policy or economic threshold changed:15MF ordinary candidate,
10–14unresolved; no upgraded, defense-premium, set/build-fit or price claim.

Next: explicit partial-evidence scalar/compound jewelry scopes for Mara and
Nagelring, preserving unresolved lower-roll segments. See
pricing/data/appraisal-partial-jewelry-trade-review-2026-10-01.md. Selected Mara
boundary probes already reject impossible resistances; no runtime boundary bug
was found. All-item completion remains open.

## Mara and Nagelring trade reviews accepted — 2026-10-01

Explicit partial-evidence scopes retain reviewed unknown lower-roll vectors only
when a current, source-pinned full-cache census supports evidence-unavailable.
Mara20–26 resistance has one priced independent seller; Nagel15–29MF has zero.
Changed snapshots, stale fingerprints, expanded bounds or three sellers prevent
closure. The existing full-disposition scopes still reject unknown legal branches.
No runtime threshold changed, and unknown does not mean use-only or worthless.

95 native cases cover legal ranges, independent/shared components, missing and
impossible values, variants and rendered trade colors.301 maintenance regressions
and1144 selected bank cases passed.27 registered reviews accepted; matrix trade
qualification rows25/26 now reviewed. Selected runtime generation remains
0f605fe633e9aeda365f96e587498d13d11df8432ec74d0ecc0cbb5743b5f951.
The scalar verifier now treats impossible native vectors as unresolved before
premium predicates, matching runtime behavior. The evidence census is preserved
in pricing/data/appraisal-partial-trade-regions-2026-10-01.json.

Next existing rules: ethereal Titan's Revenge, ethereal Sandstorm Trek, Opalvein
native property choices. Source findings are in
pricing/data/appraisal-remaining-qualified-items-review-2026-10-01.md. These are
not the remaining all-item denominator; the overall goal is unfinished.


2026-10-01 Opalvein choice census and bank repair: 16 stale lightning positives
reproduced red, corrected to unresolved under published fire/cold-only choice_keys.
90 native report cases pass with fixed proc/FCR included and invalid/mixed choice
boundaries. Full receipt1234pass384.26s;22policy and131maintenance regressions pass.
Strict full-cache census: fire4,cold3,lightning2,magic2,physical1,poison1 independent
sellers. Other choices remain thin, not worthless. No runtime policy/generation
change;27existing reviews accepted. Dedicated choice proof still pending. Matrix,
scope,completion regenerated: verified scope,complete=false,110686required tasks,
8322tradequalification gaps. Evidence: appraisal-opalvein-choice-audit-2026-10-01
.md/.json. No network/restart/staging/commit. Goal active; all handles terminal.


2026-10-01: Opalvein dedicated trade-choice review accepted. New native proof
validates all six mutually exclusive properties, native shared rolls, encoding,
fixed modifiers and every conflicting pair; independent seller census is recomputed
from the pinned full market snapshot. Fire/cold qualify, other choices remain thin
and unresolved. Changing evidence invalidates the review. 182 Opalvein native cases,
471 maintenance/policy regressions, and 1326 selected published report cases pass
(400.92s final bank). All28registered reviews accepted. Matrix/scope/completion
regenerated: scopeverified,complete=false,110685required tasks,8321trade gaps.
Runtime generation0f605 and trade thresholds unchanged. No network/restart/commit.
Next current-policy reviews: Titan and Trek, preserving audited variant/evidence
limits. Wider all-item goal stays active; no live processes or blocker streak.


2026-10-01: Sandstorm Trek native trade review accepted. Four material axes,
native repair/stamina and ethereal variant checks preserve the 15/15 attribute
segment without claiming a universal price ranking. Full source-bound census
keeps nonethereal evidence unknown (0 explicit sellers); omitted flags stay
unknown. New sufficient evidence or stale source invalidates the review.
54 distinct Trek cases; 505 selected maintenance/policy tests pass. Shared
report receipt: 1380 passed, 28870 deselected in 416.65s. All 29 registered reviews
accepted; scope verified and completion remains false: 110684 required tasks,
8320 trade qualifications. Registry Trek row28. Runtime generation0f605 unchanged;
no network, restart, staging or commit. All handles terminal. Next current-policy
review: Titan's Revenge, retaining original/upgraded cutoff caveats. The wider
all-item goal remains active, with no blocker streak.


2026-10-01: Titan runtime correction published in cab95c4ef40bdfe2d30f90aeeb942beb0896b3e56b08fc1193d6184080846f94.
Original ethereal190%+ segment retained; upgraded ethereal requires200% ED. Both
high-tier overrides and explicit trade qualification now use separate base guards
and paired ED. Upgraded190–199 remains mid/unresolved, not worthless. Independent
cohorts preserved (original8asks/4sellers; upgraded6/4). Only named_tiers.json
changed among103published artifacts; index and other artifacts unchanged.
Red/green cutoff and tier tests;56staged Titan cases pass,574maintenance/policy
tests pass,1436selected published cases pass487.58s. All20saved decoded outputs,
text and prices match old/staged/selected. All29existing reviews accepted; matrix,
scope,completion rebuilt for cab95: scopeverified,complete=false,110684required
tasks and8320trade gaps. Titan native maintenance proof remains pending and must
use a verified upgraded base code (scalar _outcome assumes original definition).
No network/restart/staging/commit. All handles terminal; goal remains active.
