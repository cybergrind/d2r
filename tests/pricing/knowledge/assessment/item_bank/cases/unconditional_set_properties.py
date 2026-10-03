"""Unconditional set extras must participate in the named appraisal contract."""

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


BASE_STATS = ((31, 0, 74), (105, 0, 20), (43, 0, 30), (188, 16, 2))
CASES = (
    Case(
        id='unconditional-set/claws-poison',
        item=Item('Heavy Bracers', 'set', "Trang-Oul's Claws", (*BASE_STATS, (332, 0, 25)), complete=True),
        context={},
        expected={
            'assessment': IsPartialDict(
                price_gaps=[],
                contract=IsPartialDict(intrinsic_properties=IsPartialDict({'783': 25})),
            )
        },
        scenario='positive',
        covers=("named:set:Trang-Oul's Claws",),
        report_contains=('+25% to Poison Skill Damage',),
        evidence=('pricing/raw/d2data/setitems.json',),
    ),
    Case(
        id='unconditional-set/claws-missing-poison',
        item=Item('Heavy Bracers', 'set', "Trang-Oul's Claws", BASE_STATS, complete=True),
        context={},
        expected={
            'assessment': IsPartialDict(
                contract=None,
                price_gaps=Contains('Named property 332:0 was not captured.'),
            )
        },
        scenario='unknown',
        covers=("named:set:Trang-Oul's Claws",),
        evidence=('pricing/raw/d2data/setitems.json',),
    ),
)
