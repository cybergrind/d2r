"""Native Enigma variants retain the independently reviewed build/base boundaries."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem
from tests.pricing.knowledge.assessment.test_enigma_priorities import MEMBERS


def cases():
    # MEMBERS is an independently authored test bank, not production profile data.
    for build, variant, cls, base in MEMBERS:
        role = f'{build}-{variant}-player-enigma'
        context = {'player_class': cls}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(
                base,
                quality,
                'Enigma',
                (
                    (127, 0, 2),
                    (97, 54, 1),
                    (96, 0, 45),
                    (36, 0, 8),
                    (76, 0, 5),
                    (220, 0, 6),
                    (240, 0, 8),
                    (31, 0, 750),
                    (194, 0, 3),
                ),
                ethereal=False,
                sockets=3,
                socket_contents='filled',
                runeword='Enigma',
                socket_items=tuple(SocketItem(n) for n in ('Jah Rune', 'Ith Rune', 'Ber Rune')),
            )
            yield Case(
                id=f'enigma-quality/{build}/{variant}/{quality}',
                item=item,
                context=context,
                covers=(role,),
                scenario='positive',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {
                                    key: IsPartialDict(configuration_ids=Contains(role + '-stats'))
                                    for key in ('127:0', '97:54', '96:0')
                                }
                            )
                        )
                    )
                },
                evidence=(
                    f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                    'third-parties/d2data/json/runes.json:/Enigma',
                ),
            )
        for quality in ('normal', 'superior', 'low_quality'):
            item = replace(item, rarity=quality)
            for label, candidate, ctx in (
                ('ethereal', replace(item, ethereal=True), context),
                ('unknown-ethereal', replace(item, ethereal=None), context),
                ('wrong-class', item, {'player_class': 'Sorceress' if cls != 'Sorceress' else 'Warlock'}),
            ):
                yield Case(
                    id=f'enigma-quality/{build}/{variant}/{label}'
                    if quality == 'low_quality'
                    else f'enigma-quality/{build}/{variant}/{quality}/{label}',
                    item=candidate,
                    context=ctx,
                    covers=(role,),
                    scenario='unknown' if label.startswith('unknown') else 'negative',
                    expected={},
                    absent_configurations=(role + '-stats',),
                    evidence=(
                        f'pricing/data/wp-a-builds.json:/{build}/variants/{variant}',
                        'third-parties/d2data/json/runes.json:/Enigma',
                    ),
                )


CASES = tuple(cases())
