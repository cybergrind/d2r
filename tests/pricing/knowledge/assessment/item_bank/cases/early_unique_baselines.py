"""Leveling uniques retain useful modifiers without being promoted to premium trades."""

from dataclasses import dataclass, replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


@dataclass(frozen=True)
class Review:
    name: str
    base: str
    native_id: int
    level: int
    strength: int
    dexterity: int
    leveling: str
    player_class: str
    stats: tuple
    snippets: tuple
    side: str = 'player'
    trade: str = 'low'


REVIEWS = (
    Review(
        'Bloodfist',
        'Heavy Gloves',
        103,
        9,
        0,
        0,
        'high',
        'Paladin',
        ((7, 0, 40 * 256), (99, 0, 30), (93, 0, 10), (16, 0, 15)),
        ('30% Faster Hit Recovery', '10% Increased Attack Speed'),
    ),
    Review(
        "Biggin's Bonnet",
        'Cap',
        71,
        3,
        0,
        0,
        'med',
        'Paladin',
        ((7, 0, 15 * 256), (9, 0, 15 * 256), (19, 0, 30)),
        ('+15 to Life', '+15 to Mana'),
    ),
    Review(
        'Bane Ash',
        'Short Staff',
        54,
        5,
        0,
        0,
        'med',
        'Sorceress',
        ((93, 0, 20), (17, 0, 55), (18, 0, 55), (107, 36, 5), (107, 37, 2), (39, 0, 50)),
        ('20% Increased Attack Speed', '(50-60%)', 'Fire Bolt', 'Warmth'),
    ),
    Review(
        'Blood Crescent',
        'Scimitar',
        26,
        7,
        0,
        21,
        'med',
        'Paladin',
        ((93, 0, 15), (60, 0, 15), (39, 0, 15), (41, 0, 15), (43, 0, 15), (45, 0, 15)),
        ('15% Increased Attack Speed', '15% Life stolen per hit'),
    ),
    Review(
        'Bloodrise',
        'Morning Star',
        20,
        15,
        36,
        0,
        'med',
        'Paladin',
        ((93, 0, 10), (107, 96, 3), (60, 0, 5)),
        ('10% Increased Attack Speed', 'Sacrifice'),
    ),
    Review(
        'Bonesnap',
        'Maul',
        23,
        24,
        69,
        0,
        'high',
        'Barbarian',
        ((136, 0, 40), (39, 0, 30), (43, 0, 30)),
        ('40% Chance of Crushing Blow', 'Fire Resist +30%'),
    ),
    Review(
        'Carin Shard',
        'Petrified Wand',
        140,
        35,
        25,
        0,
        'med',
        'Necromancer',
        ((105, 0, 10), (99, 0, 30), (83, 2, 1), (188, 18, 2)),
        ('10% Faster Cast Rate', 'Summoning Skills', 'Necromancer'),
    ),
    Review(
        'Blackhand Key',
        'Grave Wand',
        142,
        41,
        25,
        0,
        'med',
        'Necromancer',
        ((105, 0, 30), (39, 0, 37), (83, 2, 2), (188, 16, 1)),
        ('30% Faster Cast Rate', 'Curses', 'Necromancer'),
    ),
)


def cases(reviews=REVIEWS, *, prefix='early-unique-baseline'):
    for review in reviews:
        item = Item(review.base, 'unique', review.name, review.stats)
        wearer = 'mercenary' if review.side == 'merc' else 'player'
        context = {
            'player_class': review.player_class,
            f'{wearer}_level': review.level,
            f'{wearer}_strength': review.strength,
            f'{wearer}_dexterity': review.dexterity,
        }
        if review.side == 'merc':
            context.update(player_level=99, player_strength=300, player_dexterity=300)
        variants = [
            ('equip-level', item, context, 'positive', 'met'),
            ('below-level', item, {**context, f'{wearer}_level': review.level - 1}, 'negative', 'unmet'),
            (
                'unknown-level',
                item,
                {k: v for k, v in context.items() if k != f'{wearer}_level'},
                'unknown',
                'unknown',
            ),
            ('unidentified', replace(item, identified=False), context, 'negative', None),
        ]
        for attribute in ('strength', 'dexterity'):
            value = getattr(review, attribute)
            if value:
                variants.append(
                    (
                        f'below-{attribute}',
                        item,
                        {**context, f'{wearer}_{attribute}': value - 1},
                        'negative',
                        'unmet',
                    )
                )
        for label, candidate, loadout, scenario, fit in variants:
            assessment = (
                IsPartialDict(
                    trade_tier=IsPartialDict(status='reviewed', tier=review.trade),
                    leveling=Contains(
                        IsPartialDict(
                            tier=review.leveling,
                            side=review.side,
                            required_level=review.level,
                            requirements_fit=IsPartialDict(status=fit),
                        )
                    ),
                )
                if fit
                else IsPartialDict(leveling=[])
            )
            yield Case(
                id=f'{prefix}/{review.name}/{label}',
                item=candidate,
                context=loadout,
                scenario=scenario,
                covers=(f'named:unique:{review.name}',),
                expected={'assessment': assessment, 'price_estimate': IsPartialDict(estimate_ist=None)},
                report_contains=(
                    review.name,
                    f'Trade tier: {"mid" if review.trade == "med" else review.trade}',
                    *(('Leveling: high',) if review.leveling == 'high' else ()),
                    *review.snippets,
                )
                if fit
                else (),
                report_absent=('Leveling: mid', 'Leveling: low')
                + (('Trade tier:', 'Leveling:') if fit is None else ()),
                evidence=(
                    f'third-parties/d2data/json/uniqueitems.json:/{review.native_id}',
                    'third-parties/d2data/json/armor.json',
                    'third-parties/d2data/json/weapons.json',
                    'pricing/knowledge/assessment/rules/named_baselines.json',
                    f'pricing/knowledge/assessment/rules/named_leveling_reviews.json:unique:{review.name}',
                    'pricing/data/appraisal-recommendations.json',
                ),
            )


CASES = tuple(cases())
