"""Gheed's Fortune table utility and independent farming/vendor rolls."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


GROUPS = (
    ('Warlock', (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))),
    (
        'Sorceress',
        (
            ('fire-wall-sorceress-guide', 30),
            ('frozen-orb-meteor-sorceress', 29),
            ('frozen-orb-sorceress', 29),
            ('hydra-sorceress', 29),
        ),
    ),
    ('Paladin', (('fist-of-the-heavens-paladin', 34),)),
)


def cases():
    item = Item('Grand Charm', 'unique', "Gheed's Fortune", raw_stats=((80, 0, 20), (79, 0, 80), (87, 0, 10)))
    for player_class, sources in GROUPS:
        roles = (
            tuple(g + '-gheed-s-fortune-gear-inventory-charm' for g, _ in sources)
            if player_class != 'Paladin'
            else ('fist-of-the-heavens-paladin-gheeds-farming-charm',)
        )
        context = {'player_class': player_class}
        for label, candidate, loadout, truth in (
            ('minimum-rolls', item, context, 'true'),
            ('maximum-rolls', replace(item, raw_stats=((80, 0, 40), (79, 0, 160), (87, 0, 15))), context, 'true'),
            ('mf-only-perfect', replace(item, raw_stats=((80, 0, 40), (79, 0, 80), (87, 0, 10))), context, 'true'),
            (
                'discount-only-perfect',
                replace(item, raw_stats=((80, 0, 20), (79, 0, 80), (87, 0, 15))),
                context,
                'true',
            ),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('impossible-ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('illegal-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
            ('wrong-class', item, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
        ):
            expected = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles))
            }
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*(role + '-stats' for role in roles)))
                            for key in ('80:0', '79:0', '87:0')
                        }
                    )
                )
                result['assessment'] = IsPartialDict(**expected)
                grades = {
                    'minimum-rolls': ('low', 'low', 'low'),
                    'maximum-rolls': ('perfect', 'perfect', 'perfect'),
                    'mf-only-perfect': ('perfect', 'low', 'low'),
                    'discount-only-perfect': ('low', 'low', 'perfect'),
                }[label]
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=low, max=high),
                                roll_quality=grade,
                            )
                            for (stat, low, high), grade in zip(
                                ((80, 20, 40), (79, 80, 160), (87, 10, 15)), grades, strict=True
                            )
                        )
                    )
                )
            yield Case(
                id=f'gheeds-table-roles/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                report_contains=("Gheed's Fortune", '(20-40%)', '(80-160%)', '(10-15%)', 'Trade tier:')
                if truth == 'true'
                else ('Grand Charm',),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/359',
                    *(
                        'pricing/data/appraisal-guide-sections.json:/sources/'
                        f'pricing~1raw~1mr~1guides__{g}.html/sections/{n}'
                        for g, n in sources
                    ),
                ),
            )


CASES = tuple(cases())
