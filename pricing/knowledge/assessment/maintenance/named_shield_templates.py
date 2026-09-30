"""Named shields with explicit filler and partial-set conditions."""

from itertools import combinations

from pricing.knowledge.assessment.maintenance.native_membership import named_base_condition
from pricing.knowledge.definition_store import catalog


def shield_setup(name, build):
    if name == "Griswold's Honor":
        return {'op': 'socket_runes_equal', 'value': ['Ist Rune'] * 3}
    if build == 'poison-nova-necromancer':
        others = ("Trang-Oul's Guise", "Trang-Oul's Scales", "Trang-Oul's Claws", "Trang-Oul's Girth")
        return {
            'any': [
                {'all': [{'op': 'context_contains', 'field': 'player_items', 'value': n} for n in pair]}
                for pair in combinations(others, 2)
            ]
        }
    return None


def expand_named_shield(row):
    name, build = row['item'], row['build']
    if name == "Griswold's Honor":
        klass, builds = 'Paladin', ('zeal-paladin',)
        sockets = (3,)
        stats = ['31:0', '102:0', '20:0', '39:0', '41:0', '43:0', '45:0', '80:0']
        role = 'Three-Ist Zeal magic-find shield alternative'
        conditions = [
            'The source specifies three Ist runes. Shield blocking, FBR and resistances remain '
            'separate from the filler magic find. No additional Griswold set bonus or full block '
            'chance is inferred; Dexterity and character level still matter.'
        ]
    elif name == "Trang-Oul's Wing":
        klass, builds = 'Necromancer', ('poison-nova-necromancer', 'summoner-necromancer-guide')
        sockets = (0, 1)
        stats = ['188:17', '31:0', '0:0', '2:0', '39:0', '45:0', '20:0']
        role = 'Poison/Bone skill and defensive shield alternative'
        conditions = [
            'Poison and Bone skills support Poison Nova or Corpse Explosion; they do not add '
            'Raise Skeleton or Skeleton Mastery levels. Full block chance depends on level and '
            'Dexterity. No socket filler, four-piece regeneration or full-set transformation is assumed.'
        ]
        if build == 'poison-nova-necromancer':
            stats.append('336:0')
            conditions.append(
                'Enemy poison resistance reduction requires three distinct active Trang pieces '
                'including this shield. Duplicated pieces do not count; this is separate from '
                'the gloves poison skill damage. Breaking poison immunity needs other effects.'
            )
    else:
        raise ValueError('Unreviewed named shield')
    if row['class'] != klass or build not in builds or row['side'] != 'player' or row['slot'] != 'Off-Hand':
        raise ValueError('Unreviewed named shield context')
    dependency = shield_setup(name, build)
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': role,
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': [catalog().named['set', name]['base_definition']['type']],
        'qualities': ['set'],
        'must': {
            'all': [
                {'op': 'context_eq', 'field': 'player_class', 'value': klass},
                {'op': 'fact_eq', 'field': 'identified', 'value': True},
                {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
                named_base_condition(name, 'set'),
                {'any': [{'op': 'fact_eq', 'field': 'sockets', 'value': n} for n in sockets]},
            ]
        },
        'depends_on': (
            [{'label': 'Match the source fillers or distinct active set companions.', 'when': dependency}]
            if dependency
            else []
        ),
        'important_stats': stats,
        'conditions': conditions,
    }
