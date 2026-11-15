"""Fondo con parallax: capas que se desplazan más despacio cuanto más lejos están (efecto de perspectiva).

Idea física: al mover la vista, lo cercano cruza el campo visual rápido y lo lejano casi no se mueve.
Cada capa tiene un factor k entre 0 y 1 (0 = fija como el cielo, 1 = se mueve con el mundo):

    desplazamiento en pantalla de la capa = - x_cámara * k          (igual en vertical)

Las capas "en bucle" se repiten en horizontal: se dibuja la imagen en  x0 + n*ancho  con  x0 = (-x_cámara*k) mod ancho,
así nunca se acaba aunque el nivel sea más largo que la imagen.
"""
import pygame

import settings as S

FONDOS_DIR = S.SPRITES_DIR / "fondos"

# nombre del fondo -> capas de atrás hacia delante: (archivo, factor, y de la imagen en pantalla, en bucle)
FONDOS = {
    "aldea": [
        ("cielo",         0.00,   0, False),
        ("humo",          0.08,   0, True),
        ("montanas_lejos", 0.18, 190, True),
        ("montanas_cerca", 0.34, 250, True),
        ("aldea",         0.58, 250, True),
        ("arboles",       0.82, 196, True),
    ],
}


def layer_offset(camera, factor):
    """Desplazamiento de una capa en pantalla (px) para una posición de cámara dada."""
    return -camera * factor


def tile_positions(offset, width, screen_w):
    """Posiciones x (en pantalla) donde hay que dibujar una imagen de ancho `width` repetida para cubrir `screen_w`."""
    if width <= 0:
        return []
    x = offset % width
    if x > 0:
        x -= width
    out = []
    while x < screen_w:
        out.append(x)
        x += width
    return out


class Layer:
    def __init__(self, image, factor, y=0, loop=True):
        self.image, self.factor, self.y, self.loop = image, factor, y, loop

    def draw(self, surface, cam_x, cam_y):
        sw = surface.get_width()
        w = self.image.get_width()
        y = round(self.y + layer_offset(cam_y, self.factor))
        ox = layer_offset(cam_x, self.factor)
        if self.loop:
            for x in tile_positions(ox, w, sw):
                surface.blit(self.image, (x, y))
        else:
            surface.blit(self.image, (round(ox), y))


class Parallax:
    def __init__(self, layers):
        self.layers = layers
        self.enabled = True

    @classmethod
    def load(cls, name):
        """Carga las capas del fondo `name`. Si falta algún archivo, esa capa se omite (el juego sigue funcionando)."""
        layers = []
        for file, factor, y, loop in FONDOS.get(name, []):
            path = FONDOS_DIR / f"{name}_{file}.png"
            if path.exists():
                layers.append(Layer(pygame.image.load(str(path)).convert_alpha(), factor, y, loop))
        return cls(layers)

    def draw(self, surface, cam_x, cam_y):
        surface.fill(S.PAPER)
        if not self.enabled:
            return
        for layer in self.layers:
            layer.draw(surface, cam_x, cam_y)
