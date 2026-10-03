"""Individual Pillar demand is separate from three-piece bonuses or collector rolls."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    original = Item('War Boots', 'set', "Immortal King's Pillar", ((31, 0, 128),))
    specimens = [
        (f'defense-{defense}', replace(original, raw_stats=((31, 0, defense),)), True)
        for defense in (118, 123, 128, 278, 288)
    ]
    specimens.extend(
        (label, replace(original, **changes), False)
        for label, changes in (
            ('upgraded', {'base': 'Myrmidon Greaves'}),
            ('ethereal', {'ethereal': True}),
            ('unknown-ethereal', {'ethereal': None}),
            ('socketed', {'sockets': 1}),
            ('unknown-sockets', {'sockets': None}),
            ('unknown-contents', {'socket_contents': 'unknown'}),
            ('unidentified', {'identified': False}),
        )
    )
    for label, item, qualified in specimens:
        status = 'candidate' if qualified else 'unresolved'
        yield Case(
            id='ik-pillar-trade/' + label,
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
            covers=("named:set:Immortal King's Pillar",),
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status, **({'material_stats': []} if qualified else {})},
                'lines': [
                    {
                        'text': (
                            'Trade: candidate — Set component with fixed affixes; no defense-roll premium established.'
                        ),
                        'tone': 'tier_trash',
                    }
                ]
                if qualified
                else [],
            },
            report_absent=('Trade: premium candidate', 'Trade: use only'),
            evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
        )


CASES = tuple(cases())
