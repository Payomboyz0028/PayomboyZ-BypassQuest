"""
High-fidelity Captcha Image Generator for PAYOMBØYZ Verification.
Generates human-readable, bot-resistant distorted/noise text challenges
styled with dark cyber-aesthetic matching the FlowAuth challenge.
"""
import io
import os
import random
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

# Clean alphabet excluding easily confused glyphs (0/O, 1/I, S/5 if needed)
CAPTCHA_ALPHABET = [
    '2', '3', '4', '5', '6', '7', '8', '9',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
    'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R',
    'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
]

def _find_preferred_font(size: int = 50) -> ImageFont.ImageFont:
    """Find a bold monospace font on the system or fallback to default."""
    candidates = [
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/courbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/System/Library/Fonts/Monaco.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_captcha(length: int = 5) -> Tuple[str, bytes]:
    """
    Generate a random captcha code and high-quality distorted image.
    Returns:
        (code_str, png_bytes)
    """
    code = "".join(random.choices(CAPTCHA_ALPHABET, k=length))
    width, height = 380, 110
    
    # Base dark canvas matching Discord dark theme
    img = Image.new("RGB", (width, height), color=(11, 12, 18))
    draw = ImageDraw.Draw(img)
    
    # Outer cyber border
    draw.rectangle([(2, 2), (width - 3, height - 3)], outline=(35, 42, 65), width=2)
    
    # Subtle background grid lines
    for y in range(16, height - 5, 22):
        draw.line([(8, y), (width - 8, y)], fill=(20, 35, 52), width=1)
    for x in range(25, width - 10, 35):
        draw.line([(x, 8), (x, height - 8)], fill=(16, 22, 36), width=1)
        
    font = _find_preferred_font(size=52)
    
    # Render characters with individual rotation and glow
    x_start = 30
    spacing = (width - 60) // length
    
    for i, ch in enumerate(code):
        char_box = Image.new("RGBA", (75, 85), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_box)
        
        # Soft background glow / shadow
        char_draw.text((13, 11), ch, font=font, fill=(70, 75, 140, 160))
        
        # High contrast foreground text (White / Cyan / Lavender)
        fg_colors = [
            (255, 255, 255, 255),
            (230, 245, 255, 255),
            (220, 225, 255, 255),
            (195, 240, 255, 255),
        ]
        chosen_color = random.choice(fg_colors)
        char_draw.text((11, 9), ch, font=font, fill=chosen_color)
        
        # Random rotation (-9 to 9 degrees)
        angle = random.randint(-9, 9)
        rotated = char_box.rotate(angle, expand=False, resample=Image.Resampling.BILINEAR)
        
        x_pos = x_start + i * spacing + random.randint(-4, 4)
        y_pos = 14 + random.randint(-4, 4)
        img.paste(rotated, (x_pos, y_pos), rotated)
        
    # Overlay horizontal scanlines cutting across text (FlowAuth signature style)
    for _ in range(4):
        y = random.randint(28, 82)
        line_color = (
            random.randint(0, 40),
            random.randint(180, 240),
            random.randint(180, 240)
        )
        draw.line([(12, y), (width - 12, y + random.randint(-4, 4))], fill=line_color, width=1)
        
    # Subtle purple / blue horizontal laser line
    y_laser = random.randint(35, 75)
    draw.line([(15, y_laser), (width - 15, y_laser)], fill=(120, 80, 220), width=1)
    
    # Pixel dots / noise
    for _ in range(320):
        nx = random.randint(5, width - 6)
        ny = random.randint(5, height - 6)
        dot_color = (
            random.randint(90, 220),
            random.randint(90, 220),
            random.randint(160, 255)
        )
        draw.point((nx, ny), fill=dot_color)
        
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return code, buf.getvalue()
