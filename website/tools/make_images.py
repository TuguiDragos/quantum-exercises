"""Makes the screenshots the website shows from the repository's readme-assets, as WebP at the
widths the page asks for, into website/static/images. Run it again only when a screenshot changes:
uv run --with pillow python website/tools/make_images.py

A screenshot of a macOS window carries the shadow macOS draws around it, on a transparent margin.
The page draws its own shadow, so each picture is cut to the window, and its rounded corners stay
transparent rather than turning into black ones."""

from pathlib import Path

from PIL import Image

repo = Path(__file__).resolve().parents[2]
images = repo / "website/static/images"
images.mkdir(parents=True, exist_ok=True)
SHOTS = ["05-vscode-split", "07-qx-watch", "06-vscode-notebook", "08-real-hardware", "04-qx-doctor"]
for name in SHOTS:
    im = Image.open(repo / "readme-assets" / f"{name}.png").convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a == 255 else 0).getbbox())
    # Scaled with the alpha premultiplied, or the transparent corners bleed a dark fringe
    # into the edge.
    premultiplied = im.convert("RGBa")
    for old in images.glob(f"{name}-*.webp"):
        old.unlink()
    for w in sorted({800, 1200, min(1600, im.width)}):
        h = round(im.height * w / im.width)
        resized = premultiplied.resize((w, h), Image.LANCZOS).convert("RGBA")
        resized.save(images / f"{name}-{w}.webp", "WEBP", quality=80, alpha_quality=90, method=6)
    print(name, im.size)
