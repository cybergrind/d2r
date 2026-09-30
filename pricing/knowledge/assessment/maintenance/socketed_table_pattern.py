"""Reviewed Dusk Shroud pattern with bounded HTML and native gem witnesses."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq, role_requires
from pricing.knowledge.builds import decode_planner


KIND = 'fissure_four_topaz_armor'
LABEL = 'Gemmed Dusk Shroud (4x Perfect Topaz es )'
ROLE = 'fissure-druid-perfect-topaz-general-armor'
KINDS = frozenset({KIND, 'player_four_topaz_armor'})
MEMBERS = {
    'fissure-druid': ('Druid', LABEL),
    'berserk-barbarian': ('Barbarian', 'Gemmed Dusk Shroud (4x Perfect Topaz )'),
    'double-throw-barbarian-guide': ('Barbarian', LABEL),
    'lightning-strike-amazon': ('Amazon', LABEL),
}


def validate_pattern(review, role, occurrence, parser, index, read_json):
    parent = review.get('parent_span')
    member = MEMBERS.get(role['build'])
    if member is None:
        raise ValueError('Invalid socketed table pattern membership')
    klass, label = member
    if (
        review.get('pattern_kind') not in KINDS
        or (review.get('pattern_kind') == KIND and role['build'] != 'fissure-druid')
        or review.get('pattern_label') != label
        or role['id'] != role['build'] + '-perfect-topaz-general-armor'
        or role.get('names')
        or role.get('types') != ['tors']
        or set(role.get('qualities', ())) != {'normal', 'superior', 'low_quality'}
        or role.get('slot') != 'Body Armor'
        or occurrence['class'] != klass
        or type(parent) is not int
        or not 0 <= parent < len(parser.mentions)
    ):
        raise ValueError('Invalid socketed table pattern context')
    span = parser.mentions[parent]
    if (
        span['label'] != 'Gemmed Dusk Shroud'
        or parser.entry_labels[parent] != label
        or not parser.table_membership[parent]
        or not parser.positions[parent] <= parser.positions[index] < parser.entry_ends[parent]
        or occurrence['original_label'] != ('Gemmed Dusk Shroud' if index == parent else 'Perfect Topaz')
        or index not in (parent, parent + 1)
    ):
        raise ValueError('Socketed table pattern component is outside its complete armor entry')
    bases = list(metadata()['bases'].values())
    base = next(b['code'] for b in bases if b['name'] == 'Dusk Shroud')
    gem = next(b['code'] for b in bases if b['name'] == 'Perfect Topaz')
    for field, value in (
        ('base_code', base),
        ('name', 'Dusk Shroud'),
        ('sockets', 4),
        ('ethereal', False),
        ('identified', True),
    ):
        if not requires_eq(role.get('must', {}), 'fact_eq', field, value):
            raise ValueError('Socketed table pattern lost its base or socket requirements')
    expected = {
        'all': [
            {'op': 'socket_gems_equal', 'value': ['Perfect Topaz'] * 4},
            {'op': 'stat_at_least', 'key': '80:0', 'value': 96, 'absent_is_zero': True},
        ]
    }
    if not role_requires(role, expected):
        raise ValueError('Socketed table pattern lacks linked four-Topaz payload')
    planner_pin, gem_pin = review.get('planner', {}), review.get('gems', {})
    if (
        planner_pin.get('path') != f'pricing/raw/mr/planners/{span["profile_id"]}.json'
        or gem_pin.get('path') != 'third-parties/d2data/json/gems.json'
    ):
        raise ValueError('Socketed table pattern requires exact native witnesses')
    planner = decode_planner(read_json(planner_pin))
    item = planner['items'][span['item_id']]
    definition = read_json(gem_pin)[gem]
    if (
        item.get('base') != base
        or item.get('quality') != 1
        or item.get('sockets') != 4
        or item.get('socketedItems') != [gem] * 4
        or definition.get('name') != 'Perfect Topaz'
        or definition.get('helmMod1Code') != 'mag%'
        or definition.get('helmMod1Min') != 24
        or definition.get('helmMod1Max') != 24
    ):
        raise ValueError('Socketed table pattern native armor or gem effect differs')
