from pricing.knowledge.easyocr_backend import load_reader, normalize_results


def test_easyocr_preserves_region_confidence_and_geometry():
    rows = normalize_results([([[20, 30], [90, 30], [90, 50], [20, 50]], 'Kelpie Snare', 0.8)])
    assert rows[0]['text'] == 'Kelpie Snare'
    assert rows[0]['box'] == [[20, 30], [90, 50]]
    assert rows[0]['words'] == []  # Region confidence is not word confidence.
    assert rows[0]['region_confidence'] == 0.8


def test_missing_models_never_initializes_downloading_reader(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError, match='models'):
        load_reader(tmp_path)


def test_reader_disables_network_and_gpu(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace

    from pricing.knowledge.easyocr_backend import MODELS

    for name in MODELS:
        (tmp_path / name).write_bytes(b'fixture')
    calls = []

    def reader(languages, **kwargs):
        calls.append((languages, kwargs))
        return 'reader'

    monkeypatch.setitem(sys.modules, 'easyocr', SimpleNamespace(Reader=reader))
    assert load_reader(tmp_path) == 'reader'
    assert calls[0][0] == ['en']
    assert calls[0][1]['download_enabled'] is False
    assert calls[0][1]['gpu'] is False
    assert calls[0][1]['model_storage_directory'] == str(tmp_path)


def test_fragments_on_same_line_are_grouped_left_to_right():
    rows = normalize_results(
        [
            ([[110, 9], [170, 9], [170, 30], [110, 30]], 'SNARE', 0.9),
            ([[20, 11], [100, 11], [100, 31], [20, 31]], 'KELPIE', 0.8),
            ([[25, 50], [100, 50], [100, 70], [25, 70]], 'FUSCINA', 0.9),
        ]
    )
    assert [row['text'] for row in rows] == ['KELPIE SNARE', 'FUSCINA']


def test_damaged_two_hand_label_never_defaults_to_one_hand():
    from pricing.knowledge.ocr import parse_lines

    result = parse_lines(
        [{'text': text} for text in ['Fuscina', 'Twe HAND DAMAGE: 77 Te 142']],
        [{'name': 'Fuscina'}],
        {},
    )
    assert result['item']['damage'] == {'displayed': [77, 142]}


def test_supported_ocr_entry_point_uses_easyocr_without_fallback(monkeypatch):
    from pricing.knowledge import easyocr_backend, ocr

    calls = []

    def extract(path, **kwargs):
        calls.append(path)
        raise FileNotFoundError('Local EasyOCR models missing')

    monkeypatch.setattr(easyocr_backend, 'extract_image', extract)
    import pytest

    with pytest.raises(FileNotFoundError, match='EasyOCR'):
        ocr.extract_image('missing.png')
    assert calls == ['missing.png']


def test_retry_is_bounded_and_cannot_replace_original_numbers():
    from pricing.knowledge.easyocr_backend import retry_regions

    class Reader:
        def recognize(self, image, **kwargs):
            assert kwargs['decoder'] == 'greedy'
            assert image.shape == (10, 12)
            return [(None, '+3 to Life', 0.99)]

    class Image:
        shape = (10, 12)

        def __getitem__(self, slices):
            assert slices == (slice(0, 10), slice(0, 12))
            return self

    rows = [{'text': '+[3 to Life', 'box': [[0, 0], [8, 7]], 'words': []}]
    original = rows[0].copy()
    retries = retry_regions(Image(), rows, Reader(), limit=1)
    assert rows[0] == original
    assert retries[0]['original_text'] == '+[3 to Life'
    assert retries[0]['retry_text'] == '+3 to Life'
    assert retries[0]['status'] == 'review_only'
