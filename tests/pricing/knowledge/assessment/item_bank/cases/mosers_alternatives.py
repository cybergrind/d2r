"""Moser's native two sockets: empty, filled and incompletely captured contents."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item, SocketItem


USES = {
    'Druid': (('fissure-druid', 'Off-Hand', 6),),
    'Sorceress': (('lightning-sorceress', 'Off-Hand', 4), ('lightning-sorceress', 'Off-Hand Swap', 6)),
    'Amazon': (('lightning-strike-amazon', 'Off-Hand', 7),),
    'Necromancer': (('poison-nova-necromancer', 'Off-Hand', 5),),
}


def shield(base='Round Shield', ed=180, diamonds=0):
    resistance = 25 + 19 * diamonds
    return Item(
        base,
        'unique',
        "Moser's Blessed Circle",
        (
            *((stat, 0, resistance) for stat in (39, 41, 43, 45)),
            (20, 0, 25),
            (102, 0, 30),
            (16, 0, ed),
            (194, 0, 2),
        ),
        sockets=2,
        socket_contents='filled' if diamonds else 'empty',
        socket_items=tuple(SocketItem('Perfect Diamond') for _ in range(diamonds)),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(
            g + '-moser-s-blessed-circle-' + slot.lower().replace(' ', '-') + '-shield-utility-alternative'
            for g, slot, _ in uses
        )
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        examples = [
            (base + '/' + str(ed), shield(base, ed), context, 'true')
            for base in ('Round Shield', 'Luna')
            for ed in (180, 220)
        ]
        item = shield()
        examples.extend(
            (
                ('two-diamonds', shield(diamonds=2), context, 'true'),
                ('one-contents-captured', shield(diamonds=1), context, 'true'),
                ('unread-contents', replace(item, socket_contents='unknown'), context, 'true'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                (
                    'wrong-socket-count',
                    replace(
                        item,
                        sockets=1,
                        raw_stats=tuple((s, layer, 1 if s == 194 else v) for s, layer, v in item.raw_stats),
                    ),
                    context,
                    'false',
                ),
                (
                    'unknown-sockets',
                    replace(
                        item, sockets=None, raw_stats=tuple(s for s in item.raw_stats if s[0] != 194), complete=False
                    ),
                    context,
                    'unknown',
                ),
            )
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            key: IsPartialDict(configuration_ids=Contains(*configs))
                            for key in ('39:0', '41:0', '43:0', '45:0', '20:0', '102:0')
                        }
                    )
                )
                resistance = 63 if label == 'two-diamonds' else 44 if label == 'one-contents-captured' else 25
                expected['facts'] = IsPartialDict(
                    stats=IsPartialDict({f'{stat}:0': IsPartialDict(value=resistance) for stat in (39, 41, 43, 45)})
                )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                ed = next(v for s, _, v in candidate.raw_stats if s == 16)
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=16, layer=0),
                            roll_range=IsPartialDict(min=180, max=220),
                            roll_quality='perfect' if ed == 220 else 'low',
                        )
                    )
                )
            report = (item.name, 'Trade tier:', 'Sockets: 2') if truth == 'true' else (candidate.base,)
            if label == 'two-diamonds':
                report += ('Perfect Diamond',)
            if label == 'one-contents-captured':
                report += ('Perfect Diamond (1 contents captured)',)
            yield Case(
                id=f'mosers-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label in ('one-contents-captured', 'unread-contents')
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations={'16:0': configs},
                absent_configurations=() if truth == 'true' else configs,
                report_contains=report,
                report_absent=('Perfect Diamond',) if truth == 'true' and not candidate.socket_items else (),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/225',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/{slot}/{i}' for g, slot, i in uses),
                ),
            )


CASES = tuple(cases())
