# builds/warlock/mark.py: design notes

The module docstring until 2026-10-19, moved here by the phase-4 cleanup (numbers and pointers as of then).

Death Mark (skills.txt 375): what it buys and when the fight casts it (rca/2026-10-14/death-mark.md).

The player, 2026-10-14: "death mark is skill that forces daemons to attack and lowers enemy defence"; "also,
death mark is a very effective mechanism that allow to distract/re-aggro enemies". What the skill does, by the
client and the takes (death-mark.md §1-2):

- the character's demons (`pettype demon`, `requirespettype 1`: with none it cannot be cast) teleport to the
  marked monster about 0.28 s after the cast and land 2.8 units from it at the median (the Pit Lord and the
  Defiler, both in about 90% of 454 marks; the mercenary is no demon and walks); no reach cap showed in the takes
  (11 of 11 demons farther than Param9's 38 units jumped too);
- the monsters round it then go for the demons, the nearest body by the client's rule (the pack's path targets:
  44% at the character before, 8% three seconds after, against 66% steady at unmarked elites);
- the marked monster takes stats 34 and 35 at -(5 + 2 x (level - 1)) and stat 31 at -(50 + 35 x (level - 1)):
  flat, not percent (the client subtracts stats 34/35 from each element of each hit as read, with no floor:
  ai_d2_dmg_element 0x14038FB70): -31 at the character's level 14 is 31 more points an element a hit, about 2% of a
  blade's; the defence cut (-505) helps only what rolls to hit (the mercenary, the demons): `struck_more` prices it
  for the demons sent;
- the cast costs the strike about MARK_CAST_SECONDS: one volley of blades (the strike's missiles, 706, round the
  macro's marks of 2026-10-13/14: 0.73 s between the volleys across the key against 0.38 s between two; the
  1.76 s measured before counted the client's cast events, which a held strike runs together, and a Sigil's key
  that waited out a second after the mark: rca/2026-10-14/death-mark-engage.md §3).

So a mark is worth what it draws off the character (priced by the safety pricing's harm, macros/safety.py
`Safety.weigh`, at the look's price of life, so the arbiter weighs it against the retreat: the share MARK_TURNS of
the blows of the pack within MARK_PACK of the marked monster) and what the demons and the mark add to the strike on
the marked monster (`gain`: the demons' hits, landing more often by the defence cut, and the mark's points),
against the cast. The fight's buff row casts it on the hostile that price names (the safety's last look,
`BuffFacts.draws`), a leader or a boss before a plain monster of the same fight (the player, 2026-10-14: "on the
leader / most dangerous monster"); with no price fresh (the pursuit off) by `gain` alone. Never with no demon,
never on a monster a cast or two kills (TRASH_CASTS), never again on one marked while its mark lasts: a new one when
the marked monster dies or its mark runs out and the fight goes on.

## The constants' measures (comments until 2026-10-19)

- MARK_CAST_SECONDS 0.37: the strike's missiles (706) round the macro's 5 marks of 2026-10-13/14 with no other key
  within 1.5 s after: 0.73 s from the volley before the key to the one after at the median, against 0.38 s between
  two volleys; the 15 with one (a Sigil's or Engorge's key, most 1.01 s after): 1.57 s; the player's own marks (228
  of 2026-10-10/13): 1.17 s. The 1.76 s measured before counted the client's cast events, which a held strike runs
  together (rca/2026-10-14/scripts/mark_volleys.py, death-mark-engage.md §3).
- MARK_PACK 8.0: the path targets of the monsters within 8 units of a marked one were the character's in 8% three
  seconds after the key, against 66% steady round an unmarked elite at its engagement; the character lost no more
  life after a mark than after such an engagement (67 against 69 points in six seconds).
- `gain`: the takes show no kill-speed gain on marked elites beyond the selection of the toughest (death-mark.md
  §2), and one on Diablo: 5.5 s marked, 8.6 s not.
- `unmarked_herald`: a tier 5 Apparition Herald's pack killed the character at 00:54:55 on 2026-10-18, its mark laid
  1 s before.
- `why_not`: marks on plain packs priced above nothing but not pressing cost the arena's Vizier his 16 s window in
  all of ten seeds (death-mark-engage.md §5).
- `mark_passed`: the game of 06:05 on 2026-10-14, the Infector's seal boss (362, flags 10) struck to a third of its
  life during a retreat died 3.6 s later with neither a mark nor a line (run-0305-findings.md §2).
