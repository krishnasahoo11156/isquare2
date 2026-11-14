"""
Generate synthetic test image fixtures with known ground truth for iSquare Phase 03B.

All images are programmatically generated — no external download, no copyright.
They are deterministic: same script, same outputs.
"""
import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(__file__).parent


def _default_font(size: int = 24):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


def make_printed_document():
    """White background with black printed text — ideal OCR target."""
    img = Image.new("RGB", (640, 480), "white")
    draw = ImageDraw.Draw(img)
    font = _default_font(28)
    lines = [
        "iSquare Phase 03B OCR Test",
        "Date: 2026-11-14",
        "Reference: DOC-001",
        "",
        "The quick brown fox jumps over the lazy dog.",
        "Pack my box with five dozen liquor jugs.",
        "How vexingly quick daft zebras jump!",
        "",
        "TOTAL: $1,234.56",
        "Account: 9876-5432",
    ]
    y = 40
    for line in lines:
        draw.text((40, y), line, fill="black", font=font)
        y += 42
    img.save(OUT / "fixture_printed_document.png")
    return "fixture_printed_document.png", "\n".join(l for l in lines)


def make_blank_document():
    """White background, no text."""
    img = Image.new("RGB", (640, 480), "white")
    img.save(OUT / "fixture_blank_document.png")
    return "fixture_blank_document.png", ""


def make_screenshot_text():
    """Dark grey panel imitating a UI screenshot with text."""
    img = Image.new("RGB", (800, 500), (30, 30, 40))
    draw = ImageDraw.Draw(img)
    # Simulate a title bar
    draw.rectangle([0, 0, 800, 36], fill=(50, 50, 65))
    font_title = _default_font(16)
    draw.text((16, 10), "iSquare — Research Results", fill=(220, 220, 220), font=font_title)
    font_body = _default_font(18)
    items = [
        "Status: completed",
        "Analysis ID: a1b2c3d4",
        "OCR engine: Tesseract 5.3.0",
        "Words found: 42",
        "Objects detected: person (87%), chair (71%)",
    ]
    y = 60
    for item in items:
        draw.text((30, y), item, fill=(200, 220, 200), font=font_body)
        y += 36
    img.save(OUT / "fixture_screenshot.png")
    return "fixture_screenshot.png", "\n".join(items)


def make_low_resolution():
    """Low-resolution image with text — challenges OCR."""
    img = Image.new("RGB", (160, 60), "white")
    draw = ImageDraw.Draw(img)
    draw.text((4, 10), "LOW RES TEXT", fill="black")
    img.save(OUT / "fixture_low_resolution.png")
    return "fixture_low_resolution.png", "LOW RES TEXT"


def make_multiple_text_blocks():
    """Multiple columns of text simulating a poster."""
    img = Image.new("RGB", (900, 600), "lightyellow")
    draw = ImageDraw.Draw(img)
    font_header = _default_font(32)
    font_body = _default_font(20)
    draw.text((50, 20), "ANNUAL REPORT 2026", fill="darkblue", font=font_header)
    col1 = ["Revenue: $4.2M", "Growth: +18%", "Staff: 32 FTE"]
    col2 = ["Region: North", "Market share: 24%", "NPS: 71"]
    y = 100
    for line in col1:
        draw.text((50, y), line, fill="black", font=font_body)
        y += 36
    y = 100
    for line in col2:
        draw.text((500, y), line, fill="black", font=font_body)
        y += 36
    draw.text((50, 280), "Prepared by iSquare Analytics", fill="grey", font=font_body)
    img.save(OUT / "fixture_multi_column_poster.png")
    expected = "ANNUAL REPORT 2026\n" + "\n".join(col1) + "\n" + "\n".join(col2) + "\nPrepared by iSquare Analytics"
    return "fixture_multi_column_poster.png", expected


def make_no_text_geometric():
    """Geometric shapes only — no text. Tests 'no readable text' path."""
    img = Image.new("RGB", (500, 400), "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 50, 250, 250], fill="steelblue", outline="navy")
    draw.rectangle([300, 80, 460, 340], fill="tomato", outline="darkred")
    draw.polygon([(250, 320), (380, 180), (450, 380)], fill="forestgreen")
    img.save(OUT / "fixture_geometric_shapes.png")
    return "fixture_geometric_shapes.png", ""


def make_rotated_text():
    """Text rendered at 90 degrees — challenges standard OCR."""
    base = Image.new("RGB", (400, 300), "white")
    text_layer = Image.new("RGB", (300, 80), "white")
    draw = ImageDraw.Draw(text_layer)
    font = _default_font(26)
    draw.text((10, 20), "ROTATED SAMPLE TEXT", fill="black", font=font)
    rotated = text_layer.rotate(90, expand=True)
    base.paste(rotated, (160, 20))
    base.save(OUT / "fixture_rotated_text.png")
    return "fixture_rotated_text.png", "ROTATED SAMPLE TEXT"


def make_low_contrast():
    """Light grey text on white — low contrast, requires contrast enhancement."""
    img = Image.new("RGB", (640, 200), "white")
    draw = ImageDraw.Draw(img)
    font = _default_font(28)
    draw.text((40, 60), "LOW CONTRAST CONTENT", fill=(180, 180, 180), font=font)
    img.save(OUT / "fixture_low_contrast.png")
    return "fixture_low_contrast.png", "LOW CONTRAST CONTENT"


def make_corrupted_image():
    """Writes a file that is not a valid image — tests error handling."""
    path = OUT / "fixture_corrupted.bin"
    path.write_bytes(b"\xff\xd8\xff\xe0JUNK DATA NOT AN IMAGE\x00\x00")
    return "fixture_corrupted.bin", None


def make_ocr_smoke_test():
    """Known-text fixture used for CER/WER measurement."""
    ground_truth = "iSquare OCR Smoke Test\nHello World 1234"
    img = Image.new("RGB", (500, 160), "white")
    draw = ImageDraw.Draw(img)
    font = _default_font(32)
    draw.text((30, 20), "iSquare OCR Smoke Test", fill="black", font=font)
    draw.text((30, 90), "Hello World 1234", fill="black", font=font)
    img.save(OUT / "fixture_ocr_smoke.png")
    return "fixture_ocr_smoke.png", ground_truth


def main():
    results = []
    for fn in [
        make_printed_document,
        make_blank_document,
        make_screenshot_text,
        make_low_resolution,
        make_multiple_text_blocks,
        make_no_text_geometric,
        make_rotated_text,
        make_low_contrast,
        make_corrupted_image,
        make_ocr_smoke_test,
    ]:
        name, expected = fn()
        results.append((name, expected))
        print(f"  Created: {name}")
    print(f"\nAll {len(results)} fixtures written to {OUT}")
    return results


if __name__ == "__main__":
    main()

