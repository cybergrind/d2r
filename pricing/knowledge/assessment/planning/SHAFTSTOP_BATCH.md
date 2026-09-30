# Shaftstop physical-survival family — 2026-09-26

First demand batch after Hammerdin MF reconciliation. Reused cached WP-A variants
and native armor/item definitions; no extraction, network collection or captures.
Review effort estimate: fifteen minutes. Five reviewed configurations, three builds.

| Build | Variant | Mercenary | Reviewed base | Ethereal |
|---|---|---|---|---|
| Dream Paladin | Hybrid, index 1 | Act 1 Cold | Mesh Armor | Yes |
| Dream Paladin | Ubers, index 2 | Act 1 Cold | Mesh Armor / Boneweave | Yes |
| Lightning Strike Amazon | Standard, index 1 | Act 1 Cold | Mesh Armor / Boneweave | Yes |
| Strafe Amazon | Standard, index 1 | Act 2 Might | Mesh Armor | Known yes/no |
| Strafe Amazon | Magic Find, index 2 | Act 2 Might | Mesh Armor | Known yes/no |

Native uniqueitems record 215 supplies 30% physical damage reduction, 60 life,
250 defense against missiles and 180–220% enhanced defense. The reviewed survival
priorities are physical reduction (desirable) and life (supporting). Existing roll
ranges remain separate; 220% enhanced defense is not an acceptance gate. Helmet
life leech and socket-jewel IAS are not intrinsic armor effects. The guide's 50%
combined reduction is not attributed to Shaftstop alone or assumed for any helmet.

Native armor mapping verifies Mesh Armor upgrades to Boneweave, not Shadow Plate.
The initial candidate's incorrect Shadow Plate mapping failed the native-table
assertion before rules were written. Corrected it and added a rejecting regression.
Explicit Mesh citations retain original-base scope; generic Shaftstop citations
accept the verified upgrade chain subject to requirements, without claiming upgrades
are always better. Unsupported upgrades remain a review gap, not a negative price.

Dream and Lightning Strike retain Faith/Vampire Gaze and IAS/resistance jewel setup
qualifications. Strafe is an endorsed survival alternative to Chains of Honor when
Pride's low physical damage makes leech unreliable. Its unspecified ethereal status
is not inherited from the primary CoH item. The MF configuration retains the same
mercenary gear in WP-A and pins Standard's explicit survival advice as corroboration.
Both Strafe variants retain alternative strength; no duplicate breadth vote.

Double Throw's CoH planner versus Shaftstop prose is still unresolved; no reviewed
vote added from that conflict. Hardcore-only references and broad gear-table leads
remain outside this batch. Guide demand is Pending, lower bound Med, three builds.

Red: six missing-role/demand tests. After correcting the native upgrade mapping,
22 family/stat/source/demand/publication tests passed in 6.82 seconds. Lint/format
passed. Tests cover wrong qualities/identity/bases/ethereal/context, both supported
Strafe ethereal states, actual native stats versus added leech/IAS, and empty stats.
Saved replay, publication and coverage checkpoint: STATUS.md.

564 roles / 556 stat configurations. No market observations or price policies changed.
Data-only update; no additional worker restart. Evidence: tmp/shaftstop-*.
Next: one more demand/family batch, then scheduled specialist/leveling/unresolved
work. Full named tiers, bases, affixed patterns, leveling and exact prices remain
unfinished. Guide review completion is not market coverage.
