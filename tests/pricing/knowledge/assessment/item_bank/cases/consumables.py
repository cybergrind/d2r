"""Native potion identity, impossible facets and incomplete-capture scenarios."""

from dataclasses import replace

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


EXAMPLES = (
    ('mp1', 'Minor Mana Potion', 'Restores mana over time'),
    ('mp2', 'Light Mana Potion', 'Restores mana over time'),
    ('mp3', 'Mana Potion', 'Restores mana over time'),
    ('mp4', 'Greater Mana Potion', 'Restores mana over time'),
    ('mp5', 'Super Mana Potion', 'Restores mana over time'),
    ('rvs', 'Rejuvenation Potion', 'Instantly restores 35%'),
    ('rvl', 'Full Rejuvenation Potion', 'Instantly restores 100%'),
    ('vps', 'Stamina Potion', 'Restores stamina'),
    ('hp1', 'Minor Healing Potion', 'Restores life over time'),
    ('hp2', 'Light Healing Potion', 'Restores life over time'),
    ('hp3', 'Healing Potion', 'Restores life over time'),
    ('hp4', 'Greater Healing Potion', 'Restores life over time'),
    ('hp5', 'Super Healing Potion', 'Restores life over time'),
    ('wms', 'Thawing Potion', '+50% cold resistance'),
    ('yps', 'Antidote Potion', '+50% poison resistance'),
)


def cases():
    result = []
    for code, name, effect in EXAMPLES:
        item = Item(name, 'normal', complete=True)
        for scenario, specimen in (
            ('positive', item),
            ('negative', replace(item, ethereal=True)),
            ('unknown', replace(item, complete=False)),
        ):
            result.append(
                Case(
                    id=f'consumable-{code}-{scenario}',
                    item=specimen,
                    context={},
                    expected={
                        'assessment': IsPartialDict(
                            family='consumable',
                            quality_policy='consumable',
                            utility=IsPartialDict(
                                status='usable' if scenario == 'positive' else 'review', variable_rolls=False
                            ),
                            contract=IsPartialDict(policy='consumable', base_code=code)
                            if scenario == 'positive'
                            else None,
                        ),
                        **(
                            {
                                'price_estimate': IsPartialDict(
                                    estimate_ist=None, unavailable_reason='capture_incomplete'
                                )
                            }
                            if scenario == 'unknown'
                            else {}
                        ),
                    },
                    covers=('consumable:' + code,),
                    scenario=scenario,
                    report_contains=(effect, 'player'),
                    evidence=(
                        f'third-parties/d2data/json/misc.json:/{code}',
                        'pricing/data/appraisal-guide-sections.json:/sources/pricing~1raw~1mr~1guides__zeal-paladin.html/sections/44',
                    ),
                )
            )
    return tuple(result)


CASES = cases()
