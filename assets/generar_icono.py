from PIL import Image, ImageDraw, ImageFont
import os

SIZES = [16, 32, 48, 64, 128, 256]

def draw_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fondo circular dorado
    margin = max(1, size // 20)
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(218, 165, 32, 255), outline=(184, 134, 11, 255), width=max(1, size // 40))

    # Corona arriba
    crown_y = size // 12
    crown_h = size // 6
    crown_w = size // 2
    crown_x = (size - crown_w) // 2
    points = [
        (crown_x, crown_y + crown_h),
        (crown_x + crown_w * 0.15, crown_y),
        (crown_x + crown_w * 0.30, crown_y + crown_h * 0.6),
        (crown_x + crown_w * 0.50, crown_y),
        (crown_x + crown_w * 0.70, crown_y + crown_h * 0.6),
        (crown_x + crown_w * 0.85, crown_y),
        (crown_x + crown_w, crown_y + crown_h),
    ]
    draw.polygon(points, fill=(255, 215, 0, 255), outline=(218, 165, 32, 255))

    # Letra R en el centro, color rojo vino
    font_size = int(size * 0.55)
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2 + size // 12
    draw.text((x, y), text, font=font, fill=(139, 0, 0, 255))

    return img

if __name__ == "__main__":
    imgs = [draw_icon(s) for s in SIZES]
    out = os.path.join(os.path.dirname(__file__), "icon.ico")
    imgs[-1].save(out, format='ICO', sizes=[(s, s) for s in SIZES])
    print(f"Icono guardado en: {out}")
