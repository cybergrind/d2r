"""Mercenary sword uses with native handedness and distinct attack/caster stats."""

import json
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition


ROOT = Path(__file__).resolve().parents[4]
MEMBERS = {
    'double-throw-barbarian-guide': ('Barbarian', ('Act 5 Frenzy',)),
    'fissure-druid': ('Druid', ('Act 5 Bash', 'Act 5 Frenzy')),
    'berserk-barbarian': ('Barbarian', ('Act 5 Bash',)),
    'fist-of-the-heavens-paladin': ('Paladin', ('Act 5 Frenzy',)),
}


def expand_merc_sword(row):
    name = row['item']
    klass, bearers = MEMBERS[row['build']]
    caster = name == 'Crescent Moon'
    if caster:
        if row['build'] != 'fissure-druid':
            raise ValueError('Unreviewed caster mercenary build')
        bearers = ('Act 3 Lightning',)
    bearer = row['mercenary_type']
    if (
        name not in ('Lawbringer', 'Crescent Moon')
        or row['class'] != klass
        or bearer not in bearers
        or row['side'] != 'merc'
        or row['slot'] != 'Weapon'
    ):
        raise ValueError('Unreviewed Lawbringer context')
    must = [
        {'op': 'context_eq', 'field': 'player_class', 'value': klass},
        {'op': 'context_eq', 'field': 'mercenary_type', 'value': bearer},
        *[
            {'op': 'fact_eq', 'field': k, 'value': v}
            for k, v in (
                ('identified', True),
                ('runeword', name),
                ('sockets', 3),
                ('socket_contents', 'filled'),
            )
        ],
        legal_base_condition(name, ('swor',)),
    ]
    if bearer in ('Act 5 Frenzy', 'Act 3 Lightning'):
        weapons = json.loads((ROOT / 'third-parties/d2data/json/weapons.json').read_text())
        codes = sorted(k for k, b in weapons.items() if b.get('type') == 'swor' and not b.get('2handed'))
        must.append({'any': [{'op': 'fact_eq', 'field': 'base_code', 'value': code} for code in codes]})
    fixed = {'berserk-barbarian': 'Legend Sword', 'fist-of-the-heavens-paladin': 'Phase Blade'}.get(row['build'])
    if fixed:
        code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == fixed)
        must.append({'op': 'fact_eq', 'field': 'base_code', 'value': code})
    if caster:
        return {
            **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
            'role': 'Lightning caster mercenary resistance-reduction alternative',
            'review_status': 'reviewed_candidate_rule',
            'names': [name],
            'types': ['swor'],
            'qualities': ['normal', 'superior', 'low_quality'],
            'must': {'all': must},
            'important_stats': ['334:0', '147:0'],
            'conditions': [
                'The Fissure source offers an Act 3 Lightning mercenary. Enemy lightning resistance '
                'reduction supports his lightning spells, not the Druid fire damage. Magic absorption '
                'protects the wearer. Weapon ED, IAS, life/mana leech, Open Wounds and on-striking procs '
                'are not spell-casting bonuses; no active Static Field proc is assumed.',
                'Act 3 mercenaries use one-handed swords. Ethereal durability is safe; verify level '
                'and equip requirements. The source Griffon and Spirit companions are not inferred.',
            ],
        }
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': 'Mercenary Decrepify and undead control alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': ['Lawbringer'],
        'types': ['swor'],
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'important_stats': ['151:119', '198:5583', '60:0', '32:0', '2:0', '116:0', '48:0', '49:0', '54:0', '55:0'],
        'conditions': [
            'Decrepify needs a mercenary hit proc; its physical resistance reduction does not multiply '
            'Berserk magic, Fissure fire or FoH/Hammer spell damage. It can support physical attacks such '
            'as Double Throw or Smite and competes with other curses.',
            'Sanctuary supplies undead control; its physical-immunity bypass belongs to the wielder, '
            'not the player. Life leech uses the mercenary physical damage, not added elemental damage. '
            'This weapon has no native ED or IAS; check the rest of the mercenary setup.',
            'Slain Monsters Rest in Peace on mercenary kills and cold damage can remove useful corpses. '
            'Ethereal durability is safe. Frenzy requires one-handed swords, while Bash can use the '
            'documented two-handed Legend Sword. This evaluates one weapon, not ownership of a second '
            'Lawbringer, Death or the complete mercenary loadout.',
        ],
    }
