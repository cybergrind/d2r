"""Caster Crown of Ages alternatives retain minimum rolls and native socket limits."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('warlock', 'Warlock', ('blood-boil-warlock-guide', 'summoner-warlock-guide')),
    (
        'sorceress',
        'Sorceress',
        ('frozen-orb-sorceress', 'frozen-orb-meteor-sorceress', 'fire-wall-sorceress-guide', 'hydra-sorceress'),
    ),
)
STATS = ((127, 0, 1), (99, 0, 30), (36, 0, 10), (16, 0, 50), *((sid, 0, 20) for sid in (39, 41, 43, 45)))
ITEM = Item('Corona', 'unique', 'Crown of Ages', STATS, sockets=1)


def cases():
    for slug, player_class, builds in SPECS:
        roles = tuple(build + '-crown-of-ages-caster-defense-gear' for build in builds)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': player_class}
        rows = (
            ('one-socket-minimum', ITEM, context, 'true'),
            ('two-sockets-minimum', replace(ITEM, sockets=2), context, 'true'),
            (
                'maximum-resistance-reduction',
                replace(
                    ITEM,
                    sockets=2,
                    raw_stats=tuple(
                        (sid, layer, 15 if sid == 36 else 30 if sid in (39, 41, 43, 45) else value)
                        for sid, layer, value in STATS
                    ),
                ),
                context,
                'true',
            ),
            ('unknown-contents', replace(ITEM, socket_contents='unknown'), context, 'true'),
            ('zero-sockets', replace(ITEM, sockets=0), context, 'false'),
            ('three-sockets', replace(ITEM, sockets=3), context, 'false'),
            ('unknown-sockets', replace(ITEM, sockets=None), context, 'unknown'),
            ('ethereal', replace(ITEM, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
            ('unidentified', replace(ITEM, identified=False), context, 'false'),
            ('wrong-class', ITEM, {'player_class': 'Barbarian'}, 'false'),
            ('unknown-class', ITEM, {}, 'unknown'),
        )
        for label, item, loadout, truth in rows:
            expected = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles))
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*configs))
                            for key in ('127:0', '99:0', '36:0', '16:0', '39:0', '41:0', '43:0', '45:0')
                        }
                    )
                )
            yield Case(
                id=f'caster-crown-ages/{slug}/{label}',
                item=item,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else configs,
                report_contains=('Crown of Ages', 'Trade tier:', '(10-15%)', '(20-30%)')
                if truth == 'true' and label != 'unknown-contents'
                else ('Crown of Ages',),
                report_absent=('(10-15%)', '(20-30%)') if label == 'unknown-contents' else (),
                evidence=(
                    'pricing/data/appraisal-guide-sections.json',
                    'third-parties/d2data/json/uniqueitems.json:/344',
                ),
            )


CASES = tuple(cases())
