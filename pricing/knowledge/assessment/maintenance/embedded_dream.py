"""Review the two legacy Dream equipment-table components without selecting a variant."""

import json

from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq


CONTEXTS = {
    65: ('Off-Hand', 'Sacred Targe', 'off-hand', 'head', 'Bone Visage'),
    73: ('Helmets', 'Bone Visage', 'helmets', 'off_hand', 'Sacred Targe'),
}


def _accepts(rule, facts):
    if 'all' in rule:
        return all(_accepts(child, facts) for child in rule['all'])
    if 'any' in rule:
        return any(_accepts(child, facts) for child in rule['any'])
    if rule.get('op') not in ('fact_eq', 'context_eq'):
        raise ValueError('Dream predicate semantics require review')
    return rule.get('field') in facts and facts[rule['field']] == rule.get('value')


def validate_dream_equipment(review, resolved, role, root):
    evidence, context = review['evidence'], resolved['context']
    expected = CONTEXTS.get(context['span_index'])
    if (
        expected is None
        or evidence['guide']['path'] != 'pricing/raw/mr/guides__dream-paladin.html'
        or evidence['reference'].get('format') != 'legacy_item'
        or evidence['reference'].get('set_id') is not None
        or evidence['reference']['section_locator'] != '/sections/31'
        or context['label'] != 'Dream'
        or context['side'] != 'player'
    ):
        raise ValueError('Dream equipment context has not been reviewed')
    if context['slot'] != expected[0]:
        raise ValueError('Dream equipment slot differs')
    validate_component(review, resolved, role, root, expected)


def validate_native_item(item, code, runes):
    if (
        item.get('base') != code
        or item.get('unique') != 'runeword055'
        or item.get('quality') != 7
        or item.get('socketedItems') != runes
        or item.get('sockets') != 3
        or len(runes) != 3
        or item.get('ethereal', False) is not False
    ):
        raise ValueError('Dream native item identity or recipe differs')


def validate_component(review, resolved, role, root, expected):
    """Shared native and role requirements; caller must validate its source context."""
    slot, base_name, suffix, other_slot, other_name = expected
    if (
        role.get('slot') != slot
        or role.get('side') != 'player'
        or role.get('build') != 'dream-paladin'
        or role.get('names') != ['Dream']
        or set(role.get('types', [])) != ({'helm', 'circ'} if slot == 'Helmets' else {'shie', 'ashd'})
        or role.get('id') != f'dream-paladin-dream-{suffix}-aura-recipe'
        or set(role.get('qualities', [])) != {'normal', 'superior', 'low_quality'}
        or review['recipe_source']['path'] != 'third-parties/d2data/json/runes.json'
        or review['base_source']['path'] != 'third-parties/d2data/json/armor.json'
    ):
        raise ValueError('Dream equipment role or native source differs')
    bases = json.loads(_read_pin(review['base_source'], root))
    code = next(k for k, v in bases.items() if v['name'] == base_name)
    other_code = next(k for k, v in bases.items() if v['name'] == other_name)
    recipe = json.loads(_read_pin(review['recipe_source'], root))['Dream']
    runes = [recipe[f'Rune{i}'] for i in range(1, 7) if recipe.get(f'Rune{i}')]
    item = resolved['item']
    validate_native_item(item, code, runes)
    facts = {
        'base_code': code,
        'identified': True,
        'runeword': 'Dream',
        'sockets': 3,
        'socket_contents': 'filled',
        'ethereal': False,
        'player_class': 'Paladin',
    }
    must = role.get('must', {})
    required = [('context_eq', 'player_class', 'Paladin')]
    required += [
        ('fact_eq', field, facts[field])
        for field in ('identified', 'runeword', 'sockets', 'socket_contents', 'ethereal')
    ]
    if not all(requires_eq(must, *r) for r in required) or not _accepts(must, facts):
        raise ValueError('Dream role does not preserve wearer or item restrictions')
    priority = {
        '151:118',
        '99:0',
        '39:0',
        '41:0',
        '43:0',
        '45:0',
        '217:0',
        '80:0',
        '76:0' if slot == 'Helmets' else '7:0',
    }
    deps = role.get('depends_on', [])
    if not priority <= set(role.get('important_stats', [])) or len(deps) != 1:
        raise ValueError('Dream contribution or complementary equipment differs')
    pair = deps[0].get('when', {})
    condition = pair.get('when', {})
    if (
        pair.get('op') != 'equipped_item_matches'
        or pair.get('field') != 'player_equipment'
        or pair.get('slot') != other_slot
        or not all(requires_eq(condition, *r) for r in required[1:])
        or not _accepts(condition, {**facts, 'base_code': other_code})
        or _accepts(condition, facts)
    ):
        raise ValueError('Dream paired benefit needs the complementary equipped item')
    return other_code, runes
