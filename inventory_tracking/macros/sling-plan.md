# Town Portal from the Sling (plan, 2026-10-18)

The player, 2026-10-18 ~11:17: "sling provides town teleport skill, that frees two slots in inventory (we can replace
tome of town portals) - we should properly handle it in our loops: when we have sling ring equipped - we don't need to
run any logic in regard of town portal (do not track, do not buy)".

## Facts (d2data dump, `third-parties/d2data/json/`, read 2026-10-18)

- `uniqueitems.json` row 415 (`lineNumber` 416): `"index": "Sling"`, `"code": "rin"` (`*ItemName` Ring), `lvl` 58,
  `lvl req` 50, `prop1 "oskill"`, `par1 "Townportal O Skill"`, `min1/max1 1`; then `cast1` 10 (FCR), `pierce-mag`
  3-5, `enr` 10-15, `slow` 15, `mag%` 10-20. The only ring (the only item at all) in uniqueitems/setitems whose
  properties name a Town Portal skill: no other candidate.
- `skills.json` `*Id` 411 `"Townportal O Skill"`, `skilldesc "otownportal"`, `srvdofunc` 109 (the tome's 220 has 113,
  the scroll's 219 has 113), `rightskill` 1, `restrict` 1. No `mana`, no `delay`, no charges, no `scroll` flag: its
  casts cost nothing and wait for no cooldown. `skilldesc.json` `otownportal`: name `skillan219` = "Town Portal".
- `properties.json` `oskill` (id 265): `stat1 "item_nonclassskill"`; `itemstatcost.json` `item_nonclassskill` is
  stat 97 (`NONCLASS_SKILL_STAT` in native/layout.py): the skill id is the stat's layer, its level the value. So the
  Sling is told in memory as Enigma's Teleport is (world.py `given_skills`, live 22:26 on 2026-10-17: `(97, 54, 1)`):
  the stat `(97, 411, 1)` on a worn item.
- Not charges (stat 204 `item_charged_skill`): nothing to read, nothing to repair, nothing to buy.

## Design: one `PortalSource`

- `macros/portal.py` `PortalSource(skill, name, stocked)`: how the character casts Town Portal. `FROM_TOME` (220, the
  tome's charges a stock: `stocked`) and `FROM_SLING` (411, no stock). `portal_source(run)` is the one decision:
  the Sling's when the worn items' skills hold 411, else the tome's (as before). `PortalSource.count(pack)`: the tome's
  charges, None for the Sling (an unread count, which says nothing to `short`); `.said(pack)` for texts.
- `world.GameMemory.worn_skills()`: the non-class skills (stat 97 layers) the worn items outside the other weapon set
  give, read once per set of worn items (the cache `own_teleport` had); the last read kept through an unreadable look
  (a lost read must not send the loop to buy scrolls); None never read. `own_teleport` = 54 in it (unchanged meaning).
  `Run.worn_skills` exposes it; the runner wires it beside `own_teleport`.
- Consumers, each through `PortalSource` only:
  - `portal.to_town`: presses `source.skill` (its key from the slot table + key file, as the tome's). No portal after
    the cast: "is the tome empty?" only for the tome.
  - `shop.short(pack, source)`: the portals counted only when `stocked`; keys unchanged.
  - `shop.restock`: reads the source; with the Sling no scroll buy (`buys(source)`), no abort on an unread tome; texts
    say "the Sling". Her trade window is still judged by a key and a scroll in her stock (she sells scrolls anyway).
  - `loop.Loop`: `portal` read each leg in a game, logged when it changes (so at the loop's first leg):
    `Macro: loop: Town Portal from <the Sling|the tome>: skill <411|220> <in slot N|on no skill key>; worn skills [...]`.
    `short` with it; the trade session's report says `portals the Sling` instead of a count.
- Without the Sling everything reads as before: the default is `FROM_TOME`; all existing tests stay unchanged.
- No tome carried: `Pack.portals` is 0 (as today); with the Sling it is never counted. cube.py `KEPT` / stash.py keep
  a tome when there is one; none carried changes nothing there.

## The HUD/OSD portal widget (decision: no change, follow-up)

`osd/widgets/portal.py` shows `tp: N` in town only while a tome is carried at or under its threshold. With the Sling
and no tome it shows nothing, which is right. With the Sling and a low tome still carried it would remind of a refill
the player no longer needs; hiding it needs the worn items' stats in `make osd`'s resource probe
(`native/resource_probe.py`, `tracking/resources.py`), a separate process the macro must stay independent of (the HUD
canvas ruling). Follow-up only if the player keeps a tome with the Sling.

## Files

`macros/skills.py` (411, its name), `macros/world.py` (`given_skills`, `worn_skills`), `macros/engine.py`
(`Run.worn_skills`), `macros/runner.py` (wiring), `macros/portal.py`, `macros/shop.py`, `macros/loop.py`;
tests: `test_world.py`, `test_portal.py`, `test_shop.py`, `test_loop.py`, `fakes.py` (`Game.worn`).

## Tests

- world: the Sling's `(97, 411, 1)` on a ring reads as worn skill 411; Enigma's Teleport still `own_teleport`; one read
  per set of items; an unreadable look keeps the last read.
- portal: with the Sling worn and 411 on `x`, `to_town` presses `x` for 411; without it the tome's 220 as before; the
  Sling worn but 411 on no key stops naming it.
- shop: `short` ignores portals with the Sling (keys still count); `restock` with the Sling and no tome (portals 0)
  buys keys only, no Shift + right click on a scroll, says "the Sling".
- loop: a game with the Sling worn and no tome carried goes to the chests (not to Jamella); the first leg logs the
  source; the report says the Sling.

## To confirm live (the main session, at the first game after the restart)

1. `Macro: loop: Town Portal from the Sling: skill 411 in slot N; worn skills [..., 411]` at the loop's first leg.
   `the tome` there with the Sling worn: the stat is not `(97, 411)` (dump the ring's stats: world.py `read_stats`).
2. "in slot N": the client puts the oskill in the slot table by its id 411 once the player binds it to a key, as it does
   staff-charge and Enigma Teleport (54). "on no skill key": the player binds Town Portal (Sling) to a key (`x`).
3. The portal leg: `Macro: Town Portal (Sling) on x` then the portal (objects.txt 59) opens and is taken; srvdofunc 109
   differs from the tome's 113, so the portal object is assumed the same. `no Town Portal opened 2.5s after the cast from
   the Sling` would say it is not.
4. With the Sling a visit logs `Macro: shop: keys A -> B, portals 0 -> 0 (Town Portal from the Sling: none bought)` and
   says `Shop: N keys, portals from the Sling`; the trade report `portals from the Sling`.

## Open questions

- Whether the client clears the hotkey of 411 when the ring is taken off (the source then reads the tome: fine).
- The cast's quick-cast right-button skill (220 in the 2026-10-15 takes) should show 411; `press_skill` keys off the
  skill passed, so it follows.
