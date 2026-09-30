"""RotW charm identity baselines survive incomplete rolls without inventing prices."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


SPECS = (
    ('Latent Black Cleft', 432, 193, 37, -45),
    ('Latent Bone Break', 431, 192, 36, -10),
    ('Latent Crack of the Heavens', 429, 190, 41, -70),
    ('Renewed Black Cleft', 437, 193, 37, -45),
    ('Renewed Bone Break', 436, 192, 36, -10),
    ('Renewed Cold Rupture', 427, 187, 43, -70),
    ('Renewed Crack of the Heavens', 434, 190, 41, -70),
    ('Renewed Flame Rift', 433, 189, 39, -70),
)


def cases():
    for name, native, effect, penalty, value in SPECS:
        base = 'Crafted Sunder Charm' if name.startswith('Renewed') else 'Grand Charm'
        item = Item(base, 'unique', name, ((effect, 0, 300), (penalty, 0, value)), named_table_id=native)
        for label, candidate, scenario in (
            ('observed-core', item, 'positive'),
            ('unidentified', replace(item, identified=False), 'negative'),
            ('unread-effect', replace(item, raw_stats=((penalty, 0, value),)), 'unknown'),
        ):
            assessment = {'trade_tier': IsPartialDict(tier='low' if candidate.identified else None), 'contract': None}
            expected = {'assessment': IsPartialDict(**assessment), 'price_estimate': IsPartialDict(estimate_ist=None)}
            if label == 'observed-core':
                expected['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat={'id': effect, 'layer': 0, 'raw': 300},
                            status='decoded',
                            value=300,
                        )
                    )
                )
            yield Case(
                id=f'named-rotw-sunder/{name}/{label}',
                item=candidate,
                context={},
                scenario=scenario,
                covers=('named:unique:' + name,),
                expected=expected,
                report_contains=(name, 'Trade tier: low') if candidate.identified else (name,),
                report_absent=('Trade tier: high',) if candidate.identified else ('Trade tier:',),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{native}',
                    f'pricing/knowledge/assessment/rules/named_tier_reviews.json:/rows/unique:{name}',
                ),
            )


CASES = tuple(cases())
