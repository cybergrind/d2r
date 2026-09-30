"""Nature's Peace corpse utility and flat reduction do not imply an active Oak Sage."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


USES = {
    'Paladin': (('blessed-hammer-paladin', 4), ('dream-paladin', 9), ('fist-of-the-heavens-paladin', 3)),
    'Amazon': (('lightning-fury-amazon-guide', 4), ('lightning-strike-amazon', 8)),
    'Sorceress': (('lightning-sorceress', 8),),
}
SUFFIX = '-nature-s-peace-jewelry-casting-alternative'


def ring(reduction=7, poison=20, *, depleted=False):
    return Item(
        'Ring',
        'unique',
        "Nature's Peace",
        (
            (117, 0, 1),
            (108, 0, 1),
            (34, 0, reduction),
            (45, 0, poison),
            (204, 226 * 64 + 5, (27 << 8) + (0 if depleted else 27)),
        ),
        complete=True,
    )


def cases():
    for player_class, uses in USES.items():
        roles = tuple(g + SUFFIX for g, _ in uses)
        configs = tuple(r + '-stats' for r in roles)
        context = {'player_class': player_class}
        item = ring()
        examples = (
            ('minimum', item, context, 'true'),
            ('perfect', ring(11, 30), context, 'true'),
            ('reduction-perfect', ring(11), context, 'true'),
            ('poison-perfect', ring(poison=30), context, 'true'),
            ('depleted-charges', ring(depleted=True), context, 'true'),
            (
                'unread-charges',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 204), complete=False),
                context,
                'true',
            ),
            (
                'unread-rest-in-peace',
                replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 108), complete=False),
                context,
                'true',
            ),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('wrong-class', item, {'player_class': 'Warlock'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('impossible-socket', replace(item, sockets=1), context, 'false'),
            ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
        )
        for label, candidate, loadout, truth in examples:
            expected = {'roles': Contains(*(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles))}
            if truth == 'true':
                keys = ['34:0', '45:0'] + ([] if label == 'unread-rest-in-peace' else ['108:0'])
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                    )
                )
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        *(
                            IsPartialDict(
                                memory_stat=IsPartialDict(id=stat, layer=0),
                                roll_range=IsPartialDict(min=7 if stat == 34 else 20, max=11 if stat == 34 else 30),
                                roll_quality='perfect' if value == (11 if stat == 34 else 30) else 'low',
                            )
                            for stat, _, value in candidate.raw_stats
                            if stat in (34, 45)
                        )
                    )
                )
            absent = dict.fromkeys(('204:14469', '7:0', '36:0', '117:0'), configs)
            if label == 'unread-rest-in-peace':
                absent['108:0'] = configs
            report = (item.name, 'Trade tier:') if truth == 'true' else ('Ring',)
            if truth == 'true' and label != 'unread-charges':
                report += ('Oak Sage',)
            yield Case(
                id=f'natures-peace-alternatives/{player_class}/{label}',
                item=candidate,
                context=loadout,
                scenario='unknown'
                if label.startswith('unread-')
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                covers=roles,
                expected=result,
                absent_stat_configurations=absent,
                absent_configurations=() if truth == 'true' else configs,
                report_contains=report,
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/300',
                    'third-parties/d2data/json/skills.json:/226',
                    *(f'pricing/data/wp-a-builds.json:/{g}/slots/Rings/{i}' for g, i in uses),
                ),
            )


CASES = tuple(cases())
