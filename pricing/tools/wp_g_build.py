#!/usr/bin/env python3
"""wp_g_build.py — build pricing/data/wp-g-bases.json (WP-G: white bases, ranked, with why/thresholds/asks/fills).

Inputs (all dated 2026-09-18): pricing/data/wp-a-bases.json (demand), pricing/data/wp-b-prices.json (Traderie asks by
bucket, Ist via WP-F ladder), pricing/data/wp-f-ladder.json (rune→Ist), pricing/raw/d2io/search-wpg-*.html (diablo2.io
sold rows = fills). Mechanics text is quoted from cached maxroll pages (pricing/raw/mr/*.html) and cited with their
"Last Updated" dates. Run from the repo root:  python3 pricing/tools/wp_g_build.py
"""
import json, re, sys, os, glob, statistics
sys.path.insert(0, os.path.dirname(__file__))
from d2io_search import parse as d2io_parse

ROOT = os.getcwd()
A = json.load(open('pricing/data/wp-a-bases.json'))
B = json.load(open('pricing/data/wp-b-prices.json'))
F = json.load(open('pricing/data/wp-f-ladder.json'))
LADDER = {k: v['ist'] for k, v in F.items() if not k.startswith('_')}
DATE = '2026-09-18'

SRC = {
    'base':  {'url': 'https://maxroll.gg/d2/items/base-items', 'date': 'May 12, 2024', 'note': 'pre-RotW; base stat tables (defense, damage, str/dex, Weapon Speed Modifier, max sockets), qualities'},
    'sock':  {'url': 'https://maxroll.gg/d2/items/sockets', 'date': 'June 16, 2026', 'note': 'Number of Sockets by ilvl table, Larzuk quest, cube recipes'},
    'rw':    {'url': 'https://maxroll.gg/d2/items/runewords', 'date': 'June 2, 2026', 'note': 'Recommended Base Item(s), Socketed (n)'},
    'tier':  {'url': 'https://maxroll.gg/d2/tierlists/runeword-tier-list', 'date': 'February 18, 2026', 'note': 'runeword S/A/B/C/D/F tiers'},
    'new':   {'url': 'https://maxroll.gg/d2/items/new-items-in-reign-of-the-warlock', 'date': 'February 19, 2026', 'note': 'grimoire bases, RotW runewords'},
    'merc':  {'url': 'https://maxroll.gg/d2/resources/mercenary-mechanics', 'date': 'February 10, 2026', 'note': '"Ethereal Items do not suffer from Durability loss when equipped on a Mercenary"'},
    'dur':   {'url': 'https://maxroll.gg/d2/resources/durability-quantity', 'date': 'February 10, 2026', 'note': 'ethereal = +50% defense / base weapon damage, cannot be repaired, Zod = Indestructible'},
    'ias':   {'url': 'https://maxroll.gg/d2/resources/attack-speed', 'date': 'February 10, 2026', 'note': 'Weapon Speed Modifier: negative = faster'},
    'wpa':   {'url': 'pricing/data/wp-a-bases.json', 'date': DATE, 'note': 'demand weight (S=2/A=1 over 26 builds)'},
    'wpb':   {'url': 'pricing/data/wp-b-prices.json', 'date': DATE, 'note': 'Traderie asks SC/NL/PC/RotW, Ist via WP-F ladder; asks, not fills'},
    'wpf':   {'url': 'pricing/data/wp-f-ladder.json', 'date': DATE, 'note': 'Ist = 1; Pul .57 Um .67 Mal .79 Gul 1.43 Vex 2.59 Ohm 4.05 Lo 5.89 Sur 8.23 Ber 9.32 Jah 11.4 Cham 8.57 Zod 13.7'},
    'd2io':  {'url': 'https://diablo2.io/search.php (irarity=4 activesold=1 hc=2 ladder=2 plat_pc=1 legacy_resu=2)', 'date': DATE, 'note': 'fills = trades marked sold in the last 3 days; raw pricing/raw/d2io/search-wpg-*.html'},
    'guide': {'url': 'https://diablo2.io/post4505103.html', 'date': '2026-08-28', 'note': 'NL price guide "Bases" rows, orientation only'},
}

# ---------- fills ----------
RUNE_RE = re.compile(r'(\d+)\s*x?\s*(Pul|Um|Mal|Ist|Gul|Vex|Ohm|Lo|Sur|Ber|Jah|Cham|Zod|Lem)\b', re.I)

def price_to_ist(price):
    """'1 Ohm 4 Mal' -> (7.21, False); '3 Key of Terror' -> (None, True) ; mixed -> (rune part, True)."""
    tot = 0.0; n = 0
    for q, r in RUNE_RE.findall(price):
        tot += int(q) * LADDER[r.capitalize()]; n += 1
    rest = RUNE_RE.sub('', price)
    nonrune = bool(re.search(r'[A-Za-z]{3,}', rest))
    return (round(tot, 2) if n else None), nonrune

def load_fills():
    fills = {}
    for f in sorted(glob.glob('pricing/raw/d2io/search-wpg-*.html')):
        slug = os.path.basename(f)[len('search-wpg-'):-5]
        t = open(f, errors='ignore').read()
        flood = 'you cannot use search at this time' in t
        m = re.search(r'Found\s*(?:<[^>]+>\s*)*(\d+)\s*(?:<[^>]+>\s*)*matches', t)
        found = int(m.group(1)) if m else None
        rows = []
        for slug2, nl, hc, plat, rotw, sold, txt in d2io_parse(t):
            if sold != 'SOLD':
                continue
            pm = re.search(r'Sold (\d+ \w+ ago) by \S+ to \S+ for (.+)$', txt)
            when = pm.group(1) if pm else '?'
            price = pm.group(2).strip() if pm else '?'
            ist, nonrune = price_to_ist(price)
            title = re.sub(r'^WTS SOLD ', '', txt.split(' Sold ')[0]).strip()
            rows.append({'title': title[:160], 'sold': when, 'price': price, 'ist': ist,
                         'nonrune_price': nonrune, 'scope': f'{nl}/{hc}/{plat}/{rotw or "?"}',
                         'url': 'https://diablo2.io' + slug2})
        fills[slug] = {'file': f, 'found': found, 'flood_page': flood, 'rows': rows}
    return fills

FILLS = load_fills()

def fills_for(keys):
    out = []; notes = []
    for k in keys:
        fx = FILLS.get(k)
        if not fx:
            notes.append(f'"{k}": not searched (budget of 18 spaced searches)'); continue
        if fx['flood_page']:
            notes.append(f'"{k}": diablo2.io returned its flood-control page ("cannot use search at this time"); no data'); continue
        if fx['found'] == 0 or not fx['rows']:
            notes.append(f'"{k}": no fills in window (Found 0 matches, sold <=3 days, SC/NL/PC/RotW, base rarity)'); continue
        out += fx['rows']
    return out, notes

# ---------- asks ----------
def bucket(slug, key):
    b = B[slug]['buckets'].get(key)
    if not b:
        return None
    c = b['cheapest'][0] if b['cheapest'] else {}
    return {'n': b['n'], 'n_priced': b['n_priced'], 'n_offer': b['n_offer'], 'thin': b['n'] < 3,
            'min_ist': b['min_ist'], 'median_ist': b['median_ist'], 'max_ist': b['max_ist'],
            'cheapest_ask': c.get('ask_full')}

def asks(slug, keys):
    out = {}
    for k in keys:
        v = bucket(slug, k)
        if v:
            out[k] = v
    return out

def demand(name, extra=None):
    a = A.get(name)
    if not a:
        return {'runewords': [], 'sockets_by_runeword': {}, 'builds_char': 0, 'builds_merc': 0, 'weight': 0,
                'note': extra or 'not in wp-a-bases.json (no S/A build guide names it; priced by WP-B from the plan seed list)'}
    d = {'runewords': a['runewords'], 'sockets_by_runeword': a['sockets_by_runeword'], 'eth_wanted': a['eth_wanted'],
         'builds_char': len(a['builds_char']), 'builds_merc': len(a['builds_merc']), 'weight': a['weight']}
    if extra:
        d['note'] = extra
    return d

def S(*keys):
    return [dict(SRC[k]) for k in keys]

# ---------- the ranked list ----------
# ilvl_sockets = maxroll sockets table (ilvl 1-25 / 26-40 / 41+); stats = maxroll base-items page (May 12, 2024).
BASES = []
def add(**kw):
    BASES.append(kw)

add(key='BS-giant-thresher', base='Giant Thresher', cls='weapon / polearm (mercenary)', wpb='giant-thresher', wpa='Giant Thresher',
    fills_keys=['thresher'],
    ilvl_sockets='3 / 4 / 6', stats='40-114 dmg (avg 77), WSM 0, 188 str / 140 dex, qlvl 85, durability 55',
    gates=['ethereal (merc weapon: +50% base damage, no durability loss on a mercenary)', 'exactly 4 sockets on drop (Infinity/Insight/Pride are Socketed (4); Larzuk gives 6, cube on a normal eth base gives 4 only 16.67%)', 'superior (5-15% ED; 15 ED is the chase roll; superior cannot be cube-socketed)', 'never 5 or 6 sockets (Obedience 5 is the only user of 5)'],
    keep=['eth 4os superior >=15 ED: asks 126 -> 799 Ist (n=8, 4 priced; "11x Jah" cheapest) — HR territory, quote-only', 'eth 4os superior <15 ED: 57 -> 86 Ist (n=10)', 'eth 4os normal: 5.9 -> 11.4 Ist (n=20) — a Lo-to-Jah item'],
    sell=['eth 6os superior >=15 ED: 11.4 -> 86 (n=9) — BotD/Obedience-class buyers only', 'eth 0os superior >=15 ED: 9.3 -> 10.4 (n=4) — Larzuk makes it 6os, so only a 6-socket runeword can use it'],
    floor=['eth 6os normal: 0.2 -> 1.0 (n=16)', 'eth 5os normal: 0.57 -> 0.9 (n=5)', 'non-eth 4os normal: 0.67 -> 4.8 (n=6) — no merc wants a non-eth polearm'],
    ask_keys=['4os/eth/superior/15ed', '4os/eth/superior', '4os/eth/normal', '6os/eth/superior/15ed', '0os/eth/superior/15ed', '6os/eth/normal', '4os/noneth/normal'],
    why='Infinity, Pride and Obedience list "Ethereal Superior Giant Thresher" first and Insight lists it second (runewords page, June 2, 2026); WP-A: 25 of 26 S/A builds put Insight or Infinity on the Act 2 mercenary (weight 40). Ethereal adds 50% to base weapon damage but cannot be repaired (durability page, Feb 10, 2026) — harmless on a mercenary because "Ethereal Items do not suffer from Durability loss when equipped on a Mercenary" (mercenary-mechanics, Feb 10, 2026). The sockets table (June 16, 2026) gives Giant Thresher 3/4/6 sockets by ilvl, so at ilvl 41+ a drop can roll 1-6 and only the 4-socket roll fits Infinity/Insight/Pride: Larzuk always gives the maximum (6) and the cube recipe (normal/ethereal only, not superior) lands on 4 with 16.67% for a max-6 base. That is why "eth 4os" is a Lo-Jah item while "eth 6os" of the same base is a Lem. Superior 15 ED on top is the chase roll — a superior base cannot be cubed, so a superior eth 4os drop is a pure drop-luck item.',
    sources=S('rw', 'wpa', 'dur', 'merc', 'sock', 'base', 'wpb', 'wpf', 'd2io'))

add(key='BS-great-poleaxe', base='Great Poleaxe', cls='weapon / polearm (mercenary)', wpb='great-poleaxe', wpa=None,
    fills_keys=['great-poleaxe'],
    ilvl_sockets='3 / 4 / 6', stats='46-127 dmg (avg 86.5), WSM 0, 179 str / 99 dex, qlvl 84, durability 55',
    gates=['ethereal', 'exactly 4 sockets (Larzuk -> 6; cube on normal eth -> 4 at 16.67%)', 'superior >=15 ED'],
    keep=['eth 4os superior >=15 ED: 80 -> 126 Ist (n=16)', 'eth 4os "normal" >=15 ED (mislabelled superiors): 126 -> 183 (n=3)', 'eth 4os superior <15 ED: 5.9 -> 34 (n=7)'],
    sell=['eth 6os superior >=15 ED: 9.3 -> 57 (n=20)', 'eth 0os superior >=15 ED: 5.9 -> 15 (n=6) — Larzuk = 6os', 'eth 4os normal: 1.0 -> 3.9 (n=17) — Ist to Ohm'],
    floor=['eth 6os normal: 0.2 -> 0.62 (n=13)', 'eth 5os normal: 0.25 -> 0.79 (n=5)', 'non-eth 4os normal: 0.79 -> 0.9 (n=4)'],
    ask_keys=['4os/eth/superior/15ed', '4os/eth/normal/15ed', '4os/eth/superior', '6os/eth/superior/15ed', '0os/eth/superior/15ed', '4os/eth/normal', '6os/eth/normal', '4os/noneth/normal'],
    why='Not a maxroll "Recommended Base" for any runeword (runewords page June 2, 2026 lists Giant Thresher, Thresher, Matriarchal Spear, Mancatcher for Infinity/Pride/Obedience and Colossus Voulge/Giant Thresher/Thresher for Insight) and no S/A guide names it (WP-A weight 0); the market prices it as an Infinity/Insight base anyway — the diablo2.io guide of 2026-08-28 lists "Eth 4os CV/Thresher/GT/GPA Um-Vex" as one row, and WP-B found 125 SC/NL listings with the eth 4os superior 15 ED bucket asking 80-126 Ist (n=16). Mechanically it is a 6-max-socket elite polearm (sockets table June 16, 2026: 3/4/6) with 46-127 damage, WSM 0 and 179 str (base-items, May 12, 2024) — same socket lottery as Giant Thresher. Treat the demand as verified by the market, not by a guide.',
    sources=S('rw', 'guide', 'wpb', 'sock', 'base', 'wpf', 'd2io'))

add(key='BS-sacred-targe', base='Sacred Targe', cls='shield / paladin (auric)', wpb='sacred-targe', wpa='Sacred Targe',
    fills_keys=['sacred-targe'],
    ilvl_sockets='3 / 4 / 4', stats='126-158 def, block 60% (Paladin), smite 22-70, 86 str, qlvl 63, durability 20; auto-mod "All Resistances +5-45 OR 10-65% Enhanced Damage & 15-121 to Attack Rating"',
    gates=['the automod roll: All Resistances +45 is the whole value ("45@"); an ED/AR automod or <40@ is floor', 'sockets: 4 for Spirit/Phoenix/Exile, 3 for Dream/Sanctuary; 0os is fine (Larzuk gives 4 at ilvl 41+)', 'superior >=15 ED multiplies the ask (57 -> 126 vs 9.3 -> 17 for 45@ 4os)', 'ethereal 45@ is its own market (Exile repairs durability; 45.7 -> 63)'],
    keep=['45@ 4os any quality: 9.3 -> 22.8 Ist (n=26); superior >=15 ED 45@ 4os: 57 -> 126 (n=7)', '45@ 0os: 4.05 -> 40 (n=24; q1 14) — Larzuk it to 4os', '45@ eth any sockets: 45.7 -> 63 (n=9) — Exile base', '45@ 3os: 22.8 -> 45.7 (n=12) — Dream/Sanctuary buyers'],
    sell=['40-44@ 3os: 9.3 (n=3)'],
    floor=['res <40 or ED/AR automod: floor, thin (unset-res 0os 15ED rows 0.67 -> 4, n=11)'],
    ask_keys=['4os/noneth/superior/15ed/res45', '4os/noneth/normal/res45', '0os/noneth/superior/res45', '0os/noneth/normal/res45', '3os/noneth/normal/res45', '4os/eth/normal/res45', '0os/eth/normal/res45', '3os/noneth/normal/res40-44', '0os/noneth/normal/15ed/res?'],
    why='Spirit, Phoenix, Exile, Dream and Sanctuary all name "Superior Sacred Targe" (runewords page, June 2, 2026); WP-A: 25 character slots across S/A Paladin, Sorceress and other builds (weight 39). The base-items page (May 12, 2024) lists the auric-shield auto-mod "All Resistances +5-45 OR 10-65% Enhanced Damage & 15-121 to Attack Rating" — so the roll the buyer pays for is +45 all resistances, which no other Spirit shield offers, on the lightest 4-socket paladin shield (86 str vs Zakarum 142, Vortex 148, Kurast 124). Sockets table (June 16, 2026): 3/4/4, and Larzuk gives the maximum, so a 0os 45@ drop is a 4os Spirit/Phoenix/Exile base after the quest. Exile is B tier and Spirit/Phoenix S tier (tier list, Feb 18, 2026); Exile carries "Repairs 1 Durability in 4 seconds" (runewords page), which is why ethereal 45@ targes trade at 45.7-63 Ist.',
    sources=S('rw', 'base', 'sock', 'tier', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-grand-matron-bow', base='Grand Matron Bow', cls='weapon / amazon bow', wpb='grand-matron-bow', wpa='Grand Matron Bow',
    fills_keys=['grand-matron-bow'],
    ilvl_sockets='3 / 4 / 5', stats='30-54 dmg (avg 42), WSM 10, 108 str / 152 dex, qlvl 78; auto-mod +1-3 to Bow and Crossbow Skills (Amazon Only)',
    gates=['auto-mod roll: +3 Bow skills is the chase (+1/+2 rows are rare and priced far lower)', 'exactly 4 sockets (Faith is Socketed (4); Larzuk gives 5)', 'superior >=15 ED (the 91 -> 114 bucket vs 2 -> 4 for normal 4os +3)'],
    keep=['+3 4os superior >=15 ED: 91 -> 114 Ist (n=13) — HR item, asks', '+3 4os superior <15 ED: 1 -> 22.8 (n=5)'],
    sell=['+3 4os normal: 2 -> 4.05 (n=9) — Vex-Ohm, agrees with the diablo2.io guide', '+3 5os superior >=15 ED: 17 -> 39 (n=4) — Mist buyers only'],
    floor=['+3 5os normal: 0.67 -> 0.79 (n=20)', '+3 3os normal: 0.25 -> 0.79 (n=11)'],
    ask_keys=['4os/noneth/superior/15ed/skill3', '4os/noneth/superior/skill3', '4os/noneth/normal/skill3', '5os/noneth/superior/15ed/skill3', '5os/noneth/normal/skill3', '3os/noneth/normal/skill3'],
    why='Faith lists "Superior Grand Matron Bow, Matriarchal Bow" and Mist lists it second (runewords page, June 2, 2026). WP-A weight is only 4 (Strafe Amazon character + 3 mercenary tables), but the value is roll-driven: the base-items page (May 12, 2024) gives the Amazon bow auto-mod "+1-3 to Bow and Crossbow Skills", and every listing is bucketed by that roll — WP-B found "+3 4os superior 15 ED" asking 91-114 Ist while "+3 4os normal" asks 2-4. Sockets table (June 16, 2026): 3/4/5 — Faith needs 4, Larzuk gives 5, so 4os comes only from the drop or the cube (normal only, 16.67% for 4 on a max-5 base). Slow bow (WSM +10, attack-speed page Feb 10, 2026: positive = slower) — the guide pairs it with Faith\'s Fanaticism, which is why Matriarchal Bow (WSM -10) is the alternative for Ice/Mist.',
    sources=S('rw', 'base', 'sock', 'ias', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-cryptic-axe', base='Cryptic Axe', cls='weapon / polearm (mercenary)', wpb='cryptic-axe', wpa=None,
    fills_keys=['cryptic-axe'],
    ilvl_sockets='3 / 4 / 5', stats='33-150 dmg (avg 91.5), WSM 10, 165 str / 103 dex, qlvl 79, durability 65',
    gates=['ethereal', 'exactly 4 sockets (Larzuk -> 5; cube on normal eth -> 4 at 16.67%)', 'superior >=15 ED'],
    keep=['eth 4os superior >=15 ED: 91 -> 108 Ist (n=4)'],
    sell=['eth 4os superior <15 ED: 9.3 (n=2, thin)', 'eth 4os normal: 0.79 -> 1.0 (n=27) — Mal-Ist', 'eth 5os superior: 2.6 -> 5.9 (n=3)'],
    floor=['eth 5os normal: 0.4 -> 0.79 (n=16)', 'non-eth 4os normal: 0.42 -> 0.84 (n=4)'],
    ask_keys=['4os/eth/superior/15ed', '4os/eth/superior', '4os/eth/normal', '5os/eth/superior', '5os/eth/normal', '4os/noneth/normal'],
    why='Like Great Poleaxe, not a maxroll-recommended base and absent from WP-A (weight 0); the market trades it as an Infinity/Insight base (diablo2.io guide 2026-08-28 does not list it; WP-B priced 85 SC/NL listings). Highest average damage of the elite polearms (avg 91.5, base-items May 12, 2024) but the slowest (WSM +10; attack-speed page Feb 10, 2026: positive WSM = slower) and 5-max sockets (sockets table June 16, 2026: 3/4/5), so 4os comes from the drop or the cube only. The eth 4os normal bucket sits at 1 Ist (n=27) because supply of the "right" socket count is plentiful relative to Giant Thresher demand; only the superior 15 ED roll lifts it into Jah territory.',
    sources=S('rw', 'base', 'ias', 'sock', 'wpb', 'wpf', 'd2io'))

add(key='BS-mancatcher', base='Mancatcher', cls='weapon / spear (mercenary)', wpb='mancatcher', wpa='Mancatcher',
    fills_keys=['mancatcher'],
    ilvl_sockets='3 / 4 / 5', stats='42-92 dmg (avg 67), WSM -20, 132 str / 134 dex, qlvl 74, durability 28',
    gates=['ethereal', 'exactly 4 sockets (Larzuk -> 5)', 'superior >=15 ED'],
    keep=['eth 4os superior >=15 ED: 34 -> 86 Ist (n=10)', 'eth 4os superior <15 ED: 5.9 -> 11.4 (n=3)'],
    sell=['eth 4os normal: 0.2 -> 2.0 (n=31) — Um-Ist', 'non-eth 4os superior >=15 ED: 1.8 -> 7.6 (n=4)'],
    floor=['eth 5os normal: 0.13 -> 0.67 (n=16)', 'non-eth 4os normal: 0.17 -> 0.79 (n=12)'],
    ask_keys=['4os/eth/superior/15ed', '4os/eth/superior', '4os/eth/normal', '4os/noneth/superior/15ed', '5os/eth/normal', '4os/noneth/normal'],
    why='Infinity, Pride and Obedience list "Ethereal Superior Mancatcher" as the fourth option (runewords page, June 2, 2026); WP-A weight 27 (17 mercenary tables). It is the fastest Infinity base on the list (WSM -20; attack-speed page Feb 10, 2026: negative WSM adds directly to the animation rate) with the lowest str (132) but also the lowest damage (avg 67, base-items May 12, 2024) — hence the same socket rules as Thresher (3/4/5 sockets, Larzuk 5) and a lower ceiling than Giant Thresher.',
    sources=S('rw', 'base', 'ias', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-colossus-blade', base='Colossus Blade', cls='weapon / sword', wpb='colossus-blade', wpa='Colossus Blade',
    fills_keys=[],
    ilvl_sockets='3 / 4 / 6', stats='25-65 one-hand (Barbarian) / 58-115 two-hand, WSM 5, 189 str / 110 dex, qlvl 85, durability 50',
    gates=['ethereal + superior >=15 ED (Death "Ethereal Superior Colossus Blade"; Unbending Will "Superior Colossus Blade")', 'sockets 5 (Death) or 6 (Unbending Will/BotD-class): 0os eth superior is priced like 5os because Larzuk gives 6 and the buyer decides'],
    keep=['eth 0os superior >=15 ED: 68.5 -> 80 Ist (n=7)', 'eth 5os superior >=15 ED: 68.5 (n=3)', 'non-eth 5os superior >=15 ED: 11.4 -> 40 (n=11)'],
    sell=['eth 6os superior >=15 ED: 34 -> 45.7 (n=3)', 'eth 6os normal: 1 -> 4.2 (n=6)', 'eth 5os normal: 0.79 -> 2.6 (n=5)'],
    floor=['5os normal non-eth: 0.2 -> 0.79 (n=13)', '4os normal: 0.17 -> 1.0 (n=5)'],
    ask_keys=['0os/eth/superior/15ed', '5os/eth/superior/15ed', '5os/noneth/superior/15ed', '6os/eth/superior/15ed', '6os/eth/normal', '5os/eth/normal', '5os/noneth/normal'],
    why='Death lists "Ethereal Superior Berserker Axe, Ethereal Superior Colossus Blade" and Unbending Will "Superior Colossus Blade, Superior Phase Blade" (runewords page, June 2, 2026); WP-A weight 6 (Berserk Barbarian and two others). Value is almost entirely the eth + superior 15 ED combination on a 58-115 two-hand base (base-items, May 12, 2024); the plain 5os/6os sword is floor. Not searched on diablo2.io (budget).',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf'))

add(key='BS-thresher', base='Thresher', cls='weapon / polearm (mercenary)', wpb='thresher', wpa='Thresher',
    fills_keys=['thresher'],
    ilvl_sockets='3 / 4 / 5', stats='12-141 dmg (avg 76.5), WSM -10, 152 str / 118 dex, qlvl 71, durability 65',
    gates=['ethereal', 'exactly 4 sockets (Larzuk -> 5)', 'superior >=15 ED'],
    keep=['eth 4os superior >=15 ED: 57 -> 68.5 Ist (n=9)', 'eth 4os "normal" >=15 ED: 45.7 -> 57 (n=2, thin; mislabelled superior)'],
    sell=['eth 4os normal: 2.6 -> 8.1 (n=13) — Vex-Ohm', 'eth 0os superior: 1.4 -> 3.2 (n=4) — Larzuk = 5os (Obedience only)'],
    floor=['eth 5os normal: 0.17 -> 0.33 (n=20)', 'non-eth 4os normal: 0.2 -> 0.79 (n=7)'],
    ask_keys=['4os/eth/superior/15ed', '4os/eth/normal/15ed', '4os/eth/normal', '0os/eth/superior', '5os/eth/normal', '4os/noneth/normal'],
    why='Second name on Infinity/Pride/Obedience and third on Insight ("Ethereal Superior Thresher", runewords page June 2, 2026); WP-A weight 40 (25 mercenary tables). Faster than Giant Thresher (WSM -10 vs 0) with lower requirements (152 str) but lower damage (avg 76.5 vs 77 — nearly equal on average, base-items May 12, 2024) and only 5 max sockets, so "eth 5os" is the wrong roll for every S-tier polearm runeword and trades at 0.17-0.33 Ist while "eth 4os" trades at 2.6-8.1. Same ethereal/mercenary logic as Giant Thresher.',
    sources=S('rw', 'base', 'ias', 'sock', 'merc', 'dur', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-sacred-armor', base='Sacred Armor', cls='armor / body (mercenary)', wpb='sacred-armor', wpa='Sacred Armor',
    fills_keys=[],
    ilvl_sockets='3 / 4 / 4', stats='487-600 def, 232 str, qlvl 85, durability 60, medium',
    gates=['ethereal (Fortitude: "Ethereal Sacred Armor (Mercenary) - Any 850+ Defense Armor")', 'superior >=15 ED (asks 43.6 -> 57 vs 4 -> 5.9 for eth 4os normal)', 'sockets 4 or 0 (Larzuk gives 4 on any Sacred Armor at ilvl 41+); 3os is the dead roll'],
    keep=['eth 4os superior >=15 ED: 43.6 -> 57 Ist (n=5; def ~1036)', 'eth 0os superior >=15 ED: 57 -> 68.5 (n=2, thin) — Larzuk = 4os', 'eth 4os superior <15 ED: 8.6 -> 28.6 (n=8)'],
    sell=['eth 4os normal: 4.05 -> 5.9 (n=13) — Ohm-Lo', 'eth 0os normal: 2.6 -> 9.3 (n=9)', 'non-eth 4os/3os superior >=15 ED: 5.9 -> 18.6 / 5.9 -> 28.6 (n=7/6)'],
    floor=['non-eth 4os normal: 0.5 -> 1.0 (n=17)', 'eth 3os normal: 0.5 -> 0.84 (n=4)'],
    ask_keys=['4os/eth/superior/15ed', '0os/eth/superior/15ed', '4os/eth/superior', '4os/eth/normal', '0os/eth/normal', '4os/noneth/superior/15ed', '4os/noneth/normal', '3os/eth/normal'],
    why='Fortitude\'s mercenary base: "Ethereal Sacred Armor (Mercenary) - Any 850+ Defense Armor" (runewords page, June 2, 2026); the mercenary-mechanics page (Feb 10, 2026) shows "Fortitude Sacred Armor" in its Act 2 setups. WP-A weight 32 (19 mercenary tables). It has the highest base defense of any body armor (487-600, base-items May 12, 2024) and 232 str — unwearable for most characters, which is exactly why it is a mercenary-only base and why ethereal (+50% defense, no durability loss on a mercenary; durability + mercenary pages Feb 10, 2026) is the only version with a market. Sockets table (June 16, 2026): 3/4/4 — Larzuk gives 4, so a 0os eth superior 15 ED drop is worth as much as a 4os one.',
    sources=S('rw', 'merc', 'dur', 'base', 'sock', 'wpa', 'wpb', 'wpf'))

add(key='BS-berserker-axe', base='Berserker Axe', cls='weapon / axe', wpb='berserker-axe', wpa='Berserker Axe',
    fills_keys=['berserker-axe'],
    ilvl_sockets='4 / 5 / 6', stats='24-71 dmg (avg 47.5), WSM 0, 138 str / 59 dex, qlvl 85, durability 26',
    gates=['sockets: 5 (Beast, Doom, Death) or 6 (BotD); 4os is the dead roll unless Fortitude', 'superior >=15 ED (5os normal 0.79 -> 1.0 vs 5os superior 15 ED 34 -> 45.7)', 'ethereal only for BotD (Zod = Indestructible) or a mercenary; a character Beast/Doom base is non-eth'],
    keep=['5os superior >=15 ED non-eth: 34 -> 45.7 Ist (n=10)', 'eth 6os superior >=15 ED: 45.7 -> 51 (n=4) — BotD', 'eth 0os superior >=15 ED: 34 -> 45.7 (n=3) — Larzuk = 6os = BotD', '4os superior >=15 ED: 34 -> 68.5 (n=2, thin)'],
    sell=['eth 5os normal: 5.9 (n=3) — Lo', '5os superior <15 ED: 1 -> 7 (n=4)', 'eth 6os superior <15 ED: 1 -> 11.9 (n=2, thin)'],
    floor=['5os normal: 0.79 -> 1.0 (n=13)', '6os normal: 0.67 -> 0.9 (n=9)', 'eth 6os normal: 1.0 (n=5)', '3os/4os normal: 0.5 -> 0.6 / 1 -> 3.4'],
    ask_keys=['5os/noneth/superior/15ed', '6os/eth/superior/15ed', '0os/eth/superior/15ed', '5os/eth/normal', '5os/noneth/superior', '5os/noneth/normal', '6os/noneth/normal', '6os/eth/normal'],
    why='Beast and Doom list "Superior Berserker Axe", Death "Ethereal Superior Berserker Axe", Breath of the Dying "Ethereal Superior Berserker Axe" first (runewords page, June 2, 2026); WP-A weight 39 (9 character + 21 mercenary tables, Fortitude/BotD/Beast/Doom/Death). Fastest one-hand elite axe of the list (WSM 0, base-items May 12, 2024) with 6 max sockets and the lowest durability (26), which is why BotD\'s Zod rune (Indestructible — durability page Feb 10, 2026: "the easiest way to make something Indestructible is by socketing a Zod") makes the ethereal 6os version the chase item: +50% base damage with no downside. Sockets table (June 16, 2026): 4/5/6 — 6 is the Larzuk result, 5 must drop or be cubed (normal only, 16.67%).',
    sources=S('rw', 'base', 'dur', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-archon-plate', base='Archon Plate', cls='armor / body', wpb='archon-plate', wpa='Archon Plate',
    fills_keys=['archon-plate'],
    ilvl_sockets='3 / 4 / 4', stats='410-524 def, 103 str, qlvl 84, durability 60, light',
    gates=['sockets: 3 (Enigma, Dragon) vs 4 (Chains of Honor, Fortitude, Bramble); a 0os superior can only become 4os (Larzuk), never 3os', 'superior >=15 ED (3os superior 15 ED asks 22.8 -> 45.7; 3os normal 0.1 -> 1.0)', 'defense roll: 505-def 4os normal sold for 1 Mal 1 Um — a high roll does not rescue a normal 4os', 'ethereal only for a mercenary Fortitude (eth 4os normal 9.3 -> 9.3, n=3)'],
    keep=['3os superior >=15 ED: 22.8 -> 45.7 Ist (n=5) — Enigma base', '4os superior >=15 ED: 11.4 -> 20.7 (n=4) — CoH/Fortitude base', '0os superior >=15 ED: 11.4 -> 22.8 (n=8) — Larzuk to 4os', '3os superior <15 ED: 9.3 (n=3)', '4os eth normal/superior: 9.3 -> 9.3 / 22.8 (n=3 / 2)'],
    sell=['3os eth normal: 2 -> 2.6 (n=3)', '3os normal: 0.1 -> 1.0 (n=12) — about an Ist', '0os superior <15 ED: 1 -> 4 (n=11)'],
    floor=['4os normal non-eth: 0.08 -> 1.0 (n=23; q1 0.79) — Larzuk makes any Archon Plate 4os', '0os normal non-eth <=500 def: floor (Ohm asks are outliers, n=3, 2 offer)'],
    ask_keys=['3os/noneth/superior/15ed', '4os/noneth/superior/15ed', '0os/noneth/superior/15ed', '3os/noneth/superior', '4os/eth/normal', '4os/eth/superior', '3os/eth/normal', '3os/noneth/normal', '0os/noneth/superior', '4os/noneth/normal'],
    why='Enigma, Chains of Honor, Fortitude (character), Dragon and Bramble all list "Superior Archon Plate" first (runewords page, June 2, 2026); WP-A weight 41 — 25 of 26 S/A builds name one of these (mostly Enigma). Why this plate: base-items (May 12, 2024) gives 410-524 defense at 103 str and "Light" weight — the most defense per point of strength among body armors (Sacred Armor 487-600 needs 232 str, Dusk Shroud 361-467 needs 77, Wire Fleece 375-481 needs 111, Mage Plate 225-261 needs 55). Sockets table (June 16, 2026): 3/4/4 and Larzuk gives the maximum, so every Archon Plate can become 4os — that is the supply side of the 4os floor (n=23, 0.08 -> 1.0 Ist). A 3-socket drop cannot be manufactured from a superior base (cube refuses superior; Larzuk gives 4), which is why "3os superior 15 ED" asks twice what "4os superior 15 ED" asks. Enigma costs Jah + Ber (about 21 Ist on the WP-F ladder), so buyers spending that want the 15 ED roll on the base.',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-matriarchal-bow', base='Matriarchal Bow', cls='weapon / amazon bow', wpb='matriarchal-bow', wpa='Matriarchal Bow',
    fills_keys=[],
    ilvl_sockets='3 / 4 / 5', stats='20-47 dmg (avg 33.5), WSM -10, 87 str / 187 dex, qlvl 53; auto-mod +1-3 to Bow and Crossbow Skills (Amazon Only)',
    gates=['auto-mod +3 Bow skills', 'exactly 4 sockets for Ice/Faith/Harmony/Insight; 5 for Mist; 3 for Mania', 'superior >=15 ED'],
    keep=['+3 4os superior >=15 ED: 11.4 -> 45.7 Ist (n=9)', '+3 0os superior >=15 ED: 9.3 -> 28.6 (n=5) — Larzuk = 5os (Mist only) — buyer beware', '+3 5os superior >=15 ED: 9.3 -> 11.4 (n=6)'],
    sell=['+3 4os superior <15 ED: 4.05 -> 7.6 (n=6)', '+3 4os normal: 2 -> 2.6 (n=5)'],
    floor=['+3 5os normal: 0.67 -> 0.79 (n=22)'],
    ask_keys=['4os/noneth/superior/15ed/skill3', '0os/noneth/superior/15ed/skill3', '5os/noneth/superior/15ed/skill3', '4os/noneth/superior/skill3', '4os/noneth/normal/skill3', '5os/noneth/normal/skill3'],
    why='Ice lists "Superior Matriarchal Bow", Mist/Melody/Harmony/Insight/Faith/Brand name it too (runewords page, June 2, 2026); WP-A weight 40 but 25 of those are mercenary Insight tables where "any polearm" competes. Faster than Grand Matron Bow (WSM -10 vs +10; attack-speed page Feb 10, 2026) with lower damage (avg 33.5 vs 42, base-items May 12, 2024) and the same +1-3 Bow skills auto-mod; sockets 3/4/5 (sockets table June 16, 2026). Not searched on diablo2.io (budget).',
    sources=S('rw', 'base', 'ias', 'sock', 'wpa', 'wpb', 'wpf'))

add(key='BS-dusk-shroud', base='Dusk Shroud', cls='armor / body', wpb='dusk-shroud', wpa='Dusk Shroud',
    fills_keys=['dusk-shroud'],
    ilvl_sockets='3 / 4 / 4', stats='361-467 def, 77 str, qlvl 65, durability 20, light',
    gates=['sockets 3 (Enigma/Dragon) vs 4 (CoH/Fortitude); Larzuk makes any Dusk Shroud 4os', 'superior >=15 ED is the only thing that lifts it (3os superior 15 ED 11.4 -> 22.8 vs 3os normal 0.67 -> 0.79)', 'lowest str of the elite plates (77) — the reason to choose it over Archon Plate'],
    keep=['3os superior >=15 ED: 11.4 -> 22.8 Ist (n=3)', '4os superior >=15 ED: 5.9 -> 11.4 (n=5)'],
    sell=['0os superior >=15 ED: 0.79 -> 2.0 (n=14) — Larzuk = 4os', '3os eth normal/superior: 1 -> 3.4 / 1.4 -> 3.3 (n=2/2, thin) — mercenary Treachery/Stone', '4os superior <15 ED: 0.67 -> 1.2 (n=7)'],
    floor=['4os normal: 0.57 -> 0.79 (n=10)', '3os normal: 0.67 -> 0.79 (n=8)', 'eth 4os normal: 0.25 -> 0.79 (n=5)'],
    ask_keys=['3os/noneth/superior/15ed', '4os/noneth/superior/15ed', '0os/noneth/superior/15ed', '4os/noneth/superior', '3os/noneth/normal', '4os/noneth/normal', '4os/eth/normal'],
    why='Second name after Archon Plate on Enigma, Chains of Honor, Fortitude and Dragon; sole name for Prudence and "Ethereal Dusk Shroud (Mercenary)" for Stone (runewords page, June 2, 2026); WP-A weight 41. Base-items (May 12, 2024): 361-467 defense at 77 str — the lightest elite plate, chosen when the character cannot afford 103 str. It shares Archon Plate\'s socket rule (3/4/4, sockets table June 16, 2026) so every drop becomes 4os at Larzuk, and its lower defense means a plain 3os or 4os Dusk Shroud is the cheaper substitute of a plain Archon Plate: Pul-class asks (0.57-0.79 Ist).',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-phase-blade', base='Phase Blade', cls='weapon / sword', wpb='phase-blade', wpa='Phase Blade',
    fills_keys=['phase-blade'],
    ilvl_sockets='3 / 4 / 6', stats='31-35 dmg (avg 33), Indestructible, WSM -30, 25 str / 136 dex, qlvl 73',
    gates=['sockets: 5 (Grief, Kingslayer-class) or 6 (Last Wish, Unbending Will, Silence) or 4 (Phoenix, Hand of Justice) or 3 (Plague, Crescent Moon, Lawbringer, Mania, Hustle)', 'superior >=15 ED (5os superior 15 ED 11.4 -> 22.8 vs 5os normal 0.1 -> 0.67); superior also rolls +1-3 AR ("3ar" in the d2io guide row)', 'ethereal irrelevant: the base is Indestructible and has no durability'],
    keep=['5os superior >=15 ED: 11.4 -> 22.8 Ist (n=5) — Grief', '6os superior >=15 ED: 8.6 -> 9.3 (n=5) — Last Wish', '3os superior >=15 ED: 11.4 (n=2, thin)'],
    sell=['5os superior <15 ED: 0.67 -> 4.05 (n=3)', '0os superior >=15 ED: 2.6 -> 8.2 (n=4) — Larzuk = 6os'],
    floor=['5os normal: 0.1 -> 0.67 (n=18)', '6os normal: 0.1 -> 0.57 (n=17)', '4os normal: 0.2 -> 0.25 (n=12)'],
    ask_keys=['5os/noneth/superior/15ed', '6os/noneth/superior/15ed', '5os/noneth/superior', '0os/noneth/superior/15ed', '5os/noneth/normal', '6os/noneth/normal', '4os/noneth/normal'],
    why='Grief, Last Wish, Hand of Justice, Kingslayer, Phoenix (weapon), Unbending Will and Lawbringer list "Superior Phase Blade" (runewords page, June 2, 2026); WP-A weight 37 (18 character tables). Base-items (May 12, 2024): "Indestructible" in the durability column, WSM -30 — the largest negative weapon speed modifier in the list — and only 25 str; the attack-speed page (Feb 10, 2026) says a large negative WSM "adds directly to your Anim Rate". Because it never loses durability (durability page Feb 10, 2026: Phase Blades are excluded from durability), ethereal adds nothing and every Phase Blade drop is a candidate — which, together with the 3/4/6 socket table (June 16, 2026: Larzuk gives 6, so 6os is free), is why plain 5os/6os Phase Blades are a Lum-to-Um item and only the superior 15 ED roll trades for runes.',
    sources=S('rw', 'base', 'ias', 'dur', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-monarch', base='Monarch', cls='shield', wpb='monarch', wpa='Monarch',
    fills_keys=['monarch'],
    ilvl_sockets='3 / 3 / 4', stats='133-148 def, block 52/47/42 %, 156 str, qlvl 72, durability 86, light',
    gates=['4 sockets (Spirit/Phoenix are Socketed (4)); "Any Monarch always receives 4 Sockets" from Larzuk', 'superior >=15 ED is the whole premium (4os superior 15 ED 9.3 -> 17.1; 0os superior 15 ED 2.6 -> 11.4; 4os normal 0.42 -> 0.79)', 'non-eth (character shield; eth 0os superior 15 ED rows exist at 91+ but n=2)'],
    keep=['4os superior >=15 ED: 9.3 -> 17.1 Ist (n=4)', '0os superior >=15 ED: 2.6 -> 11.4 (n=14) — Larzuk it', '4os "normal" >=15 ED (mislabelled superior): 9.3 (n=3)'],
    sell=['0os superior <15 ED: 0.67 -> 4.05 (n=5)', '4os superior <15 ED: 1 -> 1.4 (n=2, thin)'],
    floor=['4os normal: 0.42 -> 0.79 (n=19)', '3os normal: 0.79 (n=5)', '0os normal: 0.42 (n=2)'],
    ask_keys=['4os/noneth/superior/15ed', '0os/noneth/superior/15ed', '4os/noneth/normal/15ed', '0os/noneth/superior', '4os/noneth/normal', '3os/noneth/normal'],
    why='Spirit and Phoenix (shield) list "Superior Monarch, Superior Sacred Targe" (runewords page, June 2, 2026); WP-A weight 39 (25 character tables — every non-Paladin caster). The sockets table (June 16, 2026) gives 4 sockets at ilvl 41+ to only three non-class shields — Aegis, Monarch, Ward — and Monarch is the lightest of them (156 str vs Aegis 219, Ward 185; base-items May 12, 2024), so it is the only 4-socket Spirit shield most characters can wear. The same page states "Any Monarch always receives 4 Sockets" from Larzuk: every Monarch drop is a Spirit base, supply is every Hell Monarch, and the plain 4os trades at Um-Mal. Only the superior 15 ED roll (5-15% ED on superior, base-items) is scarce.',
    sources=S('rw', 'sock', 'base', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-crystal-sword', base='Crystal Sword', cls='weapon / sword (normal tier)', wpb='crystal-sword', wpa='Crystal Sword',
    fills_keys=['crystal-sword'],
    ilvl_sockets='3 / 4 / 6', stats='5-15 dmg, WSM 0, 43 str, qlvl 11, durability 20',
    gates=['sockets: 4 (Spirit), 5 (Call to Arms), 3 (Plague/Crescent Moon/Lawbringer); Larzuk gives 4 only from an ilvl 26-40 drop (Normal Cow Level), 6 at ilvl 41+', 'superior >=15 ED only matters for physical users (5os superior 15 ED 8.2 -> 15.5, n=3)'],
    keep=['5os superior >=15 ED: 8.2 -> 15.5 Ist (n=3) — thin, asks'],
    sell=['4os superior >=15 ED: 2.6 -> 4.4 (n=4)', '3os superior >=15 ED: 1 -> 2.6 (n=5)'],
    floor=['5os normal: 0.2 -> 0.79 (n=27)', '5os superior <15 ED: 0.33 -> 1.0 (n=15)', '6os: 0.17 -> 0.84', '4os/3os normal: <=1.5 (n=2/2)'],
    ask_keys=['5os/noneth/superior/15ed', '4os/noneth/superior/15ed', '3os/noneth/superior/15ed', '5os/noneth/normal', '5os/noneth/superior', '6os/noneth/normal'],
    why='Spirit (sword), Call to Arms, Plague, Crescent Moon, Lawbringer, Sanctuary-class runewords list "Crystal Sword" (runewords page, June 2, 2026) — 26 character tables, WP-A weight 41, the joint-highest demand in the matrix. The white market is floor anyway: it is a normal-tier base (qlvl 11, 43 str, base-items May 12, 2024) that drops from Act 1 onward, and the sockets page (June 16, 2026) names Crystal Sword among the "very common items" from Normal Cow Level that "receive 4 Sockets from Larzuk" — a free Spirit base for anyone with the quest. Spirit and CtA are caster items whose base damage does not matter, so superior/ethereal add nothing ("Ethereal for style" on CtA). High demand met by unlimited supply = Um-Pul asks.',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-wire-fleece', base='Wire Fleece', cls='armor / body', wpb='wire-fleece', wpa=None,
    fills_keys=[],
    ilvl_sockets='3 / 4 / 4', stats='375-481 def, 111 str, qlvl 70, durability 32, light',
    gates=['superior >=15 ED', 'sockets 3 vs 4 as for Archon Plate'],
    keep=['3os superior >=15 ED: 4.05 -> 11.4 Ist (n=10)', '4os superior >=15 ED: 1.4 -> 9.3 (n=10)'],
    sell=['0os superior >=15 ED: 0.67 -> 3.3 (n=9)', 'eth 4os normal: 0.57 -> 1.0 (n=8)'],
    floor=['3os normal: 0.25 -> 0.84 (n=4)', '4os superior <15 ED: 0.25 -> 0.9 (n=6)'],
    ask_keys=['3os/noneth/superior/15ed', '4os/noneth/superior/15ed', '0os/noneth/superior/15ed', '4os/eth/normal', '3os/noneth/normal'],
    why='Not a maxroll "Recommended Base" for any runeword and named by no S/A guide (WP-A weight 0); the plan seed list carried it and WP-B priced 96 listings. Base-items (May 12, 2024): 375-481 defense at 111 str — between Dusk Shroud and Archon Plate in both, so it is a substitute Enigma/CoH base when neither is at hand. Prices track Dusk Shroud\'s.',
    sources=S('rw', 'base', 'sock', 'wpb', 'wpf'))

add(key='BS-mage-plate', base='Mage Plate', cls='armor / body (exceptional)', wpb='mage-plate', wpa='Mage Plate',
    fills_keys=['mage-plate'],
    ilvl_sockets='3 / 3 / 3', stats='225-261 def, 55 str, qlvl 60, durability 60, light',
    gates=['superior >=15 ED — the only thing with a price (3os superior 15 ED 0.79 -> 9.3; 3os normal 0.2 -> 0.73)', '3 sockets always: Larzuk gives 3 on any Mage Plate, so 0os = 3os', 'ethereal only for a mercenary Treachery ("Ethereal Mage Plate (Mercenary)"), thin'],
    keep=['3os superior >=15 ED: 0.79 -> 9.3 Ist (n=14; q1 5.9)', '0os superior >=15 ED: 4.05 -> 9.3 (n=13) — Larzuk it'],
    sell=['3os "normal" >=15 ED: 5.9 -> 8.2 (n=3)', '3os superior <15 ED: 0.67 -> 0.83 (n=5)'],
    floor=['3os normal: 0.2 -> 0.73 (n=31)', 'eth 0os: 0.83 -> 1.4 (n=3)'],
    ask_keys=['3os/noneth/superior/15ed', '0os/noneth/superior/15ed', '3os/noneth/normal/15ed', '3os/noneth/superior', '3os/noneth/normal', '0os/eth/normal'],
    why='"Superior Mage Plate" is the recommended base of thirteen 3-socket body-armor runewords — Enigma (second choice), Treachery, Duress, Smoke, Lionheart, Wealth, Hustle/Hysteria, Peace, Prudence-class, Bone, Rain, Enlightenment, Gloom (runewords page, June 2, 2026); WP-A weight 41 (19 character + 25 mercenary tables, mostly Treachery on the merc). Base-items (May 12, 2024): 225-261 defense at only 55 str, and the sockets table (June 16, 2026) gives 3/3/3 — every Mage Plate becomes 3os at Larzuk, so the plain 3os is floor (n=31, Um-Pul). The 15 ED superior roll is the premium because Enigma buyers pay Jah + Ber for the runes and the base is the only variable left.',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-flail', base='Flail', cls='weapon / mace (normal tier)', wpb='flail', wpa='Flail',
    fills_keys=['flail'],
    ilvl_sockets='3 / 4 / 5', stats='1-24 dmg, WSM -10, 41 str / 35 dex, qlvl 19, durability 30; auto-mod +50% Damage to Undead',
    gates=['sockets: 4 (Heart of the Oak), 5 (Call to Arms), 3 (Black); Larzuk gives 4 from an ilvl 26-40 drop, 5 at ilvl 41+', 'superior >=15 ED: only physical users care (4os superior 15 ED asks Ohm, n=5)'],
    keep=['4os superior >=15 ED: 4.05 Ist (n=5) — the only bucket above Ist'],
    sell=['0os eth superior >=15 ED: 11.4 (n=2, thin, "style" asks)'],
    floor=['all white 4os/5os: 0.08 -> 0.67 (n=53)', '5os superior: 0.17 -> 0.2 (n=13)', '4os normal: 0.08 -> 0.5 (n=10)'],
    ask_keys=['4os/noneth/superior/15ed', '4os/noneth/normal', '4os/noneth/superior', '5os/noneth/normal', '5os/noneth/superior', '5os/noneth/superior/15ed'],
    why='Heart of the Oak "Flail (Ethereal for style)", Call to Arms "Flail (Ethereal for style), Crystal Sword", Black "Flail" (runewords page, June 2, 2026); 26 character tables, WP-A weight 41. Same story as Crystal Sword: a normal-tier base (qlvl 19, 41 str, base-items May 12, 2024) that the sockets page (June 16, 2026) lists among the Normal Cow Level drops that "receive 4 Sockets from Larzuk", used for caster runewords where base damage is irrelevant. Unlimited supply, zero roll sensitivity — a Lum-Pul item.',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf', 'd2io'))

add(key='BS-colossus-voulge', base='Colossus Voulge', cls='weapon / polearm (mercenary)', wpb='colossus-voulge', wpa='Colossus Voulge',
    fills_keys=[],
    ilvl_sockets='3 / 4 / 4', stats='17-165 dmg (avg 91), WSM 0, 210 str / 55 dex, qlvl 64, durability 50',
    gates=['ethereal', 'sockets do not gate it: max 4 at ilvl 41+, so Larzuk turns any 0os eth Colossus Voulge into an Insight base', 'superior >=15 ED (thin, 45.7 n=2)'],
    keep=['eth 4os superior >=15 ED: 45.7 (n=2, thin)'],
    sell=['eth 0os superior: 0.67 -> 4.05 (n=6)', '4os non-eth "normal" >=15 ED: 4.05 -> 11.9 (n=2, thin)'],
    floor=['eth 4os normal: 0.6 -> 0.79 (n=37) — the standard Insight base sells for a Mal', 'eth 0os normal: 0.57 -> 0.79 (n=7)', 'non-eth 4os normal: 0.2 -> 0.79 (n=9)'],
    ask_keys=['4os/eth/superior/15ed', '0os/eth/superior', '4os/eth/normal', '0os/eth/normal', '4os/noneth/normal'],
    why='Insight lists "Ethereal Superior Colossus Voulge" first (runewords page, June 2, 2026) and 25 mercenary tables name Insight (WP-A weight 40) — the highest-demand polearm — yet it is the cheapest: base-items (May 12, 2024) gives it the highest average damage of the group (avg 91) but 210 str and a 4-socket maximum, and the sockets table (June 16, 2026) 3/4/4 means Larzuk makes every Colossus Voulge exactly 4os. No socket lottery, so supply of usable bases equals supply of ethereal drops: eth 4os normal asks 0.6-0.79 Ist (n=37). It cannot host Infinity\'s better polearm rolls (not a recommended Infinity base), which caps demand at Insight.',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf'))

add(key='BS-diadem', base='Diadem', cls='helm / circlet (elite)', wpb='diadem', wpa='Diadem',
    fills_keys=[],
    ilvl_sockets='1 / 2 / 3', stats='50-60 def, no str requirement, req level 64, qlvl 85, durability 20, "Magic Level 18"',
    gates=['3 sockets at ilvl 41+ only (1/2/3); Larzuk gives 3', 'white at all: WP-B found 196 of 200 listings magic/rare; white Diadem n=2'],
    keep=[],
    sell=['white 3os Diadem: n=2 thin — no band; the demand is met by "Any Barbarian Helmet or Druid Pelt with +x to Skills" (runewords page)'],
    floor=['no white market to speak of; the magic/rare Diadem market (2os rare 45.7 -> 171, n=68) is a WP-H/WP-I item'],
    ask_keys=['2os/noneth/rare', '2os/noneth/rare/15ed', '3os/noneth/magic', '2os/noneth/magic'],
    why='Ten helmet runewords list "Diadem" first — Lore, Bulwark, Temper, Ground, Cure, Wisdom, Dream, Flickering Flame, Hearth — followed by "Any Barbarian Helmet or Druid Pelt with +x to Skills" (runewords page, June 2, 2026), and the Fire Warlock guide names "Coven Diadem" (WP-A weight 41). Three reasons the white base still has no market: (1) substitutes — every one of those runewords also fits any 3-socket helm, and the runes are the cost (Dream = Io-Jah-Pul, Flickering Flame = Nef-Pul-Vex); (2) supply of whites is tiny — base-items (May 12, 2024) lists a "Magic Level 18" column for Diadem/Tiara only, and WP-B\'s pull shows 98% of Diadems listed are magic/rare; (3) the sockets table (June 16, 2026) gives 1/2/3, so only ilvl 41+ drops can be 3os at all. A white 3os Diadem is worth picking up for your own Dream/Coven but has no quotable band; a 2os or 0os white Diadem is Larzuk food.',
    sources=S('rw', 'base', 'sock', 'wpa', 'wpb', 'wpf'))

add(key='BS-targe', base='Targe', cls='shield / paladin (normal tier)', wpb='targe', wpa='Targe',
    fills_keys=[],
    ilvl_sockets='3 / 4 / 4', stats='8-12 def, 16 str, qlvl 4, Paladin; auto-mod All Resistances +5-45 OR ED/AR',
    gates=['45@ automod', 'superior >=15 ED', 'sockets 2 (Rhyme/Splendor) or 3 (Ancient\'s Pledge)'],
    keep=['45@ 0os superior: 4.05 -> 5.9 (n=4)', '45@ 3os superior: 2.6 -> 6 (n=3)'],
    sell=['40-44@ 3os superior: 0.67 (n=3)'],
    floor=['<45@ or unset res: floor; offer-heavy (superior 15 ED res-unset rows: 2 priced, 4-5 offer)'],
    ask_keys=['0os/noneth/superior/res45', '3os/noneth/superior/res45', '3os/noneth/superior/res40-44'],
    why='Rhyme and Splendor list "Bone Shield, Preserved Head, Targe" / "Bone Shield, Targe", Ancient\'s Pledge "Kite Shield, Large Shield" (runewords page, June 2, 2026); WP-A weight 32 from 19 character tables that use Rhyme/Splendor as leveling shields. Normal-tier (qlvl 4, base-items May 12, 2024) with the same +5-45 all-res auto-mod as Sacred Targe, so a 45@ Targe is a resist stick for a low-level Paladin; the market is thin and offer-heavy (WP-B). A self-found item, not a trade item.',
    sources=S('rw', 'base', 'wpa', 'wpb', 'wpf'))

add(key='BS-bone-shield', base='Bone Shield', cls='shield (normal tier)', wpb='bone-shield', wpa='Bone Shield',
    fills_keys=[],
    ilvl_sockets='2 / 2 / 2', stats='10-30 def, 25 str, qlvl 19',
    gates=['superior >=15 ED', '2 sockets (Rhyme/Splendor), always available via Larzuk'],
    keep=[], sell=['2os superior >=15 ED: 1.4 -> 3.7 (n=3)', '0os superior >=15 ED: 9.3 (n=3, odd asks)'],
    floor=['2os normal: 0.1 (n=1); 30 SC/NL listings site-wide — no real market'],
    ask_keys=['2os/noneth/superior/15ed', '0os/noneth/superior/15ed'],
    why='Rhyme and Splendor name it first (runewords page, June 2, 2026); WP-A weight 32 (19 leveling-shield mentions). Sockets table (June 16, 2026): 2/2/2 — every Bone Shield is a Rhyme base after Larzuk; normal-tier (qlvl 19). Pick it up for yourself, do not expect to sell it.',
    sources=S('rw', 'sock', 'base', 'wpa', 'wpb', 'wpf'))

add(key='BS-mask', base='Mask', cls='helm (normal tier)', wpb='mask', wpa='Mask',
    fills_keys=[],
    ilvl_sockets='3 / 3 / 3', stats='9-27 def, 23 str, qlvl 19',
    gates=['superior >=15 ED', '3 sockets (Wisdom); Larzuk gives 3'],
    keep=[], sell=['3os superior >=15 ED: 0.79 -> 4.05 (n=7)', '0os superior >=15 ED: 2 -> 3.3 (n=7)'],
    floor=['3os superior <15 ED: 0.57 -> 0.79 (n=4)'],
    ask_keys=['3os/noneth/superior/15ed', '0os/noneth/superior/15ed', '3os/noneth/superior'],
    why='Wisdom lists "Crown, Diadem, Carnage Helm" (runewords page, June 2, 2026); the Mask row in WP-A (weight 31) is inflated by 19 plain/gemmed mentions in leveling sections, not by a runeword. Normal-tier helm (qlvl 19, base-items May 12, 2024), 3/3/3 sockets. Asks are Ist-Ohm for the superior 15 ED roll only.',
    sources=S('rw', 'sock', 'base', 'wpa', 'wpb', 'wpf'))

add(key='BS-preserved-head', base='Preserved Head', cls='shield / necromancer head (normal tier)', wpb='preserved-head', wpa='Preserved Head',
    fills_keys=[],
    ilvl_sockets='2 / 2 / 2', stats='2-5 def, 12 str, qlvl 4, Necromancer; staff mods 0-3 different +x to Skill (Necromancer Only)',
    gates=['no clean white 2os listing exists (WP-B): the value is the necro +skills staff-mod, which is a blue-item question'],
    keep=[], sell=[], floor=['white: no market; 2os magic heads 22.8 -> 68.5 (n=12) are priced by their +skills'],
    ask_keys=['2os/noneth/magic'],
    why='Rhyme lists "Bone Shield, Preserved Head, Targe" (runewords page, June 2, 2026); WP-A weight 31 (18 Necromancer/Summoner leveling mentions). Base-items (May 12, 2024) lists "Staff Mods: 0-3 different +x to Skill (Necromancer Only)" for the head line — the reason no white one is listed: every head is priced by its skills. Not a base-value item.',
    sources=S('rw', 'base', 'wpa', 'wpb', 'wpf'))

add(key='BS-grimoire', base='Grimoire family (Grimoire / Possessed Grimoire / Blasphemous Grimoire and the 12 sibling bases)', cls='grimoire / warlock off-hand (RotW)', wpb='grimoire', wpa=None,
    fills_keys=[],
    ilvl_sockets='NOT in the maxroll sockets table (June 16, 2026) — max sockets unverified; Traderie shows 0/1/2-socket rows only, Vigilance needs 2',
    stats='new-items page (Feb 19, 2026): "Warlock-only offhands, and can be used alongside 2-handed weapons"; 15 bases in three tiers; no defense/str numbers published on the pages fetched',
    gates=['Warlock skill automods on every listing (WP-B: zero clean white grimoires across 198 + 87 + 73 site-wide listings) — the price is the skill roll, not the base', '2 sockets for Vigilance (Dol-Gul, D tier)', 'thin, offer-heavy market (6 of 11 2os Grimoire rows are "offer")'],
    keep=[], sell=['2os Grimoire (any automod): 0.67 -> 5.9 (n=11, 6 offer); superior 2os 4.05 -> 9.3 (n=4)', '2os Possessed: 1 -> 1 (n=5); Blasphemous 2os n=2 all offer'],
    floor=['0os / 1os with weak automods: offer or floor'],
    ask_keys=['2os/noneth/normal/affixed', '2os/noneth/superior/affixed', '0os/noneth/superior/affixed', '0os/noneth/normal/affixed'],
    extra_wpb=['possessed-grimoire', 'blasphemous-grimoire'],
    why='RotW added grimoires as a Warlock-only off-hand class (new-items page, Feb 19, 2026: Grimoire, Compendium, Tome, Codex, Old Book; Possessed Grimoire, Possessed Compendium, Dark Tome, Dark Codex, Burnt Text; Blasphemous Grimoire, Blasphemous Compendium, Occult Tome, Occult Codex, Forgotten Volume). The only runeword that fits is Vigilance (Dol-Gul; "Grimoires, Shields, Voodoo Heads, Auric Shields"), ranked D tier (tier list, Feb 18, 2026) and used by no S/A build (WP-A). WP-B: every grimoire listing carries Warlock skill automods, so there is no "white base" market; the maxroll sockets table has no grimoire row, so the socket maximum is "verify in-game". Thin market flag.',
    sources=S('new', 'tier', 'wpa', 'wpb', 'wpf', 'sock'))

add(key='BS-legend-spike', base='Legend Spike (Void/Ritual dagger; Fanged Knife as the alternative)', cls='weapon / dagger (RotW runewords)', wpb='legend-spike', wpa='Legend Spike',
    fills_keys=[],
    ilvl_sockets='2 / 3 / 3 (Blade-Legend Spike and Kris-Fanged Knife lines); Dagger/Dirk lines are 1/1/1 and can never hold Void or Ritual',
    stats='Legend Spike 31-47 dmg, WSM -10, 65 str / 67 dex, qlvl 85, durability 47; Fanged Knife 15-57, WSM -20, 42 str / 86 dex, qlvl 83',
    gates=['exactly 3 sockets (Void = Thul-Zod-Ist, Ritual = Amn-Shael-Ohm; 3 runes)', 'Warlock staff-mods on every listing (WP-B: 3os Legend Spike n=37, 17 offers; no clean white 3os dagger seen)', 'ethereal is pure upside for Void (Zod → Indestructible) and a drawback for Ritual (no Zod)'],
    keep=['3os Legend Spike with Warlock automods: 4.05 -> 17.3 Ist (n=37; 17 offer) — skill-priced', '3os Fanged Knife with automods: 0.67 -> 22.8 (n=42)'],
    sell=['0os automod daggers: 1 -> 11.4 (n=30) — Larzuk gives 3 at ilvl 41+'],
    floor=['Dagger/Dirk/Mithril Point/Bone Knife lines: max 1 socket, never a Void base'],
    ask_keys=['3os/noneth/normal/affixed', '3os/noneth/superior/affixed', '0os/noneth/normal/affixed'],
    extra_wpb=['fanged-knife'],
    why='Void (Daggers, Thul-Zod-Ist, B tier) and Ritual (Daggers, Amn-Shael-Ohm, F tier) are RotW runewords (new-items page Feb 19, 2026; tier list Feb 18, 2026); the Echoing Strike Warlock guide builds "Void Legend Spike" (WP-A, Aug 26, 2026 guide). The sockets page changelog (June 16, 2026) records "Release of RotW made the Blade-Legend Spike line of Daggers able to roll 3 sockets starting at ilvl 26", and its table gives Legend Spike, Stiletto, Fanged Knife, Kris 2/3/3 while Dagger, Dirk, Mithril Point, Bone Knife stay 1/1/1 — so only two dagger lines can ever hold a 3-rune runeword. Void\'s stats include "Indestructible" (new-items page), which makes an ethereal base free damage. Market caveat from WP-B: daggers now carry Warlock staff-mods, so the "white" market is a staff-mod market with heavy "offer" asks.',
    sources=S('new', 'tier', 'sock', 'base', 'wpa', 'wpb', 'wpf'))

# ---------- assemble ----------
out = {'_meta': {
    'package': 'WP-G white bases', 'date': DATE,
    'scope': 'Softcore / Non-Ladder / PC / Reign of the Warlock economy; Ist = 1.0 via pricing/data/wp-f-ladder.json',
    'ranking_rule': 'ordered by the median ask of the best clean-white bucket with >=3 priced listings in wp-b-prices.json (chase roll), demand weight (WP-A) shown alongside; bases WP-A/WP-B did not see are not listed',
    'asks_are_asks': 'every band is a Traderie asking price (WP-B, 2026-09-18); WP-B documents 3-30x ask inflation on chase rolls vs the diablo2.io guide; fills are the only sold prices and are quoted verbatim',
    'fill_conversion': 'rune fills converted with the WP-F ladder; non-rune fills (keys, essences) are quoted but not converted',
    'sockets_rule_once': 'maxroll sockets (June 16, 2026): a base gets at most the sockets its ilvl allows (table ilvl 1-25 / 26-40 / 41+; Normal difficulty caps at 3, Nightmare at 4, Hell uncapped); 1/3 of eligible drops have sockets; Larzuk gives a base its maximum for its ilvl; the cube recipes add a random 1..max to a NORMAL or ETHEREAL unsocketed base only (not superior, not low quality); runes need the EXACT socket count (runewords page); nothing reduces a socket count.',
    'sources': SRC,
    'd2io_searches': {k: {'file': v['file'], 'found': v['found'], 'flood_page': v['flood_page'], 'n_sold_rows': len(v['rows'])} for k, v in FILLS.items()},
}}
for i, b in enumerate(BASES, 1):
    fl, notes = fills_for(b['fills_keys'])
    entry = {
        'rank': i, 'base': b['base'], 'class': b['cls'],
        'demand': demand(b['wpa']) if b['wpa'] else demand('__none__', extra='not in wp-a-bases.json (no S/A guide names it; priced by WP-B from the plan seed list)'),
        'mechanics': {'sockets_by_ilvl_1-25_26-40_41+': b['ilvl_sockets'], 'base_stats': b['stats']},
        'gates': b['gates'],
        'thresholds': {'keep': b['keep'], 'sell': b['sell'], 'floor': b['floor']},
        'asks': asks(b['wpb'], b['ask_keys']) if b['wpb'] in B else {},
        'asks_scope_n': B[b['wpb']]['n_scope'] if b['wpb'] in B else None,
        'fills': fl, 'fills_notes': notes,
        'why': b['why'], 'sources': b['sources'],
    }
    for x in b.get('extra_wpb', []):
        entry['asks'][f'[{x}] all buckets n>=2'] = {k: bucket(x, k) for k, v in B[x]['buckets'].items() if v['n'] >= 2}
    out[b['key']] = entry

json.dump(out, open('pricing/data/wp-g-bases.json', 'w'), indent=1, ensure_ascii=False)
print('wrote pricing/data/wp-g-bases.json:', len(BASES), 'bases;', sum(len(v['rows']) for v in FILLS.values()), 'sold rows from', len(FILLS), 'searches')
for k, v in FILLS.items():
    print(f"  {k:18s} found={v['found']} flood={v['flood_page']} rows={len(v['rows'])}")
