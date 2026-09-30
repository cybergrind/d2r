"""Exact Sazabi mercenary set-piece and rune occurrences with full companion proof."""

from pathlib import Path

from pricing.knowledge.assessment.maintenance.armor_planner_links import (
    BUILDS,
    PROFILES,
    USES,
    pinned,
)
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
from pricing.knowledge.assessment.maintenance.planner_occurrence_links import compile_validated_planner_links, indexed
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


def compile_sazabi_planner_links(document, inventory, profiles, uses, root):
    if document is None:
        return []
    if document.get('scope') != 'reviewed_sazabi_mercenary':
        raise ValueError('Sazabi planner scope is unsupported')
    roles = indexed(profiles)
    indexed(document['rows'])

    def resolve(link, read):
        role = roles.get(link['profile_id'], {})
        if (
            not role
            or fingerprint(role) != link['profile_sha256']
            or indexed(read(PROFILES)['profiles']).get(role['id']) != role
            or role.get('review_status') != 'reviewed_setup'
            or role.get('id')
            not in {'echoing-ubers-sazabi-helm', 'echoing-ubers-sazabi-armor', 'echoing-ubers-sazabi-sword'}
            or role.get('slot') not in ('Helmet', 'Body Armor', 'Weapon')
            or role.get('side') != 'merc'
        ):
            raise ValueError('Sazabi planner requires its exact reviewed set role')
        matches = [u for u in uses if u['profile_id'] == role['id'] and fingerprint(u) == link['use_sha256']]
        if len(matches) != 1:
            raise ValueError('Sazabi planner requires its exact reviewed use')
        use = matches[0]
        if (
            use not in read(USES)['uses']
            or use.get('review_state') != 'reviewed'
            or use.get('scope') != 'softcore'
            or use.get('strength') not in ('required', 'preferred', 'alternative')
            or use.get('historical')
            or use.get('source_coverage')
            or use.get('pattern_component')
        ):
            raise ValueError('Sazabi planner use is unreviewed, partial or outside scope')
        compile_demand([use], [role])
        validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
        evidence = link['planner_endorsement']
        if evidence.get('set_loadout') != 'sazabi_frenzy' or evidence.get('guide_tab') != role['variant']:
            raise ValueError('Sazabi planner requires its exact selected guide tab and loadout proof')
        mechanics = evidence.get('ethereal_mechanics', {})
        if document['inputs'].get(mechanics.get('path')) != mechanics.get('sha256'):
            raise ValueError('Sazabi mechanics source is unpinned')
        validate_endorsement(link, role, read(BUILDS)[role['build']], root, lambda pin: pinned(read, document, pin))
        return {'occurrence_id': link['id'], 'profile_id': role['id'], 'canonical_name': role['names'][0]}, evidence

    return compile_validated_planner_links(document, inventory, root, resolve)
