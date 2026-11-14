"""Nivel cargado desde un archivo de texto.

Formato de levels/*.txt:
  - Líneas que empiezan con ';' son parámetros: ;clave=valor  (gravity, grip, nombre)
  - '#' bloque sólido, 'P' posición inicial del jugador, '.' vacío
Agregar un nivel nuevo = agregar un .txt, sin tocar el código.
"""
import pygame

from settings import TILE, GRAVITY, PLAYER_SIZE, PAPER, INK


class Level:
    def __init__(self, path):
        self.name = str(path)
        self.gravity = GRAVITY
        self.grip = 1.0           # 1.0 suelo normal, valores bajos = hielo (poca fricción)
        self.solids = []
        self.spawn = (TILE, TILE)

        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(";"):
                key, _, value = line[1:].partition("=")
                self._set_param(key.strip(), value.strip())
            elif line.strip():
                rows.append(line)

        pw, ph = PLAYER_SIZE
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == "#":
                    self.solids.append(pygame.Rect(c * TILE, r * TILE, TILE, TILE))
                elif ch == "P":
                    self.spawn = (c * TILE + (TILE - pw) / 2, (r + 1) * TILE - ph)

        self.width = max((len(row) for row in rows), default=0) * TILE
        self.height = len(rows) * TILE

    def _set_param(self, key, value):
        if key == "gravity":
            self.gravity = float(value)
        elif key == "grip":
            self.grip = float(value)
        elif key == "nombre":
            self.name = value

    def draw(self, surface, camera):
        sw, sh = surface.get_size()
        for r in self.solids:
            x, y = r.x - camera.x, r.y - camera.y
            if x + r.w < 0 or x > sw or y + r.h < 0 or y > sh:
                continue  # fuera de pantalla
            pygame.draw.rect(surface, INK, (int(x), int(y), r.w, r.h))
