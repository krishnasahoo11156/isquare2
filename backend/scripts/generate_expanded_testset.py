"""
Generate an expanded, independent evaluation dataset for iSquare validation (Phase 03D).
Target: 50 independent samples per category (10 concrete categories = 500 images)
Plus 25 blank background samples and 25 ambiguous / noisy samples.
All generated under CC0-Public-Domain license, strictly isolated from training data.
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

EXPANDED_DIR = Path(__file__).resolve().parent.parent / "storage" / "dataset" / "expanded_eval"


def _font(size: int = 16):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


# --- Diverse procedural generators ---

def draw_diverse_human(rng: random.Random) -> Image.Image:
    bg = (rng.randint(30, 240), rng.randint(30, 240), rng.randint(30, 240))
    img = Image.new("RGB", (320, 320), bg)
    draw = ImageDraw.Draw(img)
    
    # Torso
    shirt = (rng.randint(20, 220), rng.randint(20, 220), rng.randint(20, 220))
    shoulder_y = rng.randint(190, 230)
    draw.ellipse([rng.randint(20, 60), shoulder_y, rng.randint(260, 300), 450], fill=shirt)
    
    # Neck
    skin = (rng.randint(180, 255), rng.randint(140, 220), rng.randint(110, 190))
    draw.rectangle([135, shoulder_y - 40, 185, shoulder_y + 10], fill=skin)
    
    # Head
    head_y = rng.randint(50, 80)
    head_w = rng.randint(90, 115)
    draw.ellipse([160 - head_w // 2, head_y, 160 + head_w // 2, head_y + 120], fill=skin)
    
    # Hair
    hair = (rng.randint(20, 120), rng.randint(15, 90), rng.randint(10, 70))
    draw.arc([160 - head_w // 2 - 5, head_y - 15, 160 + head_w // 2 + 5, head_y + 80], 160, 380, fill=hair, width=rng.randint(12, 22))
    
    # Eyes
    eye_y = head_y + 50
    draw.ellipse([140, eye_y, 148, eye_y + 8], fill=(30, 30, 30))
    draw.ellipse([172, eye_y, 180, eye_y + 8], fill=(30, 30, 30))
    draw.line([(147, eye_y + 35), (173, eye_y + 35)], fill=(160, 60, 60), width=2)
    return img


def draw_diverse_document(rng: random.Random) -> Image.Image:
    paper = (rng.randint(245, 255), rng.randint(245, 255), rng.randint(235, 250))
    img = Image.new("RGB", (320, 320), paper)
    draw = ImageDraw.Draw(img)
    
    # Title
    titles = ["INVOICE #9482", "MEDICAL REPORT", "MEMORANDUM", "TAX RECEIPT", "SERVICE CONTRACT", "POLICY BRIEF"]
    draw.text((25, 20), rng.choice(titles), fill=(20, 20, 20), font=_font(14))
    draw.line([(25, 42), (295, 42)], fill=(100, 100, 100), width=1)
    
    # Body text lines
    columns = rng.choice([1, 2])
    y = 55
    if columns == 1:
        while y < 270:
            w = rng.randint(120, 260)
            draw.rectangle([25, y, 25 + w, y + 6], fill=(40, 40, 40))
            y += rng.randint(14, 20)
    else:
        while y < 270:
            w1 = rng.randint(70, 120)
            w2 = rng.randint(70, 120)
            draw.rectangle([25, y, 25 + w1, y + 6], fill=(40, 40, 40))
            draw.rectangle([165, y, 165 + w2, y + 6], fill=(40, 40, 40))
            y += rng.randint(14, 20)
            
    # Stamp
    if rng.random() > 0.4:
        stamp_color = (rng.randint(160, 210), rng.randint(20, 50), rng.randint(20, 50))
        draw.rectangle([180, 275, 290, 305], outline=stamp_color, width=2)
        draw.text((195, 282), "VERIFIED", fill=stamp_color, font=_font(11))
    return img


def draw_diverse_screenshot(rng: random.Random) -> Image.Image:
    dark_mode = rng.random() > 0.3
    bg = (30, 34, 42) if dark_mode else (240, 242, 245)
    header = (45, 50, 60) if dark_mode else (220, 224, 230)
    text_c = (200, 205, 215) if dark_mode else (40, 45, 55)
    
    img = Image.new("RGB", (320, 320), bg)
    draw = ImageDraw.Draw(img)
    
    # Window title bar
    draw.rectangle([0, 0, 320, 30], fill=header)
    for i, col in enumerate([(235, 80, 80), (235, 180, 50), (80, 200, 100)]):
        draw.ellipse([10 + i * 16, 10, 20 + i * 16, 20], fill=col)
    draw.text((65, 8), f"browser://session/{rng.randint(1000, 9999)}", fill=text_c, font=_font(10))
    
    # UI elements
    draw.rectangle([15, 45, 100, 75], fill=(70, 120, 220))
    draw.text((25, 52), "Action Btn", fill=(255, 255, 255), font=_font(11))
    
    draw.rectangle([15, 90, 305, 200], fill=(55, 60, 72) if dark_mode else (255, 255, 255), outline=header)
    for ly in [105, 130, 155, 180]:
        draw.rectangle([30, ly, 30 + rng.randint(120, 250), ly + 8], fill=(100, 110, 125))
    return img


def draw_diverse_logo(rng: random.Random) -> Image.Image:
    bg = (rng.randint(240, 255), rng.randint(240, 255), rng.randint(240, 255))
    img = Image.new("RGB", (320, 320), bg)
    draw = ImageDraw.Draw(img)
    
    c1 = (rng.randint(20, 220), rng.randint(20, 200), rng.randint(150, 240))
    c2 = (rng.randint(200, 250), rng.randint(60, 150), rng.randint(20, 80))
    
    mode = rng.randint(0, 3)
    if mode == 0:
        draw.ellipse([60, 60, 260, 260], outline=c1, width=16)
        draw.polygon([(160, 90), (230, 210), (90, 210)], fill=c2)
    elif mode == 1:
        draw.polygon([(160, 40), (280, 160), (160, 280), (40, 160)], fill=c1)
        draw.ellipse([110, 110, 210, 210], fill=c2)
    elif mode == 2:
        draw.rectangle([80, 80, 240, 240], fill=c1)
        draw.arc([100, 100, 220, 220], 45, 315, fill=c2, width=18)
    else:
        draw.polygon([(160, 50), (260, 110), (260, 220), (160, 270), (60, 220), (60, 110)], outline=c1, width=12)
        draw.ellipse([130, 130, 190, 190], fill=c2)
    return img


def draw_diverse_object(rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (320, 320), (235, 235, 240))
    draw = ImageDraw.Draw(img)
    
    # Shadow
    draw.ellipse([70, 250, 250, 290], fill=(200, 200, 210))
    
    mode = rng.randint(0, 3)
    if mode == 0:
        # Bottle
        draw.rectangle([130, 100, 190, 260], fill=(50, 130, 190), outline=(30, 80, 130), width=2)
        draw.rectangle([145, 65, 175, 100], fill=(210, 215, 225))
        draw.rectangle([150, 45, 170, 65], fill=(200, 40, 40))
    elif mode == 1:
        # Can / Mug
        draw.rectangle([105, 110, 215, 250], fill=(220, 60, 60))
        draw.arc([195, 135, 255, 225], 270, 90, fill=(220, 60, 60), width=12)
    elif mode == 2:
        # Cube box
        draw.polygon([(110, 140), (160, 100), (230, 130), (180, 170)], fill=(215, 170, 110))
        draw.polygon([(110, 140), (180, 170), (180, 260), (110, 220)], fill=(175, 130, 80))
        draw.polygon([(180, 170), (230, 130), (230, 210), (180, 260)], fill=(145, 100, 55))
    else:
        # Smartphone gadget
        draw.rectangle([115, 70, 205, 255], fill=(30, 35, 45), outline=(150, 155, 165), width=3)
        draw.rectangle([125, 85, 195, 235], fill=(70, 130, 190))
    return img


def draw_diverse_landscape(rng: random.Random) -> Image.Image:
    sky_colors = [(130, 190, 235), (235, 150, 100), (80, 120, 180), (220, 180, 140)]
    img = Image.new("RGB", (320, 320), rng.choice(sky_colors))
    draw = ImageDraw.Draw(img)
    
    # Sun
    sun_x = rng.randint(60, 210)
    sun_y = rng.randint(40, 120)
    draw.ellipse([sun_x, sun_y, sun_x + 50, sun_y + 50], fill=(255, 230, 120))
    
    # Mountain peaks
    pts1 = [(0, 230), (70, 130), (160, 210), (240, 140), (320, 220), (320, 320), (0, 320)]
    draw.polygon(pts1, fill=(80, 95, 125))
    pts2 = [(0, 260), (110, 170), (220, 250), (320, 200), (320, 320), (0, 320)]
    draw.polygon(pts2, fill=(45, 110, 55))
    # Foreground
    draw.rectangle([0, 280, 320, 320], fill=(35, 80, 120))
    return img


def draw_diverse_animal(rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (320, 320), (190, 215, 180))
    draw = ImageDraw.Draw(img)
    
    # Ground/perch
    draw.line([(0, 240), (320, 215)], fill=(90, 65, 40), width=12)
    
    c = (rng.randint(40, 90), rng.randint(70, 140), rng.randint(130, 210))
    draw.ellipse([110, 130, 195, 210], fill=c)
    draw.ellipse([160, 95, 215, 145], fill=c)
    draw.polygon([(210, 110), (240, 118), (210, 125)], fill=(230, 150, 40))
    draw.ellipse([185, 108, 195, 118], fill=(20, 20, 20))
    draw.polygon([(120, 185), (60, 250), (135, 210)], fill=(c[0] - 15, c[1] - 15, c[2] - 15))
    return img


def draw_diverse_artwork(rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (320, 320), (245, 240, 230))
    draw = ImageDraw.Draw(img)
    
    for _ in range(rng.randint(4, 8)):
        b = [rng.randint(20, 180), rng.randint(20, 180), rng.randint(180, 300), rng.randint(180, 300)]
        col = (rng.randint(50, 230), rng.randint(50, 210), rng.randint(50, 230))
        if rng.random() > 0.5:
            draw.ellipse(b, fill=col)
        else:
            draw.rectangle(b, fill=col)
    for _ in range(rng.randint(2, 5)):
        p1 = (rng.randint(10, 310), rng.randint(10, 310))
        p2 = (rng.randint(10, 310), rng.randint(10, 310))
        draw.line([p1, p2], fill=(20, 25, 30), width=rng.randint(3, 8))
    return img


def draw_diverse_mixed(rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (320, 320), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Graphic panel
    draw.rectangle([15, 15, 305, 140], fill=(60, 120, 175))
    draw.polygon([(25, 130), (95, 65), (165, 120), (235, 75), (295, 130)], fill=(35, 80, 135))
    draw.ellipse([225, 35, 265, 75], fill=(250, 210, 90))
    
    # Text
    draw.text((20, 155), "MARKET INSIGHTS", fill=(170, 25, 25), font=_font(13))
    for y in range(180, 290, 15):
        draw.rectangle([20, y, 145, y + 6], fill=(60, 60, 60))
        draw.rectangle([165, y, 300, y + 6], fill=(60, 60, 60))
    return img


def draw_diverse_other(rng: random.Random) -> Image.Image:
    img = Image.new("RGB", (320, 320), (128, 128, 128))
    draw = ImageDraw.Draw(img)
    step = rng.choice([16, 20, 32, 40])
    for x in range(0, 320, step):
        for y in range(0, 320, step):
            if (x // step + y // step) % 2 == 0:
                draw.rectangle([x, y, x + step, y + step], fill=(rng.randint(50, 210), rng.randint(50, 210), rng.randint(50, 210)))
    return img


GENERATORS = {
    "Human photograph": draw_diverse_human,
    "Document": draw_diverse_document,
    "Screenshot": draw_diverse_screenshot,
    "Logo or graphic": draw_diverse_logo,
    "Object or product": draw_diverse_object,
    "Landscape or outdoor scene": draw_diverse_landscape,
    "Animal photograph": draw_diverse_animal,
    "Illustration or artwork": draw_diverse_artwork,
    "Mixed-content image": draw_diverse_mixed,
    "Other": draw_diverse_other,
}


def generate_expanded_dataset(samples_per_class: int = 50):
    manifest = []
    EXPANDED_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 50 samples per concrete category (500 samples total)
    for cat_idx, category in enumerate(CATEGORIES):
        cat_slug = category.lower().replace(" ", "_").replace("/", "_")
        gen_fn = GENERATORS[category]
        for i in range(samples_per_class):
            seed = 5000000 + i * 1337 + cat_idx * 997
            rng = random.Random(seed)
            img = gen_fn(rng)
            fname = f"eval_{cat_slug}_{i:02d}.png"
            fpath = EXPANDED_DIR / fname
            img.save(fpath)
            
            manifest.append({
                "filename": fname,
                "category": category,
                "category_index": cat_idx,
                "is_ambiguous": False,
                "is_blank": False,
                "license": "CC0-Public-Domain",
            })
            
    # 2. 25 Blank background images
    blank_colors = [
        (255, 255, 255), (0, 0, 0), (128, 128, 128), (240, 240, 240),
        (20, 20, 20), (250, 248, 240), (220, 230, 242)
    ]
    for i in range(25):
        bg = blank_colors[i % len(blank_colors)]
        img = Image.new("RGB", (320, 320), bg)
        fname = f"eval_blank_{i:02d}.png"
        fpath = EXPANDED_DIR / fname
        img.save(fpath)
        manifest.append({
            "filename": fname,
            "category": "Uncertain",
            "category_index": -1,
            "is_ambiguous": True,
            "is_blank": True,
            "license": "CC0-Public-Domain",
        })
        
    # 3. 25 Ambiguous / Noise composite images
    for i in range(25):
        rng = random.Random(9000000 + i * 773)
        # Blend two distinct generators
        cat_a = rng.choice(CATEGORIES)
        cat_b = rng.choice([c for c in CATEGORIES if c != cat_a])
        img_a = GENERATORS[cat_a](rng)
        img_b = GENERATORS[cat_b](rng)
        blended = Image.blend(img_a, img_b, alpha=0.5)
        # Add slight noise
        if rng.random() > 0.5:
            blended = blended.filter(ImageFilter.GaussianBlur(radius=rng.randint(1, 3)))
            
        fname = f"eval_ambiguous_{i:02d}.png"
        fpath = EXPANDED_DIR / fname
        blended.save(fpath)
        manifest.append({
            "filename": fname,
            "category": "Uncertain",
            "category_index": -1,
            "is_ambiguous": True,
            "is_blank": False,
            "license": "CC0-Public-Domain",
        })
        
    manifest_path = EXPANDED_DIR / "expanded_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} expanded test samples into {EXPANDED_DIR}")
    return manifest


if __name__ == "__main__":
    generate_expanded_dataset(50)
