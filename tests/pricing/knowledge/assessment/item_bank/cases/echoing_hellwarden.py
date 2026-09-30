"""Helmet and jewel magic-pierce rolls remain distinct in the Ubers pairing."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'echoing-ubers-hellwarden'
CONTEXT = {'player_class': 'Warlock', 'player_items': ['Sling', 'Renewed Black Cleft']}


def helmet(native):
    from inventory_tracking.items.metadata import metadata

    base = next(b['name'] for b in metadata()['bases'].values() if b['code'] == 'cjw')
    return Item(
        'Death Mask',
        'unique',
        "Hellwarden's Will",
        ((358, 0, native + 10), (127, 0, 1), (105, 0, 20), (194, 0, 1)),
        sockets=1,
        socket_contents='filled',
        socket_items=(
            SocketItem(
                base,
                (
                    (201, 387 * 64 + 25, 1),
                    (357, 0, 10),
                    (52, 0, 15),
                    (53, 0, 35),
                    (358, 0, 10),
                    (85, 0, 5),
                    (80, 0, 35),
                    (79, 0, 50),
                ),
                name="Guardian's Light",
                complete=True,
            ),
        ),
    )


def cases():
    low, high = helmet(5), helmet(8)
    rows = [
        ('low-roll', low, CONTEXT, 'true', 'false'),
        ('perfect-roll', high, CONTEXT, 'true', 'true'),
        (
            'unread-jewel',
            replace(high, socket_items=(replace(high.socket_items[0], raw_stats=(), complete=False),)),
            CONTEXT,
            'true',
            'unknown',
        ),
        ('missing-jewel', replace(high, socket_items=(), socket_contents='unknown'), CONTEXT, 'true', 'unknown'),
        ('impossible-native', helmet(10), CONTEXT, 'true', 'unknown'),
        ('wrong-class', high, {**CONTEXT, 'player_class': 'Paladin'}, 'false', 'true'),
        ('unknown-class', high, {**CONTEXT, 'player_class': None}, 'unknown', 'true'),
        ('missing-sling', high, {**CONTEXT, 'player_items': ['Renewed Black Cleft']}, 'true', 'true'),
        ('missing-sunder', high, {**CONTEXT, 'player_items': ['Sling']}, 'true', 'true'),
        ('unknown-companions', high, {'player_class': 'Warlock'}, 'true', 'true'),
    ]
    for label, item, context, truth, preference in rows:
        yield Case(
            id='echoing/hellwarden/' + label,
            item=item,
            context=context,
            expected={
                'assessment': IsPartialDict(
                    roles=Contains(
                        IsPartialDict(
                            id=ROLE,
                            rule_trace=IsPartialDict(truth=truth),
                            preferences=[IsPartialDict(status=preference)],
                        )
                    )
                )
            },
            covers=(ROLE,),
            scenario='unknown'
            if 'unknown' in label or 'unread' in label or 'impossible' in label
            else 'positive'
            if label == 'perfect-roll'
            else 'negative',
            evidence=(
                'pricing/raw/mr/guides__echoing-strike-warlock-guide.html:/sections/24',
                'third-parties/d2data/json/uniqueitems.json:/419',
                'third-parties/d2data/json/uniqueitems.json:/425',
            ),
        )


CASES = tuple(cases())
