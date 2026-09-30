"""Remaining Magefist gear alternatives and identity-preserving Fissure components."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.magefist_caster_tables import BASES, gloves
from tests.pricing.knowledge.assessment.item_bank.models import Case


# Source glove rows reviewed independently. Fire damage on attacks is not a
# spell bonus; the element-skill stat only receives credit in the fire uses.
USES = (
    (
        'sorc-casting',
        'Sorceress',
        False,
        (('blizzard-sorceress', 0), ('lightning-sorceress', 1), ('nova-sorceress-guide', 0)),
    ),
    ('sorc-fire', 'Sorceress', True, (('enchant-sorceress', 0), ('meteor-sorceress', 0))),
    ('assassin-casting', 'Assassin', False, (('dragon-talon-assassin', 3), ('lightning-sentry-assassin', 0))),
    ('assassin-fire', 'Assassin', True, (('fire-blast-assassin', 0), ('wake-of-fire-assassin', 0))),
    ('warlock-fire', 'Warlock', True, (('fire-warlock-guide', 0),)),
    ('warlock-echoing', 'Warlock', False, (('echoing-strike-warlock-guide', 1),)),
    ('druid-fire', 'Druid', True, (('fissure-druid', 0),)),
    ('paladin-casting', 'Paladin', False, (('fist-of-the-heavens-paladin', 0),)),
    ('barbarian-casting', 'Barbarian', False, (('double-throw-barbarian-guide', 8),)),
    ('fissure-components', 'Druid', True, (('standard', 1), ('magic-find', 2), ('ubers', 3))),
)


def cases():
    for group, klass, fire, sources in USES:
        component = group == 'fissure-components'
        roles = tuple(
            f'fissure-player-{guide}-magefist' if component else guide + '-magefist-caster-progression-alternative'
            for guide, _ in sources
        )
        configs = tuple(role + '-stats' for role in roles)
        context = {'player_class': klass}
        examples = [
            (f'{base}/{ed}', gloves(base, defense, ed), context, 'true') for base, defense in BASES for ed in (20, 30)
        ]
        item = gloves('Light Gauntlets', 12)
        examples.extend(
            (
                ('ethereal', replace(item, ethereal=True), context, 'false'),
                ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
                ('unidentified', replace(item, identified=False), context, 'false'),
                ('wrong-class', item, {'player_class': 'Amazon'}, 'false'),
                ('unknown-class', item, {}, 'unknown'),
                ('component-fcr', item, dict(context, player_total_fcr=20), 'true'),
                (
                    'unread-fire-skill',
                    replace(item, raw_stats=tuple(s for s in item.raw_stats if s[0] != 126), complete=False),
                    context,
                    'true',
                ),
            )
        )
        if not component:
            examples.extend(
                (
                    ('impossible-socket', replace(item, sockets=1), context, 'false'),
                    ('unknown-sockets', replace(item, sockets=None), context, 'unknown'),
                )
            )
        for label, candidate, loadout, truth in examples:
            fire_credit = fire and label != 'unread-fire-skill'
            upgrade_needed = component and candidate.base != 'Crusader Gauntlets'
            # The legacy role retains upgrade candidates, but its Ubers stat
            # configuration requires completing the source's elite upgrade.
            active_configs = configs[:-1] if upgrade_needed else configs
            role_expectations = []
            for role in roles:
                fields = {'id': role, 'rule_trace': IsPartialDict(truth=truth)}
                if role == 'fissure-player-ubers-magefist' and upgrade_needed and truth == 'true':
                    fields.update(
                        status='partial',
                        dependencies=Contains(
                            IsPartialDict(status='false', preparation=IsPartialDict(target_name='Crusader Gauntlets'))
                        ),
                    )
                role_expectations.append(IsPartialDict(**fields))
            expected = {'roles': Contains(*role_expectations)}
            if truth == 'true':
                keys = ('105:0', '27:0', *(('126:1',) if fire_credit else ()))
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {key: IsPartialDict(configuration_ids=Contains(*active_configs)) for key in keys}
                    )
                )
            absent = dict.fromkeys(('48:0', '49:0', '16:0', '31:0'), configs)
            if not fire_credit:
                absent['126:1'] = configs
            result = {'assessment': IsPartialDict(**expected)}
            if truth == 'true':
                ed = next(raw for sid, _, raw in candidate.raw_stats if sid == 16)
                result['extraction'] = IsPartialDict(
                    decoded_stats=Contains(
                        IsPartialDict(
                            memory_stat=IsPartialDict(id=16),
                            roll_range=IsPartialDict(min=20, max=30),
                            roll_quality='perfect' if ed == 30 else 'low',
                        )
                    )
                )
            yield Case(
                id=f'magefist-remaining/{group}/{label}',
                item=candidate,
                context=loadout,
                covers=roles,
                scenario='unknown'
                if label == 'unread-fire-skill'
                else {'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                expected=result,
                absent_configurations=(configs[-1:] if upgrade_needed else ()) if truth == 'true' else configs,
                absent_stat_configurations=absent,
                report_contains=('Magefist', 'Trade tier:') if truth == 'true' else (),
                evidence=(
                    'third-parties/d2data/json/uniqueitems.json:/105',
                    *(
                        f'pricing/data/wp-a-builds.json:/fissure-druid/variants/{index}/player/Gloves/0'
                        if component
                        else f'pricing/data/wp-a-builds.json:/{guide}/slots/Gloves/{index}'
                        for guide, index in sources
                    ),
                ),
            )


CASES = tuple(cases())
