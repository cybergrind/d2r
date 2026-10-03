"""Original set bases: ordinary demand does not prove upgraded or collector value."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    claws = Item('Heavy Bracers', 'set', "Trang-Oul's Claws", ((31, 0, 74),))
    belt = Item('Mesh Belt', 'set', "Tal Rasha's Fine-Spun Cloth", ((80, 0, 15),))
    for slug, item, upgraded in (('claws', claws, 'Vambraces'), ('belt', belt, 'Mithril Coil')):
        for label, specimen, qualified in (
            ('original', item, True),
            ('upgraded', replace(item, base=upgraded), False),
            ('unidentified', replace(item, identified=False), False),
            ('ethereal', replace(item, ethereal=True), False),
            ('unknown-ethereal', replace(item, ethereal=None), False),
            ('unknown-sockets', replace(item, sockets=None), False),
            ('unknown-contents', replace(item, socket_contents='unknown'), False),
            ('socketed', replace(item, sockets=1), False),
        ):
            yield make_case(slug + '/' + label, specimen, qualified)
    for mf in (None, 9, 10, 14, 16):
        yield make_case('belt/mf-' + str(mf), replace(belt, raw_stats=() if mf is None else ((80, 0, mf),)), False)


def make_case(label, item, qualified):
    belt = label.startswith('belt/')
    status = 'candidate' if qualified else 'unresolved'
    text = (
        'Trade: ordinary candidate — 15% magic find: ordinary trade candidate.'
        if belt
        else 'Trade: candidate — Fixed modifiers: ordinary trade candidate; no defense premium established.'
    )
    return Case(
        id='original-set-trade/' + label,
        item=item,
        context={},
        expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
        scenario='positive' if qualified else 'unknown',
        covers=(f'named:set:{item.name}',),
        trade_checks={
            'schema_version': 1,
            'qualification': {'status': status, **({'material_stats': ['80:0'] if belt else []} if qualified else {})},
            'lines': [{'text': text, 'tone': 'tier_low'}] if qualified else [],
        },
        report_contains=('Trade tier: low',) if qualified else (),
        report_absent=('Trade: premium candidate', 'Trade: use only'),
        evidence=('pricing/knowledge/assessment/rules/named_tiers.json',),
    )


CASES = tuple(cases())
