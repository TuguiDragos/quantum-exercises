"""Converts readme-assets screenshots to WebP in website/static/images, cropped to the window
(dropping the macOS shadow; the page draws its own). Run:
uv run --with pillow python website/tools/make_images.py"""

from pathlib import Path

from PIL import Image

repo = Path(__file__).resolve().parents[2]
images = repo / "website/static/images"
images.mkdir(parents=True, exist_ok=True)
SHOTS = ["05-vscode-split", "07-qx-watch", "06-vscode-notebook", "08-real-hardware", "04-qx-doctor"]
for name in SHOTS:
    im = Image.open(repo / "readme-assets" / f"{name}.png").convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a == 255 else 0).getbbox())
    # Premultiplied alpha, or the transparent corners bleed a dark fringe.
    premultiplied = im.convert("RGBa")
    for old in images.glob(f"{name}-*.webp"):
        old.unlink()
    for w in sorted({800, 1200, min(1600, im.width)}):
        h = round(im.height * w / im.width)
        resized = premultiplied.resize((w, h), Image.LANCZOS).convert("RGBA")
        resized.save(images / f"{name}-{w}.webp", "WEBP", quality=80, alpha_quality=90, method=6)
    print(name, im.size)
