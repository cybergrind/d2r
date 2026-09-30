# Required correction: Berserk Teleport amulet after Enigma

Observed 2026-09-29 while independently reviewing the last Berserk bank targets.
Status: corrected and published offline on 2026-09-29; live worker adoption unverified.
Generation: e7b4f1f1e6ede564a9ba500593241a07fa420b88dc234fb3b87a4c4b27f4fbab.
Four new cases reproduced the bug; 91 affected cases pass staged and published.
All 20 saved replays match, and 90 artifact hashes plus the index hash verify.

Source `pricing/data/wp-a-builds.json`, `/berserk-barbarian/prose_only_items/8`:
“Naj's Puzzler / Staff of Teleportation / Teleport Charge Amulet only until Enigma
(Gear Notes)”. The role `berserk-barbarian-teleport-staf` has a dependency requiring
Enigma not to be in `player_items`. Its sibling `berserk-barbarian-teleport-amul`
has the same prose condition but only checks available charges in `depends_on`.

The new bank cases verify charge availability but do not prove this absent amulet
condition. Do not count their green receipt as closure of the source use.

Executed correction plan:

1. Add independent amulet cases with Enigma equipped, confirmed absent and unknown
   player equipment. Assert available-charge priority is withheld when this
   source-specific pre-Enigma dependency is unmet or unknown.
2. Fix the source role in `rules/roles/berserk-barbarian.json`; inspect other roles
   citing this same prose condition for equivalent gaps before changing them.
3. Update semantic review fingerprints only after reviewing affected behavior;
   rebuild, run focused regression, publish and verify the selected reports.
4. Preserve the separate equipment-table charge alternatives: their source scope
   may differ. Do not remove a general item's other uses or infer worthlessness.

The all-item completion contract remains unmet until this and all other required
work is closed. This document is evidence of an open task, not a scope exclusion.
