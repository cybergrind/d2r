"""Reuse validated embedded recipe reviews for exact selected planner equipment."""

from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_ABBREVIATIONS
from pricing.knowledge.assessment.maintenance.embedded_evidence import _read_pin
from pricing.knowledge.assessment.maintenance.embedded_reviews import embedded_identity
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.planner_occurrence_links import compile_validated_planner_links, indexed
from pricing.knowledge.assessment.maintenance.planner_tab_endorsement import tab_endorses
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq
from pricing.knowledge.builds import decode_planner


EMBEDDED = 'pricing/knowledge/assessment/rules/embedded_reviews.json'
GAME = 'pricing/raw/mr/planners/game-data.json'
KINDS = {'echoing_insight', 'echoing_cure', 'echoing_malice'}
SLOTS = {'Weapon': 'rarm', 'Off-Hand': 'larm', 'Helmet': 'head'}


def compile_embedded_planner_links(document, embedded, dispositions, inventory, profiles, root):
    if document is None:
        return []
    roles = indexed(profiles)
    reviews = {}
    for review in embedded['rows']:
        evidence = review['evidence']
        identity = embedded_identity({'source_id': evidence['guide']['path'], 'reference': evidence['reference']})
        if identity in reviews:
            raise ValueError('Embedded planner duplicate review')
        reviews[identity] = review
    proofs = indexed(dispositions)

    def resolve(link, read):
        if read(EMBEDDED) != embedded:
            raise ValueError('Embedded planner review artifact changed')
        review = reviews.get(link['endorsement_occurrence_id'], {})
        proof = proofs.get(link['endorsement_occurrence_id'], {})
        role = roles.get(review.get('profile_id'), {})
        if (
            fingerprint(review) != link['endorsement_sha256']
            or review.get('kind') not in KINDS
            or proof.get('state') != 'reviewed'
            or not role
            or proof.get('profile_id') != role['id']
            or fingerprint(role) != review['profile_fingerprint']
            or role.get('side') != 'merc'
            or len(role.get('names', [])) != 1
            or role.get('slot') not in SLOTS
        ):
            raise ValueError('Embedded planner requires validated complete recipe and wearer evidence')
        evidence = review['evidence']
        pin, guide = evidence['planner'], evidence['guide']
        if (
            document['inputs'].get(pin['path']) != pin['sha256']
            or document['inputs'].get(guide['path']) != guide['sha256']
            or guide['path'] != f'pricing/raw/mr/guides__{role["build"]}.html'
        ):
            raise ValueError('Embedded planner source pins disagree')
        planner = decode_planner(read(pin['path']))
        index = link['profile_index']
        slot = SLOTS[role['slot']]
        if type(index) is not int or not 0 <= index < len(planner['profiles']):
            raise ValueError('Embedded planner profile index invalid')
        profile = planner['profiles'][index]
        try:
            item_id = str(profile['mercItems'][slot])
            item = planner['items'][item_id]
            original = planner['items'][evidence['reference']['item_id']]
        except (KeyError, TypeError) as error:
            raise ValueError('Embedded planner equipment reference missing') from error
        if (
            profile.get('name') != role['variant']
            or item != original
            or fingerprint(item) != evidence['item_fingerprint']
            or item.get('quality') != 7
            or not requires_eq(
                role['must'], 'context_eq', 'player_class', CLASS_ABBREVIATIONS.get(profile.get('class'))
            )
        ):
            raise ValueError('Embedded planner copied item or player context changed')
        game = read(GAME)
        hirelings = game['hireling'].get(str(profile.get('merc')), [])
        expected = (
            (5, 'Frenzy', 'Act 5 Frenzy') if review['kind'] == 'echoing_malice' else (2, 'Prayer', 'Act 2 Prayer')
        )
        act, skill, mercenary = expected
        if (
            not hirelings
            or not requires_eq(role['must'], 'context_eq', 'mercenary_type', mercenary)
            or not all(
                h.get('act') == act
                and any(game['skills'].get(str(h.get(f'skill{i}')), {}).get('skill') == skill for i in range(1, 7))
                for h in hirelings
            )
        ):
            raise ValueError('Embedded planner mercenary context changed')
        if not tab_endorses(
            _read_pin(guide, root), role['variant'], Path(pin['path']).stem, profile.get('uid'), link['quote']
        ):
            raise ValueError('Embedded planner guide does not select this variant and profile')
        normalized = {
            'occurrence_id': link['endorsement_occurrence_id'],
            'profile_id': role['id'],
            'canonical_name': role['names'][0],
        }
        planner_evidence = {
            'planner': pin,
            'coverage': 'merc_runeword_component',
            'profile_index': index,
            'profile_name': profile['name'],
            'profile_uid': profile['uid'],
            'slot': slot,
            'item_id': item_id,
            'expected_item': item,
        }
        return normalized, planner_evidence

    return compile_validated_planner_links(document, inventory, root, resolve)
