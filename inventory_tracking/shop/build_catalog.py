"""Audit all local build lists and compile magic shopping candidates offline."""

import hashlib
import itertools
import json
import re
from collections import defaultdict
from pathlib import Path

from inventory_tracking.reports import publish


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name('magic_targets.json')
ALIASES = {
    'Gloves': 'glov',
    'Boots': 'boot',
    'Belt': 'belt',
    'Staff': 'staf',
    'Wand': 'wand',
    'Scepter': 'scep',
    'Javelin': 'jave',
    'Elite Throwing Weapon': 'throwing',
}
AFFIX_ALIASES = {
    "Artisan's": "Artificer's",
    'Gaean': "Gaea's",
    'Natural': "Nature's",
    'of Sustenance': 'of Substinence',
    'of the Colossus': 'of the Colosuss',
    'Vermilion': 'Vermillion',
}


def load(path):
    return json.loads((ROOT / path).read_text())


def walk(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + '/' + str(key).replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk(child, path + '/' + str(i))
    elif isinstance(value, str):
        yield path, value


def stat(key, value):
    return {'op': 'stat_at_least', 'key': key if ':' in key else key + ':0', 'value': value}


def item_predicate(node):
    """Class/loadout prerequisites are retained as caveats, not shopping gates.

    Only conjunctive context may be removed: doing this inside OR/NOT could
    silently turn an unrelated item into a match.
    """
    if 'all' in node:
        return {'all': [item_predicate(n) for n in node['all'] if not n.get('op', '').startswith('context_')]}
    if 'any' in node or 'not' in node:
        if any('context_' in str(n) for n in node.values()):
            raise ValueError('Context in alternative/negated shopping predicate')
        return node
    if node.get('op', '').startswith('context_'):
        raise ValueError('Context-only shopping target')
    return node


def supplemental_targets(builds):
    """Reviewed generic setup labels: candidate floors, not whole-build readiness.

    Named affixes below use native tier minima; generic starter items use the
    concrete stat families in the variant equipment rows. No fabricated prices.
    """
    targets = []

    def add(identity, kinds, nodes, description):
        targets.append(
            {
                'id': 'generic:' + identity,
                'types': kinds,
                'must': {'all': nodes},
                'label': description,
                'builds': sorted(builds),
                'sources': ['pricing/data/wp-a-blues.json', 'pricing/data/wp-a-variants/'],
                'conditions': ['Build-list candidate; verify requirements and the full setup.'],
            }
        )

    def resistance(minimum):
        return {'any': [stat(str(s), minimum) for s in (39, 41, 43, 45)]}

    def all_res(minimum):
        return {'all': [stat(str(s), minimum) for s in (39, 41, 43, 45)]}

    add('mf-res-gloves', ['glov'], [stat('80', 16), resistance(21)], 'Starter: resistance + magic-find gloves')
    add('ias-res-gloves', ['glov'], [stat('93', 20), resistance(21)], 'Starter: 20 IAS + resistance gloves')
    add('life-res-belt', ['belt'], [stat('7', 41), resistance(21)], 'Starter: life + resistance belt')
    add('fhr-res-belt', ['belt'], [stat('99', 24), resistance(21)], 'Starter: 24 FHR + resistance belt')
    add('frw-boots', ['boot'], [stat('96', 20)], 'Starter: 20+ FRW boots')
    add(
        'fcr-res-ring',
        ['ring'],
        [stat('105', 10), {'any': [all_res(5), resistance(20)]}],
        'Starter: 10 FCR + resistance ring',
    )
    add('res-ring', ['ring'], [resistance(20)], 'Starter: 20+ resistance ring')
    add('mf-ring', ['ring'], [stat('80', 27)], 'Build target: 27+ MF ring (two MF affixes)')
    add('warcries-gold-amulet', ['amul'], [stat('188:34', 1), stat('79', 41)], 'Gold Find: Warcries + gold-find amulet')
    add('traps-mf-amulet', ['amul'], [stat('188:48', 1), stat('80', 16)], 'Starter: Traps + magic-find amulet')
    add('warlock-life-amulet', ['amul'], [stat('83:7', 1), stat('7', 20)], 'Starter: Warlock skills + life amulet')
    add(
        'assassin-frw-circlet',
        ['circ'],
        [stat('83:6', 2), stat('96', 30)],
        'Build target: +2 Assassin / 30 FRW circlet',
    )
    add('grimoire-res', ['grim'], [all_res(1)], 'Starter: all-resistance Grimoire')
    add('jewel-ias', ['jewl'], [stat('93', 15)], 'Socket component: 15 IAS jewel')
    add('jewel-gold', ['jewl'], [stat('79', 21)], 'Socket component: gold-find jewel')
    add('jewel-fhr-res', ['jewl'], [stat('99', 7), all_res(11)], 'Socket component: 7 FHR + all-resistance jewel')
    add(
        'magic-find-monarch',
        ['shie'],
        [
            {
                'op': 'fact_eq',
                'field': 'base_code',
                'value': next(
                    b['code']
                    for b in load('inventory_tracking/items/data/item_metadata.json')['bases'].values()
                    if b['name'] == 'Monarch'
                ),
            },
            stat('194', 4),
            {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
        ],
        'Socket base: four-socket magic Monarch for Ist runes',
    )
    # Every build's skill charms, including Warlock and the Necromancer summoner,
    # are represented even where the older curated profile subset omits them.
    add(
        'skill-grand-charm',
        ['lcha'],
        [{'any': [stat(f'188:{c * 8 + t}', 1) for c in range(8) for t in range(3)]}],
        'Build candidate: skill-tree Grand Charm',
    )
    for kind, life, single, all_min, gold, fhr, frw, mf in (
        ('lcha', 20, 15, 10, 30, 12, 7, 0),
        ('mcha', 26, 8, 6, 0, 0, 0, 0),
        ('scha', 11, 8, 3, 8, 5, 3, 5),
    ):
        for key, minimum, label in (
            ('7', life, 'life'),
            ('79', gold, 'gold find'),
            ('99', fhr, 'FHR'),
            ('96', frw, 'FRW'),
            ('80', mf, 'magic find'),
        ):
            if minimum:
                add(kind + '-' + key, [kind], [stat(key, minimum)], f'Charm candidate: {minimum}+ {label}')
        add(kind + '-res', [kind], [{'any': [resistance(single), all_res(all_min)]}], 'Charm candidate: resistances')
    return targets


def generic_evidence(identity, text):
    """Keep generic-rule provenance specific to the item's stated stat families."""
    text = text.lower()
    groups: dict[str, list[tuple[str, ...]]] = {
        'mf-res-gloves': [('gloves',), ('mf', 'fortune'), ('res', 'garnet')],
        'ias-res-gloves': [('gloves',), ('ias', 'alacrity'), ('res', 'cobalt', 'coral')],
        'life-res-belt': [('belt', 'sash'), ('life', 'whale', 'squid'), ('res', 'garnet', 'cobalt', 'coral')],
        'fhr-res-belt': [('belt', 'sash'), ('fhr',), ('res',)],
        'frw-boots': [('boots',), ('frw', 'speed', 'acceleration')],
        'fcr-res-ring': [('ring',), ('fcr',), ('res',)],
        'res-ring': [('ring',), ('res',)],
        'mf-ring': [('ring',), ('mf', 'fortune')],
        'warcries-gold-amulet': [('amulet',), ('warcries',), ('gold',)],
        'traps-mf-amulet': [('amulet',), ('traps',), ('mf',)],
        'warlock-life-amulet': [('amulet',), ('warlock',), ('life',)],
        'assassin-frw-circlet': [('circlet', 'diadem'), ('assassin',), ('frw',)],
        'grimoire-res': [('grimoire',), ('resistance',)],
        'jewel-ias': [('jewel',), ('ias', 'fervor', 'increased attack speed')],
        'jewel-gold': [('jewel',), ('gold',)],
        'jewel-fhr-res': [('jewel',), ('fhr',), ('all res',)],
        'magic-find-monarch': [('monarch',), ('ist', 'magic find')],
        'skill-grand-charm': [
            ('grand charm',),
            (
                'skills',
                'levels',
                'sparking',
                'burning',
                'chilling',
                'natural',
                'harpoonist',
                'fungal',
                'entrapping',
                'graverobber',
                'lion branded',
            ),
        ],
    }
    if identity not in groups:
        kind, stat_id = identity.split('-')
        kind_name = {'lcha': 'grand charm', 'mcha': 'large charm', 'scha': 'small charm'}[kind]
        terms = {
            '7': ('life', 'vita', 'sustenance'),
            '79': ('gold',),
            '99': ('fhr', 'balance'),
            '96': ('frw', 'inertia'),
            '80': ('mf', 'good luck', 'magic find'),
            'res': ('res', 'shimmering', 'ruby', 'amber', 'sapphire', 'emerald', 'coral', 'garnet', 'jade'),
        }
        groups[identity] = [(kind_name,), terms[stat_id]]
    return all(any(term in text for term in alternatives) for alternatives in groups[identity])


class Compiler:
    def __init__(self):
        self.meta = load('inventory_tracking/items/data/item_metadata.json')
        self.bases = {b['name']: b for b in self.meta['bases'].values()}
        self.bases['Kris'] = self.bases['Kriss']
        self.raw = {
            r['code']: r
            for table in ('armor', 'weapons', 'misc')
            for r in load(f'third-parties/d2data/json/{table}.json').values()
            if r.get('code')
        }
        self.affixes: dict[str, defaultdict[str, list[dict]]] = {
            table: defaultdict(list) for table in ('prefix', 'suffix')
        }
        for table in self.affixes:
            for row in self.meta['affixes'][table].values():
                game = row['game_definition']
                if row.get('spawnable') and game.get('version') != 0 and game.get('frequency', 0) > 0:
                    self.affixes[table][row['name']].append(row)
        self.properties = load('third-parties/d2data/json/properties.json')
        for old, native in AFFIX_ALIASES.items():
            for table in self.affixes.values():
                if native in table:
                    table[old] = table[native]

    def split_name(self, name):
        # Bone Wand is a base, not the jewel-only Bone prefix plus a wand.
        for base in sorted(set(self.bases) | set(ALIASES), key=len, reverse=True):
            if name == base:
                return None, base, None
            if name.startswith(base + ' ') and name[len(base) + 1 :] in self.affixes['suffix']:
                return None, base, name[len(base) + 1 :]
        prefix = next(
            (p for p in sorted(self.affixes['prefix'], key=len, reverse=True) if name.startswith(p + ' ')), None
        )
        tail = name[len(prefix) + 1 :] if prefix else name
        suffix = next(
            (s for s in sorted(self.affixes['suffix'], key=len, reverse=True) if tail.endswith(' ' + s)), None
        )
        base = tail[: -len(suffix) - 1] if suffix else tail
        return prefix, base, suffix

    def base_codes(self, name):
        if name == 'Elite Throwing Weapon':
            return {
                b['code']
                for b in self.bases.values()
                if b['type'] in ('jave', 'taxe', 'tkni') and self.raw[b['code']].get('ultracode') == b['code']
            }
        if name in ALIASES:
            return {b['code'] for b in self.bases.values() if b['type'] == ALIASES[name]}
        if name in self.bases:
            base = self.bases[name]
            if name == 'Monarch':
                return {base['code']}
            return {b['code'] for b in self.bases.values() if b['type'] == base['type']}
        return set()

    def affix_values(self, row, code):
        values = {k if ':' in k else k + ':0': v['min'] for k, v in row['roll_ranges'].items()}
        charges = []
        game = row['game_definition']
        for i in range(1, 4):
            prop = game.get(f'mod{i}code')
            if not prop:
                continue
            definition = self.properties[prop]
            if definition.get('func1') == 21:
                values[f'83:{definition["val1"]}'] = game[f'mod{i}min']
            elif prop == 'sock':
                values['194:0'] = min(game[f'mod{i}param'], self.raw[code].get('gemsockets', 0))
            elif prop == 'charged':
                charges.append({'op': 'charge_skill', 'skill_id': game[f'mod{i}param'], 'value': 0})
            elif prop in ('dmg-min', 'dmg-max'):
                values['21:0' if prop == 'dmg-min' else '22:0'] = game[f'mod{i}min']
        if not values and not charges:
            raise ValueError(f'Uncompiled affix: {row["name"]}')
        return values, charges

    def named(self, name):
        prefix, base, suffix = self.split_name(name)
        codes = self.base_codes(base)
        if not codes or not (prefix or suffix):
            return []
        grouped = {}
        for left, right in itertools.product(
            self.affixes['prefix'][prefix] if prefix else [None], self.affixes['suffix'][suffix] if suffix else [None]
        ):
            rows = [r for r in (left, right) if r]
            allowed = codes.intersection(*(set(r['base_codes']) for r in rows))
            for code in sorted(allowed):
                # Keep the cited socket count even when extending a combination
                # to other bases of the same type (a Circlet cannot hold three).
                socket_rows = [r for r in rows if r['game_definition'].get('mod1code') == 'sock']
                if base in self.bases and socket_rows:
                    requested = min(
                        socket_rows[0]['game_definition']['mod1param'],
                        self.raw[self.bases[base]['code']].get('gemsockets', 0),
                    )
                    if self.raw[code].get('gemsockets', 0) < requested:
                        continue
                values, charges = {}, []
                for row in rows:
                    additions, extra = self.affix_values(row, code)
                    for key, value in additions.items():
                        values[key] = values.get(key, 0) + value
                    charges.extend(extra)
                # Amazon javelins add at least one inherent tree rank to Lancer's
                # +3 prefix (also required by the reviewed Fury starter profile).
                if self.raw[code].get('type') == 'ajav' and values.get('188:2') == 3:
                    values['188:2'] = 4
                nodes = [stat(k, v) for k, v in sorted(values.items())] + charges
                signature = json.dumps(nodes, sort_keys=True)
                group = grouped.setdefault(signature, {'base_codes': [], 'must': {'all': nodes}})
                group['base_codes'].append(code)
        return list(grouped.values())


def profile_target(profile):
    """Retain actionable requirements separately from non-blocking advice."""
    return {
        'id': 'profile:' + profile['id'],
        'types': profile['types'],
        'label': f'Build candidate: {profile["build"]} / {profile["variant"]} / {profile["role"]}',
        'must': item_predicate(profile['must']),
        'builds': [profile['build']],
        'conditions': profile.get('conditions', []),
        **({'advisory_conditions': profile['advisory_conditions']} if profile.get('advisory_conditions') else {}),
        'setup_requirements': {key: profile[key] for key in ('depends_on', 'required_socket_item') if key in profile}
        | {'original_predicate': profile['must']},
        'source': profile['source'],
    }


def build():
    sources = [
        'pricing/data/wp-a-builds.json',
        'pricing/data/wp-a-blues.json',
        'pricing/data/appraisal-build-profiles.json',
        'inventory_tracking/items/data/item_metadata.json',
        'third-parties/d2data/json/properties.json',
        *[f'third-parties/d2data/json/{t}.json' for t in ('armor', 'weapons', 'misc')],
    ]
    variant_paths = sorted((ROOT / 'pricing/data/wp-a-variants').glob('*.json'))
    fingerprints = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        for p in [*sources, *(p.relative_to(ROOT).as_posix() for p in variant_paths)]
    }
    compiler = Compiler()
    builds = load('pricing/data/wp-a-builds.json')
    blues = load('pricing/data/wp-a-blues.json')
    profiles = load('pricing/data/appraisal-build-profiles.json')['profiles']
    targets, audit, inventory = [], [], []
    for profile in profiles:
        if profile.get('scope', 'softcore') != 'softcore' or profile.get('season', 'non_ladder') != 'non_ladder':
            continue
        if 'magic' not in profile.get('qualities', []):
            continue
        targets.append(profile_target(profile))
    targets.extend(supplemental_targets(builds))
    candidates = {
        name: {'builds': row['builds'], 'sources': ['pricing/data/wp-a-blues.json/' + name]}
        for name, row in blues.items()
        if not any(t in name for t in ('Rare ', 'Crafted '))
    }
    for slug, doc in builds.items():
        for pointer, text in walk(doc.get('slots', {}), '/' + slug + '/slots'):
            inventory.append({'build': slug, 'source': 'pricing/data/wp-a-builds.json#' + pointer, 'text': text})
    for path in variant_paths:
        doc = json.loads(path.read_text())
        if 'variants' not in doc:
            continue
        slug = doc.get('slug', path.stem)
        if builds[slug].get('variants') != doc['variants']:
            raise ValueError(f'Build/variant lists disagree: {slug}; review before compiling')
        relative = path.relative_to(ROOT).as_posix()
        sources.append(relative)
        for pointer, text in walk(doc):
            # Record the entire equipment inventory, including named/nonmagic items,
            # so coverage isn't silently restricted to already-recognized targets.
            if not (
                any('/' + side + '/' in pointer for side in ('player', 'merc'))
                or pointer.startswith(('/prose_only_items/', '/planner_only_items/'))
            ):
                continue
            inventory.append(
                {
                    'build': slug,
                    'source': relative + '#' + pointer,
                    'text': text,
                    'planner_only': pointer.startswith('/planner_only_items/'),
                }
            )
    for entry_row in inventory:
        text = entry_row['text'].replace('Jewels', 'Jewel').replace('Charms', 'Charm')
        # Named affixes anywhere in a setup/alternative are separate candidates.
        for prefix in compiler.affixes['prefix']:
            if prefix + ' ' not in text:
                continue
            for base in sorted(set(compiler.bases) | set(ALIASES), key=len, reverse=True):
                stem = prefix + ' ' + base
                if not re.search(re.escape(stem) + r'(?![\w])', text):
                    continue
                suffix = next(
                    (s for s in sorted(compiler.affixes['suffix'], key=len, reverse=True) if stem + ' ' + s in text),
                    None,
                )
                name = stem + (' ' + suffix if suffix else '')
                # Rare names such as "Cruel Greaves" and normal "Sacred Targe"
                # must not become magic affix targets through substring matches.
                if name not in candidates and not compiler.named(name):
                    continue
                entry = candidates.setdefault(name, {'builds': [], 'sources': []})
                entry['builds'].append(entry_row['build'])
                entry['sources'].append(entry_row['source'])
    by_code = {b['code']: b for b in compiler.bases.values()}
    for name, evidence in sorted(candidates.items()):
        evidence = {k: sorted(set(v)) for k, v in evidence.items()}
        compiled = compiler.named(name)
        ids = []
        for i, rule in enumerate(compiled):
            identity = 'named:' + name + ':' + str(i)
            ids.append(identity)
            targets.append(
                {
                    'id': identity,
                    'label': 'Build target: ' + name,
                    'types': sorted({by_code[c]['type'] for c in rule['base_codes']}),
                    **rule,
                    **evidence,
                }
            )
        status = 'compiled_affixes'
        if not ids:
            generic_types = {
                'Grand Charm': ['lcha'],
                'Large Charm': ['mcha'],
                'Small Charm': ['scha'],
                'Resistance Grand Charm': ['lcha'],
                'Resistance Small Charm': ['scha'],
                'Magic Amulet': ['amul'],
                'Magic Belt': ['belt'],
                'Magic Boots': ['boot'],
                'Magic Gloves': ['glov'],
                'Magic Ring': ['ring'],
                'Magic Diadem': ['circ'],
            }
            charge_alias = {
                'Lower Resist Charge Wand': 'Wand of Lower Resistance',
                'Teleport Charge Staff': 'Staff of Teleportation',
                'Teleport Charge Amulet': 'Amulet of Teleportation',
            }
            if name in charge_alias:
                ids = [t['id'] for t in targets if t['id'].startswith('named:' + charge_alias[name] + ':')]
                status = 'charge_alias'
            elif name in generic_types:
                ids = [
                    t['id']
                    for t in targets
                    if t['id'].startswith(('profile:', 'generic:')) and set(t['types']) & set(generic_types[name])
                ]
                status = 'reviewed_generic_combinations'
            if not ids:
                status = 'needs_review'
        audit.append({'name': name, **evidence, 'targets': ids, 'status': status})
    for row in audit:
        if row['name'] == 'Lower Resist Charge Wand':
            row['targets'] = [t['id'] for t in targets if t['id'].startswith('named:Wand of Lower Resistance:')]
            row['status'] = 'charge_alias' if row['targets'] else 'needs_review'
    # Keep the initial broad inventory as an auditable census. A mention of a
    # unique/rare item with a magic socket component can reference both categories.
    for row in inventory:
        text = row['text'].replace('Jewels', 'Jewel').replace('Charms', 'Charm')
        references = [a for a in audit if a['name'] in text]
        row['targets'] = sorted({target for a in references for target in a['targets']})
        row['status'] = 'catalog_reference' if references else 'other_equipment_or_prose'
        if not row['targets'] and ('Magic ' in text or 'magic ' in text):
            kinds = {b['type'] for name, b in compiler.bases.items() if name in text}
            if 'Magic Grimoire' in text:
                kinds.add('grim')
            row['targets'] = sorted(
                t['id']
                for t in targets
                if kinds.intersection(t['types'])
                and (t['id'].startswith('generic:') or row['build'] in t.get('builds', []))
            )
            if row['targets']:
                row['status'] = 'generic_setup_candidates'
        if 'Jewel' in text and not ('Colossal' in text or 'Rainbow Facet' in text or 'rare Jewel' in text):
            components = []
            if 'IAS' in text or 'Increased Attack Speed' in text or 'of Fervor' in text:
                components.append('generic:jewel-ias')
            if 'FHR' in text and ('All Res' in text or 'All Resist' in text):
                components.append('generic:jewel-fhr-res')
            if 'Extra Gold' in text:
                components.append('generic:jewel-gold')
            if components:
                row['targets'] = sorted(set(row['targets']) | set(components))
                row['status'] = 'magic_socket_component'
        if any(
            s in text
            for s in (
                '30% ED / 60 AR / 7% FHR / 9 Str',
                '30% ED / 60 AR / 9 Str / 9 Dex',
                'Magic Heavy Gloves +Attack Rating / +Dexterity / Resistances',
                'Magic Ring of the Apprentice (10 FCR / AR / ML / Life / Mana / All Res)',
                'Magic Ring of the Apprentice (10 FCR / 6 ML',
                'Magic Amulet (+1 Traps / +20 All Res / 25 MF)',
                'Magic Ring (+30 Cold Res / MF / +1 Mana after kill)',
                'Magic Diadem (+2 Assassin Skills / 30 FRW / +30 Str / +20 All Res / Telekinesis charges',
                'Forbidden Diadem of the Magus (+2 Warlock Skills / 20 FCR / 30 FRW',
            )
        ):
            row.update(
                status='source_quality_conflict',
                targets=[],
                note='The described modifier bundle exceeds a magic prefix/suffix pair. '
                'Do not manufacture a magic target from a rare/planner label.',
            )
        if not row['targets'] and ('sunder' in text.lower() or 'Sunder' in text):
            row.update(status='nonmagic_sunder', note='Magic describes the damage element, not item quality.')
    for target in targets:
        if target['id'].startswith('generic:'):
            evidence = [r for r in inventory if generic_evidence(target['id'].removeprefix('generic:'), r['text'])]
            target['builds'] = sorted({r['build'] for r in evidence})
            target['sources'] = sorted({r['source'] for r in evidence})
            if any(r['status'] == 'source_quality_conflict' for r in evidence):
                target['conditions'].append(
                    'Some planner labels have conflicting quality; this rule only '
                    'uses the explicitly reviewed, legal magic subcombination, '
                    "not the planner's entire modifier bundle."
                )
            if not evidence:
                raise ValueError(f'Generic candidate lacks source evidence: {target["id"]}')
    if any(r['status'] == 'needs_review' for r in audit):
        raise ValueError('Unreviewed named magic items remain')
    for path in sources:
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != fingerprints[path]:
            raise ValueError(f'Input changed during compilation: {path}; retry')
    return {
        'schema_version': 1,
        'as_of': '2026-09-26',
        'sources': {p: fingerprints[p] for p in sources},
        'builds': sorted(builds),
        'targets': targets,
        'named_audit': audit,
        'equipment_inventory': inventory,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify the generated catalog without writing')
    args = parser.parse_args()
    result = build()
    if args.check:
        if json.loads(OUTPUT.read_text()) != result:
            raise ValueError('Shop catalog is stale; rebuild it')
    else:
        publish(OUTPUT, result)
        OUTPUT.with_name('MAGIC_COVERAGE.md').write_text(coverage_markdown(result))
    print(
        json.dumps(
            {
                'builds': len(result['builds']),
                'targets': len(result['targets']),
                'equipment_entries': len(result['equipment_inventory']),
                'needs_review': [r['name'] for r in result['named_audit'] if r['status'] == 'needs_review'],
            }
        )
    )


def coverage_markdown(data):
    lines = [
        '# Magic shopping coverage — 2026-09-26',
        '',
        'Generated offline with `uv run --offline python -m inventory_tracking.shop.build_catalog`.',
        '',
        f'{len(data["builds"])} builds; {len(data["equipment_inventory"])} equipment-list entries; '
        f'{len(data["named_audit"])} named/generic magic labels; {len(data["targets"])} compiled rules.',
        '',
        'The JSON catalog preserves every source locator, source hash, item predicate, build association, '
        'and equipment-list entry. Names describe cited examples; equivalent compatible bases of the same '
        'item type also qualify. Monarch and elite throwing-base restrictions remain explicit.',
        '',
        'Named affixes use their minimum legal rolls, summing prefix/suffix contributions to the same stat. '
        'Current expansion affixes are used; legacy version-0 records are excluded. '
        'The game-data spelling aliases are recorded in `build_catalog.py`.',
        '',
        'These are candidates to inspect, not numerical prices or declarations of complete BiS gear. '
        'Starter candidates are included. Class/loadout prerequisites are retained as conditions rather '
        'than restricting shopping to the currently played class. Sockets, filler investments, staffmods, '
        'requirements and the complete loadout still need comparison with the cited setup.',
        '',
        'Charms, jewels and other items not present in ordinary vendor stock are cataloged for completeness; '
        'the stock reader still only scans real loaded vendor items. No gamble identity is inferred.',
        '',
        '## All builds',
        '',
        '| Build | Equipment entries | Associated rules |',
        '|---|---:|---:|',
    ]
    for build_name in data['builds']:
        entries = sum(r['build'] == build_name for r in data['equipment_inventory'])
        targets = sum(build_name in r.get('builds', []) for r in data['targets'])
        lines.append(f'| {build_name} | {entries} | {targets} |')
    lines.extend(['', '## Every named magic label', '', '| Label | Coverage | Rules |', '|---|---|---:|'])
    for row in data['named_audit']:
        lines.append(f'| {row["name"]} | {row["status"]} | {len(row["targets"])} |')
    lines.extend(
        [
            '',
            '## Source conflicts',
            '',
            'These descriptions cannot be accepted as legal magic prefix/suffix bundles. '
            'They remain in the census; they do not create fabricated magic targets.',
            '',
        ]
    )
    conflicts = sorted({r['text'] for r in data['equipment_inventory'] if r['status'] == 'source_quality_conflict'})
    lines.extend('- ' + text for text in conflicts)
    lines.extend(
        [
            '',
            '## Runtime and maintenance',
            '',
            'The hotkey only loads the generated catalog once and evaluates rules indexed by item type. '
            'It does not parse guides, rebuild profiles, query prices or access the network.',
            '',
            'Rebuild the catalog after changing build lists, reviewed profiles or item metadata; '
            'restart `make serve` after updating the Python code or generated catalog.',
            '',
        ]
    )
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
