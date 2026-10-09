---
name: mules
description: Plan moving items from the shared stash tabs to mule characters in D2R - what each mule takes, which surplus or weak rolls to drop, how to compress mules and keep the trade mule clean - as step-by-step instructions with the fewest mule logins. Use for "clear the shared stash", "organise mules", "where do I put this", "what can I drop", "check what is remaining".
---

# Mule organisation

Output is a plan the player executes by hand in game. Nothing here moves items.
Values are offline KB **asks** in Ist (snapshot date from the KB); no online refresh.

## Standing rules (the player's, 2026-10-04 and 2026-10-07)

1. **Shared tabs are 1–5. There is no tab 6.** The `shared_stash 6` row in `collection space` is the
   unit behind the Gems/Materials/Runes tabs; never count it as free space.
2. **Clear tabs 3–5.** Tabs 1–2 stay as the buffer for small items (rings, amulets, jewels, charms):
   sorting those onto mules costs too many clicks, so only plan tabs 1–2 when asked or when they are
   nearly full, and then as one bulk step.
3. **Respect mule names.** Read the purpose from the name before using free space:

   | Name pattern | Holds |
   |---|---|
   | `CyberTrade` | trade mule: only the expensive items; **inventory stays empty** (needed for trade windows) |
   | `MUniq*`, `CybergrindMUniq` | uniques and sets |
   | `MSock*`, `CybergrindMSock` | socketed / runeword bases |
   | `Runewords` | made runewords |
   | `MCharm*` | charms |
   | `Jewel*` | jewels, rings, amulets |
   | `CybergrindAA` (Warlock), `CybergrindAC` (Necro), other played characters | not storage: see rule 11 |
   | anything else (`AmazonAA`, `CybergrindAB`, …) | check what it holds now and continue that theme |

   The roster changes: re-derive it from `collection status` and the snapshot each time.
4. **Trade mule:** propose only items worth about 1 Ist or more with a real band (verdict `sell`, or
   `slow` with a solid median). Stash only. If cheaper items sit there, plan moving them out.
5. **Never drop the last copy** of a unique, set or runeword. Only surplus copies are drop candidates;
   "keep" always names the better roll, and if the shared copy is the better one it *replaces* the
   mule copy (swap, then drop the mule's).
6. **Dropping weaker rolls is welcome**, most of all for low-priced items. A low-valued item with a
   perfect or near-perfect roll is kept over a mediocre copy and may be kept as a second copy.
7. **Leveling items matter** and are kept together: one mule (or one contiguous block of a mule),
   not scattered across the unique mules.
8. **Compress before creating.** The account allows 24 characters; 15–18 mules is the working cap.
   Merge half-empty mules of the same purpose and reclaim space with drops before proposing a new
   mule. A new mule needs a stated reason and a purpose-fitting name.
9. **When space runs out, drop by value.** Rank what is left by usefulness (own use, build demand,
   leveling, ask median) and compare with the average of what the mule already holds; cut from the
   bottom, sole copies and near-perfect rolls excepted.
10. **Minimise logins.** Each mule is logged once, and does all of its drops, takes and puts in that
    visit.

11. **Playable characters' personal space is the player's own (2026-10-07).** A mule's personal
    stash and inventory are the storage the plan fills. A playable character (today `CybergrindAA`, the
    Warlock, and `CybergrindAC`, the Necro, which is still level 1, so level does not tell) is never a destination: do not plan
    takes into its stash, inventory or cube, and do not propose drops from them unless asked.
    Items the triage marks for a played character (`OWN:`, class uniques, its mercenary gear) go to
    a mule as one block and are listed after the steps under "For your characters" (item, mule,
    who it is for), so the player picks them up when they choose. A playable character may still
    appear as a login for work in the shared tabs only (dropping from tabs 3–5).

## Procedure

1. **Read the state.**
   ```
   uv run --offline python -m inventory_tracking.collection status   # roster + last capture per character
   uv run --offline python -m inventory_tracking.collection space    # free cells and WxH fits per grid
   uv run --offline python .agents/skills/mules/snapshot.py > "$SCRATCH/items.tsv"
   ```
   The snapshot is one TSV row per item: `loc` (`S1`–`S5` or `<char>/<inv|sta|cub|equ|mer>`),
   `captured`, `verdict`, `median_ist`, `keep_ist`, `rarity`, `name`, `base`, `size`, `copies`,
   `stats`, `notes`. Filter it with `awk -F'\t'`; do not read the whole file into context.
   The database is `inventory_tracking/runs/collection/collection.sqlite` (tables `items`,
   `placements` with `gone_at`, `spaces`, `characters`) for ad-hoc questions.
2. **Check freshness.** A capture (Win+S in game) is per logged-in character. State the capture date
   of every mule the plan relies on; if a mule's capture is older than the last session that touched
   it, say so and put "press Win+S" in its step. Shared tabs are captured with whichever character
   is logged in.
3. **Classify the items in tabs 3–5** (and in tabs 1–2 only if in scope):
   - *own/played character*: `notes` has `OWN:` → a mule block, reported per rule 11.
   - *trade*: rule 4.
   - *surplus copy*: `copies` > 1 → compare rolls on the variable stats in `stats` across all
     copies; decide keep/swap/drop per rule 5–6.
   - *leveling*: `uv run --offline python -m pricing.knowledge recommend --class <c> --archetype <a>
     --max-level 75 --limit 80` (per class, also `--side merc`) → leveling mule.
   - *rest*: the mule whose name fits.
   Reading the verdicts: `sell`/`slow` have a usable median; on `vendor` and `check` the median is
   only a name-level reference band (white bases and class-level names can show absurd numbers), so
   treat those as low value unless the roll is near perfect. Magic/rare rings, amulets, jewels and
   charms have no priced rule: judge them by affixes with the appraise skill, or leave them in tabs 1–2.
   For a borderline roll, `uv run --offline python -m pricing.knowledge lookup "<name>" --rarity
   <rarity> --limit 2` gives the roll range.
4. **Make room on the mules.** For each purpose group, list surplus copies and the lowest-value
   items already on those mules (rule 9), then check whether two mules of the group fit into one
   (rule 8). Sum cells from the `size` column against `free`, and check the `fits` column for the
   large shapes (2x4, 2x3, 1x4): free cells are not free shapes. Leave the plan a few cells of slack.
5. **Order the logins.** Items only travel through the shared tabs, so:
   - drops from shared tabs first (any character) — this is what creates transit space;
   - a mule that only takes from shared can go at any point;
   - a mule that gives items to another mule must be logged before the receiver; park the items in
     a named tab and cell block so the receiver's step can say where to find them;
   - if two mules must exchange, one of them gets two logins; say so and keep it to that one.
   Start with the character that is logged in now when it has work to do.
6. **Verify the plan before sending it:** every item in tabs 3–5 has exactly one action; no sole
   copy is dropped; no mule receives more than it can hold; CyberTrade's inventory ends empty; nothing is planned
   into a playable character;
   no step refers to tab 6.

## Output format

The answer is always the **full, self-contained execution list**: every login and every item, in
order, readable top to bottom while playing. This also holds for an update ("I added items",
"re-check"): reprint the whole list with the changes folded in and name what changed in one line
above it; never answer with a delta plus "the other steps are unchanged".

- One numbered step per login, in login order. The heading carries the character and its capture
  date.
- Inside a step, one checkbox line per item, grouped in the order the player does it: **drop** on
  the mule, then **take** per shared tab (tab 3, tab 4, tab 5), then **put** into a shared tab.
- Concrete item names, with the distinguishing roll when copies exist ("Hexfire 147%"); never
  "the rest" or "misc uniques". A short reason in brackets on every drop ("MUniqA has 93%").
- Close each step with "Win+S" and the expected free space.
- Keep reasoning out of the steps. Assumptions, the "Mark for CyberTrade" table (item, where now,
  asks in Ist with the snapshot date), items that did not fit and optional compressions go
  *after* the list, short.

```
## 2. MUniqAB (captured 10-06)
Drop
- [ ] Heart Carver 203% — stash (keeping 218%)
- [ ] Naj's Circlet — stash (MUniqC has one)
Take
- [ ] Tab 3: Shaftstop 201%, Stealskull
- [ ] Tab 4: Hellmouth 167%
Put
- [ ] Tab 5, for CyberTrade: Infernostride ×2
- [ ] Win+S — free after: stash ~4, inventory 0
```

## Follow-up: "check what is remaining"

Re-run step 1 and diff against the plan: done / not done per step, items that went somewhere other
than planned, and new arrivals in tabs 3–5 since the plan. An item missing from every capture is
either dropped or on a mule without a fresh capture — say which mules are stale rather than
calling it gone.
