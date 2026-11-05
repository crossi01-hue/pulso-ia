import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys

out = sys.argv[1]
S = 2000
NAVY = (11, 37, 69)       # #0B2545
TEAL = (24, 179, 166)     # #18B3A6
WHITE = (240, 246, 252)
GREY = (150, 170, 190)

# Fondo: navy con viñeta radial (centro un poco más claro)
yy, xx = np.mgrid[0:S, 0:S]
cx = cy = S / 2
d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (S * 0.72)
d = np.clip(d, 0, 1)
base = np.array(NAVY, dtype=float)
lighter = base + np.array([10, 16, 24])
bg = (lighter[None, None, :] * (1 - d[..., None]) + (base * 0.72)[None, None, :] * d[..., None])
img = Image.fromarray(np.clip(bg, 0, 255).astype('uint8'), 'RGB').convert('RGBA')

# Capa de radar (anillos + barrido + blips)
radar = Image.new('RGBA', (S, S), (0, 0, 0, 0))
rd = ImageDraw.Draw(radar)
for r in [210, 380, 550, 720, 890]:
    rd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=TEAL + (46,), width=4)
# cruz tenue
rd.line([cx, cy - 900, cx, cy + 900], fill=TEAL + (26,), width=3)
rd.line([cx - 900, cy, cx + 900, cy], fill=TEAL + (26,), width=3)
# barrido (wedge) con degradé de alpha
sweep = Image.new('RGBA', (S, S), (0, 0, 0, 0))
sd = ImageDraw.Draw(sweep)
import math
a0 = -70  # grados
for k in range(60):
    a = a0 + k * 0.8
    x = cx + 900 * math.cos(math.radians(a))
    y = cy + 900 * math.sin(math.radians(a))
    alpha = int(70 * (k / 60))
    sd.line([cx, cy, x, y], fill=TEAL + (alpha,), width=5)
radar = Image.alpha_composite(radar, sweep)
# blips
for (bx, by, br) in [(cx + 300, cy - 360, 13), (cx - 430, cy + 210, 10), (cx + 560, cy + 430, 9)]:
    rd2 = ImageDraw.Draw(radar)
    rd2.ellipse([bx - br, by - br, bx + br, by + br], fill=TEAL + (190,))
    rd2.ellipse([bx - br*3, by - br*3, bx + br*3, by + br*3], outline=TEAL + (70,), width=3)
img = Image.alpha_composite(img, radar)

draw = ImageDraw.Draw(img)
fp = "/usr/share/fonts/truetype/dejavu/"
f_title = ImageFont.truetype(fp + "DejaVuSans-Bold.ttf", 250)
f_sub = ImageFont.truetype(fp + "DejaVuSans.ttf", 66)
f_brand = ImageFont.truetype(fp + "DejaVuSans-Bold.ttf", 50)

def centered(text, font, y, fill):
    b = draw.textbbox((0, 0), text, font=font)
    w = b[2] - b[0]; h = b[3] - b[1]
    draw.text(((S - w) / 2 - b[0], y), text, font=font, fill=fill)
    return y + h

# Título
yb = centered("Pulso IA", f_title, 760, WHITE + (255,))
# Subrayado teal
uw = 440
draw.rounded_rectangle([(S - uw) / 2, yb + 48, (S + uw) / 2, yb + 62], radius=7, fill=TEAL + (255,))
# Subtítulo
centered("Resumen semanal de inteligencia artificial", f_sub, yb + 110, GREY + (255,))
# Marca abajo
centered("por Isaligner", f_brand, 1830, TEAL + (255,))

img.convert('RGB').save(out, "JPEG", quality=90)
print("Portada OK", out)
