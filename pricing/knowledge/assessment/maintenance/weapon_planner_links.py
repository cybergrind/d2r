"""Exact selected Insight and Hand of Justice occurrences with native bearer proof."""

from pathlib import Path

from pricing.knowledge.assessment.maintenance.armor_planner_links import (
    BUILDS,
    GAME,
    PROFILES,
    USES,
    pinned,
    validate_armor_mercenary,
)
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
from pricing.knowledge.assessment.maintenance.planner_occurrence_links import compile_validated_planner_links, indexed
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


def compile_weapon_planner_links(document, inventory, profiles, uses, root):
    if document is None:
        return []
    if document.get('scope') != 'reviewed_weapon_components':
        raise ValueError('Weapon planner scope is unsupported')
    roles = indexed(profiles)
    indexed(document['rows'])

    def resolve(link, read):
        role = roles.get(link['profile_id'], {})
        if (
            not role
            or fingerprint(role) != link['profile_sha256']
            or indexed(read(PROFILES)['profiles']).get(role['id']) != role
            or role.get('review_status') != 'reviewed_candidate_rule'
            or role.get('names') not in (['Insight'], ['Hand of Justice'])
            or role.get('slot') != 'Weapon'
        ):
            raise ValueError('Weapon planner requires its exact reviewed weapon role')
        matches = [u for u in uses if u['profile_id'] == role['id'] and fingerprint(u) == link['use_sha256']]
        if len(matches) != 1:
            raise ValueError('Weapon planner requires its exact reviewed use')
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
            raise ValueError('Weapon planner use is unreviewed, partial or outside scope')
        compile_demand([use], [role])
        validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
        evidence = link['planner_endorsement']
        if (
            evidence.get('weapon_component') not in ('insight_mercenary', 'hand_of_justice_player')
            or evidence.get('guide_tab') != role['variant']
        ):
            raise ValueError('Weapon planner requires its exact selected guide tab and weapon proof')
        validate_endorsement(link, role, read(BUILDS)[role['build']], root, lambda pin: pinned(read, document, pin))
        if role['side'] == 'merc':
            validate_armor_mercenary(evidence, read(GAME))
        return {'occurrence_id': link['id'], 'profile_id': role['id'], 'canonical_name': role['names'][0]}, evidence

    return compile_validated_planner_links(document, inventory, root, resolve)
