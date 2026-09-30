"""Native Spirit shield rolls in six endgame component configurations."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


RUNES = tuple(SocketItem(name + ' Rune') for name in ('Tal', 'Thul', 'Ort', 'Amn'))
TAL_SET = (
    "Tal Rasha's Lidless Eye",
    "Tal Rasha's Horadric Crest",
    "Tal Rasha's Guardianship",
    "Tal Rasha's Fine-Spun Cloth",
    "Tal Rasha's Adjudication",
)
USES = (
    (
        'hammer-standard-spirit-shield',
        'Paladin',
        'Sacred Targe',
        'blessed-hammer-paladin',
        1,
        125,
        None,
        ('Sling', "Hellwarden's Will"),
    ),
    (
        'hammer-mf-spirit-shield',
        'Paladin',
        'Sacred Targe',
        'blessed-hammer-paladin',
        2,
        125,
        None,
        ('Void', 'Sling', 'Arachnid Mesh'),
    ),
    ('blizzard-set-spirit-shield', 'Sorceress', 'Monarch', 'blizzard-sorceress', 3, 105, 86, TAL_SET),
    ('meteor-standard-spirit-shield', 'Sorceress', 'Monarch', 'meteor-sorceress', 1, 63, 60, ('The Oculus',)),
    ('meteor-mf-spirit-shield', 'Sorceress', 'Monarch', 'meteor-sorceress', 2, 105, 60, ('The Oculus', *TAL_SET[2:])),
    ('meteor-set-spirit-shield', 'Sorceress', 'Monarch', 'meteor-sorceress', 3, 105, 86, TAL_SET),
)


def shield(base, quality, *, fcr=25, mana=89, absorb=3):
    # Targe's native 45 all resistances are separate from the shield rune
    # contributions: Tal/Thul/Ort add 35 poison/cold/lightning, not fire.
    paladin = base == 'Sacred Targe'
    inherent = 45 if paladin else 0
    return NativeRunewordItem(
        base,
        quality,
        'Spirit',
        (
            (127, 0, 2),
            (105, 0, fcr),
            (99, 0, 55),
            (9, 0, mana * 256),
            (3, 0, 22),
            (147, 0, absorb),
            (32, 0, 250),
            (194, 0, 4),
            (20, 0, 30 if paladin else 22),
            (78, 0, 14),
            *((sid, 0, 35 + inherent) for sid in (41, 43, 45)),
            *(((39, 0, inherent),) if paladin else ()),
        ),
        sockets=4,
        socket_contents='filled',
        socket_items=RUNES,
        runeword='Spirit',
    )


def cases():
    for role, klass, base, guide, index, fcr, fhr, companions in USES:
        roles = (role,)
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass, 'player_total_fcr': fcr, 'player_items': list(companions)}
        if fhr is not None:
            context['player_total_fhr'] = fhr
        keys = ('127:0', '105:0', '99:0', '9:0', '3:0', '41:0', '43:0', '45:0')
        if klass == 'Paladin':
            keys += ('39:0',)
        for quality in ('normal', 'superior', 'low_quality'):
            item = shield(base, quality)
            examples = [
                ('minimum', item, context, 'true'),
                ('wrong-class', item, dict(context, player_class='Amazon'), 'false'),
                ('unknown-class', item, {k: v for k, v in context.items() if k != 'player_class'}, 'unknown'),
            ]
            if quality == 'normal':
                examples.extend(
                    (
                        ('maximum', shield(base, quality, fcr=35, mana=112, absorb=8), context, 'true'),
                        ('mixed-rolls', shield(base, quality, fcr=35, mana=89, absorb=3), context, 'true'),
                        ('component-fcr', item, dict(context, player_total_fcr=25), 'true'),
                        ('below-fcr', item, dict(context, player_total_fcr=fcr - 1), 'true'),
                        ('missing-companion', item, dict(context, player_items=list(companions[1:])), 'true'),
                        ('unknown-companions', item, {k: v for k, v in context.items() if k != 'player_items'}, 'true'),
                        ('missing-rune', replace(item, socket_items=RUNES[:-1]), context, None),
                        ('reversed-runes', replace(item, socket_items=tuple(reversed(RUNES))), context, None),
                        ('unidentified', replace(item, identified=False), context, None),
                    )
                )
            if quality == 'normal' and fhr is not None:
                examples.append(('below-fhr', item, dict(context, player_total_fhr=fhr - 1), 'true'))
            for label, candidate, loadout, truth in examples:
                incomplete = label in (
                    'component-fcr',
                    'below-fcr',
                    'below-fhr',
                    'missing-companion',
                    'unknown-companions',
                )
                supported = truth == 'true' and not incomplete
                expected = {}
                if truth is not None:
                    expected['roles'] = Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                result = {'assessment': IsPartialDict(**expected)}
                if supported:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                        )
                    )
                    result['assessment'] = IsPartialDict(**expected)
                    result['extraction'] = IsPartialDict(
                        decoded_stats=Contains(
                            *(
                                IsPartialDict(
                                    memory_stat=IsPartialDict(id=sid), roll_range=IsPartialDict(min=low, max=high)
                                )
                                for sid, low, high in ((105, 25, 35), (9, 89, 112), (147, 3, 8))
                            )
                        )
                    )
                yield Case(
                    id=f'spirit-endgame/{role}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario=('unknown' if label == 'unknown-companions' else 'negative')
                    if incomplete
                    else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown', None: 'negative'}[truth],
                    expected=result,
                    absent_configurations=() if supported else configs,
                    absent_stat_configurations=dict.fromkeys(('78:0', '20:0'), configs),
                    report_contains=('Sockets: 4 — Tal, Thul, Ort, Amn',) if label == 'minimum' else (),
                    evidence=(
                        'third-parties/d2data/json/runes.json:/Spirit',
                        f'pricing/data/wp-a-builds.json:/{guide}/variants/{index}',
                    ),
                )


CASES = tuple(cases())
