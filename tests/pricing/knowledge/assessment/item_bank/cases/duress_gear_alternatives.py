"""Mercenary gear-table Duress uses, with explicit attack-bearer boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.duress_endgame_merc import duress
from tests.pricing.knowledge.assessment.item_bank.models import Case


SOURCES = (
    ('Warlock', (('blood-boil-warlock-guide', 40), ('summoner-warlock-guide', 40))),
    (
        'Sorceress',
        (
            ('fire-wall-sorceress-guide', 41),
            ('frozen-orb-meteor-sorceress', 40),
            ('frozen-orb-sorceress', 40),
            ('hydra-sorceress', 40),
        ),
    ),
    ('Paladin', (('zeal-paladin', 44),)),
)
KEYS = ('136:0', '135:0', '17:0', '18:0', '99:0', '39:0', '41:0', '43:0', '45:0')


def cases():
    for klass, sources in SOURCES:
        roles = tuple(build + '-duress-merc-survival-gear' for build, _ in sources)
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
                ('wrong-class', item, {**context, 'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', item, {'mercenary_type': 'Act 2 Might'}, 'unknown'),
                # Unlike Zeal's Cure alternative, this source rule is the Might branch only.
                ('wrong-mercenary', item, {**context, 'mercenary_type': 'Act 5 Frenzy'}, 'false'),
                ('unknown-mercenary', item, {'player_class': klass}, 'unknown'),
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
                                    'skills before choosing Duress.'
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
                                                configuration_id=config, role_id=role, desirability='desirable'
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
                    id=f'duress-gear-alternatives/{klass}/{quality}/{label}',
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
                        *(
                            f'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__{build}.html/sections/{section}'
                            for build, section in sources
                        ),
                        'third-parties/d2data/json/runes.json:/Duress',
                        'third-parties/d2data/json/gems.json:/r13',
                        'third-parties/d2data/json/gems.json:/r22',
                        'third-parties/d2data/json/gems.json:/r10',
                    ),
                )


CASES = tuple(cases())
