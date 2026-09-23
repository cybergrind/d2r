from pathlib import Path

import pytest

from pricing.knowledge.ocr import extract_image, parse_lines


CATALOG = [{'name': 'Cinquedeas', 'base_code': 'verified-from-fixture'}]
PROPERTIES = {'1577': {'labels': ['+{{value}} to Sigil: Death (Warlock Only)'], 'types': ['number']}}
TEXT = [
    '77 CINQUEDEAS 2',
    '@ne-HAND DamAGeE: 15 Te 31',
    'DURABILITY: 14 @F 24',
    'REQUIRED DEXTERITY: 73',
    'REQUIRED STRENGTH: 21',
    'REQUIRED LEVEL: 25',
    'DAGGER CLASS - VERY FAST ATTACK SPEED',
    '*3 Toe SIGIL: DEATH (WARLOCK ONLY)',
    'SeckeTeD (3)',
    'SHIFT LEFT CLICK TO EQUIP',
]


def lines(text):
    return [{'text': line, 'words': [], 'box': [[0, 0], [100, 20]]} for line in text]


def test_tooltip_grammar_and_catalog_property_mapping():
    result = parse_lines(lines(TEXT), CATALOG, PROPERTIES)
    assert result['item']['name'] == 'Cinquedeas'
    assert result['item']['damage']['one_hand'] == [15, 31]
    assert result['item']['durability'] == {'current': 14, 'maximum': 24}
    assert result['item']['requirements'] == {'dexterity': 73, 'strength': 21, 'level': 25}
    assert result['item']['sockets'] == 3
    assert result['item']['affixes'][0]['property_id'] == '1577'
    assert result['item']['ethereal'] is None
    assert result['item']['rarity'] is None
    assert result['item']['socket_contents'] is None


def test_ambiguous_digits_are_not_repaired_or_sent_to_appraisal():
    result = parse_lines(lines([line.replace('15 Te 31', 'I5 Te 3l') for line in TEXT]), CATALOG, PROPERTIES)
    assert result['item']['damage'] == {}
    assert result['status'] == 'needs_review'
    assert any('I5' in row['text'] for row in result['unparsed_lines'])
    assert result['appraisal_ready'] is False


def test_unknown_affix_is_preserved_and_never_mapped_by_similarity():
    result = parse_lines(lines([line.replace('DEATH', 'DEATX') for line in TEXT]), CATALOG, PROPERTIES)
    assert result['item']['affixes'] == []
    assert any('DEATX' in row['text'] for row in result['unparsed_lines'])


def test_duplicate_conflicting_values_fail_closed():
    result = parse_lines(lines([*TEXT[:-1], 'SOCKETED (2)']), CATALOG, PROPERTIES)
    assert result['item']['sockets'] is None
    assert any('conflict' in issue for issue in result['review'])


def test_affix_sign_is_not_silently_discarded():
    result = parse_lines(lines([line.replace('*3', '-3') for line in TEXT]), CATALOG, PROPERTIES)
    assert result['item']['affixes'] == []
    assert any('-3' in row['text'] for row in result['unparsed_lines'])


@pytest.mark.parametrize(
    ('defense_lines', 'expected'),
    [(['DEFENSE: 26'], 26), (['DEFENSE: 26', 'DEFENSE: 28', 'DEFENSE: 26'], None), (['DEFENSE: 2G'], None)],
)
def test_armor_defense_is_extracted_without_repairing_ambiguous_values(defense_lines, expected):
    result = parse_lines(
        lines(['CIRCLET', *defense_lines, 'DURABILITY: 22 @F 35', 'REQUIRED LeveL: 16']),
        [{'name': 'Circlet'}],
        {},
    )
    assert result['item']['defense'] == expected
    assert result['item']['durability'] == {'current': 22, 'maximum': 35}
    assert result['item']['requirements'] == {'level': 16}
    if expected is not None:
        assert not result['unparsed_lines']
    elif len(defense_lines) > 1:
        assert any('conflict' in issue for issue in result['review'])
    else:
        assert any('2G' in row['text'] for row in result['unparsed_lines'])


def test_actual_screenshot_offline():
    pytest.importorskip('easyocr')
    root = Path(__file__).resolve().parents[3]
    model = root / 'pricing/raw/ocr/easyocr'
    if not (model / 'english_g2.pth').exists():
        pytest.skip('Optional local English OCR model is not installed')
    image = Path(__file__).parent / 'fixtures/cinquedeas.png'
    if not image.is_file():
        pytest.skip('Optional local OCR screenshot is not installed')
    result = extract_image(image, model_dir=model)
    assert result['item']['name'] == 'Cinquedeas'
    assert result['item']['requirements']['level'] == 25
    assert result['item']['sockets'] == 3
    assert result['offline'] is True
    assert result['appraisal_ready'] is False  # Confidence is not automatic approval.


def test_actual_circlet_screenshot_offline():
    pytest.importorskip('easyocr')
    root = Path(__file__).resolve().parents[3]
    model = root / 'pricing/raw/ocr/easyocr'
    if not (model / 'english_g2.pth').exists():
        pytest.skip('Optional local English OCR model is not installed')
    image = Path(__file__).parent / 'fixtures/circlet.png'
    if not image.is_file():
        pytest.skip('Optional local OCR screenshot is not installed')
    result = extract_image(image, model_dir=model)
    assert result['item']['name'] == 'Circlet'
    assert result['item']['defense'] in (None, 26)
    # Baseline recognition may abstain; it must never accept a different value.
    assert result['item']['durability'] in (None, {'current': 22, 'maximum': 35})
    assert result['item']['requirements'].get('level') in (None, 16)
    assert result['item']['sockets'] is None
    assert result['item']['rarity'] is None
    assert result['item']['ethereal'] is None
    assert result['offline'] is True
    assert result['appraisal_ready'] is False


def test_rare_title_is_not_a_runeword_substring():
    catalog = [{'name': 'Stone'}, {'name': 'Amulet', 'base_code': 'fixture-amulet'}]
    result = parse_lines(lines(['Stone Necklace', 'Amulet', 'Required Level: 37']), catalog, {})
    assert result['item']['name'] == 'Amulet'
    assert result['item']['observed_title'] == 'Stone Necklace'
    assert result['item']['base_code'] == 'fixture-amulet'


def test_unique_title_and_base_are_resolved_separately():
    catalog = [{'name': 'Kelpie Snare'}, {'name': 'Fuscina', 'base_code': 'fixture-fuscina'}]
    result = parse_lines(lines(['Kelpie Snare', 'Fuscina', 'Required Level: 33']), catalog, {})
    assert result['item']['name'] == 'Kelpie Snare'
    assert result['item']['base_name'] == 'Fuscina'
    assert result['item']['base_code'] == 'fixture-fuscina'
    assert not result['unparsed_lines']


def test_distant_background_header_is_not_item_title():
    rows = [
        {'text': 'Shared Gems', 'box': [[0, 0], [100, 10]]},
        {'text': 'Cinquedeas', 'box': [[0, 100], [100, 120]]},
    ]
    assert parse_lines(rows, CATALOG, {})['item']['observed_title'] == 'Cinquedeas'


def test_elemental_range_requires_two_unambiguous_numbers():
    result = parse_lines(lines(['Cinquedeas', 'Adds 1-16 Lightning Damage', 'Adds T-6 Fire Damage']), CATALOG, {})
    assert result['item']['elemental_damage'] == {'lightning': [1, 16]}
    assert any('T-6' in row['text'] for row in result['unparsed_lines'])
