from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_hellwarden_ubers_preserves_magic_resistance_companions_and_jewel():
    profile = next((p for p in build()['profiles'] if p['id'] == 'echoing-ubers-hellwarden'), None)
    assert profile is not None
    item = replace(
        facts('Death Mask', 'unique', "Hellwarden's Will"),
        sockets=1,
        socket_contents='filled',
        socket_items=[{'name': "Guardian's Light"}],
        stats={
            k: {'status': 'decoded', 'value': v} for k, v in [('358:0', 8), ('127:0', 1), ('93:0', 20), ('105:0', 20)]
        },
    )
    context = {'player_class': 'Warlock', 'player_items': ['Sling', 'Renewed Black Cleft']}
    result = assess_roles(item, [profile], context)[0]
    assert result['rule_trace']['truth'] == 'true'
    assert all(d['status'] == 'true' for d in result['dependencies'])
    assert "Setup socket: Guardian's Light" in result['matched']
    assert result['preferences'][0]['status'] == 'true'
    missing = assess_roles(replace(item, socket_items=[]), [profile], context)[0]
    assert any("Guardian's Light" in message for message in missing['missing'])
    for names in (['Sling'], ['Renewed Black Cleft'], []):
        changed = assess_roles(item, [profile], {**context, 'player_items': names})[0]
        assert any(d['status'] == 'false' for d in changed['dependencies'])
    unknown = assess_roles(item, [profile], {'player_class': 'Warlock'})[0]
    assert all(d['status'] == 'unknown' for d in unknown['dependencies'])
    for changed in (replace(item, ethereal=True), replace(item, stats={})):
        assert assess_roles(changed, [profile], context)[0]['status'] == 'failed'
    assert assess_roles(item, [profile], {'player_class': 'Paladin'})[0]['status'] == 'failed'


def test_socket_requirement_schema_rejects_ambiguous_or_empty_payloads():
    import pytest

    from pricing.knowledge.assessment.profiles import validate_profiles

    profile = next(p for p in build()['profiles'] if p['id'] == 'echoing-ubers-hellwarden')
    for patch in ({'required_rune': 'Um Rune'}, {'required_socket_item': ''}, {'required_socket_item': None}):
        with pytest.raises(ValueError, match='socket item'):
            validate_profiles([{**profile, **patch}])
