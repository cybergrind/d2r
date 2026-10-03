"""Exact upgraded Waterwalk cohort, near-miss defense and missing ED."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ITEM = Item(
    'Scarabshell Boots',
    'unique',
    'Waterwalk',
    (
        (31, 0, 198),
        (16, 0, 210),
        (32, 0, 100),
        (96, 0, 20),
        (2, 0, 15),
        (7, 0, 65 * 256),
        (11, 0, 40 * 256),
        (40, 0, 5),
        (28, 0, 50),
    ),
    complete=True,
)

CASES = tuple(
    Case(
        id='waterwalk-defense/' + label,
        item=item,
        context={},
        covers=('named:unique:Waterwalk',),
        scenario=scenario,
        expected={
            'price_estimate': IsPartialDict(estimate_ist=None, sellers=sellers),
            'assessment': IsPartialDict(
                trade_qualification=IsPartialDict(status='candidate' if scenario == 'positive' else 'unresolved')
            ),
        },
        report_contains=(
            'Waterwalk',
            'Upgraded boots with 65 life, 210% ED and 198 defense have three independent asking sellers.',
        )
        if scenario == 'positive'
        else ('Waterwalk',),
        evidence=(
            'third-parties/d2data/json/uniqueitems.json:/238',
            'third-parties/d2data/json/armor.json:/uvb',
            'pricing/raw/traderie/wpi-waterwalk.json',
        ),
    )
    for label, item, scenario, sellers in (
        ('matched-dispersed', ITEM, 'positive', 3),
        (
            'different-defense',
            replace(ITEM, raw_stats=tuple((s, p, 201 if s == 31 else v) for s, p, v in ITEM.raw_stats)),
            'negative',
            0,
        ),
        (
            'unknown-ed',
            replace(ITEM, raw_stats=tuple(r for r in ITEM.raw_stats if r[0] != 16), complete=False),
            'unknown',
            0,
        ),
    )
)


def boundary_cases():
    """Native corners plus the immediately adjacent life/ED/base-defense rolls."""
    variants = []
    for base, defense_bases in [('Sharkskin Boots', (40,)), ('Scarabshell Boots', (56, 63, 64, 65))]:
        for base_defense in defense_bases:
            for life in (45, 64, 65):
                for ed in (180, 209, 210):
                    values = {31: base_defense * (100 + ed) // 100, 16: ed, 7: life * 256}
                    item = replace(
                        ITEM, base=base, raw_stats=tuple((s, p, values.get(s, v)) for s, p, v in ITEM.raw_stats)
                    )
                    candidate = base == 'Sharkskin Boots' or (base, base_defense, life, ed) == (
                        'Scarabshell Boots',
                        64,
                        65,
                        210,
                    )
                    variants.append(
                        (f'{base_defense}-{life}-{ed}', item, 'positive' if candidate else 'negative', candidate)
                    )
    for stat, values in [(7, (44 * 256, 66 * 256)), (16, (179, 211)), (31, (197, 199))]:
        for value in values:
            item = replace(ITEM, raw_stats=tuple((s, p, value if s == stat else v) for s, p, v in ITEM.raw_stats))
            variants.append((f'invalid-{stat}-{value}', item, 'negative', False))
        variants.append(
            (
                f'missing-{stat}',
                replace(ITEM, raw_stats=tuple(r for r in ITEM.raw_stats if r[0] != stat), complete=False),
                'unknown',
                False,
            )
        )
    for label, changes in [
        ('ethereal', {'ethereal': True}),
        ('unknown-ethereal', {'ethereal': None}),
        ('unknown-sockets', {'sockets': None}),
        ('unknown-contents', {'socket_contents': 'unknown'}),
        ('filled', {'socket_contents': 'filled'}),
        ('socketed', {'sockets': 1}),
        ('unidentified', {'identified': False}),
        ('incomplete', {'complete': False}),
        ('per-level-defense', {'raw_stats': (*ITEM.raw_stats, (214, 0, 8))}),
        ('per-level-ed', {'raw_stats': (*ITEM.raw_stats, (215, 0, 8))}),
    ]:
        variants.append(
            (
                label,
                replace(ITEM, **changes),
                'unknown' if label.startswith('unknown') or label == 'incomplete' else 'negative',
                False,
            )
        )
    # Repeat invalid/unknown variants on the original base, with its own totals.
    for label, item, scenario, candidate in list(variants):
        if label[0].isdigit():
            continue
        stats = {(stat, layer): value for stat, layer, value in item.raw_stats}
        if (31, 0) in stats:
            ed = stats.get((16, 0), 210)
            stats[31, 0] = (60 if item.ethereal is True else 40) * (100 + ed) // 100
            if label.startswith('invalid-31-'):
                stats[31, 0] = 123 if label.endswith('197') else 125
        original = replace(
            item,
            base='Sharkskin Boots',
            raw_stats=tuple((stat, layer, value) for (stat, layer), value in stats.items()),
        )
        variants.append(('original-' + label, original, scenario, candidate))

    for label, item, scenario, candidate in variants:
        status = 'candidate' if candidate else 'unresolved'
        reason = (
            (
                'Original boots retain asking interest below perfect life; '
                'movement, dexterity and maximum fire resistance are fixed.'
            )
            if item.base == 'Sharkskin Boots'
            else 'Upgraded boots with 65 life, 210% ED and 198 defense have three independent asking sellers.'
        )
        yield Case(
            id='waterwalk-boundaries/' + label,
            item=item,
            context={},
            covers=('named:unique:Waterwalk',),
            scenario=scenario,
            expected={'assessment': IsPartialDict(trade_qualification=IsPartialDict(status=status))},
            trade_checks={
                'schema_version': 1,
                'qualification': {'status': status},
                'lines': [{'text': 'Trade: ordinary candidate — ' + reason, 'tone': 'tier_low'}] if candidate else [],
            },
            evidence=(
                'third-parties/d2data/json/uniqueitems.json:/238',
                'third-parties/d2data/json/armor.json:/xvb',
                'third-parties/d2data/json/armor.json:/uvb',
                'pricing/raw/traderie/wpi-waterwalk.json',
            ),
        )


CASES += tuple(boundary_cases())
