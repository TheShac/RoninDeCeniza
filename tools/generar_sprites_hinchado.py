"""Genera las hojas de sprites del zombi hinchado (assets/images/zombi/hinchado/sumo_<animación>.png).

Es un luchador de sumo zombi, enorme y de frente: piel pálida con tatuajes de higanbana (la flor de la muerte)
y sangre, piel desgarrada, pantalón blanco ancho, faja roja con colas, collar de cuentas, muñequeras, moño y
pequeños cuernos. El cuerpo es UNA sola silueta continua (hombros, brazos y manos salen del mismo contorno).

Cada cuadro mide 160x128 px (más grande que los 96x96 del resto) y el cuerpo es simétrico, así que no hace
falta voltearlo. Animaciones: idle (4), walk (6), inflate (5), explode (5), hurt (2).
Al morir no hay animación de muerte aparte: el hinchado EXPLOTA.

Cómo se anima (sin huesos): cada forma se define con puntos en el espacio del dibujo original y cada punto pasa
por una función de deformación ("warp") que depende de la pose:
  * inflar : escala radial alrededor del vientre, con caída gaussiana  f = inf * exp(-d^2 / (2*95^2))
  * brazos : rotación alrededor del hombro, con peso suave (smoothstep) para que el brazo se doble sin romperse
  * piernas: la pierna se levanta más cuanto más abajo está el punto
  * cuerpo : rotación, escala vertical y traslación alrededor de los pies

Uso (requiere Pillow, ver requirements-dev.txt):
  python tools/generar_sprites_hinchado.py             # regenera las hojas
  python tools/generar_sprites_hinchado.py --preview   # además genera docs/img/zombi_hinchado.png
"""
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

FW, FH = 160, 128            # tamaño de cada cuadro (px)
SS = 4                       # supersampling
SCALE = 0.2                  # px por unidad del dibujo original
OX, OY = 80, 124             # dónde cae el punto (340, 400) del dibujo (centro de los pies) dentro del cuadro

SKIN = (217, 210, 189, 255)
SKIN_SH = (184, 176, 154, 255)
INK = (31, 30, 24, 255)
BLOOD = (168, 36, 42, 255)
BLOOD_DK = (110, 22, 30, 255)
FLESH = (122, 31, 42, 255)
FLESH_LT = (168, 36, 42, 255)
FLAP = (201, 193, 171, 255)
PANTS = (230, 226, 212, 255)
PANTS_SH = (201, 196, 176, 255)
SASH = (107, 34, 48, 255)
SASH_KNOT = (125, 42, 58, 255)
GOLD = (216, 178, 74, 255)
HAIR = (28, 32, 56, 255)
BONE = (232, 224, 200, 255)
BAND = (138, 74, 42, 255)
BEAD = (90, 61, 36, 255)
PAINT = (239, 233, 214, 255)
PETAL = (194, 48, 68, 255)
PETAL_DK = (110, 16, 32, 255)
WASH = (216, 52, 63, 255)

BODY_D = ("M300 112 Q250 118 200 142 Q150 170 128 225 Q112 270 112 300 L108 328 Q90 350 84 376 L80 396 L96 400 "
          "L101 380 L106 404 L122 406 L124 384 L132 408 L147 404 L146 380 L156 398 L168 390 L160 356 "
          "Q166 340 164 326 Q166 290 176 258 Q186 230 222 210 Q206 250 212 300 Q270 332 340 332 "
          "Q410 332 468 300 Q474 250 458 210 Q494 230 504 258 Q514 290 516 326 Q514 340 520 356 L512 390 "
          "L524 398 L534 380 L533 404 L548 408 L556 384 L558 406 L574 404 L579 380 L584 400 L600 396 "
          "L596 376 Q590 350 572 328 L568 300 Q568 270 552 225 Q530 170 480 142 Q430 118 380 112 "
          "Q340 120 300 112 Z")
PANTS_L_D = "M215 296 L345 296 L352 392 L148 392 Q170 340 215 296 Z"
PANTS_R_D = "M465 296 L335 296 L328 392 L532 392 Q510 340 465 296 Z"
SASH_D = "M208 288 Q340 320 472 288 L476 318 Q340 348 204 318 Z"
PETAL_D = "M0 0 C8 -8 22 -10 30 -26 C22 -22 14 -22 8 -14 C12 -24 8 -32 2 -36 C-2 -24 -4 -10 0 0 Z"
JAG = [(0, -17), (5, -10), (14, -13), (10, -4), (18, 1), (9, 5), (12, 14), (3, 10), (-2, 18), (-6, 10),
       (-15, 13), (-10, 3), (-18, -3), (-9, -6), (-12, -15), (-4, -10)]
# piel desgarrada: (x, y, escala) en coordenadas del dibujo
TORN = [(392, 246, 1.0), (268, 262, 0.7), (420, 196, 0.75), (352, 192, 0.65), (338, 280, 0.6), (236, 196, 0.6)]
# flores de higanbana: (x, y, escala, rotación)
FLOWERS = [(204, 180, 0.95, 0), (476, 180, 0.95, 40), (140, 278, 0.55, 20), (540, 278, 0.55, -20),
           (296, 226, 0.6, 10)]


# ---------------------------------------------------------------- geometría
def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def path_points(d, steps=8):
    """Aplana un camino SVG (M L Q C Z, coordenadas absolutas) a una lista de puntos."""
    tokens = re.findall(r"[MLQCZ]|-?\d+\.?\d*", d)
    pts, i, cmd, cur = [], 0, None, (0.0, 0.0)
    while i < len(tokens):
        if tokens[i] in "MLQCZ":
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                continue
        n = {"M": 1, "L": 1, "Q": 2, "C": 3}[cmd]
        nums = [float(t) for t in tokens[i:i + 2 * n]]
        i += 2 * n
        p = [(nums[k], nums[k + 1]) for k in range(0, len(nums), 2)]
        if cmd in "ML":
            pts.append(p[0])
        elif cmd == "Q":
            for s in range(1, steps + 1):
                t = s / steps
                pts.append(((1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * p[0][0] + t * t * p[1][0],
                            (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * p[0][1] + t * t * p[1][1]))
        else:
            for s in range(1, steps + 1):
                t = s / steps
                u = 1 - t
                pts.append((u ** 3 * cur[0] + 3 * u * u * t * p[0][0] + 3 * u * t * t * p[1][0] + t ** 3 * p[2][0],
                            u ** 3 * cur[1] + 3 * u * u * t * p[0][1] + 3 * u * t * t * p[1][1] + t ** 3 * p[2][1]))
        cur = pts[-1]
    return pts


def place(pts, x, y, s=1.0, rot=0.0):
    """Escala, gira (grados, horario en pantalla) y traslada una forma."""
    c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [(x + s * (px * c - py * sn), y + s * (px * sn + py * c)) for px, py in pts]


@dataclass
class Pose:
    dx: float = 0.0          # traslación horizontal del cuerpo (unidades del dibujo)
    dy: float = 0.0          # traslación vertical
    rot: float = 0.0         # inclinación del cuerpo alrededor de los pies (grados)
    sy: float = 1.0          # escala vertical alrededor de los pies
    inf: float = 0.0         # hinchazón del vientre (0 = normal)
    glow: float = 0.0        # brillo de las heridas (0 = apagado, 1 = a punto de reventar)
    arm_l: float = 0.0       # giro del brazo izquierdo hacia afuera (grados)
    arm_r: float = 0.0
    lift_l: float = 0.0      # cuánto sube el pie izquierdo / derecho
    lift_r: float = 0.0
    head_dx: float = 0.0
    head_dy: float = 0.0
    hit: bool = False        # destello blanco al recibir un golpe
    fade: float = 1.0        # opacidad del cuerpo (para la explosión)


def rotate_about(x, y, cx, cy, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c


def make_warps(pose):
    """Devuelve (upper, head, leg_l, leg_r): funciones que deforman un punto del dibujo según la pose."""

    def body(x, y):
        x = x + 0.0
        x += pose.dx
        y = y + pose.dy
        x, y = rotate_about(x, y, 340 + pose.dx, 400, pose.rot)
        return x, 400 + (y - 400) * pose.sy

    def upper(p):
        x, y = p
        cx, cy = 340.0, 245.0
        f = pose.inf * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 95.0 ** 2))
        x, y = cx + (x - cx) * (1 + f), cy + (y - cy) * (1 + f * 0.8)
        wl = smoothstep(180, 240, y) * (1 - smoothstep(176, 214, x))
        wr = smoothstep(180, 240, y) * smoothstep(466, 504, x)
        if wl:
            x, y = rotate_about(x, y, 205, 150, pose.arm_l * wl)
        if wr:
            x, y = rotate_about(x, y, 475, 150, -pose.arm_r * wr)
        return body(x, y)

    def head(p):
        return upper((p[0] + pose.head_dx, p[1] + pose.head_dy)) if False else body(*upper_nohead(p))

    def upper_nohead(p):
        return p[0] + pose.head_dx, p[1] + pose.head_dy

    def leg(lift):
        def w(p):
            x, y = p
            return body(x, y - lift * smoothstep(296, 392, y))
        return w

    return upper, head, leg(pose.lift_l), leg(pose.lift_r)


# ---------------------------------------------------------------- lienzo
class Canvas:
    def __init__(self):
        self.img = Image.new("RGBA", (FW * SS, FH * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    @staticmethod
    def px(p):
        return ((OX + (p[0] - 340) * SCALE) * SS, (OY + (p[1] - 400) * SCALE) * SS)

    def poly(self, pts, fill, outline=None, width=1.1, draw=None):
        d = draw or self.d
        q = [self.px(p) for p in pts]
        d.polygon(q, fill=fill)
        if outline:
            d.line(q + [q[0]], fill=outline, width=max(1, int(width * SS)), joint="curve")

    def line(self, pts, color, width, draw=None):
        d = draw or self.d
        q = [self.px(p) for p in pts]
        d.line(q, fill=color, width=max(1, int(width * SS)), joint="curve")
        for x, y in (q[0], q[-1]):
            r = width * SS / 2
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def circle(self, c, r, color, draw=None):
        d = draw or self.d
        x, y = self.px(c)
        rr = r * SCALE * SS
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color)

    def ellipse(self, c, rx, ry, color, outline=None, width=1.0, draw=None):
        d = draw or self.d
        x, y = self.px(c)
        a, b = rx * SCALE * SS, ry * SCALE * SS
        d.ellipse((x - a, y - b, x + a, y + b), fill=color, outline=outline, width=max(1, int(width * SS)))

    def final(self):
        return self.img.resize((FW, FH), Image.LANCZOS)


def flower_layer(cv, layer_draw, warp, x, y, s, rot):
    """Higanbana: seis estambres largos con punta y seis pétalos rizados."""
    for k in range(6):
        a = 20 + 60 * k + rot
        curve = []
        for t in [i / 8 for i in range(9)]:
            u = 1 - t
            px = u ** 3 * 0 + 3 * u * u * t * 8 + 3 * u * t * t * 26 + t ** 3 * 36
            py = u ** 3 * 0 + 3 * u * u * t * -18 + 3 * u * t * t * -26 + t ** 3 * -46
            curve.append((px, py))
        pts = [warp(p) for p in place(curve, x, y, s, a)]
        cv.line(pts, BLOOD, 0.9, layer_draw)
        cv.circle(pts[-1], 2.6 * s, BLOOD_DK, layer_draw)
    for k in range(6):
        pts = [warp(p) for p in place(path_points(PETAL_D), x, y, s, 60 * k + rot)]
        cv.poly(pts, PETAL, PETAL_DK, 0.7, layer_draw)
    cv.circle(warp((x, y)), 5 * s, BLOOD_DK, layer_draw)


def torn_skin(cv, warp, x, y, s, pose):
    """Piel desgarrada: borde de piel levantada y carne roja; brilla al hincharse."""
    grow = 1 + 0.6 * pose.inf
    pts = [warp(p) for p in place(JAG, x, y, s * grow)]
    cv.poly(pts, FLAP, INK, 0.7)
    flesh = tuple(int(FLESH[i] + (255 - FLESH[i]) * pose.glow * k) for i, k in enumerate((0.9, 0.7, 0.2))) + (255,)
    hot = (255, int(190 + 50 * pose.glow), int(60 + 90 * pose.glow), 255)
    c = warp((x, y))
    cv.ellipse(c, 9 * s * grow, 8 * s * grow, flesh)
    cv.ellipse((c[0] - 1 * s, c[1] + 1 * s), 5 * s * grow, 4 * s * grow, hot if pose.glow > 0.35 else FLESH_LT)


# ---------------------------------------------------------------- el zombi
def draw_zombie(pose):
    cv = Canvas()
    upper, head_w, leg_l, leg_r = make_warps(pose)
    body = Canvas()                                              # el cuerpo va en su propia capa (para el desvanecido)
    cv_ = body

    # pies y pantalón
    for cx, w in ((172, leg_l), (508, leg_r)):
        foot = [(cx + 42 * math.cos(a / 12 * math.pi), 396 + 11 * math.sin(a / 12 * math.pi)) for a in range(24)]
        cv_.poly([w(p) for p in foot], SKIN, INK, 1.1)
    for d, w in ((PANTS_L_D, leg_l), (PANTS_R_D, leg_r)):
        cv_.poly([w(p) for p in path_points(d)], PANTS, INK, 1.2)
    for pts, w in (([(250, 330), (270, 350), (262, 385)], leg_l), ([(430, 330), (410, 350), (418, 385)], leg_r)):
        cv_.line([w(p) for p in pts], PANTS_SH, 1.0)

    # silueta continua del cuerpo
    outline = [upper(p) for p in path_points(BODY_D)]
    cv_.poly(outline, SKIN, INK, 1.2)
    # sombras de las articulaciones y el pecho (líneas dentro de la piel)
    for pts in ([(196, 150), (176, 190), (186, 232)], [(484, 150), (504, 190), (494, 232)],
                [(130, 232), (152, 252), (174, 246)], [(550, 232), (528, 252), (506, 246)],
                [(116, 292), (140, 286), (168, 296)], [(564, 292), (540, 286), (512, 296)],
                [(340, 150), (340, 236)], [(234, 216), (290, 256), (340, 240)], [(446, 216), (390, 256), (340, 240)],
                [(236, 288), (340, 322), (444, 288)]):
        cv_.line([upper(p) for p in pts], SKIN_SH, 0.8)

    # capa de tatuajes, sangre y piel desgarrada, recortada a la silueta
    mask = Image.new("L", cv_.img.size, 0)
    ImageDraw.Draw(mask).polygon([cv_.px(p) for p in outline], fill=255)
    layer = Image.new("RGBA", cv_.img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    wash_alpha = (WASH[0], WASH[1], WASH[2], 128)
    for blob in ([(150, 160), (210, 140), (250, 170), (262, 214), (220, 226), (170, 232), (150, 200)],
                 [(530, 160), (470, 140), (430, 170), (418, 214), (460, 226), (510, 232), (530, 200)],
                 [(112, 248), (150, 240), (168, 262), (170, 300), (140, 308), (112, 296)],
                 [(568, 248), (530, 240), (512, 262), (510, 300), (540, 308), (568, 296)],
                 [(262, 200), (310, 196), (330, 226), (320, 256), (286, 252), (256, 240)]):
        cv_.poly([upper(p) for p in blob], wash_alpha, None, 0, ld)
    for x, y, s, r in FLOWERS:
        flower_layer(cv_, ld, upper, x, y, s, r)
    for pts in ([(230, 218), (214, 250), (196, 290)], [(452, 218), (466, 250), (484, 290)]):
        cv_.line([upper(p) for p in pts], (90, 107, 42, 255), 1.1, ld)                      # tallos
    for pts in ([(250, 150), (226, 232)], [(262, 160), (248, 204)], [(410, 160), (428, 214)], [(440, 150), (452, 230)],
                [(196, 214), (196, 246)], [(148, 300), (150, 324)], [(486, 214), (486, 252)], [(532, 300), (530, 322)],
                [(300, 262), (302, 300)]):
        cv_.line([upper(p) for p in pts], BLOOD, 0.9, ld)
        cv_.circle(upper(pts[-1]), 4.0, BLOOD, ld)
    for x, y, s in TORN:
        torn_skin(cv_, upper, x, y, s, pose)
        # lo de arriba se dibujó directo; lo repetimos en la capa recortada para que no se salga del cuerpo
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    cv_.img.alpha_composite(layer)

    # faja, colas y cuentas
    cv_.poly([upper(p) for p in path_points(SASH_D)], SASH, INK, 1.2)
    for pts in ([(338, 330), (316, 398), (334, 394), (350, 342)], [(352, 330), (372, 396), (388, 390), (368, 338)]):
        cv_.poly([upper(p) for p in pts], SASH, INK, 0.9)
    cv_.circle(upper((345, 326)), 14, SASH_KNOT)
    for p in ((325, 400), (380, 396)):
        cv_.circle(upper(p), 5, GOLD)
    for k in range(11):
        t = k / 10
        bx = 276 + 128 * t
        by = 140 + 4 * 4 * 13 * t * (1 - t)
        cv_.circle(upper((bx, by)), 5.2, BEAD)

    # cabeza (sigue al cuerpo y se mueve un poco por su cuenta)
    def hw(p):
        return upper((p[0] + pose.head_dx, p[1] + pose.head_dy))

    for pts in ([(288, 92), (276, 70), (300, 82)], [(392, 92), (404, 70), (380, 82)]):
        cv_.poly([hw(p) for p in pts], BONE, INK, 0.9)
    face = [(340 + 54 * math.cos(a / 24 * 2 * math.pi), 108 + 46 * math.sin(a / 24 * 2 * math.pi)) for a in range(24)]
    cv_.poly([hw(p) for p in face], SKIN, INK, 1.2)
    cv_.poly([hw(p) for p in path_points("M284 98 Q284 54 340 52 Q396 54 396 98 Q370 78 340 80 Q310 78 284 98 Z")],
             HAIR, INK, 0.9)
    cv_.poly([hw(p) for p in [(330, 56), (320, 26), (337, 42), (346, 18), (352, 44), (370, 30), (360, 58)]], HAIR, INK, 0.9)
    cv_.poly([hw(p) for p in path_points("M298 88 Q340 74 382 88 L380 100 Q340 90 300 100 Z")], PAINT, INK, 0.9)
    for x in (313, 327, 340, 353, 367):
        cv_.line([hw((x, 89)), hw((x, 97))], BLOOD, 0.6)
    for pts in ([(310, 106), (334, 114)], [(370, 106), (346, 114)]):
        cv_.line([hw(p) for p in pts], (58, 16, 16, 255), 1.0)
    eye = (232, 230, 168, 255) if pose.glow < 0.5 else (255, 210, 90, 255)
    for x in (324, 356):
        cv_.ellipse(hw((x, 120)), 7, 5, eye, INK, 0.5)
        cv_.circle(hw((x, 121)), 2.5, BLOOD)
    cv_.line([hw(p) for p in [(336, 124), (334, 132), (346, 132)]], (141, 133, 112, 255), 0.6)
    cv_.poly([hw(p) for p in path_points("M316 140 Q340 132 364 140 Q356 156 340 156 Q324 156 316 140 Z")],
             (138, 42, 42, 255), INK, 0.6)
    for pts in ([(322, 141), (326, 132), (329, 142)], [(358, 141), (354, 132), (351, 142)]):
        cv_.poly([hw(p) for p in pts], (241, 235, 214, 255))
    for pts in ([(322, 98), (318, 110)], [(358, 98), (362, 110)]):
        cv_.line([hw(p) for p in pts], BLOOD, 0.7)

    # muñequeras
    for pts in ([(110, 306), (165, 310), (164, 332), (107, 327)], [(570, 306), (515, 310), (516, 332), (573, 327)]):
        cv_.poly([upper(p) for p in pts], BAND, INK, 0.8)

    img = cv_.img
    if pose.fade < 1.0:
        a = img.getchannel("A").point(lambda v: int(v * pose.fade))
        img.putalpha(a)
    if pose.hit:                                                  # destello blanco sobre el cuerpo
        white = Image.new("RGBA", img.size, (255, 250, 240, 255))
        white.putalpha(ImageChops.multiply(img.getchannel("A"), Image.new("L", img.size, 70)))
        img.alpha_composite(white)
    cv.img.alpha_composite(img)
    return cv


# ---------------------------------------------------------------- animaciones
def finish(cv):
    return cv.final()


def anim_idle():
    frames = []
    for i in range(4):
        p = 2 * math.pi * i / 4
        frames.append(finish(draw_zombie(Pose(inf=0.02 * math.sin(p) + 0.02, sy=1 + 0.006 * math.sin(p),
                                              arm_l=3 + 2 * math.sin(p), arm_r=3 + 2 * math.sin(p),
                                              head_dy=2 * math.sin(p), glow=0.08))))
    return frames


def anim_walk():
    """Camina balanceándose: el peso pasa de un pie al otro y el cuerpo se inclina hacia el pie de apoyo."""
    frames = []
    for i in range(6):
        p = 2 * math.pi * i / 6
        s = math.sin(p)
        frames.append(finish(draw_zombie(Pose(
            dx=8 * s, dy=-6 * abs(s), rot=3.0 * s, inf=0.03, glow=0.1,
            lift_l=30 * max(0.0, s), lift_r=30 * max(0.0, -s),
            arm_l=6 - 5 * s, arm_r=6 + 5 * s, head_dx=-4 * s, head_dy=2 * abs(s)))))
    return frames


def anim_inflate():
    """Se hincha y tiembla, con los brazos abiertos y las heridas al rojo vivo (a punto de reventar)."""
    frames = []
    for i in range(5):
        t = i / 4
        shake = 5 * (1 if i % 2 else -1) * (0.4 + t)
        frames.append(finish(draw_zombie(Pose(
            dx=shake, inf=0.08 + 0.5 * t, glow=0.25 + 0.75 * t, arm_l=8 + 18 * t, arm_r=8 + 18 * t,
            head_dy=-4 * t, sy=1 - 0.03 * t))))
    return frames


def blast(cv, radius, color, alpha, center=(340, 225)):
    layer = Image.new("RGBA", cv.img.size, (0, 0, 0, 0))
    x, y = Canvas.px(center)
    r = radius * SCALE * SS
    ImageDraw.Draw(layer).ellipse((x - r, y - r, x + r, y + r), fill=color[:3] + (alpha,))
    cv.img.alpha_composite(layer)


def chunk(cv, p, size, color):
    x, y = p
    pts = [(x - size, y - size * 0.4), (x, y - size), (x + size * 0.9, y - size * 0.2), (x + size * 0.2, y + size)]
    cv.poly(pts, color, INK, 0.6)


def anim_explode():
    """Explosión en 5 cuadros: el cuerpo revienta, bola de fuego, pedazos que salen despedidos, humo."""
    frames = []
    cv = draw_zombie(Pose(inf=0.62, glow=1.0, arm_l=28, arm_r=28, head_dy=-6, dx=4))
    blast(cv, 90, (255, 235, 140, 255), 70, (340, 260))
    frames.append(finish(cv))
    cv = draw_zombie(Pose(inf=0.9, glow=1.0, arm_l=40, arm_r=40, head_dy=-12, fade=0.55))
    blast(cv, 215, (255, 250, 220, 255), 235)
    blast(cv, 150, (255, 190, 70, 255), 255)
    frames.append(finish(cv))
    cv = Canvas()
    blast(cv, 300, (230, 90, 30, 255), 150)
    blast(cv, 235, (255, 160, 50, 255), 235)
    blast(cv, 130, (255, 225, 120, 255), 255)
    for p, s, col in (((170, 230), 14, FLAP), ((520, 220), 16, SKIN), ((230, 110), 12, BLOOD_DK), ((450, 100), 13, BONE),
                      ((340, 60), 11, SASH), ((120, 330), 12, PANTS), ((560, 330), 12, BLOOD)):
        chunk(cv, p, s, col)
    frames.append(finish(cv))
    cv = Canvas()
    blast(cv, 320, (110, 40, 28, 255), 120)
    blast(cv, 260, (236, 120, 40, 255), 170)
    blast(cv, 140, (255, 200, 90, 255), 150)
    for p, s, col in (((110, 260), 12, FLAP), ((570, 260), 14, SKIN), ((190, 70), 10, BLOOD_DK), ((490, 60), 11, BONE),
                      ((90, 380), 11, PANTS), ((590, 380), 10, BLOOD)):
        chunk(cv, p, s, col)
    frames.append(finish(cv))
    cv = Canvas()
    blast(cv, 330, (60, 52, 48, 255), 70)
    blast(cv, 240, (90, 80, 72, 255), 60)
    for p, s, col in ((  (110, 350), 9, BLOOD_DK), ((570, 360), 9, BLOOD_DK), ((340, 396), 8, BLOOD)):
        chunk(cv, p, s, col)
    frames.append(finish(cv))
    return frames


def anim_hurt():
    frames = []
    for i, (rot, dx) in enumerate(((-5.0, -10.0), (-3.0, -6.0))):
        frames.append(finish(draw_zombie(Pose(rot=rot, dx=dx, inf=0.05, glow=0.45, arm_l=14, arm_r=14,
                                              head_dx=-8, head_dy=4, hit=(i == 0)))))
    return frames


ANIMS = {"idle": anim_idle, "walk": anim_walk, "inflate": anim_inflate, "explode": anim_explode, "hurt": anim_hurt}
VARIANTS = ("sumo",)


def save_strip(frames, path):
    strip = Image.new("RGBA", (FW * len(frames), FH), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * FW, 0))
    strip.save(path)


def save_preview(todo, path, zoom=1):
    paper = (238, 232, 218, 255)
    label_w = 90
    cols = max(len(f) for f in todo.values())
    cw, ch = FW * zoom, FH * zoom
    sheet = Image.new("RGBA", (label_w + cols * cw, len(todo) * ch), paper)
    draw = ImageDraw.Draw(sheet)
    for r, (name, frames) in enumerate(todo.items()):
        draw.text((8, r * ch + ch // 2 - 6), name, fill=(24, 24, 28, 255))
        draw.line([(0, r * ch), (sheet.width, r * ch)], fill=(214, 206, 188, 255))
        for c, f in enumerate(frames):
            sheet.alpha_composite(f.resize((cw, ch), Image.LANCZOS) if zoom != 1 else f, (label_w + c * cw, r * ch))
    sheet.save(path)


def main():
    raiz = Path(__file__).resolve().parent.parent
    out = raiz / "assets" / "images" / "zombi" / "hinchado"
    out.mkdir(parents=True, exist_ok=True)
    todo = {}
    for variant in VARIANTS:
        for name, build in ANIMS.items():
            frames = build()
            todo[f"{variant} {name}"] = frames
            save_strip(frames, out / f"{variant}_{name}.png")
            print(f"hinchado/{variant}_{name}.png: {len(frames)} cuadros")
    if "--preview" in sys.argv[1:]:
        destino = raiz / "docs" / "img"
        destino.mkdir(parents=True, exist_ok=True)
        save_preview(todo, destino / "zombi_hinchado.png", 2)
        print("docs/img/zombi_hinchado.png generado")


if __name__ == "__main__":
    main()
