# Staffmod shopping review — 2026-09-27

## Decision

A staffmod-driven shop alert now requires **+2 matching class +3 primary skill**
or **+3 matching skill tree +3 primary skill**. The tree must contain that skill.
Two unrelated +3 skills do not add up to +6 to either skill. A +2 tree prefix is
below the requested shop threshold even though it could give +5 total.

The screenshot's Master's Stiletto of Worth (native base spelled `Stilleto`)
has +3 Barbarian Combat, +1 Abyss, +3 Apocalypse, +3 Eldritch Blast and +1 minimum
damage. It is rejected: the Barbarian prefix improves neither Warlock skill.
It previously passed an unconditional `len(native) >= 2` rule. This is a matching
policy bug, not a stat-decoding bug. The regression fixture transcribes the image;
it does not claim to replay original process memory.

Plain +3 tree amulets remain the separately requested self-use exception. The
previously requested +3 Traps / 30+ IAS claws, +3 tree / 20 IAS gloves and javelin
IAS targets remain independent combinations. This review does not demand a
staffmod on those items or change ordinary armor/circlet patterns.

## What counts as useful

`staffmods.py` records explicit primary/companion groups. Primary means a
conservative shopping candidate for damage, summons or deliberate buffing, not
proven trade value or a replacement for a finished unique/runeword. FCR, sockets,
base speed, other rolls and the complete loadout still decide that.

- Fire Sorceress: Fire Ball/Meteor/Hydra, or Enchant; Fire Mastery is an extra.
- Lightning Sorceress: Lightning/Chain Lightning/Nova; Lightning Mastery extra.
- Cold Sorceress: Blizzard/Frozen Orb; Cold Mastery extra. Energy Shield is a
  separate buffing target, not ordinary damage gear.
- Necromancer: Poison Nova, Bone Spear/Bone Spirit, or Raise Skeleton. Skeleton
  Mastery improves the summoning package. Corpse Explosion/curse utility alone
  does not qualify under this deliberately strict shopping policy.
- Paladin: Blessed Hammer or Fist of the Heavens. Concentration/Conviction can be
  companions, but the Combat prefix cannot add levels to an aura from another tree.
- Barbarian: Battle Orders, War Cry, Find Item; other combat skills/masteries alone
  are not sufficient evidence for shopping a helm.
- Druid: Fissure/Volcano/Armageddon, Tornado/Hurricane, Raven/Grizzly. Extra pets or
  spirits are companions. No blanket shapeshifting +skill shopping rule.
- Assassin: Lightning Sentry, Wake of Fire, Fire Blast. Fade/Venom are deliberate
  buffing candidates. Weapon Block/Death Sentry are useful additions, not automatic
  stand-alone shopping triggers. No blanket martial-arts skill rule on magic claws.
- Warlock: Hex: Purge/Eldritch Blast/Echoing Strike/Mirrored Blades in Eldritch;
  Abyss/Miasma Chain and Apocalypse/Flame Wave/Ring of Fire in Chaos. Consume,
  Bind Demon, masteries and utility hexes alone do not trigger. Each qualifying
  skill gets only its own class/tree bonus, even if other trees occur on the item.
- Amazon: no single-skill staffmod rule added; existing native tree/IAS equipment
  patterns remain the shopping path.

Do not equate hard-point investment with an item target. Normal hard-point synergy
bonuses do not increase merely by putting +skills on an item; direct mastery and
other special mechanics must be assessed separately. No claim is made that every
skill omitted here is useless in play or has no possible specialized buyer.

## Evidence and limits

Reviewed the 26 local `pricing/data/wp-a-variants/*.json` build records, researched
2026-09-18–20, plus `guides/warlock.html`. Strong explicit magic-item examples:

| Local variant record | Direct equipment evidence |
| --- | --- |
| enchant-sorceress | +3 Fire / +3 Enchant / +3 Fire Mastery orb with 20 FCR |
| fissure-druid | +3 Elemental / +3 Fissure pelt; other staffmods are additions |
| lightning-sentry-assassin | +3 Traps / +3 Lightning Sentry / IAS claws; Death Sentry and Weapon Block extras |
| wake-of-fire-assassin | +3 Traps / +3 Wake of Fire / IAS claws; Fire Blast and Weapon Block extras |
| fire-blast-assassin | +3 Traps / +3 Fire Blast inventory claws |

Other groups are conservative role/mechanics inferences, not claimed explicit
magic-item BiS entries. White/Memory/Void/Plague and Rhyme base staffmod mentions
are not evidence that an affixed blue base can make that runeword. For example,
the Echoing Strike guide uses Void and the guide rotation names Hex: Purge and
Eldritch Blast; preserving corresponding blue +5/+6 candidates is an inference
and the user's stated requirement, not proof they outperform Void.

Native class/tree IDs resolve through `skills.json`, itself based on pinned
`third-parties/d2data/json/skills.json` and `skilldesc.json`.
General synergy reference: https://classic.battle.net/diablo2exp/skills/basics.shtml.
Current external searches are not used as price evidence. No online market refresh.

## Complete existing catalog disposition

The broad catalog remains intact for offline consumers. Runtime staffmod alerts
use the narrower review, so adding a utility skill to the catalog cannot silently
make it a new standalone shopping target. `Companion` requires a qualifying primary
in its recorded group. `Not a trigger` means outside this shop policy, not worthless.

| Class | Skill | Shopping role |
| --- | --- | --- |
| Amazon | Multiple Shot | Not a trigger |
| Amazon | Power Strike | Not a trigger |
| Amazon | Exploding Arrow | Not a trigger |
| Amazon | Charged Strike | Not a trigger |
| Amazon | Plague Javelin | Not a trigger |
| Amazon | Strafe | Not a trigger |
| Amazon | Immolation Arrow | Not a trigger |
| Amazon | Freezing Arrow | Not a trigger |
| Amazon | Valkyrie | Not a trigger |
| Amazon | Lightning Strike | Not a trigger |
| Amazon | Lightning Fury | Not a trigger |
| Sorceress | Warmth | Not a trigger |
| Sorceress | Frozen Armor | Not a trigger |
| Sorceress | Static Field | Not a trigger |
| Sorceress | Telekinesis | Not a trigger |
| Sorceress | Ice Blast | Not a trigger |
| Sorceress | Fire Ball | Primary (+5/+6 required) |
| Sorceress | Nova | Primary (+5/+6 required) |
| Sorceress | Lightning | Primary (+5/+6 required) |
| Sorceress | Shiver Armor | Not a trigger |
| Sorceress | Fire Wall | Not a trigger |
| Sorceress | Enchant | Primary (+5/+6 required) |
| Sorceress | Chain Lightning | Primary (+5/+6 required) |
| Sorceress | Teleport | Not a trigger |
| Sorceress | Glacial Spike | Not a trigger |
| Sorceress | Meteor | Primary (+5/+6 required) |
| Sorceress | Thunder Storm | Not a trigger |
| Sorceress | Energy Shield | Primary (+5/+6 required) |
| Sorceress | Blizzard | Primary (+5/+6 required) |
| Sorceress | Chilling Armor | Not a trigger |
| Sorceress | Fire Mastery | Companion only |
| Sorceress | Hydra | Primary (+5/+6 required) |
| Sorceress | Lightning Mastery | Companion only |
| Sorceress | Frozen Orb | Primary (+5/+6 required) |
| Sorceress | Cold Mastery | Companion only |
| Necromancer | Skeleton Mastery | Companion only |
| Necromancer | Raise Skeleton | Primary (+5/+6 required) |
| Necromancer | Corpse Explosion | Companion only |
| Necromancer | Golem Mastery | Not a trigger |
| Necromancer | Raise Skeletal Mage | Companion only |
| Necromancer | Life Tap | Not a trigger |
| Necromancer | Poison Explosion | Not a trigger |
| Necromancer | Bone Spear | Primary (+5/+6 required) |
| Necromancer | Decrepify | Not a trigger |
| Necromancer | Lower Resist | Companion only |
| Necromancer | Poison Nova | Primary (+5/+6 required) |
| Necromancer | Bone Spirit | Primary (+5/+6 required) |
| Necromancer | Revive | Companion only |
| Paladin | Smite | Not a trigger |
| Paladin | Holy Bolt | Companion only |
| Paladin | Holy Fire | Not a trigger |
| Paladin | Zeal | Not a trigger |
| Paladin | Blessed Aim | Not a trigger |
| Paladin | Blessed Hammer | Primary (+5/+6 required) |
| Paladin | Concentration | Companion only |
| Paladin | Holy Shield | Not a trigger |
| Paladin | Holy Shock | Not a trigger |
| Paladin | Fist of the Heavens | Primary (+5/+6 required) |
| Paladin | Fanaticism | Not a trigger |
| Paladin | Conviction | Companion only |
| Paladin | Redemption | Not a trigger |
| Barbarian | Blade Mastery | Not a trigger |
| Barbarian | Axe Mastery | Not a trigger |
| Barbarian | Mace Mastery | Not a trigger |
| Barbarian | Howl | Not a trigger |
| Barbarian | Find Potion | Not a trigger |
| Barbarian | Double Swing | Not a trigger |
| Barbarian | Polearm Mastery | Not a trigger |
| Barbarian | Throwing Mastery | Not a trigger |
| Barbarian | Spear Mastery | Not a trigger |
| Barbarian | Shout | Companion only |
| Barbarian | Double Throw | Not a trigger |
| Barbarian | Find Item | Primary (+5/+6 required) |
| Barbarian | Leap Attack | Not a trigger |
| Barbarian | Concentrate | Not a trigger |
| Barbarian | Battle Cry | Not a trigger |
| Barbarian | Frenzy | Not a trigger |
| Barbarian | Battle Orders | Primary (+5/+6 required) |
| Barbarian | Whirlwind | Not a trigger |
| Barbarian | Berserk | Not a trigger |
| Barbarian | War Cry | Primary (+5/+6 required) |
| Barbarian | Battle Command | Companion only |
| Druid | Raven | Primary (+5/+6 required) |
| Druid | Poison Creeper | Not a trigger |
| Druid | Werewolf | Not a trigger |
| Druid | Lycanthropy | Not a trigger |
| Druid | Oak Sage | Companion only |
| Druid | Summon Spirit Wolf | Companion only |
| Druid | Werebear | Not a trigger |
| Druid | Maul | Not a trigger |
| Druid | Fissure | Primary (+5/+6 required) |
| Druid | Heart of Wolverine | Companion only |
| Druid | Summon Dire Wolf | Companion only |
| Druid | Rabies | Not a trigger |
| Druid | Fire Claws | Not a trigger |
| Druid | Volcano | Primary (+5/+6 required) |
| Druid | Tornado | Primary (+5/+6 required) |
| Druid | Summon Grizzly | Primary (+5/+6 required) |
| Druid | Fury | Not a trigger |
| Druid | Armageddon | Primary (+5/+6 required) |
| Druid | Hurricane | Primary (+5/+6 required) |
| Assassin | Fire Blast | Primary (+5/+6 required) |
| Assassin | Claw Mastery | Not a trigger |
| Assassin | Tiger Strike | Not a trigger |
| Assassin | Dragon Talon | Not a trigger |
| Assassin | Burst of Speed | Companion only |
| Assassin | Fists of Fire | Not a trigger |
| Assassin | Wake of Fire | Primary (+5/+6 required) |
| Assassin | Weapon Block | Companion only |
| Assassin | Cloak of Shadows | Not a trigger |
| Assassin | Cobra Strike | Not a trigger |
| Assassin | Blade Fury | Not a trigger |
| Assassin | Fade | Primary (+5/+6 required) |
| Assassin | Claws of Thunder | Not a trigger |
| Assassin | Dragon Tail | Not a trigger |
| Assassin | Lightning Sentry | Primary (+5/+6 required) |
| Assassin | Wake of Inferno | Not a trigger |
| Assassin | Mind Blast | Not a trigger |
| Assassin | Blades of Ice | Not a trigger |
| Assassin | Dragon Flight | Not a trigger |
| Assassin | Death Sentry | Companion only |
| Assassin | Blade Shield | Not a trigger |
| Assassin | Venom | Primary (+5/+6 required) |
| Assassin | Shadow Master | Not a trigger |
| Assassin | Phoenix Strike | Not a trigger |
| Warlock | Summon Goatman | Not a trigger |
| Warlock | Demonic Mastery | Companion only |
| Warlock | Death Mark | Not a trigger |
| Warlock | Summon Tainted | Not a trigger |
| Warlock | Summon Defiler | Not a trigger |
| Warlock | Blood Oath | Not a trigger |
| Warlock | Engorge | Not a trigger |
| Warlock | Blood Boil | Not a trigger |
| Warlock | Consume | Companion only |
| Warlock | Bind Demon | Companion only |
| Warlock | Levitation Mastery | Companion only |
| Warlock | Eldritch Blast | Primary (+5/+6 required) |
| Warlock | Hex: Bane | Companion only |
| Warlock | Hex: Siphon | Not a trigger |
| Warlock | Psychic Ward | Not a trigger |
| Warlock | Echoing Strike | Primary (+5/+6 required) |
| Warlock | Hex: Purge | Primary (+5/+6 required) |
| Warlock | Blade Warp | Not a trigger |
| Warlock | Cleave | Not a trigger |
| Warlock | Mirrored Blades | Primary (+5/+6 required) |
| Warlock | Sigil: Lethargy | Not a trigger |
| Warlock | Ring of Fire | Primary (+5/+6 required) |
| Warlock | Miasma Bolt | Not a trigger |
| Warlock | Sigil: Rancor | Not a trigger |
| Warlock | Enhanced Entropy | Companion only |
| Warlock | Flame Wave | Primary (+5/+6 required) |
| Warlock | Miasma Chain | Primary (+5/+6 required) |
| Warlock | Sigil: Death | Companion only |
| Warlock | Apocalypse | Primary (+5/+6 required) |
| Warlock | Abyss | Primary (+5/+6 required) |
