"""Caster armor-table Enigma uses accept legal bases, not ethereal or empty armor."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    (
        'warlock',
        'Warlock',
        ('blood-boil-warlock-guide-enigma-caster-armor-gear', 'summoner-warlock-guide-enigma-caster-armor-gear'),
    ),
    ('necromancer', 'Necromancer', ('summoner-necromancer-guide-enigma-caster-armor-gear',)),
)
STATS = ((127, 0, 2), (97, 54, 1), (96, 0, 45), (36, 0, 8), (76, 0, 5), (220, 0, 6), (240, 0, 8), (194, 0, 3))


def cases():
    for slug, player_class, roles in SPECS:
        context = {'player_class': player_class}
        configs = tuple(role + '-stats' for role in roles)
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                'Mage Plate',
                quality,
                'Enigma',
                STATS,
                sockets=3,
                socket_contents='filled',
                runeword='Enigma',
                socket_items=tuple(SocketItem(name + ' Rune') for name in ('Jah', 'Ith', 'Ber')),
            )
            native = NativeRunewordItem(**vars(item))
            rows = (
                ('native-recipe', native, context, 'true'),
                (
                    'wrong-rune-order',
                    replace(native, socket_items=tuple(reversed(native.socket_items))),
                    context,
                    'unknown',
                ),
                ('archon-plate', replace(native, base='Archon Plate'), context, 'true'),
                ('breast-plate', replace(native, base='Breast Plate'), context, 'true'),
                ('ethereal', replace(native, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('empty-sockets', replace(item, socket_contents='empty', socket_items=()), context, 'false'),
                ('unknown-contents', replace(item, socket_contents='unknown', socket_items=()), context, 'unknown'),
                (
                    'wrong-count',
                    replace(item, sockets=2, raw_stats=(*STATS[:-1], (194, 0, 2)), socket_items=item.socket_items[:2]),
                    context,
                    'false',
                ),
                ('wrong-class', native, {'player_class': 'Barbarian'}, 'false'),
                ('unknown-class', native, {}, 'unknown'),
            )
            for label, candidate, loadout, truth in rows:
                expected = {
                    'roles': Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                }
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(configuration_ids=Contains(*configs))
                                for key in ('127:0', '97:54', '96:0')
                            }
                        )
                    )
                yield Case(
                    id=f'caster-enigma-gear/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**({} if label == 'wrong-rune-order' else expected)),
                        **(
                            {
                                'extraction': IsPartialDict(item=IsPartialDict(runeword=None)),
                                'price_estimate': IsPartialDict(estimate_ist=None),
                            }
                            if label == 'wrong-rune-order'
                            else {}
                        ),
                    },
                    covers=roles,
                    scenario='negative'
                    if label == 'wrong-rune-order'
                    else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else configs,
                    absent_roles=roles if label == 'wrong-rune-order' else (),
                    report_contains=('Enigma', 'Sockets: 3 — Jah, Ith, Ber')
                    if truth == 'true'
                    else ('Mage Plate',)
                    if label == 'wrong-rune-order'
                    else ('Enigma',),
                    evidence=(
                        'pricing/data/appraisal-guide-sections.json',
                        'third-parties/d2data/json/runes.json:/Enigma',
                    ),
                )


CASES = tuple(cases())
