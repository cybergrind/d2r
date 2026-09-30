"""Reviewed ordinary recovery and resistance potions; effects are native definitions."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact


SOURCE = Path(__file__).resolve().parents[4] / 'third-parties/d2data/json/misc.json'
SOURCE_SHA256 = '116264d5df4e7724beaf9a7ae1f005c58544a5a50a331baf4b370a4f01110072'
HEALING = frozenset({'hp1', 'hp2', 'hp3', 'hp4', 'hp5'})
MANA = frozenset({'mp1', 'mp2', 'mp3', 'mp4', 'mp5'})
REJUVENATION = frozenset({'rvs', 'rvl'})
STAMINA = frozenset({'vps'})
RESISTANCE = {'wms': ('cold', 'coldresist', 'maxcoldresist'), 'yps': ('poison', 'poisonresist', 'maxpoisonresist')}

REVIEWED_CODES = HEALING | MANA | REJUVENATION | STAMINA | RESISTANCE.keys()


@lru_cache(maxsize=2)
def definitions(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Consumable native definitions changed; review potion policy before publication.')
    data = json.loads(raw)
    return {code: data[code] for code in REVIEWED_CODES}


def assess_consumable(facts):
    row = definitions(read_artifact(SOURCE)).get(facts.base_code)
    if row is None:
        return None
    gaps = [*facts.gaps, *facts.projection_gaps]
    for field, expected in (('rarity', 'normal'), ('ethereal', False), ('sockets', 0), ('socket_contents', 'empty')):
        if getattr(facts, field) != expected:
            gaps.append(f'Ordinary potion requires {field}={expected!r}.')
    if facts.runeword or facts.properties or facts.stats or facts.socket_items:
        gaps.append('Ordinary potion has unexpected modifiers, runeword or socket contents.')
    if facts.base_name != row['name'] or facts.item_type != row['type']:
        gaps.append('Potion identity conflicts with native definition.')
    if facts.base_code in HEALING:
        effects = ['Restores life over time; not instant rejuvenation.']
        uses = ['Carry for player or mercenary healing; feed the mercenary directly when needed.']
        better = [
            (
                'Highest ordinary healing grade; actual healing depends on the recipient.'
                if facts.base_code == 'hp5'
                else 'Higher healing-potion grades provide greater recovery; actual healing depends on the recipient.'
            )
        ]
    elif facts.base_code in MANA:
        effects = ['Restores mana over time; not instant rejuvenation.']
        uses = ['Carry for player casting and mana-consuming attacks.']
        better = [
            (
                'Highest ordinary mana grade; actual recovery depends on the player.'
                if facts.base_code == 'mp5'
                else 'Higher mana-potion grades provide greater recovery; actual recovery depends on the player.'
            )
        ]
    elif facts.base_code in REJUVENATION:
        percent = row['calc1']
        if (
            row['pSpell'] != 5
            or row['stat1'] != 'hitpoints'
            or row['stat2'] != 'mana'
            or row['calc2'] != percent
            or percent not in (35, 100)
        ):
            raise ValueError('Unreviewed rejuvenation effects.')
        effects = [f'Instantly restores {percent}% of maximum life and mana.']
        uses = ['Keep for emergency player recovery or instant mercenary healing.']
        better = ['Full Rejuvenation restores 100%; ordinary Rejuvenation restores 35%.']
    elif facts.base_code in STAMINA:
        effects = ['Restores stamina and greatly increases stamina recovery for 30 seconds.']
        uses = ['Useful for player travel when stamina limits running, especially early leveling.']
        better = ['Repeated doses extend duration; the recovery bonus does not increase.']
    else:
        element, resistance, maximum = RESISTANCE[facts.base_code]
        if (row['stat1'], row['stat2'], row['calc1'], row['calc2'], row['len']) != (resistance, maximum, 50, 10, 750):
            raise ValueError('Unreviewed resistance-potion effects.')
        effects = [f'+50% {element} resistance and +10% maximum {element} resistance for 30 seconds.']
        effects.append('Removes poison.' if element == 'poison' else 'Removes chill/freeze.')
        uses = [f'Use on the player or mercenary before {element}-damage encounters.']
        better = ['Fixed potion effect; no variable roll or ethereal/socket premium.']
    return {
        'status': 'review' if gaps else 'usable',
        'kind': 'potion',
        'effects': effects,
        'uses': uses,
        'improvements': better,
        'variable_rolls': False,
        'gaps': list(dict.fromkeys(gaps)),
        'sources': [
            {
                'path': str(SOURCE.relative_to(SOURCE.parents[3])),
                'sha256': SOURCE_SHA256,
                'locator': '/' + facts.base_code,
            }
        ],
    }
