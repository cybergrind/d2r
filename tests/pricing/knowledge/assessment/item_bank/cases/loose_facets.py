"""Loose facet native identities, paired rolls and death/level-up events."""

from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.facet_shields import ELEMENTS
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def cases():
    for element, (mastery, pierce, death_id, up_id, fixed, death_skill, up_skill) in ELEMENTS.items():
        for up in (False, True):
            table_id = up_id if up else death_id
            skill, level = up_skill if up else death_skill
            event = (199 if up else 197, skill * 64 + level, 100)
            for label, damage, penetration, tier, scenario in (
                ('perfect', 5, 5, 'high', 'positive'),
                ('damage-one-short', 4, 5, 'low', 'negative'),
                ('pierce-one-short', 5, 4, 'low', 'negative'),
                ('unread-damage', None, 5, 'low', 'unknown'),
                ('unread-pierce', 5, None, 'low', 'unknown'),
            ):
                rolls = tuple(
                    (stat, 0, value) for stat, value in ((mastery, damage), (pierce, penetration)) if value is not None
                )
                complete = scenario != 'unknown'
                # The dated SC/NL/PC/RotW cache has three exact 1-Ist sellers
                # for each cold level-up 4/5 and5/4 variant. Market evidence
                # refines the qualitative low baseline; neither is perfect.
                market_mid = element == 'cold' and up and label in ('damage-one-short', 'pierce-one-short')
                tier_expectation = IsPartialDict(tier=tier)
                price_expectation = {'price_estimate': IsPartialDict(estimate_ist=None)} if not complete else {}
                if market_mid:
                    tier = 'med'
                    tier_expectation = IsPartialDict(
                        status='market_supported', tier='med', baseline=IsPartialDict(tier='low')
                    )
                    price_expectation = {
                        'price_estimate': IsPartialDict(
                            basis='classified_exact_variant_asks',
                            estimate_ist=1.0,
                            low_ist=1.0,
                            high_ist=1.0,
                            sellers=3,
                            dates=['2026-09-18'],
                        )
                    }
                yield Case(
                    id=f'loose-facet/{element}/{"level-up" if up else "death"}/{label}',
                    item=Item(
                        'Jewel',
                        'unique',
                        'Rainbow Facet',
                        (*fixed, *rolls, event),
                        complete=complete,
                        named_table_id=table_id,
                    ),
                    context={},
                    expected={
                        'assessment': IsPartialDict(
                            trade_tier=tier_expectation,
                            contract=IsPartialDict(name='Rainbow Facet', family='jewel', mode='exact_variant')
                            if complete
                            else None,
                        ),
                        **price_expectation,
                    },
                    covers=('named:unique:Rainbow Facet',),
                    scenario=scenario,
                    report_contains=(
                        'Rainbow Facet',
                        'Trade tier: ' + ('mid' if tier == 'med' else tier),
                        '(3-5%)',
                        'when you Level-Up' if up else 'when you Die',
                    ),
                    report_absent=('Trade tier: high',) if tier != 'high' else (),
                    evidence=(
                        f'third-parties/d2data/json/uniqueitems.json:/{table_id}',
                        'pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/unique:Rainbow Facet',
                    )
                    + (('pricing/raw/traderie/wph-facet-cold-levelup.json',) if market_mid else ()),
                )


CASES = tuple(cases())
