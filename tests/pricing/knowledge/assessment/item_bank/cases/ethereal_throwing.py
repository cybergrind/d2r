"""Double Throw's explicitly ethereal guide alternatives, through native decoding."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('gimmershred', 'Gimmershred', 'Flying Axe', 200),
    ('warshrike', 'Warshrike', 'Winged Knife', 200),
    ('lacerator', 'Lacerator', 'Winged Axe', 180),
    ('demon-s-arch', "Demon's Arch", 'Balrog Spear', 180),
    ('gargoyle-s-bite', "Gargoyle's Bite", 'Winged Harpoon', 200),
    ('deathbit', 'Deathbit', 'Flying Knife', 150),
)


def cases(kind='ethereal'):
    for slug, name, base, damage in SPECS:
        stats = ((17, 0, damage), (18, 0, damage))
        if name != 'Gimmershred':
            stats += ((253, 0, 25),)
        item = Item(base, 'unique', name, stats, ethereal=True)
        roles = tuple(
            f'double-throw-barbarian-guide-{slug}-{slot}-{kind}-throwing-alternative' for slot in ('weapon', 'off-hand')
        )
        variants = [
            ('ethereal', item, 'true'),
            ('nonethereal', replace(item, ethereal=False), 'false' if kind == 'ethereal' else 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), 'unknown' if kind == 'ethereal' else 'true'),
            ('unknown-sockets', replace(item, sockets=None), 'unknown'),
        ]
        if kind == 'named':
            variants.append(('invalid-sockets', replace(item, sockets=1), 'false'))
        if name == 'Deathbit':
            variants.append(('not-upgraded', replace(item, base='Battle Dart'), 'false'))
        for label, candidate, truth in variants:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {'17:0': IsPartialDict(configuration_ids=Contains(*(r + '-stats' for r in roles)))}
                    )
                )
            yield Case(
                id=f'double-throw/{"exact-ethereal" if kind == "ethereal" else "named-throwing"}/{slug}/{label}',
                item=candidate,
                context={'player_class': 'Barbarian'},
                expected={'assessment': IsPartialDict(**expected)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else tuple(r + '-stats' for r in roles),
                report_contains=('Trade tier:',),
                evidence=(
                    'pricing/data/wp-a-builds.json:/double-throw-barbarian-guide/slots',
                    'third-parties/d2data/json/uniqueitems.json',
                ),
            )


CASES = (*cases(), *cases('named'))
