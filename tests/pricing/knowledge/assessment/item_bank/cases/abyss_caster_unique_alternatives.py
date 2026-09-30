"""Explicit caster alternatives: native utility, upgrade identities, irrelevant attack stats."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_caster_weapons import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Case


SUFFIXES = {
    'razorswitch': 'razorswitch-caster-utility-alternative',
    'suicide-branch': 'suicide-branch-caster-progression-alternative',
    'spectral-shard': 'spectral-shard-caster-survival-alternative',
    'wizardspike': 'wizardspike-weapon-utility-alternative',
}


def cases(build='abyss-warlock-build-guide', player_class='Warlock', prefix='abyss', suffixes=SUFFIXES):
    for slug, _, item, upgrade, keys, irrelevant in EXAMPLES:
        if slug not in suffixes:
            continue
        role = build + '-' + suffixes[slug]
        context = {'player_class': player_class}
        rows = [
            ('native', item, context, 'true'),
            ('wrong-class', item, {'player_class': 'Sorceress'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('ethereal', replace(item, ethereal=True), context, 'false' if slug == 'wizardspike' else 'true'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown' if slug == 'wizardspike' else 'true'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('one-empty-socket', replace(item, sockets=1), context, 'true'),
        ]
        if upgrade:
            rows.append(('upgraded', replace(item, base=upgrade), context, 'true'))
        if slug in ('razorswitch', 'spectral-shard'):
            rows += [
                ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                ('invalid-sockets', replace(item, sockets=2), context, 'false'),
            ]
        for label, candidate, loadout, truth in rows:
            expected = {'roles': Contains(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)))}
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(role + '-stats')) for key in keys}
                    )
                )
                if slug == 'wizardspike':
                    expected['facts'] = IsPartialDict(stats=IsPartialDict({'217:0': IsPartialDict(value=160)}))
            yield Case(
                id=f'{prefix}/caster-unique-alternatives/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=(role,),
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else (role + '-stats',),
                absent_stat_configurations=dict.fromkeys(irrelevant, (role + '-stats',)),
                report_contains=(candidate.name, 'Trade tier:') if truth == 'true' else (candidate.name,),
                evidence=('pricing/data/wp-a-builds.json', 'third-parties/d2data/json/uniqueitems.json'),
            )


CASES = tuple(cases())
