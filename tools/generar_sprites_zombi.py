"""Genera las hojas de sprites del zombi caminante (assets/images/zombi/*.png).

Cada tipo de zombi tiene dos variantes, para que no todos se vean iguales, y su propia carpeta:
  caminante (assets/images/zombi/caminante/)
    aldeano  : campesino japonés de la era samurái, kimono índigo raído, obi, sandalias de paja, pelo enmarañado.
    samurai  : guerrero caído, pectoral de láminas con cordones desteñidos, hombreras, falda de placas,
               casco agrietado y una katana rota en la mano.
  corredor (assets/images/zombi/corredor/)
    campesino: flaco, torso al aire con costillas y cicatrices, hakama rota y banda en la frente.
    ashigaru : soldado raso con jingasa (sombrero de hierro), coraza ligera de cuero y falda de placas.

Cada animación es una tira horizontal de cuadros de 96x96 px, mirando a la DERECHA (en el juego se voltea).
Archivos: <tipo>/<variante>_<animación>.png
  caminante: walk (6), attack (4), hurt (2), death (5)
  corredor : walk (6), run (6), stun (2), death (5)

Usa el mismo esqueleto de ángulos (cinemática directa) y las mismas herramientas de dibujo que el Ronin:
  posición de la articulación = posición anterior + longitud * (sen(ángulo), cos(ángulo)).

Uso (requiere Pillow, ver requirements-dev.txt):
  python tools/generar_sprites_zombi.py                 # regenera todo
  python tools/generar_sprites_zombi.py --preview       # además genera docs/img/zombi_<tipo>.png
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_sprites_ronin import (CX, FRAME, GROUND, INK, INK2, RED, RED_DARK, STEEL, STEEL_DARK,  # noqa: E402
                                   SHIN, THIGH, TORSO, UPPER, FORE, Canvas, limb, point, ragged, rad,
                                   save_preview, save_strip)

SKIN = (150, 164, 138, 255)
SKIN_FAR = (112, 124, 106, 255)
SKIN_DARK = (84, 94, 80, 255)
BLOOD = (110, 24, 28, 255)
EYE = (210, 50, 40, 255)
HAIR = (30, 28, 30, 255)
BONE = (214, 208, 190, 255)

VARIANTS = {
    "aldeano": dict(
        armor=False, bare=False, hakama=False, hat="hair", blade=False,
        cloth=(62, 74, 108, 255), cloth_far=(46, 54, 80, 255), cloth_dark=(36, 42, 64, 255),
        sash=(118, 86, 54, 255), leg=SKIN, leg_far=SKIN_FAR, sleeve=(62, 74, 108, 255), forearm=SKIN,
    ),
    "samurai": dict(
        armor=True, bare=False, hakama=True, hat="kabuto", blade=True,
        cloth=(40, 44, 62, 255), cloth_far=(30, 33, 48, 255), cloth_dark=(22, 24, 34, 255),
        sash=(120, 44, 40, 255), leg=(36, 40, 56, 255), leg_far=(28, 30, 42, 255), sleeve=(52, 56, 72, 255),
        forearm=(62, 66, 82, 255),
    ),
    "campesino": dict(
        armor=False, bare=True, hakama=True, hat="hair", blade=False,
        cloth=SKIN, cloth_far=SKIN_FAR, cloth_dark=SKIN_DARK,
        sash=(150, 60, 50, 255), leg=(104, 92, 76, 255), leg_far=(78, 68, 56, 255), sleeve=SKIN, forearm=SKIN,
    ),
    "ashigaru": dict(
        armor=True, bare=False, hakama=True, hat="jingasa", blade=False,
        cloth=(82, 64, 48, 255), cloth_far=(60, 46, 36, 255), cloth_dark=(40, 30, 24, 255),
        sash=(120, 44, 40, 255), leg=(64, 58, 50, 255), leg_far=(48, 44, 38, 255), sleeve=(92, 72, 54, 255),
        forearm=(70, 62, 54, 255),
    ),
}

# Tipos de zombi: variantes y animaciones que genera cada uno
TYPES = {
    "caminante": ("aldeano", "samurai"),
    "corredor": ("campesino", "ashigaru"),
}


def claw(cv, end, ang, color):
    """Mano con tres dedos rígidos en la dirección del antebrazo."""
    for d in (-24, 0, 24):
        tip = point(end, 3.6, ang + d)
        cv.line([end, tip], 0.9, color)
    cv.circle(end, 1.5, color)


def broken_blade(cv, hand, ang):
    """Katana rota: empuñadura envuelta y unos 10 px de hoja con la punta quebrada."""
    base = point(hand, -2.5, ang)
    tsuba = point(hand, 1.2, ang)
    tip = point(hand, 11.0, ang)
    cv.line([base, tsuba], 2.0, (40, 36, 36, 255))
    cv.line([tsuba, tip], 1.8, STEEL_DARK)
    cv.line([point(tsuba, 1.0, ang), tip], 0.6, STEEL)
    jag = point(tip, 2.2, ang + 50)
    cv.poly([point(tsuba, 7.0, ang + 7), tip, jag], STEEL_DARK)


def draw_zombie(variant, bob=0.0, lean=18.0, front_leg=(10, -6), back_leg=(-10, 8), front_arm=(80, 6),
                back_arm=(92, 4), head_drop=3.0, sway=0.0, mouth=0.0, hit=False):
    v = VARIANTS[variant]
    armor, bare, wide, hat, blade = v["armor"], v["bare"], v["hakama"], v["hat"], v["blade"]
    cv = Canvas()
    hip = (CX, GROUND - THIGH - SHIN - bob)

    def foot_y(leg):
        mid = point(hip, THIGH, leg[0])
        return point(mid, SHIN, leg[0] + leg[1])[1]

    hip = (hip[0], hip[1] + GROUND - max(foot_y(front_leg), foot_y(back_leg)))
    ls = math.sin(rad(lean))
    lc = math.cos(rad(lean))
    shoulder = (hip[0] + TORSO * ls + sway, hip[1] - TORSO * lc)
    head = (shoulder[0] + 2.0 * ls + head_drop, shoulder[1] - 6.4 + head_drop * 0.25)
    nrm = (lc, ls)                                            # perpendicular al eje del torso

    def sandal(end, color):
        cv.line([(end[0] - 1.2, end[1] - 0.5), (end[0] + 3.8, end[1] - 0.5)], 2.4, color)

    def leg_draw(origin, leg, col, far):
        w1, w2 = (5.4, 4.6) if wide else (4.2, 3.4)
        joints = limb(cv, origin, leg[0], THIGH, leg[1], SHIN, w1, w2, col)
        knee, end = joints
        if armor:                                             # espinillera clara
            a = (knee[0] + (end[0] - knee[0]) * 0.3, knee[1] + (end[1] - knee[1]) * 0.3)
            b = (knee[0] + (end[0] - knee[0]) * 0.85, knee[1] + (end[1] - knee[1]) * 0.85)
            cv.line([a, b], 4.9, (70, 72, 88, 255) if far else (92, 94, 112, 255))
            sandal(end, INK)
        else:
            sandal(end, (150, 124, 78, 255) if not far else (112, 92, 58, 255))   # waraji de paja
        return joints

    def arm_draw(origin, arm, far):
        sleeve = v["cloth_far"] if far else v["sleeve"]
        fore = (v["cloth_far"] if armor else SKIN_FAR) if far else v["forearm"]
        mid, end = limb(cv, origin, arm[0], UPPER, arm[1], FORE, 4.2, 3.8 if armor else 3.2, sleeve)
        if not armor and not bare:                            # manga rota: antebrazo con piel
            a = (mid[0] + (end[0] - mid[0]) * 0.45, mid[1] + (end[1] - mid[1]) * 0.45)
            cv.line([a, end], 3.0, fore)
        claw(cv, end, arm[0] + arm[1], SKIN_FAR if far else SKIN)
        return mid, end

    # ---- lado lejano ----
    arm_draw((shoulder[0] - 1.0, shoulder[1] + 1.5), back_arm, True)
    leg_draw((hip[0] - 1.0, hip[1]), back_leg, v["leg_far"], True)

    # ---- torso ----
    sx, sy = shoulder
    hx, hy = hip
    tw_s, tw_h = (5.8, 5.2) if armor else ((4.6, 4.0) if bare else (5.2, 4.4))
    torso = [(sx + nrm[0] * tw_s, sy + nrm[1] * tw_s), (sx - nrm[0] * tw_s, sy - nrm[1] * tw_s),
             (hx - nrm[0] * tw_h, hy - nrm[1] * tw_h), (hx + nrm[0] * tw_h, hy + nrm[1] * tw_h)]
    cv.poly(torso, v["cloth"])
    if armor:
        for k in range(1, 5):                                 # láminas del pectoral con cordón desteñido
            t = k / 5
            ax, ay = sx + (hx - sx) * t, sy + (hy - sy) * t
            cv.line([(ax - nrm[0] * tw_s, ay - nrm[1] * tw_s), (ax + nrm[0] * tw_s, ay + nrm[1] * tw_s)], 0.8,
                    RED_DARK if k % 2 else v["cloth_dark"])
        for dx in (-3.6, 0.0, 3.6):                           # falda de placas (kusazuri)
            cv.poly([(hx + dx - 1.7, hy - 1), (hx + dx + 1.7, hy - 1), (hx + dx + 1.5, hy + 10), (hx + dx - 1.5, hy + 10)],
                    v["cloth_far"] if dx < 0 else v["cloth"])
            cv.line([(hx + dx - 1.5, hy + 4), (hx + dx + 1.5, hy + 4)], 0.7, RED_DARK)
        cv.ellipse((sx + 1.0, sy + 1.0), 4.8, 3.4, v["sleeve"])          # hombrera (sode)
        cv.line([(sx - 3.6, sy + 2.2), (sx + 5.6, sy + 2.2)], 0.9, RED_DARK)
    elif bare:                                                # torso al aire: costillas, cicatriz y sangre
        for k in range(1, 4):
            t = 0.22 + k * 0.17
            ax, ay = sx + (hx - sx) * t, sy + (hy - sy) * t
            cv.line([(ax - 0.5, ay + 0.2), (ax + nrm[0] * 3.6, ay + nrm[1] * 3.6)], 0.8, SKIN_DARK)
        cv.line([(sx + 1.2, sy + 1.5), (hx + 2.6, hy - 3.0)], 0.7, BLOOD)
        cv.poly([(hx - 4.6, hy - 1.0), (hx + 5.0, hy - 1.0), (hx + 6.0, hy + 5.5), (hx - 5.5, hy + 5.0)], v["leg"])  # hakama
    else:
        hem_y = hy + 7.5
        skirt = [(hx - 4.6, hy - 1.0), (hx + 5.0, hy - 1.0)] + ragged(hx + 6.4, hx - 6.2, hem_y, 6, 0.0, 2.2, 0.4)
        cv.poly(skirt, v["cloth"])
        cv.line([(sx - 1.0, sy - 1.0), (hx + 1.5, hy - 2.0)], 1.0, v["cloth_dark"])   # solapa del kimono
        cv.poly([(sx + 1.4, sy - 3.4), (sx + 4.4, sy - 2.2), (sx + 2.0, sy + 3.6)], SKIN)  # pecho al aire (cuello en V)
        cv.line([(sx + 1.2, sy - 0.6), (sx + 3.4, sy + 0.2)], 0.8, BLOOD)
    # obi (cinto)
    ax, ay = hx - (hx - sx) * 0.08, hy - (hy - sy) * 0.08
    cv.line([(ax - nrm[0] * tw_h, ay - nrm[1] * tw_h), (ax + nrm[0] * tw_h, ay + nrm[1] * tw_h)], 2.8, v["sash"])
    cv.line([(ax - nrm[0] * tw_h, ay - nrm[1] * tw_h), (ax - nrm[0] * tw_h - 3.2, ay - nrm[1] * tw_h + 4.4)], 1.1, v["sash"])
    # manchas de sangre
    cv.circle((sx - 0.8, sy + 5.8), 1.5, BLOOD)
    cv.circle((hx + 1.6, hy - 5.0), 1.0, BLOOD)

    # ---- lado cercano ----
    leg_draw((hip[0] + 1.0, hip[1]), front_leg, v["leg"], False)
    # cabeza: cuello, cráneo, rostro hundido
    cv.line([(sx + 0.4, sy - 1.0), (head[0] - 0.6, head[1] + 3.6)], 3.0, SKIN_FAR)
    cv.circle(head, 5.0, SKIN)
    cv.ellipse((head[0] + 1.2, head[1] + 3.6), 3.2, 2.2, SKIN)                       # mandíbula
    cv.circle((head[0] + 2.7, head[1] - 0.6), 1.5, SKIN_DARK)                        # cuenca
    cv.circle((head[0] + 3.1, head[1] - 0.5), 0.8, EYE)
    cv.circle((head[0] - 1.2, head[1] - 0.2), 1.0, SKIN_DARK)
    cv.line([(head[0] + 0.4, head[1] + 3.2), (head[0] + 4.0, head[1] + 3.2 + mouth)], 1.0, (50, 20, 22, 255))
    for k in range(3):                                                               # dientes
        cv.line([(head[0] + 1.2 + k * 1.1, head[1] + 3.0), (head[0] + 1.2 + k * 1.1, head[1] + 4.2 + mouth * 0.6)], 0.4, BONE)
    cv.line([(head[0] - 2.4, head[1] + 1.4), (head[0] - 0.4, head[1] + 2.4)], 0.6, BLOOD)   # herida
    if hat == "kabuto":
        # casco agrietado (kabuto) con un cuerno roto y barboquejo
        cv.poly([(head[0] - 5.6, head[1] - 0.6), (head[0] + 5.2, head[1] - 0.6), (head[0] + 3.6, head[1] - 6.6),
                 (head[0] - 0.4, head[1] - 8.0), (head[0] - 4.2, head[1] - 6.2)], INK2)
        cv.line([(head[0] - 6.4, head[1] - 0.8), (head[0] + 5.8, head[1] - 0.8)], 1.5, (70, 72, 88, 255))
        cv.line([(head[0] - 5.4, head[1] - 0.2), (head[0] - 6.4, head[1] + 3.8)], 0.9, RED_DARK)        # cordón
        cv.line([(head[0] + 0.6, head[1] - 7.6), (head[0] + 2.0, head[1] - 5.0)], 0.5, BONE)             # grieta
        cv.line([(head[0] - 0.4, head[1] - 7.8), (head[0] - 2.4, head[1] - 10.4)], 1.2, (130, 100, 40, 255))  # cuerno roto
        cv.line([(head[0] - 5.0, head[1] + 0.6), (head[0] - 5.4, head[1] + 4.6)], 1.6, HAIR)             # pelo suelto
    elif hat == "jingasa":
        # sombrero de hierro cónico (jingasa) abollado, con barboquejo
        cv.ellipse((head[0], head[1] - 0.8), 9.2, 2.0, (34, 34, 42, 255))
        cv.poly([(head[0] - 9.0, head[1] - 0.8), (head[0] + 9.0, head[1] - 0.8), (head[0] + 0.8, head[1] - 9.4)], INK2)
        cv.poly([(head[0] - 9.0, head[1] - 0.8), (head[0] - 3.0, head[1] - 0.8), (head[0] + 0.4, head[1] - 9.0)], (36, 38, 48, 255))
        cv.line([(head[0] - 9.0, head[1] - 0.6), (head[0] + 9.0, head[1] - 0.6)], 0.9, (92, 94, 110, 255))
        cv.circle((head[0] + 3.4, head[1] - 4.0), 1.1, (126, 70, 40, 255))                                   # óxido
        cv.line([(head[0] - 6.0, head[1] - 0.4), (head[0] - 4.4, head[1] + 3.6)], 0.8, RED_DARK)             # barboquejo
        cv.line([(head[0] - 5.2, head[1] + 0.8), (head[0] - 5.8, head[1] + 4.4)], 1.4, HAIR)                 # pelo suelto
    else:
        # pelo enmarañado con moño caído y banda rota
        cv.poly([(head[0] - 5.2, head[1] + 1.4), (head[0] - 5.0, head[1] - 3.0), (head[0] - 1.0, head[1] - 5.8),
                 (head[0] + 3.4, head[1] - 4.8), (head[0] + 1.6, head[1] - 2.8), (head[0] - 1.6, head[1] - 1.8)], HAIR)
        for k, (dx, dy) in enumerate(((-6.4, 3.4), (-6.0, 6.4), (-4.4, 8.0))):
            cv.line([(head[0] - 4.4, head[1] + k * 0.6), (head[0] + dx, head[1] + dy)], 0.9, HAIR)
        cv.line([(head[0] - 2.8, head[1] - 5.0), (head[0] - 4.8, head[1] - 8.4)], 1.5, HAIR)              # moño
        cv.line([(head[0] - 4.8, head[1] - 1.6), (head[0] + 4.2, head[1] - 2.4)], 1.1, BONE)             # hachimaki
        cv.line([(head[0] - 4.8, head[1] - 1.6), (head[0] - 8.0, head[1] + 0.8)], 0.8, BONE)
    # brazo cercano (y la katana rota del samurái)
    mid, end = arm_draw((shoulder[0] + 1.2, shoulder[1] + 1.5), front_arm, False)
    if blade:
        broken_blade(cv, end, front_arm[0] + front_arm[1])
    if hit:                                                                          # destello al recibir un golpe
        cv.effect_poly([(head[0] + 4, head[1] - 9), (head[0] + 6, head[1] - 4), (head[0] + 11, head[1] - 3),
                        (head[0] + 6.5, head[1] - 0.5), (head[0] + 7.5, head[1] + 5), (head[0] + 3.5, head[1] + 1.5)],
                       (250, 244, 232, 215))
    return cv


# ---------------------------------------------------------------- animaciones
def anim_walk(variant):
    """Caminar arrastrando los pies: pasos cortos, brazos extendidos y cabeza colgando."""
    frames = []
    n = 6
    for i in range(n):
        p = 2 * math.pi * i / n
        fl = (26 * math.sin(p), -(8 + 30 * max(0.0, math.cos(p))))
        bl = (26 * math.sin(p + math.pi), -(8 + 30 * max(0.0, math.cos(p + math.pi))))
        frames.append(draw_zombie(variant, bob=0.8 * abs(math.sin(p)), lean=18 + 2 * math.sin(p), front_leg=fl,
                                  back_leg=bl, front_arm=(78 + 8 * math.sin(p), 8), back_arm=(88 - 8 * math.sin(p), 6),
                                  head_drop=3.0 + 0.8 * math.sin(p + 1), sway=0.8 * math.sin(p),
                                  mouth=0.4 * (1 + math.sin(p))).result())
    return frames


def anim_attack(variant):
    """Zarpazo: levanta los brazos, se lanza hacia adelante y los baja de golpe."""
    p = [
        dict(lean=8, front_arm=(150, 10), back_arm=(165, 8), head_drop=1.0, mouth=2.4, front_leg=(-6, -4), back_leg=(8, 2)),
        dict(lean=16, front_arm=(130, 12), back_arm=(150, 10), head_drop=2.0, mouth=3.0, front_leg=(2, -4), back_leg=(-8, 4)),
        dict(lean=32, front_arm=(58, 4), back_arm=(70, 6), head_drop=5.0, mouth=3.0, front_leg=(24, -6), back_leg=(-18, 8), sway=2.0),
        dict(lean=26, front_arm=(40, 6), back_arm=(52, 6), head_drop=4.0, mouth=1.0, front_leg=(20, -6), back_leg=(-14, 6), sway=1.4),
    ]
    return [draw_zombie(variant, **pose).result() for pose in p]


def anim_hurt(variant):
    frames = []
    for i, lean in enumerate((-8.0, -13.0)):
        frames.append(draw_zombie(variant, lean=lean, front_arm=(128 + 10 * i, 10), back_arm=(-100, 8),
                                  front_leg=(14, -8), back_leg=(-14, 8), head_drop=-1.0, mouth=3.0,
                                  hit=(i == 0)).result())
    return frames


def anim_death(variant):
    base = draw_zombie(variant, lean=-10.0, front_arm=(130, 10), back_arm=(-100, 8), front_leg=(12, -8),
                       back_leg=(-14, 8), head_drop=-1.0, mouth=3.0)
    pasos = ((0, 0, 0), (22, 2, 0), (52, 9, 1), (82, 15, 3), (90, 17, 4))
    return [base.result(rotate=a, shift=(dx, -dy)) for a, dx, dy in pasos]


def anim_run(variant):
    """Embestida: cuerpo muy inclinado, zancadas largas y brazos extendidos al frente."""
    frames = []
    n = 6
    for i in range(n):
        p = 2 * math.pi * i / n

        def leg(phase):
            return (52 * math.sin(phase), -(10 + 70 * max(0.0, math.cos(phase))))

        frames.append(draw_zombie(variant, bob=1.8 * abs(math.sin(p)), lean=36 + 3 * math.sin(p), front_leg=leg(p),
                                  back_leg=leg(p + math.pi), front_arm=(66 + 14 * math.sin(p), 10),
                                  back_arm=(84 - 14 * math.sin(p), 8), head_drop=5.0, sway=2.2,
                                  mouth=3.0).result())
    return frames


def anim_stun(variant):
    """Aturdido tras fallar la embestida: encorvado, con la cabeza colgando y balanceándose."""
    frames = []
    for i, (lean, sway, drop) in enumerate(((14.0, -1.2, 6.5), (18.0, 1.2, 7.5))):
        frames.append(draw_zombie(variant, lean=lean, sway=sway, front_arm=(8 + 6 * i, 10), back_arm=(-6 - 6 * i, 10),
                                  front_leg=(12, -6), back_leg=(-12, 6), head_drop=drop, mouth=1.5 + i).result())
    return frames


ANIMS_BY_TYPE = {
    "caminante": {"walk": anim_walk, "attack": anim_attack, "hurt": anim_hurt, "death": anim_death},
    "corredor": {"walk": anim_walk, "run": anim_run, "stun": anim_stun, "death": anim_death},
}


def main():
    raiz = Path(__file__).resolve().parent.parent
    todo_por_tipo = {}
    for kind, variants in TYPES.items():
        out = raiz / "assets" / "images" / "zombi" / kind
        out.mkdir(parents=True, exist_ok=True)
        todo = {}
        for variant in variants:
            for name, build in ANIMS_BY_TYPE[kind].items():
                frames = build(variant)
                todo[f"{variant} {name}"] = frames
                save_strip(frames, out / f"{variant}_{name}.png")
                print(f"{kind}/{variant}_{name}.png: {len(frames)} cuadros")
        todo_por_tipo[kind] = todo
    if "--preview" in sys.argv[1:]:
        destino = raiz / "docs" / "img"
        destino.mkdir(parents=True, exist_ok=True)
        for kind, todo in todo_por_tipo.items():
            save_preview(todo, destino / f"zombi_{kind}.png", 2)
            print(f"docs/img/zombi_{kind}.png generado")


if __name__ == "__main__":
    main()
