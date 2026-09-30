"""Compile explicit semantic reviews of exact embedded guide references."""

import hashlib
import json
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.embedded_abyss_recipes import validate_abyss_recipe
from pricing.knowledge.assessment.maintenance.embedded_dream import validate_dream_equipment
from pricing.knowledge.assessment.maintenance.embedded_dream_prose import validate_dream_prose
from pricing.knowledge.assessment.maintenance.embedded_echoing_cure import validate_echoing_cure
from pricing.knowledge.assessment.maintenance.embedded_echoing_enchant import validate_echoing_enchant
from pricing.knowledge.assessment.maintenance.embedded_echoing_enigma import validate_echoing_enigma
from pricing.knowledge.assessment.maintenance.embedded_echoing_fade import validate_echoing_fade
from pricing.knowledge.assessment.maintenance.embedded_echoing_insight import validate_echoing_insight
from pricing.knowledge.assessment.maintenance.embedded_echoing_malice import validate_echoing_malice
from pricing.knowledge.assessment.maintenance.embedded_echoing_pairing import validate_echoing_pairing
from pricing.knowledge.assessment.maintenance.embedded_echoing_starter import validate_echoing_starter
from pricing.knowledge.assessment.maintenance.embedded_evidence import validate_embedded_evidence
from pricing.knowledge.assessment.maintenance.embedded_hardcore import validate_hardcore_review
from pricing.knowledge.assessment.maintenance.embedded_negative import validate_gheed_removal
from pricing.knowledge.assessment.maintenance.guide_demand import compile_demand
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


# Equipment-table slot aliases. Narrative recipe uses and Hardcore exclusions
# have separate, explicitly bounded semantic-review policies.
SLOTS = {
    'Weapon': ('Weapon',),
    'Off-Hand': ('Off-Hand',),
    'Helmets': ('Helm', 'Helmet', 'Helmets'),
    'Weapons': ('Weapon',),
    'Daggers': ('Weapon',),
    'Body Armors': ('Armor', 'Body Armor', 'Body Armors'),
    'Shields': ('Shield',),
    'Gloves': ('Gloves',),
    'Belts': ('Belt', 'Belts'),
    'Boots': ('Boots',),
    'Amulets': ('Amulet', 'Amulets'),
    'Rings': ('Ring', 'Rings'),
    'Unique Charms': ('Charms', 'Unique Charms'),
}


def embedded_identity(link):
    return hashlib.sha256(json.dumps([link['source_id'], link['reference']], sort_keys=True).encode()).hexdigest()[:24]


def compile_embedded_reviews(document, links, profiles, uses, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
        raise ValueError('Invalid embedded review schema')
    compile_demand(uses, profiles)
    by_profile = {row['id']: row for row in profiles}
    result, seen = [], set()
    for review in document['rows']:
        evidence = review['evidence']
        matches = [
            link
            for link in links
            if link['source_id'] == evidence['guide']['path'] and link['reference'] == evidence['reference']
        ]
        if len(matches) != 1:
            raise ValueError('Embedded review has no unique scoped reference')
        identity = embedded_identity(matches[0])
        if identity in seen:
            raise ValueError('Duplicate embedded semantic review')
        seen.add(identity)
        date.fromisoformat(review['review_date'])
        if not isinstance(review.get('reason'), str) or not review['reason'].strip():
            raise ValueError('Embedded semantic review needs a reason')
        kind = review.get('kind', 'equipment')
        resolved = validate_embedded_evidence(
            evidence, root, allow_legacy=kind in {'dream_equipment', 'dream_pair_prose', 'hardcore'}
        )
        if kind in {'hardcore', 'echoing_gheed_removal'}:
            if kind == 'hardcore':
                validate_hardcore_review(review, root)
            else:
                validate_gheed_removal(review, resolved, root)
            result.append(
                {
                    'id': identity,
                    'state': 'excluded',
                    'reason': review['reason'],
                    'review_date': review['review_date'],
                }
            )
            continue
        if kind not in {
            'equipment',
            'dream_equipment',
            'dream_pair_prose',
            'abyss_recipe',
            'echoing_fade',
            'echoing_enchant',
            'echoing_pairing',
            'echoing_malice',
            'echoing_insight',
            'echoing_starter',
            'echoing_cure',
            'echoing_enigma',
        }:
            raise ValueError('Unsupported embedded semantic review kind')
        context = resolved['context']
        role = by_profile.get(review['profile_id'])
        if (
            not role
            or fingerprint(role) != review['profile_fingerprint']
            or role.get('review_status') != 'reviewed_candidate_rule'
            or (
                kind == 'equipment'
                and (
                    context['side'] != 'player'
                    or role.get('side') != 'player'
                    or context['slot'] not in SLOTS
                    or role.get('slot') not in SLOTS[context['slot']]
                )
            )
        ):
            raise ValueError('Stale or incompatible embedded role')
        endorsed = [
            use
            for use in uses
            if use['profile_id'] == role['id']
            and fingerprint(use) == review['use_fingerprint']
            and use.get('review_state') == 'reviewed'
            and use.get('scope') == 'softcore'
            and use.get('strength') in ('required', 'preferred', 'alternative')
            and not use.get('historical')
        ]
        if len(endorsed) != 1:
            raise ValueError('Embedded role has no exact reviewed endorsement')
        validator = {
            'dream_equipment': validate_dream_equipment,
            'dream_pair_prose': validate_dream_prose,
            'abyss_recipe': validate_abyss_recipe,
            'echoing_fade': validate_echoing_fade,
            'echoing_enchant': validate_echoing_enchant,
            'echoing_pairing': validate_echoing_pairing,
            'echoing_malice': validate_echoing_malice,
            'echoing_insight': validate_echoing_insight,
            'echoing_starter': validate_echoing_starter,
            'echoing_cure': validate_echoing_cure,
            'echoing_enigma': validate_echoing_enigma,
        }.get(kind)
        if validator:
            validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
            validator(review, resolved, role, root)
            result.append(
                {
                    'id': identity,
                    'state': 'reviewed',
                    'profile_id': role['id'],
                    'reason': review['reason'],
                    'review_date': review['review_date'],
                }
            )
            continue
        source = role['source']
        if evidence['guide']['path'] != f'pricing/raw/mr/guides__{role["build"]}.html':
            raise ValueError('Embedded role belongs to another build guide')
        escaped = evidence['guide']['path'].replace('~', '~0').replace('/', '~1')
        prefix = f'/sources/{escaped}/'
        if (
            source['path'] != 'pricing/data/appraisal-guide-sections.json'
            or source['locator'] != f'{prefix}item_spans/{context["span_index"]}'
        ):
            raise ValueError('Embedded role does not review the exact guide span')
        validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
        cache = json.loads((root / source['path']).read_bytes())
        primary = resolve_pointer(cache, source['locator'])
        if any(primary.get(key) != context[key] for key in ('label', 'side', 'slot')):
            raise ValueError('Embedded cached guide context differs from raw source')
        refs = [
            ref
            for ref in source.get('corroborating', [])
            if ref['path'] == source['path']
            and ref['sha256'] == source['sha256']
            and ref['locator'].startswith(prefix + 'embedded_item_refs/')
            and resolve_pointer(cache, ref['locator']) == evidence['reference']
        ]
        if len(refs) != 1:
            raise ValueError('Embedded role lacks the exact reviewed tooltip reference')
        result.append(
            {
                'id': identity,
                'state': 'reviewed',
                'profile_id': role['id'],
                'reason': review['reason'],
                'review_date': review['review_date'],
            }
        )
    return result
