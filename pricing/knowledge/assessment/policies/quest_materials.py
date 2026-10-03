"""Reviewed recipe materials and Cube utility, kept separate from quest-only objects."""

import hashlib
import json
from functools import lru_cache

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.policies.consumables import SOURCE, SOURCE_SHA256


ROOT = SOURCE.parents[3]
RECIPES = ROOT / 'third-parties/d2data/json/cubemain.json'
RECIPES_SHA256 = '0b3deb18f4b1605e72a11a8d72e8ce73f1fbd662546d2a875d182be9b70b53e8'
STRINGS_SOURCE = 'third-parties/d2data/json/allstrings-eng.json'
STRINGS_SHA256 = '27f09255a8c77d43153845b0f85c9a85848df2b315a012cbf234b09e1e319ddc'
# Verified native codes and localized names, including the native ceh spelling error.
NAMES = {
    'ceh': 'Charged Essence of Hatred',
    'ua1': "Talic's Anguish",
    'ua2': "Korlic's Pain",
    'ua3': "Madawc's Ire",
    'ua4': "Bul-Kathos' Nightmare",
    'ua5': "Worusk's End",
}
KEYS = frozenset({'pk1', 'pk2', 'pk3'})
ORGANS = frozenset({'bey', 'dhn', 'mbr'})
ESSENCES = frozenset({'tes', 'ceh', 'bet', 'fed'})
STATUES = frozenset({'ua1', 'ua2', 'ua3', 'ua4', 'ua5'})
SHARDS = frozenset({'xa1', 'xa2', 'xa3', 'xa4', 'xa5'})
TRADEABLE = KEYS | ORGANS | ESSENCES | STATUES | SHARDS | {'toa'}
REVIEWED = TRADEABLE | {'box'}


@lru_cache(maxsize=2)
def _definitions(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Native quest materials changed; review before publication.')
    native = json.loads(raw)
    result = {code: {**native[code], 'market_name': NAMES.get(code, native[code]['name'])} for code in REVIEWED}
    if any(r['type'] != 'ques' or r['stackable'] != 0 or r['gemsockets'] != 0 for r in result.values()):
        raise ValueError('Unreviewed quest-material native shape.')
    return result


def definitions():
    return _definitions(read_artifact(SOURCE))


@lru_cache(maxsize=2)
def _recipes(raw):
    if hashlib.sha256(raw).hexdigest() != RECIPES_SHA256:
        raise ValueError('Material recipes changed; review before publication.')
    return json.loads(raw)


def recipe_uses(code):
    recipes = _recipes(read_artifact(RECIPES))
    rows = [
        (key, row)
        for key, row in recipes.items()
        if row.get('enabled') == 1 and not row.get('ladder') and code in [row.get(f'input {i}') for i in range(1, 8)]
    ]
    if code in KEYS:
        uses = ['Combine one of each Pandemonium key in the Cube to open a minor Uber portal.']
    elif code in ORGANS:
        uses = ["Combine Baal's Eye, Diablo's Horn and Mephisto's Brain to open Uber Tristram."]
    elif code in ESSENCES:
        uses = ['Combine all four different essences to make a Token of Absolution.']
    elif code in STATUES:
        uses = ['Combine all five different Ancient statues in Hell to open the Colossal Summit.']
    elif code in SHARDS:
        # Use actual output fields; several native descriptions still say statue instead of shard.
        outputs = sorted({r['output'].replace('Crafted ', 'Renewed ') for _, r in rows})
        uses = ['Cube ingredient for ' + ', '.join(outputs) + '; the recipe also requires its rune and perfect gem.']
    elif code == 'toa':
        uses = ['Right-click to reset Stat/Skill Points.']
    else:
        uses = ['Use the Horadric Cube for transmutation recipes and its separate storage grid.']
    if code in TRADEABLE - {'toa'} and not rows:
        raise ValueError('Reviewed material has no enabled Non-Ladder recipe.')
    return uses, [key for key, _ in rows]


def assess_material(facts):
    native = definitions().get(facts.base_code)
    if native is None:
        return None
    gaps = [*facts.gaps, *facts.projection_gaps]
    names = {native['name'], native['market_name']}
    if facts.name not in names or facts.base_name not in names or facts.item_type != native['type']:
        gaps.append('Quest-material identity conflicts with its native definition.')
    for field, expected in (('rarity', 'normal'), ('ethereal', False), ('sockets', 0), ('socket_contents', 'empty')):
        if getattr(facts, field) != expected:
            gaps.append(f'Recipe material requires {field}={expected!r}.')
    if facts.runeword or facts.stats or facts.properties or facts.socket_items:
        gaps.append('Recipe material has unexpected modifiers or socket contents.')
    uses, recipes = recipe_uses(facts.base_code)
    return {
        'status': 'review' if gaps else 'usable',
        'kind': 'quest_material' if facts.base_code in TRADEABLE else 'quest_utility',
        'name': native['market_name'],
        'effects': [],
        'uses': uses,
        'improvements': [],
        'variable_rolls': False,
        'gaps': list(dict.fromkeys(gaps)),
        'sources': [
            {'path': str(SOURCE.relative_to(ROOT)), 'sha256': SOURCE_SHA256, 'locator': '/' + facts.base_code},
            *[
                {'path': str(RECIPES.relative_to(ROOT)), 'sha256': RECIPES_SHA256, 'locator': '/' + key}
                for key in recipes
            ],
            {
                'path': STRINGS_SOURCE,
                'sha256': STRINGS_SHA256,
                'locator': '/' + ('UseTokenOfAbsolution' if facts.base_code == 'toa' else native['namestr']),
            },
        ],
    }
