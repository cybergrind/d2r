"""Direct source links for reviewed completed armor configurations."""

from pathlib import Path

from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.planner_endorsement import validate_endorsement
from pricing.knowledge.assessment.maintenance.planner_occurrence_links import compile_validated_planner_links, indexed
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


PROFILES = 'pricing/data/appraisal-build-profiles.json'
USES = 'pricing/knowledge/assessment/rules/guide_use_reviews.json'
BUILDS = 'pricing/data/wp-a-builds.json'
GAME = 'pricing/raw/mr/planners/game-data.json'
MERCENARIES = {
    'Act 2 Might': (2, 'Might'),
    'Act 2 Holy Freeze': (2, 'Holy Freeze'),
    'Act 2 Prayer': (2, 'Prayer'),
    'Act 5 Frenzy': (5, 'Frenzy'),
}


def compile_armor_planner_links(document, inventory, profiles, uses, root):
    if document is None:
        return []
    if document.get('scope') != 'reviewed_completed_armor_recipes':
        raise ValueError('Armor planner scope is unsupported')
    roles = indexed(profiles)
    indexed(document['rows'])

    def resolve(link, read):
        role = roles.get(link['profile_id'], {})
        stored_roles = indexed(read(PROFILES)['profiles'])
        if (
            not role
            or fingerprint(role) != link['profile_sha256']
            or stored_roles.get(role['id']) != role
            or role.get('review_status') != 'reviewed_candidate_rule'
            or role.get('names') not in (['Enigma'], ['Fortitude'], ['Chains of Honor'], ['Treachery'])
            or role.get('slot') != 'Body Armor'
        ):
            raise ValueError('Armor planner requires an exact reviewed armor profile')
        matches = [u for u in uses if u['profile_id'] == role['id'] and fingerprint(u) == link['use_sha256']]
        if len(matches) != 1:
            raise ValueError('Armor planner lacks its exact reviewed use')
        use = matches[0]
        if (
            use not in read(USES)['uses']
            or use.get('review_state') != 'reviewed'
            or use.get('scope') != 'softcore'
            or use.get('strength') not in ('required', 'preferred', 'alternative')
            or use.get('historical')
            or use.get('source_coverage')
            or use.get('pattern_component')
            or use.get('item') != role['names'][0]
        ):
            raise ValueError('Armor planner use is unreviewed, partial or outside Softcore scope')
        compile_demand([use], [role])
        validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
        build = read(BUILDS)[role['build']]
        if 'shared_armor' not in link['planner_endorsement']:
            source = role['source']
            parts = source['locator'].strip('/').split('/')
            if (
                source['path'] != BUILDS
                or len(parts) < 3
                or parts[:2] != [role['build'], 'variants']
                or not parts[2].isdecimal()
                or str(int(parts[2])) != parts[2]
            ):
                raise ValueError('Armor planner requires an exact primary build variant')
            try:
                variant = build['variants'][int(parts[2])]
                labels = variant[role['side']]['Body Armor']
            except (KeyError, IndexError, TypeError) as error:
                raise ValueError('Armor planner primary equipment context missing') from error
            if (
                variant.get('name') != role['variant']
                or not isinstance(labels, list)
                or not any(isinstance(label, str) and role['names'][0] in label for label in labels)
            ):
                raise ValueError('Armor planner primary variant or armor label changed')
        evidence = link['planner_endorsement']
        expected_coverage = 'merc_runeword_component' if role['side'] == 'merc' else 'player_runeword_component'
        if (
            evidence.get('coverage') != expected_coverage
            or evidence.get('guide_tab') != role['variant']
            or evidence.get('slot') != 'tors'
        ):
            raise ValueError('Armor planner needs its exact selected armor slot and guide tab')
        validate_endorsement(link, role, build, root, lambda pin: pinned(read, document, pin))
        if role['side'] == 'merc':
            validate_armor_mercenary(evidence, read(GAME))
        return {'occurrence_id': link['id'], 'profile_id': role['id'], 'canonical_name': role['names'][0]}, evidence

    return compile_validated_planner_links(document, inventory, root, resolve)


def pinned(read, document, pin):
    if document['inputs'].get(pin['path']) != pin['sha256']:
        raise ValueError('Armor planner evidence disagrees with its source pin')
    return read(pin['path'])


def validate_armor_mercenary(evidence, game):
    expected = MERCENARIES.get(evidence.get('mercenary_type'))
    hirelings = game['hireling'].get(evidence.get('mercenary_id'), [])
    if (
        expected is None
        or not hirelings
        or not all(
            row.get('act') == expected[0]
            and any(game['skills'].get(str(row.get(f'skill{i}')), {}).get('skill') == expected[1] for i in range(1, 7))
            for row in hirelings
        )
    ):
        raise ValueError('Armor planner native mercenary does not match the reviewed wearer')
