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
gloams_behind_hulks                DEAD     3.8       -   1800      5     10      0     0        0      0
witch_and_soul_beside_tanky_elite  DEAD     3.4       -   1800      0      7      0     0        0      0
dying_gloam_fresh_hulk             yes        -     2.7    432      2      7      0     0        0      0
equal_lines_far_and_in_contact     yes        -     3.4   1465      4      9      0     0        0      0
stone_skin_elite_soaks             yes        -       -   1251      3     12      0     0        0      0
ghosts_in_front_of_archers         DEAD     4.8       -   1800      2     13      0     0        0      0
bovines_closing_from_two_sides     yes        -     3.4   1174      6      9      0     0        0      0
low_life_in_melee                  DEAD     1.0       -    500      0      3      0     0        0      0
low_life_two_dying_gloams          yes        -     1.6    216      2      4      0     0        0      0
low_life_under_knights             DEAD     1.6       -    600      0      4      0     0        0      0
dolls_running_in                   yes        -     3.3   1189      8      8      0     0        0      0
dolls_on_the_character             DEAD     1.2     1.1    900      3      3      0     0        0      0
might_elite_beside_minions         yes        -     3.6    494      5      7      0     0        0      0
herald_with_minions                DEAD     2.2       -   1800      0      5      0     0        0      0
stone_skin_zone                    DEAD     4.4       -   1800      0     11      0     0        0      0
venom_lords_and_casters            yes        -     5.1   1695      6     14      0     0        0      0
total (16)                         8/16       -       -  18916     46    126      0     0        0      0
```

## gloams_behind_hulks

Threat harness: alive, 1098 taken, 7/7 killed, 6 casts. Arena: dead at 3.8 s, 1800 taken, 5/7 killed, 10 casts, moved 0 units, 0 swaps, 0 potions, ran 3.8 s. Direction: differ.

Conversion mismatches: Bramble Hulk (unit 0): 171 points a second in the threat scene, 0 in the arena; Bramble Hulk (unit 1): 171 points a second in the threat scene, 0 in the arena; Bramble Hulk (unit 2): 171 points a second in the threat scene, 0 in the arena; Bramble Hulk (unit 3): 171 points a second in the threat scene, 0 in the arena; Gloam (unit 10): 254 points a second in the threat scene, 821 in the arena; Gloam (unit 11): 254 points a second in the threat scene, 821 in the arena; Gloam (unit 12): 254 points a second in the threat scene, 821 in the arena; monster level 80 (area 77) in the arena; the threat scene is built at 95.

## witch_and_soul_beside_tanky_elite

Threat harness: alive, 1420 taken, 3/3 killed, 8 casts. Arena: dead at 3.4 s, 1800 taken, 0/3 killed, 7 casts, moved 0 units, 0 swaps, 0 potions, ran 3.4 s. Direction: differ.

Conversion mismatches: Death Lord (unit 1, elite): 225 points a second in the threat scene, 93 in the arena; Burning Soul (unit 3): 254 points a second in the threat scene, 866 in the arena; boost carried as an aura (unit 2 x1.5); monster level 85 (area 131) in the arena; the threat scene is built at 95.

## dying_gloam_fresh_hulk

Threat harness: alive, 274 taken, 2/2 killed, 4 casts. Arena: alive, 432 taken, 2/2 killed, 7 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 2.7 s. Direction: agree.

Conversion mismatches: Bramble Hulk (unit 1): 171 points a second in the threat scene, 0 in the arena; Gloam (unit 2): 254 points a second in the threat scene, 821 in the arena; monster level 80 (area 77) in the arena; the threat scene is built at 95.

## equal_lines_far_and_in_contact

Threat harness: alive, 693 taken, 4/4 killed, 6 casts. Arena: alive, 1465 taken, 4/4 killed, 9 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.4 s. Direction: agree.

Conversion mismatches: monster level 81 (area 39) in the arena; the threat scene is built at 95.

## stone_skin_elite_soaks

Threat harness: dead, 4077 taken, 0/4 killed, 28 casts. Arena: alive, 1251 taken, 3/4 killed, 12 casts, moved 0 units, 0 swaps, 0 potions, ran 10.0 s. Direction: differ.

Conversion mismatches: Afflicted (unit 2): 54 points a second in the threat scene, 158 in the arena; Afflicted (unit 3): 54 points a second in the threat scene, 158 in the arena; Afflicted (unit 4): 54 points a second in the threat scene, 158 in the arena; monster level 73 (area 36) in the arena; the threat scene is built at 95.

## ghosts_in_front_of_archers

Threat harness: dead, 4793 taken, 1/6 killed, 28 casts. Arena: dead at 4.8 s, 1800 taken, 2/6 killed, 13 casts, moved 0 units, 0 swaps, 0 potions, ran 4.8 s. Direction: agree.

Conversion mismatches: monster level 84 (area 124) in the arena; the threat scene is built at 95.

## bovines_closing_from_two_sides

Threat harness: alive, 647 taken, 6/6 killed, 9 casts. Arena: alive, 1174 taken, 6/6 killed, 9 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.4 s. Direction: agree.

Conversion mismatches: monster level 81 (area 39) in the arena; the threat scene is built at 95.

## low_life_in_melee

Threat harness: dead, 624 taken, 3/3 killed, 4 casts. Arena: dead at 1.0 s, 500 taken, 0/3 killed, 3 casts, moved 0 units, 0 swaps, 0 potions, ran 1.0 s. Direction: agree.

Conversion mismatches: monster level 81 (area 39) in the arena; the threat scene is built at 95.

## low_life_two_dying_gloams

Threat harness: alive, 91 taken, 2/2 killed, 2 casts. Arena: alive, 216 taken, 2/2 killed, 4 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 1.6 s. Direction: agree.

Conversion mismatches: Gloam (unit 1): 254 points a second in the threat scene, 821 in the arena; Gloam (unit 2): 254 points a second in the threat scene, 821 in the arena; monster level 80 (area 77) in the arena; the threat scene is built at 95.

## low_life_under_knights

Threat harness: dead, 1976 taken, 4/4 killed, 12 casts. Arena: dead at 1.6 s, 600 taken, 0/4 killed, 4 casts, moved 0 units, 0 swaps, 0 potions, ran 1.6 s. Direction: agree.

Conversion mismatches: monster level 85 (area 108) in the arena; the threat scene is built at 95.

## dolls_running_in

Threat harness: alive, 1098 taken, 8/8 killed, 6 casts. Arena: alive, 1189 taken, 8/8 killed, 8 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.3 s. Direction: agree.

Conversion mismatches: Death Lord (unit 0): 135 points a second in the threat scene, 56 in the arena; Death Lord (unit 1): 135 points a second in the threat scene, 56 in the arena; Death Lord (unit 2): 135 points a second in the threat scene, 56 in the arena; Death Lord (unit 3): 135 points a second in the threat scene, 56 in the arena; Death Lord (unit 4): 135 points a second in the threat scene, 56 in the arena; Undead Soul Killer (unit 10): 225 points a second in the threat scene, 16 in the arena; Undead Soul Killer (unit 11): 225 points a second in the threat scene, 16 in the arena; Undead Soul Killer (unit 12): 225 points a second in the threat scene, 16 in the arena; monster level 85 (area 131) in the arena; the threat scene is built at 95.

## dolls_on_the_character

Threat harness: dead, 1512 taken, 3/3 killed, 2 casts. Arena: dead at 1.2 s, 900 taken, 3/3 killed, 3 casts, moved 0 units, 0 swaps, 0 potions, ran 1.2 s, cleared at 1.1 s. Direction: agree.

Conversion mismatches: Undead Soul Killer (unit 1): 225 points a second in the threat scene, 16 in the arena; Undead Soul Killer (unit 2): 225 points a second in the threat scene, 16 in the arena; Undead Soul Killer (unit 3): 225 points a second in the threat scene, 16 in the arena; monster level 85 (area 131) in the arena; the threat scene is built at 95.

## might_elite_beside_minions

Threat harness: alive, 410 taken, 5/5 killed, 6 casts. Arena: alive, 494 taken, 5/5 killed, 7 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 3.6 s. Direction: agree.

Conversion mismatches: boost carried as an aura (unit 10 x2.0); monster level 85 (area 108) in the arena; the threat scene is built at 95.

## herald_with_minions

Threat harness: dead, 13552 taken, 1/7 killed, 28 casts. Arena: dead at 2.2 s, 1800 taken, 0/7 killed, 5 casts, moved 0 units, 0 swaps, 0 potions, ran 2.2 s. Direction: agree.

Conversion mismatches: monster level 85 (area 107) in the arena; the threat scene is built at 95.

## stone_skin_zone

Threat harness: dead, 7288 taken, 0/5 killed, 28 casts. Arena: dead at 4.4 s, 1800 taken, 0/5 killed, 11 casts, moved 0 units, 0 swaps, 0 potions, ran 4.4 s. Direction: agree.

Conversion mismatches: monster level 81 (area 39) in the arena; the threat scene is built at 95.

## venom_lords_and_casters

Threat harness: alive, 1017 taken, 6/6 killed, 9 casts. Arena: alive, 1695 taken, 6/6 killed, 14 casts, moved 0 units, 0 swaps, 0 potions, ran 20.0 s, cleared at 5.1 s. Direction: agree.

Conversion mismatches: boost carried as an aura (unit 10 x1.5); monster level 85 (area 108) in the arena; the threat scene is built at 95.

## Agreement

| scene | threat-harness outcome | arena outcome | same direction? |
|---|---|---|---|
| gloams_behind_hulks | alive, 1098 taken, 7/7 killed | dead, 1800 taken, 5/7 killed | no |
| witch_and_soul_beside_tanky_elite | alive, 1420 taken, 3/3 killed | dead, 1800 taken, 0/3 killed | no |
| dying_gloam_fresh_hulk | alive, 274 taken, 2/2 killed | alive, 432 taken, 2/2 killed | yes |
| equal_lines_far_and_in_contact | alive, 693 taken, 4/4 killed | alive, 1465 taken, 4/4 killed | yes |
| stone_skin_elite_soaks | dead, 4077 taken, 0/4 killed | alive, 1251 taken, 3/4 killed | no |
| ghosts_in_front_of_archers | dead, 4793 taken, 1/6 killed | dead, 1800 taken, 2/6 killed | yes |
| bovines_closing_from_two_sides | alive, 647 taken, 6/6 killed | alive, 1174 taken, 6/6 killed | yes |
| low_life_in_melee | dead, 624 taken, 3/3 killed | dead, 500 taken, 0/3 killed | yes |
| low_life_two_dying_gloams | alive, 91 taken, 2/2 killed | alive, 216 taken, 2/2 killed | yes |
| low_life_under_knights | dead, 1976 taken, 4/4 killed | dead, 600 taken, 0/4 killed | yes |
| dolls_running_in | alive, 1098 taken, 8/8 killed | alive, 1189 taken, 8/8 killed | yes |
| dolls_on_the_character | dead, 1512 taken, 3/3 killed | dead, 900 taken, 3/3 killed | yes |
| might_elite_beside_minions | alive, 410 taken, 5/5 killed | alive, 494 taken, 5/5 killed | yes |
| herald_with_minions | dead, 13552 taken, 1/7 killed | dead, 1800 taken, 0/7 killed | yes |
| stone_skin_zone | dead, 7288 taken, 0/5 killed | dead, 1800 taken, 0/5 killed | yes |
| venom_lords_and_casters | alive, 1017 taken, 6/6 killed | alive, 1695 taken, 6/6 killed | yes |
