"""Ormus alternatives credit matching spell elements and optional legal skill rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = (
    ('fire-wall-sorceress-guide', 30, ('329:0',), 51),
    ('frozen-orb-meteor-sorceress', 29, ('329:0', '331:0'), 56),
    ('frozen-orb-sorceress', 29, ('331:0',), None),
    ('hydra-sorceress', 29, ('329:0',), None),
)
MINIMUM = ((105, 0, 20), (27, 0, 10), (31, 0, 10), (329, 0, 10), (330, 0, 10), (331, 0, 10))
MAXIMUM = ((105, 0, 20), (27, 0, 15), (31, 0, 20), (329, 0, 15), (330, 0, 15), (331, 0, 15))


def cases():
    item = Item('Dusk Shroud', 'unique', "Ormus' Robes", (*MINIMUM, (107, 36, 3)))
    context = {'player_class': 'Sorceress'}
    roles = tuple(f'{guide}-ormus-robes-caster-armor-remainder' for guide, *_ in USES)
    examples = [
        ('unrelated-fire-bolt', item, context, 'positive', 36),
        ('maximum-rolls', replace(item, raw_stats=(*MAXIMUM, (107, 36, 3))), context, 'positive', 36),
        ('fire-wall-roll', replace(item, raw_stats=(*MINIMUM, (107, 51, 3))), context, 'positive', 51),
        ('meteor-roll', replace(item, raw_stats=(*MINIMUM, (107, 56, 3))), context, 'positive', 56),
        ('unread-skill', replace(item, raw_stats=MINIMUM, complete=False), context, 'positive', None),
        ('open-socket', replace(item, sockets=1), context, 'positive', 36),
        ('unread-socket-payload', replace(item, sockets=1, socket_contents='unknown'), context, 'positive', 36),
        ('ethereal', replace(item, ethereal=True), context, 'negative', 36),
        ('unread-ethereal', replace(item, ethereal=None), context, 'unknown', 36),
        ('unidentified', replace(item, identified=False), context, 'negative', 36),
        ('wrong-class', item, {'player_class': 'Barbarian'}, 'negative', 36),
        ('unread-class', item, {}, 'unknown', 36),
        ('too-many-sockets', replace(item, sockets=2), context, 'negative', 36),
        ('unread-sockets', replace(item, sockets=None), context, 'unknown', 36),
    ]
    for label, candidate, loadout, scenario, skill in examples:
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
                    for role in roles
                )
            )
        }
        present = {}
        absent = {}
        for role, (_, _, elements, matching_skill) in zip(roles, USES, strict=True):
            config = role + '-stats'
            keys = ('105:0', '27:0', '31:0', *elements)
            if skill is not None and skill == matching_skill:
                keys = (*keys, f'107:{skill}')
            if scenario == 'positive':
                for key in keys:
                    present.setdefault(key, []).append(config)
            for key in ('329:0', '330:0', '331:0', '107:36', '107:51', '107:56', '107:62', '107:64'):
                if key not in keys:
                    absent.setdefault(key, []).append(config)
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {key: IsPartialDict(configuration_ids=Contains(*configs)) for key, configs in present.items()}
                )
            )
        yield Case(
            id=f'ormus-alternative/{label}',
            item=candidate,
            context=loadout,
            scenario=scenario,
            covers=roles,
            expected={'assessment': IsPartialDict(**expected)},
            absent_configurations=() if scenario == 'positive' else tuple(role + '-stats' for role in roles),
            absent_stat_configurations={key: tuple(configs) for key, configs in absent.items()},
            report_contains=("Ormus' Robes",),
            evidence=(
                *(
                    f'pricing/data/appraisal-guide-sections.json:/sources/'
                    f'pricing~1raw~1mr~1guides__{guide}.html/sections/{section}'
                    for guide, section, *_ in USES
                ),
                'third-parties/d2data/json/uniqueitems.json:/358',
                *(f'third-parties/d2data/json/skills.json:/{skill}' for skill in (36, 51, 56, 62, 64)),
            ),
        )


CASES = tuple(cases())
