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

    def play(self, name):
        """Cambia de animación. No reinicia si ya es la que se está reproduciendo."""
        if name != self.name and name in self.animations:
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


# nombre de la animación: (cuadros por segundo, cíclica)
RONIN_ANIMATIONS = {
    "idle": (5, True),
    "run": (12, True),
    "jump": (1, False),
    "fall": (1, False),
}


def load_ronin_animations():
    """Carga las hojas del Ronin. Devuelve None si faltan (el juego usa un dibujo provisional)."""
    try:
        return {
            name: Animation(load_strip(S.SPRITES_DIR / "ronin" / f"{name}.png", S.SPRITE_FRAME, S.SPRITE_FRAME),
                            fps, loop)
            for name, (fps, loop) in RONIN_ANIMATIONS.items()
        }
    except (FileNotFoundError, pygame.error) as error:
        print(f"Aviso: no se pudieron cargar los sprites del Ronin ({error}).")
        return None
