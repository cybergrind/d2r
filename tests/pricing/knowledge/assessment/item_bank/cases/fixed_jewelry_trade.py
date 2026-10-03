"""Fixed-stat named jewelry needs demand/identity checks, not perfect-roll grading."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SOJ = Item(
    'Ring',
    'unique',
    'The Stone of Jordan',
    ((9, 0, 20 * 256), (77, 0, 25), (50, 0, 1), (51, 0, 12), (127, 0, 1)),
    complete=True,
)
TAL = Item(
    'Amulet',
    'set',
    "Tal Rasha's Adjudication",
    ((83, 1, 2), (7, 0, 50 * 256), (9, 0, 42 * 256), (41, 0, 33), (50, 0, 3), (51, 0, 32)),
    complete=True,
)


HIGHLORD = Item('Amulet', 'unique', "Highlord's Wrath", ((41, 0, 35), (93, 0, 20), (127, 0, 1), (128, 0, 15)))


def cases():
    for slug, item, tier in (
        ('soj', SOJ, 'high'),
        ('tal', TAL, 'low'),
        ('highlord', HIGHLORD, 'med'),
    ):
        for label, specimen, status in (
            ('standalone', item, 'candidate'),
            ('partial-stats', replace(item, raw_stats=(), complete=False), 'candidate'),
            ('unidentified', replace(item, identified=False), 'unresolved'),
            ('ethereal', replace(item, ethereal=True), 'unresolved'),
            ('unknown-ethereal', replace(item, ethereal=None), 'unresolved'),
            ('unknown-sockets', replace(item, sockets=None), 'unresolved'),
            ('unknown-contents', replace(item, socket_contents='unknown'), 'unresolved'),
            ('socketed', replace(item, sockets=1), 'unresolved'),
        ):
            positive = status == 'candidate'
            yield Case(
                id=f'fixed-jewelry-trade/{slug}/{label}',
                item=specimen,
                context={},
                trade_checks={
                    'schema_version': 1,
                    'qualification': {'status': status, **({'material_stats': []} if positive else {})},
                    'lines': [
                        {
                            'text': (
                                'Trade: candidate — Fixed stats: trade demand does not require a random-roll threshold.'
                            ),
                            'tone': 'tier_' + tier,
                        }
                    ]
                    if positive
                    else [],
                },
                expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
                scenario='positive' if positive else 'unknown' if label == 'unidentified' else 'negative',
                covers=(f'named:{item.rarity}:{item.name}',),
                report_contains=('Trade: candidate', f'Trade tier: {"mid" if tier == "med" else tier}', 'Fixed stats:')
                if positive
                else (),
                report_absent=(
                    'Trade: ordinary candidate',
                    'Trade: premium candidate',
                    *(('Trade: candidate',) if not positive else ()),
                    *(('10% Faster Cast Rate',) if slug == 'tal' else ()),
                ),
                evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
            )


CASES = tuple(cases())
