# Mercenary HP: external reader comparison

Researched 2026-09-21. Source inspection only: no game input, runtime changes or
new live samples. The accepted implementation remains unchanged.

## Finding

Our normalized life calculation matches the d2go family. No inspected D2R reader
established a continuously exact mercenary inventory-panel HP source. Legacy D2
code exposes separate health-update paths, including throttled monster updates,
an owner-facing percentage, and explicit merc stat delivery. These are stronger
research leads than adjusting the divisor or rounding our estimate.

## Compared implementations

| Project/source snapshot | Method | Relevance |
| --- | --- | --- |
| [d2go](https://github.com/relentlessricktrinidad/d2go/blob/1fb1e7a6569fef21e6e3a63749244f65a80673a0/pkg/data/data.go#L101-L115), 2025-08-17 | `MercHPPercent`: raw life <=32768 is scaled by max HP /32768; larger life is shifted by 8 as ordinary HP. Returns integer percent. | Same normalized branch as ours; magnitude-based fallback is a heuristic, not proof of encoding. |
| [D2R-AutoPotion-Go](https://github.com/Apethor/D2R-AutoPotion-Go/blob/e1d1e6e424db16b3d426b45ed34e872c4926e065/pkg/data/data.go#L82-L97), 2023-10-26 | Same dual-interpretation calculation. | Related code lineage, not independent corroboration. |
| [Koolo](https://github.com/dulingzhi/koolo/blob/91a04550a54684a2ff315919f1990651a97bb42e/internal/health/health_manager.go#L86-L108), 2023-11-27 | Calls d2go `MercHPPercent` for potion/chicken decisions. | Does not solve exact HP separately. |
| [MapAssist](https://github.com/dglEnraged/MapAssist/blob/c503b29d014d0bdb0a8a14667fec2375ffcc2e3a/Types/UnitMonster.cs#L80-L91), 2022-06-08 | Generic monster health ratio is life/max-life. | No merc-specific normalization in this accessor; cannot transplant into our mixed normalized-life/absolute-max samples. |
| [d2r-mapview](https://github.com/joffreybesos/d2r-mapview/blob/50131a7651833a468774374b7c7b07c4ff08b7f8/src/memory/readMobs.ahk#L80-L107), 2022-11-04 | Generic monster current/max stats shifted by 8; comments note unboosted max. | No exact merc HP solution in this reader. |
| [Botty](https://github.com/johannes-do/botty/blob/22ab86b3877e441a61cfb46f43bf5b368d8251cf/src/ui/meters.py#L22-L28), 2022-07-01 | Crops one horizontal row of the merc health bar, thresholds grayscale pixels, measures filled fraction. | Independent visual percentage; could cross-check memory, not exact HP. |
| [D2BS](https://github.com/noah-/d2bs/blob/f4b99bbe8de6916384991dfdd198ecf234cef1c0/JSUnit.cpp#L1689-L1706), 2021-04-05 | Calls client `GetUnitHPPercent(merc unit ID)`. | Legacy D2, not D2R. Suggests tracing the client percentage lookup's data source; old function address is unusable here. |

The Cartographer/Wanderer repository advertises a merc HP display but its checked
snapshot (`390698dc775f28688d70164006615da4583ff294`, 2026-09-10) contains README/images,
not inspectable implementation. It supplies no algorithm evidence. Original
hectorgimenez/d2go and koolo URLs were inaccessible during cloning; public forks
above were inspected instead. Snapshot dates are commit dates, not compatibility claims.

One additional difference: [d2go's monster reader](https://github.com/relentlessricktrinidad/d2go/blob/1fb1e7a6569fef21e6e3a63749244f65a80673a0/pkg/memory/monsters.go#L37-L40)
reads the base-stat descriptor at +0x30. Our merc selection reads full stats at
+0xe8; research probes retain both. Compare them on the same owned unit before
assuming their life/max pairs have identical meaning. Do not switch blindly:
effective max HP is the quantity we matched in the current build.

## Legacy engine evidence and its limits

[D2MOO MonsterMode.cpp](https://github.com/ThePhrozenKeep/D2MOO/blob/5596f5cb6c5251a0a07c6637d26458b06099d516/source/D2Game/src/MONSTER/MonsterMode.cpp#L400-L414)
reconstructs monster health as `floor(128 * integer_current_HP / integer_max_HP)`,
with 128 for full life. This supports a 128-step interpretation of our observed
raw values when multiplied by 256; it is not a verified D2R client write path.

The [regeneration update](https://github.com/ThePhrozenKeep/D2MOO/blob/5596f5cb6c5251a0a07c6637d26458b06099d516/source/D2Game/src/MONSTER/MonsterMode.cpp#L574-L629)
compares the new step with the last sent step, sending through a queued 0xAB
message only when the absolute difference exceeds four. In this path, reaching
full does not itself force an update. Other animation/damage/update paths also
exist, so this is not a global update rule. It makes a lingering near-full value
plausible, without proving the cause in RotW.

A [separate owner-facing update](https://github.com/ThePhrozenKeep/D2MOO/blob/5596f5cb6c5251a0a07c6637d26458b06099d516/source/D2Game/src/GAME/SCmd.cpp#L1222-L1323)
uses packet 0x7F and whole percent, with its own change/count suppression. D2BS's
client percentage function may expose such a cache, but that connection was not
traced. Neither source proves it is the merc inventory's exact HP source.

[MONSTERAI_SendMercStats](https://github.com/ThePhrozenKeep/D2MOO/blob/5596f5cb6c5251a0a07c6637d26458b06099d516/source/D2Game/src/MONSTER/MonsterAI.cpp#L157-L179)
also sends actual current HP and base max HP through the merc stat delivery path.
This is another candidate for why panel and monster estimates differ. Its D2R
recipient, storage location and refresh semantics remain unverified. Do not assume
these legacy packet identifiers, layouts or functions transfer to the installed build.

## Relation to our discrepancy

Calculated from the recorded max of 2090 HP:

- One 128th step is 16.328125 HP (0.78125 percentage points).
- Recorded raw 32256 = 126 * 256; our estimate is floor(2090 * 126/128) = 2057 HP.
- Reaching full from step 126 changes only two steps, below the legacy regen
  send threshold. That is consistent with the reported lingering ~2057 value,
  but requires a D2R trace or controlled evidence to establish causation.
- Inventory 2048 versus OSD 1943 differs by 105 HP, substantially more than one
  rounding step. Quantization alone does not explain that pair, and the legacy
  four-step suppression rule alone does not establish an explanation either.

## Best next investigation if pursuing exact HP

Trace the supported build's merc panel/portrait health readers and their backing
storage, using the legacy client percentage and explicit merc-stat paths as leads.
Record synchronized panel HP, portrait percentage, and base/full life/max stats
for the same owner/unit while damaged, regenerating, and after panel reopen.
This distinguishes different caches, stale panel data and stat-list interpretation.
Faster polling cannot refresh a value the game has not updated. Keep the current
normalized policy and approximate display until another source is validated;
none of this inspection justifies a production offset or formula change.
