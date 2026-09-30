"""Tal Rasha caster alternatives: intrinsic stats and distinct-piece activation."""

from itertools import combinations

from pricing.knowledge.assessment.maintenance.caster_core_templates import BUILDS
from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


PIECES = (
    "Tal Rasha's Guardianship",
    "Tal Rasha's Horadric Crest",
    "Tal Rasha's Fine-Spun Cloth",
    "Tal Rasha's Lidless Eye",
    "Tal Rasha's Adjudication",
)
MEMBERS = {
    PIECES[0]: ('Body Armor', ('80:0', '39:0', '41:0', '43:0', '35:0', '31:0')),
    PIECES[1]: ('Helmet', ('7:0', '9:0', '31:0', '39:0', '41:0', '43:0', '45:0')),
    PIECES[2]: ('Belt', ('9:0', '2:0', '114:0', '80:0')),
    PIECES[3]: ('Weapon', ('7:0', '9:0', '1:0', '105:0')),
}
FIRE = frozenset(('fire-wall-sorceress-guide', 'hydra-sorceress', 'frozen-orb-meteor-sorceress'))
COLD = frozenset(('frozen-orb-sorceress', 'frozen-orb-meteor-sorceress'))


def companions(name, klass, count):
    others = [p for p in PIECES if p != name and (klass == 'Sorceress' or p != PIECES[3])]
    return {
        'any': [
            {'all': [{'op': 'context_contains', 'field': 'player_items', 'value': p} for p in group]}
            for group in combinations(others, count - 1)
        ]
    }


def tal_priority(row, key):
    name = row['item']
    count = {
        PIECES[0]: {'105:0': 2},
        PIECES[2]: {'31:0': 2, '105:0': 3},
        PIECES[3]: {'83:1': 2, '333:0': 3, '331:0': 5},
    }.get(name, {}).get(key)
    minimum = {'105:0': 10, '31:0': 60, '333:0': 15, '331:0': 15}.get(key, 1) if count else 1
    observed = {'op': 'stat_at_least', 'key': key, 'value': minimum, 'absent_is_zero': True}
    return {'all': [companions(name, row['class'], count), observed]} if count else observed


def expand_tal_caster(row):
    name = row['item']
    if (
        name not in MEMBERS
        or BUILDS.get(row['build']) != row['class']
        or row['side'] != 'player'
        or row['slot'] != MEMBERS[name][0]
        or (row['class'] != 'Sorceress' and name != PIECES[0])
    ):
        raise ValueError('Unreviewed Tal caster alternative')
    definition = catalog().named['set', name]
    maximum = 0 if row['slot'] == 'Belt' else 1
    stats = list(MEMBERS[name][1])
    if name == PIECES[0]:
        stats.append('105:0')
    elif name == PIECES[2]:
        stats.extend(('31:0', '105:0'))
    elif name == PIECES[3]:
        stats.append('83:1')
        if row['build'] in FIRE:
            stats.extend(('107:61', '333:0'))
        if row['build'] in COLD:
            stats.extend(('107:65', '331:0'))
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': row['class']},
        {'op': 'fact_eq', 'field': 'identified', 'value': True},
        named_base_condition(name, 'set'),
        {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in range(maximum + 1)]},
    ]
    if not maximum:
        must.append({'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'})
    conditions = [
        'Intrinsic item bonuses are separate from partial bonuses. Partial bonuses require the observed stat '
        'and enough distinct compatible equipped set pieces; duplicate names do not count twice. '
        'The appraised piece counts once. No complete loadout or socket filler is inferred.',
        'Armor casting speed needs two pieces; belt defense needs two and casting speed three. '
        'Orb Sorceress Skills needs two pieces, fire pierce three, and Cold Skill Damage all five. '
        'The class-exclusive orb cannot count as an equipped Warlock companion.',
        'Mastery and resistance modifiers apply to the relevant wearer spells. Lightning Mastery '
        'and lightning pierce are not credited to these fire/cold builds. Helmet leech does not '
        'heal a caster from ordinary spell or summoned-minion damage. Damage Taken Goes to Mana '
        'is recovery from eligible damage, not damage reduction.',
        'Whole-set bonuses are separate; do not infer them from owning a single piece or from '
        'an aggregate item stat. Respect casting breakpoints, requirements and survival needs.',
    ]
    dependencies = []
    if name == PIECES[3]:
        dependencies.append(
            {
                'label': 'The guide recommends Lidless Eye only with other Tal Rasha pieces.',
                'when': companions(name, row['class'], 2),
            }
        )
        conditions.append(
            'The gear-table footnote excludes a standalone orb recommendation. At least one '
            'other compatible piece establishes a combination candidate; this does not establish '
            'the three-piece fire or five-piece cold setup.'
        )
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': 'Tal Rasha caster gear alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [definition['base_definition']['type']],
        'qualities': ['set'],
        'must': {'all': must},
        'depends_on': dependencies,
        'important_stats': stats,
        'conditions': conditions,
    }
