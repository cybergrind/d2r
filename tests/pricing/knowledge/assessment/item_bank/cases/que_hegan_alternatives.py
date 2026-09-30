"""Que-Hegan's defensive caster benefits do not award mana for demon kills."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GUIDES = ('blood-boil-warlock-guide', 'summoner-warlock-guide')
ROLES = tuple(f'{guide}-que-hegan-s-wisdom-caster-armor-remainder' for guide in GUIDES)
STATS = ((127, 0, 1), (105, 0, 20), (99, 0, 20), (138, 0, 3), (35, 0, 6), (1, 0, 15), (16, 0, 140))


def cases():
    item = Item('Mage Plate', 'unique', "Que-Hegan's Wisdom", STATS)
    context = {'player_class': 'Warlock'}
    examples = (
        ('minimum-rolls', item, context, 'positive'),
        (
            'maximum-rolls',
            replace(
                item, raw_stats=tuple((stat, layer, {35: 10, 16: 160}.get(stat, value)) for stat, layer, value in STATS)
            ),
            context,
            'positive',
        ),
        ('upgraded', replace(item, base='Archon Plate'), context, 'positive'),
        ('open-socket', replace(item, sockets=1), context, 'positive'),
        ('unread-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'positive'),
        ('ethereal', replace(item, ethereal=True), context, 'negative'),
        ('unread-ethereal', replace(item, ethereal=None), context, 'unknown'),
        ('unidentified', replace(item, identified=False), context, 'negative'),
        ('wrong-class', item, {'player_class': 'Barbarian'}, 'negative'),
        ('unread-class', item, {}, 'unknown'),
        ('too-many-sockets', replace(item, sockets=2), context, 'negative'),
        ('unread-sockets', replace(item, sockets=None), context, 'unknown'),
    )
    configs = tuple(role + '-stats' for role in ROLES)
    for label, candidate, loadout, scenario in examples:
        expected = {
            'roles': Contains(
                *(
                    IsPartialDict(
                        id=role,
                        rule_trace=IsPartialDict(
                            truth={
                                'positive': 'true',
                                'negative': 'false',
                                'unknown': 'unknown',
                            }[scenario]
                        ),
                    )
                    for role in ROLES
                )
            )
        }
        if scenario == 'positive':
            annotations = {
                key: IsPartialDict(configuration_ids=Contains(*configs))
                for key in ('127:0', '105:0', '99:0', '35:0', '1:0', '16:0')
            }
            annotations['138:0'] = IsPartialDict(configuration_ids=Contains(configs[0]))
            expected['stat_evaluation'] = IsPartialDict(annotations=IsPartialDict(annotations))
        yield Case(
            id=f'que-hegan-alternative/{label}',
            item=candidate,
            context=loadout,
            scenario=scenario,
            covers=ROLES,
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if scenario == 'positive' else configs,
            absent_stat_configurations={'138:0': (configs[1],)},
            report_contains=("Que-Hegan's Wisdom",),
            evidence=(
                *(
                    f'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__{guide}.html/sections/29'
                    for guide in GUIDES
                ),
                'third-parties/d2data/json/uniqueitems.json:/223',
            ),
        )


CASES = tuple(cases())
