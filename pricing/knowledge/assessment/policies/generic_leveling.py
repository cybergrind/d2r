"""Reviewed affixed and socketed leveling utility, independent of trade tiers and prices."""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.domain.facts import FactStatus, StatKey
from pricing.knowledge.assessment.mechanics.equipment import assess_requirements
from pricing.knowledge.assessment.policies.socket_leveling import socket_patterns
from pricing.knowledge.assessment.registry import FAMILIES


SOURCE = Path(__file__).resolve().parents[3] / 'data/appraisal-leveling-candidates-2026-09-23.json'
SOURCE_SHA256 = '7a32a4ab275b78c862f485da9c53c3b3f74bace86967f99c8a9fe387b3233cd7'


# Source indices are stable under the reviewed fingerprint. Native stat IDs,
# never market property IDs, govern the observed utility.
@dataclass(frozen=True)
class Pattern:
    source_index: int
    item_types: frozenset[str]
    stat_groups: tuple[tuple[int, ...], ...]
    archetype: str
    condition: str
    qualities: tuple[str, ...] = ('magic', 'rare')
    side: str = 'player'

    def matches(self, facts):
        return (
            (self.side == 'mercenary' or facts.ethereal is False)
            and not (facts.rarity == 'set' and facts.ethereal is True)
            and facts.rarity in self.qualities
            and facts.item_type in self.item_types
            and all(any(positive_stat(facts, stat) for stat in group) for group in self.stat_groups)
        )


PATTERNS = (
    Pattern(
        6,
        frozenset({'pole', 'spea'}),
        ((136,),),
        'attack',
        'Act 2 mercenary boss-fight option; compare damage, attack speed, survival and wearer requirements.',
        ('unique', 'set'),
        'mercenary',
    ),
    Pattern(
        6,
        next(f.types for f in FAMILIES if f.name == 'weapon'),
        ((136,),),
        'attack',
        'Use Crushing Blow for boss fights when the attack build needs it; '
        'compare weapon damage, speed and equipment requirements.',
        ('magic', 'rare', 'crafted'),
    ),
    Pattern(
        0,
        frozenset({'boot'}),
        ((96,),),
        'all',
        'Early leveling; compare movement speed and defenses with current boots.',
    ),
    Pattern(8, frozenset({'ring'}), ((105,),), 'caster', 'Use when the cast rate reaches a needed casting breakpoint.'),
    Pattern(
        8,
        frozenset({'ring'}),
        ((7, 9, 39, 41, 43, 45),),
        'all',
        'Use for a current life, mana or resistance need; preserve required casting breakpoints.',
    ),
    Pattern(
        12,
        frozenset({'scha', 'mcha', 'lcha'}),
        ((39, 41, 43, 45),),
        'all',
        'Use to cover a current resistance shortfall.',
    ),
    Pattern(
        2,
        frozenset({'ring', 'glov', 'boot'}),
        ((80,),),
        'all',
        'Early magic find; keep adequate survival and damage while leveling.',
    ),
    Pattern(
        3,
        frozenset({'glov'}),
        ((93,), (0, 2, 7, 19, 39, 41, 43, 45)),
        'attack',
        'Use attack speed with a useful secondary stat when current gloves are weaker.',
    ),
    Pattern(
        4,
        frozenset({'belt'}),
        ((105,),),
        'caster',
        'Use when the crafted belt reaches a needed casting breakpoint.',
        ('crafted',),
    ),
    Pattern(
        11,
        frozenset({'belt'}),
        ((7, 39, 41, 99),),
        'all',
        'Leveling fallback for life, fire/lightning resistance or hit recovery; compare current belt.',
    ),
)


def positive_stat(facts, stat):
    observed = facts.stat(StatKey(stat, 0))
    value = observed.value
    return observed.status == FactStatus.KNOWN and type(value) in (int, float) and math.isfinite(value) and value > 0


def assess_generic_leveling(facts, *, loadout=None):
    if facts.identified is not True:
        return []
    matches = [p for p in PATTERNS if p.matches(facts)]
    if facts.ethereal is False:
        matches.extend(Pattern(index, frozenset(), (), 'all', condition) for index, condition in socket_patterns(facts))
    if not matches:
        return []
    try:
        raw = read_artifact(SOURCE)
        if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
            return []
        document = json.loads(raw)
    except OSError, ValueError:
        return []
    uses = []
    seen = set()
    for pattern in matches:
        index, archetype, condition = pattern.source_index, pattern.archetype, pattern.condition
        key = index, pattern.side
        if key in seen:
            continue
        seen.add(key)
        source = document['generic_patterns'][index]
        uses.append(
            {
                'tier': 'med',
                'status': 'conditional',
                'side': pattern.side,
                'classes': ['all classes'],
                'archetypes': [archetype],
                'reason': source['context'],
                'conditions': [condition],
                'required_level': None,
                'requirements': {},
                'requirements_fit': assess_requirements({}, pattern.side, loadout),
                'stage': 'leveling',
                'source': {
                    'id': document['source']['id'],
                    'locator': f'/generic_patterns/{index}',
                    'date': '2025-04-24',
                    'review': '2026-09-24: conditional native-stat utility; no trade-value inference.',
                },
            }
        )
    return uses
