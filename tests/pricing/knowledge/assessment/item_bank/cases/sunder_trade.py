"""Item-specific original Sunder penalty segments and native variant boundaries."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


VARIANTS = (
    ('fire', 'Flame Rift', 39, 189, 'Fire', -90, -70, False),
    ('lightning', 'Crack of the Heavens', 41, 190, 'Lightning', -90, -70, False),
    ('cold', 'Cold Rupture', 43, 187, 'Cold', -90, -70, True),
    ('poison', 'Rotting Fissure', 45, 191, 'Poison', -90, -70, False),
    ('magic', 'Black Cleft', 37, 193, 'Magic', -65, -45, True),
    ('physical', 'Bone Break', 36, 192, 'Physical', -20, -10, True),
)


def make_case(slug, label, item, stat, kind, qualified, premium=False, maximum=None):
    status = ('premium' if premium else 'candidate') if qualified else 'unresolved'
    reason = (
        f'{kind} sunder: perfect {maximum}% penalty has a higher asking segment.'
        if premium
        else f'{kind} sunder: ordinary trading demand across legal penalty rolls.'
    )
    return Case(
        id=f'sunder-trade/{slug}/{label}',
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario=(
            'positive'
            if qualified
            else 'unknown'
            if label.startswith('unknown-') or label in ('unidentified', 'incomplete') or label.endswith('-None')
            else 'negative'
        ),
        covers=(f'named:unique:{item.name}',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': [f'{stat}:0']} if qualified else {})},
            'lines': [
                {
                    'text': 'Trade: ' + ('premium' if premium else 'ordinary') + ' candidate — ' + reason,
                    'tone': 'tier_high' if premium else 'tier_low',
                }
            ]
            if qualified
            else [],
        },
        report_absent=('Trade: use only',) + (() if premium else ('Trade: premium candidate',)),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


def cases():
    for slug, name, stat, sunder, kind, minimum, maximum, has_premium in VARIANTS:
        item = Item('Grand Charm', 'unique', name, ((sunder, 0, 300), (stat, 0, maximum)))
        for penalty in (minimum, maximum - 1, maximum, None, minimum - 1, maximum + 1, -maximum, -minimum):
            raw = ((sunder, 0, 300),) if penalty is None else ((sunder, 0, 300), (stat, 0, penalty))
            yield make_case(
                slug,
                f'penalty-{penalty}',
                replace(item, raw_stats=raw),
                stat,
                kind,
                penalty is not None and minimum <= penalty <= maximum,
                has_premium and penalty == maximum,
                maximum,
            )
        for label, changes in (
            ('unidentified', {'identified': False}),
            ('ethereal', {'ethereal': True}),
            ('unknown-ethereal', {'ethereal': None}),
            ('socketed', {'sockets': 1}),
            ('unknown-sockets', {'sockets': None}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
        ):
            yield make_case(slug, label, replace(item, **changes), stat, kind, False)


CASES = tuple(cases())
