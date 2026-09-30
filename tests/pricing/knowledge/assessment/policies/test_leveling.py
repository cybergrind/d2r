from dataclasses import replace

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_leveling_uses_reviewed_identity_and_does_not_infer_trade_value():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    uses = assess_leveling(item)
    assert uses
    assert uses[0]['tier'] == 'high'
    assert uses[0]['required_level'] == 9
    assert 'price' not in uses[0]
    assert assess_leveling(replace(item, identified=None)) == []
    assert assess_leveling(replace(item, rarity='rare')) == []
    assert assess_leveling(facts('Long Sword', 'unique', 'Bloodfist')) == []


def test_set_leveling_benefits_keep_companion_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    uses = assess_leveling(facts('Leather Gloves', 'set', "Death's Hand"))
    assert uses
    assert uses[0]['status'] == 'conditional'
    assert any("Death's Guard" in c for c in uses[0]['conditions'])


def test_upgraded_or_socketed_item_does_not_inherit_original_equip_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    upgraded = upgraded_bloodfist()
    assert assess_leveling(upgraded)[0]['required_level'] is None
    socketed = replace(facts('Shako', 'unique', 'Harlequin Crest'), sockets=1, socket_contents='filled')
    # The reviewed late-caster use survives, but the filler may raise equip level.
    use = assess_leveling(socketed)[0]
    assert use['required_level'] is None
    assert use['status'] == 'conditional'


def test_leveling_report_is_highlighted_in_shared_terminal_and_osd_document():
    from inventory_tracking.appraisal.presentation import ItemAssessment
    from inventory_tracking.presentation import Tone
    from pricing.knowledge.assessment.engine import assess

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    extraction = {'item': item.to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}
    result = {
        'extraction': extraction,
        'assessment': assess(extraction, profiles=[]),
        'decision': {'price_status': 'unknown'},
    }
    doc = ItemAssessment.from_record({'state': 'complete', 'request_id': 1, 'result': result})
    lines = [line for line in doc.to_osd() if line.text.startswith('Leveling:')]
    assert lines
    assert lines[0].tone == Tone.TIER_HIGH
    assert 'high' in lines[0].text
    assert doc.to_text() == doc.to_rich().plain


def test_leveling_keeps_value_but_reports_current_wearer_level_shortfall():
    from inventory_tracking.appraisal.sections import leveling_lines
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    use = assess_leveling(item, loadout={'player_level': 5})[0]
    assert use['tier'] == 'high'
    assert use['requirements_fit']['status'] == 'unmet'
    assert use['requirements_fit']['shortfalls'] == ['Player level 5; requires 9.']
    assert 'Player level 5; requires 9.' in '\n'.join(leveling_lines({'assessment': {'leveling': [use]}}))
    ready = assess_leveling(item, loadout={'player_level': 9})[0]
    assert ready['requirements_fit']['status'] == 'met'
    unknown = assess_leveling(item)[0]
    assert unknown['requirements_fit']['status'] == 'unknown'
    upgraded = assess_leveling(upgraded_bloodfist(), loadout={'player_level': 99})[0]
    assert upgraded['requirements_fit']['status'] == 'unknown'


def test_engine_passes_player_context_to_leveling_policy():
    from pricing.knowledge.assessment.engine import assess

    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    extraction = {'item': item.to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}
    result = assess(extraction, profiles=[], loadout={'player_level': 5})
    assert result['leveling'][0]['requirements_fit']['status'] == 'unmet'


def test_leveling_uses_pinned_facts_and_recommendations_until_next_assessment(tmp_path, monkeypatch):
    from pricing.knowledge.artifacts import artifact_snapshot
    from pricing.knowledge.assessment.policies import leveling

    paths = []
    for name in ('appraisal-recommendations.json', 'appraisal-item-facts.json'):
        path = tmp_path / name
        path.write_bytes((leveling.DATA / name).read_bytes())
        paths.append(path)
    monkeypatch.setattr(leveling, 'DATA', tmp_path)
    item = facts('Heavy Gloves', 'unique', 'Bloodfist')
    with artifact_snapshot(paths):
        for path in paths:
            path.write_text('{"schema_version": 1, "rows": []}')
        assert leveling.assess_leveling(item)[0]['required_level'] == 9
    assert leveling.assess_leveling(item) == []


def upgraded_bloodfist():
    definition = named_definitions()['unique', 'Bloodfist']
    return replace(
        facts('Sharkskin Gloves', 'unique', 'Bloodfist'),
        provenance={'capture': {'item_identity': {'table': 'unique', 'table_id': definition['table_id']}}},
    )


def test_amazon_guide_only_twitchthroe_keeps_leveling_value_and_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    item = facts('Studded Leather', 'unique', 'Twitchthroe')
    uses = assess_leveling(item, loadout={'player_level': 1})
    guide = next(u for u in uses if u['source']['id'] == 'leveling-amazon')
    assert guide['tier'] == 'high'
    assert guide['classes'] == ['amazon']
    assert guide['requirements_fit']['status'] == 'unmet'
    assert any('shield' in c for c in guide['conditions'])
    assert 'price' not in guide
    assert not assess_leveling(replace(item, identified=False))


def test_titans_leveling_use_keeps_real_equip_gates_and_variant_uncertainty():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    item = facts('Ceremonial Javelin', 'unique', "Titan's Revenge")
    use = next(u for u in assess_leveling(item, loadout={'player_level': 41}) if u['source']['id'] == 'leveling-amazon')
    assert use['tier'] == 'high'
    assert use['required_level'] == 42
    assert use['requirements_fit']['status'] == 'unmet'
    assert use['requirements']['dexterity'] == 109
    eth = next(u for u in assess_leveling(replace(item, ethereal=True)) if u['source']['id'] == 'leveling-amazon')
    assert eth['requirements'] == {'level': 42, 'strength': 15, 'dexterity': 99}
    assert eth['requirements_fit']['status'] == 'unknown'
    assert any('attack speed' in c.lower() for c in eth['conditions'])


def test_cow_king_guide_combination_is_conditional_for_each_piece():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for name, base, level in [
        ("Cow King's Hide", 'Studded Leather', 18),
        ("Cow King's Hooves", 'Heavy Boots', 13),
        ("Cow King's Horns", 'War Hat', 25),
    ]:
        item = facts(base, 'set', name)
        uses = assess_leveling(item)
        guide = next(u for u in uses if u['source']['id'] == 'leveling-amazon')
        assert guide['tier'] == 'med'
        assert guide['status'] == 'conditional'
        assert guide['required_level'] == level
        assert any('single piece' in c for c in guide['conditions'])
        assert not assess_leveling(replace(item, ethereal=True))
        assert not assess_leveling(replace(item, identified=False))


def test_movement_boots_keep_standalone_guide_use_and_native_equip_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for name, base, level in [("Hsarus' Iron Heel", 'Chain Boots', 3), ("Sander's Riprap", 'Heavy Boots', 20)]:
        item = facts(base, 'set', name)
        uses = assess_leveling(item, loadout={'player_level': level - 1})
        guides = {u['source']['id']: u for u in uses if u['source']['id'].startswith('leveling-')}
        assert set(guides) == {
            'leveling-' + c
            for c in ['amazon', 'assassin', 'barbarian', 'druid', 'necromancer', 'paladin', 'sorceress', 'warlock']
        }
        for source, guide in guides.items():
            assert guide['required_level'] == level
            assert guide['requirements_fit']['status'] == 'unmet'
            assert guide['status'] == (
                'conditional' if source in ('leveling-barbarian', 'leveling-paladin') else 'recommended'
            )
            assert not any('second' in c.lower() or 'piece' in c.lower() for c in guide['conditions'])
            assert 'price' not in guide
        assert not assess_leveling(replace(item, identified=False))
        assert not assess_leveling(replace(item, ethereal=True))


def test_druid_paladin_caster_alternatives_keep_actual_level_and_variant_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for name, base, level in [
        ('Spectral Shard', 'Blade', 25),
        ('Suicide Branch', 'Burnt Wand', 33),
        ('Skin of the Vipermagi', 'Serpentskin Armor', 29),
        ('Magefist', 'Light Gauntlets', 23),
    ]:
        item = facts(base, 'unique', name)
        uses = assess_leveling(item, loadout={'player_level': 18})
        for cls in ('druid', 'paladin'):
            guide = next((u for u in uses if u['source']['id'] == 'leveling-' + cls), None)
            assert guide is not None
            assert guide['archetypes'] == ['caster']
            assert guide['required_level'] == level
            assert guide['requirements_fit']['status'] == 'unmet'
            assert guide['status'] == 'conditional'
            assert 'price' not in guide
        variant = assess_leveling(replace(item, ethereal=True))
        assert all(u['required_level'] == level for u in variant)
        assert all(u['requirements_fit']['status'] == 'unknown' for u in variant)
        assert not assess_leveling(replace(item, identified=False))


def test_assassin_pair_and_armor_leveling_remains_conditional_without_price():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for base, rarity, name, level in (
        ('Leather Gloves', 'set', "Death's Hand", 6),
        ('Sash', 'set', "Death's Guard", 6),
        ('Studded Leather', 'unique', 'Twitchthroe', 16),
    ):
        item = facts(base, rarity, name)
        uses = assess_leveling(item)
        row = next(r for r in uses if r['source']['id'] == 'leveling-assassin')
        assert row['tier'] == 'high'
        assert row['status'] == 'conditional'
        assert row['required_level'] == level
        assert 'price' not in row
        assert row['requirements_fit']['status'] == 'unknown'
        assert not assess_leveling(replace(item, identified=None))
        if rarity == 'set':
            assert not assess_leveling(replace(item, ethereal=True))
            assert any("Death's Hand" in c or 'pair' in c for c in row['conditions'])
        else:
            assert any('shield' in c for c in row['conditions'])


def test_assassin_skill_items_keep_native_equip_levels_and_conditional_advice():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for base, name, level in (
        ('Ring', 'The Stone of Jordan', 29),
        ('Amulet', 'The Eye of Etlich', 15),
        ('Serpentskin Armor', 'Skin of the Vipermagi', 29),
        ('Light Gauntlets', 'Magefist', 23),
    ):
        item = facts(base, 'unique', name)
        use = next(r for r in assess_leveling(item) if r['source']['id'] == 'leveling-assassin')
        assert use['required_level'] == level
        assert use['tier'] == 'high'
        assert use['status'] == 'conditional'
        assert 'price' not in use
        assert not assess_leveling(replace(item, identified=None))
        young = next(
            r
            for r in assess_leveling(item, loadout={'player_level': level - 1})
            if r['source']['id'] == 'leveling-assassin'
        )
        assert young['requirements_fit']['status'] == 'unmet'


def test_assassin_guide_aliases_reach_canonical_named_leveling_policy():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for base, name, level in [('Ring', 'Raven Frost', 45), ('Amulet', "Mara's Kaleidoscope", 67)]:
        item = facts(base, 'unique', name)
        use = next(r for r in assess_leveling(item) if r['source']['id'] == 'leveling-assassin')
        assert use['required_level'] == level
        assert use['tier'] == 'high'
        assert use['status'] == 'conditional'
        assert 'price' not in use
        assert not assess_leveling(replace(item, identified=None))


def test_early_melee_and_general_gloves_reach_runtime_with_native_requirements():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for base, name, quality, level in (
        ('Leather Gloves', "Death's Hand", 'set', 6),
        ('Sash', "Death's Guard", 'set', 6),
        ('Heavy Gloves', 'Bloodfist', 'unique', 9),
    ):
        item = facts(base, quality, name)
        for cls in ('barbarian', 'paladin'):
            row = next((r for r in assess_leveling(item) if r['source']['id'] == 'leveling-' + cls), None)
            assert row is not None
            assert row['required_level'] == level
            assert row['status'] == 'conditional'
            assert 'price' not in row
            if name == 'Bloodfist':
                assert row['archetypes'] == ['general']
                assert 'entire leveling' in row['reason']
            else:
                assert row['archetypes'] == ['melee']
                assert any('both pieces' in c for c in row['conditions'])


def test_caster_tail_uses_native_levels_and_does_not_treat_respec_as_equip_level():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for cls, base, name, level in (
        ('barbarian', 'Serpentskin Armor', 'Skin of the Vipermagi', 29),
        ('barbarian', 'Light Gauntlets', 'Magefist', 23),
        ('barbarian', 'Amulet', 'The Eye of Etlich', 15),
        ('barbarian', 'Ring', 'The Stone of Jordan', 29),
        ('barbarian', 'Slayer Guard', "Arreat's Face", 42),
        ('paladin', 'Amulet', 'The Eye of Etlich', 15),
        ('paladin', 'Ring', 'The Stone of Jordan', 29),
        ('druid', 'Amulet', 'The Eye of Etlich', 15),
        ('druid', 'Ring', 'The Stone of Jordan', 29),
        ('druid', 'Grim Shield', 'Lidless Wall', 41),
        ('druid', 'Totemic Mask', "Jalal's Mane", 42),
    ):
        item = facts(base, 'unique', name)
        source = 'leveling-' + cls
        row = next((r for r in assess_leveling(item) if r['source']['id'] == source), None)
        assert row is not None
        assert row['required_level'] == level
        assert row['archetypes'] == ['caster']
        assert row['status'] == 'conditional'
        assert 'price' not in row
        young = next(
            r for r in assess_leveling(item, loadout={'player_level': level - 1}) if r['source']['id'] == source
        )
        assert young['requirements_fit']['status'] == 'unmet'
        assert not assess_leveling(replace(item, identified=None))


def test_verified_empty_sockets_preserve_named_equip_requirements():
    """Empty holes add neither socketed-item level nor requirement modifiers."""
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for base, name, count, level, strength in (
        ('Round Shield', "Moser's Blessed Circle", 2, 31, 53),
        ('Gothic Shield', 'The Ward', 1, 26, 60),
    ):
        item = replace(facts(base, 'unique', name), sockets=count, socket_contents='empty')
        context = {'player_level': level, 'player_strength': strength, 'player_dexterity': 0}
        uses = assess_leveling(item, loadout=context)
        assert uses
        assert all(use['requirements_fit']['status'] == 'met' for use in uses)
        assert all(use['required_level'] == level for use in uses)
        for uncertain in (
            replace(item, socket_contents='unknown'),
            replace(item, socket_contents='filled'),
            replace(item, socket_contents='filled', filled_sockets=0, empty_sockets=count),
            replace(item, socket_items=[{'name': 'Hel Rune'}]),
            replace(item, sockets=None),
        ):
            assert all(use['required_level'] is None for use in assess_leveling(uncertain, loadout=context))


def test_ethereal_named_requirements_use_native_order_without_double_reduction():
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    for base, name, sockets, level, strength, dexterity in (
        ('Mesh Armor', 'Shaftstop', 0, 38, 82, 0),
        ('Ogre Axe', 'Bonehew', 2, 64, 185, 65),
        ('Great Maul', 'Steeldriver', 0, 29, 40, 0),
    ):
        item = replace(facts(base, 'unique', name), ethereal=True, sockets=sockets)
        context = {
            'player_level': level,
            'player_strength': strength,
            'player_dexterity': dexterity,
            'mercenary_level': level,
            'mercenary_strength': strength,
            'mercenary_dexterity': dexterity,
        }
        uses = assess_leveling(item, loadout=context)
        assert uses
        for use in uses:
            assert use['requirements'] == {'level': level, 'strength': strength, 'dexterity': dexterity}
            assert use['requirements_fit']['status'] == 'met'
        for uncertain in (replace(item, ethereal=None), replace(item, socket_contents='unknown')):
            assert all(use['required_level'] is None for use in assess_leveling(uncertain, loadout=context))


def test_inherently_ethereal_requirement_is_not_reduced_twice():
    from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
    from pricing.knowledge.assessment.mechanics.equipment import named_requirements

    item = replace(facts('Silver-edged Axe', 'unique', 'Ethereal Edge'), ethereal=True)
    definition, _ = resolve_named_definition(item)
    reviewed = {'level': 74, 'strength': 156, 'dexterity': 55}
    assert named_requirements(item, definition, reviewed) == reviewed
    assert named_requirements(replace(item, ethereal=False), definition, reviewed) == {}


def test_ordinary_leveling_recommendations_stay_out_of_value_focused_report():
    from inventory_tracking.appraisal.sections import leveling_lines
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    uses = assess_leveling(facts('Field Plate', 'unique', 'Rockfleece'))
    assert uses
    assert all(use['tier'] in ('med', 'low') for use in uses)
    assert leveling_lines({'assessment': {'leveling': uses}}) == []


def test_top_leveling_highlight_keeps_companion_conditions():
    from inventory_tracking.appraisal.sections import leveling_lines
    from pricing.knowledge.assessment.policies.leveling import assess_leveling

    uses = assess_leveling(facts('Leather Gloves', 'set', "Death's Hand"))
    lines = leveling_lines({'assessment': {'leveling': uses}})
    assert any(line.startswith('Leveling: high') for line in lines)
    assert any("Death's Guard" in line for line in lines)
