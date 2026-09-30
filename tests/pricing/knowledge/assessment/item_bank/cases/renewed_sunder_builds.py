"""Remaining Renewed Sunder uses: native core, distinct identity, no invented bonus bounds."""

from dataclasses import replace

from dirty_equals import Contains, IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.models import Case, Item


# Native IDs distinguish Renewed charms from their Grand Charm predecessors.
SPECS = (
    ('blizzard-sorceress', 'Sorceress', 'Cold Rupture', 427, 187, 43, -70, ('standard', 'magic-find')),
    ('double-throw-barbarian-guide', 'Barbarian', 'Bone Break', 436, 192, 36, -10, ('standard', 'magic-find')),
    ('dream-paladin', 'Paladin', 'Crack of the Heavens', 434, 190, 41, -70, ('standard', 'hybrid', 'ubers')),
    ('echoing-strike-warlock-guide', 'Warlock', 'Black Cleft', 437, 193, 37, -45, ('standard', 'magic-find', 'ubers')),
    ('echoing-strike-warlock-guide', 'Warlock', 'Bone Break', 436, 192, 36, -10, ('main-alternatives',)),
    ('enchant-sorceress', 'Sorceress', 'Flame Rift', 433, 189, 39, -70, ('standard',)),
    ('fire-blast-assassin', 'Assassin', 'Flame Rift', 433, 189, 39, -70, ('standard',)),
    (
        'lightning-fury-amazon-guide',
        'Amazon',
        'Crack of the Heavens',
        434,
        190,
        41,
        -70,
        ('main-alternatives', 'standard', 'magic-find', 'ubers'),
    ),
    (
        'nova-sorceress-guide',
        'Sorceress',
        'Crack of the Heavens',
        434,
        190,
        41,
        -70,
        ('main-alternatives', 'standard', 'magic-find', 'hydra-hybrid'),
    ),
)


def cases():
    for build, player_class, original, native, core, penalty, loss, variants in SPECS:
        name = 'Renewed ' + original
        slug = original.lower().replace(' ', '-')
        roles = tuple(f'{build}-renewed-{slug}-{variant}-renewed-sunder' for variant in variants)
        configs = tuple(role + '-stats' for role in roles)
        item = Item('Crafted Sunder Charm', 'unique', name, ((core, 0, 300), (penalty, 0, loss)), named_table_id=native)
        context = {'player_class': player_class}
        rows = (
            ('native-core', item, context, 'true'),
            ('core-one-low', replace(item, raw_stats=((core, 0, 299), (penalty, 0, loss))), context, 'unknown'),
            ('core-one-high', replace(item, raw_stats=((core, 0, 301), (penalty, 0, loss))), context, 'unknown'),
            ('unread-core', replace(item, raw_stats=((penalty, 0, loss),)), context, 'unknown'),
            ('missing-core', replace(item, raw_stats=((penalty, 0, loss),), complete=True), context, 'false'),
            ('wrong-class', item, {'player_class': 'Druid'}, 'false'),
            ('unknown-class', item, {}, 'unknown'),
            ('unknown-ethereal', replace(item, ethereal=None), context, 'unknown'),
            ('unidentified', replace(item, identified=False), context, 'false'),
            ('illegal-socket', replace(item, sockets=1), context, 'false'),
        )
        for label, candidate, loadout, truth in rows:
            expected = {
                'roles': Contains(*(IsPartialDict(id=role, rule_trace=IsPartialDict(truth=truth)) for role in roles))
            }
            if truth == 'true':
                expected['stat_evaluation'] = IsPartialDict(
                    annotations=IsPartialDict(
                        {
                            f'{core}:0': IsPartialDict(configuration_ids=Contains(*configs)),
                        }
                    )
                )
            yield Case(
                id=f'renewed-sunder-builds/{build}/{slug}/{label}',
                item=candidate,
                context=loadout,
                expected={'assessment': IsPartialDict(**expected), 'price_estimate': IsPartialDict(estimate_ist=None)},
                covers=roles,
                scenario={'true': 'positive', 'false': 'negative', 'unknown': 'unknown'}[truth],
                absent_configurations=() if truth == 'true' else configs,
                report_contains=(name,),
                evidence=('pricing/data/wp-a-builds.json', f'third-parties/d2data/json/uniqueitems.json:/{native}'),
            )
        yield Case(
            id=f'renewed-sunder-builds/{build}/{slug}/original-is-distinct',
            item=Item('Grand Charm', 'unique', original, ((core, 0, 300), (penalty, 0, loss))),
            context=context,
            expected={'price_estimate': IsPartialDict(estimate_ist=None)},
            covers=roles,
            scenario='negative',
            absent_configurations=configs,
            report_contains=(original,),
            report_absent=(name,),
            evidence=('pricing/data/wp-a-builds.json', f'third-parties/d2data/json/uniqueitems.json:/{native}'),
        )


CASES = tuple(cases())
