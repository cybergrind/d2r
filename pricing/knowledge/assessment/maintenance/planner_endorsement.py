"""Evidence for explicitly recommended, planner-only native equipment components.

Native component and rune-socket scopes are explicit. Neither certifies a
complete loadout or an unreviewed socket payload.
"""

import hashlib
import re

from inventory_tracking.items.stat_constants import CLASS_ABBREVIATIONS
from pricing.knowledge.assessment.maintenance.cta_swap_endorsement import cta_swap_role
from pricing.knowledge.assessment.maintenance.named_socket_endorsement import named_socket_role
from pricing.knowledge.assessment.maintenance.planner_equipment_branch import equipment_branch
from pricing.knowledge.assessment.maintenance.planner_equipment_quote import equipment_quote_matches
from pricing.knowledge.assessment.maintenance.planner_jewel_endorsement import validate_jewel_socket
from pricing.knowledge.assessment.maintenance.planner_runeword_endorsement import validate_runeword
from pricing.knowledge.assessment.maintenance.planner_set_endorsement import validate_set_component
from pricing.knowledge.assessment.maintenance.planner_socket_endorsement import validate_rune_socket
from pricing.knowledge.assessment.maintenance.planner_tab_endorsement import tab_endorses, tab_selects_equipment
from pricing.knowledge.assessment.maintenance.sazabi_loadout_endorsement import sazabi_loadout_role
from pricing.knowledge.assessment.maintenance.shared_armor_endorsement import shared_armor_role
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq
from pricing.knowledge.assessment.maintenance.spirit_loadout_endorsement import spirit_loadout_role
from pricing.knowledge.assessment.maintenance.weapon_component_endorsement import weapon_component_role
from pricing.knowledge.builds import decode_planner


def words(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


def validate_endorsement(review, role, build, root, read_json):
    evidence = review.get('planner_endorsement')
    if not isinstance(evidence, dict) or evidence.get('coverage') not in (
        'intrinsic_component',
        'merc_runeword_component',
        'player_runeword_component',
        'player_intrinsic_component',
        'player_set_component',
        'merc_set_component',
        'player_rune_socket_component',
        'merc_rune_socket_component',
        'player_rune_socket_preparation',
        'player_rare_jewel_component',
    ):
        raise ValueError('Planner-only item needs an explicit native-component endorsement')
    runeword = evidence['coverage'] in ('merc_runeword_component', 'player_runeword_component')
    if 'equipment_branches' in evidence:
        if not runeword:
            raise ValueError('Equipment branch endorsements currently require a completed runeword')
        role = {**role, 'must': equipment_branch(role['must'], evidence['equipment_branches'])}
    shared_armor = 'shared_armor' in evidence
    if shared_armor:
        role = shared_armor_role(evidence, role, build, read_json)
    prebuff_swap = 'prebuff_swap' in evidence
    if prebuff_swap:
        role = cta_swap_role(evidence, role, build, read_json)
    weapon_component = 'weapon_component' in evidence
    if weapon_component:
        role = weapon_component_role(evidence, role, build, read_json)
    spirit_loadout = 'spirit_loadout' in evidence
    if spirit_loadout:
        role = spirit_loadout_role(evidence, role, build, read_json)
    set_loadout = 'set_loadout' in evidence
    if set_loadout:
        role = sazabi_loadout_role(evidence, role, build, read_json, root)
    named_socket = 'named_socket' in evidence
    if named_socket:
        role = named_socket_role(evidence, role, build, read_json)
    if evidence['coverage'] == 'merc_rune_socket_component' and not named_socket:
        raise ValueError('Mercenary rune component requires validated native named scope')
    if evidence['coverage'] == 'merc_set_component' and not set_loadout:
        raise ValueError('Mercenary set component requires validated loadout scope')
    set_component = evidence['coverage'] in ('player_set_component', 'merc_set_component')
    qualities = role.get('qualities', [])
    valid_quality = (
        bool(qualities) and set(qualities) <= {'normal', 'superior', 'low_quality'}
        if runeword
        else qualities == (['set'] if set_component else ['unique'])
    )
    guide_source = evidence.get('guide_source')
    if (
        role['side'] != ('player' if evidence['coverage'].startswith('player_') else 'merc')
        or not valid_quality
        or guide_source != f'pricing/raw/mr/guides__{role["build"]}.html'
        or evidence.get('guide', {}).get('path') != 'pricing/data/appraisal-guide-sections.json'
    ):
        raise ValueError('Unsupported planner endorsement scope')
    guide = read_json(evidence['guide'])['sources'][guide_source]
    raw = (root / guide_source).read_bytes()
    if hashlib.sha256(raw).hexdigest() != guide['source_sha256']:
        raise ValueError('Planner endorsement guide changed')
    sections = guide['sections']
    index = evidence.get('section_index')
    equipment_quote = 'equipment_quote' in evidence
    if equipment_quote:
        if not (prebuff_swap or weapon_component or spirit_loadout or named_socket):
            raise ValueError('Equipment quote endorsement requires validated weapon scope')
        quote_verified = equipment_quote_matches(evidence, role, read_json)
    else:
        if type(index) is not int or not 0 <= index < len(sections):
            raise ValueError('Invalid endorsement section')
        quote_verified = isinstance(evidence.get('quote'), str) and evidence['quote'] in sections[index]['text']
    quote, alias = evidence.get('quote'), evidence.get('variant_alias')
    tab = evidence.get('guide_tab')
    planner_path = evidence.get('planner', {}).get('path', '')
    tab_matches = (
        tab == alias
        and (
            tab_selects_equipment(
                raw.decode(),
                tab,
                planner_path.removeprefix('pricing/raw/mr/planners/').removesuffix('.json'),
                evidence.get('profile_uid'),
            )
            if equipment_quote
            else tab_endorses(
                raw.decode(),
                tab,
                planner_path.removeprefix('pricing/raw/mr/planners/').removesuffix('.json'),
                evidence.get('profile_uid'),
                quote,
            )
        )
        if tab is not None
        else False
    )
    if (
        not isinstance(quote, str)
        or not quote.strip()
        or not quote_verified
        or not any(quote in text for text in role['source']['quotes'])
        or not isinstance(alias, str)
        or not alias.strip()
        or words(alias) != words(role['variant'])
        or (not tab_matches if tab is not None else words(alias) not in words(quote))
    ):
        raise ValueError('Guide does not establish the reviewed variant recommendation')
    planner_pin = evidence.get('planner', {})
    planner_id = planner_pin.get('path', '').removeprefix('pricing/raw/mr/planners/').removesuffix('.json')
    sources = build.get('variants_sources', {})
    singular = sources.get('planner_profile')
    singular_match = re.fullmatch(r'([a-zA-Z0-9]+)\s+\([^()\r\n]+\)', singular) if isinstance(singular, str) else None
    cited = (
        planner_id in sources.get('planner_profiles', {})
        or planner_id == sources.get('planner_id')
        or (tab_matches and planner_id in sources.get('planner_ids', {}))
        or (tab_matches and singular_match is not None and singular_match[1] == planner_id)
    )
    if planner_pin.get('path') != f'pricing/raw/mr/planners/{planner_id}.json' or not cited:
        raise ValueError('Planner is not a cited source for this build')
    planner = decode_planner(read_json(planner_pin))
    index = evidence.get('profile_index')
    if type(index) is not int or not 0 <= index < len(planner['profiles']):
        raise ValueError('Invalid endorsed planner profile')
    profile = planner['profiles'][index]
    slot, item_id = evidence.get('slot'), evidence.get('item_id')
    item = planner['items'].get(item_id)
    if (
        profile.get('uid') != evidence.get('profile_uid')
        or profile.get('name') != evidence.get('profile_name')
        or profile.get('name') != role['variant']
        or profile.get('class') != evidence.get('player_class_code')
        or CLASS_ABBREVIATIONS.get(profile.get('class')) != build['class']
        or not wearer_matches(role, evidence, profile, build)
        or {
            'Helmet': 'head',
            'Gloves': 'glov',
            'Body Armor': 'tors',
            'Weapon': 'rarm',
            'Off-Hand': 'larm',
            'Weapon-Swap': 'rarm2',
            'Off-Hand-Swap': 'larm2',
        }.get(role['slot'])
        != slot
        or str(profile.get('items' if role['side'] == 'player' else 'mercItems', {}).get(slot)) != item_id
        or not item
        or item != evidence.get('expected_item')
        or item.get('quality') != (7 if runeword else 5 if set_component else 6)
        or not requires_eq(role['must'], 'fact_eq', 'base_code', item.get('base'))
        or not ethereal_matches(
            role,
            evidence,
            item,
            shared_armor=shared_armor,
            prebuff_swap=prebuff_swap,
            spirit_loadout=spirit_loadout,
            set_loadout=set_loadout,
            named_socket=named_socket,
        )
    ):
        raise ValueError('Endorsed planner equipment or wearer changed')
    if runeword:
        validate_runeword(evidence, role, item, read_json)
        return
    if set_component:
        if set_loadout:
            validate_rune_socket(evidence, role, item, read_json)
        else:
            validate_set_component(evidence, role, item, read_json)
        return
    unique = item.get('unique', '')
    if not unique.startswith('unique') or not any(
        ref.get('path') == 'third-parties/d2data/json/uniqueitems.json'
        and ref.get('locator') == '/' + unique.removeprefix('unique')
        for ref in role['source'].get('corroborating', [])
    ):
        raise ValueError('Planner named identity lacks its native definition')
    if evidence['coverage'] in (
        'player_rune_socket_component',
        'player_rune_socket_preparation',
        'merc_rune_socket_component',
    ):
        validate_rune_socket(evidence, role, item, read_json)
    elif evidence['coverage'] == 'player_rare_jewel_component':
        validate_jewel_socket(evidence, role, item, planner, read_json)
    elif item.get('socketedItems') and not (
        isinstance(evidence.get('socket_note'), str) and evidence['socket_note'].strip()
    ):
        raise ValueError('Intrinsic review must retain separate socket-payload work')


def wearer_matches(role, evidence, profile, build):
    if role['side'] == 'player':
        return requires_eq(role['must'], 'context_eq', 'player_class', build['class'])
    return str(profile.get('merc')) == evidence.get('mercenary_id') and requires_eq(
        role['must'], 'context_eq', 'mercenary_type', evidence.get('mercenary_type')
    )


def ethereal_matches(
    role,
    evidence,
    item,
    *,
    shared_armor=False,
    prebuff_swap=False,
    spirit_loadout=False,
    set_loadout=False,
    named_socket=False,
):
    if named_socket and role['id'] == 'lightning-fury-ubers-gaze-merc':
        # The validated rule has no ethereal requirement. Absence remains unknown.
        return 'ethereal' not in item or type(item['ethereal']) is bool
    if set_loadout:
        # Legal set scope has a separately pinned mechanics review, not an observed false flag.
        return 'ethereal' not in item or item['ethereal'] is False
    if prebuff_swap or spirit_loadout:
        # These validated roles impose no ethereal constraint. Missing remains unknown.
        return 'ethereal' not in item or type(item['ethereal']) is bool
    if 'ethereal' in item:
        return type(item['ethereal']) is bool and requires_eq(role['must'], 'fact_eq', 'ethereal', item['ethereal'])
    # A missing planner flag is not evidence of false. An explicit review may
    # target nonethereal player/shared armor use without claiming the planner proves it.
    return (
        (role['side'] == 'player' or shared_armor)
        and evidence.get('ethereal_scope') == 'nonethereal_only'
        and requires_eq(role['must'], 'fact_eq', 'ethereal', False)
    )
