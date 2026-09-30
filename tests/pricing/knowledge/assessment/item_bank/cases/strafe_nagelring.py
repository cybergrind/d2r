"""Strafe's MF ring substitution requires the cited equipped helmet and jewel."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from pricing.knowledge.assessment.adapters.capture import normalize
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


ROLE = 'strafe-mf-stealskull-nagelring'
CONFIG = ROLE + '-stats'
RING = Item('Ring', 'unique', 'Nagelring', ((35, 0, 3), (78, 0, 3), (19, 0, 50), (80, 0, 15)))
HELMET = Item(
    'Casque',
    'unique',
    'Stealskull',
    ((60, 0, 5), (62, 0, 5), (99, 0, 10), (93, 0, 25), (16, 0, 200), (80, 0, 30), (194, 0, 1)),
    sockets=1,
    socket_contents='filled',
    socket_items=(SocketItem('Jewel', ((93, 0, 15),), complete=True),),
)


def equipped(item):
    return {'head': normalize(item.capture()).to_dict()}


def cases():
    base = {'player_class': 'Amazon', 'player_equipment': equipped(HELMET)}
    examples = [
        ('minimum-mf', RING, base, 'positive', 'true', 'true'),
        ('perfect-mf', replace(RING, raw_stats=(*RING.raw_stats[:-1], (80, 0, 30))), base, 'positive', 'true', 'true'),
        (
            'upgraded-helmet',
            RING,
            {**base, 'player_equipment': equipped(replace(HELMET, base='Armet'))},
            'positive',
            'true',
            'true',
        ),
        ('wrong-class', RING, {**base, 'player_class': 'Sorceress'}, 'negative', 'false', 'true'),
        ('unknown-class', RING, {**base, 'player_class': None}, 'unknown', 'unknown', 'true'),
        ('empty-head-slot', RING, {**base, 'player_equipment': {'head': None}}, 'negative', 'true', 'false'),
        ('unknown-equipment', RING, {'player_class': 'Amazon'}, 'unknown', 'true', 'unknown'),
        (
            'name-list-only',
            RING,
            {'player_class': 'Amazon', 'player_items': ['Stealskull']},
            'unknown',
            'true',
            'unknown',
        ),
        (
            'mercenary-helmet',
            RING,
            {'player_class': 'Amazon', 'mercenary_equipment': equipped(HELMET)},
            'unknown',
            'true',
            'unknown',
        ),
        (
            'swap-helmet',
            RING,
            {'player_class': 'Amazon', 'player_swap_equipment': equipped(HELMET)},
            'unknown',
            'true',
            'unknown',
        ),
    ]
    for label, helmet, scenario, truth in (
        (
            'wrong-helmet',
            Item(
                'Shako',
                'unique',
                'Harlequin Crest',
                sockets=1,
                socket_contents='filled',
                socket_items=HELMET.socket_items,
            ),
            'negative',
            'false',
        ),
        ('unidentified-helmet', replace(HELMET, identified=False), 'negative', 'false'),
        ('aggregate-ias-only', replace(HELMET, socket_items=()), 'unknown', 'unknown'),
        ('unread-jewel', replace(HELMET, socket_items=(SocketItem('Jewel'),)), 'unknown', 'unknown'),
        (
            'wrong-jewel',
            replace(HELMET, socket_items=(SocketItem('Jewel', ((39, 0, 30),), complete=True),)),
            'negative',
            'false',
        ),
        ('empty-socket', replace(HELMET, socket_contents='empty', socket_items=()), 'negative', 'false'),
        # This existential dependency needs one verified child, not every socket's capacity.
        (
            'known-jewel-unknown-capacity',
            replace(HELMET, sockets=None, raw_stats=tuple(stat for stat in HELMET.raw_stats if stat[0] != 194)),
            'positive',
            'true',
        ),
    ):
        examples.append((label, RING, {**base, 'player_equipment': equipped(helmet)}, scenario, 'true', truth))
    for label, item, context, scenario, required, dependency in examples:
        expected = {
            'roles': Contains(
                IsPartialDict(
                    id=ROLE,
                    status='failed' if required == 'false' else 'partial',
                    rule_trace=IsPartialDict(truth=required),
                    dependencies=Contains(IsPartialDict(status=dependency)),
                )
            )
        }
        if scenario == 'positive':
            expected['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        '80:0': IsPartialDict(configuration_ids=Contains(CONFIG)),
                    }
                )
            )
        yield Case(
            id=f'strafe/nagelring/{label}',
            item=item,
            context=context,
            covers=(ROLE,),
            scenario=scenario,
            expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
            absent_configurations=() if scenario == 'positive' else (CONFIG,),
            absent_stat_configurations={'19:0': (CONFIG,), '35:0': (CONFIG,)},
            report_contains=('Nagelring', 'Trade tier:'),
            evidence=(
                'pricing/data/wp-a-builds.json:/strafe-amazon/variants/2',
                'third-parties/d2data/json/uniqueitems.json:/120',
                'third-parties/d2data/json/uniqueitems.json:/203',
            ),
        )


CASES = tuple(cases())
