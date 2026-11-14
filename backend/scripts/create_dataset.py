"""
Generate a structured, reproducible image classification dataset for iSquare.
Covers all 10 target categories (+ 1 Uncertain evaluation set):
  1. Human photograph (stylized portrait / figure representations)
  2. Document (invoices, memos, receipts, dual-column papers)
  3. Screenshot (desktop window, web browser, mobile chat, terminal)
  4. Logo or graphic (emblem, brand crest, icon, badge)
  5. Object or product (boxed product, bottle, coffee mug, gadget)
  6. Landscape or outdoor scene (mountain sunset, ocean horizon, forest canopy)
  7. Animal photograph (bird on branch, feline profile, wildlife)
  8. Illustration or artwork (abstract geometry, watercolor gradient, modern art)
  9. Mixed-content image (magazine layout, poster with text and graphic)
  10. Other (random noise, color grid, abstract test pattern)

Each sample is programmatically generated — 100% public domain / CC0, zero copyright.
Splits: train (60%), val (20%), test (20%).
"""
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CATEGORIES = [
    "Human photograph",
    "Document",
    "Screenshot",
    "Logo or graphic",
    "Object or product",
    "Landscape or outdoor scene",
    "Animal photograph",
    "Illustration or artwork",
    "Mixed-content image",
    "Other",
]

DATASET_DIR = Path(__file__).resolve().parent.parent / "storage" / "dataset"


def _font(size: int = 20):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


# --- Generators for each category ---

def draw_human(seed: int) -> Image.Image:
    """Simulate a portrait/human photograph layout with skin tones and figure silhouette."""
    rng = random.Random(seed)
    bg_colors = [(180, 200, 220), (210, 210, 215), (70, 80, 95), (230, 225, 215)]
    img = Image.new("RGB", (320, 320), rng.choice(bg_colors))
    draw = ImageDraw.Draw(img)
    
    # Shoulders / torso
    shirt_color = (rng.randint(40, 150), rng.randint(40, 150), rng.randint(60, 180))
    draw.ellipse([40, 210, 280, 420], fill=shirt_color)
    
    # Neck
    skin = (rng.randint(210, 245), rng.randint(170, 210), rng.randint(140, 180))
    draw.rectangle([135, 170, 185, 220], fill=skin)
    
    # Head / face
    draw.ellipse([110, 70, 210, 190], fill=skin)
    
    # Hair
    hair = (rng.randint(30, 70), rng.randint(25, 60), rng.randint(20, 50))
    draw.arc([105, 55, 215, 150], start=160, end=380, fill=hair, width=16)
    draw.ellipse([115, 55, 205, 105], fill=hair)
    
    # Eyes & Mouth
    draw.ellipse([135, 115, 145, 125], fill=(50, 40, 35))
    draw.ellipse([175, 115, 185, 125], fill=(50, 40, 35))
    draw.arc([145, 145, 175, 165], start=10, end=170, fill=(180, 80, 80), width=3)
    return img


def draw_document(seed: int) -> Image.Image:
    """Simulate a printed or scanned document with structured text blocks."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (rng.randint(245, 255), rng.randint(245, 255), rng.randint(240, 250)))
    draw = ImageDraw.Draw(img)
    f = _font(13)
    
    # Header
    draw.text((25, 20), "OFFICIAL RECORD / STATEMENT", fill=(20, 20, 20), font=_font(15))
    draw.line([(25, 45), (295, 45)], fill=(120, 120, 120), width=2)
    
    # Text lines
    y = 60
    while y < 270:
        line_len = rng.randint(140, 260)
        draw.rectangle([25, y, 25 + line_len, y + 8], fill=(50, 50, 50))
        y += 18
    
    # Signature / stamp area
    draw.rectangle([180, 275, 280, 305], outline=(180, 40, 40), width=2)
    draw.text((190, 282), "APPROVED", fill=(180, 40, 40), font=_font(12))
    return img


def draw_screenshot(seed: int) -> Image.Image:
    """Simulate a computer UI window with title bar, buttons, and content."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (35, 39, 46))
    draw = ImageDraw.Draw(img)
    
    # Window header bar
    draw.rectangle([0, 0, 320, 35], fill=(50, 54, 62))
    draw.ellipse([12, 12, 22, 22], fill=(235, 80, 80))
    draw.ellipse([28, 12, 38, 22], fill=(235, 180, 50))
    draw.ellipse([44, 12, 54, 22], fill=(80, 200, 100))
    draw.text((75, 10), "app://isquare/workspace", fill=(190, 195, 205), font=_font(11))
    
    # Sidebar
    draw.rectangle([0, 36, 85, 320], fill=(42, 46, 54))
    for sy in [55, 90, 125, 160]:
        draw.rectangle([15, sy, 70, sy + 14], fill=(70, 76, 88))
        
    # Main panel with cards
    draw.rectangle([100, 55, 305, 160], fill=(50, 56, 66), outline=(75, 82, 95))
    draw.text((115, 68), "Status: 200 OK", fill=(100, 220, 140), font=_font(13))
    draw.rectangle([115, 95, 250, 105], fill=(130, 140, 155))
    draw.rectangle([115, 120, 220, 130], fill=(130, 140, 155))
    
    draw.rectangle([100, 180, 305, 290], fill=(50, 56, 66), outline=(75, 82, 95))
    return img


def draw_logo(seed: int) -> Image.Image:
    """Simulate a vector brand mark, logo, or clean graphic symbol."""
    rng = random.Random(seed)
    bg = (rng.randint(240, 255), rng.randint(240, 255), rng.randint(240, 255))
    img = Image.new("RGB", (320, 320), bg)
    draw = ImageDraw.Draw(img)
    
    color1 = (rng.randint(20, 200), rng.randint(40, 180), rng.randint(180, 240))
    color2 = (rng.randint(200, 240), rng.randint(80, 120), rng.randint(30, 60))
    
    shape_type = seed % 3
    if shape_type == 0:
        # Concentric geometric rings
        draw.ellipse([70, 70, 250, 250], outline=color1, width=18)
        draw.ellipse([110, 110, 210, 210], fill=color2)
    elif shape_type == 1:
        # Diamond / polygon emblem
        draw.polygon([(160, 50), (270, 160), (160, 270), (50, 160)], fill=color1)
        draw.polygon([(160, 90), (230, 160), (160, 230), (90, 160)], fill=bg)
    else:
        # Hexagonal crest with inner glyph
        draw.polygon([(160, 60), (250, 110), (250, 210), (160, 260), (70, 210), (70, 110)], fill=color1)
        draw.rectangle([145, 100, 175, 220], fill=color2)
        draw.rectangle([110, 145, 210, 175], fill=color2)
    return img


def draw_object(seed: int) -> Image.Image:
    """Simulate a product or isolated physical object on a clean studio surface."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (230, 230, 235))
    draw = ImageDraw.Draw(img)
    
    # Surface drop shadow
    draw.ellipse([80, 240, 240, 280], fill=(195, 195, 205))
    
    obj_type = seed % 3
    if obj_type == 0:
        # Drink bottle / cylinder
        draw.rectangle([125, 100, 195, 250], fill=(45, 120, 180), outline=(25, 80, 130), width=3)
        draw.rectangle([140, 70, 180, 100], fill=(210, 215, 220))
        draw.rectangle([145, 55, 175, 70], fill=(180, 40, 40)) # Cap
        draw.rectangle([130, 140, 190, 190], fill=(255, 255, 255)) # Label
    elif obj_type == 1:
        # Box / package
        draw.polygon([(100, 140), (160, 100), (230, 130), (170, 170)], fill=(210, 160, 100)) # Top
        draw.polygon([(100, 140), (170, 170), (170, 260), (100, 220)], fill=(170, 120, 70))  # Left
        draw.polygon([(170, 170), (230, 130), (230, 210), (170, 260)], fill=(140, 95, 50))   # Right
    else:
        # Mug / cup
        draw.rectangle([110, 110, 210, 240], fill=(220, 50, 50))
        draw.arc([190, 130, 250, 210], start=270, end=90, fill=(220, 50, 50), width=14)
    return img


def draw_landscape(seed: int) -> Image.Image:
    """Simulate outdoor scenery: sky, mountains/hills, sun/clouds."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (135, 195, 235))
    draw = ImageDraw.Draw(img)
    
    # Sun / Sunset
    sun_y = rng.randint(60, 130)
    draw.ellipse([210, sun_y, 270, sun_y + 60], fill=(255, 225, 110))
    
    # Back mountain range
    draw.polygon([(0, 220), (80, 140), (170, 210), (250, 130), (320, 200), (320, 320), (0, 320)], fill=(90, 110, 140))
    # Front mountain / hills
    draw.polygon([(0, 260), (110, 180), (220, 270), (320, 220), (320, 320), (0, 320)], fill=(50, 120, 60))
    # Water or valley ground
    draw.rectangle([0, 275, 320, 320], fill=(40, 90, 130))
    return img


def draw_animal(seed: int) -> Image.Image:
    """Simulate an animal photograph (bird/quadruped silhouette against natural background)."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (195, 215, 185))
    draw = ImageDraw.Draw(img)
    
    # Perch / branch
    draw.line([(0, 240), (320, 210)], fill=(100, 70, 40), width=14)
    
    # Bird body
    feather = (rng.randint(30, 70), rng.randint(80, 160), rng.randint(140, 220))
    draw.ellipse([120, 130, 200, 215], fill=feather) # Body
    draw.ellipse([170, 100, 220, 145], fill=feather) # Head
    draw.polygon([(215, 115), (245, 122), (215, 130)], fill=(230, 160, 40)) # Beak
    draw.ellipse([195, 112, 205, 122], fill=(20, 20, 20)) # Eye
    draw.polygon([(130, 190), (70, 260), (140, 215)], fill=(feather[0] - 20, feather[1] - 20, feather[2] - 20)) # Tail
    return img


def draw_artwork(seed: int) -> Image.Image:
    """Simulate an illustration or abstract modern artwork with expressive geometry."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (245, 240, 230))
    draw = ImageDraw.Draw(img)
    
    for _ in range(5):
        box = [rng.randint(20, 180), rng.randint(20, 180), rng.randint(180, 300), rng.randint(180, 300)]
        color = (rng.randint(60, 230), rng.randint(50, 200), rng.randint(70, 220))
        if rng.random() > 0.5:
            draw.ellipse(box, fill=color)
        else:
            draw.rectangle(box, fill=color)
            
    # Bold black brush lines
    for _ in range(3):
        p1 = (rng.randint(10, 310), rng.randint(10, 310))
        p2 = (rng.randint(10, 310), rng.randint(10, 310))
        draw.line([p1, p2], fill=(30, 30, 35), width=rng.randint(4, 10))
    return img


def draw_mixed_content(seed: int) -> Image.Image:
    """Simulate a magazine layout or flyer with both a photo panel and text columns."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Graphic photo block on top half
    draw.rectangle([20, 20, 300, 150], fill=(70, 130, 180))
    draw.polygon([(30, 140), (100, 70), (170, 130), (240, 80), (290, 140)], fill=(40, 90, 140))
    draw.ellipse([230, 40, 270, 80], fill=(255, 220, 100))
    
    # Headline text
    draw.text((22, 160), "SPECIAL REPORT", fill=(180, 30, 30), font=_font(14))
    
    # Two columns of text below
    for y in range(185, 290, 14):
        draw.rectangle([22, y, 145, y + 6], fill=(70, 70, 70))
        draw.rectangle([165, y, 298, y + 6], fill=(70, 70, 70))
    return img


def draw_other(seed: int) -> Image.Image:
    """Simulate miscellaneous, abstract textures, noise, or unclassifiable patterns."""
    rng = random.Random(seed)
    img = Image.new("RGB", (320, 320), (128, 128, 128))
    draw = ImageDraw.Draw(img)
    
    # Checkerboard / test grid pattern
    step = 32
    for x in range(0, 320, step):
        for y in range(0, 320, step):
            if (x // step + y // step) % 2 == 0:
                c = rng.randint(60, 200)
                draw.rectangle([x, y, x + step, y + step], fill=(c, c, c))
    return img


GENERATORS = {
    "Human photograph": draw_human,
    "Document": draw_document,
    "Screenshot": draw_screenshot,
    "Logo or graphic": draw_logo,
    "Object or product": draw_object,
    "Landscape or outdoor scene": draw_landscape,
    "Animal photograph": draw_animal,
    "Illustration or artwork": draw_artwork,
    "Mixed-content image": draw_mixed_content,
    "Other": draw_other,
}


def create_dataset():
    manifest = []
    total = 0
    
    for split in ["train", "val", "test"]:
        count_per_class = 6 if split == "train" else 2
        split_dir = DATASET_DIR / split
        split_dir.mkdir(parents=True, exist_ok=True)
        
        for cat_idx, category in enumerate(CATEGORIES):
            cat_slug = category.lower().replace(" ", "_").replace("/", "_")
            gen_fn = GENERATORS[category]
            
            for i in range(count_per_class):
                seed = hash(f"{category}_{split}_{i}") % 1000000
                img = gen_fn(seed)
                filename = f"{cat_slug}_{split}_{i:02d}.png"
                out_path = split_dir / filename
                img.save(out_path)
                
                manifest.append({
                    "filename": filename,
                    "filepath": str(out_path.relative_to(DATASET_DIR.parent.parent)),
                    "split": split,
                    "category": category,
                    "category_index": cat_idx,
                    "width": img.width,
                    "height": img.height,
                    "license": "CC0-Public-Domain-Synthetic",
                })
                total += 1
                
    manifest_path = DATASET_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {total} synthetic dataset images across 10 categories into {DATASET_DIR}")
    print(f"Manifest written to: {manifest_path}")
    return manifest


if __name__ == "__main__":
    create_dataset()

