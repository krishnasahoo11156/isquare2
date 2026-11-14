# Test Fixture Manifest — iSquare Phase 03B

All fixtures are **programmatically generated** using `create_fixtures.py`.
No external images were downloaded. All images are original synthetic outputs.

| Filename | Source | License | Expected Category | Expected Text (ground truth) | Expected Objects | Quality Notes |
|---|---|---|---|---|---|---|
| `fixture_printed_document.png` | Synthetic (Pillow) | Original | Document | See below | None | High contrast, clean |
| `fixture_blank_document.png` | Synthetic (Pillow) | Original | Document | _(empty)_ | None | No content |
| `fixture_screenshot.png` | Synthetic (Pillow) | Original | Screenshot | See below | None | Dark background, light text |
| `fixture_low_resolution.png` | Synthetic (Pillow) | Original | Document | `LOW RES TEXT` | None | 160×60 px — challenges OCR |
| `fixture_multi_column_poster.png` | Synthetic (Pillow) | Original | Mixed/Document | See below | None | Two-column layout |
| `fixture_geometric_shapes.png` | Synthetic (Pillow) | Original | Illustration/Artwork | _(empty)_ | None | No text, geometric shapes |
| `fixture_rotated_text.png` | Synthetic (Pillow) | Original | Document | `ROTATED SAMPLE TEXT` | None | 90° rotation — standard OCR will likely fail |
| `fixture_low_contrast.png` | Synthetic (Pillow) | Original | Document | `LOW CONTRAST CONTENT` | None | Light grey text, needs contrast enhancement |
| `fixture_corrupted.bin` | Synthetic (manual) | Original | N/A | N/A | N/A | Not a valid image — error path test |
| `fixture_ocr_smoke.png` | Synthetic (Pillow) | Original | Document | `iSquare OCR Smoke Test\nHello World 1234` | None | Primary CER/WER ground truth fixture |

## Ground Truth Text

### fixture_printed_document.png
```
iSquare Phase 03B OCR Test
Date: 2026-11-14
Reference: DOC-001

The quick brown fox jumps over the lazy dog.
Pack my box with five dozen liquor jugs.
How vexingly quick daft zebras jump!

TOTAL: $1,234.56
Account: 9876-5432
```

### fixture_screenshot.png
```
Status: completed
Analysis ID: a1b2c3d4
OCR engine: Tesseract 5.3.0
Words found: 42
Objects detected: person (87%), chair (71%)
```

### fixture_multi_column_poster.png
```
ANNUAL REPORT 2026
Revenue: $4.2M
Growth: +18%
Staff: 32 FTE
Region: North
Market share: 24%
NPS: 71
Prepared by iSquare Analytics
```

### fixture_ocr_smoke.png (primary CER/WER measurement)
```
iSquare OCR Smoke Test
Hello World 1234
```

## Notes

- Ground truth is **kept separate** from model predictions.
- Synthetic fixtures do not substitute for real-world image diversity.
- Font rendering depends on system fonts. `arial.ttf` is used when available; fallback to Pillow default.
- Results on these fixtures should not be cited as general OCR accuracy.
- The corrupted fixture (`fixture_corrupted.bin`) is not a valid image file and must trigger an error response, not a crash.

