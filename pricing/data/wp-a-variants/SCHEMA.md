# WP-A variants — one JSON per S/A build guide (2026-09-20)

Why: `wp-a-builds.json` holds the main gear table (Slot | Item Options | Desirable Stats) and the merc table (Early/Mid/End) only.
Variant sections (Starter / Standard / Magic Find / Ubers / Terror Zone / Colossal Ancients / Budget …) are prose + d2planner embeds
and were never extracted — Sazabi's set on the Echoing Strike uber merc was missed that way.

File: `<slug>.json`
{
  "slug", "url", "tier", "class", "last_updated",
  "sources": {"cached_html": "pricing/raw/mr/guides__<slug>.html (fetched 2026-09-18)", "live_fetch": "2026-09-20", "live_last_updated": "..."},
  "variants": [
    {"name": "Standard", "purpose": "one sentence from the guide", "planner_only": false,
     "player": {"Weapon": [], "Off-Hand": [], "Weapon-Swap": [], "Off-Hand-Swap": [], "Helmet": [], "Body Armor": [], "Gloves": [], "Belt": [],
                "Boots": [], "Amulet": [], "Rings": [], "Charms": [], "Prebuff": [], "Other": []},
     "merc": {"type": "Act 2 Prayer / Act 5 Frenzy / Act 1 Rogue / Act 3 …", "Weapon": [], "Body Armor": [], "Helmet": [], "Off-Hand": []},
     "quotes": ["exact sentences that justify unusual picks, set items, prebuffs"]}
  ],
  "prose_only_items": ["items named anywhere in the guide but absent from the main gear table"],
  "notes": "uncertainties"
}
Item names as maxroll writes them (runeword + base when given: "Insight Giant Thresher"; magic/rare/crafted patterns with the affix words the guide uses).
