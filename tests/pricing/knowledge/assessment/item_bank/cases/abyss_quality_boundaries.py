"""Reviewed quality variants preserve rejection and uncertainty through appraisal."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_words import EXAMPLES as MERC_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_player_words import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_void import RAW as VOID_RAW
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


def case(role, label, item, truth, context):
    return Case(
        id=f'abyss/quality-boundaries/{role}/{item.rarity}/{label}',
        item=item,
        context=context,
        expected={
            'assessment': IsPartialDict(roles=Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth))))
        },
        covers=(role,),
        scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
        absent_configurations=() if truth == 'true' else (role + '-stats',),
        evidence=(
            'pricing/data/appraisal-guide-sections.json',
            'third-parties/d2data/json/runes.json' if item.runeword else 'third-parties/d2data/json/magicsuffix.json',
        ),
    )


def cases():
    words = [
        ('abyss-warlock-player-word-' + slug, name, base, sockets, raw)
        for slug, span, name, base, sockets, slot, raw, keys, irrelevant in EXAMPLES
    ]
    words += [
        (
            'abyss-warlock-player-utility-cta',
            'Call to Arms',
            'Crystal Sword',
            5,
            ((97, 149, 1), (97, 155, 2), (127, 0, 1)),
        ),
        ('abyss-warlock-table-dagger-void', 'Void', 'Kriss', 3, VOID_RAW),
        (
            'abyss-warlock-build-guide-player-void-weapon-main-alternatives-caster-word-remainder',
            'Void',
            'Kriss',
            3,
            VOID_RAW,
        ),
    ]
    for role, name, base, sockets, raw in words:
        for quality in ('superior', 'low_quality'):
            item = Item(base, quality, name, raw, sockets=sockets, socket_contents='filled', runeword=name)
            yield case(role, 'empty', replace(item, socket_contents='empty'), 'false', {'player_class': 'Warlock'})
            yield case(role, 'unknown-sockets', replace(item, sockets=None), 'unknown', {'player_class': 'Warlock'})
            if role.endswith('caster-word-remainder'):
                yield case(role, 'native-low', item, 'true', {'player_class': 'Warlock'})
    for slug, _span, original, _keys in MERC_WORDS:
        role = 'abyss-warlock-merc-table-' + slug
        for quality in ('superior', 'low_quality'):
            item = replace(original, rarity=quality)
            yield case(role, 'wrong-merc', item, 'false', {'player_class': 'Warlock', 'mercenary_type': 'Act 5 Frenzy'})
            yield case(role, 'unknown-merc', item, 'unknown', {'player_class': 'Warlock'})
    for role in ('abyss-warlock-build-guide-skill-charge-combination', 'abyss-warlock-table-dagger-arch-devil'):
        item = Item('Kriss', 'rare', raw_stats=((204, 5827, 82 << 8),), complete=True)
        yield case(role, 'missing-prefix', item, 'false', {'player_class': 'Warlock'})
        yield case(
            role,
            'unread-charge',
            replace(item, raw_stats=((83, 7, 2),), complete=False),
            'unknown',
            {'player_class': 'Warlock'},
        )
    role = 'abyss-warlock-player-utility-teleport'
    item = Item('Long Staff', 'rare', raw_stats=((204, 91 * 64 + 3, (82 << 8) | 1),), complete=True)
    yield case(role, 'wrong-charge', item, 'false', {'player_class': 'Warlock'})
    yield case(
        role, 'unread-charge', replace(item, raw_stats=(), complete=False), 'unknown', {'player_class': 'Warlock'}
    )


CASES = tuple(cases())
