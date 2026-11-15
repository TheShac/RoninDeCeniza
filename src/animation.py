"""Animaciones por cuadros: una tira horizontal de imágenes que se recorre según el tiempo.

El cuadro actual se calcula como: indice = int(tiempo * fps), con `%` si la animación es cíclica.
Así la animación avanza según el tiempo real (dt) y no según los fps de la pantalla.
"""
import pygame

import settings as S


class Animation:
    def __init__(self, frames, fps, loop=True):
        self.frames = frames
        self.fps = fps
        self.loop = loop


class Animator:
    def __init__(self, animations, start="idle"):
        self.animations = animations
        self.name = start
        self.time = 0.0

    def play(self, name, restart=False):
        """Cambia de animación. No reinicia si ya es la que se reproduce, salvo que `restart` sea True."""
        if name in self.animations and (name != self.name or restart):
            self.name = name
            self.time = 0.0

    def update(self, dt, speed=1.0):
        """`speed` acelera o frena la animación (por ejemplo, según la velocidad al correr)."""
        self.time += dt * speed

    @property
    def frame(self):
        anim = self.animations[self.name]
        index = int(self.time * anim.fps)
        if anim.loop:
            index %= len(anim.frames)
        else:
            index = min(index, len(anim.frames) - 1)
        return anim.frames[index]


def load_strip(path, frame_w, frame_h):
    """Carga una tira horizontal de cuadros y devuelve la lista de imágenes."""
    image = pygame.image.load(str(path)).convert_alpha()
    count = image.get_width() // frame_w
    return [image.subsurface((i * frame_w, 0, frame_w, frame_h)).copy() for i in range(count)]


# Animaciones del Ronin. Cíclicas: fps fijo. De acción: duración en segundos (el fps se calcula
# como cuadros / duración, así la animación dura exactamente lo mismo que la acción).
RONIN_ANIMATIONS = {
    "idle": dict(fps=5, loop=True),
    "run": dict(fps=12, loop=True),
    "crouch": dict(fps=3, loop=True),
    "crouch_walk": dict(fps=8, loop=True),
    "jump": dict(fps=1, loop=False),
    "fall": dict(fps=1, loop=False),
    "attack": dict(duration=S.ACTION_TIME["attack"]),
    "parry": dict(duration=S.ACTION_TIME["parry"]),
    "throw": dict(duration=S.ACTION_TIME["throw"]),
    "dash": dict(duration=S.ACTION_TIME["dash"]),
    "hurt": dict(duration=S.ACTION_TIME["hurt"]),
    "death": dict(duration=S.ACTION_TIME["death"]),
}


def load_ronin_animations():
    """Carga las hojas del Ronin. Devuelve None si faltan (el juego usa un dibujo provisional)."""
    try:
        animations = {}
        for name, spec in RONIN_ANIMATIONS.items():
            frames = load_strip(S.SPRITES_DIR / "ronin" / f"{name}.png", S.SPRITE_FRAME, S.SPRITE_FRAME)
            if "duration" in spec:
                animations[name] = Animation(frames, len(frames) / spec["duration"], loop=False)
            else:
                animations[name] = Animation(frames, spec["fps"], spec["loop"])
        return animations
    except (FileNotFoundError, pygame.error) as error:
        print(f"Aviso: no se pudieron cargar los sprites del Ronin ({error}).")
        return None


# Animaciones de los zombis. Cada tipo tiene su carpeta (assets/images/zombi/<tipo>/<variante>_<animación>.png)
# y sus variantes de apariencia.
ENEMY_VARIANTS = {
    "caminante": ("aldeano", "samurai"),
    "corredor": ("campesino", "ashigaru"),
}
ENEMY_ANIMATIONS = {
    "caminante": {
        "walk": dict(fps=6, loop=True),
        "attack": dict(duration=S.ENEMY_ACTION_TIME["attack"]),
        "hurt": dict(duration=S.ENEMY_ACTION_TIME["hurt"]),
        "death": dict(duration=S.ENEMY_ACTION_TIME["death"]),
    },
    "corredor": {
        "walk": dict(fps=7, loop=True),
        "run": dict(fps=14, loop=True),
        "stun": dict(fps=4, loop=True),
        "death": dict(duration=S.ENEMY_ACTION_TIME["death"]),
    },
}


def load_enemy_animations(kind, variant):
    """Carga las hojas de una variante de zombi. Devuelve None si faltan (se dibuja un rectángulo)."""
    try:
        animations = {}
        for name, spec in ENEMY_ANIMATIONS[kind].items():
            frames = load_strip(S.SPRITES_DIR / "zombi" / kind / f"{variant}_{name}.png", S.SPRITE_FRAME, S.SPRITE_FRAME)
            if "duration" in spec:
                animations[name] = Animation(frames, len(frames) / spec["duration"], loop=False)
            else:
                animations[name] = Animation(frames, spec["fps"], spec["loop"])
        return animations
    except (FileNotFoundError, pygame.error) as error:
        print(f"Aviso: no se pudieron cargar los sprites de {kind} {variant} ({error}).")
        return None
