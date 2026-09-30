"""Named specialist demand follows native skill rolls, not the item name alone."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    ('Thunderstroke', 'Matriarchal Javelin', 338, (188, 2), 4, 3, '(2-4)', ((93, 0, 15), (334, 0, 15))),
    ("Arkaine's Valor", 'Balrog Skin', 251, (127, 0), 2, 1, '(1-2)', ((99, 0, 30), (16, 0, 180))),
)


def cases():
    for name, base, table_id, skill, best, lesser, interval, fixed in EXAMPLES:
        for label, roll, ethereal, tier, scenario in (
            ('maximum', best, False, 'med', 'positive'),
            ('lower', lesser, False, 'low', 'negative'),
            ('unread-skill', None, False, 'low', 'unknown'),
            ('ethereal-maximum', best, True, 'med', 'positive'),
            ('unknown-ethereal', best, None, 'low', 'unknown'),
        ):
            stats = (*fixed, *(((*skill, roll),) if roll is not None else ()))
            yield Case(
                id=f'specialist-skill-roll/{name}/{label}',
                item=Item(base, 'unique', name, stats, ethereal=ethereal, named_table_id=table_id),
                context={},
                expected={
                    'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier)),
                    'price_estimate': IsPartialDict(estimate_ist=None),
                },
                covers=('named:unique:' + name,),
                scenario=scenario,
                report_contains=(
                    name,
                    'Trade tier: ' + ('mid' if tier == 'med' else tier),
                    interval
                    if roll is not None
                    else ('Increased Attack Speed' if name == 'Thunderstroke' else 'Faster Hit Recovery'),
                ),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{table_id}',
                    f'pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/unique:{name}',
                ),
            )


CASES = tuple(cases())


def socket_cases():
    for label, sockets, contents, tier, scenario in (
        ('four-open', 4, 'empty', 'med', 'positive'),
        ('three-open', 3, 'empty', 'low', 'negative'),
        ('unread-sockets', None, 'unknown', 'low', 'unknown'),
        ('unread-contents', 4, 'unknown', 'low', 'unknown'),
    ):
        yield Case(
            id='specialist-skill-roll/Griswold-sockets/' + label,
            item=Item(
                'Caduceus',
                'set',
                "Griswold's Redemption",
                ((17, 0, 240), (18, 0, 240), (93, 0, 40)),
                sockets=sockets,
                socket_contents=contents,
                named_table_id=83,
            ),
            context={},
            expected={
                'assessment': IsPartialDict(trade_tier=IsPartialDict(tier=tier)),
                'price_estimate': IsPartialDict(estimate_ist=None),
            },
            covers=("named:set:Griswold's Redemption",),
            scenario=scenario,
            report_contains=(
                "Griswold's Redemption",
                'Trade tier: ' + ('mid' if tier == 'med' else tier),
                '(200-240%)' if contents == 'empty' else 'Enhanced Damage',
            ),
            # Unknown fillers can contribute ED; do not rank the total as a native roll.
            report_absent=('(200-240%)', 'Trade tier: mid') if contents != 'empty' else (),
            evidence=(
                "third-parties/d2data/json/setitems.json:/Griswolds's Redemption",
                "pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/set:Griswold's Redemption",
            ),
        )


CASES += tuple(socket_cases())
