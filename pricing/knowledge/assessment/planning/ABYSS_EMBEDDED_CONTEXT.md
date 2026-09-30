# Abyss embedded guide context review

2026-09-28. Status: pending semantic review. Exact HTML context is verified; this does not establish item assessment or pricing completion.

Source: `pricing/raw/mr/guides__abyss-warlock-build-guide.html` (`95020de34fa8cbe5cbced07aae716b0696af9df15b8e280cfe8b4ff853caea3b`).
The existing `embedded_item_refs` retain item/set IDs omitted from legacy `item_spans`.

| Span | Item | Visible label | Guide slot | Planner set |
|---|---|---|---|---|
| 8 | 1 | Void | Weapon | dGH5vCiB |
| 20 | 120 | Rare Kris | Weapon | dGH5vCiB |
| 21 | 226 | Arch-Devil's Kris of Lower Resistance | Weapon | dGH5vCiB |
| 22 | 129 | (blank) | Off-Hand | dGH5vCiB |
| 26 | 139 | (blank) | Off-Hand | dm4EcrJ5 |
| 37 | 143 | (blank) | Helmets | dm4EcrJ5 |
| 38 | 144 | (blank) | Helmets | dm4EcrJ5 |
| 39 | 140 | (blank) | Helmets | dm4EcrJ5 |
| 40 | 141 | (blank) | Helmets | dm4EcrJ5 |
| 41 | 142 | (blank) | Helmets | dm4EcrJ5 |
| 45 | 145 | (blank) | Body Armors | dm4EcrJ5 |
| 51 | 146 | (blank) | Body Armors | dm4EcrJ5 |
| 55 | 147 | (blank) | Gloves | dm4EcrJ5 |
| 57 | 92 | Caster Crafted Bramble Mitts | Gloves | dGH5vCiB |
| 61 | 152 | (blank) | Belts | dm4EcrJ5 |
| 62 | 148 | (blank) | Belts | dm4EcrJ5 |
| 63 | 154 | (blank) | Boots | dm4EcrJ5 |
| 64 | 153 | (blank) | Boots | dm4EcrJ5 |
| 71 | 84 | Caster Crafted Amulet | Amulets | wNE5FX6D |
| 73 | 157 | (blank) | Amulets | dm4EcrJ5 |
| 74 | 158 | (blank) | Amulets | dm4EcrJ5 |
| 75 | 11 | (blank) | Amulets | dm4EcrJ5 |
| 76 | 156 | (blank) | Amulets | dm4EcrJ5 |
| 79 | 160 | (blank) | Rings | dm4EcrJ5 |
| 80 | 161 | (blank) | Rings | dm4EcrJ5 |
| 83 | 159 | (blank) | Rings | dm4EcrJ5 |
| 87 | 137 | (blank) | Unique Charms | dGH5vCiB |

Next: validate named identities and affix/socket payloads against the cached planner, bind reviewed role fingerprints, and add validated embedded-use dispositions to the completion compiler. Do not treat inventory membership or raw `review_state` flags as semantic review. Preserve definition-only guide references.
