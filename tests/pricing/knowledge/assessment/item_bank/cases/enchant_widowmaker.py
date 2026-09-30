"""Guided Arrow is an active Enchant delivery oskill, not a spell multiplier."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLE = 'enchant-sorceress-widowmaker-weapon-tail-alternative'
CONFIG = ROLE + '-stats'


def cases():
    context = {'player_class': 'Sorceress'}
    original = Item(
        'Ward Bow',
        'unique',
        'Widowmaker',
        ((17, 0, 150), (18, 0, 150), (141, 0, 33), (115, 0, 1), (157, 0, 11), (97, 22, 3)),
        named_table_id=331,
    )
    rows = [
        (
            f'rolls-{ed}-{skill}',
            replace(
                original,
                raw_stats=tuple(
                    (s, p, ed if s in (17, 18) else skill if s == 97 else v) for s, p, v in original.raw_stats
                ),
            ),
            context,
            'true',
        )
        for ed in (150, 200)
        for skill in (3, 5)
    ]
    rows += [
        ('ethereal-invalid', replace(original, ethereal=True), context, 'false'),
        ('unknown-ethereal', replace(original, ethereal=None), context, 'unknown'),
        ('wrong-class', original, {'player_class': 'Amazon'}, 'false'),
        ('unknown-class', original, {}, 'unknown'),
        ('unidentified', replace(original, identified=False), context, 'false'),
        (
            'unread-oskill',
            replace(original, raw_stats=tuple(s for s in original.raw_stats if s[0] != 97)),
            context,
            'true',
        ),
        ('unread-stats', replace(original, raw_stats=()), context, 'true'),
        ('empty-socket', replace(original, sockets=1, raw_stats=(*original.raw_stats, (194, 0, 1))), context, 'true'),
        (
            'unknown-filler',
            replace(original, sockets=1, socket_contents='unknown', raw_stats=(*original.raw_stats, (194, 0, 1))),
            context,
            'true',
        ),
        ('unknown-sockets', replace(original, sockets=None, socket_contents='unknown'), context, 'unknown'),
    ]
    for label, item, loadout, truth in rows:
        active = truth == 'true'
        skill = next((v for s, p, v in item.raw_stats if (s, p) == (97, 22)), None)
        assessment = {'roles': Contains(IsPartialDict(id=ROLE, rule_trace=IsPartialDict(truth=truth)))}
        if active and skill:
            assessment['stat_evaluation'] = IsPartialDict(
                annotations=IsPartialDict(
                    {
                        '97:22': IsPartialDict(
                            contributions=Contains(
                                IsPartialDict(configuration_id=CONFIG, role_id=ROLE, desirability='desirable')
                            )
                        )
                    }
                )
            )
        yield Case(
            id='enchant-widowmaker/' + label,
            item=item,
            context=loadout,
            expected={'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=(ROLE,),
            scenario='unknown'
            if truth == 'unknown' or label.startswith('unread')
            else 'positive'
            if active
            else 'negative',
            absent_configurations=() if active else (CONFIG,),
            absent_stat_configurations=dict.fromkeys(
                ('17:0', '18:0', '141:0', '115:0', '157:0', *(('97:22',) if skill is None else ())), (CONFIG,)
            ),
            report_contains=(('Widowmaker', 'Trade tier:') if item.identified and item.ethereal is False else ())
            + ((f'+{skill} (3-5) to Guided Arrow',) if item.identified and skill and item.sockets == 0 else ()),
            detail_contains=(
                'Guided Arrow is an oskill that must be selected and used',
                'Enchant must be supplied separately',
                'Deadly Strike do not multiply Enchant fire damage',
            )
            if active
            else (),
            evidence=(
                'pricing/data/wp-a-builds.json:/enchant-sorceress/slots/Weapon/2',
                'third-parties/d2data/json/uniqueitems.json:/331',
            ),
        )


CASES = tuple(cases())
