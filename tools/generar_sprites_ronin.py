"""Genera las hojas de sprites del Ronin (assets/images/ronin/*.png).

Cada animación es una tira horizontal de cuadros de 96x96 px con fondo transparente.
El personaje se dibuja mirando a la DERECHA; en el juego se voltea para mirar a la izquierda.

Diseño: un ronin errante de rostro cubierto, sombrero de paja (kasa) con moño, capa raída de bordes
desgarrados, bufanda y cinto de cuerda rojos, hombreras, antebrazos protegidos y varias katanas.

Cómo funciona (útil para el informe, trigonometría y movimiento rotacional):
  el cuerpo es un esqueleto de segmentos. Cada extremidad se define por ángulos (cinemática directa):
  posición de la articulación = posición anterior + longitud * (sen(ángulo), cos(ángulo)).
  Los ángulos se miden desde la vertical hacia abajo; positivo = hacia adelante.
  Cada cuadro de animación es una "pose" (conjunto de ángulos). Al encadenar poses se obtiene el ciclo.
  La animación de muerte rota el dibujo completo alrededor de los pies.

Uso (requiere Pillow, ver requirements-dev.txt):
  python tools/generar_sprites_ronin.py                      # regenera assets/images/ronin/*.png
  python tools/generar_sprites_ronin.py --preview            # además genera docs/img/ronin_animaciones.png
  python tools/generar_sprites_ronin.py --preview attack run # vista previa solo de algunas animaciones
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

FRAME = 96          # tamaño final de cada cuadro (px)
SS = 6              # supersampling para bordes suaves
GROUND = 90         # y del suelo dentro del cuadro
CX = 48             # x del centro del cuerpo dentro del cuadro (centrado: al voltear no se desplaza)

INK = (24, 24, 28, 255)
INK2 = (44, 44, 54, 255)          # piezas de armadura
INK_FAR = (62, 62, 72, 255)       # lado lejano (da profundidad)
MASK = (34, 34, 42, 255)
STRAW = (170, 150, 110, 255)
STRAW_SHADE = (132, 114, 80, 255)
STRAW_LINE = (104, 88, 60, 255)
STRAW_UNDER = (62, 52, 38, 255)
RED = (190, 40, 40, 255)
RED_DARK = (130, 24, 28, 255)
STEEL = (196, 200, 210, 255)
STEEL_DARK = (96, 98, 110, 255)
SHEATH = (58, 58, 68, 255)
GOLD = (160, 128, 64, 255)

THIGH, SHIN = 12.0, 12.0
UPPER, FORE = 7.5, 7.5
TORSO = 14.0
BLADE = 24.0


def rad(deg):
    return math.radians(deg)


def point(p, length, ang_deg):
    """Punto a `length` de `p`, con ángulo medido desde la vertical hacia abajo (positivo = hacia adelante)."""
    return (p[0] + length * math.sin(rad(ang_deg)), p[1] + length * math.cos(rad(ang_deg)))


class Canvas:
    def __init__(self):
        self.size = FRAME * SS
        self.img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _s(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def line(self, pts, width, color):
        pts = self._s(pts)
        w = width * SS
        self.d.line(pts, fill=color, width=max(1, int(w)), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = w / 2
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def poly(self, pts, color):
        self.d.polygon(self._s(pts), fill=color)

    def circle(self, c, r, color):
        x, y = c[0] * SS, c[1] * SS
        self.d.ellipse((x - r * SS, y - r * SS, x + r * SS, y + r * SS), fill=color)

    def ellipse(self, c, rx, ry, color):
        x, y = c[0] * SS, c[1] * SS
        self.d.ellipse((x - rx * SS, y - ry * SS, x + rx * SS, y + ry * SS), fill=color)

    def effect_poly(self, pts, color):
        """Polígono con transparencia real (se compone sobre lo ya dibujado)."""
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(self._s(pts), fill=color)
        self.img = Image.alpha_composite(self.img, layer)
        self.d = ImageDraw.Draw(self.img)

    def result(self, rotate=0.0, shift=(0.0, 0.0)):
        img = self.img
        if rotate:
            img = img.rotate(rotate, resample=Image.BICUBIC, center=(CX * SS, GROUND * SS))
        if shift != (0.0, 0.0):
            moved = Image.new("RGBA", img.size, (0, 0, 0, 0))
            moved.paste(img, (int(shift[0] * SS), int(shift[1] * SS)))
            img = moved
        return img.resize((FRAME, FRAME), Image.LANCZOS)


def limb(cv, start, a1, l1, a2, l2, w1, w2, color):
    """Dibuja una extremidad de dos segmentos. a2 es relativo a a1. Devuelve (articulación, extremo)."""
    mid = point(start, l1, a1)
    end = point(mid, l2, a1 + a2)
    cv.line([start, mid], w1, color)
    cv.line([mid, end], w2, color)
    return mid, end


def foot(cv, joints, color):
    """Pie con sandalia y polaina (banda clara en la pantorrilla)."""
    knee, end = joints
    band0 = (knee[0] + (end[0] - knee[0]) * 0.35, knee[1] + (end[1] - knee[1]) * 0.35)
    band1 = (knee[0] + (end[0] - knee[0]) * 0.7, knee[1] + (end[1] - knee[1]) * 0.7)
    cv.line([band0, band1], 4.6, (84, 84, 94, 255) if color == INK else (74, 74, 84, 255))
    cv.line([(end[0] - 1.0, end[1] - 0.6), (end[0] + 3.6, end[1] - 0.6)], 2.6, color)


def ragged(x0, x1, y, n, wind, jag=2.4, phase=0.0):
    """Borde inferior desgarrado (dientes de sierra irregulares) de x0 a x1 a la altura y."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        irregular = math.sin(i * 2.7 + phase) * 0.8
        pts.append((x - wind * (1 - t * 0.2), y + (jag if i % 2 else -jag * 0.2) + irregular))
    return pts


def scarf(cv, neck, phase, amp, droop, length, width, dy=0.0):
    """Bufanda roja que ondea hacia atrás. `droop` > 0 la deja caer, < 0 la levanta."""
    top, bottom = [], []
    for i in range(length + 1):
        t = i / length
        x = neck[0] - i * 2.1
        y = neck[1] + dy + droop * t * t * 7 + amp * math.sin(phase - i * 0.75) * (0.3 + t) * 1.8
        w = width * (1 - 0.78 * t)
        top.append((x, y - w / 2))
        bottom.append((x, y + w / 2))
    cv.poly(top + bottom[::-1], RED)


def kasa(cv, head, wind):
    """Sombrero de paja cónico con trama, moño y hebras sueltas."""
    hx, hy = head
    left, right, apex = (hx - 17.5, hy - 1.0), (hx + 17.5, hy - 1.0), (hx + 0.8, hy - 13.0)

    def edge(a, b, bow):
        pts = []
        for i in range(9):
            t = i / 8
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            pts.append((x + bow * math.sin(math.pi * t), y + abs(bow) * 0.45 * math.sin(math.pi * t)))
        return pts

    cv.ellipse((hx, hy - 0.6), 17.5, 2.2, STRAW_UNDER)                       # cara inferior del ala
    cone = edge(left, apex, 2.4) + edge(apex, right, -2.4)[1:] + [right, left]
    cv.poly(cone, STRAW)
    shade = edge(left, apex, 2.4) + [(hx - 1, hy - 1.0)]
    cv.poly(shade, STRAW_SHADE)                                              # lado en sombra
    for k in range(-4, 5):                                                   # trama radial
        cv.line([(apex[0] + k * 0.15, apex[1] + 1.0), (hx + k * 3.8, hy - 1.3)], 0.45, STRAW_LINE)
    cv.line([(hx - 17.0, hy - 1.0), (hx + 17.0, hy - 1.0)], 0.9, STRAW_LINE)  # borde del ala
    cv.line([apex, (apex[0] + 0.3, apex[1] - 3.2)], 1.0, INK)                # moño
    cv.line([(apex[0] + 0.3, apex[1] - 3.0), (apex[0] + 1.6, apex[1] - 4.4)], 0.6, INK)
    for i, dx in enumerate((-15.5, -11.0, 12.5, 15.8)):                      # hebras de paja
        sw = -wind * 0.25
        cv.line([(hx + dx, hy - 0.4), (hx + dx - 0.6 + sw, hy + 3.0 + i % 2 * 1.4)], 0.5, STRAW_LINE)


def draw_pose(bob=0.0, lean=4.0, front_leg=(8, -4), back_leg=(-8, 4), front_arm=(-20, 112), back_arm=(8, 30),
              scarf_phase=0.0, scarf_amp=0.8, scarf_droop=0.0, wind=0.5, hem_lift=0.0, snap=True, breath=0.0,
              blade=None, star=False, slash=None, spark=None, streaks=False, sheathed=True, tilt_head=0.0):
    cv = Canvas()
    hip = (CX, GROUND - THIGH - SHIN - bob)

    def foot_y(leg):
        mid = point(hip, THIGH, leg[0])
        return point(mid, SHIN, leg[0] + leg[1])[1]

    dy = 0.0
    if snap:
        dy = GROUND - max(foot_y(front_leg), foot_y(back_leg))
    hip = (hip[0], hip[1] + dy)

    shoulder = (hip[0] + TORSO * math.sin(rad(lean)), hip[1] - TORSO * math.cos(rad(lean)) - breath)
    head = (shoulder[0] + 2.0 * math.sin(rad(lean)) + 0.8 + tilt_head, shoulder[1] - 7.2)

    # ---- trazos de velocidad (dash) ----
    if streaks:
        for k, (yy, ln) in enumerate(((hip[1] - 14, 22), (hip[1] - 4, 28), (hip[1] + 6, 18))):
            x0 = hip[0] - 8 - k * 2
            cv.effect_poly([(x0, yy), (x0 - ln, yy + 0.6), (x0, yy + 1.2)], (24, 24, 28, 90))

    # ---- lado lejano: brazo, pierna y capa trasera ----
    limb(cv, (shoulder[0] - 1.2, shoulder[1] + 1.5), back_arm[0], UPPER, back_arm[1], FORE, 3.2, 3.0, INK_FAR)
    foot(cv, limb(cv, (hip[0] - 1.0, hip[1]), back_leg[0], THIGH, back_leg[1], SHIN, 5.0, 4.2, INK_FAR), INK_FAR)
    cape_hem = hip[1] + 9 - hem_lift
    cv.poly([(shoulder[0] - 3.5, shoulder[1] - 1.5), (shoulder[0] + 3.0, shoulder[1] + 3.0), (hip[0] + 1, hip[1] + 4)]
            + ragged(hip[0] - 1 - wind * 0.5, hip[0] - 13 - wind * 1.4, cape_hem, 5, wind * 0.3, 2.8, 0.7)[::-1]
            + [(shoulder[0] - 7.5 - wind * 0.4, shoulder[1] + 6)], INK2)

    # ---- katanas envainadas en la cadera (dos) ----
    if sheathed:
        for k, (tip_dx, tip_dy, hx_off) in enumerate(((-19.0, 7.0, 4.5), (-15.0, 12.5, 3.8))):
            s0 = (hip[0] + hx_off, hip[1] - 3.0 + k * 2.0)
            s1 = (hip[0] + tip_dx - wind * 0.5, hip[1] + tip_dy)
            cv.line([s0, s1], 2.0, SHEATH)
            cv.line([s0, (s0[0] + 4.0, s0[1] - 1.5)], 2.3, INK)                  # empuñadura
            cv.line([(s0[0] + 1.2, s0[1] - 0.5), (s0[0] + 3.0, s0[1] - 1.1)], 1.0, RED)

    # ---- torso: kimono + armadura ligera ----
    cv.poly([(shoulder[0] - 4.6, shoulder[1] - 0.8), (shoulder[0] + 4.6, shoulder[1] + 0.6),
             (hip[0] + 5.4, hip[1] + 2.0), (hip[0] - 5.4, hip[1] + 2.0)], INK)
    for k in range(3):                                                           # láminas del pectoral
        t = 0.28 + k * 0.22
        y = shoulder[1] + (hip[1] - shoulder[1]) * t
        x = shoulder[0] + (hip[0] - shoulder[0]) * t
        cv.line([(x - 3.8, y), (x + 4.2, y)], 0.55, INK_FAR)

    # ---- pierna cercana ----
    foot(cv, limb(cv, (hip[0] + 1.0, hip[1]), front_leg[0], THIGH, front_leg[1], SHIN, 5.4, 4.4, INK), INK)

    # ---- falda raída (cubre el muslo, deja ver la pantorrilla) ----
    hem = hip[1] + 13.0 - hem_lift
    skirt = [(hip[0] - 6.2, hip[1] - 1.0), (hip[0] + 6.8, hip[1] - 1.0)]
    skirt += ragged(hip[0] + 8.0 - wind * 0.5 + hem_lift * 0.4, hip[0] - 9.5 - wind * 1.1 - hem_lift * 0.4,
                    hem, 7, wind * 0.4, 2.6, 0.0)
    cv.poly(skirt, INK)
    cv.poly([(hip[0] - 4, hip[1] + 2), (hip[0] + 2, hip[1] + 2), (hip[0] + 1.0, hem - 1), (hip[0] - 5, hem - 2)],
            (14, 14, 18, 255))                                                   # pliegue oscuro

    # ---- cinto de cuerda roja con nudo y colas ----
    cv.line([(hip[0] - 5.5, hip[1] - 0.6), (hip[0] + 5.8, hip[1] - 0.6)], 2.2, RED)
    cv.circle((hip[0] + 4.2, hip[1] - 0.4), 1.5, RED_DARK)
    cv.line([(hip[0] + 4.2, hip[1] + 0.5), (hip[0] + 3.0 - wind * 0.3, hip[1] + 6.5)], 0.9, RED)
    cv.line([(hip[0] + 4.6, hip[1] + 0.5), (hip[0] + 5.2 - wind * 0.4, hip[1] + 5.5)], 0.9, RED)

    # ---- brazo cercano (con antebrazo protegido) ----
    sh_near = (shoulder[0] + 1.2, shoulder[1] + 1.5)
    elbow, hand = limb(cv, sh_near, front_arm[0], UPPER, front_arm[1], FORE, 3.4, 3.2, INK)
    g0 = (elbow[0] + (hand[0] - elbow[0]) * 0.25, elbow[1] + (hand[1] - elbow[1]) * 0.25)
    g1 = (elbow[0] + (hand[0] - elbow[0]) * 0.85, elbow[1] + (hand[1] - elbow[1]) * 0.85)
    cv.line([g0, g1], 4.0, INK2)
    cv.line([g0, g1], 0.7, STEEL_DARK)
    cv.circle(hand, 1.9, INK)

    # ---- katana desenvainada ----
    if blade is not None:
        ang, ln = blade
        tip = point(hand, ln, ang)
        back = point(hand, -4.2, ang)
        cv.line([back, hand], 2.4, INK)                                          # empuñadura
        cv.line([point(hand, -2.2, ang), point(hand, -0.4, ang)], 2.5, RED)
        guard_a, guard_b = point(hand, 0.8, ang + 90), point(hand, 0.8, ang - 90)
        cv.line([guard_a, guard_b], 1.0, GOLD)                                   # tsuba
        cv.line([point(hand, 1.0, ang), tip], 1.9, STEEL)
        cv.line([point(hand, 1.4, ang - 4), point(tip, -1.5, ang)], 0.5, STEEL_DARK)

    if star:                                                                     # shuriken en la mano
        pts = []
        for i in range(8):
            r = 4.4 if i % 2 == 0 else 1.4
            a = rad(45 * i + 22)
            pts.append((hand[0] + r * math.cos(a), hand[1] + r * math.sin(a)))
        cv.poly(pts, STEEL)
        cv.circle(hand, 0.7, INK)

    # ---- hombrera (sode) ----
    cv.ellipse((shoulder[0] + 1.0, shoulder[1] + 1.2), 5.2, 3.4, INK2)
    cv.line([(shoulder[0] - 3.4, shoulder[1] + 3.2), (shoulder[0] + 5.4, shoulder[1] + 3.0)], 0.8, RED)
    cv.line([(shoulder[0] - 2.8, shoulder[1] + 1.2), (shoulder[0] + 4.8, shoulder[1] + 1.0)], 0.5, INK_FAR)

    # ---- cabeza con el rostro cubierto, ojos y sombrero ----
    cv.circle(head, 4.4, MASK)
    cv.line([(head[0] + 0.8, head[1] + 1.8), (head[0] + 4.0, head[1] + 1.8)], 0.9, (214, 204, 184, 255))
    kasa(cv, head, wind)

    # ---- bufandas ----
    neck = (shoulder[0] - 1.0, shoulder[1] - 1.0)
    cv.ellipse((neck[0] + 0.5, neck[1] + 0.2), 4.6, 2.4, RED)
    scarf(cv, neck, scarf_phase, scarf_amp, scarf_droop, 14, 4.4)
    scarf(cv, neck, scarf_phase + 1.1, scarf_amp * 0.8, scarf_droop, 9, 3.2, dy=2.2)

    # ---- efectos: estela del tajo y chispa del desvío ----
    if slash:
        a0, a1, radius = slash
        outer, inner = [], []
        steps = 14
        for i in range(steps + 1):
            t = i / steps
            a = a0 + (a1 - a0) * t
            thick = 0.8 + 7.0 * math.sin(math.pi * min(1.0, t * 0.9 + 0.05))
            outer.append(point(sh_near, radius, a))
            inner.append(point(sh_near, radius - thick, a))
        cv.effect_poly(outer + inner[::-1], (24, 24, 28, 105))
    if spark:
        if spark is True and blade is not None:
            sx, sy = point(hand, blade[1] * 0.8, blade[0])
        else:
            sx, sy = spark
        pts = []
        for i in range(12):
            r = 6.5 if i % 2 == 0 else 2.0
            a = rad(30 * i)
            pts.append((sx + r * math.cos(a), sy + r * math.sin(a)))
        cv.effect_poly(pts, (255, 236, 200, 230))
        cv.circle((sx, sy), 1.8, RED)

    return cv


# ----------------------------------------------------------------------------- animaciones
def anim_idle():
    frames = []
    for i in range(4):
        t = i / 4
        b = math.sin(2 * math.pi * t)
        frames.append(draw_pose(
            lean=3.0 + 1.5 * b, breath=0.8 * b, front_leg=(8, -4), back_leg=(-8, 4),
            front_arm=(-20 + 4 * b, 112), back_arm=(8 - 4 * b, 30),
            scarf_phase=2 * math.pi * t, scarf_amp=0.9, wind=0.8 + 0.8 * b).result())
    return frames


def anim_run():
    frames = []
    n = 6
    for i in range(n):
        p = 2 * math.pi * i / n

        def leg(phase):
            return (46 * math.sin(phase), -(14 + 62 * max(0.0, math.cos(phase))))

        frames.append(draw_pose(
            bob=1.5 * abs(math.sin(p)), lean=13.0, front_leg=leg(p), back_leg=leg(p + math.pi),
            front_arm=(-40 * math.sin(p) + 10, 55), back_arm=(40 * math.sin(p) + 10, 55),
            scarf_phase=p, scarf_amp=1.6, scarf_droop=-0.2, wind=5.0 + 1.5 * math.sin(p + 1)).result())
    return frames


def anim_jump():
    return [draw_pose(bob=3.0, lean=8.0, front_leg=(48, -78), back_leg=(-22, -60), front_arm=(70, 45),
                      back_arm=(-75, 30), scarf_phase=0.6, scarf_amp=0.9, scarf_droop=1.4, wind=2.0,
                      hem_lift=-3.0, snap=False).result()]


def anim_fall():
    return [draw_pose(bob=1.0, lean=2.0, front_leg=(22, -12), back_leg=(-24, 10), front_arm=(105, 15),
                      back_arm=(-105, 15), scarf_phase=1.2, scarf_amp=1.2, scarf_droop=-1.8, wind=1.0,
                      hem_lift=5.0, snap=False).result()]


def anim_crouch():
    frames = []
    for i in range(2):
        b = i * 0.6
        frames.append(draw_pose(lean=24.0, breath=b, front_leg=(68, -112), back_leg=(-36, -58),
                                front_arm=(-10, 105), back_arm=(30, 40), scarf_phase=i * 1.5, scarf_amp=0.8,
                                wind=1.5).result())
    return frames


def anim_crouch_walk():
    """Avance agachado en 6 cuadros: pasos cortos y bajos, torso inclinado, sin rebote."""
    frames = []
    n = 6
    for i in range(n):
        p = 2 * math.pi * i / n
        fl = (68 + 20 * math.sin(p), -(112 - 22 * max(0.0, math.cos(p))))
        bl = (-36 + 20 * math.sin(p + math.pi), -(58 + 22 * max(0.0, math.cos(p + math.pi))))
        frames.append(draw_pose(lean=26.0, bob=0.0, breath=0.4 * math.sin(p), front_leg=fl, back_leg=bl,
                                front_arm=(-10 + 14 * math.sin(p), 105), back_arm=(30 - 14 * math.sin(p), 40),
                                scarf_phase=p, scarf_amp=1.0, wind=2.5 + math.sin(p + 1)).result())
    return frames


def anim_attack():
    """Tajo en 6 cuadros: preparación, golpe (con estela), seguimiento y recuperación."""
    p = [
        dict(lean=-4, front_leg=(14, -10), back_leg=(-20, 12), front_arm=(150, -38), blade=(205, BLADE), wind=1),
        dict(lean=4, front_leg=(24, -22), back_leg=(-24, 12), front_arm=(130, -5), blade=(160, BLADE), wind=2),
        dict(lean=14, front_leg=(38, -48), back_leg=(-32, 8), front_arm=(100, 0), blade=(115, BLADE), wind=4,
             slash=(148, 108, 39)),
        dict(lean=20, front_leg=(44, -58), back_leg=(-38, 6), front_arm=(80, 5), blade=(65, BLADE), wind=6,
             slash=(108, 72, 39)),
        dict(lean=18, front_leg=(40, -54), back_leg=(-36, 6), front_arm=(62, 8), blade=(40, BLADE), wind=5,
             slash=(72, 49, 39)),
        dict(lean=8, front_leg=(20, -22), back_leg=(-20, 10), front_arm=(40, 22), blade=(80, BLADE), wind=2),
    ]
    return [draw_pose(back_arm=(-35, 40), scarf_phase=0.8 * i, scarf_amp=1.4, scarf_droop=-0.3, **pose).result()
            for i, pose in enumerate(p)]


def anim_parry():
    """Desvío en 4 cuadros: guardia, bloqueo con chispa, retorno."""
    p = [
        dict(lean=-2, front_arm=(150, -30), blade=(200, BLADE)),
        dict(lean=-5, front_arm=(125, -12), blade=(160, BLADE)),
        dict(lean=-7, front_arm=(110, -5), blade=(135, BLADE), spark=True),
        dict(lean=-3, front_arm=(95, 5), blade=(115, BLADE)),
    ]
    frames = []
    for i, pose in enumerate(p):
        spark = pose.pop("spark", None)
        frames.append(draw_pose(front_leg=(22, -26), back_leg=(-24, 14), back_arm=(-30, 40),
                                scarf_phase=0.9 * i, scarf_amp=1.0, wind=1.5, spark=spark, **pose).result())
    return frames


def anim_throw():
    """Lanzamiento de shuriken en 4 cuadros."""
    p = [
        dict(lean=-6, front_arm=(-130, 35), star=True),
        dict(lean=2, front_arm=(10, 40), star=True),
        dict(lean=12, front_arm=(105, 5)),
        dict(lean=9, front_arm=(75, 25)),
    ]
    return [draw_pose(front_leg=(18, -14), back_leg=(-20, 10), back_arm=(-25, 30), scarf_phase=0.9 * i,
                      scarf_amp=1.2, wind=3.0, **pose).result() for i, pose in enumerate(p)]


def anim_dash():
    return [draw_pose(bob=-1.0, lean=36.0, front_leg=(58, -22), back_leg=(-52, -8), front_arm=(-65, 12),
                      back_arm=(-80, 10), scarf_phase=0.5 * i, scarf_amp=1.2, scarf_droop=-0.4, wind=8.0,
                      streaks=True).result() for i in range(2)]


def anim_hurt():
    frames = []
    for i, lean in enumerate((-14.0, -19.0)):
        frames.append(draw_pose(lean=lean, front_leg=(14, -8), back_leg=(-16, 10), front_arm=(135 + 8 * i, 10),
                                back_arm=(-125, 10), scarf_phase=1.0 + i, scarf_amp=1.4, wind=-2.0,
                                tilt_head=-1.5, spark=(CX + 3, GROUND - 31) if i == 0 else None).result())
    return frames


def anim_death():
    """Caída hacia atrás: se rota el dibujo completo alrededor de los pies."""
    base = draw_pose(lean=-16.0, front_leg=(14, -8), back_leg=(-16, 10), front_arm=(140, 10), back_arm=(-125, 10),
                     scarf_phase=1.0, scarf_amp=1.4, wind=-1.0, tilt_head=-1.5)
    pasos = ((0, 0, 0), (22, 2, 0), (52, 9, 1), (82, 15, 3), (90, 17, 4))   # (ángulo, desplazamiento x, y)
    return [base.result(rotate=a, shift=(dx, -dy)) for a, dx, dy in pasos]


ANIMS = {
    "idle": anim_idle, "run": anim_run, "jump": anim_jump, "fall": anim_fall, "crouch": anim_crouch, "crouch_walk": anim_crouch_walk,
    "attack": anim_attack, "parry": anim_parry, "throw": anim_throw, "dash": anim_dash,
    "hurt": anim_hurt, "death": anim_death,
}


def save_strip(frames, path):
    strip = Image.new("RGBA", (FRAME * len(frames), FRAME), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * FRAME, 0))
    strip.save(path)


def save_preview(all_frames, path, zoom=2):
    paper = (238, 232, 218, 255)
    label_w = 80
    cols = max(len(f) for f in all_frames.values())
    rows = len(all_frames)
    cell = FRAME * zoom
    sheet = Image.new("RGBA", (label_w + cols * cell, rows * cell), paper)
    draw = ImageDraw.Draw(sheet)
    for r, (name, frames) in enumerate(all_frames.items()):
        draw.text((8, r * cell + cell // 2 - 6), name, fill=(24, 24, 28, 255))
        draw.line([(0, r * cell), (sheet.width, r * cell)], fill=(214, 206, 188, 255))
        for c, f in enumerate(frames):
            big = f.resize((cell, cell), Image.LANCZOS)
            sheet.alpha_composite(big, (label_w + c * cell, r * cell))
    sheet.save(path)


def main():
    raiz = Path(__file__).resolve().parent.parent
    out = raiz / "assets" / "images" / "ronin"
    out.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    nombres = [a for a in args if not a.startswith("--")] or list(ANIMS)
    zoom = 3 if len(nombres) <= 4 else 2
    todo = {}
    for name in nombres:
        frames = ANIMS[name]()
        todo[name] = frames
        save_strip(frames, out / f"{name}.png")
        print(f"{name}.png: {len(frames)} cuadros")
    if "--preview" in args:
        destino = raiz / "docs" / "img"
        destino.mkdir(parents=True, exist_ok=True)
        save_preview(todo, destino / "ronin_animaciones.png", zoom)
        print("docs/img/ronin_animaciones.png generado")


if __name__ == "__main__":
    main()
