from PIL import Image
import os

SIZES = [16, 32, 48, 64, 128, 256]


def draw_icon(size, source):
    return source.resize((size, size), Image.Resampling.LANCZOS).convert('RGBA')


if __name__ == "__main__":
    src_path = os.path.join(os.path.dirname(__file__), "icon_source.png")
    source = Image.open(src_path).convert('RGBA')

    imgs = [draw_icon(s, source) for s in SIZES]
    out = os.path.join(os.path.dirname(__file__), "icon.ico")
    imgs[-1].save(
        out,
        format='ICO',
        sizes=[(s, s) for s in SIZES],
        append_images=imgs[:-1],
    )
    print(f"Icono guardado en: {out}")
