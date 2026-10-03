"""Splendor shield families, observed staffmods and active-slot qualifications."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import observation
from tests.pricing.knowledge.assessment.item_bank.models import Case, SocketItem
from tests.pricing.knowledge.assessment.item_bank.native_runeword import NativeRunewordItem


SPECS = (
    ('echoing-strike-warlock-guide', 'Warlock', 'Off-Hand', 2),
    ('enchant-sorceress', 'Sorceress', 'Off-Hand-Swap', 2),
    ('fire-warlock-guide', 'Warlock', 'Off-Hand', 7),
    ('summoner-necromancer-guide', 'Necromancer', 'Off-Hand', 3),
    ('blood-boil-warlock-guide', 'Warlock', None, 29),
    ('summoner-warlock-guide', 'Warlock', None, 29),
)
RUNES = tuple(SocketItem(r + ' Rune') for r in ('Eth', 'Lum'))
KEYS = ('127:0', '105:0', '102:0', '80:0', '79:0', '27:0', '1:0')
CAVEAT = (
    'Bonuses apply only while this shield is active; All Skills does not grant Battle Orders without '
    'the actual Call to Arms weapon. Faster Cast Rate does not speed attacks or trap placement. '
    'Class-specific shield staffmods/resistance remain additional base properties, not assumed recipe bonuses.'
)


def shield(quality, defense=60):
    return NativeRunewordItem(
        'Small Shield',
        quality,
        'Splendor',
        (
            (127, 0, 1),
            (105, 0, 10),
            (102, 0, 20),
            (80, 0, 20),
            (79, 0, 50),
            (27, 0, 15),
            (1, 0, 10),
            (16, 0, defense),
            (89, 0, 3),
            (194, 0, 2),
        ),
        sockets=2,
        socket_contents='filled',
        runeword='Splendor',
        socket_items=RUNES,
    )


def cases():
    for klass in ('Warlock', 'Sorceress', 'Necromancer'):
        specs = tuple(s for s in SPECS if s[1] == klass)
        roles = tuple(
            f'{build}-player-splendor-{slot.lower()}-main-alternatives-word-utility-alternative'
            if slot
            else f'{build}-splendor-caster-recipe-gear'
            for build, _, slot, _ in specs
        )
        configs = tuple(role + '-stats' for role in roles)
        sources = tuple(
            f'pricing/data/wp-a-builds.json:/{build}/slots/{slot}/{index}'
            if slot
            else 'pricing/data/appraisal-guide-sections.json:/sources/'
            f'pricing~1raw~1mr~1guides__{build}.html/sections/{index}'
            for build, _, slot, index in specs
        )
        context = {'player_class': klass}
        staffmod = 388 if klass == 'Warlock' else 70
        staffmod_name = 'Echoing Strike' if klass == 'Warlock' else 'Raise Skeleton'
        for quality in ('normal', 'superior', 'low_quality'):
            item = shield(quality)
            examples = [
                ('minimum', item, context, 'true'),
                ('maximum', shield(quality, 100), context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', observation(item, ethereal=None), context, 'unknown'),
                ('wrong-class', item, {'player_class': 'Paladin'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('empty', replace(item, socket_items=(), socket_contents='empty'), context, 'false'),
                ('wrong-recipe', replace(item, socket_items=RUNES[::-1]), context, 'false'),
                ('paladin-shield', replace(item, base='Sacred Targe'), context, 'false'),
                ('weapon', replace(item, base='Crystal Sword'), context, 'false'),
            ]
            if klass != 'Sorceress':
                class_item = replace(item, base='Grimoire' if klass == 'Warlock' else 'Demon Head')
                examples.extend(
                    [
                        ('class-base', class_item, context, 'true'),
                        (
                            'class-staffmod',
                            replace(class_item, raw_stats=(*item.raw_stats, (107, staffmod, 3))),
                            context,
                            'true',
                        ),
                    ]
                )
            for label, candidate, loadout, truth in examples:
                active = truth == 'true'
                expected = {}
                if label not in ('unidentified', 'empty', 'wrong-recipe', 'paladin-shield', 'weapon'):
                    expected['roles'] = Contains(
                        *(
                            IsPartialDict(
                                id=role,
                                side='player',
                                slot=spec[2] or 'Off-Hand',
                                rule_trace=IsPartialDict(truth=truth),
                                missing=Contains(
                                    CAVEAT,
                                    *(
                                        (
                                            'A shield requires a compatible main-hand setup. '
                                            'Only a Book off-hand permits the Warlock two-handed weapon exception.',
                                        )
                                        if spec[2] is None
                                        else ()
                                    ),
                                ),
                            )
                            for role, spec in zip(roles, specs, strict=True)
                        )
                    )
                if active:
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {
                                key: IsPartialDict(
                                    contributions=Contains(
                                        *(
                                            IsPartialDict(
                                                configuration_id=config,
                                                desirability='desirable' if key in ('127:0', '105:0') else 'supporting',
                                            )
                                            for config in configs
                                        )
                                    )
                                )
                                for key in KEYS
                            }
                        )
                    )
                yield Case(
                    id=f'splendor-shield-choices/{klass}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    covers=roles,
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    absent_configurations=() if active else configs,
                    absent_stat_configurations={'93:0': configs, f'107:{staffmod}': configs},
                    report_contains=(('Splendor', 'Eth, Lum') + ((staffmod_name,) if label == 'class-staffmod' else ()))
                    if active
                    else (),
                    evidence=(
                        *sources,
                        'third-parties/d2data/json/runes.json:/Splendor',
                        'third-parties/d2data/json/gems.json',
                        'third-parties/d2data/json/skills.json',
                    ),
                )


CASES = tuple(cases())
