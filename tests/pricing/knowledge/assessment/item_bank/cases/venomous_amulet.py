"""Maximum Poison/Bone amulets: exact tree, magic quality and optional suffix."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = tuple(f'poison-nova-necromancer-{variant}-venomous' for variant in ('starter', 'budget'))
CONFIGS = tuple(role + '-stats' for role in ROLES)
CAVEAT = 'Check the complete loadout for cast-rate breakpoints, resistances and equipment requirements.'


def cases():
    item = Item('Amulet', 'magic', raw_stats=((188, 17, 3),), affix_records=(('prefix', 462),), complete=True)
    context = {'player_class': 'Necromancer'}
    examples = [
        ('plain', item, context, 'true'),
        (
            'apprentice',
            replace(
                item, raw_stats=(*item.raw_stats, (105, 0, 10)), affix_records=(*item.affix_records, ('suffix', 174))
            ),
            context,
            'true',
        ),
        ('lower-tier', replace(item, raw_stats=((188, 17, 2),), affix_records=(('prefix', 461),)), context, 'false'),
        ('wrong-tree', replace(item, raw_stats=((188, 18, 3),), affix_records=(('prefix', 465),)), context, 'false'),
        ('absent-tree', replace(item, raw_stats=(), affix_records=()), context, 'false'),
        ('unread-tree', replace(item, raw_stats=(), complete=False), context, 'unknown'),
        ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', item, {}, 'unknown'),
        ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'false'),
        ('rare', replace(item, rarity='rare', affix_records=None), context, 'false'),
        ('wrong-slot', replace(item, base='Circlet'), context, 'false'),
    ]
    for label, candidate, loadout, truth in examples:
        active = truth == 'true'
        expected = {}
        if label not in ('unidentified', 'rare', 'wrong-slot'):
            expected['roles'] = Contains(
                *(
                    IsPartialDict(
                        id=role, slot='Amulet', rule_trace=IsPartialDict(truth=truth), missing=Contains(CAVEAT)
                    )
                    for role in ROLES
                )
            )
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        '188:17': IsPartialDict(
                            contributions=Contains(
                                *(
                                    IsPartialDict(configuration_id=config, desirability='desirable')
                                    for config in CONFIGS
                                )
                            )
                        ),
                    }
                )
            )
        yield Case(
            id=f'venomous-amulet/{label}',
            item=candidate,
            context=loadout,
            covers=tuple('role:' + role + ':magic' for role in ROLES),
            scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if active else CONFIGS,
            absent_stat_configurations={'105:0': CONFIGS, '188:18': CONFIGS},
            report_contains=(
                '[desirable] +3 (1-3) to Poison and Bone Skills (Necromancer Only) [T1; T1: 3-3]',
                'conditional: Poison Nova Necromancer',
            )
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/poison-nova-necromancer/variants/0/player/Amulet/0',
                'pricing/data/wp-a-builds.json:/poison-nova-necromancer/variants/4/player/Amulet/0',
                'third-parties/d2data/json/magicprefix.json:/462',
                'third-parties/d2data/json/magicsuffix.json:/174',
            ),
        )


CASES = tuple(cases())
