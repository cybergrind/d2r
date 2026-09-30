"""Exact named-item and rune occurrences with native minima and wearer proof."""

from pathlib import Path

from pricing.knowledge.assessment.maintenance.armor_planner_links import (
    BUILDS,
    PROFILES,
    USES,
    pinned,
)
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.named_socket_endorsement import CONFIGS
from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
from pricing.knowledge.assessment.maintenance.planner_occurrence_links import compile_validated_planner_links, indexed
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


def compile_named_planner_links(document, inventory, profiles, uses, root):
    if document is None:
        return []
    if document.get('scope') != 'reviewed_named_sockets':
        raise ValueError('Named planner scope is unsupported')
    roles = indexed(profiles)
    indexed(document['rows'])

    def resolve(link, read):
        role = roles.get(link['profile_id'], {})
        if (
            not role
            or fingerprint(role) != link['profile_sha256']
            or indexed(read(PROFILES)['profiles']).get(role['id']) != role
            or role.get('review_status') != 'reviewed_candidate_rule'
            or role.get('id') not in CONFIGS
        ):
            raise ValueError('Named planner requires its exact reviewed named role')
        matches = [u for u in uses if u['profile_id'] == role['id'] and fingerprint(u) == link['use_sha256']]
        if len(matches) != 1:
            raise ValueError('Named planner requires its exact reviewed use')
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
            raise ValueError('Named planner use is unreviewed, partial or outside scope')
        compile_demand([use], [role])
        validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
        evidence = link['planner_endorsement']
        if evidence.get('named_socket') != 'native_unique' or evidence.get('guide_tab') != role['variant']:
            raise ValueError('Named planner requires its exact selected guide tab and loadout proof')
        validate_endorsement(link, role, read(BUILDS)[role['build']], root, lambda pin: pinned(read, document, pin))
        return {'occurrence_id': link['id'], 'profile_id': role['id'], 'canonical_name': role['names'][0]}, evidence

    return compile_validated_planner_links(document, inventory, root, resolve)
