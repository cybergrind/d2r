"""Source-enumerated Gheed inventory uses share farming utility, not combat fit."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


VARIANTS = {
    'double-throw-barbarian-guide': (1, 2),
    'dream-paladin': (0, 1),
    'echoing-strike-warlock-guide': (1, 2),
    'enchant-sorceress': (1, 2),
    'fire-blast-assassin': (1,),
    'fire-warlock-guide': (2,),
    'fissure-druid': (1, 2),
    'gold-find-barbarian': (0, 1, 2, 3),
    'lightning-fury-amazon-guide': (2,),
    'lightning-sentry-assassin': (2,),
    'lightning-sorceress': (0, 1, 2),
    'lightning-strike-amazon': (0, 1),
    'meteor-sorceress': (1, 2, 3),
    'mirrored-blades-warlock-guide': (1,),
    'nova-sorceress-guide': (1, 2, 3),
    'poison-nova-necromancer': (1, 2),
    'strafe-amazon': (2,),
    'summoner-necromancer-guide': (1, 2),
    'wake-of-fire-assassin': (1,),
}
ROLES = tuple(f'{g}-{v}-gheeds-inventory' for g, vs in VARIANTS.items() for v in vs)


def cases():
    item = Item('Grand Charm', 'unique', "Gheed's Fortune", raw_stats=((80, 0, 20), (79, 0, 80), (87, 0, 10)))
    for label, candidate, truth, scenario, keys in (
        ('minimum', item, 'true', 'positive', ('80:0', '79:0', '87:0')),
        (
            'perfect',
            replace(item, raw_stats=((80, 0, 40), (79, 0, 160), (87, 0, 15))),
            'true',
            'positive',
            ('80:0', '79:0', '87:0'),
        ),
        ('unidentified', replace(item, identified=False), 'false', 'negative', ()),
        ('unread-stats', replace(item, raw_stats=(), complete=False), 'true', 'unknown', ()),
        (
            'unread-discount',
            replace(item, raw_stats=((80, 0, 20), (79, 0, 80)), complete=False),
            'true',
            'unknown',
            ('80:0', '79:0'),
        ),
        (
            'unread-mf',
            replace(item, raw_stats=((79, 0, 80), (87, 0, 10)), complete=False),
            'true',
            'unknown',
            ('79:0', '87:0'),
        ),
    ):
        expected = {
            'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
        }
        if keys:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in ROLES)))
                        for key in keys
                    }
                )
            )
        yield Case(
            id='gheeds-inventory-variants/' + label,
            item=candidate,
            context={},
            scenario=scenario,
            covers=ROLES,
            expected={'assessment': IsPartialDict(**expected)},
            absent_stat_configurations={
                key: tuple(role + '-stats' for role in ROLES) for key in ('80:0', '79:0', '87:0') if key not in keys
            },
            report_contains=("Gheed's Fortune", 'Trade tier:') if truth == 'true' else ('Grand Charm',),
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/359',
                *(
                    f'pricing/data/wp-a-builds.json:/{g}/variants/{v}/player/Charms'
                    for g, vs in VARIANTS.items()
                    for v in vs
                ),
            ),
        )


CASES = tuple(cases())
