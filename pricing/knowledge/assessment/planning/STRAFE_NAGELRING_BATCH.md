# Strafe MF ring companion — 2026-09-25

Second demand batch after Assassin leveling tail. This completes the reviewed
Strafe prose Nagelring substitution, not every Strafe setup or named-item tier.
Estimated review effort: ten minutes including equipment/socket boundary tests.

Membership: strafe-mf-stealskull-nagelring, player Amazon unique identified
nonethereal Nagelring; wp-a-builds.json /strafe-amazon/variants/2. Source hash
8a9da0d8cdd38e74d5b03721f5cf9de78e63c17ce87170cb706a6acfa31d59a2;
original date and quoted prose retained in the role.

The guide's prose permits replacing the rare ring because Stealskull supplies dual
leech, and requires a helmet IAS jewel to maintain breakpoints. Native uniqueitems
record203 confirms5life/5mana leech and10IAS; magicsuffix of Fervor provides fixed15IAS
on jewels. Require an actual identified unique Stealskull helmet with a linked15IAS
jewel. Aggregate helmet IAS, an inventory name, a different slot, mercenary gear or
the conflicting Harlequin Crest planner cannot satisfy this dependency. Upgraded
and ethereal equip/durability considerations stay qualified; no premium inferred.

Remaining complete attack-speed, glove, sustain and defensive requirements remain
conditional. Prose recommends Chance Guards and low-player-count farming without
Demons; planner glove/helmet differences are explicitly not treated as equivalent.
Only observed MF receives farming desirability;15useful/30optional target. Source
prose supports guide demand, not a numerical price. Demand is now5builds/6uses,
Pending with High lower bound; two Berserk variants still count once.

The existing equipped_item_matches predicate now accepts the item-local
socket_jewel_stat_at_least operator. Context recursion remains prohibited. Socket
occupancy/unknown semantics and native key traversal reuse the existing evaluator.
Snapshot validation rejects malformed child stats as unknown instead of crashing.
A Python worker restart is required for these runtime changes.

Red: unsupported equipped socket predicate, missing Strafe rule, malformed child
stats crash. Positive, empty/unknown, contradictory occupancy, aggregate-only,
wrong-slot/beneficiary, JSON snapshot and immutable context-copy checks added.
Validation results/publication recorded in STATUS.md; evidence tmp/strafe-nagelring-*
and tmp/equipment-sockets-*. No live market collection or item probes.

Next is a scheduled specialist/leveling/unresolved tail. Universal named tiers,
base desirability, affixed configurations, source closure and exact scoped prices
remain unfinished. Stealskull's own role/market evaluation remains independent of
this companion identity check.
