"""Useful Spirit components: exact guide bases, native rolls and loadout gates."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation, spirit
from tests.pricing.knowledge.assessment.item_bank.cases.spirit_endgame import RUNES, shield
from tests.pricing.knowledge.assessment.item_bank.models import Case


USES = (
    ('lightning-sword', 'Sorceress', 'Crystal Sword', ('lightning-starter-spirit-sword',), 117),
    ('lightning-shield', 'Sorceress', 'Monarch', ('lightning-starter-spirit-shield',), 117),
    ('fissure-sword', 'Druid', 'Crystal Sword', ('fissure-starter-spirit-sword',), None),
    ('hammer-sword', 'Paladin', 'Crystal Sword', ('hammer-starter-spirit-sword',), None),
    (
        'paladin-shields',
        'Paladin',
        'Targe',
        ('hammer-starter-spirit-shield', 'foh-starter-spirit-shield', 'holy-bolt-starter-spirit-shield'),
        None,
    ),
)
SOURCE_VARIANTS = {
    'lightning-sword': ('lightning-sorceress/variants/0',),
    'lightning-shield': ('lightning-sorceress/variants/0',),
    'fissure-sword': ('fissure-druid/variants/0',),
    'hammer-sword': ('blessed-hammer-paladin/variants/0',),
    'paladin-shields': (
        'blessed-hammer-paladin/variants/0',
        'fist-of-the-heavens-paladin/variants/0',
        'fist-of-the-heavens-paladin/variants/1',
    ),
}


def item_for(base, quality, maximum=False):
    if base != 'Targe':
        return spirit(quality, base == 'Monarch', maximum=maximum)
    item = shield(
        'Sacred Targe', quality, fcr=35 if maximum else 25, mana=112 if maximum else 89, absorb=8 if maximum else 3
    )
    return replace(item, base='Targe', raw_stats=tuple((s, p, 10 if s == 20 else v) for s, p, v in item.raw_stats))


def cases():
    for group, klass, base, roles, threshold in USES:
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass, **({'player_total_fcr': threshold} if threshold else {})}
        priorities = {
            '127:0': 'desirable',
            '105:0': 'desirable',
            '99:0': 'supporting',
            '9:0': 'supporting',
            '3:0': 'supporting',
        }
        if base != 'Crystal Sword':
            priorities.update(dict.fromkeys(('41:0', '43:0', '45:0'), 'supporting'))
        if base == 'Targe':
            priorities['39:0'] = 'supporting'
        for quality in ('normal', 'superior', 'low_quality'):
            item = item_for(base, quality)
            examples = [
                ('minimum', item, context, 'true', True),
                ('wrong-class', item, dict(context, player_class='Amazon'), 'false', False),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown', False),
            ]
            if quality == 'normal':
                examples.extend(
                    (
                        ('maximum', item_for(base, quality, True), context, 'true', True),
                        ('missing-rune', replace(item, socket_items=RUNES[:-1]), context, None, False),
                        ('reversed-runes', replace(item, socket_items=RUNES[::-1]), context, None, False),
                        ('unidentified', replace(item, identified=False), context, None, False),
                        (
                            'unknown-sockets',
                            observation(
                                item,
                                sockets=None,
                                socket_items=(),
                                socket_contents='unknown',
                                raw_stats=tuple(s for s in item.raw_stats if s[0] != 194),
                            ),
                            context,
                            'unknown',
                            False,
                        ),
                        (
                            'uncaptured-fcr',
                            replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 105)),
                            context,
                            'true',
                            True,
                        ),
                    )
                )
                if threshold:
                    examples.extend(
                        (
                            ('below-total-fcr', item, dict(context, player_total_fcr=threshold - 1), 'true', False),
                            ('item-is-not-total-fcr', item, dict(context, player_total_fcr=25), 'true', False),
                            ('unknown-total-fcr', item, {'player_class': klass}, 'true', False),
                        )
                    )
            for label, candidate, loadout, truth, supported in examples:
                captured = {f'{s}:{p}' for s, p, _ in candidate.raw_stats}
                expected = {}
                if truth is not None:
                    expected['roles'] = Contains(
                        *(IsPartialDict(id=r, rule_trace=IsPartialDict(truth=truth)) for r in roles)
                    )
                if supported:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        *(IsPartialDict(configuration_id=c, desirability=grade) for c in configs)
                                    )
                                )
                                for key, grade in priorities.items()
                                if key in captured
                            }
                        )
                    )
                missing = {key: configs for key in priorities if key not in captured}
                missing.update(dict.fromkeys(('60:0', '78:0', '20:0'), configs))
                if base == 'Crystal Sword':
                    missing.update(dict.fromkeys(('39:0', '41:0', '43:0', '45:0'), configs))
                result = {'assessment': IsPartialDict(**expected)}
                if label in ('minimum', 'maximum'):
                    result['extraction'] = IsPartialDict(
                        decoded_stats=Contains(
                            *(
                                IsPartialDict(memory_stat=IsPartialDict(id=s), roll_range=IsPartialDict(min=lo, max=hi))
                                for s, lo, hi in ((105, 25, 35), (9, 89, 112), (147, 3, 8))
                            )
                        )
                    )
                yield Case(
                    id=f'spirit-progression/{group}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario='positive' if supported else 'unknown' if 'unknown' in label else 'negative',
                    expected=result,
                    absent_configurations=() if supported else configs,
                    absent_stat_configurations=missing,
                    report_contains=('Spirit', 'Sockets: 4 — Tal, Thul, Ort, Amn') if label == 'minimum' else (),
                    evidence=(
                        'third-parties/d2data/json/runes.json:/Spirit',
                        'third-parties/d2data/json/armor.json:/pa1',
                        *(f'pricing/data/wp-a-builds.json:/{source}' for source in SOURCE_VARIANTS[group]),
                    ),
                )


CASES = tuple(cases())
