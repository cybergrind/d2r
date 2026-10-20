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

WHITE = ['normal', 'superior']
LIFE = 256  # maxhp raw units a point
RESISTS = ['39:0', '41:0', '43:0', '45:0']
VOID_STAFFMODS = ['107:402', '107:389', '107:401']  # Abyss, Hex: Purge, Apocalypse
WARLOCK_TABS = ['188:56', '188:57', '188:58']
POLEARMS = ['Thresher', 'Giant Thresher', 'Cryptic Axe', 'Great Poleaxe', 'Colossus Voulge', 'Mancatcher']
VOID_BASES = ['Kriss', 'Blade', 'Cinquedeas', 'Stilleto', 'Fanged Knife', 'Legend Spike']
CIRCLETS = ['Circlet', 'Coronet', 'Tiara', 'Diadem']


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

# The rows (loot/design.md §4.2). `bases`: names resolved to codes; `asks`: a wp-b bucket (item slug, bucket).
ROWS: list[dict[str, Any]] = [
    # G3 merc eth polearms (PK-merc-polearms)
    {
        'id': 'merc-polearm-eth-4os-superior',
        'class': 'G3',
        'who': 'merc',
        'label': 'Insight / Infinity base: eth 4os Superior merc polearm',
        'bases': POLEARMS,
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
        'source': f'{PINDLE}:291; {WARLOCK}:166',
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
        'source': f'{WARLOCK}:139; {PINDLE}:286',
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
        'id': 'spirit-monarch-plain-4os',
        'class': 'G5',
        'who': 'warlock',
        'label': 'Spirit base: plain 4os Monarch',
        'bases': ['Monarch'],
        'qualities': ['normal'],
        'ground': [sockets(4)],
        'must': [sockets(4)],
        'asks': ('monarch', '4os/noneth/normal'),
        'source': f'{PINDLE}:288; {WARLOCK}:156',
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
        'source': f'{PINDLE}:289; inventory_tracking/macros/pickmode.py:75',
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
        'source': 'inventory_tracking/macros/pickmode.py:135',
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
        'source': f'{PRICING}:330; {PINDLE}:294; inventory_tracking/macros/pickmode.py:66',
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
        'source': 'inventory_tracking/macros/pickmode.py:68',
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
            at_least(['127:0', '83:0', '83:1', '83:2', '83:3', '83:4', '83:5', '83:6', '83:7'], 2),
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
]


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
