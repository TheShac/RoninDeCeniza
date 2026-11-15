"""Genera las capas del fondo con parallax (assets/images/fondos/<fondo>_<capa>.png). Estilo tinta sobre papel.

Fondo "aldea" (nivel 1, aldea en llamas): cielo con sol rojo, humo, dos cordilleras, casas con llamas y árboles secos.
Las capas en bucle son PERIÓDICAS (el borde derecho enlaza con el izquierdo): las crestas se construyen con senos de
frecuencia entera  f(x) = sum a_k sin(2 pi k x / W + fase_k)  y nada cruza el borde.

Uso (requiere Pillow):  python tools/generar_fondos.py [--preview]
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets" / "images" / "fondos"
W, H = 960, 544
SS = 2                                   # supersampling


def ridge(width, base, amps, seed):
    rnd = random.Random(seed)
    phases = [rnd.uniform(0, 2 * math.pi) for _ in amps]
    return [base + sum(a * math.sin(2 * math.pi * (k + 1) * x / width + ph) for k, (a, ph) in enumerate(zip(amps, phases)))
            for x in range(width + 1)]


def down(img):
    return img.resize((img.width // SS, img.height // SS), Image.LANCZOS)


def sky():
    img = Image.new("RGBA", (W, H))
    px = img.load()
    top, mid, low = (226, 210, 190), (232, 196, 160), (226, 150, 112)
    for y in range(H):
        t = y / (H - 1)
        a, b, u = (top, mid, t / 0.55) if t < 0.55 else (mid, low, (t - 0.55) / 0.45)
        c = tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3))
        for x in range(W):
            px[x, y] = c + (255,)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((600 - 170, 160 - 170, 600 + 170, 160 + 170), fill=(214, 90, 60, 90))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
    sun = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    ImageDraw.Draw(sun).ellipse(((600 - 62) * SS, (160 - 62) * SS, (600 + 62) * SS, (160 + 62) * SS), fill=(176, 38, 38, 235))
    img.alpha_composite(down(sun))
    return img


def smoke(width=1280, height=300):
    rnd = random.Random(5)
    big = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for _ in range(26):                       # nubes de humo: elipses translúcidas; se dibuja una copia desplazada para el bucle
        cx, cy = rnd.uniform(0, width), rnd.uniform(40, 200)
        rx, ry = rnd.uniform(70, 190), rnd.uniform(16, 34)
        shade = rnd.randint(96, 130)
        for dx in (-width, 0, width):
            d.ellipse(((cx + dx - rx) * SS, (cy - ry) * SS, (cx + dx + rx) * SS, (cy + ry) * SS), fill=(shade, shade - 6, shade - 10, rnd.randint(40, 80)))
    return down(big.filter(ImageFilter.GaussianBlur(10 * SS)))


def mountains(width, height, base, amps, color, seed, mist):
    ys = ridge(width, base, amps, seed)
    big = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.polygon([(x * SS, y * SS) for x, y in enumerate(ys)] + [(width * SS, height * SS), (0, height * SS)], fill=color)
    img = down(big)
    fog = Image.new("RGBA", (width, height), (0, 0, 0, 0))               # niebla al pie de la cordillera
    ImageDraw.Draw(fog).rectangle((0, height * 0.62, width, height), fill=(238, 232, 218, mist))
    img.alpha_composite(fog.filter(ImageFilter.GaussianBlur(18)))
    return img


def house(d, x, ground, w, h, roof, body, seed):
    rnd = random.Random(seed)
    d.rectangle((x, ground - h, x + w, ground), fill=body)
    for wx in range(int(x + 8), int(x + w - 8), 18):                      # postes de madera
        d.line((wx * 1, ground - h, wx, ground), fill=(60, 50, 48, 255), width=2)
    ov = 14
    d.polygon([(x - ov, ground - h + 4), (x + w / 2, ground - h - h * 0.62), (x + w + ov, ground - h + 4),
               (x + w + ov - 6, ground - h + 12), (x + w / 2, ground - h - h * 0.45), (x - ov + 6, ground - h + 12)], fill=roof)


def flame(d, cx, base, size, rnd):
    for s, col in ((1.0, (206, 80, 38, 255)), (0.62, (240, 150, 50, 255)), (0.3, (252, 214, 110, 255))):
        h = size * s
        d.polygon([(cx - h * 0.42, base), (cx - h * 0.2, base - h * 0.55), (cx + rnd.uniform(-0.15, 0.15) * h, base - h),
                   (cx + h * 0.24, base - h * 0.5), (cx + h * 0.42, base)], fill=col)


def village(width=1536, height=244):
    rnd = random.Random(11)
    big = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    ground = (height - 6) * SS
    x = 40.0
    n = 0
    fires = []
    while x < width - 190:
        w, h = rnd.randint(80, 130), rnd.randint(46, 74)
        burning = n % 2 == 1
        roof = (74, 64, 62, 255) if not burning else (58, 46, 44, 255)
        sc = lambda v: v * SS
        house(d, sc(x), ground, sc(w), sc(h), roof, (112, 98, 92, 255), n)
        # (house usa postes con ancho 2: se reescala sin problema)
        if burning:
            fires.append((x + w * 0.5, ground / SS - h, h))
        x += w + rnd.randint(30, 80)
        n += 1
    out = down(big)
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for fx, fy, h in fires:
        gd.ellipse((fx - 70, fy - 60, fx + 70, fy + 40), fill=(230, 110, 40, 90))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)))
    fb = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fb)
    for fx, fy, h in fires:
        for k in range(3):
            flame(fd, (fx + (k - 1) * 22) * SS, (fy + 6) * SS, rnd.uniform(34, 56) * SS, rnd)
    out.alpha_composite(down(fb))
    return out


def trees(width=1920, height=294):
    rnd = random.Random(23)
    big = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    ink = (52, 44, 44, 255)
    def branch(x, y, ang, ln, wd, depth):
        x2, y2 = x + math.cos(ang) * ln, y - math.sin(ang) * ln
        d.line((x * SS, y * SS, x2 * SS, y2 * SS), fill=ink, width=max(1, int(wd * SS)))
        if depth > 0:
            for da in (-rnd.uniform(0.35, 0.8), rnd.uniform(0.35, 0.8)):
                branch(x2, y2, ang + da, ln * rnd.uniform(0.62, 0.78), wd * 0.68, depth - 1)
    for tx in (140, 520, 900, 1300, 1700):
        branch(tx, height - 4, math.pi / 2 + rnd.uniform(-0.1, 0.1), rnd.uniform(70, 95), 7, 5)
    return down(big)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    layers = {
        "cielo": sky(),
        "humo": smoke(),
        "montanas_lejos": mountains(1280, 354, 150, (36, 22, 12, 6), (186, 176, 170, 235), 3, 150),
        "montanas_cerca": mountains(1280, 294, 120, (30, 18, 10, 5), (140, 128, 124, 245), 8, 170),
        "aldea": village(),
        "arboles": trees(),
    }
    for name, img in layers.items():
        img.save(OUT / f"aldea_{name}.png")
        print("escrito", name, img.size)
    if "--preview" in sys.argv:
        prev = Image.new("RGBA", (W, H), (238, 232, 218, 255))
        for name, y in (("cielo", 0), ("humo", 0), ("montanas_lejos", 190), ("montanas_cerca", 250), ("aldea", 250), ("arboles", 196)):
            layer = layers[name].crop((0, 0, W, layers[name].height))
            prev.alpha_composite(layer.crop((0, 0, W, min(layer.height, H - y))), (0, y))      # la vista previa mide 960x544
        prev.convert("RGB").save(Path(__file__).resolve().parent.parent / "docs" / "img" / "fondo_aldea.png")


if __name__ == "__main__":
    build()
