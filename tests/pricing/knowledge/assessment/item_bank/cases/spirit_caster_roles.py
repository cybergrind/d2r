"""Spirit gear/swap alternatives retain base scope and rune recipient semantics."""

from dataclasses import fields, replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_endgame import RUNES, shield
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


WARLOCK = (('blood-boil-warlock-guide', 29), ('summoner-warlock-guide', 29))
SORC_EXACT = (('frozen-orb-sorceress', 29), ('frozen-orb-meteor-sorceress', 29))
SORC_GENERIC = (('fire-wall-sorceress-guide', 30), ('hydra-sorceress', 29))
NECRO = (('summoner-necromancer-guide', 33),)
USES = (
    ('warlock-swords', 'Warlock', False, False, tuple((g, n, 'weapon') for g, n in WARLOCK)),
    ('sorc-generic-swords', 'Sorceress', False, False, tuple((g, n, 'weapon') for g, n in SORC_GENERIC)),
    ('sorc-crystal-swords', 'Sorceress', False, True, tuple((g, n, 'weapon') for g, n in SORC_EXACT)),
    ('necro-crystal-sword', 'Necromancer', False, True, tuple((g, n, 'weapon') for g, n in NECRO)),
    (
        'warlock-shields',
        'Warlock',
        True,
        False,
        (
            ('blood-boil-warlock-guide', 29, 'off-hand'),
            ('blood-boil-warlock-guide', 29, 'off-hand-swap'),
            ('summoner-warlock-guide', 29, 'off-hand-swap'),
        ),
    ),
    (
        'sorc-monarchs',
        'Sorceress',
        True,
        True,
        tuple((g, n, slot) for g, n in (*SORC_EXACT, *SORC_GENERIC) for slot in ('off-hand', 'off-hand-swap')),
    ),
    (
        'necro-monarchs',
        'Necromancer',
        True,
        True,
        tuple((g, n, slot) for g, n in NECRO for slot in ('off-hand', 'off-hand-swap')),
    ),
)


def observation(item, **changes):
    # Unknown flags/counts have no invented native ItemData. This fixture starts
    # at the decoded-observation boundary, preserving the supplied uncertainty.
    return replace(Item(**{f.name: getattr(item, f.name) for f in fields(Item)}), **changes)


def spirit(quality, is_shield, *, maximum=False):
    item = shield(
        'Monarch', quality, fcr=35 if maximum else 25, mana=112 if maximum else 89, absorb=8 if maximum else 3
    )
    if is_shield:
        return item
    return replace(
        item,
        base='Crystal Sword',
        raw_stats=(
            *(s for s in item.raw_stats if s[0] not in (20, 78, 41, 43, 45)),
            (60, 0, 7),
        ),
    )


def cases():
    for group, klass, is_shield, exact, sources in USES:
        roles = tuple(f'{g}-spirit-{slot}-core-caster-word-gear' for g, _, slot in sources)
        configs = tuple(role + '-stats' for role in roles)
        keys = ('127:0', '105:0', '99:0', '9:0', '3:0', '147:0', '32:0')
        if is_shield:
            keys += ('41:0', '43:0', '45:0')
        context = {'player_class': klass}
        for quality in ('normal', 'superior', 'low_quality'):
            item = spirit(quality, is_shield)
            examples = [
                ('minimum', item, context, 'true'),
                ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
            ]
            if quality == 'normal':
                alternate = replace(item, base='Ward' if is_shield else 'Broad Sword')
                if is_shield:
                    alternate = replace(
                        alternate,
                        raw_stats=tuple(
                            (sid, layer, 24 if sid == 20 else raw) for sid, layer, raw in alternate.raw_stats
                        ),
                    )
                examples.extend(
                    (
                        ('maximum', spirit(quality, is_shield, maximum=True), context, 'true'),
                        ('ethereal', replace(item, ethereal=True), context, 'false' if is_shield else 'true'),
                        (
                            'unknown-ethereal',
                            observation(item, ethereal=None),
                            context,
                            'unknown' if is_shield else 'true',
                        ),
                        ('other-legal-base', alternate, context, None if exact else 'true'),
                        ('component-fcr', item, dict(context, player_total_fcr=25), 'true'),
                        ('missing-rune', replace(item, socket_items=RUNES[:-1]), context, None),
                        ('unidentified', replace(item, identified=False), context, None),
                        (
                            'unknown-sockets',
                            observation(
                                item,
                                sockets=None,
                                socket_contents='unknown',
                                socket_items=(),
                                raw_stats=tuple(s for s in item.raw_stats if s[0] != 194),
                            ),
                            context,
                            'unknown',
                        ),
                    )
                )
            for label, candidate, loadout, truth in examples:
                expected = {}
                if truth is not None:
                    expected['roles'] = Contains(
                        *(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles)
                    )
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(*configs)) for key in keys}
                        )
                    )
                yield Case(
                    id=f'spirit-caster/{group}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown', None: 'negative'}[truth],
                    expected={'assessment': IsPartialDict(**expected)},
                    absent_configurations=() if truth == 'true' else configs,
                    absent_stat_configurations=dict.fromkeys(('60:0', '78:0', '20:0'), configs),
                    report_contains=('Spirit', 'Sockets: 4 — Tal, Thul, Ort, Amn') if label == 'minimum' else (),
                    evidence=(
                        'third-parties/d2data/json/runes.json:/Spirit',
                        *(
                            f'pricing/data/appraisal-guide-sections.json:/sources/'
                            f'pricing~1raw~1mr~1guides__{g}.html/sections/{n}'
                            for g, n, _ in sources
                        ),
                    ),
                )


CASES = tuple(cases())
