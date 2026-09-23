# Offline EasyOCR extraction

EasyOCR is the supported CPU engine. Tesseract is removed from the runtime path;
there is no engine fallback or automatic model download. Shared parsing lives in
`tooltip.py`; `ocr.py` preserves the module entry point.

## Run

Use the explicitly provisioned Python 3.12 environment (the main project remains
Python 3.14; installing the OCR stack into it has not been validated):

```sh
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 /tmp/d2r-easyocr-env/bin/python -m pricing.knowledge.ocr IMAGE --output tmp/ocr/result.json
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 /tmp/d2r-easyocr-env/bin/python -m pricing.knowledge image IMAGE
```

The first command extracts a draft; the second also retrieves local candidate KB
evidence. The calling agent reviews the original image and bundle and performs the
appraisal under the offline skill. No local LLM is installed or invoked. The bundle
always reports REVIEW and unresolved pricing until that review; this is not an
unattended appraisal. Unknown rarity/ethereal/socket contents stay unknown.

`--model-dir DIR` selects provisioned models. Extraction accepts `--retry-limit 1`
(up to 3): grayscale greedy recognition of unparsed regions, with clipped crop
coordinates. Both readings are retained; retry text never replaces observed values.
Retries are disabled by default. No masks, beamsearch or numeric repair is enabled.
Output includes raw geometry, region confidence, image/model hashes and timings.
Region confidence is not word confidence or a calibrated correctness probability.

## Explicit setup only

```sh
uv venv --python 3.12 /tmp/d2r-easyocr-env
uv pip install --python /tmp/d2r-easyocr-env/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python /tmp/d2r-easyocr-env/bin/python easyocr==1.7.2
/tmp/d2r-easyocr-env/bin/python -c 'import easyocr; easyocr.Reader(["en"], gpu=False, model_storage_directory="pricing/raw/ocr/easyocr", user_network_directory="pricing/raw/ocr/easyocr/user_network", download_enabled=True)'
```

Setup is a separate network operation, never part of appraisal. Models and PNG
fixtures remain outside Git. The previous `ocr` project extra and `--tessdata`,
`--diagnostics`, `--full` flags are retired; use `--output` for complete evidence.

## Validation and limitations

The parser now distinguishes complete named titles from rare-title substrings and
retains the separate base line. It supports explicit two-number elemental damage;
unreadable digits remain raw. Compound labels with OCR errors still need review.
Four development screenshots are not held-out validation. Real EasyOCR tests skip
in the main environment; run installed-model probes separately. The provisional
one-second warm latency target is not met on all images. Model hashes are currently
computed per extraction and no persistent reader service is provided.

## Historical experiments (prior parser/backend migration)

The following measurements record earlier experiments, not current engine choices.

### EasyOCR first result (2026-09-23)

With four CPU threads and original Kelpie pixels, grouped regions correctly read
KELPIE SNARE. Required level 33 and +10 Strength parse; Strength requirement 61
is misread as 6 [, life 113 as +[3, and several numeric tokens split.
This is not yet an accurate full-tooltip extractor. Region grouping is for one
horizontal tooltip only. The shared parser now leaves damaged hand labels unknown.
The initial CPU process took 5152.51 ms including reader initialization 3065.07 ms.
A subsequent extraction with a preloaded reader took 1818.71 ms (recognition
1625.30 ms); one sample, not p95. Python socket connections were blocked during
the probe. Tesseract's earlier ~502 ms sample was faster but missed the unique title.
Both remain review-only; preprocessing and held-out evaluation remain pending.

### Step 1: preprocessing comparison (2026-09-23)

One Kelpie screenshot, English CPU reader already loaded, four CPU threads,
Python socket connections blocked. All variants used the same reader/settings;
no numeric correction or parser change. Recognition-only single-run timings:

| Input | Recognition ms | Observed result |
| --- | ---: | --- |
| Original RGB | 1656.52 | Correct title/base; strength 61 becomes 6 [, life 113 becomes +[3 |
| Inverted autocontrast grayscale | 1628.62 | Title becomes KELPTE SNARE; base and several labels degrade |
| Gold/white/blue threshold mask | 1542.27 | Fire-resist +50% and slow 75 % clearer; base and ED degrade |
| Same mask scaled 2x | 5225.95 | Damage 142 becomes [42; no reliable numeric improvement |

Color masks use broad channel thresholds; this is an exploratory one-image
comparison, not a calibrated pipeline. Timings exclude preprocessing, model
initialization and parsing; single sequential samples cannot establish a speed
advantage. No variant is adopted. Keep original pixels as the baseline.
Next experiment: isolate detected line regions and compare recognition settings
on development images, preserving the original OCR and flagging disagreements.
Test selected settings on other screenshots before adopting them.

Local reproducibility artifacts (ignored, outside the committed dataset):
`tmp/easyocr-preprocess/probe.py`, `results.json`, and variant PNGs.

### Step 2: detected line recognition (2026-09-23)

Used the baseline's geometric line groups with four horizontal and three vertical
pixels of padding, clipped to image bounds. Re-recognized these regions with
grayscale/greedy, grayscale/beamsearch and inverted-autocontrast/greedy settings.
No hand-selected text coordinates or KB-derived numeric corrections. Three
development screenshots; none is held out. Same English reader, four CPU threads,
network connections blocked, one sample per setting.

| Screenshot | Baseline OCR ms | Gray greedy retry ms | Baseline + retry ms |
| --- | ---: | ---: | ---: |
| Kelpie Snare | 2122.57 | 406.29 | 2528.86 |
| Cinquedeas | 1916.55 | 447.10 | 2363.65 |
| Circlet | 356.57 | 77.51 | 434.08 |

These are recognition timings, not upload-to-result or complete preprocessing
timings. Readers were loaded in advance; ordering and warm-up can affect samples.

- Gray greedy fixes Cinquedeas damage from `15 T0 3 [` to `15 Te 31`.
  Strength remains `2[` instead of 21.
- Gray greedy reads Circlet's title, defense 26, durability 22/35 and level 16
  correctly (the documented @ -> O label normalization handles @F).
- Kelpie gray greedy improves durability but changes life to `+3` instead of
  113 and strength bonus to `+I0`. A syntactically valid number can still be wrong.
- Inverted line recognition recovers Kelpie's `+113`, but damages Cinquedeas
  damage/durability and Circlet name/level. It is not a global improvement.
- Beam search emits numerical overflow warnings in this installed stack and
  truncates text, including Circlet's maximum durability from 35 to 3.
  Do not adopt beam search on this evidence; its root cause is not established.

Decision: keep defaults unchanged. Gray greedy line recognition is a candidate
for a bounded review retry, retaining both readings and explicit disagreements;
it is not authoritative and does not justify automatic appraisal readiness.
Next step: build a labeled field-level evaluation and disagreement gate before
wiring retries into the appraiser. Correct digits must be evaluated independently
of identity matches, and agreement alone is not proof of correctness.

Reproduction:
`OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONPATH=. /tmp/d2r-easyocr-env/bin/python tmp/easyocr-preprocess/line_probe.py`.
Raw results and automatic crop boxes: `tmp/easyocr-preprocess/line-results.json`.
These local experiment artifacts are not staged; preserve with the data backup.

### Fresh-image check: Stone Necklace (2026-09-23)

Settings from step 2 were frozen before this image was tested. The supplied rare
Amulet has level 37, +2 Eldritch Skills (Warlock Only), 1–6 fire damage, 1–16
lightning damage, +4 Mana, +13% Fire Resist and Damage Reduced by 2.

EasyOCR original recognition took 1245.94 ms; gray greedy line retry added
241.68 ms (1487.62 ms total recognition). Base Amulet, level 37 and physical
Damage Reduced by 2 parse. Only one of six modifiers parses. The skill text is
read but contains label errors; damage minima become T or [, Mana loses its
plus sign, and FIRE becomes FRE. The retry improves some labels but turns
resistance 13 into [3 and leaves both damage ranges unreliable. Beam search
again warns and truncates. No setting change is justified by this image.

Tesseract comparison took 371.87 ms for complete extraction and parsed resistance
13 plus physical damage reduction 2, but falsely identified the item as Stone
from the rare title Stone Necklace. This is a separate catalog-substring bug:
rare titles must not resolve to a named catalog item from one matching token.
Add this negative case to E1a alongside exact unique-name/base resolution.
Both engines remain needs_review; this sample is OCR evaluation, not appraisal.

Local image: tests/pricing/knowledge/fixtures/stone-necklace.png (Git-ignored).
Evidence: tmp/easyocr-preprocess/stone-necklace-results.json, visual truth in
stone-necklace-truth.json, Tesseract full diagnostics in amulet-tesseract/result.json.
