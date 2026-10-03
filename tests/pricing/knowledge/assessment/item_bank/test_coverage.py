from dataclasses import replace

from tests.pricing.knowledge.assessment.item_bank.cases.zeal import CASES
from tests.pricing.knowledge.assessment.item_bank.coverage import audit_cases


def test_magic_trade_bank_requires_boundaries_and_unknowns():
    from tests.pricing.knowledge.assessment.item_bank.cases.jmod_trade import CASES as JMOD

    options = {'magic_trade': ['jmod-shell']}
    result = audit_cases(JMOD[:1], [], {'rows': []}, **options)
    assert result['missing']['trade:magic:jmod-shell'] == ['negative', 'unknown']
    result = audit_cases(JMOD, [], {'rows': []}, **options)
    assert result['case_coverage_complete'] is True


def test_bank_coverage_retains_unrepresented_builds_and_valuable_named_items():
    profile = {'id': CASES[0].covers[0], 'build': 'zeal-paladin', 'qualities': ['unique']}
    unseen = {'id': 'unseen-mercenary-use', 'build': 'other-build', 'qualities': ['rare']}
    tiers = {
        'rows': [
            {
                'quality': 'unique',
                'name': 'Valuable item',
                'tier': 'high',
                'leveling_review': 'no_specific_recommendation',
            }
        ]
    }
    result = audit_cases(CASES, [profile, unseen], tiers)
    assert result['case_coverage_complete'] is False
    assert 'role:unseen-mercenary-use:rare' in result['missing']
    assert 'named:unique:Valuable item' in result['missing']
    assert 'role:' + profile['id'] + ':unique' not in result['missing']
    assert result['verification'] == 'Case inventory only; execute appraisal tests to establish behavior.'


def test_positive_cases_alone_do_not_close_boundary_and_unknown_coverage():
    cases = [replace(CASES[0], covers=('example',))]
    result = audit_cases(cases, [{'id': 'example', 'build': 'test', 'qualities': ['unique']}], {'rows': []})
    assert result['missing']['role:example:unique'] == ['negative', 'unknown']


def test_one_quality_does_not_cover_other_legal_qualities():
    cases = [replace(case, covers=('example',)) for case in CASES if case.covers == CASES[0].covers]
    result = audit_cases(cases, [{'id': 'example', 'build': 'test', 'qualities': ['unique', 'rare']}], {'rows': []})
    assert 'role:example:unique' not in result['missing']
    assert result['missing']['role:example:rare'] == ['negative', 'positive', 'unknown']


def test_precise_json_evidence_locators_resolve():
    """Native set tables use named keys; item IDs are not interchangeable pointers."""
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES as ALL_CASES

    root = Path(__file__).resolve().parents[5]
    references = {e for case in ALL_CASES for e in case.evidence if '.json:/' in e}
    assert references
    for reference in sorted(references):
        path, pointer = reference.split(':/', 1)
        node = json.loads((root / path).read_text())
        for index, token in enumerate(pointer.split('/')):
            # Planner /data is a JSON-encoded document. Nested planner locators
            # address that decoded payload, not characters in the source string.
            if (
                index == 1
                and pointer.startswith('data/')
                and path.startswith('pricing/raw/mr/planners/')
                and isinstance(node, str)
            ):
                node = json.loads(node)
            token = token.replace('~1', '/').replace('~0', '~')
            if isinstance(node, list):
                assert token.isdigit(), reference
                assert int(token) < len(node), reference
                node = node[int(token)]
            else:
                assert isinstance(node, dict), reference
                assert token in node, reference
                node = node[token]


def test_stat_qualified_trade_watches_require_boundary_and_unknown_scenarios():
    from tests.pricing.knowledge.assessment.item_bank.cases.charm_trade import CASES as CHARMS

    watch = {
        'kind': 'affixed_value_watch',
        'rarity': 'magic',
        'details': {
            'watch_id': 'druid-summoning-life-skiller',
            'priority': 'valuable_candidate',
        },
    }
    cases = [replace(c, covers=('watch:druid-summoning-life-skiller',)) for c in CHARMS if c.item.rarity == 'magic']
    result = audit_cases([c for c in cases if c.scenario == 'positive'], [], {'rows': []}, watches=[watch])
    target = 'watch:druid-summoning-life-skiller:magic'
    assert result['missing'][target] == ['negative', 'unknown']
    result = audit_cases(cases, [], {'rows': []}, watches=[watch])
    assert result['case_coverage_complete'] is True
    assert result['verification'] == 'Case inventory only; execute appraisal tests to establish behavior.'


def test_consumable_coverage_requires_identity_boundary_and_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.consumables import CASES as POTIONS

    positive = [case for case in POTIONS if case.id == 'consumable-wms-positive']
    result = audit_cases(positive, [], {'rows': []}, consumables=['wms'])
    assert result['missing']['consumable:wms'] == ['negative', 'unknown']
    cases = [case for case in POTIONS if case.covers == ('consumable:wms',)]
    assert audit_cases(cases, [], {'rows': []}, consumables=['wms'])['case_coverage_complete']


def test_wrong_quality_negative_targets_intended_role_quality():
    profiles = [{'id': 'example', 'build': 'test', 'qualities': ['magic', 'rare']}]
    case = replace(
        CASES[0],
        scenario='negative',
        item=replace(CASES[0].item, rarity='normal'),
        covers=('role:example:magic',),
    )
    result = audit_cases([case], profiles, {'rows': []})
    assert result['orphaned_case_targets'] == []
    assert result['missing']['role:example:magic'] == ['positive', 'unknown']
    assert result['missing']['role:example:rare'] == ['negative', 'positive', 'unknown']
    unknown_target = replace(case, covers=('role:missing:magic',))
    assert audit_cases([unknown_target], profiles, {'rows': []})['orphaned_case_targets'] == ['role:missing:magic']


def test_wrong_quality_cannot_supply_positive_or_unknown_target_coverage():
    import pytest

    for scenario in ('positive', 'unknown'):
        case = replace(
            CASES[0],
            scenario=scenario,
            item=replace(CASES[0].item, rarity='normal'),
            covers=('role:example:magic',),
        )
        with pytest.raises(ValueError, match=r'quality.*negative'):
            audit_cases([case], [{'id': 'example', 'build': 'test', 'qualities': ['magic']}], {'rows': []})


def test_material_identity_requires_positive_negative_and_unknown_cases():
    case = replace(CASES[0], covers=('socket_material:r01',), scenario='positive')
    result = audit_cases([case], [], {'rows': []}, socket_materials=['r01', 'r02'])
    assert result['missing']['socket_material:r01'] == ['negative', 'unknown']
    assert result['missing']['socket_material:r02'] == ['negative', 'positive', 'unknown']
    assert result['orphaned_case_targets'] == []


def test_supply_case_inventory_requires_all_scenarios_per_exact_native_identity():
    from tests.pricing.knowledge.assessment.item_bank.cases.supplies import CASES as SUPPLIES

    result = audit_cases(SUPPLIES, [], {'rows': []}, supplies=['isc', 'tsc', 'ibk', 'tbk', 'key', 'aqv', 'cqv'])
    assert result['case_coverage_complete']
    assert result['counts']['required_targets'] == 7
    missing = audit_cases(SUPPLIES[:2], [], {'rows': []}, supplies=['isc'])
    assert missing['missing'] == {'supply:isc': ['unknown']}


def test_recipe_material_inventory_requires_every_native_identity_and_scenario():
    from tests.pricing.knowledge.assessment.item_bank.cases.quest_materials import CASES as MATERIALS, EXAMPLES

    codes = [code for code, _, _ in EXAMPLES]
    result = audit_cases(MATERIALS, [], {'rows': []}, quest_materials=codes)
    assert result['case_coverage_complete']
    assert result['counts']['required_targets'] == 22
    assert result['orphaned_case_targets'] == []
    missing = audit_cases(MATERIALS[:2], [], {'rows': []}, quest_materials=codes)
    assert missing['missing']['quest_material:pk1'] == ['unknown']
    assert missing['missing']['quest_material:box'] == ['negative', 'positive', 'unknown']


def test_plain_resistance_and_gold_watches_have_individual_boundary_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.collectible_combinations import CASES as COLLECTIBLES
    from tests.pricing.knowledge.assessment.item_bank.cases.gold_find_charms import CASES as GOLD

    identifiers = {
        'plain-res-3',
        'plain-res-4',
        'plain-res-5',
        'grand-gold',
        'small-gold',
        'lucky-gold',
        'warcries-gold',
        'sharp-gold',
        'shimmering-gold',
        'ruby-gold',
    }
    targets = {f'watch:{key}' for key in identifiers}
    cases = [case for case in (*COLLECTIBLES, *GOLD) if targets.intersection(case.covers)]
    watches = [
        {
            'kind': 'affixed_value_watch',
            'rarity': 'magic',
            'details': {'watch_id': key, 'priority': 'valuable_candidate'},
        }
        for key in identifiers
    ]
    result = audit_cases(cases, [], {'rows': []}, watches=watches)
    assert result['missing'] == {}
    assert result['orphaned_case_targets'] == []


def test_intrinsic_socket_roll_regressions_count_toward_their_named_items():
    from tests.pricing.knowledge.assessment.item_bank.cases.andariel_intrinsic_rolls import CASES as ANDARIEL
    from tests.pricing.knowledge.assessment.item_bank.cases.guardian_intrinsic_rolls import CASES as GUARDIAN

    tiers = {
        'rows': [
            {'quality': 'unique', 'name': name, 'tier': 'high'} for name in ("Andariel's Visage", 'Guardian Angel')
        ]
    }
    result = audit_cases((*ANDARIEL, *GUARDIAN), [], tiers)
    assert result['orphaned_case_targets'] == []
    assert result['missing'] == {
        "named:unique:Andariel's Visage": ['negative'],
        'named:unique:Guardian Angel': ['negative', 'unknown'],
    }


def test_low_baselines_with_valuable_rolls_still_require_named_cases():
    policies = [
        {'quality': 'unique', 'name': 'Perfect roll', 'default_tier': 'low', 'overrides': [{'tier': 'med'}]},
        {
            'quality': 'unique',
            'name': 'Valuable variant',
            'default_tier': 'trash',
            'overrides': [],
            'variant_rules': [{'default_tier': 'low', 'overrides': [{'tier': 'high'}]}],
        },
        {'quality': 'unique', 'name': 'Excluded identity', 'default_tier': 'high', 'overrides': []},
    ]
    tiers = {
        'rows': [
            {'quality': 'unique', 'name': name, 'tier': 'low'}
            for name in ('Perfect roll', 'Valuable variant', 'Ordinary')
        ]
    }
    result = audit_cases([], [], tiers, named_policies=policies)
    assert set(result['missing']) == {'named:unique:Perfect roll', 'named:unique:Valuable variant'}


def test_conditional_weapon_and_resistance_variants_have_named_boundary_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES as BANK

    names = ('Death Cleaver', "Demon's Arch", 'Tomb Reaver', "Kira's Guardian")
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'med'} for name in names]}
    result = audit_cases(BANK, [], tiers)
    assert result['missing'] == {}


def test_abyss_insight_bank_covers_bearer_boundaries_in_each_legal_base_quality():
    from tests.pricing.knowledge.assessment.item_bank.cases.abyss_insight import CASES as MERC
    from tests.pricing.knowledge.assessment.item_bank.cases.abyss_player_insight import CASES as PLAYER

    profiles = [
        {'id': role, 'qualities': ['normal', 'superior', 'low_quality'], 'build': 'abyss-warlock-build-guide'}
        for role in ('abyss-warlock-insight-act-2-might', 'abyss-warlock-player-insight-staff')
    ]
    result = audit_cases((*MERC, *PLAYER), profiles, {'rows': []})
    assert result['missing'] == {}
    assert result['orphaned_case_targets'] == []


def test_high_demand_named_roll_cases_cover_premium_near_miss_and_unknown():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = ["Andariel's Visage", 'Arachnid Mesh', 'War Traveler', 'Raven Frost']
    targets = {'named:unique:' + name for name in names}
    relevant = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'high'} for name in names]}
    result = audit_cases(relevant, [], tiers)
    assert result['missing'] == {}


def test_caster_premium_bank_keeps_roll_and_socket_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = ["Griffon's Eye", "Mara's Kaleidoscope", "Death's Web", 'Crown of Ages']
    targets = {'named:unique:' + name for name in names}
    relevant = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'high'} for name in names]}
    assert audit_cases(relevant, [], tiers)['missing'] == {}


def test_poison_nova_andariel_bank_preserves_both_mercenary_variants():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        f'poison-nova-necromancer-{variant}-merc-andariel-{kind}'
        for variant in (1, 2)
        for kind in ('native', 'ias-fire')
    }
    profiles = [{'id': role, 'build': 'poison-nova-necromancer', 'qualities': ['unique']} for role in roles]
    relevant = [case for case in CASES if roles.intersection(case.covers)]
    assert audit_cases(relevant, profiles, {'rows': []})['missing'] == {}


def test_generic_leveling_scope_keeps_existing_cases_optional_and_valuable_targets_required(tmp_path):
    from pricing.knowledge.assessment.maintenance.value_scope import profile_fingerprint
    from tests.pricing.knowledge.assessment.maintenance.test_value_scope import inputs

    profile, review = inputs(tmp_path)
    profile.update(build='example', qualities=['unique'])
    review['uses'][0]['profile_sha256'] = profile_fingerprint(profile)
    cases = [replace(CASES[0], covers=(profile['id'],))]
    valuable = {'id': 'valuable-use', 'build': 'example', 'qualities': ['unique']}
    result = audit_cases(cases, [profile, valuable], {'rows': []}, value_scope=review, source_root=tmp_path)
    assert 'role:temporary-dagger:unique' not in result['missing']
    assert result['optional_case_targets'] == ['role:temporary-dagger:unique']
    assert result['orphaned_case_targets'] == []
    assert result['missing']['role:valuable-use:unique'] == ['negative', 'positive', 'unknown']
    assert not result['case_coverage_complete']


def test_named_generic_leveling_is_optional_but_top_and_unknown_uses_stay_required():
    names = ('Ordinary', 'Exceptional', 'Missing evidence', 'Trade valuable')
    tiers = {
        'rows': [
            {
                'quality': 'unique',
                'name': name,
                'tier': 'high' if name == 'Trade valuable' else 'low',
                'leveling_review': 'recommendation',
            }
            for name in names
        ]
    }
    reviews = [
        {'quality': 'unique', 'name': name, 'status': 'recommendation', 'recommendation_ids': [name]} for name in names
    ]
    recommendations = [
        {
            'id': name,
            'priority': 1 if name == 'Exceptional' else 2,
            'intent': 'recommend',
            'purpose': 'leveling',
            'review': 'Reviewed use',
            'evidence_strength': 'explicit',
        }
        for name in names
        if name != 'Missing evidence'
    ]
    case = replace(CASES[0], covers=('named:unique:Ordinary',))
    result = audit_cases([case], [], tiers, named_leveling=reviews, recommendations=recommendations)
    assert result['optional_case_targets'] == ['named:unique:Ordinary']
    assert result['orphaned_case_targets'] == []
    assert set(result['missing']) == {'named:unique:' + name for name in names[1:]}


def test_supplemental_best_leveling_cannot_be_excluded_by_ordinary_recommendation():
    tier = {'quality': 'unique', 'name': 'Combination', 'tier': 'low', 'leveling_review': 'conditional_combination'}
    review = {**tier, 'recommendation': {'tier': 'high'}, 'recommendation_ids': []}
    result = audit_cases([], [], {'rows': [tier]}, named_leveling=[review], recommendations=[])
    assert 'named:unique:Combination' in result['missing']


def test_premium_named_watch_remains_required_despite_low_baseline_and_ordinary_leveling():
    row = {'quality': 'unique', 'name': 'War Traveler', 'tier': 'low', 'leveling_review': 'recommendation'}
    review = {**row, 'recommendation': {'tier': 'med'}}
    watch = {
        'name': 'War Traveler',
        'rarity': 'unique',
        'kind': 'value_watch',
        'details': {'priority': 'valuable_candidate'},
    }
    result = audit_cases([], [], {'rows': [row]}, watches=[watch], named_leveling=[review])
    assert 'named:unique:War Traveler' in result['missing']
    assert 'named:unique:War Traveler' not in result['scope_excluded_targets']


def test_premium_unique_charms_have_named_roll_boundary_and_unknown_scenarios():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = ('Annihilus', 'Hellfire Torch')
    targets = {'named:unique:' + name for name in names}
    cases = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'high'} for name in names]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_elemental_and_survival_premiums_have_named_boundary_scenarios():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = ("Eschuta's Temper", "Nightwing's Veil", 'Ravenlore', "Verdungo's Hearty Cord")
    targets = {'named:unique:' + name for name in names}
    cases = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'high'} for name in names]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_specialist_skill_rolls_have_named_positive_negative_and_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = ('Thunderstroke', "Arkaine's Valor")
    targets = {'named:unique:' + name for name in names}
    cases = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'high'} for name in names]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_griswold_weapon_socket_premium_has_named_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    target = "named:set:Griswold's Redemption"
    cases = [case for case in CASES if target in case.covers]
    tiers = {'rows': [{'quality': 'set', 'name': "Griswold's Redemption", 'tier': 'med'}]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_loose_facet_variants_have_named_roll_boundary_and_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    target = 'named:unique:Rainbow Facet'
    cases = [case for case in CASES if target in case.covers]
    tiers = {'rows': [{'quality': 'unique', 'name': 'Rainbow Facet', 'tier': 'high'}]}
    assert audit_cases(cases, [], tiers)['missing'] == {}
    assert {case.item.named_table_id for case in cases} == set(range(392, 400))


def test_original_sunder_named_penalty_boundaries_have_bank_coverage():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = ('Cold Rupture', 'Flame Rift', 'Crack of the Heavens', 'Bone Break', 'Black Cleft')
    targets = {'named:unique:' + name for name in names}
    cases = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'high'} for name in names]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_remaining_valuable_set_pieces_have_named_identity_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = (
        "Guillaume's Face",
        "Immortal King's Soul Cage",
        "Tal Rasha's Adjudication",
        "Tal Rasha's Horadric Crest",
        "Tal Rasha's Lidless Eye",
        "Trang-Oul's Girth",
    )
    targets = {'named:set:' + name for name in names}
    cases = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'set', 'name': name, 'tier': 'med'} for name in names]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_thundergod_defense_roll_and_unknown_capture_have_named_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    target = "named:unique:Thundergod's Vigor"
    cases = [case for case in CASES if target in case.covers]
    tiers = {'rows': [{'quality': 'unique', 'name': "Thundergod's Vigor", 'tier': 'med'}]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_latent_and_renewed_watch_targets_have_independent_named_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    names = (
        'Latent Black Cleft',
        'Latent Bone Break',
        'Latent Crack of the Heavens',
        'Renewed Black Cleft',
        'Renewed Bone Break',
        'Renewed Cold Rupture',
        'Renewed Crack of the Heavens',
        'Renewed Flame Rift',
    )
    targets = {'named:unique:' + name for name in names}
    cases = [case for case in CASES if targets.intersection(case.covers)]
    tiers = {'rows': [{'quality': 'unique', 'name': name, 'tier': 'med'} for name in names]}
    assert audit_cases(cases, [], tiers)['missing'] == {}


def test_assassin_trap_claw_candidates_have_native_combination_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = ('lightning-sentry-claw-candidate', 'wake-of-fire-claw-candidate')
    cases = [case for case in CASES if set(roles).intersection(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['magic']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_enchant_prebuff_combination_has_native_missing_component_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    role = 'enchant-prebuff-orb-candidate'
    cases = [case for case in CASES if role in case.covers]
    profiles = [{'id': role, 'build': 'enchant-sorceress', 'qualities': ['magic']}]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_circlet_candidates_cover_class_cast_rate_and_fire_skill_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'poison-nova-standard-circlet': 'rare',
        'foh-tribrid-circlet': 'rare',
        'enchant-standard-circlet': 'magic',
        'enchant-prebuff-circlet': 'magic',
    }
    cases = [case for case in CASES if roles.keys() & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': [quality]} for role, quality in roles.items()]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_tri_resist_boots_cover_shared_candidate_roles():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'blizzard-standard-boots',
        'lightning-sentry-standard-boots',
        'fire-warlock-standard-boots',
        'fire-warlock-mf-boots',
        'lightning-fury-ubers-boots',
        'lightning-strike-ubers-boots',
        'fissure-ubers-boots',
        'lightning-sorceress-ubers-boots',
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['rare']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_gold_find_boots_have_combination_and_unknown_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    role = 'gold-find-budget-boots'
    cases = [case for case in CASES if role in case.covers]
    profiles = [{'id': role, 'build': 'gold-find-barbarian', 'qualities': ['rare']}]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_javelin_gloves_cover_magic_rare_and_boss_swap_candidates():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'lightning-fury-standard-gloves': 'magic',
        'lightning-strike-boss-gloves': 'magic',
        'lightning-fury-mf-gloves': 'rare',
        'lightning-fury-ubers-gloves': 'rare',
        'lightning-strike-standard-gloves': 'rare',
    }
    cases = [case for case in CASES if roles.keys() & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': [quality]} for role, quality in roles.items()]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_crafted_gloves_have_specialist_combination_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {'double-throw-standard-gloves', 'smite-high-investment-gloves', 'dragon-talon-budget-gloves'}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['crafted']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_sorceress_amulets_distinguish_cast_rate_and_prebuff_skill_requirements():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'nova-standard-amulet': 'crafted',
        'nova-mf-amulet': 'crafted',
        'nova-hydra-amulet': 'crafted',
        'enchant-standard-amulet': 'crafted',
        'enchant-mf-amulet': 'crafted',
        'enchant-prebuff-amulet': 'magic',
    }
    cases = [case for case in CASES if roles.keys() & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': [quality]} for role, quality in roles.items()]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_specialist_farming_accessories_have_stat_and_loadout_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {'meteor-standard-volcanic-luck-amulet': 'magic', 'goldfind-budget-belt': 'rare'}
    cases = [case for case in CASES if roles.keys() & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': [quality]} for role, quality in roles.items()]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_remaining_teleport_amulet_alternatives_cover_both_qualities():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'double-throw-barbarian-guide-charge-alternative-amulets-5',
        'dream-paladin-charge-alternative-amulets-4',
        'fissure-druid-charge-alternative-amulets-9',
        'poison-nova-necromancer-charge-alternative-amulets-8',
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['magic', 'rare']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_zeal_teleport_amulet_footnote_has_both_quality_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    role = 'zeal-paladin-teleport-amulet-footnote'
    cases = [case for case in CASES if role in case.covers]
    profiles = [{'id': role, 'build': 'zeal-paladin', 'qualities': ['magic', 'rare']}]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_retained_three_skill_amulets_have_native_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {'enchant-budget-amulet', 'lightning-starter-amulet'}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['magic']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_razortail_alternatives_cover_each_source_build():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        guide + '-razortail-boots-belts-alternative'
        for guide in (
            'double-throw-barbarian-guide',
            'enchant-sorceress',
            'lightning-fury-amazon-guide',
            'strafe-amazon',
        )
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_combat_boot_and_belt_alternatives_cover_remaining_builds():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    groups = {
        'nosferatu-s-coil': (
            'double-throw-barbarian-guide',
            'dream-paladin',
            'lightning-fury-amazon-guide',
            'strafe-amazon',
        ),
        'goblin-toe': ('double-throw-barbarian-guide', 'dream-paladin', 'smite-paladin'),
        'gore-rider': ('double-throw-barbarian-guide', 'dream-paladin', 'smite-paladin', 'strafe-amazon'),
    }
    roles = {f'{guide}-{item}-boots-belts-alternative' for item, guides in groups.items() for guide in guides}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_standalone_set_accessories_cover_remaining_build_alternatives():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    groups = {
        'natalya-s-soul': (
            'fissure-druid',
            'lightning-fury-amazon-guide',
            'lightning-sentry-assassin',
            'lightning-strike-amazon',
            'wake-of-fire-assassin',
        ),
        'trang-oul-s-girth': ('gold-find-barbarian', 'smite-paladin'),
    }
    roles = {f'{guide}-{item}-boots-belts-alternative' for item, guides in groups.items() for guide in guides}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['set']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_aldur_boot_alternatives_cover_remaining_source_builds():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'echoing-strike-warlock-guide',
        'enchant-sorceress',
        'fire-blast-assassin',
        'fire-warlock-guide',
        'fissure-druid',
        'fist-of-the-heavens-paladin',
        'lightning-fury-amazon-guide',
        'lightning-sentry-assassin',
        'lightning-sorceress',
        'lightning-strike-amazon',
        'meteor-sorceress',
        'mirrored-blades-warlock-guide',
        'poison-nova-necromancer',
        'smite-paladin',
        'strafe-amazon',
        'wake-of-fire-assassin',
    )
    roles = {guide + '-aldur-boots-alternative' for guide in guides}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['set']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_waterwalk_alternatives_cover_remaining_source_builds():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'echoing-strike-warlock-guide',
        'fire-blast-assassin',
        'fire-warlock-guide',
        'fist-of-the-heavens-paladin',
        'lightning-sentry-assassin',
        'meteor-sorceress',
        'mirrored-blades-warlock-guide',
        'nova-sorceress-guide',
        'poison-nova-necromancer',
        'smite-paladin',
        'wake-of-fire-assassin',
    )
    roles = {guide + '-waterwalk-boots-alternative' for guide in guides}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_silkweave_alternatives_cover_casters_and_distinct_summoners():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        guide + '-silkweave-caster-progression-alternative'
        for guide in (
            'echoing-strike-warlock-guide',
            'fire-warlock-guide',
            'fist-of-the-heavens-paladin',
            'lightning-fury-amazon-guide',
            'lightning-sorceress',
            'nova-sorceress-guide',
        )
    } | {
        'blood-boil-warlock-guide-silkweave-caster-accessory-gear',
        'summoner-warlock-guide-silkweave-caster-accessory-gear',
        'summoner-necromancer-guide-silkweave-summoner-caster-gear',
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_sandstorm_caster_alternatives_cover_self_repair_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        guide + '-sandstorm-trek-caster-accessory-gear'
        for guide in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'frozen-orb-sorceress',
            'frozen-orb-meteor-sorceress',
            'fire-wall-sorceress-guide',
            'hydra-sorceress',
        )
    } | {'summoner-necromancer-guide-sandstorm-trek-summoner-caster-gear'}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_caster_section_aldur_and_waterwalk_alternatives_have_scenarios():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'blood-boil-warlock-guide',
        'summoner-warlock-guide',
        'frozen-orb-sorceress',
        'frozen-orb-meteor-sorceress',
        'fire-wall-sorceress-guide',
        'hydra-sorceress',
    )
    roles = {
        f'{guide}-{item}-caster-accessory-gear': quality
        for guide in guides
        for item, quality in (('aldur-s-advance', 'set'), ('waterwalk', 'unique'))
    }
    roles['summoner-necromancer-guide-aldur-s-advance-summoner-caster-gear'] = 'set'
    cases = [case for case in CASES if roles.keys() & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': [quality]} for role, quality in roles.items()]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_caster_magic_find_accessories_cover_all_reviewed_sources():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'blood-boil-warlock-guide',
        'summoner-warlock-guide',
        'frozen-orb-sorceress',
        'frozen-orb-meteor-sorceress',
        'fire-wall-sorceress-guide',
        'hydra-sorceress',
    )
    roles = {f'{guide}-{item}-caster-accessory-gear' for guide in guides for item in ('chance-guards', 'goldwrap')}
    roles |= {f'summoner-necromancer-guide-{item}-summoner-caster-gear' for item in ('chance-guards', 'goldwrap')}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_caster_ring_alternatives_cover_skill_life_and_fire_defense():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'blood-boil-warlock-guide',
        'summoner-warlock-guide',
        'frozen-orb-sorceress',
        'frozen-orb-meteor-sorceress',
        'fire-wall-sorceress-guide',
        'hydra-sorceress',
    )
    roles = {f'{guide}-bul-kathos-wedding-band-caster-accessory-gear' for guide in guides}
    roles |= {f'{guide}-dwarf-star-caster-accessory-gear' for guide in guides[2:]}
    roles.add('summoner-necromancer-guide-bul-kathos-wedding-band-summoner-caster-gear')
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_defensive_caster_belts_cover_mitigation_without_leech_credit():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        guide + '-verdungo-s-hearty-cord-caster-accessory-gear'
        for guide in (
            'frozen-orb-sorceress',
            'frozen-orb-meteor-sorceress',
            'fire-wall-sorceress-guide',
            'hydra-sorceress',
        )
    } | {'summoner-necromancer-guide-string-of-ears-summoner-caster-gear'}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_vipermagi_caster_alternatives_cover_socket_and_upgrade_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        f'{guide}-skin-of-the-vipermagi-caster-core-gear'
        for guide in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'frozen-orb-sorceress',
            'frozen-orb-meteor-sorceress',
            'fire-wall-sorceress-guide',
            'hydra-sorceress',
        )
    } | {'summoner-necromancer-guide-skin-of-the-vipermagi-summoner-caster-gear'}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_ormus_alternatives_cover_element_and_optional_skill_recipients():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        f'{guide}-ormus-robes-caster-armor-remainder'
        for guide in (
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_que_hegan_alternatives_separate_player_and_minion_kills():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        f'{guide}-que-hegan-s-wisdom-caster-armor-remainder'
        for guide in ('blood-boil-warlock-guide', 'summoner-warlock-guide')
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_skullder_alternatives_cover_all_source_uses_and_repair_uncertainty():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.skullder_alternatives import USES

    roles = {
        f'{guide}-skullder-{slot.lower().replace(" ", "-")}-utility-alternative'
        for _, sources in USES
        for guide, slot, _ in sources
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_arachnid_caster_alternatives_cover_all_reviewed_gear_tables():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        guide + '-arachnid-mesh-caster-core-gear'
        for guide in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    } | {
        'summoner-necromancer-guide-arachnid-mesh-summoner-caster-gear',
        'blizzard-standard-arachnid',
        'meteor-standard-arachnid',
        'lightning-standard-arachnid',
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_stone_of_jordan_build_variants_and_table_alternatives_are_covered():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    variants = {
        'blizzard-sorceress': (1,),
        'enchant-sorceress': (1,),
        'fissure-druid': (1, 2, 3),
        'lightning-sentry-assassin': (1,),
        'lightning-sorceress': (1,),
        'nova-sorceress-guide': (1, 2, 3),
        'poison-nova-necromancer': (1, 2),
        'summoner-necromancer-guide': (1, 2),
    }
    roles = {f'{guide}-{variant}-soj' for guide, indices in variants.items() for variant in indices}
    roles |= {
        guide + '-the-stone-of-jordan-caster-core-gear'
        for guide in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_harlequin_caster_tables_and_magic_find_variants_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-2-harlequin'
        for g in (
            'blizzard-sorceress',
            'double-throw-barbarian-guide',
            'echoing-strike-warlock-guide',
            'enchant-sorceress',
            'fire-warlock-guide',
            'meteor-sorceress',
            'lightning-sentry-assassin',
        )
    }
    roles |= {
        g + '-harlequin-crest-caster-core-gear'
        for g in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    }
    roles.add('summoner-necromancer-guide-harlequin-crest-summoner-caster-gear')
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_nightwing_cold_caster_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'blizzard-sorceress-nightwing-s-veil-equipment-tail-alternative',
        'frozen-orb-sorceress-nightwing-s-veil-caster-defense-gear',
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_fathom_cold_caster_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'blizzard-sorceress-death-s-fathom-caster-shield-alternative',
        'frozen-orb-meteor-sorceress-death-s-fathom-caster-weapon-gear',
        'frozen-orb-sorceress-death-s-fathom-caster-weapon-gear',
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_wizardspike_slot_and_table_roles_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    slots = {
        'blizzard-sorceress': ('weapon',),
        'dragon-talon-assassin': ('weapon',),
        'dream-paladin': ('weapon-swap',),
        'echoing-strike-warlock-guide': ('weapon',),
        'fire-warlock-guide': ('weapon',),
        'fist-of-the-heavens-paladin': ('weapon',),
        'gold-find-barbarian': ('weapon-swap', 'off-hand-swap'),
        'lightning-fury-amazon-guide': ('weapon-swap',),
        'lightning-sentry-assassin': ('weapon',),
        'lightning-sorceress': ('weapon', 'weapon-swap'),
        'lightning-strike-amazon': ('weapon-swap',),
        'meteor-sorceress': ('weapon',),
        'wake-of-fire-assassin': ('weapon',),
    }
    roles = {f'{g}-wizardspike-{slot}-utility-alternative' for g, slots in slots.items() for slot in slots}
    roles |= {
        g + '-wizardspike-caster-weapon-gear'
        for g in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    }
    roles.add('summoner-necromancer-guide-wizardspike-summoner-caster-gear')
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_oculus_native_and_upgraded_caster_alternatives_are_covered():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-the-oculus-jewelry-casting-alternative'
        for g in (
            'blizzard-sorceress',
            'lightning-sorceress',
            'meteor-sorceress',
            'nova-sorceress-guide',
        )
    }
    roles |= {
        g + '-the-oculus-caster-weapon-gear'
        for g in (
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_eschuta_element_specific_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-eschuta-s-temper-caster-survival-alternative'
        for g in (
            'enchant-sorceress',
            'lightning-sorceress',
            'meteor-sorceress',
        )
    }
    roles |= {g + '-eschuta-s-temper-caster-weapon-gear' for g in ('fire-wall-sorceress-guide', 'hydra-sorceress')}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_war_traveler_caster_tables_and_fissure_farming_are_covered():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-war-traveler-caster-core-gear'
        for g in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    }
    roles |= {
        'summoner-necromancer-guide-war-traveler-summoner-caster-gear',
        'fissure-player-standard-war-traveler',
        'fissure-player-magic-find-war-traveler',
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_war_traveler_sorceress_farming_breakpoints_are_covered():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {'meteor-mf-war-traveler', 'lightning-mf-war-traveler'}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_gheeds_fortune_caster_table_and_foh_roles_are_covered():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-gheed-s-fortune-gear-inventory-charm'
        for g in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    } | {'fist-of-the-heavens-paladin-gheeds-farming-charm'}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_gheeds_inventory_variants_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    variants = {
        'double-throw-barbarian-guide': (1, 2),
        'dream-paladin': (0, 1),
        'echoing-strike-warlock-guide': (1, 2),
        'enchant-sorceress': (1, 2),
        'fire-blast-assassin': (1,),
        'fire-warlock-guide': (2,),
        'fissure-druid': (1, 2),
        'gold-find-barbarian': (0, 1, 2, 3),
        'lightning-fury-amazon-guide': (2,),
        'lightning-sentry-assassin': (2,),
        'lightning-sorceress': (0, 1, 2),
        'lightning-strike-amazon': (0, 1),
        'meteor-sorceress': (1, 2, 3),
        'mirrored-blades-warlock-guide': (1,),
        'nova-sorceress-guide': (1, 2, 3),
        'poison-nova-necromancer': (1, 2),
        'strafe-amazon': (2,),
        'summoner-necromancer-guide': (1, 2),
        'wake-of-fire-assassin': (1,),
    }
    roles = {f'{g}-{v}-gheeds-inventory' for g, vs in variants.items() for v in vs}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_fire_warlock_gheeds_wager_has_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    role = 'fire-warlock-guide-gheed-s-wager-caster-utility-alternative'
    cases = [case for case in CASES if role in case.covers]
    assert (
        audit_cases(cases, [{'id': role, 'build': 'fire-warlock-guide', 'qualities': ['unique']}], {'rows': []})[
            'missing'
        ]
        == {}
    )


def test_goldwrap_slot_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-goldwrap-find-absorb-alternative'
        for g in (
            'double-throw-barbarian-guide',
            'dream-paladin',
            'echoing-strike-warlock-guide',
            'fire-blast-assassin',
            'fire-warlock-guide',
            'fissure-druid',
            'fist-of-the-heavens-paladin',
            'gold-find-barbarian',
            'lightning-sentry-assassin',
            'meteor-sorceress',
            'mirrored-blades-warlock-guide',
            'nova-sorceress-guide',
            'strafe-amazon',
            'wake-of-fire-assassin',
        )
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_goldwrap_farming_variants_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {'fire-warlock-guide-2-goldwrap', *(f'gold-find-barbarian-{i}-goldwrap' for i in (1, 2, 3))}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_gull_swap_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'abyss-warlock-build-guide',
        'blessed-hammer-paladin',
        'blizzard-sorceress',
        'echoing-strike-warlock-guide',
        'fire-warlock-guide',
        'fist-of-the-heavens-paladin',
        'meteor-sorceress',
        'mirrored-blades-warlock-guide',
    )
    roles = {g + '-gull-weapon-swap-find-weapon-alternative' for g in guides}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_ali_baba_loot_roles_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'abyss-warlock-build-guide',
        'blessed-hammer-paladin',
        'blizzard-sorceress',
        'echoing-strike-warlock-guide',
        'fire-warlock-guide',
        'fist-of-the-heavens-paladin',
        'lightning-sorceress',
        'meteor-sorceress',
        'mirrored-blades-warlock-guide',
    )
    roles = {g + '-blade-of-ali-baba-weapon-swap-find-weapon-alternative' for g in guides}
    roles.update(
        'gold-find-barbarian-blade-of-ali-baba-' + slot + '-find-weapon-alternative'
        for slot in ('weapon', 'off-hand', 'weapon-swap', 'off-hand-swap')
    )
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_annihilus_gear_tables_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-annihilus-gear-inventory-charm'
        for g in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'frozen-orb-sorceress',
            'hydra-sorceress',
        )
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_annihilus_variants_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.annihilus_variants import USES, role_rows

    roles = {role for uses in USES.values() for role, _ in role_rows(uses)}
    assert len(roles) == 55
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_torch_caster_tables_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-hellfire-torch-gear-inventory-charm'
        for g in (
            'blood-boil-warlock-guide',
            'summoner-warlock-guide',
            'fire-wall-sorceress-guide',
            'frozen-orb-meteor-sorceress',
            'hydra-sorceress',
            'frozen-orb-sorceress',
        )
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_torch_variants_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.torch_variants import USES

    roles = {f'{g}-{i}-torch' for _, _, uses in USES for g, indices in uses for i in indices}
    assert len(roles) == 56
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_tal_armor_amulet_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-tal-rasha-s-guardianship-tal-player-alternative'
        for g in (
            'blizzard-sorceress',
            'meteor-sorceress',
            'echoing-strike-warlock-guide',
            'fire-warlock-guide',
            'mirrored-blades-warlock-guide',
        )
    }
    roles.update(
        g + '-tal-rasha-s-adjudication-tal-player-alternative'
        for g in ('blizzard-sorceress', 'meteor-sorceress', 'nova-sorceress-guide')
    )
    roles.update(
        g + '-tal-rasha-s-adjudication-caster-gear-alternative'
        for g in ('fire-wall-sorceress-guide', 'frozen-orb-meteor-sorceress', 'frozen-orb-sorceress', 'hydra-sorceress')
    )
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['set']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_tal_belt_orb_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-tal-rasha-s-fine-spun-cloth-tal-player-alternative'
        for g in ('blizzard-sorceress', 'meteor-sorceress', 'nova-sorceress-guide')
    }
    roles.update(
        g + '-tal-rasha-s-lidless-eye-tal-player-alternative'
        for g in ('blizzard-sorceress', 'lightning-sorceress', 'meteor-sorceress')
    )
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['set']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_lightning_tal_three_piece_has_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {f'lightning-mf-tal-{piece}' for piece in ('armor', 'belt', 'amulet')}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['set']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_bk_utility_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.bk_utility_alternatives import USES

    roles = {g + '-bk-ring-rings-utility-alternative' for uses in USES.values() for g, _ in uses}
    assert len(roles) == 17
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_trek_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.trek_alternatives import USES

    roles = {g + '-trek-boots-alternative' for uses in USES.values() for g, _ in uses}
    assert len(roles) == 14
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_verdungo_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.verdungo_alternatives import USES

    roles = {g + '-verdungo-s-hearty-cord-defensive-alternative' for uses in USES.values() for g, _ in uses}
    assert len(roles) == 14
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_chance_guards_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.chance_guards_alternatives import SUFFIX, USES

    roles = {g + SUFFIX for uses in USES.values() for g, _ in uses}
    assert len(roles) == 13
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_dwarf_star_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.dwarf_star_alternatives import USES

    roles = {g + '-dwarf-star-defensive-alternative' for uses in USES.values() for g, _ in uses}
    assert len(roles) == 9
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_wisp_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.wisp_alternatives import USES

    roles = {g + '-wisp-projector-find-absorb-alternative' for uses in USES.values() for g, _ in uses}
    assert len(roles) == 7
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_highlord_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES
    from tests.pricing.knowledge.assessment.item_bank.cases.highlord_alternatives import USES

    roles = {g + '-highlord-s-wrath-jewelry-casting-alternative' for uses in USES.values() for g, _ in uses}
    assert len(roles) == 7
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_magefist_caster_tables_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'blood-boil-warlock-guide',
        'summoner-warlock-guide',
        'fire-wall-sorceress-guide',
        'frozen-orb-meteor-sorceress',
        'frozen-orb-sorceress',
        'hydra-sorceress',
    )
    roles = {g + '-magefist-caster-gear-alternative' for g in guides}
    roles.add('summoner-necromancer-guide-magefist-summoner-caster-gear')
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_magefist_build_variants_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    uses = {
        'enchant-sorceress': (1,),
        'fire-blast-assassin': (1,),
        'fire-warlock-guide': (1,),
        'fissure-druid': (1, 2, 3),
        'fist-of-the-heavens-paladin': (2, 3),
        'lightning-sentry-assassin': (1,),
        'meteor-sorceress': (1, 3, 4),
        'nova-sorceress-guide': (1, 2, 3),
        'wake-of-fire-assassin': (1,),
    }
    roles = {f'{guide}-{index}-magefist' for guide, indices in uses.items() for index in indices}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_lidless_wall_slot_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if '-lidless-wall-' in p['id'] and p['id'].endswith('-shield-utility-alternative')]
    assert len(profiles) == 17
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_lidless_caster_tables_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        g + '-lidless-wall-caster-gear-alternative' for g in ('blood-boil-warlock-guide', 'summoner-warlock-guide')
    }
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_thundergod_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'].endswith('-thundergod-s-vigor-defensive-alternative')]
    assert len(profiles) == 12
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_string_of_ears_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'].endswith('-string-of-ears-defensive-alternative')]
    assert len(profiles) == 7
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_cats_eye_alternatives_have_native_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    guides = (
        'double-throw-barbarian-guide',
        'dragon-talon-assassin',
        'lightning-fury-amazon-guide',
        'lightning-strike-amazon',
        'strafe-amazon',
    )
    roles = {g + '-the-cat-s-eye-jewelry-casting-alternative' for g in guides}
    cases = [case for case in CASES if roles & set(case.covers)]
    profiles = [{'id': role, 'build': role, 'qualities': ['unique']} for role in roles]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_metalgrid_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'].endswith('-metalgrid-jewelry-casting-alternative')]
    assert len(profiles) == 6
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_natures_peace_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'].endswith('-nature-s-peace-jewelry-casting-alternative')]
    assert len(profiles) == 6
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_mosers_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if '-moser-s-blessed-circle-' in p['id']]
    assert len(profiles) == 5
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_dream_pair_has_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'].startswith('dream-paladin-dream-')]
    assert len(profiles) == 2
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_suicide_branch_has_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p.get('names') == ['Suicide Branch']]
    assert len(profiles) == 11
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_blizzard_rare_rings_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'] in ('blizzard-mf-ring', 'blizzard-set-ring')]
    assert len(profiles) == 2
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_mercenary_ias_fire_jewels_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'].endswith('-ias-fire-jewel')]
    assert len(profiles) == 6
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_jmod_bases_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'].endswith('-jmod-base')]
    assert len(profiles) == 12
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_fire_warlock_ars_diabolos_has_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {'fire-warlock-standard-ars-diabolos', 'fire-warlock-mf-ars-diabolos'}
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'] in roles]
    assert len(profiles) == 2
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_remaining_griffon_variants_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'fist-of-the-heavens-paladin-2-griffon-eye',
        'lightning-fury-amazon-guide-1-griffon-eye',
        'lightning-fury-amazon-guide-3-griffon-eye',
        'lightning-sorceress-3-griffon-eye',
        'lightning-strike-amazon-2-griffon-eye',
        'nova-sorceress-guide-2-griffon-eye',
    }
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'] in roles]
    assert len(profiles) == 6
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_remaining_vipermagi_variant_components_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        'enchant-sorceress-1-vipermagi',
        'enchant-sorceress-2-vipermagi',
        'fist-of-the-heavens-paladin-4-vipermagi',
        'meteor-sorceress-4-vipermagi',
        'nova-sorceress-guide-1-vipermagi',
        'nova-sorceress-guide-2-vipermagi',
    }
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'] in roles]
    assert len(profiles) == 6
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_dracul_melee_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        build + '-dracul-s-grasp-dracul-alternative'
        for build in (
            'dragon-talon-assassin',
            'dream-paladin',
            'smite-paladin',
        )
    }
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'] in roles]
    assert len(profiles) == 3
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_herald_caster_shield_alternatives_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    roles = {
        build + '-herald-of-zakarum-caster-shield-alternative'
        for build in (
            'fist-of-the-heavens-paladin',
            'smite-paladin',
        )
    }
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p['id'] in roles]
    assert len(profiles) == 2
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_all_reviewed_chains_of_honor_roles_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p.get('names') == ['Chains of Honor']]
    assert len(profiles) >= 25
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_all_reviewed_fortitude_roles_have_native_cases():
    import json
    from pathlib import Path

    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    profiles = [p for p in profiles if p.get('names') == ['Fortitude']]
    assert len(profiles) >= 21
    roles = {p['id'] for p in profiles}
    cases = [case for case in CASES if roles & set(case.covers)]
    assert audit_cases(cases, profiles, {'rows': []})['missing'] == {}


def test_hoto_variant_roles_have_boundaries_for_each_legal_quality():
    from tests.pricing.knowledge.assessment.item_bank.cases.hoto_variants import CASES as HOTO

    roles = (
        'fire-blast-assassin-1-heart-oak',
        'fissure-druid-1-heart-oak',
        'fissure-druid-2-heart-oak',
        'fist-of-the-heavens-paladin-2-heart-oak',
        'gold-find-barbarian-1-heart-oak',
        'gold-find-barbarian-2-heart-oak',
        'gold-find-barbarian-3-heart-oak',
        'lightning-sentry-assassin-2-heart-oak',
        'lightning-sorceress-1-heart-oak',
        'summoner-necromancer-guide-1-heart-oak',
    )
    for role in roles:
        for quality in ('normal', 'superior', 'low_quality'):
            scenarios = {c.scenario for c in HOTO if role in c.covers and c.item.rarity == quality}
            assert scenarios >= {'positive', 'negative', 'unknown'}, (role, quality)


def test_hoto_generic_caster_roles_have_each_quality_and_uncertainty():
    from tests.pricing.knowledge.assessment.item_bank.cases.hoto_caster_roles import CASES as HOTO

    for guide in (
        'blood-boil-warlock-guide',
        'summoner-warlock-guide',
        'frozen-orb-sorceress',
        'frozen-orb-meteor-sorceress',
        'fire-wall-sorceress-guide',
        'hydra-sorceress',
    ):
        role = guide + '-heart-of-the-oak-weapon-core-caster-word-gear'
        for quality in ('normal', 'superior', 'low_quality'):
            assert {c.scenario for c in HOTO if role in c.covers and c.item.rarity == quality} >= {
                'positive',
                'negative',
                'unknown',
            }


def test_remaining_magefist_roles_have_item_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases.magefist_remaining import CASES as MAGEFIST

    roles = [
        f'{guide}-magefist-caster-progression-alternative'
        for guide in (
            'blizzard-sorceress',
            'double-throw-barbarian-guide',
            'dragon-talon-assassin',
            'echoing-strike-warlock-guide',
            'enchant-sorceress',
            'fire-blast-assassin',
            'fire-warlock-guide',
            'fissure-druid',
            'fist-of-the-heavens-paladin',
            'lightning-sentry-assassin',
            'lightning-sorceress',
            'meteor-sorceress',
            'nova-sorceress-guide',
            'wake-of-fire-assassin',
        )
    ]
    roles += [f'fissure-player-{variant}-magefist' for variant in ('standard', 'magic-find', 'ubers')]
    for role in roles:
        assert {case.scenario for case in MAGEFIST if role in case.covers} >= {'positive', 'negative', 'unknown'}


def test_spirit_endgame_variants_have_each_quality_and_uncertainty():
    from tests.pricing.knowledge.assessment.item_bank.cases.spirit_endgame import CASES as SPIRIT

    for role in (
        'hammer-standard-spirit-shield',
        'hammer-mf-spirit-shield',
        'blizzard-set-spirit-shield',
        'meteor-standard-spirit-shield',
        'meteor-mf-spirit-shield',
        'meteor-set-spirit-shield',
    ):
        for quality in ('normal', 'superior', 'low_quality'):
            assert {c.scenario for c in SPIRIT if role in c.covers and c.item.rarity == quality} >= {
                'positive',
                'negative',
                'unknown',
            }


def test_spirit_gear_and_swap_roles_have_all_quality_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import CASES as SPIRIT

    uses = {
        'blood-boil-warlock-guide': ('weapon', 'off-hand', 'off-hand-swap'),
        'summoner-warlock-guide': ('weapon', 'off-hand-swap'),
        'frozen-orb-sorceress': ('weapon', 'off-hand', 'off-hand-swap'),
        'frozen-orb-meteor-sorceress': ('weapon', 'off-hand', 'off-hand-swap'),
        'fire-wall-sorceress-guide': ('weapon', 'off-hand', 'off-hand-swap'),
        'hydra-sorceress': ('weapon', 'off-hand', 'off-hand-swap'),
        'summoner-necromancer-guide': ('weapon', 'off-hand', 'off-hand-swap'),
    }
    for guide, slots in uses.items():
        for slot in slots:
            role = f'{guide}-spirit-{slot}-core-caster-word-gear'
            for quality in ('normal', 'superior', 'low_quality'):
                assert {c.scenario for c in SPIRIT if role in c.covers and c.item.rarity == quality} >= {
                    'positive',
                    'negative',
                    'unknown',
                }


def test_softcore_facet_recipient_roles_have_boundary_and_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.facet_recipients import CASES as FACETS

    roles = [
        f'{guide}-rainbow-facet-v{variant}-{slot}-{index}-named-socket-jewel'
        for guide, variant, slot, index in (
            ('blizzard-sorceress', 1, 'weapon', 0),
            ('blizzard-sorceress', 1, 'body-armor', 0),
            ('enchant-sorceress', 1, 'body-armor', 0),
            ('enchant-sorceress', 2, 'body-armor', 0),
            ('fire-warlock-guide', 1, 'weapon', 0),
            ('fissure-druid', 3, 'helmet', 0),
            ('fist-of-the-heavens-paladin', 2, 'helmet', 0),
            ('lightning-sorceress', 3, 'helmet', 0),
            ('lightning-strike-amazon', 2, 'helmet', 0),
            ('meteor-sorceress', 4, 'weapon', 0),
            ('nova-sorceress-guide', 1, 'body-armor', 0),
        )
    ]
    roles.append('hydra-standard-fire-facet')
    for role in roles:
        assert {c.scenario for c in FACETS if role in c.covers} >= {'positive', 'negative', 'unknown'}


def test_protector_stone_softcore_uses_have_positive_negative_and_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.protector_stone_recipients import CASES as STONE

    for guide, variant, slot in (
        ('double-throw-barbarian-guide', 2, 'helmet'),
        ('gold-find-barbarian', 1, 'helmet'),
        ('gold-find-barbarian', 3, 'helmet'),
        ('mirrored-blades-warlock-guide', 1, 'weapon'),
        ('mirrored-blades-warlock-guide', 2, 'helmet'),
        ('smite-paladin', 1, 'off-hand'),
        ('smite-paladin', 2, 'helmet'),
        ('strafe-amazon', 1, 'weapon'),
        ('strafe-amazon', 2, 'weapon'),
        ('summoner-necromancer-guide', 1, 'helmet'),
        ('summoner-necromancer-guide', 2, 'helmet'),
    ):
        role = f'{guide}-protector-s-stone-v{variant}-{slot}-0-named-socket-jewel'
        assert {c.scenario for c in STONE if role in c.covers} >= {'positive', 'negative', 'unknown'}


def test_guardian_thunder_recipients_have_positive_negative_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.guardian_thunder_recipients import CASES as THUNDER

    for guide, variants in (
        ('fist-of-the-heavens-paladin', (2,)),
        ('lightning-fury-amazon-guide', (1, 2, 3)),
        ('lightning-sentry-assassin', (1, 2)),
        ('lightning-sorceress', (1, 2)),
        ('lightning-strike-amazon', (1,)),
        ('nova-sorceress-guide', (1, 2, 3)),
    ):
        for variant in variants:
            role = f'{guide}-guardian-s-thunder-v{variant}-helmet-0-named-socket-jewel'
            assert {c.scenario for c in THUNDER if role in c.covers} >= {'positive', 'negative', 'unknown'}


def test_guardian_light_echoing_uses_have_positive_negative_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.guardian_light_recipients import CASES as LIGHT

    for variant in (2, 3):
        role = f'echoing-strike-warlock-guide-guardian-s-light-v{variant}-helmet-0-named-socket-jewel'
        assert {c.scenario for c in LIGHT if role in c.covers} >= {'positive', 'negative', 'unknown'}


def test_elemental_colossal_recipients_have_positive_negative_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.elemental_colossal_recipients import CASES as JEWELS

    for guide, jewel, variants, slot in (
        ('blizzard-sorceress', 'protector-s-frost', (1, 2), 'helmet'),
        ('enchant-sorceress', 'defender-s-fire', (2,), 'helmet'),
        ('fire-warlock-guide', 'defender-s-fire', (2,), 'helmet'),
        ('meteor-sorceress', 'defender-s-fire', (1, 2), 'helmet'),
        ('poison-nova-necromancer', 'defender-s-bile', (1,), 'weapon'),
    ):
        for variant in variants:
            role = f'{guide}-{jewel}-v{variant}-{slot}-0-named-socket-jewel'
            assert {c.scenario for c in JEWELS if role in c.covers} >= {'positive', 'negative', 'unknown'}


def test_cta_caster_swaps_have_all_quality_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases.cta_caster_swaps import CASES as CTA

    for guide in (
        'blood-boil-warlock-guide',
        'summoner-warlock-guide',
        'frozen-orb-sorceress',
        'frozen-orb-meteor-sorceress',
        'fire-wall-sorceress-guide',
        'hydra-sorceress',
        'summoner-necromancer-guide',
    ):
        role = guide + '-call-to-arms-weapon-swap-core-caster-word-gear'
        for quality in ('normal', 'superior', 'low_quality'):
            assert {c.scenario for c in CTA if role in c.covers and c.item.rarity == quality} >= {
                'positive',
                'negative',
                'unknown',
            }


def test_memory_caster_swaps_have_all_quality_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases.memory_caster_swaps import CASES as MEMORY

    for guide in (
        'blizzard-sorceress',
        'enchant-sorceress',
        'meteor-sorceress',
        'nova-sorceress-guide',
        'frozen-orb-sorceress',
        'frozen-orb-meteor-sorceress',
        'fire-wall-sorceress-guide',
        'hydra-sorceress',
    ):
        suffix = (
            '-player-memory-weapon-swap-main-alternatives-word-utility-alternative'
            if guide
            in (
                'blizzard-sorceress',
                'enchant-sorceress',
                'meteor-sorceress',
                'nova-sorceress-guide',
            )
            else '-memory-caster-recipe-gear'
        )
        for quality in ('normal', 'superior', 'low_quality'):
            assert {c.scenario for c in MEMORY if guide + suffix in c.covers and c.item.rarity == quality} >= {
                'positive',
                'negative',
                'unknown',
            }


def test_obsession_caster_uses_have_all_quality_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases.obsession_caster_uses import CASES as WORD

    for guide in (
        'echoing-strike-warlock-guide',
        'fire-warlock-guide',
        'lightning-sorceress',
        'blood-boil-warlock-guide',
        'summoner-warlock-guide',
        'frozen-orb-sorceress',
        'frozen-orb-meteor-sorceress',
        'fire-wall-sorceress-guide',
        'hydra-sorceress',
    ):
        suffix = (
            '-player-obsession-weapon-main-alternatives-caster-word-remainder'
            if guide
            in (
                'echoing-strike-warlock-guide',
                'fire-warlock-guide',
                'lightning-sorceress',
            )
            else '-obsession-caster-recipe-gear'
        )
        for quality in ('normal', 'superior', 'low_quality'):
            assert {c.scenario for c in WORD if guide + suffix in c.covers and c.item.rarity == quality} >= {
                'positive',
                'negative',
                'unknown',
            }


def test_naj_puzzler_swaps_have_positive_negative_unknown_cases():
    from tests.pricing.knowledge.assessment.item_bank.cases.naj_puzzler_swaps import CASES as NAJ

    for guide in (
        'double-throw-barbarian-guide',
        'dream-paladin',
        'echoing-strike-warlock-guide',
        'fire-warlock-guide',
        'fissure-druid',
        'lightning-fury-amazon-guide',
        'lightning-strike-amazon',
        'mirrored-blades-warlock-guide',
        'poison-nova-necromancer',
        'strafe-amazon',
        'summoner-necromancer-guide',
    ):
        assert {c.scenario for c in NAJ if guide + '-naj-teleport-swap' in c.covers} >= {
            'positive',
            'negative',
            'unknown',
        }


def test_treachery_endgame_mercs_have_all_quality_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases.treachery_endgame_mercs import CASES as WORD

    for guide, variant in (
        ('dream-paladin', 0),
        ('lightning-fury-amazon-guide', 3),
        ('lightning-sorceress', 3),
        ('lightning-strike-amazon', 2),
        ('meteor-sorceress', 4),
    ):
        role = f'{guide}-{variant}-merc-treachery-native'
        for quality in ('normal', 'superior', 'low_quality'):
            assert {c.scenario for c in WORD if role in c.covers and c.item.rarity == quality} >= {
                'positive',
                'negative',
                'unknown',
            }


def test_treachery_shared_and_zeal_uses_have_all_quality_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases.treachery_shared_zeal import CASES as WORD

    for role in (
        'smite-shared-treachery',
        'zeal-paladin-treachery-fade-prebuff',
        'zeal-paladin-merc-word-treachery-end',
    ):
        for quality in ('normal', 'superior', 'low_quality'):
            assert {c.scenario for c in WORD if role in c.covers and c.item.rarity == quality} >= {
                'positive',
                'negative',
                'unknown',
            }


def test_low_tier_trade_rules_require_all_three_named_scenarios():
    tiers = {
        'rows': [
            {'quality': 'unique', 'name': name, 'tier': 'low'}
            for name in ('Stormshield', 'Reviewed candidate', 'Ordinary')
        ]
    }
    policies = [
        {
            'quality': 'unique',
            'name': 'Reviewed candidate',
            'default_tier': 'low',
            'trade_qualification': {'default_status': 'candidate'},
        }
    ]
    result = audit_cases(
        [], [], tiers, named_policies=policies, named_trade=(('unique', 'Stormshield'), ('unique', 'Excluded identity'))
    )
    assert result['missing'] == {
        'named:unique:Stormshield': ['negative', 'positive', 'unknown'],
        'named:unique:Reviewed candidate': ['negative', 'positive', 'unknown'],
    }


def test_stormshield_trade_bank_distinguishes_unknown_facts_from_illegal_variants():
    from tests.pricing.knowledge.assessment.item_bank.cases.stormshield_trade import CASES as STORMSHIELD

    tiers = {'rows': [{'quality': 'unique', 'name': 'Stormshield', 'tier': 'low'}]}
    result = audit_cases(STORMSHIELD, [], tiers, named_trade=(('unique', 'Stormshield'),))
    assert result['missing'] == {}
    assert result['orphaned_case_targets'] == []


def test_ordinary_named_trade_candidates_have_invalid_and_unknown_boundaries():
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES as BANK

    identities = [
        ('set', "Horazon's Legacy"),
        ('set', "Immortal King's Pillar"),
        ('unique', "Defender's Bile"),
        ('unique', "Protector's Frost"),
        ('unique', 'Rotting Fissure'),
    ]
    tiers = {'rows': [{'quality': q, 'name': n, 'tier': 'low'} for q, n in identities]}
    result = audit_cases(BANK, [], tiers, named_trade=identities)
    assert result['missing'] == {}


def test_known_low_tier_regressions_are_supplemental_not_orphaned_or_scope_excluded():
    item = replace(CASES[0].item, name='Ordinary', rarity='unique')
    case = replace(CASES[0], item=item, covers=('named:unique:Ordinary',), scenario='positive')
    tiers = {'rows': [{'quality': 'unique', 'name': 'Ordinary', 'tier': 'low'}]}
    result = audit_cases([case], [], tiers)
    assert result['case_coverage_complete']
    assert result['supplemental_case_targets'] == ['named:unique:Ordinary']
    assert result['scope_excluded_targets'] == []
    assert result['counts']['required_targets'] == 0
    typo = replace(case, covers=('named:unique:Ordniary',))
    assert audit_cases([typo], [], tiers)['orphaned_case_targets'] == ['named:unique:Ordniary']


def test_supplemental_regressions_cannot_hide_conditional_trade_requirements():
    item = replace(CASES[0].item, name='Conditional', rarity='unique')
    case = replace(CASES[0], item=item, covers=('named:unique:Conditional',), scenario='positive')
    tiers = {'rows': [{'quality': 'unique', 'name': 'Conditional', 'tier': 'low'}]}
    result = audit_cases([case], [], tiers, named_trade=(('unique', 'Conditional'),))
    assert result['supplemental_case_targets'] == []
    assert result['missing'] == {'named:unique:Conditional': ['negative', 'unknown']}
    assert not result['case_coverage_complete']
