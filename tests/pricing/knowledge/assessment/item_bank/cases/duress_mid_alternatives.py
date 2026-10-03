"""Native mid-game Duress options retain attack and corpse-shatter conditions."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.duress_endgame_merc import duress
from tests.pricing.knowledge.assessment.item_bank.models import Case


SOURCES = (
    (
        'Sorceress',
        ('blizzard-sorceress', 'enchant-sorceress', 'lightning-sorceress', 'meteor-sorceress', 'nova-sorceress-guide'),
    ),
    ('Barbarian', ('double-throw-barbarian-guide', 'gold-find-barbarian')),
    ('Paladin', ('dream-paladin', 'fist-of-the-heavens-paladin')),
    ('Assassin', ('fire-blast-assassin', 'lightning-sentry-assassin')),
    ('Warlock', ('fire-warlock-guide', 'mirrored-blades-warlock-guide')),
    ('Druid', ('fissure-druid',)),
    ('Amazon', ('lightning-fury-amazon-guide', 'lightning-strike-amazon', 'strafe-amazon')),
    ('Necromancer', ('poison-nova-necromancer', 'summoner-necromancer-guide')),
)

KEYS = ('136:0', '135:0', '17:0', '18:0', '99:0', '39:0', '41:0', '43:0', '45:0')


def cases():
    for klass, sources in SOURCES:
        roles = tuple(build + '-duress-mid-merc-resistance-alternative' for build in sources)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass, 'mercenary_type': 'Act 2 Might'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = duress(quality)
            examples = [
                (f'rolls-{damage}-{defense}', duress(quality, damage, defense), context, 'true')
                for damage in (10, 20)
                for defense in (150, 200)
            ]
            examples += [
                ('ethereal', replace(item, ethereal=True), context, 'true'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'true'),
                ('elite-base', replace(item, base='Dusk Shroud'), context, 'true'),
                ('insufficient-capacity', replace(item, base='Quilted Armor'), context, 'false'),
                (
                    'wrong-class',
                    item,
                    {**context, 'player_class': 'Barbarian' if klass == 'Warlock' else 'Warlock'},
                    'false',
                ),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                # These generic table entries retain attack/equip caveats instead of naming a bearer.
                ('unspecified-bearer', item, {'player_class': klass}, 'true'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ]
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                expected = {
                    'roles': Contains(
                        *(
                            IsPartialDict(
                                id=role,
                                side='merc',
                                rule_trace=IsPartialDict(truth=truth),
                                missing=Contains(
                                    'Cold damage can shatter corpses; consider Find Item or corpse-dependent '
                                    'skills before choosing Duress.',
                                    'Crushing Blow, Open Wounds and off-weapon damage need eligible attacks, '
                                    'not mercenary spells. Duress supplies no life leech.',
                                ),
                            )
                            for role in roles
                        )
                    )
                }
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    configuration_ids=Contains(*configs),
                                    contributions=Contains(
                                        *(
                                            IsPartialDict(
                                                configuration_id=config,
                                                role_id=role,
                                                desirability='desirable' if key in {'136:0', '135:0'} else 'supporting',
                                            )
                                            for role, config in zip(roles, configs, strict=True)
                                        )
                                    ),
                                )
                                for key in KEYS
                            }
                        )
                    )
                yield Case(
                    id=f'duress-mid-alternatives/{klass}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario='unknown' if label.startswith('unknown-') else 'positive' if active else 'negative',
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else configs,
                    absent_stat_configurations=dict.fromkeys(('60:0', '1:0', '3:0'), configs),
                    report_contains=(
                        'Duress',
                        'Shael, Um, Thul',
                        '15% Chance of Crushing Blow',
                        '33% Chance of Open Wounds',
                    )
                    if active
                    else (),
                    report_absent=('Life stolen per hit',),
                    evidence=(
                        *(f'pricing/data/wp-a-builds.json:/{build}/merc/Body Armor/mid/1' for build in sources),
                        'third-parties/d2data/json/runes.json:/Duress',
                        'third-parties/d2data/json/gems.json:/r13',
                        'third-parties/d2data/json/gems.json:/r22',
                        'third-parties/d2data/json/gems.json:/r10',
                    ),
                )


CASES = tuple(cases())
