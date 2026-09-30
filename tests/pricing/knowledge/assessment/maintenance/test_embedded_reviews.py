"""Only exact reviewed guide configurations can discharge embedded references."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_embedded_evidence import evidence


def review_inputs(tmp_path, source_slot='Helmets'):
    source = evidence(tmp_path, slot=source_slot)
    guide_path = 'pricing/raw/mr/guides__test-build.html'
    (tmp_path / guide_path).write_bytes((tmp_path / source['guide']['path']).read_bytes())
    source['guide']['path'] = guide_path
    reference = source['reference']
    cache_path = 'pricing/data/appraisal-guide-sections.json'
    cache = {
        'sources': {
            guide_path: {
                'item_spans': [{'label': '', 'side': 'player', 'slot': source_slot}],
                'embedded_item_refs': [reference],
            }
        }
    }
    raw = json.dumps(cache).encode()
    path = tmp_path / cache_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    pin = {'path': cache_path, 'sha256': hashlib.sha256(raw).hexdigest()}
    role = {
        'id': 'helmet',
        'build': 'test-build',
        'variant': 'alternative',
        'side': 'player',
        'slot': 'Helm',
        'review_status': 'reviewed_candidate_rule',
        'names': [],
        'source': {
            **pin,
            'locator': '/sources/pricing~1raw~1mr~1guides__test-build.html/item_spans/0',
            'corroborating': [
                {**pin, 'locator': '/sources/pricing~1raw~1mr~1guides__test-build.html/embedded_item_refs/0'},
            ],
        },
    }
    use = {key: deepcopy(role[key]) for key in ('build', 'variant', 'side', 'source')}
    use.update(
        profile_id='helmet',
        pattern='helmet',
        profile_fingerprint=fingerprint(role),
        review_state='reviewed',
        scope='softcore',
        strength='alternative',
    )
    link = {'source_id': guide_path, 'reference': reference, 'status': 'definition_only'}
    row = {
        'evidence': source,
        'profile_id': 'helmet',
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'review_date': '2026-09-28',
        'reason': 'Rare casting helmet alternative; example maxima are optional.',
    }
    return {'schema_version': 1, 'rows': [row]}, [link], [role], [use]


def test_review_binds_exact_embedded_guide_use(tmp_path):
    from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews

    args = review_inputs(tmp_path)
    result = compile_embedded_reviews(*args, tmp_path)
    assert len(result) == 1
    assert result[0]['state'] == 'reviewed'
    assert result[0]['profile_id'] == 'helmet'


@pytest.mark.parametrize('change', ['role', 'use', 'side', 'slot', 'primary', 'reference', 'missing_link', 'duplicate'])
def test_review_rejects_unrelated_or_stale_configuration(tmp_path, change):
    from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews

    document, links, roles, uses = review_inputs(tmp_path)
    if change == 'role':
        document['rows'][0]['profile_fingerprint'] = 'stale'
    elif change == 'use':
        document['rows'][0]['use_fingerprint'] = 'stale'
    elif change in ('side', 'slot'):
        roles[0][change] = 'merc' if change == 'side' else 'Weapon'
    elif change == 'primary':
        roles[0]['source']['locator'] = '/sources/other/item_spans/0'
    elif change == 'reference':
        roles[0]['source']['corroborating'] = []
    elif change == 'missing_link':
        links.clear()
    else:
        document['rows'].append(deepcopy(document['rows'][0]))
    # Fresh fingerprints must not make an incompatible configuration valid.
    if change in ('side', 'slot', 'primary', 'reference'):
        uses[0].update({key: deepcopy(roles[0][key]) for key in ('side', 'source')})
        uses[0]['profile_fingerprint'] = fingerprint(roles[0])
        document['rows'][0]['profile_fingerprint'] = fingerprint(roles[0])
        document['rows'][0]['use_fingerprint'] = fingerprint(uses[0])
    with pytest.raises(ValueError, match=r'[Ee]mbedded'):
        compile_embedded_reviews(document, links, roles, uses, tmp_path)


def test_embedded_review_evidence_changes_completion_scope(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import scope_fingerprint

    document, _, _, _ = review_inputs(tmp_path)
    before = scope_fingerprint({}, {}, {}, [], [], embedded_reviews=document)
    document['rows'][0]['reason'] += ' Additional reviewed condition.'
    assert scope_fingerprint({}, {}, {}, [], [], embedded_reviews=document) != before


@pytest.mark.parametrize('slot', ['Helm', 'Helmet', 'Helmets'])
def test_review_accepts_existing_helmet_slot_spellings(tmp_path, slot):
    from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews

    document, links, roles, uses = review_inputs(tmp_path)
    roles[0]['slot'] = slot
    uses[0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['use_fingerprint'] = fingerprint(uses[0])
    assert compile_embedded_reviews(document, links, roles, uses, tmp_path)[0]['state'] == 'reviewed'


def test_body_armor_review_accepts_existing_slot_name(tmp_path):
    from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews

    document, links, roles, uses = review_inputs(tmp_path, source_slot='Body Armors')
    roles[0]['slot'] = 'Body Armors'
    uses[0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['use_fingerprint'] = fingerprint(uses[0])
    assert compile_embedded_reviews(document, links, roles, uses, tmp_path)[0]['state'] == 'reviewed'


@pytest.mark.parametrize(
    ('source_slot', 'role_slot'),
    [
        ('Off-Hand', 'Off-Hand'),
        ('Gloves', 'Gloves'),
        ('Belts', 'Belt'),
        ('Belts', 'Belts'),
        ('Boots', 'Boots'),
        ('Amulets', 'Amulet'),
        ('Amulets', 'Amulets'),
        ('Rings', 'Ring'),
        ('Rings', 'Rings'),
        ('Unique Charms', 'Charms'),
        ('Unique Charms', 'Unique Charms'),
    ],
)
def test_equipment_table_reviews_preserve_slot(tmp_path, source_slot, role_slot):
    from pricing.knowledge.assessment.maintenance.embedded_reviews import compile_embedded_reviews

    document, links, roles, uses = review_inputs(tmp_path, source_slot=source_slot)
    roles[0]['slot'] = role_slot
    uses[0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['use_fingerprint'] = fingerprint(uses[0])
    assert compile_embedded_reviews(document, links, roles, uses, tmp_path)[0]['state'] == 'reviewed'

    roles[0]['slot'] = 'Gloves' if source_slot == 'Belts' else 'Belts'
    uses[0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['profile_fingerprint'] = fingerprint(roles[0])
    document['rows'][0]['use_fingerprint'] = fingerprint(uses[0])
    with pytest.raises(ValueError, match=r'[Ee]mbedded'):
        compile_embedded_reviews(document, links, roles, uses, tmp_path)
