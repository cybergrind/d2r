"""Named baselines must survive low or unknown rolls without inventing premiums."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SHAKO = Item(
    'Shako',
    'unique',
    'Harlequin Crest',
    (
        (0, 0, 2),
        (1, 0, 2),
        (2, 0, 2),
        (3, 0, 2),
        (31, 0, 141),
        (36, 0, 10),
        (72, 0, 12),
        (73, 0, 12),
        (80, 0, 50),
        (127, 0, 2),
        (216, 0, 3072),
        (217, 0, 3072),
    ),
    complete=True,
    owned_stats=((31, 0, 141),),
)
TARGET = 'named:unique:Harlequin Crest'
CASES = tuple(
    Case(
        id='named/shako/' + scenario,
        item=item,
        context={},
        scenario=scenario,
        expected={'assessment': IsPartialDict(trade_tier=IsPartialDict(status='reviewed', tier='med'))},
        covers=(TARGET,),
        report_contains=('Harlequin Crest', 'Trade tier: mid')
        + (() if scenario == 'unknown' else (f'Defense: {141 if scenario == "positive" else 98} (98-141)',)),
        evidence=(
            'pricing/knowledge/assessment/rules/named_tier_reviews.json',
            'third-parties/d2data/json/uniqueitems.json:/248',
        ),
    )
    for scenario, item in (
        ('positive', SHAKO),
        (
            'negative',
            replace(
                SHAKO,
                owned_stats=((31, 0, 98),),
                raw_stats=tuple((stat, layer, 98 if stat == 31 else value) for stat, layer, value in SHAKO.raw_stats),
            ),
        ),
        ('unknown', replace(SHAKO, raw_stats=tuple(row for row in SHAKO.raw_stats if row[0] != 31), complete=False)),
    )
)
