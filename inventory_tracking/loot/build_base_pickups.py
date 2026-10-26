"""Regenerate loot/data/base-pickups.json and rca/2026-10-23/base-pickups.md: the allowlist of the white and grey
(normal, superior) weapons and armor the loop picks up, each worth MIN_IST or more by dated repo evidence.

The player, 2026-10-23 ~00:50: "redo the home work, you must sytseematically collect each white/grey base that we're
going to pickup, every base must worth 4+ist at least / we need to pickup something like +45 all res, 4os sacret
target and so on. or 3os grey kris with +3 abyss (and, probably, even other synergy)"; ~17:20 on the base-price study
(rca/2026-10-23/base-prices-findings.md): "Sales-backed now" (the adds sales back now, the drops and the six
narrowings; the adds that only asks back held for review: eth 4os Archon asks said 9.3 Ist, sales 2.6), "Drop both" on
the two conflicts (Sacred Rondache 0os 45 res normal, Archon Staff 6os normal: sales decide); "I want to have one
place that decides pickups/value".

The evidence is one module's (pricing/knowledge/base_evidence.py, read through pricing/api.py `base_evidence`): fills,
asks and bids per facet from the 2026-10-23 Traderie pulls, and the KB's asks bands per plain key. The rule (`decide`),
per facet, never pooled with another facet:
1. MIN_FILLS fills or more decide: a median of MIN_IST or more passes, under it fails;
2. else MIN_BUYERS distinct buyers or more bidding MIN_IST pass;
3. else asks from MIN_SELLERS sellers or more with a median of MIN_IST pass, unless the facet has 1-2 fills all
   under MIN_IST (contested: fails); such asks under MIN_IST fail unless the fills' median holds MIN_IST;
4. else unproven: the entry's own older evidence stands.
Every entry records `decided_by`. A facet that passes on asks alone and no entry takes is `held` (not picked) with its
evidence, for a later ruling. A failing facet an entry takes is `denied` when it is atomic (plain facts, a res band,
or a staff mod alone), else the entry is narrowed here (RULED); `unresolved` lists any left (the tests want none).

Entries, as before the rule:
- a wants row of the ground read's classes (loot/ground_judge.py BASE_CLASSES, loot/data/wants.json): its own asks
  (`Want.asks`) or EVIDENCE, else the KB band of every plain fact combination it picks;
- the allowlist's own rows (CUSTOM, NARROWED: wants.json format, loot/wants.py `parse`);
- a KB key (base, quality, ethereal flag, sockets, ED grade) the KB's band prices exactly, split by wp-b's 15 ED
  buckets; then the facets: a key's own facet decides it.

Prices are the repo's, never the web. Run: uv run --offline python -m inventory_tracking.loot.build_base_pickups
"""

import argparse
import datetime
import json
from collections.abc import Iterator, Mapping, Sequence
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.game.records import VALUABLE, Drop, Rolls
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import base_floor, wants as want_rows
from inventory_tracking.loot.facts import (
    DAMAGE_PERCENT,
    DEFENSE_PERCENT,
    NORMAL,
    RESISTS,
    SINGLE_SKILL,
    SOCKETS,
    SUPERIOR,
    ItemFacts,
    Owner,
    base_of_code,
    from_drop,
)
from inventory_tracking.loot.wants import Want, parse
from inventory_tracking.reports import publish


__all__ = [
    'MIN_BUYERS',
    'MIN_FILLS',
    'MIN_IST',
    'MIN_SELLERS',
    'build',
    'decide',
    'facet_keys',
    'facet_row',
    'kb_band',
    'main',
    'markdown',
    'representatives',
]

MIN_IST = base_floor.PICKUP_IST
MIN_SELLERS = 3
MIN_FILLS = 3
MIN_BUYERS = 2  # distinct buyers bidding MIN_IST or more (the evidence's `buyers_ge4`: MIN_IST is 4)
SALES = frozenset(('fills', 'bids'))  # the passes taken now; a pass on asks alone is held (the player, 2026-10-23)
PERFECT_ED = base_floor.PERFECT_ED
REPORT = Path(__file__).parents[2] / 'rca' / '2026-10-23' / 'base-pickups.md'
QUALITIES = {NORMAL: 'normal', SUPERIOR: 'superior'}
CANDIDATES = 'rca/2026-10-23/base-candidates.md'  # the evidence sheet of 2026-10-23 (fills beat asks)
STUDY = 'rca/2026-10-23/base-prices-findings.md'  # the base-price study of 2026-10-23 (the facets' evidence)
RULING = 'the player, 2026-10-23 ~17:20: "Sales-backed now"'
VOID = ['kri', 'bld', '9kr', '9bl', '7kr', '7bl']  # wants.json void-dagger-3os-plus3 codes (d2data weapons)
WHITE_GREY = ['normal', 'superior']
RES = ['39:0', '41:0', '43:0', '45:0']  # fire, lightning, cold, poison resistance (loot/facts.py RESISTS)
# The facet's group -> the pickup class of a row the builder adds for it (the CUSTOM rows' own classes)
GROUP_CLASS = {'Sacred shields': 'G7', 'Void daggers': 'G8', 'Assassin claws': 'G20', 'Warlock off-hands': 'G20'}
GRADES = {'normal': ('normal', False), 'sup<15': ('superior', False), 'sup15': ('superior', True)}


@cache
def class_skills(klass: str) -> tuple[str, ...]:
    """The single-skill stat keys ('107:<skill>') of a class's skills, by the game data (items metadata skills)."""
    return tuple(f'{SINGLE_SKILL}:{skill}' for skill, row in metadata()['skills'].items() if row['class'] == klass)


def _second(klass: str, level: int = 2) -> dict[str, Any]:
    """A second staff mod of `klass` at `level` or more: the second best of its skills."""
    return {'keys': list(class_skills(klass)), 'min': level, 'count': 2}


def _fills(q1: float, median: float, n: int, observed: str, source: str, kind: str = 'fills') -> dict[str, Any]:
    return {'q1_ist': q1, 'median_ist': median, 'n': n, 'kind': kind, 'observed': observed, 'source': source}


# Rows whose own asks are missing or wrong, with the evidence rca/2026-10-23/base-candidates.md §1 gives (fills first)
EVIDENCE: dict[str, dict[str, Any]] = {
    'wand-plus3-bone-spear-bone-spirit': _fills(20.05, 22.8, 16, '2026-04-07..09-16',
                                                f'{CANDIDATES} §1a; pricing/raw/traderie/recent-20261009 wands'),
    'sacred-targe-40-res-3os': _fills(2.58, 9.32, 5, '2026-10-08..09',
                                      f'{CANDIDATES} §1b; recent-20261009/sacred-targe.json'),
    'dusk-wire-superior-15ed': _fills(1.43, 9.32, 9, '2026-09-18', f'{CANDIDATES} §1c: wp-b Wire Fleece 4os (the '
                                      'least of Wire 3os 11.4 n10, 4os 9.32 n9, Dusk 3os 22.8 n3, 4os 11.4 n5)',
                                      'asks'),
    'merc-sacred-armor-eth': _fills(4.05, 5.88, 11, '2026-09-18', f'{CANDIDATES} §1c: wp-b eth 4os normal (the least '
                                    'of eth 0os 9.32 n7, 4os 5.88 n11, superior eth 4os 28.6 n8)', 'asks'),
    'scepter-plus3-fist-of-the-heavens': _fills(4.05, 4.23, 4, '2026-10-09', f'{CANDIDATES} §1a/§5: FoH alone in 5os '
                                                '(with a second +3: 57.1, n3); recent-20261009 scepters'),
    'scepter-plus3-hammer-concentration': _fills(43.6, 91.0, 3, '2026-10-09', f'{CANDIDATES} §1a: fills 43.6, 57.1; '
                                                 'completed-listing asks n3 median 91', 'asks'),
    'barbarian-helm-3os-plus3-find-item': _fills(19.5, 31.5, 4, '2026-09-23', f'{CANDIDATES} §1a: KB asks', 'asks'),
    'sorceress-staff-4-5os-plus3-energy-shield': _fills(22.8, 34.3, 4, '2026-09-23',
                                                        f'{CANDIDATES} §1a: KB asks 5os (4os 22.8, 3 sellers)', 'asks'),
}  # fmt: skip
# Rows the allowlist takes in narrower form (CUSTOM) or not at all, with why (base-candidates.md §5)
EXCLUDED = {
    'merc-polearm-eth-4os-plain': 'eth 4os plain Cryptic Axe 1.0, Colossus Voulge 0.79, Mancatcher 2.0, Great Poleaxe '
                                  '3.90 Ist (§4): only Thresher passes (the KB key 7s8 eth 4os, 5.89 n15)',
    'targe-superior-45-res': 'Targe 45 res fills n5 median 1.0 Ist (§4; asks 5.88 n3: fills decide)',
    'void-dagger-3os-plus3': 'takes +3 Apocalypse alone (fills 1.0): replaced by the void-* rules below (§3)',
    'void-dagger-0os-plus3-abyss': 'replaced by void-0os-plus3-abyss (§1a evidence)',
    'void-dagger-0os-plus3-hex-purge': 'replaced by void-hex-purge-0-3os (§1a evidence)',
    'market-mask-superior-15ed-0-3os': '0os 3.32 Ist n6 (§4): replaced by mask-superior-15ed-3os',
    'market-crystal-sword-superior-15ed-4-5os': '5os only 2 priced listings (§2): replaced by '
                                                'crystal-sword-superior-15ed-4os',
    'market-bone-shield-superior-15ed-0-2os': 'only 2 priced listings (§2); 2os 1.43-3.66',
    'own-merc-cure-helm-eth-3os': 'only eth superior 15 ED Bone Visage / Demonhead are priced (§1c): '
                                  'replaced by cure-helm-eth-superior-15ed',
    'pelt-3os-plus3-paid': 'Armageddon and Fury unpriced: replaced by pelt-3os-plus3-hurricane-tornado-volcano',
    'sacred-rondache-45-superior': 'priced only superior 15 ED 4os (§1b): replaced by rondache-45-superior-15ed-4os',
    'own-merc-archon-eth-4os': 'own use, 1 kept: loot/base_floor.py OWN_USE picks it under its cap (eth 4os normal '
                               'fills n83 median 2.58; the player, 2026-10-25)',
}  # fmt: skip
KB_EXCLUDED = {
    '7h7/normal/eth/4os/ordinary': 'eth 4os plain Great Poleaxe 3.90 Ist n16 (§4, wp-b; triage 4.05 borderline)',
    '7h7/superior/noneth/6os/ordinary': 'thin: triage 4.24-5.89 n3, wp-b has only the 15 ED bucket (n3, 2.59 -> 5.89; '
    'the verifier, base-pickups-verify.md)',
}
# A pooled ordinary key (its band equal to its 15 ED twin's, no wp-b split) is kept when even the pool's lower quartile
# is this high (the coordinator, 2026-10-23: "we absolutely MUST NOT trash good items"); under it, left
POOLED_KEEP_IST = 10.0
VERIFY = 'rca/2026-10-23/base-pickups-verify.md'
PALADIN = [f'107:{skill}' for skill in range(96, 126)]  # the Paladin's skills (skills.json class 'pal', 96-125)
# The narrowing of wants rows: row id -> the allowlist rule replacing it (wants.json format: `id`, `label`, `ground`
# replacing the row's; `codes`, `qualities` when narrower; `evidence` for the row's own, else the first of `facets` the
# rule passes, else the row's asks). The verifier's (rca/2026-10-23/base-pickups-verify.md "entries broader than their
# evidence") and the base-price study's (RULING: rca/2026-10-23/base-prices-proposal.json `rule_changes`)
NARROWED: dict[str, dict[str, Any]] = {
    'own-exile-paladin-shield-4os-40res': {
        'id': 'exile-shield-eth-0-4os-40res',
        'label': 'eth Sacred Targe / Rondache 0os / 4os, all res 40+ (Exile)',
        'ground': [{'key': 'sockets', 'in': [0, 4]}, {'keys': RES, 'min': 40}, {'key': 'ethereal', 'equals': True}],
        'evidence': _fills(57.1, 74.2, 4, '2026-09-18', f'{VERIFY}: wp-b eth 4os 45 Targe; non-eth 40-44 Rondache '
                           '0.5-3.59 left (45 res non-eth: sacred-targe-45-res, rondache-45-*)', 'asks'),
    },
    'grimoire-white-plus3-paid': {
        'id': 'grimoire-2os-plus3-paid',
        # +3 Sigil: Death taken out (the rule, 2026-10-23: contested, asks n3 9.32 against one fill of 1.43)
        'label': 'White grimoire 2os +3 Summon Tainted / Consume / Bind Demon',
        'ground': [{'key': 'sockets', 'in': [2]}, {'keys': ['107:376', '107:381', '107:382'], 'min': 3}],
        'facets': ['tome-2os-plus3-bind-demon'],
    },
    'sacred-targe-40-res-3os': {
        'id': 'sacred-targe-40-res-exactly-3os',
        'label': 'Sacred Targe 40-44 all res, 3os',
        'ground': [{'keys': RES, 'min': 40}, {'key': 'sockets', 'in': [3]}],
        'evidence': _fills(2.58, 9.32, 5, '2026-10-08..09', f'{CANDIDATES} §1b; recent-20261009/sacred-targe.json '
                           '(3os; 4os 40-44 n1 2.59)'),
    },
    'scepter-plus3-fist-of-the-heavens': {
        'id': 'scepter-plus3-foh-and-paladin-2',
        'label': 'White War / Divine Scepter / Caduceus +3 FoH and a second Paladin skill +2',
        'ground': [{'key': '107:121', 'min': 3}, {'keys': PALADIN, 'min': 2, 'count': 2}],
        'evidence': _fills(5.88, 9.32, 9, '2026-09-24..10-08', f'{VERIFY}: FoH +3 with a companion n9 median 9.32 (FoH '
                           'alone n4 median 3.3: left); recent-20261009/{war,divine}-scepter.json'),
    },
    'claw-white-plus3-phoenix-strike': {
        'id': 'claw-3os-plus3-phoenix-strike',
        'label': 'White Greater / Runic Talons 3os +3 Phoenix Strike',
        'ground': [{'key': 'sockets', 'in': [3]}, {'key': '107:280', 'min': 3}],
        'facets': ['claw-3os-plus3-phoenix-strike'],
    },
    'claw-white-plus3-lightning-sentry': {
        'id': 'claw-3os-plus3-lightning-sentry',
        # RULING: only with a second claw mod >= +2 (alone: fills n8 median 1.79)
        'label': 'White Greater / Runic Talons 3os +3 Lightning Sentry and a second claw mod +2',
        'ground': [{'key': 'sockets', 'in': [3]}, {'key': '107:271', 'min': 3}, _second('ass')],
        'facets': ['claw-3os-plus3-lightning-sentry-plus2'],
    },
    'merc-polearm-eth-4os-superior-slow': {
        'id': 'merc-polearm-eth-4os-superior-poleaxe',
        'label': 'eth 4os Superior Great Poleaxe (Infinity / Insight)',
        'ground': [{'key': 'ethereal', 'equals': True}, {'key': 'sockets', 'in': [4]}],
        'codes': ['7h7'],
        'evidence': _fills(34.3, 34.3, 6, '2026-09-18', f'{VERIFY}: wp-b Great Poleaxe non-15 ED n6 (Cryptic Axe n1, '
                           'Colossus Voulge n1, Matriarchal Spear none: left)', 'asks'),
    },
    'grimoire-white-2os-plus3-abyss-apocalypse': {
        'id': 'grimoire-2os-plus3-abyss',
        # RULING: +3 Abyss only (+3 Apocalypse fills n6 median 1.0)
        'label': 'White grimoire 2os +3 Abyss',
        'ground': [{'key': 'sockets', 'in': [2]}, {'key': '107:402', 'min': 3}],
        'facets': ['tome-2os-plus3-abyss'],
    },
    'merc-coh-archon-eth-4os': {
        'id': 'merc-coh-archon-eth-4os-superior',
        # RULING: superior only (eth 4os normal fills n83 median 2.58 against asks n98 9.32)
        'label': 'CoH / Fortitude base: eth 4os Superior Archon Plate',
        'ground': [{'key': 'ethereal', 'equals': True}, {'key': 'sockets', 'in': [4]}],
        'qualities': ['superior'],
        'facets': ['archon-plate-eth-4os-sup<15', 'archon-plate-eth-4os-sup15'],
    },
    'merc-sacred-armor-eth': {
        'id': 'merc-sacred-armor-eth-no-normal-4os',
        # RULING: without the normal 4os (fills n34 median 2.58)
        'label': 'eth Sacred Armor 0os, or 4os Superior',
        'ground': [{'key': 'ethereal', 'equals': True}, {'key': 'sockets', 'in': [0, 4]},
                   {'either': [{'key': 'quality', 'in': ['superior']}, {'key': 'sockets', 'in': [0]}]}],
        'facets': ['sacred-armor-eth-0os-normal', 'sacred-armor-eth-0os-sup<15', 'sacred-armor-eth-4os-sup<15',
                   'sacred-armor-eth-4os-sup15'],
    },
    'enigma-mage-plate-superior-15ed': {
        'id': 'enigma-mage-plate-superior-15ed-3os',
        # RULING: 3os only (0os sup15 fills n7 median 2.58)
        'label': 'Enigma base: Superior 15 ED Mage Plate 3os',
        'ground': [{'key': 'sockets', 'in': [3]}, {'key': '16:0', 'min': 15}],
        'facets': ['mage-plate-3os-sup15', 'mage-plate-eth-3os-sup15'],
    },
}  # fmt: skip
# The allowlist's own rows (wants.json format, loot/wants.py `parse`), each with its evidence (or the first of its
# `facets` the rule passes)
CUSTOM: list[dict[str, Any]] = [
    {'id': 'void-3os-plus3-abyss', 'class': 'G8', 'label': 'Void base 3os +3 Abyss (any companion)',
     'codes': VOID, 'qualities': WHITE_GREY, 'ground': [{'key': 'sockets', 'in': [3]}, {'key': '107:402', 'min': 3}],
     'facets': ['dagger-3os-plus3-abyss-alone', 'dagger-3os-abyss3-plus2'],
     'evidence': _fills(2.58, 4.03, 16, '2026-09-17..10-09', f'{CANDIDATES} §3: +3 Abyss alone (the player named it); '
                        'with a second mod >= +2 n16 median 22.8')},
    {'id': 'void-hex-purge-0-3os', 'class': 'G8', 'label': 'Void base 0os / 3os +3 Hex: Purge',
     'codes': VOID, 'qualities': WHITE_GREY,
     'ground': [{'key': 'sockets', 'in': [0, 3]}, {'key': '107:389', 'min': 3}],
     'facets': ['dagger-3os-plus3-hex-purge-alone', 'dagger-0os-plus3-hex-purge-alone'],
     'evidence': _fills(14.6, 18.6, 8, '2026-09-14..10-09', f'{CANDIDATES} §3')},
    {'id': 'void-0os-plus3-abyss', 'class': 'G8', 'label': 'Void base 0os +3 Abyss (Larzuk)',
     'codes': VOID, 'qualities': WHITE_GREY, 'ground': [{'key': 'sockets', 'in': [0]}, {'key': '107:402', 'min': 3}],
     'facets': ['dagger-0os-plus3-abyss-alone'],
     'evidence': _fills(5.0, 6.9, 7, '2026-09-18', f'{CANDIDATES} §1a: KB asks 0os +3 Abyss; with a second mod '
                        '>= +2 fills n20 median 9.32', 'asks')},
    # RULING: only with a second staff mod >= +2 (alone: EB fills n9 median 1.43, Siphon 0.84 / 0.89, Defiler thin)
    {'id': 'void-3os-plus3-no-abyss', 'class': 'G8', 'label': 'Void base 3os +3 Eldritch Blast / Summon Defiler / '
     'Hex: Siphon and a second staff mod +2', 'codes': VOID, 'qualities': WHITE_GREY,
     'ground': [{'key': 'sockets', 'in': [3]}, {'keys': ['107:384', '107:377', '107:386'], 'min': 3}, _second('war')],
     'facets': ['dagger-3os-eb-def-siph3-plus2'],
     'evidence': _fills(7.06, 7.06, 3, '2026-09-14..10-09', f'{CANDIDATES} §3: the least of EB n4 8.23, SD n4 7.06, '
                        'Siphon n3 11.4')},
    {'id': 'mask-superior-15ed-3os', 'class': 'G16', 'label': 'Superior 15 ED Mask 3os (Wisdom)', 'codes': ['msk'],
     'qualities': ['superior'], 'ground': [{'key': 'sockets', 'in': [3]}, {'key': '16:0', 'min': 15}],
     'evidence': _fills(0.79, 4.05, 7, '2026-09-18', f'{CANDIDATES} §1c: wp-b; KB n7 median 4.05', 'asks')},
    {'id': 'crystal-sword-superior-15ed-4os', 'class': 'G16', 'label': 'Superior 15 ED Crystal Sword 4os',
     'codes': ['crs'], 'qualities': ['superior'], 'ground': [{'key': 'sockets', 'in': [4]}, {'key': '17:0', 'min': 15}],
     'evidence': _fills(2.58, 4.45, 4, '2026-09-18', f'{CANDIDATES} §1c: wp-b; KB n4 median 4.45', 'asks')},
    {'id': 'cure-helm-eth-superior-15ed', 'class': 'G17', 'label': 'eth Superior 15 ED Bone Visage / Demonhead 0/3os',
     'codes': ['uh9', 'usk'], 'qualities': ['superior'],
     'ground': [{'key': 'ethereal', 'equals': True}, {'key': 'sockets', 'in': [0, 3]}, {'key': '16:0', 'min': 15}],
     'evidence': _fills(11.4, 11.4, 4, '2026-09-23', f'{CANDIDATES} §1c: KB asks Demonhead n4 11.4 (Bone Visage n4 '
                        '34)', 'asks')},
    {'id': 'pelt-3os-plus3-hurricane-tornado-volcano', 'class': 'G20', 'label': 'White Druid pelt 3os +3 Hurricane / '
     'Tornado / Volcano', 'types': ['pelt'], 'qualities': WHITE_GREY,
     'ground': [{'key': 'sockets', 'in': [3]}, {'keys': ['107:250', '107:245', '107:244'], 'min': 3}],
     'evidence': _fills(97.0, 97.0, 6, '2026-09-18', f'{CANDIDATES} §1a: KB asks per mod on 3os: Tornado 97 n6, '
                        'Hurricane 148 n6, Volcano 228 n3', 'asks')},
    {'id': 'rondache-45-superior-15ed-4os', 'class': 'G7', 'label': 'Superior 15 ED Sacred Rondache 4os 45 all res',
     'codes': ['pac'], 'qualities': ['superior'],
     'ground': [{'keys': RES, 'min': 45}, {'key': 'sockets', 'in': [4]}, {'key': '16:0', 'min': 15}],
     'evidence': _fills(57.1, 68.5, 3, '2026-09-18', f'{CANDIDATES} §1b: wp-b', 'asks')},
    {'id': 'wand-plus3-poison-nova', 'class': 'G20', 'label': 'White wand +3 Poison Nova',
     'codes': ['bwn', 'gwn', '9bw', '9gw', '7bw', '7gw'], 'qualities': WHITE_GREY,
     'ground': [{'key': '107:92', 'min': 3}],
     'evidence': _fills(8.82, 11.4, 4, '2026-04-07..10-07', f'{CANDIDATES} §1a; recent-20261009 wands')},
    {'id': 'claw-3os-plus3-assassin-skills', 'class': 'G20', 'label': 'White Greater / Runic Talons 3os +3 Venom / '
     'Fade / Blade Fury / Blade Shield / Dragon Flight / Mind Blast', 'codes': ['9tw', '7tw'], 'qualities': WHITE_GREY,
     'ground': [{'key': 'sockets', 'in': [3]},
                {'keys': ['107:278', '107:267', '107:266', '107:277', '107:275', '107:273'], 'min': 3}],
     'evidence': _fills(8.6, 8.6, 3, '2026-09-23', f'{CANDIDATES} §1a: KB asks per mod on 3os n3-8, the least '
                        'Mind Blast 86; at the Greater Talons fill/ask ratio (fills 11.4 against asks 57-114, the '
                        'least 0.1): 86 x 0.1 = 8.6', 'asks x fill ratio')},
    {'id': 'gilded-shield-45-res', 'class': 'G7', 'label': 'Gilded Shield 45 all res', 'codes': ['pa9'],
     'qualities': WHITE_GREY, 'ground': [{'keys': RES, 'min': 45}],
     'evidence': _fills(2.19, 4.97, 8, '2026-04-05..10-07', f'{CANDIDATES} §1b; recent-20261009/gilded-shield.json')},
]  # fmt: skip
# Allowlist rules the player ruled out (RULING: "Drop both" on the conflicts; sales decide)
RULED_OUT = {
    'rondache-45-0os-normal': {
        'label': 'Sacred Rondache 0os 45 all res (Larzuk)',
        'class': 'G7',
        'why': 'the player, 2026-10-23 ~17:20, "Drop both": asks n11 median 4.05 against one fill of 2.0 (10-11); '
        f'sales decide (facet rondache-45res-0os-normal, {STUDY})',
    },
}


# -- the rule


def decide(fills: Mapping[str, Any], asks: Mapping[str, Any], bids: Mapping[str, Any]) -> tuple[str, str]:
    """The sales-first rule on one facet's evidence (pricing/knowledge/base_evidence.py records): (result,
    decided_by), result 'pass', 'fail' or 'unproven'; decided_by 'fills', 'bids', 'asks', 'contested' or 'thin'.
    Pure."""
    filled = fills.get('n') or 0
    if filled >= MIN_FILLS:
        return ('pass' if fills['median'] >= MIN_IST else 'fail'), 'fills'
    if (bids.get('buyers_ge4') or 0) >= MIN_BUYERS:
        return 'pass', 'bids'
    if (asks.get('sellers') or 0) >= MIN_SELLERS and asks.get('median') is not None:
        if asks['median'] >= MIN_IST:
            if filled and fills['max'] < MIN_IST:
                return 'fail', 'contested'
            return 'pass', 'asks'
        if not (filled and fills['median'] >= MIN_IST):
            return 'fail', 'asks'
    return 'unproven', 'thin'


def _entry_decided(evidence: Mapping[str, Any]) -> tuple[str, str]:
    """The rule on an entry's own record (q1_ist / median_ist / n / kind): fills when its kind says so, else asks."""
    median, n = evidence.get('median_ist'), evidence.get('n') or 0
    if median is None:
        return 'unproven', 'thin'
    if evidence.get('kind') == 'fills':
        return decide({'n': n, 'median': median, 'max': median}, {}, {})
    return decide({}, {'sellers': n, 'median': median}, {})


def kb_band(record: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """A KB band (the evidence's `kb`, exact fits) the allowlist counts: MIN_SELLERS sellers, and an ED pooled (a
    superior of an ordinary roll priced with the 15 ED ones) only when even its lower quartile holds MIN_IST (the eth
    Superior Sacred Armor 0os, 22.8-28.6 Ist over 10 sellers, 2026-10-04). Pure."""
    if record is None or (record.get('n') or 0) < MIN_SELLERS:
        return None
    if record.get('relaxed') and (record.get('q1_ist') or 0) < MIN_IST:
        return None
    return {name: value for name, value in record.items() if name != 'relaxed'}


# -- the facets as allowlist entries


def facet_keys(facet: Mapping[str, Any]) -> list[str] | None:
    """The plain keys a facet of plain facts is (one per code), None for a facet of a res band, staff mods, any
    ethereal flag or several socket counts."""
    sockets = facet.get('sockets') or ()
    if not facet['plain'] or facet['all_res'] or facet['grade'] not in GRADES or facet['ethereal'] is None:
        return None
    if len(sockets) != 1 or facet.get('skill_class'):
        return None
    rarity, perfect = GRADES[facet['grade']]
    return [base_floor.key(code, rarity, ethereal=facet['ethereal'], sockets=sockets[0], perfect=perfect)
            for code in facet['codes']]  # fmt: skip


def _ed_key(codes: Sequence[str]) -> str:
    found = {(base_of_code(code) or (0, {}))[1].get('category') for code in codes}
    return f'{DAMAGE_PERCENT if found == {"weapons"} else DEFENSE_PERCENT}:0'


def _class_of(group: str) -> str:
    return next((klass for head, klass in GROUP_CLASS.items() if group.startswith(head)), 'G16')


def facet_row(facet_id: str, facet: Mapping[str, Any]) -> dict[str, Any]:
    """The facet as an allowlist row (wants.json format): its codes, qualities and every condition it names."""
    grade = facet['grade']
    qualities = {'normal': ['normal'], 'white': WHITE_GREY}.get(grade, ['superior'])
    ground: list[dict[str, Any]] = []
    if facet.get('sockets') is not None:
        ground.append({'key': 'sockets', 'in': list(facet['sockets'])})
    if facet.get('ethereal') is not None:
        ground.append({'key': 'ethereal', 'equals': facet['ethereal']})
    if grade == 'sup<15':
        ground.append({'key': _ed_key(facet['codes']), 'max': PERFECT_ED - 1})
    elif grade == 'sup15':
        ground.append({'key': _ed_key(facet['codes']), 'min': PERFECT_ED})
    if facet.get('all_res'):
        low, high = facet['all_res']
        ground.append({'keys': RES, 'min': low} | ({'max': high} if high < 99 else {}))
    ground += [{'key': f'{SINGLE_SKILL}:{skill}', 'min': level} for skill, level in facet.get('skills_min') or ()]
    ground += [{'key': f'{SINGLE_SKILL}:{skill}', 'min': level, 'max': level}
               for skill, level in facet.get('skills_exact') or ()]  # fmt: skip
    if facet.get('skills_any_min'):
        ground.append({'either': [{'key': f'{SINGLE_SKILL}:{skill}', 'min': level}
                                  for skill, level in facet['skills_any_min']]})  # fmt: skip
    klass = facet.get('skill_class')
    if klass and facet.get('second') is not None:
        ground.append(_second(klass, facet['second']))
    if klass and facet.get('others_max') is not None:
        listed = (*facet.get('skills_min', ()), *facet.get('skills_exact', ()), *facet.get('skills_any_min', ()))
        named = {f'{SINGLE_SKILL}:{skill}' for skill, _ in listed}
        ground.append({'keys': [key for key in class_skills(klass) if key not in named], 'max': facet['others_max']})
    if klass and facet.get('best') is not None:
        ground.append({'keys': list(class_skills(klass)), 'min': facet['best'], 'max': facet['best']})
    return {'id': facet_id, 'class': _class_of(facet['group']), 'who': 'trade', 'label': facet['label'],
            'codes': list(facet['codes']), 'qualities': qualities, 'ground': ground, 'facet': facet_id}  # fmt: skip


def representatives(facet: Mapping[str, Any]) -> list[ItemFacts]:
    """One item per code of the facet's least facts (the lowest socket count, ED 5 for an ordinary superior, the
    res band's floor, each named staff mod at its level, every other at 0): what its entry must take. Pure but for
    the game data."""
    grade, klass = facet['grade'], facet.get('skill_class')
    found = []
    for code in facet['codes']:
        txt, base = base_of_code(code) or (0, {})
        sockets = (facet.get('sockets') or [0])[0]
        rolls = {f'{SOCKETS}:0': sockets}
        ed = {'sup<15': 5, 'sup15': PERFECT_ED, 'superior': 5}.get(grade, 0)
        if ed:
            rolls[_ed_key([code])] = ed
        if facet.get('all_res'):
            rolls |= {f'{stat}:0': facet['all_res'][0] for stat in RESISTS}
        for skill, level in (*(facet.get('skills_min') or ()), *(facet.get('skills_exact') or ())):
            rolls[f'{SINGLE_SKILL}:{skill}'] = max(rolls.get(f'{SINGLE_SKILL}:{skill}', 0), level)
        if facet.get('skills_any_min'):
            skill, level = facet['skills_any_min'][0]
            rolls.setdefault(f'{SINGLE_SKILL}:{skill}', level)
        others = [key for key in class_skills(klass) if key not in rolls] if klass else []
        if facet.get('second') is not None and others:
            rolls[others.pop(0)] = facet['second']
        if facet.get('best') is not None and others and not any(key in rolls for key in class_skills(klass or '')):
            rolls[others.pop(0)] = facet['best']
        found.append(ItemFacts(
            unit_id=0, code=code, base_type=base.get('type', ''), size=(1, 1),
            quality=NORMAL if grade in ('normal', 'white') else SUPERIOR, identified=True,
            ethereal=bool(facet.get('ethereal')), sockets=sockets, rolls=rolls, owner=Owner.LOOP, txt=txt or None,
            base_name=base.get('name', ''),
        ))  # fmt: skip
    return found


def _facet_evidence(facet_id: str, facet: Mapping[str, Any], decided_by: str, sources: Mapping[str, str]) -> dict:
    """An entry's evidence record from the facet that decides it (`decided_by`'s numbers first)."""
    fills, asks, bids = facet['fills'], facet['asks'], facet['bids']
    if decided_by == 'fills':
        record = {'q1_ist': fills.get('q1'), 'median_ist': fills.get('median'), 'n': fills['n'],
                  'observed': '..'.join(fills.get('dates') or ())}  # fmt: skip
    elif decided_by == 'bids':
        high = [offer for offer in bids.get('offers') or () if offer >= MIN_IST]
        record = {'q1_ist': min(high), 'median_ist': high[len(high) // 2], 'n': bids['buyers_ge4'],
                  'observed': '..'.join(bids.get('dates') or ())}  # fmt: skip
    else:
        record = {'q1_ist': asks.get('q1'), 'median_ist': asks.get('median'), 'n': asks.get('sellers') or 0,
                  'observed': '..'.join(asks.get('dates') or ())}  # fmt: skip
    kind = decided_by if decided_by in ('fills', 'bids') else 'asks'
    return record | {
        'kind': kind,
        'decided_by': decided_by,
        'facet': facet_id,
        'facts': facet['label'],
        'source': f'pricing/data/base-evidence.json facet {facet_id}: {sources.get(kind, "")}',
        'fills_n_median': [fills['n'], fills.get('median')],
        'asks_n_median': [asks.get('sellers') or 0, asks.get('median')],
        'bids_buyers_ge4': [bids.get('buyers') or 0, bids.get('buyers_ge4') or 0],
    }


# -- the entries as before the facets (the KB's and the wants rows' own evidence)


def _combos(base: Mapping[str, Any]) -> Iterator[tuple[int, bool, int, int]]:
    for quality in QUALITIES:
        for ethereal in (False, True):
            for sockets in range(int(base.get('max_sockets') or 0) + 1):
                for ed in (0,) if quality == NORMAL else (0, PERFECT_ED):
                    yield quality, ethereal, sockets, ed


def _drop(txt: int, base: Mapping[str, Any], quality: int, ethereal: bool, sockets: int, ed: int) -> Drop:
    weapon = base.get('category') == 'weapons'
    rolls = Rolls(sockets, ethereal=ethereal, damage=ed if weapon else 0, defense=0 if weapon else ed)
    return Drop(txt, 0.0, 0.0, base['name'], VALUABLE, prized=False, source='shown', txt=txt, quality=quality,
                rolls=rolls)  # fmt: skip


def _row_kb(row: Want, kb: Mapping[str, Any], bases: Mapping[str, Mapping[str, Any]]) -> tuple[dict | None, str]:
    """The least KB band over every plain fact combination `row` picks, and why none."""
    found, combos = [], 0
    for txt, base in bases.items():
        if base.get('category') not in ('weapons', 'armor') or (row.codes and base['code'] not in row.codes):
            continue
        if row.types and base.get('type') not in row.types:
            continue
        for quality, ethereal, sockets, ed in _combos(base):
            if row.picks(from_drop(_drop(int(txt), base, quality, ethereal, sockets, ed))) is not True:
                continue
            combos += 1
            rarity = QUALITIES[quality]
            named = base_floor.key(base['code'], rarity, ethereal=ethereal, sockets=sockets, perfect=ed >= PERFECT_ED)
            record = kb_band(kb.get(named))
            if record is None:
                return None, f'no exact band of {MIN_SELLERS}+ sellers for {rarity} {base["name"]} {sockets}os'
            found.append(record | {'facts': f'{rarity}{" eth" if ethereal else ""} {base["name"]} {sockets}os'})
    if not combos:
        return None, 'no plain facts it picks (a staff mod or resistance condition): no KB band prices it'
    return min(found, key=lambda record: record['median_ist']), ''


def _linked(entry: Mapping[str, Any], facets: Mapping[str, Any], decided: Mapping[str, tuple[str, str]],
            sources: Mapping[str, str]) -> dict[str, Any] | None:  # fmt: skip
    """The evidence of the first of an entry's `facets` the rule passes; None when none does. A facet it names that
    fails is a narrowing out of step with the evidence: raised."""
    found = None
    for facet_id in entry.get('facets') or ():
        if facet_id not in facets:
            continue
        result, by = decided[facet_id]
        if result == 'fail':
            raise ValueError(f'{entry["id"]}: its facet {facet_id} fails ({by}): narrow it')
        if result == 'pass' and found is None:
            found = _facet_evidence(facet_id, facets[facet_id], by, sources)
    return found


def _today(evidence: Mapping[str, Any], rows: Sequence[Want], bases: Mapping[str, Mapping[str, Any]],
           raw: Mapping[str, Mapping[str, Any]], decided: Mapping[str, tuple[str, str]]) -> dict[str, Any]:  # fmt: skip
    """The entries by their own evidence (the KB's bands, the wants rows' asks, CUSTOM, NARROWED), each decided by the
    rule; the facets they name refresh their evidence."""
    facets, sources = evidence.get('facets') or {}, evidence.get('sources') or {}
    allowed, dropped = {}, {}

    def judged(entry: dict[str, Any], own: Mapping[str, Any] | None, why: str = '') -> tuple[dict | None, str]:
        linked = _linked(entry, facets, decided, sources)
        if linked is not None:
            return linked, ''
        if not own:
            return None, why or 'no evidence'
        result, by = _entry_decided(own)
        if result != 'pass':
            said = f'median {own["median_ist"]} Ist (n={own["n"]}, {own.get("observed")})'
            return None, f'under {MIN_IST:g} Ist or unproven ({by}): {why or said}'
        return dict(own) | {'decided_by': by}, ''

    narrowed = []
    for row in rows:
        if row.id in NARROWED:
            rule = NARROWED[row.id]
            dropped[row.id] = {'label': row.label, 'class': row.klass, 'why': f'narrowed into {rule["id"]}'}
            asks = row.asks or {}
            own = rule.get('evidence') or ({
                'q1_ist': asks.get('min_ist'), 'median_ist': asks.get('median_ist'), 'n': asks.get('n'),
                'kind': asks.get('kind'), 'observed': asks.get('observed'), 'source': asks.get('source'),
            } if asks else None)  # fmt: skip
            kept = {k: v for k, v in raw[row.id].items() if k not in ('ground', 'must', 'asks', 'evidence', 'source')}
            narrowed.append(kept | {name: value for name, value in rule.items() if name != 'evidence'}
                            | {'narrows': row.id, 'evidence': own})  # fmt: skip
            continue
        if row.id in EXCLUDED:
            dropped[row.id] = {'label': row.label, 'class': row.klass, 'why': EXCLUDED[row.id]}
            continue
        asks = row.asks or {}
        if row.id in EVIDENCE:
            own, why = EVIDENCE[row.id], ''
        elif asks.get('median_ist') is not None and (asks.get('n') or 0) >= MIN_SELLERS:
            own = {
                'q1_ist': asks.get('min_ist'), 'median_ist': asks['median_ist'], 'n': asks['n'],
                'kind': asks.get('kind'), 'observed': asks.get('observed'), 'source': asks.get('source'),
            }  # fmt: skip
            why = ''
        else:
            own, why = _row_kb(row, evidence.get('kb') or {}, bases)
            if asks:
                why = f'its asks {asks.get("min_ist")}-{asks.get("median_ist")} Ist n={asks.get("n")}; {why}'
        record, why = judged({'id': row.id}, own, why)
        if record is not None:
            allowed[row.id] = {'label': row.label, 'class': row.klass, 'evidence': record,
                               'decided_by': record['decided_by']}  # fmt: skip
        else:
            dropped[row.id] = {'label': row.label, 'class': row.klass, 'why': why}
    custom = {}
    for entry in [*CUSTOM, *narrowed]:
        record, why = judged(entry, entry.get('evidence'))
        if record is None:
            dropped[entry['id']] = {'label': entry['label'], 'class': entry['class'], 'why': why}
            continue
        custom[entry['id']] = entry | {
            'who': entry.get('who', 'allowlist'), 'evidence': record, 'decided_by': record['decided_by'],
            'source': record.get('source') or '',
        }  # fmt: skip
    dropped |= RULED_OUT
    kb, kb_dropped = {}, {}
    triaged = {key: record for key, raw_record in (evidence.get('kb') or {}).items()
               if (record := kb_band(raw_record)) is not None}  # fmt: skip
    split = evidence.get('wpb') or {}
    for key, record in triaged.items():
        if key in KB_EXCLUDED or record['median_ist'] < MIN_IST:
            continue
        code, rarity, eth, sockets, grade = key.split('/')
        if rarity == 'superior' and grade == 'ordinary':
            # An ordinary superior's band pools the 15 ED listings (the verifier: twelve ordinary keys carry their
            # 15 ED twin's numbers): wp-b's ED split decides when it has the bucket, else a band equal to the twin's
            # is the twin's and gives the ordinary copy nothing
            twin = triaged.get(f'{code}/{rarity}/{eth}/{sockets}/perfect')
            if key in split:
                record = split[key]
                if record['median_ist'] < MIN_IST:
                    kb_dropped[key] = f'wp-b split by ED: {_said(record)} ({record["source"]})'
                    continue
            elif (
                twin is not None
                and all(twin[part] == record[part] for part in ('q1_ist', 'median_ist', 'n'))
                and (record.get('q1_ist') or 0) < POOLED_KEEP_IST
            ):
                kb_dropped[key] = f'the triage band pools the 15 ED copies ({_said(record)}), wp-b has no split'
                continue
        kb[key] = record | {'decided_by': 'asks'}
    for key, record in split.items():
        if key in kb or key in kb_dropped or key in KB_EXCLUDED or record['median_ist'] < MIN_IST:
            continue
        kb[key] = record | {'decided_by': 'asks'}  # a wp-b bucket of 4+ Ist the triage lacks (base-pickups-verify.md)
    return {'rows': allowed, 'custom': custom, 'kb': kb, 'kb_dropped': kb_dropped, 'dropped': dropped}


# -- the build


def _doc(report: Mapping[str, Any], rows: Sequence[Want]) -> tuple[Mapping, tuple, tuple]:
    """(the doc, its allowed rows, its denied rows) for base_floor.allowed_by."""
    return report, base_floor.allowed_rows(report, rows), base_floor.denied_rows(report)


def _picks(facts: Sequence[ItemFacts], doc: tuple[Mapping, tuple, tuple]) -> list[bool]:
    return [base_floor.allowed_by(item, *doc) is not None for item in facts]


def _held(facet_id: str, facet: Mapping[str, Any], keys: list[str] | None, decided_by: str,
          pooled: str | None = None) -> dict[str, Any]:  # fmt: skip
    why = (f'its least copy is facet {pooled}, which no sale passes: taking it would pool the companions\' sales with '
           'it (no pooling)' if pooled else f'asks only: held for review ({RULING}; asks run far above fills: eth 4os '
           'Archon asks 9.3 Ist, sales 2.6)')  # fmt: skip
    return {
        'label': facet['label'], 'group': facet['group'], 'codes': facet['codes'],
        **({'keys': keys} if keys else {'row': facet_row(facet_id, facet)}),
        'fills': facet['fills'], 'asks': facet['asks'], 'bids': facet['bids'], 'result': 'pass',
        'decided_by': decided_by, 'why': why,
    }  # fmt: skip


def _pooled(facet: Mapping[str, Any], facets: Mapping[str, Any], decided: Mapping[str, tuple[str, str]],
            held: Mapping[str, Any]) -> str | None:  # fmt: skip
    """The atomic facet (a staff mod alone, plain facts) a broader facet's least copy falls in when that one fails or
    is held: the broader facet's sales are its companions' (+3 Lightning Sentry with any companion fills n18 while
    alone it fills n8 at 1.79), so it is not taken whole. None else."""
    least = representatives(facet)
    for other_id, other in facets.items():
        if other is facet or not _atomic(other) or (decided[other_id][0] != 'fail' and other_id not in held):
            continue
        row = parse(facet_row(other_id, other) | {'source': ''})
        if any(row.applies(item) and row.picks(item) is True for item in least):
            return other_id
    return None


def _atomic(facet: Mapping[str, Any]) -> bool:
    """A facet no companion roll can make better: plain facts (a res band included) or a staff mod alone."""
    return facet['plain'] or facet.get('others_max') is not None


def build(
    evidence: Mapping[str, Any],
    rows: Sequence[Want],
    bases: Mapping[str, Mapping[str, Any]],
    raw: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """The allowlist from the evidence (pricing/knowledge/base_evidence.py), the wants rows of BASE_CLASSES `rows`,
    the item `bases` (metadata) and the raw wants rows `raw` by id (NARROWED)."""
    facets, sources = evidence.get('facets') or {}, evidence.get('sources') or {}
    decided = {facet_id: decide(facet['fills'], facet['asks'], facet['bids']) for facet_id, facet in facets.items()}
    report = _today(evidence, rows, bases, raw or {}, decided)
    kb, kb_dropped = report['kb'], report['kb_dropped']
    before = _doc(report | {'kb': dict(kb), 'kb_dropped': dict(kb_dropped)}, rows)  # what the entries took
    # 1. a key's own facet decides it: a fail takes it out, a pass refreshes its evidence
    for facet_id, facet in facets.items():
        result, by = decided[facet_id]
        for key in facet_keys(facet) or ():
            if result == 'fail':
                if kb.pop(key, None) is not None:
                    kb_dropped[key] = f'facet {facet_id} fails ({by}): {facet["label"]}'
            elif result == 'pass' and key in kb:
                kb[key] = _facet_evidence(facet_id, facet, by, sources)
    # 2. a pass no entry takes: added on sales, held on asks
    today = _doc(report, rows)
    held, added = {}, {}
    passes = [facet_id for facet_id in facets if decided[facet_id][0] == 'pass']
    for facet_id in sorted(passes, key=lambda found: not _atomic(facets[found])):  # the atomic first: `_pooled`
        facet, by = facets[facet_id], decided[facet_id][1]
        least = representatives(facet)
        if all(_picks(least, today)):
            continue
        keys = facet_keys(facet)
        pooled = None if _atomic(facet) else _pooled(facet, facets, decided, held)
        kept = all(_picks(least, before))  # a pass the entries took before a failing lower key went: kept
        if pooled is not None or not (by in SALES or kept):
            held[facet_id] = _held(facet_id, facet, keys, by, pooled)
        elif keys:
            for key in keys:
                kb[key] = _facet_evidence(facet_id, facet, by, sources)
                kb_dropped.pop(key, None)
        else:
            record = _facet_evidence(facet_id, facet, by, sources)
            added[facet_id] = facet_row(facet_id, facet) | {'evidence': record, 'decided_by': by,
                                                            'source': record['source']}  # fmt: skip
    report['custom'] |= added
    # 3. a fail an entry still takes: denied when atomic, else unresolved (an entry to narrow in RULED)
    taken = _doc(report, rows)
    denied, unresolved = {}, {}
    for facet_id, facet in facets.items():
        result, by = decided[facet_id]
        if result != 'fail' or not any(_picks(representatives(facet), taken)):
            continue
        record = _facet_evidence(facet_id, facet, by, sources)
        if not _atomic(facet):
            unresolved[facet_id] = {'label': facet['label'], 'decided_by': by, 'evidence': record}
            continue
        keys = facet_keys(facet)
        denied[facet_id] = facet_row(facet_id, facet) | {
            'evidence': record, 'decided_by': by, 'source': record['source'], 'plain': bool(keys),
            **({'keys': keys} if keys else {}),
        }  # fmt: skip
    report['denied'] = denied
    # 4. a pass the denials took from an entry (none expected: the facets the rule passes and fails are disjoint)
    final = _doc(report, rows)
    conflicts = []
    for facet_id, facet in facets.items():
        if decided[facet_id][0] != 'pass' or facet_id in held:
            continue
        least = representatives(facet)
        if any(was and not now for was, now in zip(_picks(least, taken), _picks(least, final), strict=True)):
            conflicts.append(facet_id)
    return {
        'built': datetime.date.today().isoformat(),
        'min_ist': MIN_IST,
        'min_sellers': MIN_SELLERS,
        'min_fills': MIN_FILLS,
        'min_buyers': MIN_BUYERS,
        'rule': f'per facet ({STUDY}): {MIN_FILLS}+ fills decide (median {MIN_IST:g}+ passes); else {MIN_BUYERS}+ '
        f'buyers bidding {MIN_IST:g}+ pass; else asks from {MIN_SELLERS}+ sellers at a median of {MIN_IST:g}+ pass '
        f'unless 1-2 fills all sit under {MIN_IST:g} (contested: fails). A pass on asks alone no entry takes is held '
        f'({RULING}).',
        'evidence': f'pricing/data/base-evidence.json (built {evidence.get("built")}, pulled {evidence.get("pulled")})',
        'rows': dict(sorted(report['rows'].items())),
        'custom': report['custom'],
        'kb_excluded': KB_EXCLUDED,
        'kb': dict(sorted(kb.items())),
        'kb_dropped': dict(sorted(kb_dropped.items())),
        'denied': dict(sorted(denied.items())),
        'held': dict(sorted(held.items())),
        'unresolved': unresolved,
        'conflicts': conflicts,
        'dropped': dict(sorted(report['dropped'].items())),
        'facets': {facet_id: list(decided[facet_id]) for facet_id in sorted(facets)},
    }


def _said(evidence: Mapping[str, Any]) -> str:
    return (f'{evidence.get("q1_ist")}-{evidence["median_ist"]} Ist, n={evidence["n"]}, {evidence.get("kind")}, '
            f'{evidence.get("observed")}')  # fmt: skip


def markdown(report: Mapping[str, Any]) -> str:
    lines = [
        '# Base pickups allowlist (2026-10-23)',
        '',
        'Built by `uv run --offline python -m inventory_tracking.loot.build_base_pickups` into '
        '`inventory_tracking/loot/data/base-pickups.json`; read by `loot/base_floor.py` (`allowed`) in every pickup '
        'level. The player, 2026-10-23 ~00:50: "every base must worth 4+ist at least"; ~17:20: "Sales-backed now". A '
        'white or grey weapon or armor no entry matches, a denied facet, or whose facts the ground read lacks, is left '
        'on the ground and sold in town (keep.py K9).',
        '',
        f"Rule: {report['rule']} Evidence: {report['evidence']}. Prices are the repo's, never the web.",
        '',
        f'## Wants rows allowed ({len(report["rows"])})',
        '',
        '| row | class | base and facts | decided by | evidence (q1-median, n, kind, date) | source |',
        '|---|---|---|---|---|---|',
    ]
    lines += [f'| `{row}` | {entry["class"]} | {entry["label"]} | {entry["decided_by"]} | {_said(entry["evidence"])} | '
              f'{entry["evidence"].get("source")} |' for row, entry in report['rows'].items()]  # fmt: skip
    lines += [
        '',
        f'## Allowlist rules (narrowed, new or added from a facet, {len(report["custom"])})',
        '',
        '| rule | class | base and facts | decided by | evidence | source |',
        '|---|---|---|---|---|---|',
    ]
    lines += [f'| `{rule}` | {entry["class"]} | {entry["label"]} | {entry["decided_by"]} | '
              f'{_said(entry["evidence"])} | {entry["evidence"].get("source")} |'
              for rule, entry in report['custom'].items()]  # fmt: skip
    lines += ['', f'## KB keys allowed ({len(report["kb"])})', '', '| key | facts | decided by | evidence | source |',
              '|---|---|---|---|---|']  # fmt: skip
    lines += [f'| `{key}` | {entry["facts"]} | {entry["decided_by"]} | {_said(entry)} | {entry["source"]} |'
              for key, entry in report['kb'].items()]  # fmt: skip
    lines += ['', '## KB keys left out', '']
    lines += [f'- `{key}`: {why}' for key, why in report['kb_excluded'].items()]
    lines += [f'- `{key}`: {why}' for key, why in (report.get('kb_dropped') or {}).items()]
    lines += [
        '',
        'A better copy (a superior over a normal, 15 ED over an ordinary roll) matches the lower key when its '
        'own is missing, unless the list above or a denied facet proves its own under the floor (loot/base_floor.py '
        '`kb_match`).',
        '',
        f'## Denied facets ({len(report["denied"])}): failing facets an entry would take, left whatever the entries',
        '',
        '| facet | facts | decided by | evidence |',
        '|---|---|---|---|',
    ]
    lines += [f'| `{facet}` | {entry["label"]} | {entry["decided_by"]} | {_said(entry["evidence"])} |'
              for facet, entry in report['denied'].items()]  # fmt: skip
    lines += ['', f'## Held for review ({len(report["held"])}): passes on asks alone, not picked', '',
              '| facet | facts | fills n / median | asks sellers / median | bids at 4+ |',
              '|---|---|---|---|---|']  # fmt: skip
    lines += [f'| `{facet}` | {entry["label"]} | {entry["fills"]["n"]} / {entry["fills"].get("median")} | '
              f'{entry["asks"]["sellers"]} / {entry["asks"].get("median")} | {entry["bids"]["buyers_ge4"]} |'
              for facet, entry in report['held'].items()]  # fmt: skip
    lines += ['', f'## Unresolved ({len(report["unresolved"])}) and conflicts ({len(report["conflicts"])})', '']
    lines += [f'- `{facet}`: {entry["label"]} ({entry["decided_by"]})' for facet, entry in report['unresolved'].items()]
    lines += [f'- conflict: `{facet}`' for facet in report['conflicts']]
    lines += ['', f'## Wants rows and rules left out ({len(report["dropped"])})', '', '| row | class | base | why |',
              '|---|---|---|---|']  # fmt: skip
    lines += [f'| `{row}` | {entry["class"]} | {entry["label"]} | {entry["why"]} |'
              for row, entry in report['dropped'].items()]  # fmt: skip
    return '\n'.join(lines) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    from inventory_tracking.loot.ground_judge import BASE_CLASSES
    from inventory_tracking.loot.wants import wants
    from pricing.api import base_evidence

    rows = [row for row in wants() if row.klass in BASE_CLASSES]
    raw = {row['id']: row for row in json.loads(want_rows.WANTS_FILE.read_text())['rows']}
    report = build(base_evidence(), rows, metadata()['bases'], raw)
    publish(base_floor.PICKUPS, report)  # a temp file of its own, then a rename (reports.py `publish`)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(markdown(report))
    print(
        f'{len(report["rows"])} rows, {len(report["custom"])} rules, {len(report["kb"])} KB keys allowed '
        f'({len(report["kb_dropped"])} proved under), {len(report["denied"])} facets denied, {len(report["held"])} '
        f'held, {len(report["unresolved"])} unresolved, {len(report["conflicts"])} conflicts, {len(report["dropped"])} '
        'rows left out'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
