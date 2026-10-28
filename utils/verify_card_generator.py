"""
PAYOMBOYZ Sentinel Verification & Welcome Card Generator
Renders ultra-high-definition, center-aligned luxury cyberpunk welcome cards
using 'Lerning/Blackground Sep.png' as the base background.
"""
import io
import os
import time
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageOps

def _get_background_path() -> Optional[str]:
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "Blackground Sep.png")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Blackground Sep.png")),
        r"d:\Deobfuscate\Lerning\Blackground Sep.png",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Blackground Sep.png")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Lerning", "Blackground Sep.png")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def _get_fonts():
    # 1. Bundled assets (100% portable on Bot-Hosting.net Linux & Windows)
    bundled_bold = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "font_bold.ttf"))
    bundled_reg = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "font_regular.ttf"))
    if os.path.exists(bundled_bold):
        reg = bundled_reg if os.path.exists(bundled_reg) else bundled_bold
        return bundled_bold, reg

    font_bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        r"C:\Windows\Fonts\leelawdb.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
    ]
    font_reg_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        r"C:\Windows\Fonts\LeelawUI.ttf",
        r"C:\Windows\Fonts\leelawad.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]

    bold_path = next((p for p in font_bold_candidates if os.path.exists(p)), None)
    reg_path = next((p for p in font_reg_candidates if os.path.exists(p)), bold_path)

    return bold_path, reg_path

def generate_verification_card_sync(
    user_name: str,
    user_handle: str,
    user_id: str,
    role_name: str,
    guild_name: str,
    member_count: int = 0,
    avatar_bytes: Optional[bytes] = None
) -> io.BytesIO:
    """
    Renders an elite, 1000x460 center-aligned HighSpec-style welcome card:
    - Base: Lerning/Blackground Sep.png
    - Center large circular avatar with glowing gold/cyan dual-ring halo
    - Stylized WELCOME typography with drop shadow
    - Crisp White User Display Name + Emerald Member Count
    - Obsidian cyber glass container with golden HUD corner brackets
    """
    W, H = 1000, 460
    bg_path = _get_background_path()

    # 1. Base Background Image
    if bg_path and os.path.exists(bg_path):
        try:
            bg = Image.open(bg_path).convert("RGBA")
            bg_ratio = bg.width / bg.height
            target_ratio = W / H
            if bg_ratio > target_ratio:
                nw = int(bg.height * target_ratio)
                l = (bg.width - nw) // 2
                bg = bg.crop((l, 0, l + nw, bg.height))
            else:
                nh = int(bg.width / target_ratio)
                t = (bg.height - nh) // 2
                bg = bg.crop((0, t, bg.width, t + nh))
            bg = bg.resize((W, H), Image.Resampling.LANCZOS)
        except Exception:
            bg = Image.new("RGBA", (W, H), (14, 16, 22, 255))
    else:
        bg = Image.new("RGBA", (W, H), (14, 16, 22, 255))

    # 2. Dark Cyber HUD Overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Dark glass panel in center
    m_x, m_y = 28, 20
    p_w, p_h = W - 2 * m_x, H - 2 * m_y
    d.rounded_rectangle(
        [m_x, m_y, m_x + p_w, m_y + p_h],
        radius=24,
        fill=(10, 12, 18, 225),
        outline=(255, 200, 0, 140),
        width=2
    )

    # Cyber corner brackets (Gold / Amber)
    c_len = 32
    for cx, cy in [(m_x, m_y), (m_x + p_w, m_y), (m_x, m_y + p_h), (m_x + p_w, m_y + p_h)]:
        dx = -1 if cx > W // 2 else 1
        dy = -1 if cy > H // 2 else 1
        d.line([(cx, cy), (cx + dx * c_len, cy)], fill=(255, 215, 0, 255), width=3)
        d.line([(cx, cy), (cx, cy + dy * c_len)], fill=(255, 215, 0, 255), width=3)

    # 3. Avatar Processing (Centered)
    av_size = 170
    av_x = (W - av_size) // 2
    av_y = m_y + 30

    if avatar_bytes:
        try:
            av_raw = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        except Exception:
            av_raw = Image.new("RGBA", (av_size, av_size), (40, 50, 75, 255))
    else:
        av_raw = Image.new("RGBA", (av_size, av_size), (40, 50, 75, 255))
        d_raw = ImageDraw.Draw(av_raw)
        d_raw.ellipse([10, 10, av_size - 10, av_size - 10], fill=(70, 95, 140))

    # Circular mask with antialiasing
    scale_factor = 2
    big_size = av_size * scale_factor
    mask_big = Image.new("L", (big_size, big_size), 0)
    d_mask = ImageDraw.Draw(mask_big)
    d_mask.ellipse([0, 0, big_size, big_size], fill=255)
    mask = mask_big.resize((av_size, av_size), Image.Resampling.LANCZOS)

    av_fitted = ImageOps.fit(av_raw, (av_size, av_size), method=Image.Resampling.LANCZOS)
    av_fitted.putalpha(mask)

    # Glowing halo rings behind avatar
    halo_size = av_size + 22
    halo = Image.new("RGBA", (halo_size, halo_size), (0, 0, 0, 0))
    d_h = ImageDraw.Draw(halo)
    d_h.ellipse([4, 4, halo_size - 4, halo_size - 4], outline=(255, 215, 0, 230), width=4)
    d_h.ellipse([7, 7, halo_size - 7, halo_size - 7], outline=(0, 240, 255, 160), width=2)
    overlay.alpha_composite(halo, (av_x - 11, av_y - 11))

    # Paste Avatar
    overlay.alpha_composite(av_fitted, (av_x, av_y))

    # Verified badge pinned on bottom-right of avatar
    badge_size = 42
    bx = av_x + av_size - badge_size + 2
    by = av_y + av_size - badge_size + 2
    d.ellipse([bx, by, bx + badge_size, by + badge_size], fill=(10, 12, 18, 255), outline=(0, 255, 170, 255), width=3)
    d.line([(bx + 11, by + 22), (bx + 18, by + 29)], fill=(0, 255, 170), width=4)
    d.line([(bx + 18, by + 29), (bx + 31, by + 14)], fill=(0, 255, 170), width=4)

    # 4. Typography (Centered, High-Spec)
    font_bold_path, font_reg_path = _get_fonts()
    if font_bold_path:
        f_welcome = ImageFont.truetype(font_bold_path, 36)
        f_name = ImageFont.truetype(font_bold_path, 30)
        f_sub = ImageFont.truetype(font_bold_path, 17)
        f_foot = ImageFont.truetype(font_reg_path or font_bold_path, 14)
    else:
        f_welcome = f_name = f_sub = f_foot = ImageFont.load_default()

    # WELCOME title
    w_text = "W E L C O M E"
    bb_w = d.textbbox((0, 0), w_text, font=f_welcome)
    tw_w = bb_w[2] - bb_w[0]
    # Drop shadow
    d.text(((W - tw_w) // 2 + 2, av_y + av_size + 22), w_text, font=f_welcome, fill=(0, 0, 0, 180))
    d.text(((W - tw_w) // 2, av_y + av_size + 20), w_text, font=f_welcome, fill=(255, 215, 0))

    # User Display Name
    name_str = user_name[:24] if user_name else "User"
    bb_n = d.textbbox((0, 0), name_str, font=f_name)
    tw_n = bb_n[2] - bb_n[0]
    d.text(((W - tw_n) // 2 + 2, av_y + av_size + 68), name_str, font=f_name, fill=(0, 0, 0, 180))
    d.text(((W - tw_n) // 2, av_y + av_size + 66), name_str, font=f_name, fill=(255, 255, 255))

    # Member Count & Server Tag
    count_str = f"MEMBER #{member_count:,}  •  @{user_handle}" if member_count > 0 else f"@{user_handle}  •  ID: {user_id}"
    bb_s = d.textbbox((0, 0), count_str, font=f_sub)
    tw_s = bb_s[2] - bb_s[0]
    d.text(((W - tw_s) // 2, av_y + av_size + 110), count_str, font=f_sub, fill=(0, 255, 170))

    # Footer Watermark
    guild_tag = (guild_name or "PAYOMBOYZ").upper()
    foot_str = f"{guild_tag} • OFFICIAL MEMBER • SENTINEL v3.0"
    bb_f = d.textbbox((0, 0), foot_str, font=f_foot)
    tw_f = bb_f[2] - bb_f[0]
    d.text(((W - tw_f) // 2, av_y + av_size + 138), foot_str, font=f_foot, fill=(120, 135, 155))

    # 5. Composite Final Image
    final = Image.alpha_composite(bg, overlay)
    buf = io.BytesIO()
    final.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
