"""Standalone named caster gear alternatives with native property recipients."""

from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


BUILDS = {
    'fissure-druid': 'Druid',
    'blood-boil-warlock-guide': 'Warlock',
    'summoner-warlock-guide': 'Warlock',
    'fire-wall-sorceress-guide': 'Sorceress',
    'frozen-orb-meteor-sorceress': 'Sorceress',
    'frozen-orb-sorceress': 'Sorceress',
    'hydra-sorceress': 'Sorceress',
    'summoner-necromancer-guide': 'Necromancer',
}
MEMBERS = {
    'Harlequin Crest': ('Helmet', ('127:0', '216:0', '217:0', '80:0', '36:0', '0:0', '1:0', '2:0', '3:0')),
    'Skin of the Vipermagi': ('Body Armor', ('127:0', '105:0', '39:0', '41:0', '43:0', '45:0', '35:0', '16:0')),
    'Arachnid Mesh': ('Belt', ('127:0', '105:0', '77:0', '16:0')),
    'The Stone of Jordan': ('Rings', ('127:0', '9:0', '77:0')),
    "Mara's Kaleidoscope": ('Amulets', ('127:0', '39:0', '41:0', '43:0', '45:0', '0:0', '1:0', '2:0', '3:0')),
    'War Traveler': ('Boots', ('80:0', '96:0', '0:0', '3:0', '16:0')),
}


def expand_caster_core(row):
    name = row['item']
    if (
        name not in MEMBERS
        or BUILDS.get(row['build']) != row['class']
        or row['side'] != 'player'
        or (row['build'] == 'fissure-druid' and name != 'Skin of the Vipermagi')
    ):
        raise ValueError('Unreviewed caster core member or wearer')
    slot, stats = MEMBERS[name]
    if row['slot'] != slot or (name == "Mara's Kaleidoscope" and row['class'] != 'Sorceress'):
        raise ValueError('Unreviewed caster core slot or guide alternative')
    definition = catalog().named['unique', name]
    maximum = 1 if slot in ('Helmet', 'Body Armor') else 0
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        named_base_condition(name, 'unique'),
        {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in range(maximum + 1)]},
    ]
    if not maximum:
        must.append({'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'})
    conditions = [
        'This is a standalone gear-table alternative. Meet equipment requirements and preserve '
        'the rest of the casting, resistance and resource setup. Neither a full-build breakpoint '
        'nor an unspecified socket filler is inferred.',
        'Faster Cast Rate changes casting animations; it does not remove casting delays or '
        'multiply persistent minion attacks. All Skills and resource bonuses are separate from '
        'added weapon damage, on-hit effects and charged skills.',
    ]
    if name == 'Harlequin Crest':
        conditions.append(
            'Life and mana per level scale with character level; they are not flat unscaled resource rolls.'
        )
    if name == 'War Traveler':
        conditions.append('Flat weapon damage and attacker thorns are not credited as caster spell or minion damage.')
    if name == 'Arachnid Mesh':
        conditions.append('Slows Target and Venom charges are not passive bonuses to these spells or summoned attacks.')
    if name == 'The Stone of Jordan':
        conditions.append('Added lightning attack damage does not increase spell or minion lightning damage.')
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': 'Caster skill, resource and survival gear alternative'
        if name != 'War Traveler'
        else 'Caster farming boots alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['unique'],
        'must': {'all': must},
        'important_stats': list(stats),
        'conditions': conditions,
    }
