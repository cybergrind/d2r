# Local screenshot preprocessing

The prototype uses **PyOCR's libtesseract C-API backend**, Pillow, and a local
English Tesseract model. It makes no network requests. The new stage is separate
from market lookup:

```text
Screenshot -> local OCR with word boxes -> tooltip grammar + catalog validation
           -> structured draft + uncertain fields -> visual review -> appraisal
```

For the greatest workflow benefit, run this in the upload handler before sending
the appraisal request to a model. Attach compact JSON and the original image.
Running another tool after the model already sees an easy tooltip may add latency;
local OCR timing alone cannot establish end-to-end improvement.

## Run

```sh
uv run --extra ocr python -m pricing.knowledge.ocr /path/to/item.png
uv run --extra ocr python -m pricing.knowledge.ocr /path/to/item.png \
  --diagnostics tmp/item-ocr/review --full
```

`--diagnostics` saves field crops, original OCR text, word boxes/confidences and
structured evidence. The normal output keeps the item fields and review flags.
This is a transcription draft, not an automatic appraisal: `appraisal_ready` is
deliberately false until another step reviews the image and unresolved fields.

Optional Python dependencies are in the `ocr` extra. Tesseract's native library
must also be installed. The model is provisioned separately, never downloaded
implicitly while parsing an image:

```sh
mkdir -p pricing/raw/ocr/tessdata
curl -fsSL https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata \
  -o pricing/raw/ocr/tessdata/eng.traineddata
sha256sum pricing/raw/ocr/tessdata/eng.traineddata
```

Tested model SHA-256:
`7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
Use `--tessdata DIR` for a different local model location. The output records the
actual model and image hashes. A changed model requires renewed fixture testing.

## What the experiment established

On the supplied Cinquedeas screenshot, the parser extracts:

- Damage 15–31; durability 14/24.
- Dexterity 73, strength 21, required level 25.
- Three sockets; +3 to Sigil: Death, mapped to local property 1577.
- Name and verified base code from the local catalog.

The source and measurements are in
[appraisal-ocr-experiment-2026-09-23.json](../data/appraisal-ocr-experiment-2026-09-23.json).
Raw PyOCR/C-API recognition initially took about 335 ms; the complete extraction
stage took roughly half a second on this machine. This is one screenshot, not a
representative accuracy or speed benchmark.

Preprocessing was not consistently beneficial: maximum-channel thresholding
changed 31 damage to 3; enlarging a crop produced `I5`, `3l` and `2]`; an unscaled
crop dropped the gray name. Therefore the implemented first pass preserves the
original pixels. Alternative preprocessing must be compared against the original,
and numeric disagreements require review.

PyOCR's command-line backend failed in this machine's isolated model directory
because hOCR configuration was absent. The C-API backend succeeded without those
config files, so selection is explicit rather than relying on discovery order.

## Safety and current scope

- One English tooltip per screenshot; text-box segmentation and multiple-item
  screenshots are not solved by this prototype.
- Case and a small documented set of Diablo-font label errors are normalized.
  Digits such as `I5` and `3l` are never silently corrected. Conflicting repeated
  values are cleared and flagged.
- Affix names must match an observed local property template. Unknown or compound
  modifiers, including unsupported multi-value/charge patterns, remain raw lines.
  No nearest-neighbor skill-name substitution occurs.
- Word confidence is a review heuristic, not a probability of correctness.
- Text alone does not establish name color/rarity, absence of ethereal/superior
  modifiers, or whether sockets are empty. Those fields remain null; null is never
  converted to false. This prevents blue staffmods from making a gray base “magic.”
- Item codes and property IDs come from the existing portable catalog/dictionary.
  Market evidence and typical item stats are not used to repair OCR numbers.

Before enabling unattended extraction, collect a held-out fixture set spanning
rarities, resolutions/UI scales, socket contents, long and negative affixes,
charges, partial crops and multiple tooltips. Measure exact deciding-field
accuracy and false acceptance, then benchmark a detector/recognizer alternative
such as PP-OCR on those same fixtures. A larger OCR model is not yet justified by
this single example. Keep a visual fallback for uncertain fields regardless.

## Primary references inspected 2026-09-23

- [PyOCR package documentation](https://pypi.org/project/pyocr/): wrappers, C-API
  backend and bounding-box builders.
- [Tesseract image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html):
  background, scaling, borders and segmentation affect recognition.
- [PaddleOCR inference documentation](https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/pipeline_usage/OCR.html):
  an alternative local detector/recognizer to evaluate if fixture results require it.

## Local regression images

The real screenshots in `tests/pricing/knowledge/fixtures/*.png` are excluded from Git.
Restore `cinquedeas.png` and `circlet.png` from the separate local data backup to run
image integration tests. Those tests skip when the image or local model is absent;
tooltip grammar tests remain available in a code-only checkout.
