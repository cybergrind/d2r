"""Completed shield quality must not suppress an otherwise valid caster setup."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.cases.farming_nagelring import SPIRIT
from tests.pricing.knowledge.assessment.item_bank.cases.strafe_nagelring import RING
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


PHOENIX = Item(
    'Monarch',
    'normal',
    'Phoenix',
    ((194, 0, 4),),
    sockets=4,
    socket_contents='filled',
    runeword='Phoenix',
    socket_items=tuple(SocketItem(name + ' Rune') for name in ('Vex', 'Vex', 'Lo', 'Jah')),
)
AMULET = Item('Amulet', 'crafted', raw_stats=((105, 0, 12), (83, 6, 1)))
SPECS = (
    ('fire-blast-standard-spirit-nagelring', RING, SPIRIT, ('80:0',)),
    (
        'fire-blast-standard-soj-phoenix',
        Item('Ring', 'unique', 'The Stone of Jordan', ((127, 0, 1), (9, 0, 20 * 256), (77, 0, 25))),
        PHOENIX,
        ('127:0', '9:0', '77:0'),
    ),
    ('fire-blast-standard-crafted-amulet', AMULET, PHOENIX, ('105:0',)),
    ('fire-blast-standard-rare-ring', Item('Ring', 'rare', raw_stats=((105, 0, 10),)), PHOENIX, ('105:0',)),
)


def context(shield):
    return {
        'player_class': 'Assassin',
        'player_total_fcr': 102,
        'player_equipment': {
            'off_hand': normalize(shield.capture()).to_dict(),
            'amulet': normalize(AMULET.capture()).to_dict(),
        },
    }


def cases():
    for role, item, shield, keys in SPECS:
        examples = [
            (quality, context(replace(shield, rarity=quality)), 'positive' if quality != 'magic' else 'negative')
            for quality in ('normal', 'superior', 'low_quality', 'magic')
        ]
        examples.extend(
            (
                ('wrong-base', context(replace(shield, base='Crystal Sword')), 'negative'),
                ('unidentified-shield', context(replace(shield, identified=False)), 'negative'),
                (
                    'unknown-offhand',
                    {**context(shield), 'player_equipment': {'amulet': normalize(AMULET.capture()).to_dict()}},
                    'unknown',
                ),
                ('below-cast-breakpoint', {**context(shield), 'player_total_fcr': 101}, 'negative'),
            )
        )
        for label, ctx, scenario in examples:
            config = role + '-stats'
            expected = {'roles': Contains(IsPartialDict(id=role))}
            if scenario == 'positive':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict({key: IsPartialDict(configuration_ids=Contains(config)) for key in keys})
                )
            yield Case(
                id=f'fire-blast/companion-quality/{role}/{label}',
                item=item,
                context=ctx,
                covers=(role,),
                scenario=scenario,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                absent_configurations=() if scenario == 'positive' else (config,),
                evidence=(
                    'pricing/data/wp-a-builds.json:/fire-blast-assassin/variants/1',
                    'third-parties/D2MOO/source/D2Common/src/Items/Items.cpp:ITEMS_GetRunesTxtRecordFromItem',
                    'third-parties/d2data/json/runes.json:/' + shield.runeword,
                ),
            )


CASES = tuple(cases())
