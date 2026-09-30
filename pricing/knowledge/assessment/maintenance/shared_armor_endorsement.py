"""Scope a shared Fade armor example without narrowing its runtime base rule."""

from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import SOURCES


SHARED_QUOTE = (
    'At the very least, the Mercenary can hold Treachery until you need to proc Fade on yourself. '
    "Note: Be sure to make the Mercenary's Treachery in a non Ethereal base."
)


def shared_armor_role(evidence, role, build, read_json):
    source = role['source']
    parts = source['locator'].strip('/').split('/')
    if (
        evidence.get('shared_armor') != 'mercenary_player_fade'
        or evidence.get('coverage') != 'merc_runeword_component'
        or evidence.get('ethereal_scope') != 'nonethereal_only'
        or evidence.get('quote') != SHARED_QUOTE
        or SHARED_QUOTE not in source.get('quotes', [])
        or role.get('names') != ['Treachery']
        or role.get('side') != 'merc'
        or role.get('slot') != 'Body Armor'
        or source['path'] != f'pricing/data/wp-a-variants/{role["build"]}.json'
        or len(parts) != 4
        or parts[0] != 'variants'
        or parts[2:] != ['merc', 'Body Armor']
        or not parts[1].isdecimal()
        or str(int(parts[1])) != parts[1]
    ):
        raise ValueError('Shared armor requires its exact Fade-sharing source and nonethereal scope')
    try:
        variant = read_json(source)['variants'][int(parts[1])]
        labels = variant['merc']['Body Armor']
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError('Shared armor source variant missing') from error
    if (
        variant.get('name') != role['variant']
        or variant.get('planner_only')
        or variant.get('delta_only')
        or SHARED_QUOTE not in variant.get('quotes', [])
        or labels != role.get('alternatives')
        or role.get('conditions') != ['Confirm the player can equip this armor to proc Fade.']
    ):
        raise ValueError('Shared armor source or player equipment condition changed')
    required = [
        {'op': 'context_eq', 'field': 'player_class', 'value': build['class']},
        *[
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in (
                ('runeword', 'Treachery'),
                ('sockets', 3),
                ('socket_contents', 'filled'),
                ('ethereal', False),
                ('identified', True),
            )
        ],
    ]
    dependencies = role.get('depends_on', [])
    wearer = {'op': 'context_eq', 'field': 'mercenary_type', 'value': evidence.get('mercenary_type')}
    if (
        role.get('must') != {'all': required}
        or len(dependencies) != 1
        or dependencies[0].get('required', True) is not True
        or dependencies[0].get('when') != wearer
        or evidence.get('mercenary_type') != 'Act 2 Might'
        or not variant['merc'].get('type', '').startswith('Act 2 Might ')
    ):
        raise ValueError('Shared armor must preserve identification, recipe, class and required wearer')
    pins = evidence.get('recipe_sources', {})
    if set(pins) != set(SOURCES) or any(pins[key].get('path') != path for key, path in SOURCES.items()):
        raise ValueError('Shared armor requires pinned native recipe sources')
    item = evidence.get('expected_item', {})
    base = read_json(pins['armor']).get(item.get('base'), {})
    if (
        not base.get('name')
        or not any(label.startswith('Treachery ' + base['name'] + ' (') for label in labels)
        or ('ethereal' in item and item['ethereal'] is not False)
    ):
        raise ValueError('Shared armor example base or ethereal status conflicts with its source')
    # This is a proof for one source example, not a replacement runtime rule.
    # The normal endorsement validator still checks actual selected equipment,
    # wearer ID, guide tab, native recipe, legal base, and ordered rune contents.
    return {
        **role,
        'must': {
            'all': [
                role['must'],
                wearer,
                {'op': 'fact_eq', 'field': 'base_code', 'value': item['base']},
            ]
        },
        'source': {
            **source,
            'corroborating': [
                *source.get('corroborating', []),
                {**pins['runes'], 'locator': '/Treachery'},
            ],
        },
    }
