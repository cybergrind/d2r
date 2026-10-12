# Threat scenes in the arena

Each of the 16 scenes of `scenarios/threat/scenes.py` converted by `scenes_threat.py` and played by the
production macro (ATTACK pressed at 0.0 s, seed 1) to the scene's horizon. The threat harness column
is `threat.harness.run(spec.scene(), today, spec.horizon)`, which never moves and only casts.
The threat harness counts damage on past the death; the arena stops at it, so a dead arena play
shows at most the character's life. A Herald's tier is not carried (only its life, in `full`); a
boost is carried as an aura by unit. Rates are probed: one such monster alone, 20 s.

```
scene                              alive  dead@  clear@  taken  kills  casts  moved  pots  charges  swaps
---------------------------------  -----  -----  ------  -----  -----  -----  -----  ----  -------  -----
gloams_behind_hulks                yes        -     5.2      0      7     14      0     0        0      0
witch_and_soul_beside_tanky_elite  yes        -     5.4      0      3     12      0     0        0      0
dying_gloam_fresh_hulk             yes        -     2.6      0      2      7      0     0        0      0
equal_lines_far_and_in_contact     yes        -     3.4      0      4      9      0     0        0      0
stone_skin_elite_soaks             yes        -       -      0      3     12      0     0        0      0
ghosts_in_front_of_archers         yes        -       -    116      3     16      0     0        0      0
bovines_closing_from_two_sides     yes        -     3.4      0      6      9      0     0        0      0
low_life_in_melee                  yes        -     2.2      0      3      6      0     0        0      0
low_life_two_dying_gloams          yes        -     1.6      0      2      4      0     0        0      0
low_life_under_knights             yes        -     5.9      0      4     17      0     0        0      0
dolls_running_in                   yes        -     3.3    900      8      8      0     0        0      0
dolls_on_the_character             DEAD     1.2     1.1    900      3      3      0     0        0      0
might_elite_beside_minions         yes        -     3.7      0      5      8      0     0        0      0
herald_with_minions                yes        -       -      0      1     27      0     0        0      0
stone_skin_zone                    yes        -       -    637      0     20      0     0        0      0
venom_lords_and_casters            yes        -     5.1      0      6     14      0     0        0      0
total (16)                         15/16      -       -   2553     60    186      0     0        0      0
```

## gloams_behind_hulks

Threat harness: alive, 1098 taken, 7/7 killed, 6 casts. Arena: alive, 0 taken, 7/7 killed, 14 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 5.2 s. Direction: agree.

Conversion mismatches: Bramble Hulk (unit 0): 171 points a second in the threat scene, 19 in the arena; Bramble Hulk (unit 1): 171 points a second in the threat scene, 19 in the arena; Bramble Hulk (unit 2): 171 points a second in the threat scene, 19 in the arena; Bramble Hulk (unit 3): 171 points a second in the threat scene, 19 in the arena; Gloam (unit 10): 254 points a second in the threat scene, 0 in the arena; Gloam (unit 11): 254 points a second in the threat scene, 0 in the arena; Gloam (unit 12): 254 points a second in the threat scene, 0 in the arena; monster level 80 (area 77) in the arena; the threat scene is built at 95.

## witch_and_soul_beside_tanky_elite

Threat harness: alive, 1420 taken, 3/3 killed, 8 casts. Arena: alive, 0 taken, 3/3 killed, 12 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 5.4 s. Direction: agree.

Conversion mismatches: Death Lord (unit 1, elite): 225 points a second in the threat scene, 27 in the arena; Hell Witch (unit 2): 96 points a second in the threat scene, 0 in the arena; Burning Soul (unit 3): 254 points a second in the threat scene, 0 in the arena; boost carried as an aura (unit 2 x1.5); monster level 85 (area 131) in the arena; the threat scene is built at 95.

## dying_gloam_fresh_hulk

Threat harness: alive, 274 taken, 2/2 killed, 4 casts. Arena: alive, 0 taken, 2/2 killed, 7 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 2.6 s. Direction: agree.

Conversion mismatches: Bramble Hulk (unit 1): 171 points a second in the threat scene, 19 in the arena; Gloam (unit 2): 254 points a second in the threat scene, 0 in the arena; monster level 80 (area 77) in the arena; the threat scene is built at 95.

## equal_lines_far_and_in_contact

Threat harness: alive, 693 taken, 4/4 killed, 6 casts. Arena: alive, 0 taken, 4/4 killed, 9 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.4 s. Direction: agree.

Conversion mismatches: Hell Bovine (unit 1): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 2): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 3): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 4): 193 points a second in the threat scene, 24 in the arena; monster level 81 (area 39) in the arena; the threat scene is built at 95.

## stone_skin_elite_soaks

Threat harness: dead, 4077 taken, 0/4 killed, 28 casts. Arena: alive, 0 taken, 3/4 killed, 12 casts, moved 0 units, 0 swaps, 0 potions, ran 10.0 s. Direction: differ.

Conversion mismatches: Ghoul (unit 1, elite): 266 points a second in the threat scene, 24 in the arena; Afflicted (unit 2): 54 points a second in the threat scene, 0 in the arena; Afflicted (unit 3): 54 points a second in the threat scene, 0 in the arena; Afflicted (unit 4): 54 points a second in the threat scene, 0 in the arena; monster level 73 (area 36) in the arena; the threat scene is built at 95.

## ghosts_in_front_of_archers

Threat harness: dead, 4793 taken, 1/6 killed, 28 casts. Arena: alive, 116 taken, 3/6 killed, 16 casts, moved 0 units, 0 swaps, 0 potions, ran 10.0 s. Direction: differ.

Conversion mismatches: Ghost (unit 0): 112 points a second in the threat scene, 13 in the arena; Ghost (unit 1): 112 points a second in the threat scene, 13 in the arena; Ghost (unit 2): 112 points a second in the threat scene, 13 in the arena; Returned Archer (unit 10): 75 points a second in the threat scene, 0 in the arena; Returned Archer (unit 11): 75 points a second in the threat scene, 0 in the arena; Slayer (unit 12): 123 points a second in the threat scene, 14 in the arena; monster level 84 (area 124) in the arena; the threat scene is built at 95.

## bovines_closing_from_two_sides

Threat harness: alive, 647 taken, 6/6 killed, 9 casts. Arena: alive, 0 taken, 6/6 killed, 9 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.4 s. Direction: agree.

Conversion mismatches: Hell Bovine (unit 0): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 1): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 2): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 10): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 11): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 12): 193 points a second in the threat scene, 24 in the arena; monster level 81 (area 39) in the arena; the threat scene is built at 95.

## low_life_in_melee

Threat harness: dead, 624 taken, 3/3 killed, 4 casts. Arena: alive, 0 taken, 3/3 killed, 6 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 2.2 s. Direction: differ.

Conversion mismatches: Hell Bovine (unit 1): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 2): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 3): 193 points a second in the threat scene, 24 in the arena; monster level 81 (area 39) in the arena; the threat scene is built at 95.

## low_life_two_dying_gloams

Threat harness: alive, 91 taken, 2/2 killed, 2 casts. Arena: alive, 0 taken, 2/2 killed, 4 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 1.6 s. Direction: agree.

Conversion mismatches: Gloam (unit 1): 254 points a second in the threat scene, 0 in the arena; Gloam (unit 2): 254 points a second in the threat scene, 0 in the arena; monster level 80 (area 77) in the arena; the threat scene is built at 95.

## low_life_under_knights

Threat harness: dead, 1976 taken, 4/4 killed, 12 casts. Arena: alive, 0 taken, 4/4 killed, 17 casts, moved 0 units, 0 swaps, 0 potions, ran 10.0 s, cleared at 5.9 s. Direction: differ.

Conversion mismatches: Oblivion Knight (unit 1): 144 points a second in the threat scene, 0 in the arena; Oblivion Knight (unit 2): 144 points a second in the threat scene, 0 in the arena; Oblivion Knight (unit 3): 144 points a second in the threat scene, 0 in the arena; Oblivion Knight (unit 4): 144 points a second in the threat scene, 0 in the arena; monster level 85 (area 108) in the arena; the threat scene is built at 95.

## dolls_running_in

Threat harness: alive, 1098 taken, 8/8 killed, 6 casts. Arena: alive, 900 taken, 8/8 killed, 8 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.3 s. Direction: agree.

Conversion mismatches: Death Lord (unit 0): 135 points a second in the threat scene, 16 in the arena; Death Lord (unit 1): 135 points a second in the threat scene, 16 in the arena; Death Lord (unit 2): 135 points a second in the threat scene, 16 in the arena; Death Lord (unit 3): 135 points a second in the threat scene, 16 in the arena; Death Lord (unit 4): 135 points a second in the threat scene, 16 in the arena; Undead Soul Killer (unit 10): 225 points a second in the threat scene, 14 in the arena; Undead Soul Killer (unit 11): 225 points a second in the threat scene, 14 in the arena; Undead Soul Killer (unit 12): 225 points a second in the threat scene, 14 in the arena; monster level 85 (area 131) in the arena; the threat scene is built at 95.

## dolls_on_the_character

Threat harness: dead, 1512 taken, 3/3 killed, 2 casts. Arena: dead at 1.2 s, 900 taken, 3/3 killed, 3 casts, moved 0 units, 0 swaps, 0 potions, ran 1.2 s, cleared at 1.1 s. Direction: agree.

Conversion mismatches: Undead Soul Killer (unit 1): 225 points a second in the threat scene, 14 in the arena; Undead Soul Killer (unit 2): 225 points a second in the threat scene, 14 in the arena; Undead Soul Killer (unit 3): 225 points a second in the threat scene, 14 in the arena; monster level 85 (area 131) in the arena; the threat scene is built at 95.

## might_elite_beside_minions

Threat harness: alive, 410 taken, 5/5 killed, 6 casts. Arena: alive, 0 taken, 5/5 killed, 8 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.7 s. Direction: agree.

Conversion mismatches: Venom Lord (unit 0): 171 points a second in the threat scene, 21 in the arena; Venom Lord (unit 1): 171 points a second in the threat scene, 21 in the arena; Venom Lord (unit 2): 171 points a second in the threat scene, 21 in the arena; Venom Lord (unit 3): 171 points a second in the threat scene, 21 in the arena; Venom Lord (unit 10, elite): 284 points a second in the threat scene, 35 in the arena; boost carried as an aura (unit 10 x2.0); monster level 85 (area 108) in the arena; the threat scene is built at 95.

## herald_with_minions

Threat harness: dead, 13552 taken, 1/7 killed, 28 casts. Arena: alive, 0 taken, 1/7 killed, 27 casts, moved 0 units, 0 swaps, 0 potions, ran 10.0 s. Direction: differ.

Conversion mismatches: Abyss Knight (unit 10, elite): 281 points a second in the threat scene, 0 in the arena; Abyss Knight (unit 1): 206 points a second in the threat scene, 0 in the arena; Abyss Knight (unit 2): 206 points a second in the threat scene, 0 in the arena; Abyss Knight (unit 3): 206 points a second in the threat scene, 0 in the arena; Abyss Knight (unit 4): 206 points a second in the threat scene, 0 in the arena; Abyss Knight (unit 5): 206 points a second in the threat scene, 0 in the arena; Abyss Knight (unit 6): 206 points a second in the threat scene, 0 in the arena; monster level 85 (area 107) in the arena; the threat scene is built at 95.

## stone_skin_zone

Threat harness: dead, 7288 taken, 0/5 killed, 28 casts. Arena: alive, 637 taken, 0/5 killed, 20 casts, moved 0 units, 0 swaps, 0 potions, ran 10.0 s. Direction: differ.

Conversion mismatches: Hell Bovine (unit 0): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 1): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 2): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 3): 193 points a second in the threat scene, 24 in the arena; Hell Bovine (unit 4): 193 points a second in the threat scene, 24 in the arena; monster level 81 (area 39) in the arena; the threat scene is built at 95.

## venom_lords_and_casters

Threat harness: alive, 1017 taken, 6/6 killed, 9 casts. Arena: alive, 0 taken, 6/6 killed, 14 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 5.1 s. Direction: agree.

Conversion mismatches: Venom Lord (unit 0): 171 points a second in the threat scene, 21 in the arena; Venom Lord (unit 1): 171 points a second in the threat scene, 21 in the arena; Venom Lord (unit 2): 171 points a second in the threat scene, 21 in the arena; Oblivion Knight (unit 10): 144 points a second in the threat scene, 0 in the arena; Storm Caster (unit 11): 128 points a second in the threat scene, 0 in the arena; Storm Caster (unit 12): 128 points a second in the threat scene, 0 in the arena; boost carried as an aura (unit 10 x1.5); monster level 85 (area 108) in the arena; the threat scene is built at 95.

## Agreement

| scene | threat-harness outcome | arena outcome | same direction? |
|---|---|---|---|
| gloams_behind_hulks | alive, 1098 taken, 7/7 killed | alive, 0 taken, 7/7 killed | yes |
| witch_and_soul_beside_tanky_elite | alive, 1420 taken, 3/3 killed | alive, 0 taken, 3/3 killed | yes |
| dying_gloam_fresh_hulk | alive, 274 taken, 2/2 killed | alive, 0 taken, 2/2 killed | yes |
| equal_lines_far_and_in_contact | alive, 693 taken, 4/4 killed | alive, 0 taken, 4/4 killed | yes |
| stone_skin_elite_soaks | dead, 4077 taken, 0/4 killed | alive, 0 taken, 3/4 killed | no |
| ghosts_in_front_of_archers | dead, 4793 taken, 1/6 killed | alive, 116 taken, 3/6 killed | no |
| bovines_closing_from_two_sides | alive, 647 taken, 6/6 killed | alive, 0 taken, 6/6 killed | yes |
| low_life_in_melee | dead, 624 taken, 3/3 killed | alive, 0 taken, 3/3 killed | no |
| low_life_two_dying_gloams | alive, 91 taken, 2/2 killed | alive, 0 taken, 2/2 killed | yes |
| low_life_under_knights | dead, 1976 taken, 4/4 killed | alive, 0 taken, 4/4 killed | no |
| dolls_running_in | alive, 1098 taken, 8/8 killed | alive, 900 taken, 8/8 killed | yes |
| dolls_on_the_character | dead, 1512 taken, 3/3 killed | dead, 900 taken, 3/3 killed | yes |
| might_elite_beside_minions | alive, 410 taken, 5/5 killed | alive, 0 taken, 5/5 killed | yes |
| herald_with_minions | dead, 13552 taken, 1/7 killed | alive, 0 taken, 1/7 killed | no |
| stone_skin_zone | dead, 7288 taken, 0/5 killed | alive, 637 taken, 0/5 killed | no |
| venom_lords_and_casters | alive, 1017 taken, 6/6 killed | alive, 0 taken, 6/6 killed | yes |
