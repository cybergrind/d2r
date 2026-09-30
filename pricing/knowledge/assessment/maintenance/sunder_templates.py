"""Reviewed original Sunder charm uses, distinct from generated Renewed charms."""

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.definition_store import catalog


# Native immunity statistic and wearer penalty, verified against uniqueitems.
MEMBERS = {
    'Cold Rupture': ('187:0', '43:0', 'cold'),
    'Flame Rift': ('189:0', '39:0', 'fire'),
    'Crack of the Heavens': ('190:0', '41:0', 'lightning'),
    'Rotting Fissure': ('191:0', '45:0', 'poison'),
    'Bone Break': ('192:0', '36:0', 'physical'),
    'Black Cleft': ('193:0', '37:0', 'magic'),
}


def expand_sunder_charm(row):
    name = row['item']
    if (
        name not in MEMBERS
        or row['class'] not in CLASS_NAMES
        or row['side'] != 'player'
        or row['slot'] != 'Unique Charms'
    ):
        raise ValueError('Invalid original Sunder charm membership')
    definition = catalog().named['unique', name]
    immunity, penalty, damage_type = MEMBERS[name]
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        *[
            {'op': 'fact_eq', 'field': k, 'value': v}
            for k, v in (
                ('identified', True),
                ('base_code', definition['base_codes'][0]),
                ('ethereal', False),
                ('sockets', 0),
                ('socket_contents', 'empty'),
            )
        ],
        {'op': 'stat_at_least', 'key': immunity, 'value': 300, 'absent_is_zero': True},
        {'not': {'op': 'stat_at_least', 'key': immunity, 'value': 301}},
    ]
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': f'{damage_type.capitalize()} immunity-breaking inventory alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['unique'],
        'must': {'all': must},
        'important_stats': [immunity, penalty],
        'conditions': [
            'Keep in active inventory and meet level 75. This reviews an existing original charm; '
            'Latent and Renewed identities and their generated modifiers are separate.',
            f'Use only when the actual setup deals relevant {damage_type} damage against immune targets. '
            'Breaking immunity does not remove all enemy resistance; follow-up resistance reduction '
            'and survival still depend on the complete setup.',
            'The negative wearer resistance is a cost, not a damage bonus. Prefer the less-negative '
            'penalty; account for it in the full resistance or physical mitigation total.',
            *row.get('conditions', []),
        ],
    }
