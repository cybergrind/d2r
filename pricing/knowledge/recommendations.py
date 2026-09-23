"""Reviewed local leveling advice, deliberately separate from source mentions.

The review table selects advice; it is not a prose classifier. Game facts resolve
identity and eligibility separately. Rebuild with ``python -m
pricing.knowledge.recommendations`` after exporting item facts.
"""

import hashlib
import json
from pathlib import Path


CLASSES = ('amazon', 'assassin', 'barbarian', 'druid', 'necromancer', 'paladin', 'sorceress', 'warlock')
# Benefit summaries reviewed against timestamped local transcript candidates.
# Numeric values are supplied by the independently verified item-facts layer.
GENERAL = {
    "Hsarus' Iron Stay": 'Life and cold resistance for early survival.',
    "Hsarus' Iron Heel": 'Movement speed and fire resistance; attack-rating set bonus is conditional.',
    "Berserker's Headgear": 'Fire resistance for early survival.',
    'Infernal Cranium': 'All resistances for early survival.',
    "Sander's Paragon": 'Magic find for finding leveling equipment; a farming option.',
    "Sander's Taboo": 'Life for survival; attack speed helps attack builds only.',
    "Sander's Riprap": 'Fast movement and attributes; attack rating helps attacks only.',
    "Vidala's Fetlock": 'Movement speed; weigh the strength investment.',
    "Cow King's Hooves": 'Movement speed, dexterity and magic find.',
    'Telling of Beads': 'Skills and resistances for progression.',
    "Iratha's Coil": 'Fire and lightning resistance for survival.',
    "Tal Rasha's Fine-Spun Cloth": 'Mana and magic find for progression or farming.',
    "Bul-Kathos' Wedding Band": 'Skills and life for later progression.',
    'Dwarf Star': 'Life and fire protection when cast rate is covered elsewhere.',
    "Duriel's Shell": 'Resistances, life and cannot be frozen for survival.',
    "Moser's Blessed Circle": 'Resistances and customizable sockets for survival.',
    'Rockstopper': 'Resistances, recovery and physical damage reduction.',
    'Infernostride': 'Movement and fire resistance for progression.',
    'The Stone of Jordan': 'Skills and mana for skill-based builds.',
    'String of Ears': 'Physical damage reduction for survival; life leech helps attacks only.',
    'Peasant Crown': 'Skills, movement and attributes for leveling.',
    'Nightsmoke': 'Mana and resistances for progression.',
    'Duskdeep': 'Resistances and damage reduction for early survival.',
    'Treads of Cthon': 'Movement and life for early progression.',
    'The Eye of Etlich': 'All skills benefits casters too; leech and cold damage apply to attacks.',
    'Tarnhelm': 'All skills and magic find for early progression.',
    'Nokozan Relic': 'Fire resistance and recovery for dangerous fire encounters.',
    'Gorefoot': 'Movement speed for early progression.',
    'Bloodfist': 'Life and hit recovery for early survival.',
    'Nagelring': 'Magic find for early farming; attack rating helps attacks only.',
    'Pelta Lunata': 'Early vitality, energy and strength with blocking.',
    "Biggin's Bonnet": 'Life and mana for very early progression.',
}
CASTER = {
    "Trang-Oul's Claws": 'Faster cast rate and cold resistance for caster progression.',
    'Lidless Wall': 'Skills, cast rate and mana after kills; cover resistances elsewhere.',
    'Suicide Branch': 'Cast rate, skills, life and resistances; compare your cast breakpoint.',
    'Skin of the Vipermagi': 'Skills, cast rate and resistances for caster progression.',
    'Razorswitch': 'Caster skills, cast rate and defensive stats if better alternatives are unavailable.',
    'Spectral Shard': 'Cast rate, mana and resistances; account for dexterity investment.',
    'Magefist': 'Faster cast rate for casters; fire-skill bonus only benefits relevant skills.',
    'Maelstrom': 'Early cast rate and lightning resistance; usable by casters beyond Necromancer.',
}
MELEE = {
    "Death's Guard": 'Cannot be frozen for attack builds.',
    "Death's Hand": 'Attack speed and resistances with the paired belt.',
    "Sigon's Visor": 'Conditional set attack rating for attack builds.',
    "Sigon's Gage": 'Conditional set attack speed for attack builds.',
    "Magnus' Skin": 'Attack speed, attack rating and fire resistance for attack builds.',
    'Crushflange': 'Crushing blow for attacking bosses.',
    'Knell Striker': 'Crushing blow for attacking bosses.',
    "The Cat's Eye": 'Attack speed, movement and dexterity for attack builds.',
    'Raven Frost': 'Cannot be frozen, dexterity and attack rating for attack builds.',
}
RESTRICTED = {
    'The Oculus': ('sorceress', 'caster', 'Sorceress skills and caster utility; consider the teleport-on-hit effect.'),
    "Arreat's Face": ('barbarian', 'melee', 'Barbarian skills and combat utility for progression.'),
    'Homunculus': ('necromancer', 'caster', 'Necromancer skills and resistances for progression.'),
    "Jalal's Mane": ('druid', 'general', 'Druid skills and defensive utility for progression.'),
    'Herald of Zakarum': ('paladin', 'general', 'Paladin skills and defensive utility for progression.'),
    "Titan's Revenge": ('amazon', 'melee', 'Amazon javelin skills for javelin progression.'),
}
CONDITIONS = {
    "Death's Hand": [
        "Equip Death's Guard as the second Death's Disguise piece for the recommended attack-speed bonus."
    ],
    "Hsarus' Iron Heel": [
        "Attack-rating set bonus requires a second Hsarus piece (for example Hsarus' Iron Stay). "
        'Movement and fire resistance are standalone.'
    ],
    "Sigon's Visor": ["Equip at least one other Sigon's Complete Steel piece for the recommended attack-rating bonus."],
    "Sigon's Gage": ["Equip at least one other Sigon's Complete Steel piece for the recommended attack-speed bonus."],
    'Magefist': ['Fire-skill bonus is conditional on using fire skills; cast rate remains useful to other casters.'],
    'Dwarf Star': ['Use when your required faster-cast-rate breakpoint is already covered.'],
    'Lidless Wall': ['Cover resistances in other equipment.'],
    'Razorswitch': ['Two-handed staff prevents equipping a shield; compare available alternatives.'],
}
GAPS = {
    "Sander's Superstition": 'Incidental mention without evaluated utility.',
    'The Spirit Shroud': 'Incidental alternative; no prepared recommendation yet.',
    "Sigon's Sabot": 'Conditional set bonus piece-count review not complete.',
    "Sigon's Wrap": 'Supporting set-piece mention; no independent recommendation reviewed.',
    "Cow King's Horns": 'Collective set endorsement without individual utility review.',
    "Cow King's Hide": 'Collective set endorsement without individual utility review.',
}

# Exact cached guide selections reviewed on 2026-09-23. New mentions are never
# admitted by a keyword heuristic; changed locators need another review.
GUIDE_REVIEW = (
    ('sorceress', 'Skin of the Vipermagi', 'essentials-header/item/79@(77, 80)'),
    ('sorceress', 'Magefist', 'essentials-header/item/80@(77, 233)'),
    ('sorceress', 'The Eye of Etlich', 'essentials-header/item/81@(77, 814)'),
    ('sorceress', "Hsarus' Iron Heel", 'essentials-header/item/83@(77, 979)'),
    ('sorceress', "Sander's Riprap", 'essentials-header/item/84@(77, 1055)'),
    ('sorceress', 'The Stone of Jordan', 'essentials-header/item/85@(77, 1248)'),
    ('sorceress', 'Lidless Wall', 'essentials-header/item/87@(77, 1645)'),
    ('necromancer', 'Skin of the Vipermagi', 'essentials-header/item/82@(74, 80)'),
    ('necromancer', 'Magefist', 'essentials-header/item/83@(74, 233)'),
    ('necromancer', 'The Eye of Etlich', 'essentials-header/item/84@(74, 1033)'),
    ('necromancer', "Hsarus' Iron Heel", 'essentials-header/item/86@(74, 1198)'),
    ('necromancer', "Sander's Riprap", 'essentials-header/item/87@(74, 1274)'),
    ('necromancer', 'The Stone of Jordan', 'essentials-header/item/88@(74, 1554)'),
    ('warlock', "Hsarus' Iron Heel", 'essentials-header/item/47@(90, 80)'),
    ('warlock', "Sander's Riprap", 'essentials-header/item/48@(90, 156)'),
    ('warlock', 'The Stone of Jordan', 'essentials-header/item/49@(90, 414)'),
    ('warlock', 'The Eye of Etlich', 'essentials-header/item/50@(90, 1008)'),
)
PRIORITY = {
    'Magefist': 1,
    'Maelstrom': 1,
    'Tarnhelm': 1,
    'The Eye of Etlich': 1,
    'Bloodfist': 1,
    "Sander's Riprap": 1,
    'Skin of the Vipermagi': 1,
    'Pelta Lunata': 2,
    "Biggin's Bonnet": 2,
    'Nightsmoke': 2,
    'Infernal Cranium': 2,
    'Treads of Cthon': 2,
    'Nagelring': 5,
    "Sander's Paragon": 5,
}


def _key(name):
    return name.casefold().replace('\u2019', "'").strip()


def build_recommendations(candidates, facts, utility):
    """Build reviewed records; unreviewed evidence cannot become recommendations."""
    identities = {}
    for fact in facts['rows']:
        for name in [fact['name'], *fact.get('aliases', [])]:
            identities.setdefault(_key(name), {})[fact['item_id']] = fact
    rows, census = [], []
    for candidate in candidates['items']:
        name = candidate['name']
        record = {'name': name, 'source_locator': candidate['source_timestamp']}
        matches = identities.get(_key(name), {})
        reason = GENERAL.get(name) or CASTER.get(name) or MELEE.get(name)
        classes = list(CLASSES)
        archetypes = ['caster' if name in CASTER else 'melee' if name in MELEE else 'general']
        if name in RESTRICTED:
            cls, archetype, reason = RESTRICTED[name]
            classes, archetypes = [cls], [archetype]
        if name in GAPS or not reason or len(matches) != 1:
            record.update(
                status='gap',
                reason=GAPS.get(name)
                or (
                    'Runeword/base-dependent facts are not published in this recommendation layer.'
                    if candidate.get('item_kind') == 'runeword'
                    else 'Missing or ambiguous verified identity.'
                    if len(matches) != 1
                    else 'No reviewed applicability rule.'
                ),
            )
            census.append(record)
            continue
        fact = next(iter(matches.values()))
        conditions = CONDITIONS.get(name, []).copy()
        entry = {
            'id': 'leveling:' + fact['item_id'],
            'item_id': fact['item_id'],
            'name': fact['name'],
            'kind': 'recommendation',
            'intent': 'recommend',
            'purpose': 'leveling',
            'classes': classes,
            'archetypes': archetypes,
            'priority': PRIORITY.get(name, 3),
            'side': 'player',
            'stage': 'leveling',
            'reason': reason,
            'conditions': conditions,
            'benefits': [reason],
            'evidence_strength': 'explicit' if name in RESTRICTED else 'reviewed_inference',
            'source_id': 'mrllamasc-transcript',
            'source_locator': candidate['source_timestamp'],
            'source_date': '2025-04-24',
            'provenance': [{'source_id': 'mrllamasc-transcript', 'locator': candidate['source_timestamp']}],
            'review': (
                '2026-09-23: applicability reviewed; general utility extended across classes, including Warlock. '
                'Historical source does not establish RotW-specific mechanics.'
            ),
        }
        rows.append(entry)
        if name in {'Rockstopper', "Duriel's Shell", 'Duskdeep'}:
            rows.append(
                {
                    **entry,
                    'id': entry['id'] + ':merc',
                    'side': 'merc',
                    'evidence_strength': 'explicit',
                    'conditions': [*conditions, 'Check mercenary level, strength and equipment-slot compatibility.'],
                }
            )
        census.append({**record, 'status': 'conditional' if conditions else 'accepted', 'item_id': fact['item_id']})
    guide_census = []
    source_ids = {'mrllamasc-transcript'}
    reviewed_rows = {(r.get('source_id'), r.get('source_locator'), r['name']): r for r in utility['rows']}
    for cls, name, locator in GUIDE_REVIEW:
        source_id = 'leveling-' + cls
        entry = next((r for r in rows if r['name'] == name and r['side'] == 'player'), None)
        present = (source_id, locator, name) in reviewed_rows
        guide_census.append(
            {
                'class': cls,
                'name': name,
                'source_id': source_id,
                'source_locator': locator,
                'status': 'accepted' if present and entry else 'gap',
            }
        )
        if not present or entry is None:
            continue
        source_ids.add(source_id)
        source_meta = next((s for s in utility['sources'] if s['id'] == source_id), {})
        rows.append(
            {
                **entry,
                'id': entry['id'] + ':' + cls,
                'classes': [cls],
                'evidence_strength': 'explicit',
                'source_id': source_id,
                'source_locator': locator,
                'source_date': source_meta.get('source_date'),
                'provenance': [{'source_id': source_id, 'locator': locator}],
                'review': '2026-09-23: reviewed explicit optional leveling equipment advice in guide essentials.',
            }
        )
    for cls in ('sorceress', 'necromancer', 'warlock'):
        guide_census.append(
            {
                'class': cls,
                'name': 'Ring / Amulet vendor mentions',
                'source_id': 'leveling-' + cls,
                'source_locator': 'playstyle-progression-header',
                'status': 'excluded',
                'reason': 'Pickup-to-sell instructions are not equipment advice.',
            }
        )
    patterns = [
        {
            **p,
            'item_id': None,
            'kind': 'recommendation_pattern',
            'status': 'conditional',
            'intent': 'pattern',
            'source_id': 'mrllamasc-transcript',
            'reason': 'Requires matching the actual item and verifying its requirements.',
        }
        for p in candidates['generic_patterns']
    ]
    exclusions = [{**p, 'status': 'excluded', 'intent': 'exclude'} for p in candidates['negative_or_scope_mentions']]
    source = next(
        (s for s in utility['sources'] if s['id'] == 'mrllamasc-transcript'),
        {
            'id': 'mrllamasc-transcript',
            'path': candidates.get('transcript_path'),
            'sha256': candidates.get('transcript_sha256'),
            'source_date': '2025-04-24',
        },
    )
    class_coverage = {}
    for cls in CLASSES:
        mentions = sum(r.get('class') == cls for r in utility['rows'])
        class_coverage[cls] = {
            'recommendations': sum(cls in r['classes'] for r in rows),
            'cached_evidence_rows': mentions,
            'gap': (
                'Class guide and shared-planner evidence is not automatically advice; '
                'build-specific and mercenary review remains incomplete.'
            ),
        }
    return {
        'schema_version': 1,
        'generated_at': '2026-09-23',
        'adapter_version': 1,
        'sources': [source, *[s for s in utility['sources'] if s['id'] in source_ids - {'mrllamasc-transcript'}]],
        'rows': rows,
        'patterns': patterns,
        'coverage': {
            'named': census,
            'guide_reviews': guide_census,
            'patterns': len(patterns),
            'exclusions': exclusions,
            'classes': class_coverage,
            'gaps': [
                'Named unique/set recommendations are reviewed, not an exhaustive leveling list.',
                'Runeword/base eligibility remains in existing socket and utility evidence.',
                'Mercenary coverage is limited to three reviewed defensive helm/body options.',
                'Pre-RotW transcript class-independent utility is reviewed inference for Warlock.',
            ],
        },
    }


def export_recommendations(root):
    paths = {
        key: root / 'pricing/data' / filename
        for key, filename in {
            'candidates': 'appraisal-leveling-candidates-2026-09-23.json',
            'facts': 'appraisal-item-facts.json',
            'utility': 'appraisal-utility.json',
        }.items()
    }
    payload = build_recommendations(**{key: json.loads(path.read_text()) for key, path in paths.items()})
    payload['inputs'] = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()
    }
    output = root / 'pricing/data/appraisal-recommendations.json'
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    return payload


if __name__ == '__main__':
    result = export_recommendations(Path(__file__).resolve().parents[2])
    print(json.dumps({'recommendations': len(result['rows']), 'coverage': result['coverage']}))
