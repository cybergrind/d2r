"""Exact reviewed Abyss recipe examples; not a generic name-based equivalence."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


# Guide section, recipe, wearer, slot, base, existing reviewed contribution.
CONTEXTS = {
    0: (12, 'Spirit', 'player', 'Weapon', 'crs', 'player-word-spirit-sword'),
    1: (12, "Ancients' Pledge", 'player', 'Off-Hand', 'kit', 'player-word-pledge'),
    2: (13, 'Insight', 'merc', 'Weapon', '9pa', 'insight-act-2-might'),
    3: (13, 'Bulwark', 'merc', 'Helmet', 'uh9', 'merc-table-bulwark'),
    4: (13, 'Treachery', 'merc', 'Body Armor', 'xtp', 'merc-table-treachery'),
    5: (17, 'Insight', 'merc', 'Weapon', '7wc', 'insight-act-2-might'),
    6: (21, 'Insight', 'merc', 'Weapon', '7wc', 'insight-act-2-might'),
    94: (39, 'Insight', 'merc', 'Weapon', '7wc', 'insight-act-2-might'),
    97: (40, 'Insight', 'merc', 'Weapon', '7wc', 'insight-act-2-might'),
}
SECTION_CLAIMS = {
    12: ('Setup', 'Starter setup', 'capping your resistances'),
    13: ('Mercenary', 'Act 2 Might Mercenary', 'Meditation Aura', 'Life Steal', 'Fade'),
    17: ('Mercenary', 'Act 2 Might Mercenary', 'Magic Immunes', 'Mana issues'),
    21: ('Mercenary', 'Act 2 Might Mercenary', 'Magic Immunes', 'Mana issues'),
    39: ('Insight, Might', 'Desert Mercenary with Might Aura', 'Insight Giant Thresher', 'Meditation Aura'),
    40: ('Gear Progression', 'Weapon Insight Insight', 'The Mercenary'),
}


CONTRIBUTIONS = {
    'Spirit': ({'swor'}, {'127:0', '105:0', '99:0', '9:0'}),
    "Ancients' Pledge": ({'shie'}, {'39:0', '41:0', '43:0', '45:0'}),
    'Insight': ({'pole'}, {'151:120', '17:0', '18:0', '97:9'}),
    'Bulwark': ({'helm', 'circ'}, {'60:0', '36:0', '34:0'}),
    'Treachery': ({'tors'}, {'93:0', '201:17103'}),
}


def _matches(predicate, facts, context):
    if 'all' in predicate:
        return all(_matches(child, facts, context) for child in predicate['all'])
    if 'any' in predicate:
        return any(_matches(child, facts, context) for child in predicate['any'])
    if predicate.get('op') not in {'fact_eq', 'context_eq'}:
        raise ValueError('Abyss recipe equivalence requires review of new predicate semantics')
    source = facts if predicate['op'] == 'fact_eq' else context
    return predicate['field'] in source and source[predicate['field']] == predicate['value']


def validate_abyss_recipe(review, resolved, role, root):
    evidence = review['evidence']
    if evidence['guide']['path'] != 'pricing/raw/mr/guides__abyss-warlock-build-guide.html':
        raise ValueError('Abyss recipe review belongs to another guide')
    context = CONTEXTS.get(resolved['context']['span_index'])
    if context is None:
        raise ValueError('Abyss recipe context has not been reviewed')
    section_id, name, side, slot, base, suffix = context
    guide = section_inventory(_read_pin(evidence['guide'], root))
    section = guide['sections'][section_id]
    heading, *claims = SECTION_CLAIMS[section_id]
    if (
        evidence['reference']['section_locator'] != f'/sections/{section_id}'
        or review['section'] != section
        or section['heading'] != heading
        or not all(claim in section['text'] for claim in claims)
    ):
        raise ValueError('Abyss recipe wearer/contribution evidence differs')
    if (
        review['recipe'] != name
        or role.get('id') != f'abyss-warlock-{suffix}'
        or role.get('build') != 'abyss-warlock-build-guide'
        or role.get('names') != [name]
        or role.get('side') != side
        or role.get('slot') != slot
        or review['recipe_source']['path'] != 'pricing/raw/d2data/runes.json'
    ):
        raise ValueError('Abyss recipe configuration differs')
    types, priorities = CONTRIBUTIONS[name]
    if (
        set(role.get('types', [])) != types
        or not priorities <= set(role.get('important_stats', []))
        or set(role.get('qualities', [])) != {'normal', 'superior', 'low_quality'}
    ):
        raise ValueError('Abyss recipe contribution or item family differs')
    recipe = json.loads(_read_pin(review['recipe_source'], root))[name]
    runes = [recipe[f'Rune{i}'] for i in range(1, 7) if recipe.get(f'Rune{i}')]
    item = resolved['item']
    if (
        item.get('base') != base
        or item.get('quality') != 7
        or not str(item.get('unique', '')).startswith('runeword')
        or item.get('socketedItems') != runes
        or item.get('sockets') != len(runes)
        or item.get('ethereal', False) is not (side == 'merc')
    ):
        raise ValueError('Abyss native recipe/base/socket/ethereal example differs')
    facts = {
        'base_code': base,
        'identified': True,
        'runeword': name,
        'sockets': len(runes),
        'socket_contents': 'filled',
        'ethereal': side == 'merc',
    }
    wearer = {'player_class': 'Warlock', 'mercenary_type': 'Act 2 Might'}
    must = role.get('must', {})
    required = [('context_eq', 'player_class', 'Warlock')]
    required += [('fact_eq', field, facts[field]) for field in ('identified', 'runeword', 'sockets', 'socket_contents')]
    if side == 'merc':
        required.append(('context_eq', 'mercenary_type', 'Act 2 Might'))
    if not all(requires_eq(must, *claim) for claim in required) or not _matches(must, facts, wearer):
        raise ValueError('Abyss existing rule does not assess this exact example')
