"""Guide progression alternatives require completed words and wearable legal bases."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_helmets import EXAMPLES as HELMETS
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    (
        'lore',
        next(item for slug, item, _ in HELMETS if slug == 'lore'),
        ('127:0', '41:0', '34:0', '138:0', '1:0'),
        'Circlet',
        'Mask',
    ),
    (
        'ancients-pledge',
        Item(
            'Kite Shield',
            'normal',
            "Ancients' Pledge",
            ((39, 0, 48), (41, 0, 48), (43, 0, 43), (45, 0, 48), (16, 0, 50)),
            sockets=3,
            socket_contents='filled',
            runeword="Ancients' Pledge",
        ),
        ('39:0', '41:0', '43:0', '45:0'),
        'Large Shield',
        'Tower Shield',
    ),
)


def cases():
    for slug, original, keys, alternate, second in EXAMPLES:
        role = f'abyss-warlock-build-guide-{slug}-progression-equipment'
        context = {'player_class': 'Warlock'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(original, rarity=quality)
            rows = (
                ('complete', item, context, 'true'),
                ('alternate-base', replace(item, base=alternate), context, 'true'),
                ('second-base', replace(item, base=second), context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('wrong-count', replace(item, sockets=item.sockets - 1), context, 'false'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'abyss/progression-words/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    report_contains=(item.name,),
                    evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/runes.json'),
                )


CASES = tuple(cases())
