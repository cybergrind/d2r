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
