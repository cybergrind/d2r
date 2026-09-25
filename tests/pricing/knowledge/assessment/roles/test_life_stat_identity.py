from dataclasses import replace

from inventory_tracking.items.metadata import decode_stats
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_decoded_item_life_bonus_satisfies_belt_role_but_current_hitpoints_do_not():
    profile = next(p for p in build()['profiles'] if p['id'] == 'foh-starter-belt')
    decoded, _, _ = decode_stats([{'id': 7, 'layer': 0, 'raw': 100 * 256}, {'id': 43, 'layer': 0, 'raw': 30}])
    item = normalize(
        {'item': facts('Belt', 'magic').to_dict(), 'decoded_stats': decoded, 'source': {'stat_capture_complete': True}}
    )
    assert item.stats['7:0']['value'] == 100
    assert assess_roles(item, [profile])[0]['rule_trace']['truth'] == 'true'
    wrong = replace(item, stats={'6:0': item.stats['7:0'], '43:0': item.stats['43:0']})
    assert assess_roles(wrong, [profile])[0]['rule_trace']['truth'] == 'false'


def test_all_reviewed_life_small_charms_accept_real_decoded_life_stat():
    profiles = build()['profiles']
    ids = {
        'lightning-ubers-sc-life-res',
        'blizzard-standard-sc-life-res',
        'blizzard-standard-sc-life-cold',
        'hammer-ubers-sc-life-res',
    }
    decoded, _, _ = decode_stats(
        [{'id': 7, 'layer': 0, 'raw': 20 * 256}, *({'id': stat, 'layer': 0, 'raw': 11} for stat in (39, 41, 43, 45))]
    )
    item = normalize(
        {
            'item': facts('Small Charm', 'magic').to_dict(),
            'decoded_stats': decoded,
            'source': {'stat_capture_complete': True},
        }
    )
    selected = [p for p in profiles if p['id'] in ids]
    assert len(selected) == 4
    assert all(r['rule_trace']['truth'] == 'true' for r in assess_roles(item, selected))
    without_life = replace(item, stats={k: v for k, v in item.stats.items() if k != '7:0'})
    assert all(r['rule_trace']['truth'] == 'false' for r in assess_roles(without_life, selected))
