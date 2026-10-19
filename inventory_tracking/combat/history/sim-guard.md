# combat/sim/guard.py: design notes

The module docstring until 2026-10-19, moved here by the phase-4 cleanup (numbers and pointers as of then).

A guard on the character: a pool that takes some kinds of a blow's damage before the resistances, and while it
stands stuns a monster whose melee blow lands on the character. The rules are the client's, read in the decrypted
executable (rca/2026-10-13/re/notes-absorb.md); which skill sets a guard, its pool and its stun are a build's.

[code] the pool (event 11 `absorbdamage`, run by the damage resolve before the flat reductions, the resistances
and the absorb percentages):

- it takes only the kinds the rule names, each up to what is left of the pool: a blow's part of such a kind
  loses min(left, part), the pool as much;
- at 0 the state is removed: the guard is down until the build sets it again; a set always refills it to its
  most (the old state node is dropped and a new one made with the pool at its most);
- it has no length: it stands until it is used up or set again.

[code] the stun (event 1 `damagedinmelee`, run after the resolve, for a blow that hit, also one the pool took
whole; gone with the state, so not for the blow that took the pool to 0 [inferred: the remove callback drops the
state's handlers, the free path that calls it not read]): the striker is stunned for the rule's frames, at most
STUN_MOST; a monster with the unique flag only on UNIQUE_STUN of the character's rolls, never a boss (monstats
`boss`, BOSSES), never one that cannot move (monstats `Velocity` 0). A stunned monster neither thinks, walks, swings
nor casts until the stun is over [take: in the records of 2026-10-13 a Doom Knight's swing is followed by the
get-hit mode with state 21 on, then the neutral mode, then a walk 3.1 to 3.6 s later at the samples' resolution;
the AI's own test of the state not read], then thinks at once [inferred].

Which blows: only those of the types played by the client's own rules (sim/casters.py, a walker with a mind):
the fitted types' chances to take life and their cadence were fitted to takes in which the guard mostly stood, so
it is in them already (sim/casters.py's module text; rca/2026-10-13/sim-casters.md section 5).
