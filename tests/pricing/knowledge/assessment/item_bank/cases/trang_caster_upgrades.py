"""Upgrade recognition must preserve each caster role's wearer and stat semantics."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BUILDS = (
    ('blood-boil-warlock-guide', 'Warlock'),
    ('summoner-warlock-guide', 'Warlock'),
    ('fire-wall-sorceress-guide', 'Sorceress'),
    ('frozen-orb-meteor-sorceress', 'Sorceress'),
    ('frozen-orb-sorceress', 'Sorceress'),
    ('hydra-sorceress', 'Sorceress'),
)


def cases():
    original = Item(
        'Heavy Bracers',
        'set',
        "Trang-Oul's Claws",
        (
            (105, 0, 20),
            (43, 0, 30),
            (31, 0, 67),
            (188, 16, 2),
        ),
    )
    for build, wearer in BUILDS:
        role = build + '-trang-oul-s-claws-caster-gear-alternative'
        for base in ('Heavy Bracers', 'Vambraces'):
            item = replace(original, base=base)
            for label, candidate, context, truth in (
                ('native-or-upgraded', item, {'player_class': wearer}, 'true'),
                ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), {'player_class': wearer}, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), {'player_class': wearer}, 'unknown'),
                ('invalid-sockets', replace(item, sockets=1), {'player_class': wearer}, 'false'),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                for key in ('105:0', '43:0', '31:0')
                            }
                        )
                    )
                yield Case(
                    id=f'trang-caster-upgrades/{build}/{base}/{label}',
                    item=candidate,
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations={'188:16': (role + '-stats',)},
                    report_contains=("Trang-Oul's Claws",),
                    evidence=('third-parties/d2data/json/cubemain.json', 'pricing/data/appraisal-guide-sections.json'),
                )


CASES = tuple(cases())
