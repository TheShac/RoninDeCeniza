"""Genera las hojas de sprites del Ronin (assets/images/ronin/*.png).

Cada animación es una tira horizontal de cuadros de 64x64 px con fondo transparente.
El personaje se dibuja mirando a la DERECHA; en el juego se voltea para mirar a la izquierda.

Cómo funciona (útil para el informe, movimiento rotacional):
  el cuerpo es un esqueleto de segmentos. Cada extremidad se define por ángulos (cinemática directa):
  posición de la articulación = posición anterior + longitud * (sen(ángulo), cos(ángulo)).
  Cada cuadro de animación es una "pose" (conjunto de ángulos). Al encadenar poses se obtiene el ciclo.

Uso (requiere Pillow, ver requirements-dev.txt):
  python tools/generar_sprites_ronin.py            # regenera assets/images/ronin/*.png
  python tools/generar_sprites_ronin.py --preview  # además genera docs/img/ronin_animaciones.png
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

FRAME = 64          # tamaño final de cada cuadro (px)
SS = 8              # supersampling para bordes suaves
GROUND = 62         # y del suelo dentro del cuadro
CX = 32             # x del centro del cuerpo dentro del cuadro (centrado: al voltear no se desplaza)

INK = (24, 24, 28, 255)
INK_FAR = (58, 58, 66, 255)       # extremidades del lado lejano (da profundidad)
HAT = (36, 36, 42, 255)
HAT_RIM = (92, 92, 100, 255)
RED = (190, 40, 40, 255)
SKIN = (226, 205, 180, 255)
STEEL = (150, 150, 160, 255)

THIGH, SHIN = 13.0, 13.0
UPPER, FORE = 8.0, 8.0
TORSO = 15.0


def rad(deg):
    return math.radians(deg)


def point(p, length, ang_deg):
    """Punto a `length` de `p`, con ángulo medido desde la vertical hacia abajo (positivo = hacia adelante)."""
    return (p[0] + length * math.sin(rad(ang_deg)), p[1] + length * math.cos(rad(ang_deg)))


class Canvas:
    def __init__(self):
        self.img = Image.new("RGBA", (FRAME * SS, FRAME * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _s(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def line(self, pts, width, color):
        pts = self._s(pts)
        w = width * SS
        self.d.line(pts, fill=color, width=int(w), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = w / 2
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def poly(self, pts, color):
        self.d.polygon(self._s(pts), fill=color)

    def circle(self, c, r, color):
        x, y = c[0] * SS, c[1] * SS
        self.d.ellipse((x - r * SS, y - r * SS, x + r * SS, y + r * SS), fill=color)

    def result(self):
        return self.img.resize((FRAME, FRAME), Image.LANCZOS)


def limb(cv, start, a1, l1, a2, l2, w1, w2, color):
    """Dibuja una extremidad de dos segmentos. a2 es relativo a a1. Devuelve (rodilla/codo, extremo)."""
    mid = point(start, l1, a1)
    end = point(mid, l2, a1 + a2)
    cv.line([start, mid], w1, color)
    cv.line([mid, end], w2, color)
    return mid, end


def scarf(cv, neck, phase, amp, droop, length=9):
    """Bufanda roja que ondea hacia atrás. `droop` > 0 la deja caer, < 0 la levanta."""
    top, bottom = [], []
    for i in range(length + 1):
        t = i / length
        x = neck[0] - i * 2.4
        y = neck[1] + droop * t * t * 6 + amp * math.sin(phase - i * 0.85) * (0.3 + t) * 1.6
        w = 3.4 * (1 - 0.75 * t)
        top.append((x, y - w / 2))
        bottom.append((x, y + w / 2))
    cv.poly(top + bottom[::-1], RED)


def draw_pose(bob=0.0, lean=4.0, front_leg=(10, 0), back_leg=(-10, 0), front_arm=(-10, 40),
              back_arm=(10, 40), scarf_phase=0.0, scarf_amp=0.6, scarf_droop=0.0, snap=True, breath=0.0):
    cv = Canvas()
    hip = (CX, 36.0 - bob)

    # --- cálculo del apoyo en el suelo (para que los pies queden sobre y = GROUND) ---
    def foot_y(leg):
        mid = point(hip, THIGH, leg[0])
        return point(mid, SHIN, leg[0] + leg[1])[1]

    dy = 0.0
    if snap:
        dy = GROUND - max(foot_y(front_leg), foot_y(back_leg))
    hip = (hip[0], hip[1] + dy)

    # el torso sube con inclinación `lean` (hacia adelante); `breath` sube/baja el pecho al respirar
    shoulder = (hip[0] + TORSO * math.sin(rad(lean)), hip[1] - TORSO * math.cos(rad(lean)) - breath)
    head = (shoulder[0] + 2.2 * math.sin(rad(lean)) + 0.6, shoulder[1] - 7.5)

    # lado lejano
    limb(cv, (shoulder[0] - 1.2, shoulder[1] + 1.5), back_arm[0], UPPER, back_arm[1], FORE, 3.2, 3.0, INK_FAR)
    limb(cv, (hip[0] - 1.0, hip[1]), back_leg[0], THIGH, back_leg[1], SHIN, 6.2, 4.6, INK_FAR)

    # katana en la cadera (vaina hacia atrás)
    sw0 = (hip[0] + 1.5, hip[1] - 2.5)
    sw1 = (hip[0] - 15.5, hip[1] + 5.5 - lean * 0.15)
    cv.line([sw0, sw1], 2.0, (70, 70, 80, 255))
    cv.line([sw0, (sw0[0] + 3.2, sw0[1] - 1.4)], 2.4, RED)

    # torso (kimono) como polígono
    cv.poly([(shoulder[0] - 4.2, shoulder[1] - 0.5), (shoulder[0] + 4.2, shoulder[1] + 0.5),
             (hip[0] + 5.2, hip[1] + 2.0), (hip[0] - 5.2, hip[1] + 2.0)], INK)
    cv.line([(shoulder[0] - 3.5, hip[1] - 1.0), (shoulder[0] + 4.5, hip[1] - 1.0)], 2.0, RED)   # obi (cinturón)

    # lado cercano
    limb(cv, (hip[0] + 1.0, hip[1]), front_leg[0], THIGH, front_leg[1], SHIN, 6.6, 4.8, INK)
    limb(cv, (shoulder[0] + 1.2, shoulder[1] + 1.5), front_arm[0], UPPER, front_arm[1], FORE, 3.4, 3.2, INK)

    # cabeza, rostro y sombrero (kasa)
    cv.circle(head, 4.4, SKIN)
    cv.poly([(head[0] - 14, head[1] - 1.0), (head[0] + 14, head[1] - 1.0), (head[0] + 1, head[1] - 12.5)], HAT)
    cv.line([(head[0] - 14, head[1] - 1.0), (head[0] + 14, head[1] - 1.0)], 1.3, HAT_RIM)
    cv.poly([(head[0] - 4.4, head[1] - 0.6), (head[0] + 4.4, head[1] - 0.6), (head[0] + 3.8, head[1] + 2.0),
             (head[0] - 3.8, head[1] + 2.0)], (36, 36, 42, 210))   # sombra bajo el ala
    cv.circle((head[0] + 2.2, head[1] + 1.2), 0.7, INK)            # ojo

    # bufanda
    neck = (shoulder[0] - 1.5, shoulder[1] - 1.0)
    scarf(cv, neck, scarf_phase, scarf_amp, scarf_droop)
    return cv.result()


# ----------------------------------------------------------------------------- animaciones
def anim_idle():
    frames = []
    for i in range(4):
        t = i / 4
        b = math.sin(2 * math.pi * t)
        frames.append(draw_pose(
            bob=0.0, lean=3.0 + 1.5 * b, breath=0.9 * b,
            front_leg=(9, -4), back_leg=(-9, 4),
            front_arm=(-20 + 4 * b, 112), back_arm=(8 - 4 * b, 30),
            scarf_phase=2 * math.pi * t, scarf_amp=0.9))
    return frames


def anim_run():
    frames = []
    n = 6
    for i in range(n):
        p = 2 * math.pi * i / n

        def leg(phase):
            thigh = 46 * math.sin(phase)
            shin = -(14 + 62 * max(0.0, math.cos(phase)))
            return (thigh, shin)

        front = leg(p)
        back = leg(p + math.pi)
        frames.append(draw_pose(
            bob=1.6 * abs(math.sin(p)), lean=13.0,
            front_leg=front, back_leg=back,
            front_arm=(-40 * math.sin(p) + 10, 55), back_arm=(40 * math.sin(p) + 10, 55),
            scarf_phase=p * 1.0, scarf_amp=1.5, scarf_droop=-0.2))
    return frames


def anim_jump():
    return [draw_pose(bob=3.0, lean=8.0, front_leg=(48, -78), back_leg=(-22, -60),
                      front_arm=(70, 45), back_arm=(-75, 30), scarf_phase=0.6, scarf_amp=0.9,
                      scarf_droop=1.4, snap=False)]


def anim_fall():
    return [draw_pose(bob=1.0, lean=2.0, front_leg=(22, -12), back_leg=(-24, 10),
                      front_arm=(105, 15), back_arm=(-105, 15), scarf_phase=1.2, scarf_amp=1.2,
                      scarf_droop=-1.8, snap=False)]


ANIMS = {"idle": anim_idle, "run": anim_run, "jump": anim_jump, "fall": anim_fall}


def save_strip(frames, path):
    strip = Image.new("RGBA", (FRAME * len(frames), FRAME), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * FRAME, 0))
    strip.save(path)


def save_preview(all_frames, path, zoom=5):
    paper = (238, 232, 218, 255)
    cols = max(len(f) for f in all_frames.values())
    rows = len(all_frames)
    sheet = Image.new("RGBA", (cols * FRAME * zoom, rows * FRAME * zoom), paper)
    for r, (name, frames) in enumerate(all_frames.items()):
        for c, f in enumerate(frames):
            big = f.resize((FRAME * zoom, FRAME * zoom), Image.NEAREST)
            sheet.alpha_composite(big, (c * FRAME * zoom, r * FRAME * zoom))
    sheet.save(path)


def main():
    raiz = Path(__file__).resolve().parent.parent
    out = raiz / "assets" / "images" / "ronin"
    out.mkdir(parents=True, exist_ok=True)
    todo = {}
    for name, fn in ANIMS.items():
        frames = fn()
        todo[name] = frames
        save_strip(frames, out / f"{name}.png")
        print(f"{name}.png: {len(frames)} cuadros")
    if "--preview" in sys.argv:
        destino = raiz / "docs" / "img"
        destino.mkdir(parents=True, exist_ok=True)
        save_preview(todo, destino / "ronin_animaciones.png")
        print("docs/img/ronin_animaciones.png generado")


if __name__ == "__main__":
    main()
