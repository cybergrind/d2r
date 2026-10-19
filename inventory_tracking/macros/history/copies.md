# macros/copies.py — design notes (moved from the module docstring, 2026-10-19)

The player, 16:50 on 2026-10-18: "loop should keep the best copy first" — the loop had sold a Maelstrom, set rings
and a Skin of the Flayed One the appraisal called junk. Standing rule of 2026-10-04: cleanup never drops the last copy
of a unique or set, only the surplus.

A set or unique item of the loop's junk (macros/junk.py `junk_of`) is kept, and stashed like any keeper, when

- no copy is owned (the first copy),
- no owned copy rolls at least as well (appraisal/owned.py `overall`, `AT_LEAST_AS_GOOD`), or
- what is owned cannot be told: its identify read is not found, or the collection cannot be read (the safe side).

The worse stashed copy stays where it is: the stash's cleanup is the player's ("very carefully").

## What is owned

The collection database (collection/store.py), read only. The stash watcher captures the character's stash,
inventory, cube, equipment, mercenary and the shared stash each time the stash closes (collection/watch.py), so the
loop's own stash stops keep it current; mules are as of their last capture (Win+S, or a stash closed on them). The
character that played last (`characters.last_seen`) is the loop's: its inventory and cube are left out, they hold the
loop's items in transit (16:54 on 2026-10-18: a junk Cathan's Seal lay in the cube as captured, sold a minute later).
Not covered: a character never captured, an item moved on a mule since its last capture. Copies match as
appraisal/owned.py matches them: the same unique or set row, ethereal or not; rolls compared on the variable stats
both share.

## The item's own read

The identify watcher keeps each item it reads in the service's run directory (identify/service.py `_assess`,
corpus/store.py `persist`: `identified/<id>.json`, with its unit id). An item carried from an earlier game has a new
unit id and no read (kept). Two copies in one visit: the best rolled is judged first and counts as owned for the next.
