"""Local English EasyOCR CPU backend; provision models separately."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from pricing.knowledge.tooltip import ROOT, parse_lines


MODELS = ('craft_mlt_25k.pth', 'english_g2.pth')


def load_reader(model_dir):
    model_dir = Path(model_dir).resolve()
    if any(not (model_dir / name).is_file() for name in MODELS):
        raise FileNotFoundError(f'Local EasyOCR models missing in {model_dir}; see pricing/knowledge/OCR.md')
    import easyocr

    return easyocr.Reader(
        ['en'],
        gpu=False,
        model_storage_directory=str(model_dir),
        user_network_directory=str(model_dir / 'user_network'),
        download_enabled=False,
        verbose=False,
    )


def normalize_results(results):
    """Keep region confidence distinct from Tesseract word confidence."""
    lines = []
    for polygon, text, confidence in results:
        xs, ys = zip(*polygon, strict=True)
        lines.append(
            {
                'text': text,
                'box': [[int(min(xs)), int(min(ys))], [int(max(xs)), int(max(ys))]],
                'polygon': [[float(x), float(y)] for x, y in polygon],
                'words': [],
                'region_confidence': float(confidence),
            }
        )
    groups = []
    for line in sorted(lines, key=lambda row: sum(point[1] for point in row['box'])):
        top, bottom = line['box'][0][1], line['box'][1][1]
        center = (top + bottom) / 2
        group = next(
            (g for g in groups if abs(center - g['center']) <= min(bottom - top, g['height']) * 0.4),
            None,
        )
        if group is None:
            groups.append({'center': center, 'height': bottom - top, 'parts': [line]})
        else:
            group['parts'].append(line)
    merged = []
    for group in groups:
        parts = sorted(group['parts'], key=lambda row: row['box'][0][0])
        merged.append(
            {
                'text': ' '.join(part['text'] for part in parts),
                'box': [
                    [min(p['box'][0][0] for p in parts), min(p['box'][0][1] for p in parts)],
                    [max(p['box'][1][0] for p in parts), max(p['box'][1][1] for p in parts)],
                ],
                'words': [],
                'region_confidence': min(p['region_confidence'] for p in parts),
                'regions': parts,
            }
        )
    return merged


def retry_regions(gray, lines, reader, *, limit=3):
    """One greedy retry per supplied uncertain line; never replace original evidence."""
    if not 0 <= limit <= 3:
        raise ValueError('Retry limit must be between 0 and 3')
    height, width = gray.shape[:2]
    observations = []
    for line in lines[:limit]:
        if not line.get('box'):
            continue
        (left, top), (right, bottom) = line['box']
        left, top = max(0, left - 4), max(0, top - 3)
        right, bottom = min(width, right + 4), min(height, bottom + 3)
        if right <= left or bottom <= top:
            continue
        recognized = reader.recognize(gray[top:bottom, left:right], detail=1, decoder='greedy', workers=0)
        observations.append(
            {
                'original_text': line['text'],
                'retry_text': ' '.join(row[1] for row in recognized),
                'box': [[left, top], [right, bottom]],
                'status': 'review_only',
                'reason': 'Retry agreement or confidence does not verify digits; inspect original pixels',
            }
        )
    return observations


def extract_image(path, *, model_dir=None, reader=None, retry_limit=0):
    from PIL import Image

    model_dir = Path(model_dir or ROOT / 'pricing/raw/ocr/easyocr').resolve()
    start = time.perf_counter()
    if reader is None:
        reader = load_reader(model_dir)
    loaded = time.perf_counter()
    path = Path(path)
    # Bytes force local input; URLs are never forwarded to EasyOCR.
    payload = path.read_bytes()
    lines = normalize_results(reader.readtext(payload, detail=1, paragraph=False, workers=0))
    recognized = time.perf_counter()
    catalog = []
    for name in ('appraisal-catalog.json', 'appraisal-trade-catalog.json'):
        catalog.extend(json.loads((ROOT / 'pricing/data' / name).read_text())['rows'])
    properties = json.loads((ROOT / 'pricing/data/appraisal-properties.json').read_text())['properties']
    result = parse_lines(lines, catalog, properties)
    with Image.open(path) as image:
        dimensions = list(image.size)
    if retry_limit:
        import numpy as np

        with Image.open(path) as image:
            gray = np.asarray(image.convert('L'))
        result['retries'] = retry_regions(gray, result['unparsed_lines'], reader, limit=retry_limit)
    result.update(
        engine='EasyOCR/CPU',
        language='en',
        raw_lines=lines,
        dimensions=dimensions,
        image_sha256=hashlib.sha256(payload).hexdigest(),
        model_sha256={name: hashlib.sha256((model_dir / name).read_bytes()).hexdigest() for name in MODELS},
        timings_ms={
            'reader_init': round((loaded - start) * 1000, 2),
            'recognition': round((recognized - loaded) * 1000, 2),
        },
    )
    result['elapsed_ms'] = round((time.perf_counter() - start) * 1000, 2)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--model-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--retry-limit', type=int, choices=range(4), default=0)
    args = parser.parse_args(argv)
    try:
        result = extract_image(args.image, model_dir=args.model_dir, retry_limit=args.retry_limit)
    except (OSError, ImportError, RuntimeError) as error:
        parser.exit(2, f'Local EasyOCR unavailable: {error}\n')
    output = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    else:
        print(output, end='')


if __name__ == '__main__':
    main()
