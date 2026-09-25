"""Runeword base fitness, separate from prices and completed-runeword rolls.

Recipe edges and recommendations come from the portable offline utility KB.
Only reviewed use cases receive quality judgments; ordering in a guide is never
interpreted as a universal DPS ranking. No third-party checkout is needed at runtime.
"""

import json
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.adapters.capture import bases_by_code
from pricing.knowledge.assessment.domain.facts import freeze
from pricing.knowledge.assessment.mechanics.preparation import prepare_sockets
from pricing.knowledge.assessment.mechanics.recipe_index import compile_recipe_index


MERC_WORDS = frozenset({'Insight', 'Infinity', 'Pride', 'Obedience'})
BASE_QUALITIES = frozenset({'normal', 'superior', 'low_quality', 'low quality'})
UTILITY = Path(__file__).resolve().parents[2] / 'data/appraisal-utility.json'


@lru_cache(maxsize=2)
def _recipes(raw):
    document = json.loads(raw)
    if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
        raise ValueError('Unsupported utility artifact schema')
    return freeze(document['rows'])


def recipe_catalog():
    try:
        raw = read_artifact(UTILITY)
    except FileNotFoundError:
        return ()
    return _recipes(raw)


@lru_cache(maxsize=2)
def _recipe_index(raw, types):
    return compile_recipe_index(_recipes(raw), dict(types))


def recipe_index():
    try:
        raw = read_artifact(UTILITY)
    except FileNotFoundError:
        return compile_recipe_index((), {})
    types = tuple(sorted((b['name'], b['type']) for b in bases_by_code().values()))
    return _recipe_index(raw, types)


def roll(facts, stat):
    row = facts.stats.get(f'{stat}:0')
    return row['raw'] if row and row['status'] == 'decoded' and type(row['raw']) is int else None


def weapon_quality(facts):
    strengths, missing = [], []
    if facts.ethereal is True:
        strengths.append('Ethereal: +50% base damage; mercenary equipment does not lose durability.')
    elif facts.ethereal is False:
        missing.append('Ethereal would improve mercenary damage; this base cannot be made ethereal.')
    else:
        missing.append('Ethereal status has not been read.')
    damage = roll(facts, 17)
    if damage == 15 and roll(facts, 18) == 15:
        strengths.append('Perfect superior damage: 15% Enhanced Damage.')
    else:
        missing.append('15% superior Enhanced Damage is an optional premium; it cannot be added later.')
    if roll(facts, 19) == 3:
        strengths.append('Perfect superior Attack Rating: +3 (small practical benefit).')
    else:
        missing.append('+3 superior Attack Rating is an optional collector roll; it cannot be added later.')
    return strengths, missing


def player_quality(facts, name, *, wearer=None):
    """Role-specific priorities; no mercenary ethereal rule leaks into player gear."""
    strengths, missing = [], []
    if name == 'Grief' and facts.base_name == 'Phase Blade':
        role = 'player melee'
        strengths.append('Fast, inherently indestructible base: no durability repairs.')
        if roll(facts, 17) == 15 and roll(facts, 18) == 15 and roll(facts, 19) == 3:
            strengths.append('Perfect superior rolls: 15% Enhanced Damage and +3 Attack Rating.')
        else:
            missing.append('Optional premium: 15% Enhanced Damage / +3 Attack Rating; cannot be added later.')
        tradeoff = 'Grief damage and IAS rolls are rolled when making the word; superior ED affects base damage only.'
    elif name == 'Spirit' and facts.base_name in ('Monarch', 'Sacred Targe'):
        role = 'Paladin caster' if facts.base_name == 'Sacred Targe' else 'non-Paladin caster'
        if facts.base_name == 'Sacred Targe':
            resists = [roll(facts, stat) for stat in (39, 41, 43, 45)]
            if resists == [45] * 4:
                strengths.append('Perfect inherent resistances: +45 all resistances.')
            else:
                missing.append('Preferred inherent roll: +45 all resistances; cannot be added to this base.')
            strengths.append('High-block, low-strength elite Paladin shield.')
        else:
            strengths.append('Lowest strength requirement among non-Paladin four-socket shields (156).')
        missing.append('Premium defense needs a separate base-defense roll check; it is optional for Spirit.')
        tradeoff = 'Caster utility mainly depends on the completed Spirit FCR roll; base defense does not improve FCR.'
    elif name in ('Enigma', 'Fortitude') and facts.item_type == 'tors':
        role = wearer or ('mercenary' if name == 'Fortitude' else 'player')
        if roll(facts, 16) == 15:
            strengths.append('Perfect superior Enhanced Defense: 15%.')
        else:
            missing.append('15% superior Enhanced Defense is an optional premium; it cannot be added later.')
        missing.append(
            'Check base defense and wearer strength before investing runes; ED alone does not prove maximum defense.'
        )
        tradeoff = (
            'Higher-defense armor can require more strength; use the best defense the intended mercenary can equip.'
            if name == 'Fortitude'
            else 'Low strength requirements can outweigh extra defense; superior armor increases repair costs.'
        )
    else:
        return None
    wanted_ethereal = role == 'mercenary'
    if facts.ethereal is wanted_ethereal:
        strengths.append('Ethereal suits mercenary use.' if wanted_ethereal else 'Non-ethereal suits player use.')
    elif facts.ethereal is None:
        missing.append('Ethereal status has not been read.')
    else:
        missing.append(
            'Prefer an ethereal mercenary base; this property cannot be added.'
            if wanted_ethereal
            else 'Prefer non-ethereal for player use; this runeword does not repair an ethereal base.'
        )
    return role, strengths, missing, tradeoff


def assess_runeword_base(facts):
    """Evaluate normalized item facts once within the assessment engine."""
    if facts.runeword or facts.rarity not in BASE_QUALITIES or not facts.base_name:
        return []
    index = recipe_index()
    catalog = index.by_base.get(facts.base_name, ())
    recommended = {r['details']['runeword']: r for r in catalog if r.get('details', {}).get('recommended')}
    rows = []
    for recipe in catalog:
        details = recipe.get('details', {})
        name = details.get('runeword')
        if details.get('legality') != 'verified_type_and_capacity':
            continue
        # These established recipes are available on Non-Ladder. Do not infer
        # availability for new/ladder-only recipes from a compatibility edge.
        merc_weapon = facts.item_type in ('pole', 'spea') and name in MERC_WORDS
        player = player_quality(facts, name) if not merc_weapon else None
        if not merc_weapon and player is None:
            continue
        preparation = prepare_sockets(facts, recipe)
        status, needs = preparation.status, list(preparation.messages)
        if merc_weapon:
            role = 'Act 2 mercenary'
            strengths, missing = weapon_quality(facts)
            tradeoff = (
                'Best damage depends on the mercenary attack-speed breakpoint and other gear; '
                '15% ED and +3 AR are premiums, not prerequisites for useful gear.'
            )
        else:
            role, strengths, missing, tradeoff = player
        if facts.socket_contents != 'empty':
            strengths = []
            missing = ['Base rolls need verification without socket contributions.']
        recommendation = recommended.get(name, {})
        context = recommendation.get('details', {}).get('context', {})
        preferred = name in recommended and (not merc_weapon or bool(context.get('builds_merc')))
        if facts.rarity in ('low_quality', 'low quality'):
            strengths = []
            missing = ['Assess base rolls again after normalization.']
        if status == 'ready':
            status = 'preferred base' if preferred else 'usable alternative'
            if preferred and not missing and not facts.gaps:
                status = 'perfect preferred base'
        missing = needs + missing
        if not facts.capture_complete or facts.identified is not True:
            missing.append('Complete identified-item capture is needed to verify all base rolls.')
        alternatives = index.mercenary_alternatives.get(name, ()) if merc_weapon else ()
        rows.append(
            {
                'runeword': name,
                'preparation': [option.to_dict() for option in preparation.options],
                'role': role,
                'ethereal_preference': base_ethereal_preference(role, facts.base_name),
                'status': status,
                'strengths': strengths,
                'missing': missing,
                'alternatives': [n for n in alternatives if n != facts.base_name],
                'tradeoff': tradeoff,
                'sources': [recipe.get('source_locator'), recommended.get(name, {}).get('source_locator')],
            }
        )
        if extra := additional_player_use(facts, recipe, recommendation):
            rows.append(extra)
    return sorted(rows, key=lambda r: (r['status'] == 'wrong socket count', r['runeword']))


def additional_player_use(facts, recipe, recommendation):
    """Reviewed player uses that must not inherit a mercenary's damage priorities."""
    context = recommendation.get('details', {}).get('context', {})
    name = recipe['details']['runeword']
    if name == 'Infinity' and facts.base_name == 'Scythe' and 'nova-sorceress-guide' in context.get('builds_char', []):
        role = 'Nova player caster'
        strengths = ['Scythe is the cited player base for self-wielded Nova Infinity.']
        missing = ['Confirm the intended caster setup and wearer requirements before investing runes.']
        tradeoff = (
            'Caster use prioritizes requirements and completed Infinity lightning pierce; '
            'superior physical damage and Attack Rating do not improve Nova.'
        )
        if facts.ethereal is None:
            missing.append('Ethereal status has not been read.')
        elif facts.ethereal:
            tradeoff += ' An ethereal weapon cannot be repaired if used for melee attacks.'
    elif name == 'Fortitude' and facts.base_name == 'Archon Plate' and context.get('builds_char'):
        role, strengths, missing, tradeoff = player_quality(facts, name, wearer='player')
        tradeoff = 'Player use values survivability and physical damage; compare strength requirements and repair cost.'
    else:
        return None
    preparation = prepare_sockets(facts, recipe)
    status, needs = preparation.status, list(preparation.messages)
    if status == 'ready':
        status = 'preferred base'
    if facts.socket_contents != 'empty':
        strengths = []
        missing.append('Base rolls need verification without socket contributions.')
    if facts.rarity in ('low_quality', 'low quality'):
        strengths = []
        missing = ['Assess base rolls again after normalization.']
    if not facts.capture_complete or facts.identified is not True:
        missing.append('Complete identified-item capture is needed to verify all base rolls.')
    return {
        'runeword': name,
        'preparation': [option.to_dict() for option in preparation.options],
        'role': role,
        'ethereal_preference': base_ethereal_preference(role, facts.base_name),
        'status': status,
        'strengths': strengths,
        'missing': needs + missing,
        'alternatives': [],
        'tradeoff': tradeoff,
        'sources': [recipe.get('source_locator'), recommendation.get('source_locator')],
    }


def base_ethereal_preference(role, base_name):
    """Preferences for the reviewed base-use branches above, not arbitrary gear."""
    if role in ('Act 2 mercenary', 'mercenary'):
        return {'preference': 'preferred', 'reason': 'Mercenary equipment benefits without durability loss.'}
    if role == 'Nova player caster':
        return {'preference': 'neutral', 'reason': 'Casting Nova does not use weapon damage or weapon durability.'}
    if base_name == 'Phase Blade':
        return {'preference': 'neutral', 'reason': 'This runeword base has no durability and cannot be ethereal.'}
    return {'preference': 'avoid', 'reason': 'Player armor and shields need repairs; this recipe does not repair them.'}
