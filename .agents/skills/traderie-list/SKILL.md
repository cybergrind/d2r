---
name: traderie-list
description: Post a D2R item for sale on Traderie through the player's own browser (Chrome DevTools port), choosing which copy to list and the asking price from the offline cache, and review the player's active listings against cached asks. Use for "list this on Traderie", "create a listing", "sell the Echoing spear", "check my listings".
---

# Listing an item on Traderie

Posting a listing is public and under the player's account. Only post when the player asked for that
listing; otherwise fill the form and leave the last click to them.

## Before you start

- The player starts their browser with remote debugging (`--remote-debugging-port=8333`) and is logged
  in to Traderie. Check with `curl -s http://127.0.0.1:8333/json/version`.
- The browser holds the player's other tabs (mail, chat, work). **Touch only tabs the script opens.**
  Never read, navigate or close a tab you did not open.
- The item must be on the trade mule (`CyberTrade`). Read what is there from the collection database:
  `inventory_tracking/runs/collection/collection.sqlite`, tables `items` and `placements`
  (`gone_at is null`, `owner = 'CyberTrade'`); `stat_lines` holds the decoded rolls.

## Choosing the copy and the price

1. Look the item up offline first (`uv run --offline python -m pricing.knowledge lookup …`, the appraise
   skill). No web search for prices.
2. Count priced sellers for the same rolls in `pricing/data/appraisal-market.jsonl` and note which rune
   they ask. Rune values in Ist are in `pricing/data/wp-f-ladder.json` (2026-09-18: Um 0.67, Mal 0.79,
   Ist 1, Gul 1.4, Vex 2.6, Ohm 4.1, Lo 5.9, Sur 8.2, Cham 8.6, Ber 9.3, Jah 11.4).
3. The cache holds **asks only, no completed trades**. To sell rather than sit, price one rune step
   under the pack when the item is common (many sellers at the same rune), and at the lower quartile
   when it is thin. Leave offers open unless the player says otherwise.
4. With several copies, list the one whose extra roll is useful to the buyer; say which one and why.

## Posting

Write a spec and run the tool. Without `--submit` it fills and verifies the form and stops.

```sh
cat > /tmp/spec.json <<'JSON'
{"item": "Throwing Spear", "rarity": "magic", "ethereal": false,
 "properties": [{"search": "Warcries", "option": "+X to Warcries (Barbarian Only)", "value": 3},
                {"search": "Increased Attack Speed", "option": "+X% Increased Attack Speed", "value": 30}],
 "price": [{"rune": "Mal Rune", "amount": 1}]}
JSON
node pricing/tools/traderie_list.mjs /tmp/spec.json            # fill + verify only
node pricing/tools/traderie_list.mjs /tmp/spec.json --submit   # also press "Add Listing"
```

- `item` is the exact name in Traderie's item search (the base name for magic and rare items, the
  unique or set name otherwise). `rarity` is only for magic / rare / crafted bases.
- Each property needs the text to type (`search`) and the exact option text Traderie shows (`option`,
  with `X` for the number). The option labels are the first label of each entry in
  `pricing/data/appraisal-properties.json` with `{{value}}` written as `X`.
- Ladder, platform, mode and game version come from the account defaults; the tool checks they read
  Non Ladder / PC / softcore / reign of the warlock and stops if they do not.
- The tool prints what it read back from the form. `problems` must be empty; on any mismatch it stops
  and leaves the tab open. Success with `--submit` is Traderie's "Your listing has been submitted".
- One `price` entry per rune. "Or" alternatives and "items you're looking for" are not supported; add
  those by hand in the tab.
- If the harness blocks `--submit` (real-world transaction), run without it and ask the player to
  press "Add Listing" in the new tab.

## Changing a price

Traderie's edit form changes pricing only; the item and its rolls stay as listed (to change a roll,
remove the listing and post it again).

```sh
node pricing/tools/traderie_edit.mjs <listing id> --price "Ist Rune:6"            # fill + verify only
node pricing/tools/traderie_edit.mjs <listing id> --price "Ist Rune:6" --submit   # also press "Edit Listing"
```

- Repeat `--price` to ask for several runes together. The old price rows are removed first.
- A listing with an "Or" alternative makes the tool stop; edit those by hand.
- Without `--submit` each run leaves one open tab with the new price filled in, for the player to save.
- The `--submit` path of this tool has not been exercised yet (2026-10-09): check the listing afterwards.

## Reviewing active listings

```sh
node pricing/tools/traderie_listings.mjs <profile id>     # JSON: id, item lines, asking price
```

The profile id is the number in the player's profile URL (`…/profile/<id>/listings`). Compare each
listing with cached asks for the same item and rolls (priced sellers, lower quartile, median). Report
three groups: in line, priced under the pack, priced over it or without comparables. Do not edit or
remove listings unless asked.

## Notifications

```sh
node pricing/tools/traderie_notifications.mjs             # one JSON line: offers, messages, read flags
```

It uses one hidden tab (not in the tab strip, closed when the script exits), loads Traderie there and
reads the answer to the site's own notifications request; it never reads the login token. `make serve`
runs it with `--watch` and shows unread notifications on the HUD, also while the game is not running
(`inventory_tracking/hud/traderie.py`, `TRADERIE` in `inventory_tracking/config.py`, `--no-traderie`).

## Tools

All three share `pricing/tools/traderie_browser.mjs` (opens one new tab, real mouse and key events,
select helpers, price rows). Add further Traderie actions (mark sold, relist, remove) as new small
scripts on that module, each with a fill-and-verify default and an explicit `--submit`.

## Report

Say what was posted (item, rolls, price, offers), why that copy and price, the evidence date, and that
the numbers are asks. Fold nothing into the guides unless a price finding contradicts them.
