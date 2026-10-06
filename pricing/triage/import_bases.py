"""Transcribe clean WP-B bucket definitions; rebuild prices from scoped listings."""

import json
import re
from collections import Counter, defaultdict

from pricing.knowledge.refresh import atomic_json
from pricing.triage.build import ROOT


SOURCE = 'pricing/data/wp-b-prices.json'


def compile_bucket(name, key):
    parts = key.split('/')
    if len(parts) < 3 or not re.fullmatch(r'[0-6]os', parts[0]):
        return None
    sockets, ethereal, rarity, *suffixes = parts
    if ethereal not in ('eth', 'noneth') or rarity not in ('normal', 'superior'):
        return None
    if set(suffixes) - {'15ed', 'res45', 'res40-44', 'res<40', 'skill1', 'skill2', 'skill3'}:
        return None
    conditions = {
        'sockets': int(sockets[0]),
        'ethereal': ethereal == 'eth',
        'rarity': rarity,
        'empty_sockets': True,
        'base_ed': 15 if '15ed' in suffixes else {'min': 0, 'max': 14},
    }
    properties = {}
    for suffix in suffixes:
        if suffix.startswith('res'):
            properties['441'] = {'res45': 45, 'res40-44': {'min': 40, 'max': 44}, 'res<40': {'min': 0, 'max': 39}}[
                suffix
            ]
        elif suffix.startswith('skill'):
            properties['454'] = int(suffix[-1])
    return {
        'category': 'base',
        'name': name,
        'bucket': 'wp-b:' + key,
        'conditions': conditions,
        'properties': properties,
        'source': SOURCE + '#' + name + '/' + key,
    }


def staffmod_rules():
    """Guide §2/§7 Void bases; modifiers remain price facets, not pooled bonuses."""
    from inventory_tracking.items.metadata import metadata

    properties = json.loads((ROOT / 'pricing/data/appraisal-properties.json').read_text())['properties']
    skills = {s['name'] for s in metadata()['skills'].values()}
    class_labels = {name: {} for name in ('Warlock', 'Barbarian', 'Assassin', 'Sorceress', 'Necromancer', 'Druid')}
    for prop, entry in properties.items():
        for label in entry['labels']:
            match = re.fullmatch(
                r'\+\{\{value\}\} to (.+) \((Warlock|Barbarian|Assassin|Sorceress|Necromancer|Druid) Only\)', label
            )
            if match and match[1] in skills:
                class_labels[match[2]][prop] = match[1]
    labels = class_labels['Warlock']
    rows, policies = [], []
    utility = json.loads((ROOT / 'pricing/data/appraisal-utility.json').read_text())['rows']
    void_codes = {
        row['base_code']
        for row in utility
        if row.get('sockets') == 3
        and row.get('details', {}).get('runeword') == 'Void'
        and row['details'].get('legality') == 'verified_type_and_capacity'
    }
    for base in metadata()['bases'].values():
        if base['type'] != 'knif' or base['max_sockets'] < 3 or base['code'] not in void_codes:
            continue
        name = base['name']
        source = 'guides/pricing.html#s7'
        rows.append(
            {
                'category': 'base',
                'name': name,
                'bucket': 'void-three-socket',
                'conditions': {
                    'sockets': 3,
                    'empty_sockets': True,
                    'rarity': {'in': ['normal', 'superior']},
                    'base_ed': {'min': 0, 'max': 15},
                },
                'properties': {},
                'source': source,
                'imported_staffmod_base': True,
            }
        )
        policies.append(
            {
                'category': 'base',
                'name': name,
                'require_bucket': True,
                'facets': ['rarity', 'ethereal', 'sockets', 'socket_contents', 'base_ed_grade', 'base_modifiers'],
                'compare_staffmods': labels,
                'source': source,
                'imported_staffmod_base': True,
            }
        )
    paid = {
        p: label
        for p, label in labels.items()
        if label in {'Summon Tainted', 'Consume', 'Bind Demon', 'Sigil: Death', 'Summon Defiler', 'Apocalypse', 'Abyss'}
    }
    for base in metadata()['bases'].values():
        if base['type'] == 'grim':
            sockets, prefix, title = 2, 'grimoire', 'Two-socket grimoire with paid staffmod'
            skill_labels, paid_skills, source = labels, paid, 'pricing/raw/traderie/pull-20261003/'
        elif base['type'] == 'phlm':
            sockets, prefix, title = 3, 'bo-helm', 'Three-socket Barbarian helm with paid staffmod'
            skill_labels = class_labels['Barbarian']
            paid_skills = {p: label for p, label in skill_labels.items() if label in {'Battle Orders', 'Find Item'}}
            # Three priced independent sellers of +3 Find Item without +3 BO.
            source = 'pricing/raw/traderie/pull-20261003/'
        elif base['type'] == 'pelt':
            sockets, prefix, title = 3, 'druid-pelt', 'Three-socket Druid pelt with paid staffmod'
            skill_labels = class_labels['Druid']
            paid_skills = {
                p: label for p, label in skill_labels.items() if label in {'Tornado', 'Volcano', 'Armageddon'}
            }
            # Cached independent priced sellers: Tornado 10, Volcano 6, Armageddon 9.
            # Fire-skill cohorts remain after excluding +3 Tornado listings.
            source = 'pricing/raw/traderie/pull-20261003/'
        elif base['type'] == 'h2h2':
            sockets, prefix, title = 3, 'claw', 'Three-socket claw with paid staffmod'
            skill_labels = class_labels['Assassin']
            # 2026-10-03 scoped cached asks: 4-14 independent sellers per
            # full three-socket/+3 pattern. Other skills remain comparison
            # dimensions; a perfect unlisted skill is not a paid pattern.
            paid_skills = {
                p: label
                for p, label in skill_labels.items()
                if label in {'Lightning Sentry', 'Phoenix Strike', 'Blades of Ice', 'Claws of Thunder'}
            }
            source = 'pricing/raw/traderie/pull-20261003/'
        elif base['type'] in ('wand', 'staf'):
            # Scoped 2026-10-03 asks: 29 sellers for 2os/+3 Bone Spear;
            # 14 for 4os/+3 Energy Shield. Capacity checks exclude bases
            # that cannot take the White/Memory recipe's socket count.
            wand = base['type'] == 'wand'
            sockets = 2 if wand else 4
            prefix = 'white-wand' if wand else 'memory-staff'
            title = 'Two-socket Bone Spear wand' if wand else 'Four-socket Energy Shield staff'
            skill_labels = class_labels['Necromancer' if wand else 'Sorceress']
            paid_skills = {
                p: label for p, label in skill_labels.items() if label == ('Bone Spear' if wand else 'Energy Shield')
            }
            source = 'pricing/raw/traderie/pull-20261003/'
        else:
            continue
        if base['max_sockets'] < sockets:
            continue
        socket_counts = (4, 5) if base['type'] == 'staf' else (sockets,)
        for sockets in socket_counts:
            if base['max_sockets'] < sockets:
                continue
            if base['type'] == 'staf' and sockets == 5:
                # Utility definitions verify Call to Arms on five-socket staves;
                # ten priced sellers support +3 Energy Shield in this format.
                prefix, title = 'cta-staff', 'Five-socket Energy Shield staff'
            conditions = {'sockets': sockets, 'empty_sockets': True, 'rarity': {'in': ['normal', 'superior']}}
            for prop, label in paid_skills.items():
                rows.append(
                    {
                        'category': 'base',
                        'name': base['name'],
                        'bucket': f'{prefix}:{prop}',
                        'conditions': conditions | {'base_ed': {'min': 0, 'max': 15}},
                        'properties': {prop: 3},
                        'labels': {prop: label},
                        'pattern': {'conditions': conditions, 'properties': {prop: {'min': 1, 'max': 3}}},
                        'pattern_label': title,
                        'source': source,
                        'imported_staffmod_base': True,
                    }
                )
        policies.append(
            {
                'category': 'base',
                'name': base['name'],
                'require_bucket': True,
                'facets': ['rarity', 'ethereal', 'sockets', 'socket_contents', 'base_ed_grade', 'base_modifiers'],
                'compare_staffmods': skill_labels,
                'source': source,
                'imported_staffmod_base': True,
            }
        )
    # Cached unsocketed asks support BO, traps, ES, Abyss and Bone Spear.
    # 2026-10-03: two priced sellers each for +3 Abyss grimoires and +3 Bone Spear wands.
    # These are preparation candidates, not copies of the socketed price band.
    for row in list(rows):
        skill = next(iter(row.get('labels', {}).values()), None)
        if skill not in {'Battle Orders', 'Lightning Sentry', 'Energy Shield', 'Abyss', 'Bone Spear'}:
            continue
        count = row['conditions']['sockets']
        conditions = row['pattern']['conditions'] | {'sockets': 0}
        rows.append(
            {
                'category': 'base',
                'name': row['name'],
                'conditions': conditions,
                'properties': row['properties'],
                'pattern': {'conditions': conditions, 'properties': row['properties']},
                'pattern_label': f'Unsocketed +3 {skill} base; needs {count} sockets',
                'required_socket_counts': [count],
                'source': 'pricing/raw/traderie/pull-20261003/',
                'imported_staffmod_base': True,
            }
        )
    return rows, policies


# Generic starter bases are outside the player's current pickup scope. Premium
# rolls still need their own sourced pattern; a recipe alone is not a price.
STARTER_WORDS = {'Stealth', 'Smoke', 'Lore', "Ancient's Pledge", "Ancients' Pledge", 'Leaf', 'Strength'}


def build_demand(document, source):
    """Collect explicit player/mercenary equipment from every cached variant."""
    utility = json.loads((ROOT / 'pricing/data/appraisal-utility.json').read_text())['rows']
    recipes = {
        f'{r["details"]["runeword"]} {r["name"]}': (r['name'], r['details']['runeword'], r['sockets'])
        for r in utility
        if r.get('details', {}).get('legality') == 'verified_type_and_capacity'
        and r['details']['runeword'] not in STARTER_WORDS
    }
    demand = {}

    def visit(value, path=(), equipment=False):
        if isinstance(value, dict):
            variant = str(value.get('name', '')).casefold()
            if any(word in variant for word in ('starter', 'leveling', 'levelling')):
                return
            for key, child in value.items():
                visit(child, (*path, str(key)), equipment or key in ('player', 'mercenary', 'merc'))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, (*path, str(index)), equipment)
        elif equipment and isinstance(value, str) and (recipe := recipes.get(value.split(' (', 1)[0])):
            name, word, sockets = recipe
            entry = demand.setdefault(name, {'sockets_by_runeword': {}, 'source': source + '#' + '/'.join(path)})
            entry['sockets_by_runeword'][word] = sockets

    visit(document)
    return demand


def demand_rules(demand, existing):
    """Fill missing families from documented build/merc base recommendations."""
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.listing_defaults import BASE_ALIASES

    bases = {b['name']: b for b in metadata()['bases'].values()}
    utility = json.loads((ROOT / 'pricing/data/appraisal-utility.json').read_text())['rows']
    legal = {
        (r['base_code'], r['sockets'], r['details']['runeword'])
        for r in utility
        if r.get('details', {}).get('legality') == 'verified_type_and_capacity'
    }

    def compatible(code, sockets, word):
        candidates = (word, 'Hustle (weapon)', 'Hustle (armor)') if word == 'Hustle' else (word,)
        return any((code, sockets, name) in legal for name in candidates)

    rows, policies = [], []
    for market_name, entry in demand.items():
        name = BASE_ALIASES.get(market_name, market_name)
        if name not in bases:
            continue
        recipes = {
            word: count
            for word, count in entry.get('sockets_by_runeword', {}).items()
            if word not in STARTER_WORDS
            and type(count) is int
            and count not in existing.get(name, set())
            and 1 <= count <= bases[name]['max_sockets']
            and compatible(bases[name]['code'], count, word)
        }
        if not recipes:
            continue
        source = entry.get('source') or 'pricing/data/wp-a-bases.json#' + market_name
        for count in sorted(set(recipes.values())):
            rows.append(
                {
                    'category': 'base',
                    'name': name,
                    'bucket': f'demand:{count}os',
                    'conditions': {
                        'sockets': count,
                        'empty_sockets': True,
                        'rarity': {'in': ['normal', 'superior']},
                        'base_ed': {'min': 0, 'max': 15},
                    },
                    'properties': {},
                    'source': source,
                    'imported_demand_base': True,
                    'runewords': sorted(word for word, sockets in recipes.items() if sockets == count),
                }
            )
        policies.append(
            {
                'category': 'base',
                'name': name,
                'require_bucket': True,
                'facets': ['rarity', 'ethereal', 'sockets', 'socket_contents', 'base_ed_grade', 'base_modifiers'],
                'source': source,
                'imported_demand_base': True,
            }
        )
    return rows, policies


def native_shield_rules():
    """Top damage/AR automod on elite Paladin bases, supported by cached asks."""
    from inventory_tracking.items.metadata import metadata

    # d2data automagic.json, Knight's: 51-65 damage and 101-121 AR.
    # WP-G records this alternative to resistance; scoped 2026-10-03 asks
    # establish paid copies on Sacred Targe/Rondache. Prices stay base-specific.
    source = 'pricing/raw/traderie/pull-20261003/'
    names = {'Sacred Targe', 'Sacred Rondache'}
    rows, policies = [], []
    for base in metadata()['bases'].values():
        if base['name'] not in names:
            continue
        rows.append(
            {
                'category': 'base',
                'name': base['name'],
                'bucket': 'native-damage-shield',
                'conditions': {
                    'sockets': {'in': [0, 3, 4]},
                    'empty_sockets': True,
                    'rarity': {'in': ['normal', 'superior']},
                    'base_ed': {'min': 0, 'max': 15},
                },
                'properties': {'510': {'min': 51, 'max': 65}, '423': {'min': 101, 'max': 121}},
                'source': source,
                'imported_native_base': True,
            }
        )
        policies.append(
            {
                'category': 'base',
                'name': base['name'],
                'require_bucket': True,
                'facets': ['rarity', 'ethereal', 'sockets', 'socket_contents', 'base_ed_grade', 'base_modifiers'],
                'compare_inherent': {
                    '510': {'min': 51, 'max': 65, 'label': '% native enhanced damage'},
                    '423': {'min': 101, 'max': 121, 'label': 'native attack rating'},
                },
                'source': source,
                'imported_native_base': True,
            }
        )
    return rows, policies


def guide_base_patterns():
    """Keep explicit guide variants reviewable when their price cohort is absent.

    These rows carry no price bucket: they cannot borrow the normal or perfect
    superior band. Historical floor rows do not establish paid patterns.
    """
    from pricing.triage.guide_cases import base_table_examples, extract, item_from_spec

    source = 'guides/pindle-anya.html'
    rows = []
    for case in extract((ROOT / source).read_text(), source):
        examples = base_table_examples(case)
        if not examples:
            continue
        groups = defaultdict(list)
        for example in examples:
            item = item_from_spec(example['spec'])
            # Only ED endpoints of the same quality/socket/ethereal/modifier variant
            # may form a range. Never copy the first variant's selectors to the others.
            properties = {key: value for key, value in item['properties'].items() if key not in {'425', '510'}}
            key = item['rarity'], item['ethereal'], item['sockets'], json.dumps(properties, sort_keys=True)
            groups[key].append(item)
        for items in groups.values():
            item = items[0]
            eds = [entry['base_ed'] for entry in items]
            conditions = {
                'rarity': item['rarity'],
                'ethereal': item['ethereal'],
                'sockets': item['sockets'],
                'empty_sockets': True,
                'base_ed': {'min': min(eds), 'max': max(eds)},
            }
            properties = {key: value for key, value in item['properties'].items() if key not in {'425', '510'}}
            rows.append(
                {
                    'category': 'base',
                    'name': item['name'],
                    'conditions': conditions,
                    'properties': properties,
                    'pattern': {'conditions': conditions, 'properties': properties},
                    'pattern_label': 'Guide-listed runeword base',
                    'source': case['id'],
                    'imported_guide_base': True,
                }
            )
            if item['rarity'] == 'normal' and item['sockets'] > 0:
                # §9 says sub-perfect superior ED is a plain base, not a premium.
                # Retain its paid pattern, but do not copy the plain base's price.
                # Unsocketed bases are excluded: superior cannot use the cube recipe.
                superior = conditions | {'rarity': 'superior', 'base_ed': {'min': 0, 'max': 14}}
                rows.append(
                    rows[-1]
                    | {
                        'conditions': superior,
                        'pattern': {'conditions': superior, 'properties': properties},
                        'sources': [case['id'], 'guides/pricing.html#s9'],
                    }
                )
    # §5's mixed "40-44 sell / <40 floor" row is not a single-variant
    # auto-transcription. Import only its explicit paid pattern; floor is not
    # an instruction to copy a premium band or discard every lower roll.
    conditions = {'rarity': {'in': ['normal', 'superior']}, 'ethereal': False, 'sockets': 3, 'empty_sockets': True}
    properties = {'441': {'min': 40, 'max': 44}}
    rows.append(
        {
            'category': 'base',
            'name': 'Sacred Targe',
            'conditions': conditions,
            'properties': properties,
            'pattern': {'conditions': conditions, 'properties': properties},
            'pattern_label': 'Three-socket Sacred Targe with 40-44 all resistance',
            'source': 'guides/pindle-anya.html#s5:34',
            'imported_guide_base': True,
        }
    )
    return rows


def main():
    source = json.loads((ROOT / SOURCE).read_text())
    path = ROOT / 'pricing/data/triage/rules.json'
    document = json.loads(path.read_text())
    rows, skipped = [], Counter()
    for entry in source.values():
        if not isinstance(entry, dict) or 'buckets' not in entry:
            continue
        for key in entry['buckets']:
            rule = compile_bucket(entry['name'], key)
            if rule:
                rows.append(rule)
            else:
                skipped[key] += 1
    staffmods, policies = staffmod_rules()
    native_rows, native_policies = native_shield_rules()
    demand = json.loads((ROOT / 'pricing/data/wp-a-bases.json').read_text())
    covered = defaultdict(set)
    for rule in rows + staffmods:
        if type(count := rule.get('conditions', {}).get('sockets')) is int:
            covered[rule['name']].add(count)
    extra, extra_policies = demand_rules(demand, covered)
    for rule in extra:
        covered[rule['name']].add(rule['conditions']['sockets'])
    paths = [ROOT / 'pricing/data/wp-a-builds.json', *sorted((ROOT / 'pricing/data/wp-a-variants').glob('*.json'))]
    for build_path in paths:
        build_rows, build_policies = demand_rules(
            build_demand(json.loads(build_path.read_text()), str(build_path.relative_to(ROOT))), covered
        )
        extra.extend(build_rows)
        extra_policies.extend(build_policies)
        for rule in build_rows:
            covered[rule['name']].add(rule['conditions']['sockets'])
    staffmods += extra + native_rows
    # Native comparison policy must win over an existing demand-only policy.
    policies = native_policies + [
        p for p in policies + extra_policies if p.get('name') not in {n['name'] for n in native_policies}
    ]
    document['rows'] = (
        [
            r
            for r in document['rows']
            if not r.get('imported_market_base')
            and not r.get('imported_guide_base')
            and not r.get('imported_native_base')
            and not r.get('imported_demand_base')
            and not r.get('imported_staffmod_base')
            and not (isinstance(r.get('source'), str) and r['source'].startswith(SOURCE + '#'))
        ]
        + rows
        + staffmods
    )
    document['policies'] = [
        p
        for p in document['policies']
        if not p.get('imported_native_base')
        and not p.get('imported_staffmod_base')
        and not p.get('imported_demand_base')
    ] + policies
    policy = next(p for p in document['policies'] if p.get('category') == 'base' and 'name' not in p)
    policy['require_bucket'] = True
    policy['facets'] = ['rarity', 'ethereal', 'sockets', 'socket_contents', 'base_ed_grade', 'base_modifiers']
    for base_policy in document['policies']:
        if base_policy.get('category') == 'base':
            # qualityitems.json: superior attack rating 1-3 and durability 10-15.
            base_policy['compare_modifiers'] = {
                '423': {'min': 1, 'max': 3, 'label': 'attack rating'},
                '937': {'min': 10, 'max': 15, 'label': '% maximum durability'},
            }
    from pricing.triage.build import market_rows
    from pricing.triage.market_bases import compile_market_bases

    utility = json.loads((ROOT / 'pricing/data/appraisal-utility.json').read_text())['rows']
    observations, _ = market_rows()
    market_rules = compile_market_bases(
        observations,
        document['rows'],
        document['policies'],
        utility,
        keep_ist=document['keep_ist'],
        excluded_words=STARTER_WORDS,
    )
    document['rows'].extend(market_rules)
    document['rows'].extend(guide_base_patterns())
    names = {r['name'] for r in document['rows'] if r.get('category') == 'base' and r.get('name')}
    document['socket_caps'] = {
        r['name']: r['details']['larzuk_unknown_ilvl']['maximum_by_ilvl_bracket']
        for r in utility
        if r.get('name') in names and r.get('details', {}).get('rule') == 'socket_potential'
    }
    atomic_json(path, document)
    print(
        json.dumps(
            {
                'rules': len(rows) + len(staffmods) + len(market_rules),
                'market_variants': len(market_rules),
                'bases': len({r['name'] for r in rows + staffmods + market_rules}),
                'skipped_buckets': sum(skipped.values()),
                'historical_prices_imported': False,
            }
        )
    )


if __name__ == '__main__':
    main()
