"""Card / profile image generation.

Uses OpenCV when available for compositing/resizing, Pillow for text.
All art is original placeholders so it can be replaced with licensed art later.
Results are cached on disk; never block the event loop (call via run_in_executor).
"""
import hashlib
import os

from PIL import Image, ImageDraw, ImageFont

try:
    import cv2  # type: ignore
    import numpy as np

    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

RARITY_BG = {
    "Common": (45, 45, 48),
    "Uncommon": (46, 125, 50),
    "Rare": (21, 101, 192),
    "Epic": (106, 27, 154),
    "Legendary": (245, 124, 0),
    "Mythic": (183, 28, 28),
}

CACHE_DIR = os.getenv("IMAGE_CACHE_DIR", "assets/generated")


def _font(size: int):
    for path in (
        "/usr/share/fonts/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _ensure_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _hash(*parts: str) -> str:
    h = hashlib.md5("|".join(parts).encode()).hexdigest()[:12]
    return h


def _post_process_pil(img: Image.Image) -> Image.Image:
    """Use cv2 for a subtle border/blur polish when available."""
    if not HAS_CV2:
        return img
    try:
        import numpy as np

        arr = np.array(img.convert("RGB"))
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        # slight sharpen via unsharp mask
        blur = cv2.GaussianBlur(bgr, (0, 0), 1.2)
        sharp = cv2.addWeighted(bgr, 1.25, blur, -0.25, 0)
        rgb = cv2.cvtColor(sharp, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    except Exception:
        return img


def character_card(name: str, rarity: str, style: str, faction: str, power: int,
                   stats: dict, art_path: str | None = None) -> str:
    """Build a 600x900 placeholder card, return file path (cached)."""
    _ensure_cache()
    key = _hash("char", name, rarity, style, faction, str(power), str(sorted(stats.items())))
    out = os.path.join(CACHE_DIR, f"char_{key}.png")
    if os.path.exists(out):
        return out

    bg = RARITY_BG.get(rarity, (43, 45, 49))
    img = Image.new("RGB", (600, 900), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 590, 890], outline=(255, 255, 255), width=4)

    # portrait placeholder (replace with licensed art via art_path later)
    if art_path and os.path.exists(art_path):
        try:
            art = Image.open(art_path).convert("RGB").resize((560, 420))
            img.paste(art, (20, 60))
        except Exception:
            d.rectangle([20, 60, 580, 480], fill=(20, 20, 22))
    else:
        d.rectangle([20, 60, 580, 480], fill=(20, 20, 22))
        d.text((200, 250), "NO ART", font=_font(48), fill=(120, 120, 120))

    d.text((24, 16), f"{name}", font=_font(34), fill=(255, 255, 255))
    d.text((24, 495), f"{rarity}  |  {style}", font=_font(24), fill=(255, 255, 255))
    d.text((24, 530), f"{faction}  |  POW {power}", font=_font(24), fill=(230, 230, 230))

    y = 580
    for k in ("STR", "SPD", "END", "TEC", "IQ"):
        v = int(stats.get(k, 10))
        w = max(0, min(540, int(v * 4)))
        d.text((24, y), f"{k} {v}", font=_font(22), fill=(255, 255, 255))
        d.rectangle([140, y + 4, 140 + 420, y + 22], fill=(0, 0, 0))
        d.rectangle([140, y + 4, 140 + w, y + 22], fill=(87, 242, 135))
        y += 36

    d.text((24, 830), "Crewism placeholder art", font=_font(18), fill=(200, 200, 200))

    img = _post_process_pil(img)
    # thumbnail via cv2 path also exercises resize when available
    if HAS_CV2:
        try:
            arr = np.array(img)
            small = cv2.resize(arr, (600, 900), interpolation=cv2.INTER_AREA)
            img = Image.fromarray(small)
        except Exception:
            pass
    img.save(out)
    return out


def profile_card(name: str, level: int, money: int, wins: int, losses: int) -> str:
    _ensure_cache()
    key = _hash("profile", name, str(level), str(money), str(wins), str(losses))
    out = os.path.join(CACHE_DIR, f"profile_{key}.png")
    if os.path.exists(out):
        return out
    img = Image.new("RGB", (800, 320), (30, 31, 34))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 8, 792, 312], outline=(87, 242, 135), width=3)
    d.text((30, 30), name, font=_font(40), fill=(255, 255, 255))
    d.text((30, 100), f"LV {level}   {money:,} Won", font=_font(28), fill=(230, 230, 230))
    d.text((30, 150), f"W {wins}  L {losses}", font=_font(28), fill=(180, 180, 180))
    d.text((30, 220), "CREWISM • Lookism world", font=_font(22), fill=(120, 120, 120))
    img = _post_process_pil(img)
    img.save(out)
    return out


def vs_card(left: str, right: str) -> str:
    _ensure_cache()
    key = _hash("vs", left, right)
    out = os.path.join(CACHE_DIR, f"vs_{key}.png")
    if os.path.exists(out):
        return out
    img = Image.new("RGB", (800, 400), (18, 18, 20))
    d = ImageDraw.Draw(img)
    d.text((60, 160), left[:14], font=_font(40), fill=(87, 242, 135))
    d.text((360, 150), "VS", font=_font(64), fill=(255, 255, 255))
    d.text((520, 160), right[:14], font=_font(40), fill=(237, 66, 69))
    img = _post_process_pil(img)
    img.save(out)
    return out
