"""Belt utility benefits must bind to the intended build and wearer context."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    (
        'Arachnid Mesh',
        'Spiderweb Sash',
        'arachnid-mesh',
        ((127, 0, 1), (105, 0, 20), (77, 0, 5), (150, 0, 10)),
        ('105:0', '150:0'),
    ),
    ('Goldwrap', 'Heavy Belt', 'goldwrap', ((80, 0, 30), (79, 0, 50), (93, 0, 10)), ('80:0', '93:0')),
    (
        "Thundergod's Vigor",
        'War Belt',
        'thundergod-s-vigor',
        ((42, 0, 10), (145, 0, 20), (0, 0, 20), (3, 0, 20)),
        ('42:0', '145:0'),
    ),
)


def cases():
    result = []
    for name, base, slug, stats, keys in SPECS:
        role = slug + '-zeal-utility-belt'
        for scenario, context, status in (
            ('positive', {'player_class': 'Paladin'}, 'partial'),
            ('negative', {'player_class': 'Necromancer'}, 'failed'),
            ('unknown', {}, 'partial'),
        ):
            expected = {
                'roles': Contains(
                    IsPartialDict(
                        id=role,
                        build='zeal-paladin',
                        status=status,
                        rule_trace=IsPartialDict(
                            truth={'positive': 'true', 'negative': 'false', 'unknown': 'unknown'}[scenario]
                        ),
                    )
                )
            }
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
            result.append(
                Case(
                    id='zeal/utility-belts/' + slug + '/' + scenario,
                    item=Item(base, 'unique', name, stats),
                    context=context,
                    expected={'assessment': IsPartialDict(**expected)},
                    covers=(role,),
                    scenario=scenario,
                    absent_configurations=() if scenario == 'positive' else (role + '-stats',),
                    report_contains=(name, 'Trade tier:'),
                    evidence=(
                        'pricing/raw/mr/guides__zeal-paladin.html:gear-table',
                        'third-parties/d2data/json/uniqueitems.json',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
