"""Bounded recipe uses with source-specific bases, attack modes and bearers."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.merc_survival_templates import legal_base_condition
from pricing.knowledge.definition_store import catalog


# Reviewed memberships, not a fallback for arbitrary builds or weapon modes.
MEMBERS = {
    'Enigma': {
        'builds': {'fissure-druid': 'Druid'},
        'types': ('tors',),
        'slot': 'Body Armor',
        'stats': ('127:0', '97:54', '96:0', '36:0', '76:0', '220:0', '240:0', '31:0', '86:0', '114:0'),
        'conditions': 'General Fissure caster armor alternative for Teleport, skills and mobility. Legal body '
        'armor bases remain candidates; compare requirements and movement penalties instead of treating the '
        'planner Archon Plate as mandatory. Strength and magic find scale with character level. Do not assume '
        'the armor own Strength can equip itself. Teleport speed depends on the full FCR setup; this armor '
        'adds no FCR. Life after a credited kill differs from weapon life leech, and Damage Taken Goes To Mana '
        'restores mana from eligible hits rather than absorbing damage. No automatic best-base price premium.',
    },
    'Smoke': {
        'builds': {'fissure-druid': 'Druid'},
        'types': ('tors',),
        'slot': 'Body Armor',
        'stats': ('39:0', '41:0', '43:0', '45:0', '99:0', '16:0', '32:0', '1:0'),
        'conditions': 'Fissure resistance and recovery armor alternative. Legal body armor bases are not '
        'restricted to a planner example; meet requirements and compare movement penalties. Energy supports '
        'mana, not spell damage. Weaken charges require an actual cast and do not weaken enemies passively. '
        'No Teleport, FCR breakpoint or complete survival setup is supplied by this armor.',
    },
    'Treachery': {
        'builds': {'fissure-druid': 'Druid'},
        'types': ('tors',),
        'slot': 'Body Armor',
        'stats': ('201:17103', '99:0', '43:0'),
        'conditions': 'Fissure defensive armor alternative. The chance to trigger level 15 Fade when struck '
        'is useful potential, not proof Fade is currently active; its benefits expire. IAS, Assassin skills '
        'and Venom weapon-hit damage do not improve Fissure casting or spell damage. FHR and cold resistance '
        'remain separate observed properties. No active prebuff, Teleport or FCR breakpoint is assumed.',
    },
    'Chains of Honor': {
        'builds': {'fissure-druid': 'Druid'},
        'types': ('tors',),
        'slot': 'Body Armor',
        'stats': ('127:0', '39:0', '41:0', '43:0', '45:0', '36:0', '0:0', '74:0', '80:0', '16:0'),
        'conditions': 'Fissure caster armor alternative for skills, resistances and physical damage reduction. '
        'The general gear table specifies no base: compare requirements, defense and movement penalties. '
        'Non-ethereal supports sustained player use. Life leech and damage to demons or undead apply to '
        'eligible weapon attacks, not Fissure spell damage. This armor supplies neither Teleport nor FCR; '
        'check mobility and the full casting setup when replacing Enigma or Vipermagi. No Ubers loadout '
        'or best-base premium is inferred.',
    },
    'Black': {
        'builds': {'dragon-talon-assassin': 'Assassin', 'smite-paladin': 'Paladin'},
        'base': 'Flail',
        'types': ('mace',),
        'stats': ('136:0', '93:0', '35:0', '3:0'),
        'conditions': 'Crushing Blow and IAS support kicks or Smite. Weapon Enhanced Damage does not. '
        'Attack Rating helps Dragon Talon but not Smite; added cold damage applies to kicks only. '
        'The source uses a Flail; check the complete speed setup. Corpse Explosion charges are not an active cast.',
    },
    'Kingslayer': {
        'builds': {'smite-paladin': 'Paladin'},
        'base': 'Phase Blade',
        'types': ('swor',),
        'stats': ('93:0', '136:0', '135:0', '0:0'),
        'conditions': 'Crushing Blow, Open Wounds, IAS and Strength support Smite. Weapon ED, Attack Rating, '
        'target-defense reduction and Vengeance levels do not increase Smite damage. Check the actual speed setup.',
    },
    'Honor': {
        'builds': {'zeal-paladin': 'Paladin'},
        'base': 'Naga',
        'types': ('axe',),
        'stats': ('17:0', '18:0', '19:0', '141:0', '127:0', '60:0', '0:0', '74:0', '138:0'),
        'conditions': 'The source lists Honor Naga as a weapon alternative. ED, skills, AR, Deadly Strike '
        'and life leech support physical Zeal. There is no native IAS; evaluate speed with the full setup. '
        'Deadly Strike and another critical effect do not combine into quadruple damage.',
    },
    'Mist': {
        'builds': {'strafe-amazon': 'Amazon'},
        'base': 'Matriarchal Bow',
        'types': ('abow',),
        'stats': (
            '17:0',
            '18:0',
            '127:0',
            '151:113',
            '156:0',
            '93:0',
            '119:0',
            '3:0',
            '39:0',
            '41:0',
            '43:0',
            '45:0',
            '188:0',
        ),
        'conditions': 'The source uses a Matriarchal Bow. Concentration, weapon ED, pierce and IAS support Strafe; '
        'native bow skill levels remain a separate base property. Do not add this aura to another Concentration '
        'source such as Pride. Freeze Target can destroy corpses; check the actual attack-speed breakpoint.',
    },
    'Hand of Justice': {
        'builds': {'dream-paladin': 'Paladin'},
        'base': 'Phase Blade',
        'types': ('swor',),
        'stats': ('17:0', '18:0', '93:0', '151:102', '333:0', '115:0', '141:0', '60:0'),
        'conditions': 'Holy Fire and enemy fire-resistance reduction support the wielder fire damage, not Holy Shock. '
        'The Hybrid guide adds Dragon armor for level 30 Holy Fire; this weapon alone provides level 16. '
        'Weapon ED, life leech and Deadly Strike apply to physical attacks. Do not assume the complementary '
        'Dragon, dual Dreams, Faith mercenary or complete speed breakpoint from this item.',
    },
    'Stone': {
        'builds': {'zeal-paladin': 'Paladin'},
        'types': ('tors',),
        'slot': 'Body Armor',
        'stats': ('16:0', '32:0', '99:0', '0:0', '3:0', '1:0', '39:0', '41:0', '43:0', '45:0'),
        'conditions': 'A reviewed defensive Zeal armor alternative: defense, FHR, attributes and resistances. '
        'The guide does not prescribe one base; legal body armors remain candidates subject to requirements. '
        'Clay Golem charges are not an active summon. Ethereal repairable armor is not a durable player setup.',
    },
    'Strength': {
        'builds': {'strafe-amazon': 'Amazon'},
        'types': ('pole', 'spea'),
        'merc': 'Act 2 Might',
        'stats': ('17:0', '18:0', '136:0', '60:0', '0:0'),
        'conditions': 'Early Act 2 mercenary alternative. Crushing Blow, weapon ED, life leech and Strength '
        'benefit the mercenary, not Amazon arrows. Vitality and mana recovery do not supply mercenary resources. '
        'Ethereal durability is safe; check level, requirements and the rest of the survival setup.',
    },
    'Malice': {
        'builds': {'echoing-strike-warlock-guide': 'Warlock'},
        'base': 'Mythical Sword',
        'types': ('swor',),
        'merc': 'Act 5 Frenzy',
        'slot': 'Off-Hand',
        'stats': ('135:0', '17:0', '18:0', '19:0', '116:0'),
        'conditions': 'The Ubers source uses an ethereal Mythical Sword in the second hand of a Frenzy mercenary '
        'wearing full Sazabi. Its Open Wounds apply through mercenary hits; they do not transfer to Echoing Strike. '
        'Prevent Monster Heal is not credited to the mercenary. The low-damage weapon does not replace the '
        'rest of the sustain and prebuff setup; ethereal durability is safe for this bearer.',
    },
}


def expand_source_recipe(row):
    name = row['item']
    member = MEMBERS[name]
    merc = member.get('merc')
    if (
        member['builds'].get(row['build']) != row['class']
        or row['side'] != ('merc' if merc else 'player')
        or row['slot'] != member.get('slot', 'Weapon')
        or (merc and row.get('mercenary_type') != merc)
    ):
        raise ValueError('Unreviewed source recipe context')
    must = [{'op': 'context_eq', 'field': 'player_class', 'value': row['class']}]
    if merc:
        must.append({'op': 'context_eq', 'field': 'mercenary_type', 'value': merc})
    if not merc or name == 'Malice':
        must.append({'op': 'fact_eq', 'field': 'ethereal', 'value': bool(merc)})
    must.extend(
        {'op': 'fact_eq', 'field': key, 'value': value}
        for key, value in (
            ('identified', True),
            ('runeword', name),
            ('sockets', len(catalog().runewords[name]['runes'])),
            ('socket_contents', 'filled'),
        )
    )
    must.append(legal_base_condition(name, member['types']))
    if base := member.get('base'):
        code = next(b['code'] for b in metadata()['bases'].values() if b['name'] == base)
        must.append({'op': 'fact_eq', 'field': 'base_code', 'value': code})
    stats = list(member['stats'])
    if name == 'Black' and row['build'] == 'dragon-talon-assassin':
        stats.extend(('19:0', '54:0', '55:0'))
    return {
        **{k: v for k, v in row.items() if k not in ('template', 'item', 'class')},
        'role': 'Mercenary attack support alternative' if merc else 'Source-specific completed recipe alternative',
        'review_status': 'reviewed_candidate_rule',
        'names': [name],
        'types': list(member['types']),
        'qualities': ['normal', 'superior', 'low_quality'],
        'must': {'all': must},
        'important_stats': stats,
        'conditions': [member['conditions']],
    }
