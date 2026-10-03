"""Druid life skiller trade interest is independent of the player's build."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


CASES = tuple(
    Case(
        id=f'charm/trainer-trade/{label}',
        item=Item('Grand Charm', rarity, raw_stats=stats, identified=identified, complete=complete),
        context={},
        covers=('watch:druid-summoning-life-skiller',) if rarity == 'magic' else (),
        expected={
            'value_watch': Contains(
                IsPartialDict(
                    details=IsPartialDict(
                        watch_id='druid-summoning-life-skiller',
                        priority='valuable_candidate',
                    )
                )
            )
            if valuable
            else []
        },
        scenario='positive' if valuable else 'unknown' if not complete or not identified else 'negative',
        report_contains=('TRADE CANDIDATE', 'Druid Summoning skiller with 30-45 Life') if valuable else (),
        evidence=("pricing/raw/mr/items__valuable-magic-items.html:Trainer's Grand Charm of Vita",),
    )
    for label, stats, rarity, identified, complete, valuable in (
        ('life29', ((188, 40, 1), (7, 0, 29 << 8)), 'magic', True, True, False),
        ('life30', ((188, 40, 1), (7, 0, 30 << 8)), 'magic', True, True, True),
        ('life37', ((188, 40, 1), (7, 0, 37 << 8)), 'magic', True, True, True),
        ('life45', ((188, 40, 1), (7, 0, 45 << 8)), 'magic', True, True, True),
        ('life-unknown', ((188, 40, 1),), 'magic', True, False, False),
        ('skill-unknown', ((7, 0, 37 << 8),), 'magic', True, False, False),
        ('different-tree', ((188, 41, 1), (7, 0, 37 << 8)), 'magic', True, True, False),
        ('unidentified', ((188, 40, 1), (7, 0, 37 << 8)), 'magic', False, True, False),
        ('invalid-rarity', ((188, 40, 1), (7, 0, 37 << 8)), 'rare', True, True, False),
    )
)
