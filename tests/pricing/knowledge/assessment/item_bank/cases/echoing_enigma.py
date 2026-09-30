"""Late-game Enigma replaces Blade Warp without requiring the exact illustrated armor base."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'echoing-late-game-enigma-player'
CONTEXT = {'player_class': 'Warlock'}


def cases():
    for quality in ('normal', 'superior', 'low_quality'):
        item = Item(
            'Mage Plate',
            quality,
            'Enigma',
            ((97, 54, 1), (194, 0, 3)),
            ethereal=False,
            sockets=3,
            socket_contents='filled',
            runeword='Enigma',
            socket_items=tuple(SocketItem(n) for n in ('Jah Rune', 'Ith Rune', 'Ber Rune')),
        )
        rows = [
            ('mage-plate', item, CONTEXT, True),
            ('alternative-dusk-shroud', replace(item, base='Dusk Shroud'), CONTEXT, True),
            ('ethereal', replace(item, ethereal=True), CONTEXT, False),
            ('unknown-ethereal', replace(item, ethereal=None), CONTEXT, False),
            ('wrong-class', item, {'player_class': 'Paladin'}, False),
            ('unknown-class', item, {}, False),
            ('illegal-helmet', replace(item, base='Grand Crown'), CONTEXT, False),
            ('unidentified', replace(item, identified=False), CONTEXT, False),
        ]
        for label, candidate, context, usable in rows:
            yield Case(
                id=f'echoing/enigma-late-game/{quality}/{label}',
                item=candidate,
                context=context,
                covers=(ROLE,),
                scenario='unknown' if label.startswith('unknown') else 'positive' if usable else 'negative',
                expected={
                    'assessment': IsPartialDict(
                        stat_evaluation=IsPartialDict(
                            annotations=IsPartialDict(
                                {'97:54': IsPartialDict(configuration_ids=Contains(ROLE + '-stats'))}
                            )
                        )
                    )
                }
                if usable
                else {},
                absent_configurations=() if usable else (ROLE + '-stats',),
                evidence=(
                    'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/30',
                    'third-parties/d2data/json/runes.json:/Enigma',
                ),
            )


CASES = tuple(cases())
