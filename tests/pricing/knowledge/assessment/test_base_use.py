from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.base_use import assess_runeword_base


def capture(name='Giant Thresher', *, sockets=4, ethereal=True, quality='superior', ed=15, ar=3, contents='empty'):
    base = next(b for b in metadata()['bases'].values() if b['name'] == name)
    return {
        'item': {
            'name': name,
            'base_name': name,
            'base_code': base['code'],
            'rarity': quality,
            'identified': True,
            'ethereal': ethereal,
            'sockets': sockets,
            'socket_contents': contents,
        },
        'source': {'stat_capture_complete': True},
        'decoded_stats': [
            {'status': 'decoded', 'value': value, 'memory_stat': {'id': stat, 'layer': 0, 'raw': value}}
            for stat, value in [(17, ed), (18, ed), (19, ar)]
        ],
    }


def word(rows, name):
    return next(r for r in rows if r['runeword'] == name)


def test_perfect_preferred_merc_base_and_imperfect_alternative():
    result = word(assess_runeword_base(normalize(capture())), 'Infinity')
    assert result['status'] == 'perfect preferred base'
    assert '15% Enhanced Damage' in ' '.join(result['strengths'])
    assert 'attack-speed' in result['tradeoff']
    result = word(
        assess_runeword_base(normalize(capture('Cryptic Axe', ethereal=False, quality='normal', ed=0, ar=0))), 'Insight'
    )
    assert result['status'] == 'usable alternative'
    assert any('Ethereal' in s and 'cannot' in s for s in result['missing'])
    assert any('optional' in s for s in result['missing'])


def test_legality_socket_paths_and_missing_evidence_never_claim_perfection():
    rows = assess_runeword_base(normalize(capture('Mancatcher')))
    assert 'Insight' not in {r['runeword'] for r in rows}
    assert word(rows, 'Infinity')['status'] == 'perfect preferred base'
    blocked = word(assess_runeword_base(normalize(capture(sockets=5))), 'Infinity')
    assert blocked['status'] == 'wrong socket count'
    assert any('cannot' in s for s in blocked['missing'])
    blank = word(assess_runeword_base(normalize(capture(sockets=0))), 'Infinity')
    assert any('Larzuk' in s and 'item level' in s for s in blank['missing'])
    assert any('Superior' in s and 'cube' in s for s in blank['missing'])
    unknown = capture()
    unknown['source'] = {}
    assert word(assess_runeword_base(normalize(unknown)), 'Infinity')['status'] != 'perfect preferred base'
    assert assess_runeword_base(normalize(capture(quality='magic'))) == []
    filled = word(assess_runeword_base(normalize(capture(contents='filled'))), 'Infinity')
    assert any('destroys' in s for s in filled['missing'])


def test_player_roles_do_not_inherit_mercenary_ethereal_preferences():
    grief = word(assess_runeword_base(normalize(capture('Phase Blade', sockets=5, ethereal=False))), 'Grief')
    assert grief['status'] == 'perfect preferred base'
    assert not grief['missing']
    spirit = word(
        assess_runeword_base(normalize(capture('Monarch', ethereal=False, quality='normal', ed=0, ar=0))), 'Spirit'
    )
    assert '156' in ' '.join(spirit['strengths'])
    assert not any('Prefer an ethereal' in s for s in spirit['missing'])
    armor = word(assess_runeword_base(normalize(capture('Archon Plate', ethereal=False))), 'Fortitude')
    assert any('ethereal' in s for s in armor['missing'])
    assert armor['status'] != 'perfect preferred base'


def test_unsocketed_superior_phase_blade_cannot_be_prepared_for_grief():
    result = word(assess_runeword_base(normalize(capture('Phase Blade', sockets=0, ethereal=False))), 'Grief')
    assert result['status'] == 'cannot prepare this base'


def test_report_deduplicates_shared_needs_and_highlights_perfect_bases():
    from inventory_tracking.appraisal.text import base_lines, roll_styles

    assessment = {'uses': assess_runeword_base(normalize(capture()))}
    text = '\n'.join(base_lines(assessment))
    assert text.count('Perfect superior damage') == 1
    styles = roll_styles({'result': {'base_assessment': assessment}})
    assert styles['Infinity / Act 2 mercenary: perfect preferred base'] == 'bold bright_green'
    alternatives = word(assess_runeword_base(normalize(capture('Cryptic Axe'))), 'Infinity')['alternatives']
    assert 'Matriarchal Bow' not in alternatives
    assert 'Maiden Spear' not in alternatives


def test_self_wield_scythe_recommendation_is_not_a_preferred_mercenary_base():
    rows = assess_runeword_base(normalize(capture('Scythe', sockets=4, quality='normal', ethereal=False, ed=0, ar=0)))
    infinity = [r for r in rows if r['runeword'] == 'Infinity']
    merc = next(r for r in infinity if r['role'] == 'Act 2 mercenary')
    player = next(r for r in infinity if r['role'] == 'Nova player caster')
    assert merc['status'] == 'usable alternative'
    assert player['status'] == 'preferred base'
    assert not any('mercenary damage' in s or '15%' in s or '+3 superior' in s for s in player['missing'])
    blank = assess_runeword_base(normalize(capture('Scythe', sockets=0, quality='normal', ethereal=False)))
    assert next(r for r in blank if r['role'] == 'Nova player caster')['status'] == 'needs sockets'


def test_archon_fortitude_has_separate_player_and_mercenary_ethereal_advice():
    rows = assess_runeword_base(normalize(capture('Archon Plate', sockets=4, ethereal=False)))
    fort = [r for r in rows if r['runeword'] == 'Fortitude']
    merc = next(r for r in fort if r['role'] == 'mercenary')
    player = next(r for r in fort if r['role'] == 'player')
    assert any('ethereal mercenary' in s for s in merc['missing'])
    assert not any('ethereal mercenary' in s for s in player['missing'])
    assert 'Non-ethereal suits player use.' in player['strengths']


def test_perfect_base_requires_complete_identified_capture_and_superior_quality():
    from dataclasses import replace

    item = normalize(capture())
    for changed in (
        replace(item, capture_complete=False, gaps=[]),
        replace(item, identified=None, gaps=[]),
        replace(item, identified=False, gaps=[]),
        replace(item, rarity='normal', gaps=[]),
    ):
        result = word(assess_runeword_base(changed), 'Infinity')
        assert result['status'] != 'perfect preferred base'


def test_conflicting_native_rolls_do_not_produce_perfect_strength_claims():
    from dataclasses import replace

    item = normalize(capture())
    item = replace(item, gaps=['Duplicate native stat 17:0.', 'Duplicate native stat 19:0.'])
    result = word(assess_runeword_base(item), 'Infinity')
    assert not any('Perfect superior' in value for value in result['strengths'])
    grief = replace(normalize(capture('Phase Blade', sockets=5, ethereal=False)), gaps=item.gaps)
    assert not any('Perfect superior' in value for value in word(assess_runeword_base(grief), 'Grief')['strengths'])


def test_spirit_swords_keep_caster_priorities_separate_from_melee_premiums():
    for base in ('Crystal Sword', 'Broad Sword', 'Long Sword'):
        for ethereal in (True, False, None):
            result = word(
                assess_runeword_base(
                    normalize(
                        capture(
                            base,
                            quality='normal',
                            ethereal=ethereal,
                            ed=0,
                            ar=0,
                        )
                    )
                ),
                'Spirit',
            )
            assert result['role'] == 'Spirit player caster'
            assert result['ethereal_preference']['preference'] == 'neutral'
            assert result['status'] == ('preferred base' if base == 'Crystal Sword' else 'usable alternative')
            assert not any('premium' in line or 'Attack Rating' in line for line in result['missing'])
            assert any('wearer' in line for line in result['missing'])
            if ethereal is None:
                assert any('Ethereal status' in line for line in result['missing'])
            if ethereal:
                assert 'cannot be repaired' in result['tradeoff']
    blank = word(assess_runeword_base(normalize(capture('Crystal Sword', sockets=0))), 'Spirit')
    assert any('item level' in line for line in blank['missing'])
    wrong = word(assess_runeword_base(normalize(capture('Crystal Sword', sockets=5))), 'Spirit')
    assert wrong['status'] == 'wrong socket count'
    assert not assess_runeword_base(normalize(capture('Crystal Sword', quality='magic')))


def test_call_to_arms_prebuff_bases_preserve_preparation_and_staffmod_gaps():
    from dataclasses import replace

    for base in ('Crystal Sword', 'Flail', 'War Scepter'):
        facts = normalize(capture(base, sockets=5))
        result = word(assess_runeword_base(facts), 'Call to Arms')
        assert result['role'] == 'player prebuff'
        assert result['status'] == 'preferred base'
        assert result['ethereal_preference']['preference'] == 'neutral'
        assert not any('premium' in line or '15%' in line for line in result['missing'])
        assert 'cannot be repaired' in result['tradeoff']
        if base == 'War Scepter':
            assert any('staffmods' in line for line in result['missing'])
        assert result['status'] != 'perfect preferred base'
        blank = normalize(capture(base, sockets=0))
        high = word(assess_runeword_base(replace(blank, item_level=50)), 'Call to Arms')
        assert high['status'] == ('cannot prepare this base' if base == 'Crystal Sword' else 'needs sockets')
        low = word(assess_runeword_base(replace(blank, item_level=20)), 'Call to Arms')
        assert low['status'] == 'cannot prepare this base'
    filled = word(assess_runeword_base(normalize(capture('Flail', sockets=5, contents='filled'))), 'Call to Arms')
    assert filled['status'] == 'needs empty sockets'
    assert filled['strengths'] == []


def test_heart_of_the_oak_flail_keeps_charge_and_socket_limits():
    from dataclasses import replace

    for ethereal in (True, False, None):
        result = word(assess_runeword_base(normalize(capture('Flail', ethereal=ethereal))), 'Heart of the Oak')
        assert result['status'] == 'preferred base'
        assert result['role'] == 'Heart of the Oak player caster'
        assert 'charges' in result['tradeoff']
        assert any('wearer' in s for s in result['missing'])
        if ethereal:
            assert 'cannot be recharged' in result['tradeoff']
        if ethereal is None:
            assert any('Ethereal status' in s for s in result['missing'])
    superior = replace(normalize(capture('Flail', sockets=0)), item_level=50)
    assert word(assess_runeword_base(superior), 'Heart of the Oak')['status'] == 'cannot prepare this base'
    normal = replace(superior, rarity='normal')
    result = word(assess_runeword_base(normal), 'Heart of the Oak')
    assert result['status'] == 'needs sockets'
    assert any('16.7%' in s for s in result['missing'])
    assert 'Heart of the Oak' not in {r['runeword'] for r in assess_runeword_base(normalize(capture('Crystal Sword')))}


def test_specialist_caster_bases_do_not_infer_staffmods_after_normalization():
    for name, base, sockets in [('Leaf', 'Short Staff', 2), ('Memory', 'Battle Staff', 4), ('White', 'Bone Wand', 2)]:
        result = word(assess_runeword_base(normalize(capture(base, sockets=sockets, ethereal=False))), name)
        assert result['status'] == 'preferred base'
        assert any('staffmods' in s for s in result['missing'])
        assert result['status'] != 'perfect preferred base'
        if name in ('Leaf', 'Memory'):
            assert 'two-handed' in result['tradeoff']
        low = word(assess_runeword_base(normalize(capture(base, sockets=0, quality='low_quality'))), name)
        assert low['strengths'] == []
        assert any('staffmods' in s and 'not assumed' in s for s in low['missing'])
        assert low['status'] == 'needs normalization and sockets'
        if name == 'Memory':
            assert any('socket cap becomes 4' in s for s in low['missing'])
    assert not assess_runeword_base(normalize(capture('Bone Wand', sockets=2, quality='magic')))


def test_treachery_mage_plate_retains_player_and_mercenary_durability_tradeoffs():
    for ethereal in (True, False, None):
        rows = [
            r
            for r in assess_runeword_base(
                normalize(
                    capture(
                        'Mage Plate',
                        sockets=3,
                        ethereal=ethereal,
                    )
                )
            )
            if r['runeword'] == 'Treachery'
        ]
        assert {r['role'] for r in rows} == {'mercenary', 'player'}
        by_role = {r['role']: r for r in rows}
        assert by_role['mercenary']['ethereal_preference']['preference'] == 'preferred'
        assert by_role['player']['ethereal_preference']['preference'] == 'avoid'
        assert all(r['status'] == 'preferred base' for r in rows)
        assert all(any('defense' in s and 'requirements' in s for s in r['missing']) for r in rows)
        assert all('Fade' in r['tradeoff'] for r in rows)
        if ethereal is True:
            assert any('non-ethereal' in s for s in by_role['player']['missing'])
        if ethereal is False:
            assert any('ethereal mercenary' in s for s in by_role['mercenary']['missing'])
        if ethereal is None:
            assert all(any('Ethereal status' in s for s in r['missing']) for r in rows)
    filled = [
        r
        for r in assess_runeword_base(
            normalize(
                capture(
                    'Mage Plate',
                    sockets=3,
                    contents='filled',
                )
            )
        )
        if r['runeword'] == 'Treachery'
    ]
    assert len(filled) == 2
    assert all(r['status'] == 'needs empty sockets' and not r['strengths'] for r in filled)
