"""Regenerate loot/data/wants.json: the demand rows the loot layers read (loot/design.md §4.4).

Each row is written here once, with its source: a guide line (`guides/<file>.html:<line>`, checked to exist and, with
`quote`, to still say it), a `pricing/data/*.json` bucket, or the triage own-use rows (`pricing/data/triage/own.json`,
imported). Bases are named, never coded: the builder resolves each name to its items.txt code from the game data
(items/metadata.py) and checks it in the d2data dump (third-parties/d2data/json/{armor,weapons,misc}.json; AGENTS.md
rule 3). Asks come from pricing/data/wp-b-prices.json buckets (Traderie SC / NL / PC / RotW, dated in its _meta);
never from the web. A row without a source, a name the data lacks or a quote the guide no longer holds fails the
build.

Magic and better rows have no ground conditions: an unidentified item's stat list holds no affix and no socket count
(research R1, rca/2026-10-20/loot-m0-research.md), so they are picked by base and quality and judged once identified.

Stat ids are itemstatcost's (third-parties/d2data/json/itemstatcost.json): maxhp 7 (in 256ths), toblock 20,
armor ED 16, weapon max-damage ED 17, resists 39/41/43/45, life leech 60, mana leech 62, class skills 83 (layer 7
Warlock), faster block 102, FCR 105, staff mod 107 (layer = skill: Hex: Purge 389, Apocalypse 401, Abyss 402),
skill tab 188 (layer 56 Demon / 57 Eldritch / 58 Chaos, items/stat_constants.py SKILL_TABS), sockets 194.

Run: uv run --offline python -m inventory_tracking.loot.build_wants
"""

import html
import json
import re
import sys
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.items.metadata import metadata
from inventory_tracking.reports import publish


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).parent / 'data' / 'wants.json'
PRICES = 'pricing/data/wp-b-prices.json'
OWN = 'pricing/data/triage/own.json'
D2DATA = ('armor.json', 'weapons.json', 'misc.json')
PINDLE, WARLOCK, PRICING = 'guides/pindle-anya.html', 'guides/warlock.html', 'guides/pricing.html'
PRIMER = 'guides/pricing-primer.html'
RUNES = 'third-parties/d2data/json/runes.json'  # a runeword's item types (itype) and runes (= its socket count)
ARMOR = 'third-parties/d2data/json/armor.json'

WHITE = ['normal', 'superior']
LIFE = 256  # maxhp raw units a point
RESISTS = ['39:0', '41:0', '43:0', '45:0']
VOID_STAFFMODS = ['107:402', '107:389', '107:401']  # Abyss, Hex: Purge, Apocalypse
WARLOCK_TABS = ['188:56', '188:57', '188:58']
POLEARMS = ['Thresher', 'Giant Thresher', 'Cryptic Axe', 'Great Poleaxe', 'Colossus Voulge', 'Mancatcher']
# PK-merc-polearms names it too ("Matriarchal Spear (6)"): `amd`, item type `aspe` (Amazon Spear), not `spea`
MERC_SPEARS = [*POLEARMS, 'Matriarchal Spear']
# The merc's own bases are the fast ones (the player, 2026-10-20 ~13:20: "I'm not sure about colosus voulge speed wise,
# probably we need to keep only fast bases first"): weapons.json speed -10, Thresher and Giant Thresher (Great Poleaxe
# 0, Cryptic Axe and Colossus Voulge +10, Mancatcher -20 but a spear: no Insight, runes.json Insight itype pole/staf/
# miss). Mancatcher (-20, a spear) is the fast Infinity base (runes.json Infinity itype pole/spea; the player, ~13:25:
# "we will need good infinity base later"). The slower ones are market rows, kept by their worth alone
MERC_FAST = ['Thresher', 'Giant Thresher', 'Mancatcher']
MERC_SLOW = [base for base in MERC_SPEARS if base not in MERC_FAST]
AMAZON_BOWS = ['Grand Matron Bow', 'Matriarchal Bow']
BOW_SKILLS = '188:0'  # +N to Bow and Crossbow Skills: the Amazon's (class 0) first tab (items/stat_constants.py)
VOID_BASES = ['Kriss', 'Blade', 'Cinquedeas', 'Stilleto', 'Fanged Knife', 'Legend Spike']
CIRCLETS = ['Circlet', 'Coronet', 'Tiara', 'Diadem']
CLASS_SKILLS = [f'83:{layer}' for layer in range(8)]  # +N to a class's skills, layer = class (7 the Warlock)
SKILL_TREES = [f'188:{klass * 8 + tree}' for klass in range(8) for tree in range(3)]  # stat 188 layer class*8+tree
# The player, 2026-10-20 ~12:50: "I want to keep more monarch bases". The Spirit base row (a white or superior non-eth
# 4os Monarch) keeps copies until this many are owned in all (bases in the collection, no runeword: 2 on 2026-10-20,
# MSockB and MSockC); later copies only when better (Superior 15 ED on the ground; better ED once carried, keep.py)
SPIRIT_MONARCH_CAP = 6


def eth(value: bool = True) -> dict:
    return {'key': 'ethereal', 'equals': value}


def sockets(*counts: int) -> dict:
    return {'key': 'sockets', 'in': list(counts)}


def at_least(key: str | list[str], value: int, scale: int = 1) -> dict:
    found: dict[str, Any] = {'keys': key} if isinstance(key, list) else {'key': key}
    return found | {'min': value} | ({'scale': scale} if scale != 1 else {})


def spec(key: str, label: str, low: int, high: int, good: int | None = None, scale: int = 1) -> dict:
    found: dict[str, Any] = {'key': key, 'label': label, 'low': low, 'high': high}
    return found | ({'good': good} if good is not None else {}) | ({'scale': scale} if scale != 1 else {})


ED_ARMOR = spec('16:0', 'Enhanced Defense (superior)', 1, 15, good=15)
ED_WEAPON = spec('17:0', 'Enhanced Damage (superior)', 1, 15, good=15)
# A rare circlet's valuable third stat beside FCR and +skills (pricing.html §4 rare table, the Circlet row's "then two
# of": FRW, sockets, res, life, mana, str/dex; IAS cannot roll on a circlet). The floors follow the circlet affixes
# (d2data magicsuffix/magicprefix): life 30+ (of the Tiger 21-30, Mammoth 31-40, Colosuss 41-60), a resist 10+, str or
# dex 10+ (of the Giant, of Precision), mana 40+ (Wyrm's 41-60), a socket (Mechanist's 1-2), 30 FRW (of Speed)
CIRCLET_EXTRAS = [
    at_least('7:0', 30, LIFE),
    at_least(RESISTS, 10),
    at_least('0:0', 10),
    at_least('2:0', 10),
    at_least('9:0', 40, LIFE),
    at_least('194:0', 1),
    at_least('96:0', 30),
]


# The rows (loot/design.md §4.2). `bases`: names resolved to codes; `asks`: a wp-b bucket (item slug, bucket).
ROWS: list[dict[str, Any]] = [
    # G3 merc eth polearms (PK-merc-polearms)
    {
        'id': 'merc-polearm-eth-4os-superior',
        'class': 'G3',
        'who': 'merc',
        'label': 'Insight / Infinity base: eth 4os Superior fast merc polearm',
        'bases': MERC_FAST,
        'qualities': ['superior'],
        'ground': [eth(), sockets(4)],
        'must': [eth(), sockets(4)],
        'always_keep': True,
        'must_have': True,
        'matters': [ED_WEAPON],
        'asks': ('giant-thresher', '4os/eth/superior'),
        'source': f'{PINDLE}:291',
        'quote': 'Keep eth 4os Superior of any',
    },
    {
        'id': 'merc-polearm-eth-4os-superior-slow',
        'class': 'G3',
        'who': 'trade',
        'label': 'Infinity / Insight base, slow or a spear: eth 4os Superior (kept by its worth)',
        'bases': MERC_SLOW,
        'qualities': ['superior'],
        'ground': [eth(), sockets(4)],
        'must': [eth(), sockets(4)],
        'matters': [ED_WEAPON],
        'asks': ('giant-thresher', '4os/eth/superior'),
        'source': f'{PINDLE}:291',
        'quote': 'Keep eth 4os Superior of any',
    },
    {
        'id': 'merc-insight-gt-eth-4os',
        'class': 'G3',
        'who': 'merc',
        'label': 'Insight base: eth 4os Giant Thresher',
        'bases': ['Giant Thresher'],
        'qualities': ['normal'],
        'ground': [eth(), sockets(4)],
        'must': [eth(), sockets(4)],
        'always_keep': True,
        'must_have': True,
        'asks': ('giant-thresher', '4os/eth/normal'),
        'source': f'{PINDLE}:291; {WARLOCK}:166; {RUNES}:1639',
        'quote': 'eth 4os plain GT',
    },
    {
        'id': 'merc-polearm-eth-4os-plain',
        'class': 'G3',
        'who': 'trade',
        'label': 'eth 4os plain merc polearm (sell)',
        'bases': ['Thresher', 'Cryptic Axe', 'Great Poleaxe', 'Colossus Voulge', 'Mancatcher'],
        'qualities': ['normal'],
        'ground': [eth(), sockets(4)],
        'must': [eth(), sockets(4)],
        'asks': ('thresher', '4os/eth/normal'),
        'source': f'{PINDLE}:291',
        'quote': 'Sell: eth 4os plain Thresher',
    },
    {
        'id': 'merc-polearm-eth-0os-superior-15ed',
        'class': 'G3',
        'who': 'trade',
        'label': 'eth 0os Superior 15 ED Giant Thresher / Great Poleaxe',
        'bases': ['Giant Thresher', 'Great Poleaxe'],
        'qualities': ['superior'],
        'ground': [eth(), sockets(0), at_least('17:0', 15)],
        'must': [eth(), sockets(0), at_least('17:0', 15)],
        'matters': [ED_WEAPON],
        'asks': ('giant-thresher', '0os/eth/superior/15ed'),
        'source': f'{PINDLE}:291',
        'quote': 'eth 0os Superior 15 ED GT/GPA',
    },
    {
        'id': 'merc-polearm-eth-6os-superior-15ed',
        'class': 'G3',
        'who': 'trade',
        'label': 'eth 6os Superior 15 ED Giant Thresher / Great Poleaxe',
        'bases': ['Giant Thresher', 'Great Poleaxe'],
        'qualities': ['superior'],
        'ground': [eth(), sockets(6), at_least('17:0', 15)],
        'must': [eth(), sockets(6), at_least('17:0', 15)],
        'matters': [ED_WEAPON],
        'asks': ('giant-thresher', '6os/eth/superior/15ed'),
        'source': f'{PINDLE}:291',
        'quote': 'eth 6os Superior 15 ED GT/GPA',
    },
    # G4 merc / runeword armor (PK-elite-armor, PK-mage-plate; the merc fix, warlock.html §0.1)
    {
        'id': 'merc-fortitude-dusk-eth-4os',
        'class': 'G4',
        'who': 'merc',
        'label': 'Fortitude base: eth 4os Dusk Shroud',
        'bases': ['Dusk Shroud'],
        'qualities': WHITE,
        'ground': [eth(), sockets(4)],
        'must': [eth(), sockets(4)],
        'always_keep': True,
        'must_have': True,
        'asks': ('dusk-shroud', '4os/eth/normal'),
        'source': f'{WARLOCK}:139',
        'quote': 'Fortitude (El-Sol-Dol-Lo) in an eth 4os Dusk Shroud',
    },
    {
        'id': 'merc-coh-archon-eth-4os',
        'class': 'G4',
        'who': 'merc',
        'label': 'CoH / Fortitude base: eth 4os Archon Plate',
        'bases': ['Archon Plate'],
        'qualities': WHITE,
        'ground': [eth(), sockets(4)],
        'must': [eth(), sockets(4)],
        'always_keep': True,
        'must_have': True,
        'asks': ('archon-plate', '4os/eth/normal'),
        'source': f'{WARLOCK}:139; {PINDLE}:286; {RUNES}:353',
        'quote': 'Eth 4os Archon Plate asks 9.3',
    },
    {
        'id': 'archon-eth',
        'class': 'G4',
        'who': 'merc',
        'label': 'any eth Archon Plate',
        'bases': ['Archon Plate'],
        'qualities': WHITE,
        'ground': [eth()],
        'must': [eth()],
        'source': f'{PINDLE}:286',
        'quote': 'any eth Archon',
    },
    {
        'id': 'archon-superior-15ed',
        'class': 'G4',
        'who': 'runeword-base',
        'label': 'Enigma / CoH base: Superior 15 ED Archon Plate 0/3/4os',
        'bases': ['Archon Plate'],
        'qualities': ['superior'],
        'ground': [sockets(0, 3, 4), at_least('16:0', 15)],
        'must': [sockets(0, 3, 4), at_least('16:0', 15)],
        'matters': [ED_ARMOR],
        'asks': ('archon-plate', '0os/noneth/superior/15ed'),
        'source': f'{PINDLE}:286',
        'quote': 'Superior ≥15 ED in 3/4/0os Archon',
    },
    {
        'id': 'dusk-wire-superior-15ed',
        'class': 'G4',
        'who': 'runeword-base',
        'label': 'Superior 15 ED Dusk Shroud / Wire Fleece 3/4os',
        'bases': ['Dusk Shroud', 'Wire Fleece'],
        'qualities': ['superior'],
        'ground': [sockets(3, 4), at_least('16:0', 15)],
        'must': [sockets(3, 4), at_least('16:0', 15)],
        'matters': [ED_ARMOR],
        'source': f'{PINDLE}:286',
        'quote': '3os/4os Superior ≥15 ED Dusk/Wire',
    },
    {
        'id': 'enigma-mage-plate-superior-15ed',
        'class': 'G4',
        'who': 'runeword-base',
        'label': 'Enigma base: Superior 15 ED Mage Plate 0/3os',
        'bases': ['Mage Plate'],
        'qualities': ['superior'],
        'ground': [sockets(0, 3), at_least('16:0', 15)],
        'must': [sockets(0, 3), at_least('16:0', 15)],
        'matters': [ED_ARMOR],
        'asks': ('mage-plate', '3os/noneth/superior/15ed'),
        'source': f'{PINDLE}:287',
        'quote': 'keep only Superior ≥15 ED, 3os or 0os',
    },
    {
        'id': 'merc-sacred-armor-eth',
        'class': 'G4',
        'who': 'merc',
        'label': 'eth Sacred Armor 0/4os',
        'bases': ['Sacred Armor'],
        'qualities': WHITE,
        'ground': [eth(), sockets(0, 4)],
        'must': [eth(), sockets(0, 4)],
        'source': f'{PINDLE}:286',
        'quote': 'eth Sacred Armor (4os or 0os)',
    },
    # G5 white Monarch (PK-monarch)
    {
        'id': 'spirit-monarch-superior-15ed',
        'class': 'G5',
        'who': 'runeword-base',
        'label': 'Spirit base: Superior 15 ED Monarch 0/4os',
        'bases': ['Monarch'],
        'qualities': ['superior'],
        'ground': [sockets(0, 4), at_least('16:0', 15)],
        'must': [sockets(0, 4), at_least('16:0', 15)],
        'matters': [ED_ARMOR],
        'asks': ('monarch', '4os/noneth/superior/15ed'),
        'source': f'{PINDLE}:288',
        'quote': 'keep Superior ≥15 ED 4os or 0os',
    },
    {
        # The player, 2026-10-20 ~12:18: "also keep a base for spirit monarch". Spirit is Tal-Thul-Ort-Amn in any
        # shield (runes.json itype shld, 4 runes); not eth on the player's own shield (PK-eth: eth loses durability
        # and no vendor repairs it). ~12:50 "I want to keep more monarch bases": picked and kept until
        # SPIRIT_MONARCH_CAP are owned (`keep_up_to`: ground_judge.py, keep.py K3), later copies only when better;
        # a Superior 15 ED one is the previous row's
        'id': 'spirit-monarch-plain-4os',
        'class': 'G5',
        'who': 'warlock',
        'label': 'Spirit base (own use): non-eth 4os Monarch',
        'bases': ['Monarch'],
        'qualities': WHITE,
        'ground': [eth(False), sockets(4)],
        'must': [eth(False), sockets(4)],
        'keep_up_to': SPIRIT_MONARCH_CAP,
        'matters': [ED_ARMOR],
        'asks': ('monarch', '4os/noneth/normal'),
        'source': f'{PINDLE}:288; {WARLOCK}:156; {PINDLE}:285; {RUNES}:2982',
        'quote': 'plain 4os = self-use Spirit base',
    },
    # G6 magic Monarch (PK-blue-jeweler)
    {
        'id': 'monarch-of-deflecting-4os',
        'class': 'G6',
        'who': 'trade',
        'label': "Jeweler's Monarch of Deflecting (4os)",
        'bases': ['Monarch'],
        'qualities': ['magic'],
        'then': 'identify',
        'must': [sockets(4), at_least('20:0', 20), at_least('102:0', 30)],
        'always_keep': True,
        'must_have': True,
        'asks': ('_blues', "Jeweler's Monarch of Deflecting (4os magic, 30 FBR/20 block)"),
        'source': f'{PRICING}:331; {PINDLE}:296; third-parties/d2data/json/magicsuffix.json:2990',
        'quote': "Jeweler's Monarch of Deflecting — always sell",
    },
    {
        'id': 'monarch-jewelers-4os',
        'class': 'G6',
        'who': 'trade',
        'label': "Jeweler's Monarch (4os, any suffix)",
        'bases': ['Monarch'],
        'qualities': ['magic'],
        'then': 'identify',
        'must': [sockets(4)],
        'must_have': True,
        'asks': ('_blues', 'Monarch 4os magic, any affix (context)'),
        'source': f'{PINDLE}:296',
        'quote': "any Jeweler's Monarch/Archon",
    },
    {
        'id': 'monarch-of-deflecting-3os',
        'class': 'G6',
        'who': 'trade',
        'label': 'Monarch of Deflecting (3os)',
        'bases': ['Monarch'],
        'qualities': ['magic'],
        'then': 'identify',
        'must': [sockets(3), at_least('20:0', 20), at_least('102:0', 30)],
        'asks': ('monarch', '3os/noneth/magic'),
        'source': f'{PRICING}:199; third-parties/d2data/json/magicsuffix.json:2990',
        'quote': "Jeweler's (4os) + of Deflecting (Monarch)",
    },
    {
        'id': 'elite-armor-magic-identify',
        'class': 'G12',
        'who': 'trade',
        'label': 'every magic elite armor and Sacred Targe: identified, then judged',
        'bases': ['Archon Plate', 'Dusk Shroud', 'Wire Fleece', 'Sacred Armor', 'Sacred Targe'],
        'qualities': ['magic'],
        'then': 'identify',
        'source': f'{PINDLE}:296',
        'quote': 'ID every blue Archon / Dusk / Wire Fleece',
    },
    {
        'id': 'monarch-magic-identify',
        'class': 'G6',
        'who': 'trade',
        'label': 'every magic Monarch: identified, then judged',
        'bases': ['Monarch'],
        'qualities': ['magic'],
        'then': 'identify',
        'source': f'{PINDLE}:296',
        'quote': 'ID every blue Archon / Dusk / Wire Fleece',
    },
    # G7 Paladin shields (PK-pala-shields; macros/pickmode.py shield_base)
    {
        'id': 'sacred-targe-45-res',
        'class': 'G7',
        'who': 'trade',
        'label': 'Sacred Targe 45 all res',
        'bases': ['Sacred Targe'],
        'qualities': WHITE,
        'ground': [at_least(RESISTS, 45)],
        'must': [at_least(RESISTS, 45)],
        'matters': [spec('39:0', 'All Resistances', 30, 45, good=45)],
        'asks': ('sacred-targe', '0os/noneth/normal/res45'),
        'source': f'{PINDLE}:289',
        'quote': 'Keep Sacred Targe 45@ at any sockets/eth',
    },
    {
        'id': 'sacred-targe-40-res-3os',
        'class': 'G7',
        'who': 'trade',
        'label': 'Sacred Targe 40-44 all res, 3+os',
        'bases': ['Sacred Targe'],
        'qualities': WHITE,
        'ground': [at_least(RESISTS, 40), at_least('194:0', 3)],
        'must': [at_least(RESISTS, 40), at_least('194:0', 3)],
        'source': f'{PINDLE}:289; inventory_tracking/macros/pickmode.py:93',
        'quote': 'sell 40–44@',  # ruff: ignore[ambiguous-unicode-character-string] (the guide's dash)
    },
    {
        'id': 'sacred-rondache-45-4os',
        'class': 'G7',
        'who': 'trade',
        'label': 'Sacred Rondache 45 all res 4os',
        'bases': ['Sacred Rondache'],
        'qualities': WHITE,
        'ground': [at_least(RESISTS, 45), sockets(4)],
        'must': [at_least(RESISTS, 45), sockets(4)],
        'source': f'{PINDLE}:289',
        'quote': 'Rondache only 45@ 4os',
    },
    {
        'id': 'sacred-rondache-45-eth',
        'class': 'G7',
        'who': 'trade',
        'label': 'Sacred Rondache 45 all res eth',
        'bases': ['Sacred Rondache'],
        'qualities': WHITE,
        'ground': [at_least(RESISTS, 45), eth()],
        'must': [at_least(RESISTS, 45), eth()],
        'source': 'inventory_tracking/macros/pickmode.py:176',
        'quote': 'found.ethereal',
    },
    {
        'id': 'sacred-rondache-45-superior',
        'class': 'G7',
        'who': 'trade',
        'label': 'Superior Sacred Rondache 45 all res',
        'bases': ['Sacred Rondache'],
        'qualities': ['superior'],
        'ground': [at_least(RESISTS, 45)],
        'must': [at_least(RESISTS, 45)],
        'source': f'{PINDLE}:289',
        'quote': 'Rondache only 45@ 4os or Superior',
    },
    # G8 Void daggers (PK-rotw-daggers-grimoires; the player, 2026-10-17: 3os and a paid staff mod)
    {
        'id': 'void-dagger-3os-plus3',
        'class': 'G8',
        'who': 'warlock',
        'label': 'Void base: 3os elite-line dagger, +3 Abyss / Hex: Purge / Apocalypse',
        'bases': VOID_BASES,
        'qualities': WHITE,
        'ground': [sockets(3), at_least(VOID_STAFFMODS, 3)],
        'must': [sockets(3), at_least(VOID_STAFFMODS, 3)],
        'matters': [
            spec('107:389', '+3 Hex: Purge', 1, 3, good=3),
            spec('107:402', '+3 Abyss', 1, 3, good=3),
            spec('107:401', '+3 Apocalypse', 1, 3, good=3),
        ],
        'asks': ('legend-spike', '3os/noneth/normal/affixed'),
        'source': f'{PRICING}:330; {PINDLE}:294; inventory_tracking/macros/pickmode.py:84',
        'quote': 'a second 3os elite dagger with +3 Abyss / Chaos staff-mods',
    },
    {
        'id': 'void-dagger-0os-plus3-abyss',
        'class': 'G8',
        'who': 'warlock',
        'label': '0os elite-line dagger with +3 Abyss (Larzuk)',
        'bases': VOID_BASES,
        'qualities': WHITE,
        'ground': [sockets(0), at_least('107:402', 3)],
        'must': [sockets(0), at_least('107:402', 3)],
        'source': 'inventory_tracking/macros/pickmode.py:86',
        'quote': '0 socket +3 abyss',
    },
    # G9 Warlock class items (PK-blue-class-items; pricing.html §7)
    {
        'id': 'warlock-class-item-identify',
        'class': 'G9',
        'who': 'warlock',
        'label': 'every magic / rare dagger and grimoire: identified, then judged',
        'types': ['knif', 'grim'],
        'qualities': ['magic', 'rare'],
        'then': 'identify',
        'source': f'{PINDLE}:298',
        'quote': "Arch-Devil's / +3 Abyss-Chaos-Eldritch daggers & grimoires",
    },
    {
        'id': 'warlock-plus2-dagger-grimoire',
        'class': 'G9',
        'who': 'warlock',
        'label': '+2 Warlock dagger / grimoire',
        'types': ['knif', 'grim'],
        'qualities': ['magic', 'rare'],
        'must': [at_least('83:7', 2)],
        'source': f'{PRICING}:346; {PRICING}:349',
        'quote': '+2 to Warlock Skills',
    },
    {
        'id': 'warlock-grimoire-plus3-tree',
        'class': 'G9',
        'who': 'warlock',
        'label': 'magic grimoire +3 to a Warlock tree',
        'types': ['grim'],
        'qualities': ['magic'],
        'must': [at_least(WARLOCK_TABS, 3)],
        'source': f'{PRICING}:347',
        'quote': 'Magic grimoire +3 to a tree',
    },
    # G10 circlets (PK-blue-circlet; the Warlock helm, warlock.html:158)
    {
        'id': 'circlet-identify',
        'class': 'G10',
        'who': 'warlock',
        'label': 'every magic / rare circlet: identified, then judged',
        'bases': CIRCLETS,
        'qualities': ['magic', 'rare'],
        'then': 'identify',
        'source': f'{PINDLE}:297',
        'quote': 'ID every magic/rare Circlet / Coronet / Tiara / Diadem',
    },
    # The player, 2026-10-20 ~12:50: "I want to try to find rare helms (tiara, corona, etc) that are really good - fcr
    # + 2skills level + other valuable stats". Only circlets roll either on a rare (d2data: of the Magus 20 FCR
    # magicsuffix.json:3029 itype circ/orb/rod, of the Apprentice 10 FCR :3009; Arch-Devil's +2 Warlock
    # magicprefix.json:13176 rare, amul/circ, affix level 90; +2 to a Warlock tree rare: Dreadful Demon :13114,
    # TaintedAffix Eldritch :13043, Erratic Chaos :12974, the +3 trees magic only). A plain helm (Corona, Shako...,
    # type helm) rolls no FCR and only Barbarian Combat / Assassin Shadow tree prefixes: never a Warlock helm.
    # 20 FCR is the circlet's top FCR (the build sits at the 125 breakpoint, warlock.html:114). The scoped asks of
    # 2026-09-18/19 (pricing/data/appraisal-market.jsonl, one ask a seller): +2 Warlock + 20 FCR + a third stat 11.4
    # q1 -> 57.1 median (5 priced sellers), with nothing else 17.1 -> 22.8 (2), +2 Warlock without FCR 25.7 -> 34.3
    # (6, with a third stat), +2 Eldritch/Chaos/Demon + 20 FCR 11.4 (1) and 17.1 -> 22.8 (3, with a third stat)
    {
        'id': 'warlock-circlet-fcr-plus2-warlock-extra',
        'class': 'G10',
        'who': 'warlock',
        'label': 'Warlock helm, really good: rare circlet 20 FCR, +2 Warlock and a third stat',
        'bases': CIRCLETS,
        'qualities': ['rare', 'crafted'],
        'must': [at_least('105:0', 20), at_least('83:7', 2)],
        'any': CIRCLET_EXTRAS,
        'always_keep': True,
        'matters': [spec('7:0', 'Life', 1, 60, scale=LIFE), spec('39:0', 'Fire Resist', 1, 40)],
        'asks': ('diadem', '2os/noneth/rare'),
        'source': f'{PRICING}:233; {WARLOCK}:114; {WARLOCK}:158; third-parties/d2data/json/magicprefix.json:13176; '
        'third-parties/d2data/json/magicsuffix.json:3029',
        'quote': '20 FCR with +1 class skills',
    },
    {
        'id': 'warlock-circlet-fcr-plus2-eldritch-extra',
        'class': 'G10',
        'who': 'warlock',
        'label': 'Warlock helm, really good: rare circlet 20 FCR, +2 Eldritch (Echoing Strike) and a third stat',
        'bases': CIRCLETS,
        'qualities': ['rare', 'crafted'],
        'must': [at_least('105:0', 20), at_least('188:57', 2)],
        'any': CIRCLET_EXTRAS,
        'always_keep': True,
        'matters': [spec('7:0', 'Life', 1, 60, scale=LIFE), spec('39:0', 'Fire Resist', 1, 40)],
        'source': f'{PRICING}:233; third-parties/d2data/json/magicprefix.json:13043; '
        'third-parties/d2data/json/skilldesc.json:2575',
        'quote': '+2 to a skill tree',
    },
    {
        'id': 'warlock-circlet-fcr-plus2',
        'class': 'G10',
        'who': 'warlock',
        'label': 'Warlock helm: circlet 20 FCR with +2 Warlock or +3 Eldritch',
        'bases': CIRCLETS,
        'qualities': ['magic', 'rare', 'crafted'],
        'must': [at_least('105:0', 20)],
        'any': [at_least('83:7', 2), at_least('188:57', 3)],
        'always_keep': True,
        'matters': [spec('105:0', 'Faster Cast Rate', 10, 20, good=20)],
        'source': f'{WARLOCK}:158; {PRICING}:332; {PRICING}:233',
        'quote': 'Rare Diadem',
    },
    # The weaker rare circlets the evidence still prices at 1 Ist or more (pricing.html §4 rare table, Circlet row,
    # "Must-affixes": "+2 class skills alone; or 20 FCR with +1 class skills, +2 to a skill tree or 30 FRW"): kept
    # (never field-dropped: a want), not as always-keep rows. Every other rare circlet is junk (keep.py K8)
    {
        'id': 'rare-circlet-plus2-class',
        'class': 'G10',
        'who': 'trade',
        'label': 'rare circlet +2 class skills (any class, FCR or not)',
        'bases': CIRCLETS,
        'qualities': ['rare', 'crafted'],
        'must': [at_least(CLASS_SKILLS, 2)],
        'asks': ('tiara', '0os/noneth/rare'),
        'source': f'{PRICING}:233; {PRIMER}:482',
        'quote': '+2 class without FCR: 33 priced sellers the FCR-only gate missed, lower quartile 8 Ist',
    },
    {
        'id': 'rare-circlet-fcr-gate',
        'class': 'G10',
        'who': 'trade',
        'label': 'rare circlet 20 FCR with +1 class skills, +2 to a skill tree or 30 FRW',
        'bases': CIRCLETS,
        'qualities': ['rare', 'crafted'],
        'must': [at_least('105:0', 20)],
        'any': [at_least(CLASS_SKILLS, 1), at_least(SKILL_TREES, 2), at_least('96:0', 30)],
        'source': f'{PRICING}:233',
        'quote': '20 FCR with +1 class skills, +2 to a skill tree or 30 FRW',
    },
    # G11 rare rings and amulets (PK-blue-jewelry-gloves; pricing.html §6)
    {
        'id': 'ring-dual-leech-fcr',
        'class': 'G11',
        'who': 'trade',
        'label': 'ring: 10 FCR, life leech and mana leech',
        'bases': ['Ring'],
        'qualities': ['rare', 'crafted'],
        'must': [at_least('105:0', 10), at_least('60:0', 1), at_least('62:0', 1)],
        'always_keep': True,
        'matters': [spec('60:0', 'Life stolen', 1, 9), spec('62:0', 'Mana stolen', 1, 6)],
        'source': f'{PRICING}:230; {PRICING}:232',
        'quote': 'Ring (caster)',
    },
    {
        'id': 'warlock-ring-fcr-res-life',
        'class': 'G11',
        'who': 'warlock',
        'label': 'Warlock ring: 10 FCR, res and life',
        'bases': ['Ring'],
        'qualities': ['rare', 'crafted'],
        'must': [at_least('105:0', 10), at_least(RESISTS, 10), at_least('7:0', 1, LIFE)],
        'always_keep': True,
        'source': f'{WARLOCK}:164; {PRICING}:230',
        'quote': 'Rare Ring (10 FCR + res + life)',
    },
    {
        'id': 'warlock-amulet-plus2-fcr',
        'class': 'G11',
        'who': 'warlock',
        'label': 'Warlock amulet: +2 Warlock and 10 FCR',
        'bases': ['Amulet'],
        'qualities': ['magic', 'rare', 'crafted'],
        'must': [at_least('83:7', 2), at_least('105:0', 10)],
        'always_keep': True,
        'source': f'{WARLOCK}:163; {PRICING}:229',
        'quote': 'Forbidden Amulet of the Apprentice (+2 Warlock / 10 FCR magic amulet)',
    },
    {
        'id': 'rare-amulet-fcr-life-skills',
        'class': 'G11',
        'who': 'trade',
        'label': 'rare / crafted amulet with any FCR, any life or +2 skills',
        'bases': ['Amulet'],
        'qualities': ['rare', 'crafted'],
        'must': [],
        'any': [
            at_least('105:0', 1),
            at_least('7:0', 1, LIFE),
            # +2 all, class or tree skills: macros/keepers.py `amulet_keeper` counts the skill tree's 188 too (M6,
            # 2026-10-20: this row keeps what it keeps once the town decides by the keep rules)
            at_least(['127:0', *CLASS_SKILLS, *SKILL_TREES], 2),
        ],
        'always_keep': True,
        'source': 'inventory_tracking/macros/keepers.py:3',
        'quote': 'Rare amulets with +FCR, +2 skills, +life are good',
    },
    {
        'id': 'jewelry-identify',
        'class': 'G11',
        'who': 'trade',
        'label': 'every magic+ ring and amulet: identified',
        'bases': ['Ring', 'Amulet'],
        'qualities': ['magic', 'rare', 'crafted', 'set', 'unique'],
        'then': 'identify',
        'source': f'{PINDLE}:299',
        'quote': 'ID every rare ring/amulet',
    },
    # G12 expensive blues (pricing-primer §3.3; wp-b _blues)
    {
        'id': 'jewelers-archon-of-the-whale',
        'class': 'G12',
        'who': 'merc',
        'label': "Jeweler's Archon Plate of the Whale (4os, life 90-100)",
        'bases': ['Archon Plate'],
        'qualities': ['magic'],
        'then': 'identify',
        'must': [sockets(4), at_least('7:0', 90, LIFE)],
        'always_keep': True,
        'must_have': True,
        'matters': [spec('7:0', 'Life', 81, 100, good=90, scale=LIFE)],
        'asks': ('_blues', "Jeweler's Archon Plate of the Whale (4os magic, +life 90-100)"),
        'source': f'{PINDLE}:296',
        'quote': 'Archon of the Whale 90–100',  # ruff: ignore[ambiguous-unicode-character-string] (the guide's dash)
    },
    {
        'id': 'jewelers-elite-armor-4os',
        'class': 'G12',
        'who': 'trade',
        'label': "Jeweler's elite armor (4os magic Archon / Dusk / Wire / Sacred Armor)",
        'bases': ['Archon Plate', 'Dusk Shroud', 'Wire Fleece', 'Sacred Armor'],
        'qualities': ['magic'],
        'then': 'identify',
        'must': [sockets(4)],
        'must_have': True,
        'asks': ('_blues', 'Archon Plate 4os magic, any affix (context)'),
        'source': f'{PINDLE}:296',
        'quote': "Keep any Jeweler's (4os)",
    },
    {
        'id': 'warlock-skiller-gc',
        'class': 'G12',
        'who': 'warlock',
        'label': 'Warlock skiller grand charm',
        'bases': ['Grand Charm'],
        'qualities': ['magic'],
        'must': [at_least(WARLOCK_TABS, 1)],
        'source': f'{WARLOCK}:165; {PINDLE}:303',
        'quote': 'Warlock skillers (Chaos / Eldritch / Demon GCs)',
    },
    # G19 magic gloves (the player, 2026-10-20 ~13:30: "we want to identify magic gloves that can roll something like
    # 40ias + annother valuable roll, like skills / that is required for javazon or something like that"). From the game
    # data (d2data, itype glov, Equiv armo): the IAS suffixes on gloves are of Readiness 10 (magicsuffix.json:12399) and
    # of Alacrity 20 (:2936), one suffix group (7): 20 IAS is the most a magic glove rolls (40 is of Quickness, itype
    # mele, :2916: javelins). The tab prefixes on gloves (group 125, +1 / +2 / +3 at affix levels 20 / 40 / 60, +3 magic
    # only): Bow and Crossbow (Fletcher's / Bowyer's / Archer's, magicprefix.json:7476-7517), Passive and Magic
    # (:7537-7580), Javelin and Spear (Harpoonist's / Spearmaiden's / Lancer's, :7601-7642), Martial Arts (Shogukusha's
    # / Sensei's / Kenshi's, :9173-9218); stat 188, layer class*8+tree: 188:0 Bow, 188:1 Passive, 188:2 Javelin, 188:50
    # Martial Arts. The asks (pricing/data/triage/bands.json skill-gloves-20-ias, Gauntlets: 27 sellers, q1 3.32, median
    # 4.05, 2026-08-21..09-19; the guide's pull of 2026-09-19: +3 Jav 1-2 Jah, +3 Bow 4-22, +3 MA 4-11, +2 Jav 1, +3
    # Passive 1 Ist). +3 skills without IAS, IAS alone, +2 Passive or +2 Bow of Alacrity: vendor (the guide), dropped in
    # the field unless the KB prices the read at 1 Ist or more (keep.py JUNK_MAGIC, K5)
    {
        'id': 'gloves-magic-identify',
        'class': 'G19',
        'who': 'trade',
        'label': 'every magic glove: identified, then judged',
        'types': ['glov'],
        'qualities': ['magic'],
        'then': 'identify',
        'source': f'{PINDLE}:299',
        'quote': "Lancer's/Archer's/Kenshi's Gloves of Alacrity",
    },
    {
        'id': 'gloves-plus3-jav-bow-ma-alacrity',
        'class': 'G19',
        'who': 'trade',
        'label': "Lancer's / Archer's / Kenshi's Gloves of Alacrity (+3 Javelin, Bow or Martial Arts, 20 IAS)",
        'types': ['glov'],
        'qualities': ['magic'],
        'must': [at_least('93:0', 20), at_least(['188:0', '188:2', '188:50'], 3)],
        'always_keep': True,
        'source': f'{PRICING}:203; pricing/triage/import_affixed_rules.py:1003; '
        'pricing/data/triage/bands.json:1019434; third-parties/d2data/json/magicsuffix.json:2936; '
        'third-parties/d2data/json/magicprefix.json:7642',
        'quote': "Lancer's / Archer's / Kenshi's (+3 Jav / Bow / MA)",
    },
    {
        'id': 'gloves-plus3-passive-alacrity',
        'class': 'G19',
        'who': 'trade',
        'label': 'Gloves of Alacrity +3 Passive and Magic (20 IAS)',
        'types': ['glov'],
        'qualities': ['magic'],
        'must': [at_least('93:0', 20), at_least('188:1', 3)],
        'source': f'{PRICING}:203; third-parties/d2data/json/magicprefix.json:7580',
        'quote': 'or +3 Passive and Magic',
    },
    {
        'id': 'gloves-plus2-jav-ma-alacrity',
        'class': 'G19',
        'who': 'trade',
        'label': 'Gloves of Alacrity +2 Javelin or Martial Arts (20 IAS): a low check',
        'types': ['glov'],
        'qualities': ['magic'],
        'must': [at_least('93:0', 20), at_least(['188:2', '188:50'], 2)],
        'source': f'{PRICING}:203; pricing/triage/import_affixed_rules.py:708; '
        'third-parties/d2data/json/magicprefix.json:7621',
        'quote': '+2 Jav or +2 MA of Alacrity is a low CHECK',
    },
]


# G16 market-only white bases (Q7 of loot/design.md §8, the recommended answer the player took on 2026-10-20 ~12:00,
# "start all three": "Pick only rows >= 1 Ist with the exact socket count (superior >= 15 ED); never plain ones; never
# carried to town to be sold"). No build or merc of the player's uses them; the guide's Keep/Sell rows that are
# Superior >= 15 ED, each with its asks bucket at >= 1 Ist (wp-b, 2026-09-18). Plain ones (PK-elite-weapons' "Floor",
# PK-bows' "4os plain +3 GMB") are left.
MARKET_ROWS: list[dict[str, Any]] = [
    {
        'id': 'market-phase-blade-superior-15ed-5-6os',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED Phase Blade 5/6os (Grief, Last Wish)',
        'bases': ['Phase Blade'],
        'qualities': ['superior'],
        'ground': [sockets(5, 6), at_least('17:0', 15)],
        'must': [sockets(5, 6), at_least('17:0', 15)],
        'matters': [ED_WEAPON],
        'asks': ('phase-blade', '5os/noneth/superior/15ed'),
        'source': f'{PINDLE}:290',
        'quote': 'PB 5os or 6os',
    },
    {
        'id': 'market-berserker-axe-superior-15ed-5os',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED Berserker Axe 5os, not eth',
        'bases': ['Berserker Axe'],
        'qualities': ['superior'],
        'ground': [eth(False), sockets(5), at_least('17:0', 15)],
        'must': [eth(False), sockets(5), at_least('17:0', 15)],
        'matters': [ED_WEAPON],
        'asks': ('berserker-axe', '5os/noneth/superior/15ed'),
        'source': f'{PINDLE}:290',
        'quote': 'BA 5os non-eth, eth 6os, eth 0os',
    },
    {
        'id': 'market-berserker-axe-eth-superior-15ed-0-6os',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED eth Berserker Axe 0/6os',
        'bases': ['Berserker Axe'],
        'qualities': ['superior'],
        'ground': [eth(), sockets(0, 6), at_least('17:0', 15)],
        'must': [eth(), sockets(0, 6), at_least('17:0', 15)],
        'matters': [ED_WEAPON],
        'asks': ('berserker-axe', '6os/eth/superior/15ed'),
        'source': f'{PINDLE}:290',
        'quote': 'BA 5os non-eth, eth 6os, eth 0os',
    },
    {
        'id': 'market-colossus-blade-superior-15ed-5os',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED Colossus Blade 5os',
        'bases': ['Colossus Blade'],
        'qualities': ['superior'],
        'ground': [sockets(5), at_least('17:0', 15)],
        'must': [sockets(5), at_least('17:0', 15)],
        'matters': [ED_WEAPON],
        'asks': ('colossus-blade', '5os/noneth/superior/15ed'),
        'source': f'{PINDLE}:290',
        'quote': 'CB 5os, or eth 0/5/6os',
    },
    {
        'id': 'market-colossus-blade-eth-superior-15ed-0-6os',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED eth Colossus Blade 0/5/6os',
        'bases': ['Colossus Blade'],
        'qualities': ['superior'],
        'ground': [eth(), sockets(0, 5, 6), at_least('17:0', 15)],
        'must': [eth(), sockets(0, 5, 6), at_least('17:0', 15)],
        'matters': [ED_WEAPON],
        'asks': ('colossus-blade', '0os/eth/superior/15ed'),
        'source': f'{PINDLE}:290',
        'quote': 'CB 5os, or eth 0/5/6os',
    },
    {
        'id': 'market-amazon-bow-superior-15ed-4os-plus3',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED +3 Bow skills Grand Matron / Matriarchal Bow 4os',
        'bases': AMAZON_BOWS,
        'qualities': ['superior'],
        'ground': [sockets(4), at_least('17:0', 15), at_least(BOW_SKILLS, 3)],
        'must': [sockets(4), at_least('17:0', 15), at_least(BOW_SKILLS, 3)],
        'matters': [ED_WEAPON],
        'asks': ('grand-matron-bow', '4os/noneth/superior/15ed/skill3'),
        'source': f'{PINDLE}:292',
        'quote': 'Keep 4os Superior ≥15 ED +3 (either)',
    },
    {
        'id': 'market-matriarchal-bow-superior-15ed-0os-plus3',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED +3 Bow skills Matriarchal Bow 0os',
        'bases': ['Matriarchal Bow'],
        'qualities': ['superior'],
        'ground': [sockets(0), at_least('17:0', 15), at_least(BOW_SKILLS, 3)],
        'must': [sockets(0), at_least('17:0', 15), at_least(BOW_SKILLS, 3)],
        'matters': [ED_WEAPON],
        'asks': ('matriarchal-bow', '0os/noneth/superior/15ed/skill3'),
        'source': f'{PINDLE}:292',
        'quote': '0os Superior 15 ED +3 Mat Bow',
    },
    {
        'id': 'market-grand-matron-bow-superior-15ed-5os-plus3',
        'class': 'G16',
        'who': 'trade',
        'label': 'Superior 15 ED +3 Bow skills Grand Matron Bow 5os (sell)',
        'bases': ['Grand Matron Bow'],
        'qualities': ['superior'],
        'ground': [sockets(5), at_least('17:0', 15), at_least(BOW_SKILLS, 3)],
        'must': [sockets(5), at_least('17:0', 15), at_least(BOW_SKILLS, 3)],
        'matters': [ED_WEAPON],
        'asks': ('grand-matron-bow', '5os/noneth/superior/15ed/skill3'),
        'source': f'{PINDLE}:292',
        'quote': '5os Superior ≥15 ED +3 GMB',
    },
]
ROWS += MARKET_ROWS


# The player's own-use bases (2026-10-20 ~12:15: "Also, I want to get some bases for what I personally want: - bis
# preferrably ethereal base for merc insight - best base for exile (4os, at least +40 all res, preferrably ethereal
# shield) for paladin - base for cure (3os) for merc - merc chain of honor base (archon plate? maybe ethereal, 4os)").
# Insight and Chains of Honor are the G3/G4 merc rows above (eth 4os Giant Thresher or any eth 4os Superior merc
# polearm; eth 4os Archon Plate); these add Exile and Cure. Kept, never field-dropped (a want: loot/api.py
# `droppable`); a later copy under 1 Ist only when better by the rolls that matter (keep.py K6), eth and non-eth
# being different items (value.py `comparable`).
OWN_BASES: list[dict[str, Any]] = [
    {
        'id': 'own-exile-paladin-shield-4os-40res',
        'class': 'G7',
        'who': 'runeword-base',
        'label': 'Exile base (own Paladin): Sacred Targe / Rondache 4os or 0os, all res 40+, eth preferred',
        'bases': ['Sacred Targe', 'Sacred Rondache'],
        'qualities': WHITE,
        'ground': [sockets(0, 4), at_least(RESISTS, 40)],
        'must': [sockets(0, 4), at_least(RESISTS, 40)],
        'matters': [spec('39:0', 'All Resistances', 30, 45, good=45), ED_ARMOR],
        'asks': ('sacred-targe', '4os/eth/normal/res45'),
        'source': f'{PRIMER}:372; {PINDLE}:289; {PINDLE}:285; {RUNES}:955',
        'quote': 'eth 45@ 45.7 → 63 (n=9, Exile)',
    },
    {
        # Cure is Shael-Io-Tal in a helm (runes.json itype helm, 3 runes); the merc's eth (PK-eth: "Ethereal gear is
        # preferred since it doesn't lose durability" in the merc sections). The elite 3-socket helms by defense
        # (armor.json): Corona 111-165 (str 174), Spired Helm 114-159 (192), Bone Visage 100-157 (106), Demonhead
        # 101-154 (102), all under the Act 2 merc's 204 str (warlock.html §0.1); 0os: Larzuk gives their maximum 3
        'id': 'own-merc-cure-helm-eth-3os',
        'class': 'G17',
        'who': 'merc',
        'label': 'Cure base (merc): eth 3os or 0os Corona / Spired Helm / Bone Visage / Demonhead',
        'bases': ['Corona', 'Spired Helm', 'Bone Visage', 'Demonhead'],
        'qualities': WHITE,
        'ground': [eth(), sockets(0, 3)],
        'must': [eth(), sockets(0, 3)],
        'matters': [ED_ARMOR],
        'source': f'{PINDLE}:480; {WARLOCK}:141; {PINDLE}:285; {RUNES}:496; {ARMOR}:11724',
        'quote': 'early merc helms (Bulwark/Temper/Ground/Cure/Hearth 3)',
    },
]
ROWS += OWN_BASES


@cache
def _bases() -> dict[str, list[tuple[str, str]]]:
    """Base name -> [(code, type)] from the game data the decoder uses."""
    found: dict[str, list[tuple[str, str]]] = {}
    for row in metadata()['bases'].values():
        found.setdefault(row['name'], []).append((row['code'], row['type']))
    return found


@cache
def _d2data_codes() -> dict[str, str]:
    """items.txt code -> name in the d2data dump."""
    codes = {}
    for name in D2DATA:
        data = json.loads((ROOT / 'third-parties/d2data/json' / name).read_text())
        for row in data.values() if isinstance(data, dict) else data:
            if isinstance(row, dict) and row.get('code'):
                codes[row['code']] = row.get('name', '')
    return codes


def codes_of(names: Iterable[str]) -> list[str]:
    """The items.txt codes of base names, each checked in the d2data dump; a name the data lacks fails."""
    codes = []
    for name in names:
        found = _bases().get(name)
        if not found:
            raise ValueError(f'base {name!r} is not in the item metadata')
        for code, _ in found:
            if _d2data_codes().get(code) != name:
                raise ValueError(f'base {name!r} code {code!r} is not {name!r} in the d2data dump')
            codes.append(code)
    return sorted(set(codes))


def _lines(path: str) -> list[str]:
    return (ROOT / path).read_text().splitlines()


def check_source(source: str, quote: str | None) -> None:
    """Every reference names a file and line (or anchor) that exists; `quote` is in the first one's lines."""
    if not source.strip():
        raise ValueError('a row without a source')
    first = True
    for reference in (part.strip() for part in source.split(';')):
        path, _, where = reference.partition(':')
        path, _, anchor = path.partition('#')
        if not (ROOT / path).exists():
            raise ValueError(f'source {reference!r}: no such file')
        lines = _lines(path)
        if where:
            number = int(where.split('-')[0])
            if not 0 < number <= len(lines):
                raise ValueError(f'source {reference!r}: no line {number}')
            if first and quote is not None:
                text = '\n'.join(lines[max(number - 3, 0) : number + 2])
                plain = html.unescape(re.sub(r'<[^>]+>', '', text))
                if quote not in text and quote not in plain:
                    raise ValueError(f'source {reference!r} no longer says {quote!r}')
        elif anchor and f'id="{anchor}"' not in '\n'.join(lines):
            raise ValueError(f'source {reference!r}: no anchor')
        first = False


def asks_of(reference: tuple[str, str] | None, prices: dict) -> dict | None:
    """The asks of a wp-b bucket (min and median ask, sellers, date) as the row's evidence."""
    if reference is None:
        return None
    item, bucket = reference
    observed = prices['_meta'].get('pulled')
    if item == '_blues':
        row = prices['_blues'][bucket]
        return {'min_ist': row['min_ist'], 'median_ist': row['median_ist'], 'n': row['n'], 'kind': 'asks',
                'observed': observed, 'source': f'{PRICES}#_blues/{bucket}'}  # fmt: skip
    row = prices[item]['buckets'][bucket]
    return {'min_ist': row['min_ist'], 'median_ist': row['median_ist'], 'n': row['n'], 'kind': 'asks',
            'observed': observed, 'source': f'{PRICES}#{item}/{bucket}'}  # fmt: skip


def built_row(row: dict[str, Any], prices: dict) -> dict[str, Any]:
    check_source(row['source'], row.get('quote'))
    out = {key: value for key, value in row.items() if key not in ('bases', 'asks', 'quote')}
    if 'bases' in row:
        out['codes'] = codes_of(row['bases'])
        out['bases'] = row['bases']
    out['asks'] = asks_of(row.get('asks'), prices)
    return out


def own_rows(own: dict) -> list[dict[str, Any]]:
    """The triage's own-use unique and set rows (pricing/data/triage/own.json) as wants: kept by name (their
    property conditions are Traderie property ids and are not translated here; a want only spares an item)."""
    rows = []
    for index, row in enumerate(own['rows']):
        if row['category'] not in ('uniques', 'sets') or not row.get('name'):
            continue
        conditions = row.get('conditions') or {}
        must = [eth(conditions['ethereal'])] if isinstance(conditions.get('ethereal'), bool) else []
        rows.append({
            'id': f'own-{index}-{re.sub(r"[^a-z0-9]+", "-", row["name"].lower()).strip("-")}', 'class': 'own',
            'who': 'merc' if 'merc' in row['label'].lower() else 'warlock', 'label': f'{row["label"]}: {row["name"]}',
            'names': [row['name']], 'qualities': ['unique' if row['category'] == 'uniques' else 'set'], 'must': must,
            'asks': None, 'source': f'{OWN}; {row["source"]}',
        })  # fmt: skip
    return rows


def build() -> dict[str, Any]:
    prices = json.loads((ROOT / PRICES).read_text())
    own = json.loads((ROOT / OWN).read_text())
    rows = [built_row(row, prices) for row in ROWS]
    for row in own_rows(own):
        check_source(row['source'], None)
        rows.append(row)
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate want ids')
    return {
        '_meta': {
            'built_by': 'uv run --offline python -m inventory_tracking.loot.build_wants',
            'design': 'inventory_tracking/loot/design.md §4.4',
            'asks': f'{PRICES} (Traderie asks SC/NL/PC/RotW, pulled {prices["_meta"].get("pulled")})',
            'own_use': f'{OWN} (reviewed {own.get("reviewed_at")})',
        },
        'rows': rows,
    }


def main() -> int:
    publish(OUTPUT, build())
    print(f'{OUTPUT}: {len(json.loads(OUTPUT.read_text())["rows"])} rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
