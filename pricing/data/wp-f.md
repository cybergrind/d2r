# WP-F · Currency and the NL rune ladder (SC / Non-Ladder / PC / Reign of the Warlock) — pulled 2026-09-18

**Unit: 1 Ist Rune = 1.0.** Convert everything else with the *ladder* column; the JSON twin is `pricing/data/wp-f-ladder.json`.

| Rune | ladder (Ist) | ask median [min–max] | n asks / sellers | fills (diablo2.io, sold ≤3 d) | d2io guide band 2026-08-28 | flag |
|---|---|---|---|---|---|---|
| Pul | **0.57** | 0.67 [0.31–1.03] | 16 / 8 | — | 0.25–0.35 | +62 % above band (bulk-stack asks; buyers value Pul at 0.23: "Jah x1 → 50 Pul") |
| Um | **0.67** | 0.79 [0.50–1.22] | 18 / 8 | — | 0.35–0.50 | +35 % above band |
| Mal | **0.79** | 0.88 [0.64–1.35] | 27 / 13 | — | 0.55–0.70 | +13 % |
| Ist | **1** | 1.04 [0.91–2.02] | 25 / 14 | 1 sold row seen, lost (see unresolved) | 1 | — |
| Gul | **1.43** | 1.43 [1.04–2.37] | 28 / 14 | — | 1.4–1.7 | in band |
| Vex | **2.59** | 2.86 [1.96–4.05] | 43 / 21 | — | 2.5–3 | in band |
| Ohm | **4.05** | 3.81 [2.59–8.57] | 61 / 40 | — | 3.5–4 | in band |
| Lo | **5.89** | 5.71 [5.00–9.32] | 40 / 23 | — | 5–6 | in band |
| Sur | **8.23** | 8.57 [5.71–12.6] | 47 / 20 | — | 7–9 | in band |
| Ber | **9.32** | 11.4 [8.4–16.5] | 52 / 19 | 9.3 ("5 Ist 3 Gul"), 12.0 (16 Ber for 192 Ist); 4 Ber sold unpriced · bids 9 / 9 / 11 / 12 Ist | 10–12 | −7 % (asks at 1 Jah; buyers pay 9–12 Ist) |
| Jah | **11.4** | 13.8 [10.0–28.4] | 61 / 21 | 12 Ist (8 h ago), 10 Ist (1 d ago) | 10–12 | in band; fills 10–12 |
| Cham | **8.57** | 9.32 [6.2–16.5] | 40 / 28 | — | "offer" (ladder col 4–8) | ≈ Sur; sellers list it "1 Ber OR 1 Jah OR 1 Zod"; ×3 maxroll-2024 ("slightly > Vex") |
| Zod | **13.7** | 17.1 [11.4–19.0] | 61 / 12 | — | ≈ Jah (10–12) | +14 % joint, **+43 % on the ask median**; 41/61 listings = one seller ("Zod x2 → 3 Jah") |

Sources of the table: Traderie API, 100 newest listings per rune, SC/NL/PC, asks paid purely in runes (raw `pricing/raw/traderie/rune-*.json`); fills/bids from `pricing/raw/d2io/search-rune-{jah,ber}-sold.html`, `search-rune-ber-active.html` (2026-09-18 15:02–15:05, hc=2 ladder=2 plat_pc=1 legacy_resu=2). Solver `pricing/tools/rune_ladder.py` (seeded from the d2io ladder, converged in 3 outer iterations; Lem fixed at 0.20).
Ist in lesser runes (observed seller equivalences, 2026-09-18): "Ist x1 → 1 Gul OR 2 Mal OR 3 Um OR 4 Pul"; "Mal x1 → 1 Gul OR 1 Ist OR 2 Um OR 3 Pul"; "Um x1 → 1 Ist OR 1 Mal OR 2 Pul OR 3 Lem"; "Pul x1 → 1 Ist OR 1 Mal OR 1 Um OR 2 Lem". Bulk buyers value low runes lower: "Jah x1 → 50 Pul / 22 Mal / 13 Gul". d2io guide: "Ist ≈ 40 PGems or ≈ 12 PAmethyst", "≈7 Gul ≈ 1 Jah", "Ist x11 ≈ Ber ≈ Jah ≈ Zod ≈ 2 Lo". Observed bid: "1 Ber = 100 pskull" (diablo2.io WTB).

## How to read a price
* **Asks ≠ fills.** Traderie and diablo2.io "active" rows are asking prices; the only fills we can fetch are diablo2.io rows marked SOLD (≤3 days). Ber/Jah asks sit 10–25 % above their fills (Ber ask median 11.4 vs sold 9.3–12; Jah 13.8 vs sold 10–12). Quote the ladder column, expect to pay/receive the fill.
* **A Traderie ask is for the whole stack** and a listing may name several alternative prices (OR); the effective price is the cheapest alternative. Single low runes are commonly listed "1 Ist OR 1 Mal OR 1 Um OR 2 Lem" — only the last is a real price.
* **Two economies:** diablo2.io — "Resurrected characters cannot trade with Reign of the Warlock characters" (legacy_resu filter); never mix NL Ist with Ladder Ist (d2io guide 2026-08-28: Ber/Jah 16–22 Ist on Ladder vs 10–12 NL).
* **Why runes are the money** (maxroll Runes, 2026-02-10; Rune Value, 2024-03-06; Trading, 2026-02-10): every rune has a fixed cube exchange rate upward ("2x Ist + Sapphire = Gul … 2x Sur + Flawless Amethyst = Ber … 2x Cham + Flawless Emerald = Zod"), so they are divisible/fungible and never lose value to a bad roll; demand is set by runewords: Ber → Enigma (Jah-Ith-Ber), Infinity (Ber-Mal-Ber-Ist), CoH (Dol-Um-Ber-Ist); Jah → Enigma, Dream (Io-Jah-Pul), Faith/Ice/Phoenix; Lo → Grief (Eth-Tir-Lo-Mal-Ral), Fortitude (El-Sol-Dol-Lo); Ohm → CtA (Amn-Ral-Mal-Ist-Ohm), Ritual (Amn-Shael-Ohm, RotW); Vex → HotO (Ko-Vex-Pul-Thul), Flickering Flame (Nef-Pul-Vex), Phoenix; Ist → CtA, Infinity, CoH, Coven (Ist-Ral-Io, RotW), Void (Thul-Zod-Ist, RotW), MF socketing; Zod → BotD, Void, "Indestructible" socketing; Cham → Plague (Cham-Shael-Um), CBF socketing; Sur → cubing to Ber. Runeword tier list (2026-02-18) S tier: CtA, Enigma, Flickering Flame, Fortitude, Grief, HotO, Infinity, Insight, Last Wish, Phoenix, Spirit, Stealth. Observed: "WTB Jah … building my first enigma", "WTB 2 Ber … to make an infinity". Bulk junk runes trade too: "40x Hel / 40x Sol = High" (maxroll Rune Value), "8x Hel rune" for a Captain's GC (diablo2.io sold row).

**Glossary** (maxroll Trading guide 2026-02-10 unless marked *obs* = observed listing 2026-09-18): **LF** looking for · **ISO** in search of · **O / Offer** the seller has no fixed price ("Lf Offer", *obs*) · **OBO** or best offer ("LF Um or 10 pgems OBO", *obs*) · **N** need · **P** perfect · **WUG / WUN** what do you have / need · **T4T** thanks for trade · **Mid-Runes** Lem–Gul, **High-Runes / HR** Vex–Zod ("aiming for multiple HRs", *obs*; "1x mid rune (um, pul, lem)", *obs*) · **break a rune** trade it for lower runes (Ist = Mal + Um) · **BIN** buy-it-now, the fixed price that ends negotiation ("Edit: BIN is 1 ist rune", *obs*; not in the maxroll guide) · **pgems / pskull / pamy** perfect gems as small change (Ist ≈ 40 PGems, d2io guide; "1 ber = 100 pskull", *obs*) · **WTS / WTB / WTT** want to sell / buy / trade (diablo2.io row markers) · **each / per** a per-unit price on a multi-rune ask ("4 ber … 12 ist per", *obs*) · **fat** — no observed use in this session's pulls and not in the maxroll guide: do not define from memory, verify.

## Findings
* **Per-stack confirmed on 322 listings.** Of the amount>1 rune listings, 322 only make sense as a price for the whole stack ("Ist x11 → 1 Jah", "Gul x7 → 1 Jah", "Mal x18 → 1 Zod", "Zod x2 → 3 Jah"); 15 (4 %) only make sense per unit ("Ber x3 → 2 Lo/1 Jah", "Vex x155 → 1 Ohm", "Jah x7 → 14 Ist") and were excluded. Rule for every package: divide a Traderie rune/gem ask by `amount`; prices[].group = alternatives.
* **Property 1854 split (SC/NL/PC listings):** RotW 87–98 % per rune (Ber 53 RotW / 12 LoD / 10 unset; Ist 39/2/0; Zod 65/1/0; Pul 30/6/0). LoD-tagged asks do not price differently at this n (Ber 11.4 vs 11.4, Vex 2.94 vs 2.86, Gul 1.68 vs 1.50), so the ladder uses all SC/NL/PC listings; packages may keep 1854 as a soft filter.
* **>30 % vs the d2io 2026-08-28 ladder:** Pul +62 % and Um +35 % (seller asks for bulk stacks; the buyer side and the guide agree at 0.23–0.35 — convert *your* low runes at the guide band, price *their* stacks at the ladder), Zod ask median +43 % (joint +14 %; one seller's wall). Cham is not a "offer" item on Traderie: 40 asks, ≈ Sur. Ordering is now Zod > Jah > Ber (guide: Ber ≈ Jah ≈ Zod).

## Unresolved / verify
* Fills are thin: 2 Jah + 2 priced Ber in 3 days; nothing sold for Ist–Sur under a bare-name title. The one "ist" sold row was overwritten by a flood-empty retry (`search-rune-ist-sold.html` is the empty page) — re-pull with the same command on a later day. Widen with repeated 3-day pulls (WP-G/H/I share the diablo2.io slot).
* diablo2.io: rune listings are titled with the bare name ("Ber"), not "Ber Rune", and irarity=8 (Misc) does NOT match them — search `ber`, `jah`, `ist`… without a rarity filter; "lo"/"um" are under phpBB's 3-letter minimum (untested).
* "fat" undefined by any source fetched; Lem fixed from the guide (5 observations); Zod rests on 12 sellers.
* Traderie shows 100 listings/rune all bumped to 2026-09-18 — recency is seller bumps, not sales.

## Sources (fetched/cached 2026-09-18)
Traderie API `listings?item=<id>` (Pul 2899268590 · Um 2654038235 · Mal 2401638276 · Ist 2290642411 · Gul 4160776515 · Vex 3806138905 · Ohm 3896329590 · Lo 3632079454 · Sur 3382986705 · Ber 4149485449 · Jah 2552039455 · Cham 3191411278 · Zod 4067651730) · diablo2.io search.php (10 calls, log `pricing/raw/d2io/wpf-search-batch.log`) · diablo2.io post4505103 "D2R RotW SC price guide — revised 28 Aug 2026" · maxroll.gg/d2/items/rune-value (2024-03-06, pre-RotW: ratios not used, runeword map used) · maxroll.gg/d2/items/runes (2026-02-10) · maxroll.gg/d2/resources/trade-guide (2026-02-10) · maxroll.gg/d2/tierlists/runeword-tier-list (2026-02-18) · maxroll.gg/d2/items/runewords (2026-06-02) · maxroll.gg/d2/items/new-items-in-reign-of-the-warlock (2026-02-19).
