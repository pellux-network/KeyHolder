"""Generates assets/icon.ico, assets/icon.png, and assets/logo.png.

Not part of the app itself — a one-off/rerunnable art generator. Run with:
    python scripts/generate_icon.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

GREEN_LIGHT = (102, 187, 106)  # bevel highlight base
GREEN_DARK = (56, 142, 60)  # bevel shadow base
GREEN_BORDER = (46, 125, 50)
WHITE = (255, 255, 255)
TEXT_DARK = (51, 51, 51)

FONT_PATH = r"C:\Windows\Fonts\segoeuib.ttf"


def _rounded_rect_mask(size, box, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
    return mask


def make_icon(canvas_size: int = 512, *, detailed: bool = True) -> Image.Image:
    # Small (taskbar-size) icons need to be bold and fill nearly the whole
    # canvas. Critically, they're rendered as their OWN flat/high-contrast
    # design (detailed=False), not produced by shrinking the big gradient
    # artwork: a smooth 512px gradient only has 16-32 rows left once
    # downsampled to taskbar size, which shows up as muddy banding instead
    # of a clean fill — see build_ico_frames().
    s = canvas_size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    margin = int(s * 0.06)
    box = [margin, margin, s - margin, s - margin]
    radius = int(s * 0.20)

    if detailed:
        fill_img = Image.new("RGB", (s, s), GREEN_LIGHT)
        grad_draw = ImageDraw.Draw(fill_img)
        top, bottom = box[1], box[3]
        for y in range(top, bottom + 1):
            t = (y - top) / max(1, (bottom - top))
            color = tuple(int(GREEN_LIGHT[i] + (GREEN_DARK[i] - GREEN_LIGHT[i]) * t) for i in range(3))
            grad_draw.line([(box[0], y), (box[2], y)], fill=color)
    else:
        fill_img = Image.new("RGB", (s, s), GREEN_DARK)

    mask = _rounded_rect_mask((s, s), box, radius)
    keycap = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    keycap.paste(fill_img, (0, 0), mask)
    img = Image.alpha_composite(img, keycap)

    # Border stroke.
    border = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        box, radius=radius, outline=GREEN_BORDER + (255,), width=max(2, int(s * 0.022))
    )
    img = Image.alpha_composite(img, border)

    if detailed:
        # Top bevel highlight (keycap light reflection) — only at sizes
        # large enough for a soft translucent rectangle to read as a
        # highlight instead of a fuzzy smear.
        highlight = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        hl_box = [
            box[0] + int(s * 0.09),
            box[1] + int(s * 0.07),
            box[2] - int(s * 0.09),
            box[1] + int(s * 0.24),
        ]
        ImageDraw.Draw(highlight).rounded_rectangle(hl_box, radius=int(s * 0.06), fill=WHITE + (70,))
        img = Image.alpha_composite(img, highlight)

    # Centered "K" glyph.
    font = ImageFont.truetype(FONT_PATH, int(s * 0.52))
    text_layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    td = ImageDraw.Draw(text_layer)
    bbox = td.textbbox((0, 0), "K", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (s - tw) / 2 - bbox[0]
    ty = (s - th) / 2 - bbox[1] + int(s * 0.01)
    td.text((tx, ty), "K", font=font, fill=WHITE + (255,))
    img = Image.alpha_composite(img, text_layer)

    return img


def make_icon_frame(target_size: int, *, detailed: bool) -> Image.Image:
    """Renders at a large supersampled canvas, then downsamples to target_size.

    This keeps edges clean (antialiased) at the final small size without
    ever passing through the detailed/gradient artwork.
    """
    supersample = max(target_size * 8, 256)
    frame = make_icon(supersample, detailed=detailed)
    return frame.resize((target_size, target_size), Image.LANCZOS)


def build_ico_frames() -> list[Image.Image]:
    flat_sizes = [16, 20, 24, 32, 40, 48]
    detailed_sizes = [64, 96, 128, 256]
    frames = [make_icon_frame(sz, detailed=False) for sz in flat_sizes]
    frames += [make_icon_frame(sz, detailed=True) for sz in detailed_sizes]
    return frames


def make_wordmark(icon: Image.Image, width: int = 900, height: int = 240) -> Image.Image:
    banner = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    icon_h = int(height * 0.8)
    icon_resized = icon.resize((icon_h, icon_h), Image.LANCZOS)
    icon_x = int(height * 0.1)
    icon_y = (height - icon_h) // 2
    banner.paste(icon_resized, (icon_x, icon_y), icon_resized)

    draw = ImageDraw.Draw(banner)
    font = ImageFont.truetype(FONT_PATH, int(height * 0.42))
    text = "KeyHolder"
    bbox = draw.textbbox((0, 0), text, font=font)
    th = bbox[3] - bbox[1]
    text_x = icon_x + icon_h + int(height * 0.18)
    text_y = (height - th) / 2 - bbox[1]
    draw.text((text_x, text_y), text, font=font, fill=TEXT_DARK + (255,))

    content_right = text_x + draw.textlength(text, font=font)
    return banner.crop((0, 0, int(content_right + height * 0.1), height))


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)

    icon = make_icon(512)
    icon.save(os.path.join(ASSETS_DIR, "icon.png"))

    frames = build_ico_frames()
    frames[-1].save(
        os.path.join(ASSETS_DIR, "icon.ico"),
        sizes=[(f.width, f.height) for f in frames],
        append_images=frames[:-1],
    )

    wordmark = make_wordmark(icon)
    wordmark.save(os.path.join(ASSETS_DIR, "logo.png"))

    print(f"Wrote {ASSETS_DIR}\\icon.png, icon.ico, logo.png")


if __name__ == "__main__":
    main()
