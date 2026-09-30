"""Seraph's skill contribution is distinct from its weapon-only monster bonuses."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BUILDS = (('dream-paladin', 6), ('fist-of-the-heavens-paladin', 1), ('smite-paladin', 1))
ROLES = tuple(build + '-seraph-s-hymn-jewelry-casting-alternative' for build, _ in BUILDS)
CONFIGS = tuple(role + '-stats' for role in ROLES)
RAW = ((127, 0, 2), (188, 26, 1), (121, 0, 25), (122, 0, 25), (123, 0, 150), (124, 0, 150), (89, 0, 2))
ITEM = Item('Amulet', 'unique', "Seraph's Hymn", RAW, named_table_id=302)


def cases():
    context = {'player_class': 'Paladin'}
    for label, item, ctx, truth in (
        ('minimum-rolls', ITEM, context, 'true'),
        (
            'maximum-rolls',
            replace(
                ITEM,
                raw_stats=(
                    (127, 0, 2),
                    (188, 26, 2),
                    (121, 0, 50),
                    (122, 0, 50),
                    (123, 0, 250),
                    (124, 0, 250),
                    (89, 0, 2),
                ),
            ),
            context,
            'true',
        ),
        ('wrong-class', ITEM, {'player_class': 'Sorceress'}, 'false'),
        ('unknown-class', ITEM, {}, 'unknown'),
        ('unknown-ethereal', replace(ITEM, ethereal=None), context, 'unknown'),
        ('invalid-ethereal', replace(ITEM, ethereal=True), context, 'false'),
        ('invalid-socket', replace(ITEM, sockets=1, raw_stats=(*RAW, (194, 0, 1))), context, 'false'),
        ('unknown-sockets', replace(ITEM, sockets=None, socket_contents='unknown'), context, 'unknown'),
        ('unidentified', replace(ITEM, identified=False), context, 'false'),
    ):
        active = truth == 'true'
        expected = {
            'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in ROLES))
        }
        if active:
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        '127:0': IsPartialDict(configuration_ids=Contains(*CONFIGS)),
                        **{
                            key: IsPartialDict(configuration_ids=Contains(CONFIGS[0]))
                            for key in ('121:0', '122:0', '123:0', '124:0')
                        },
                    }
                )
            )
        yield Case(
            id='seraph-paladin-uses/' + label,
            item=item,
            context=ctx,
            covers=ROLES,
            scenario='positive' if active else 'unknown' if truth == 'unknown' else 'negative',
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if active else CONFIGS,
            absent_stat_configurations=dict.fromkeys(('121:0', '122:0', '123:0', '124:0'), CONFIGS[1:]),
            report_contains=("Seraph's Hymn", 'Trade tier:', '+2 to All Skills', '(1-2)') if active else (),
            evidence=(
                *(f'pricing/data/wp-a-builds.json:/{build}/slots/Amulets/{index}' for build, index in BUILDS),
                'third-parties/d2data/json/uniqueitems.json:/302',
            ),
        )


CASES = tuple(cases())
