"""Explicit caster word alternatives preserve recipe capacity and damage-type relevance."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_player_words import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


ROLES = {
    'plague': 'plague-weapon-main-alternatives-caster-word-remainder',
    'obsession': 'obsession-weapon-main-alternatives-caster-word-remainder',
    'splendor': 'splendor-off-hand-main-alternatives-word-utility-alternative',
}


def cases():
    for slug, _, name, base, count, _, stats, keys, irrelevant in EXAMPLES:
        if slug not in ROLES:
            continue
        role = 'abyss-warlock-build-guide-player-' + ROLES[slug]
        context = {'player_class': 'Warlock'}
        for quality in ('normal', 'superior', 'low_quality'):
            item = Item(base, quality, name, stats, sockets=count, socket_contents='filled', runeword=name)
            for label, candidate, loadout, truth in (
                ('native-low', item, context, 'true'),
                ('ethereal', replace(item, ethereal=True), context, 'false' if slug == 'splendor' else 'true'),
                (
                    'unknown-ethereal',
                    replace(item, ethereal=None),
                    context,
                    'unknown' if slug == 'splendor' else 'true',
                ),
                ('empty', replace(item, socket_contents='empty'), context, 'false'),
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('wrong-count', replace(item, sockets=count - 1), context, 'false'),
                ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
            ):
                expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
                if truth == 'true':
                    expected['stat_evaluation'] = IsPartialDict(
                        annotations=IsPartialDict(
                            {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                        )
                    )
                yield Case(
                    id=f'abyss/caster-word-alternatives/{slug}/{quality}/{label}',
                    item=candidate,
                    context=loadout,
                    expected={
                        'assessment': IsPartialDict(**expected),
                        'price_estimate': IsPartialDict(estimate_ist=None),
                    },
                    covers=(role,),
                    scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                    absent_configurations=() if truth == 'true' else (role + '-stats',),
                    absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                    report_contains=(name,),
                    evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/runes.json'),
                )


CASES = tuple(cases())
