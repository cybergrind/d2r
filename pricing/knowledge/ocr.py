"""Supported local OCR entry point: EasyOCR only, with no engine fallback."""

from pricing.knowledge.tooltip import ROOT, parse_lines  # ruff: ignore[unused-import]


def extract_image(path, **kwargs):
    from pricing.knowledge.easyocr_backend import extract_image as extract

    return extract(path, **kwargs)


def main(argv=None):
    from pricing.knowledge.easyocr_backend import main as run

    return run(argv)


if __name__ == '__main__':
    main()
