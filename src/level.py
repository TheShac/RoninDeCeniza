"""Nivel cargado desde un archivo de texto.

Formato de levels/*.txt:
  - Líneas que empiezan con ';' son parámetros: ;clave=valor  (gravity, grip, nombre, modo=pruebas)
  - '#' bloque sólido, 'P' posición inicial del jugador, '.' vacío
  - Zombis (aparecen apoyados en el suelo de esa casilla): 'Z' caminante aldeano, 'X' caminante samurai,
    'R' corredor campesino, 'A' corredor ashigaru, 'C' arquero cazador, 'Y' arquero kyudoka, 'H' hinchado (sumo)
  - 'O' sierra giratoria fija (centrada en la casilla). Una sierra con riel: ;sierra=col,fila,recorrido_x,recorrido_y[,velocidad[,radio]]
Agregar un nivel nuevo = agregar un .txt, sin tocar el código.
"""
import pygame

from settings import TILE, GRAVITY, PLAYER_SIZE, PAPER, INK, SAW_RADIUS, SAW_PATH_SPEED


ENEMY_CHARS = {                       # letra -> (tipo, variante)
    "Z": ("caminante", "aldeano"),
    "X": ("caminante", "samurai"),
    "R": ("corredor", "campesino"),
    "A": ("corredor", "ashigaru"),
    "C": ("arquero", "cazador"),
    "Y": ("arquero", "kyudoka"),
    "H": ("hinchado", "sumo"),
}


class Level:
    def __init__(self, path):
        self.name = str(path)
        self.gravity = GRAVITY
        self.grip = 1.0           # 1.0 suelo normal, valores bajos = hielo (poca fricción)
        self.solids = []
        self.test_mode = False    # ;modo=pruebas habilita las teclas 1 y 2 para generar zombis
        self.spawn = (TILE, TILE)
        self.enemy_spawns = []    # (tipo, variante, x de los pies, y de los pies)
        self.saw_specs = []       # (cx, cy, radio, dx, dy, velocidad): sierras (todo en px)

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
                elif ch == "O":
                    self.saw_specs.append((c * TILE + TILE / 2, r * TILE + TILE / 2, SAW_RADIUS, 0.0, 0.0, SAW_PATH_SPEED))
                elif ch in ENEMY_CHARS:
                    self.enemy_spawns.append((*ENEMY_CHARS[ch], c * TILE + TILE / 2, (r + 1) * TILE))

        self.width = max((len(row) for row in rows), default=0) * TILE
        self.height = len(rows) * TILE

    def _add_saw(self, value):
        """;sierra=col,fila,recorrido_x,recorrido_y[,velocidad[,radio]]  (col y fila en casillas; el recorrido es el
        desplazamiento total del riel en casillas, 0,0 = fija; velocidad en px/s; radio en px)."""
        try:
            nums = [float(v) for v in value.split(",")]
            if not 4 <= len(nums) <= 6:
                raise ValueError("se esperan de 4 a 6 números")
            col, row, dx, dy = nums[:4]
            speed = nums[4] if len(nums) > 4 else SAW_PATH_SPEED
            radius = nums[5] if len(nums) > 5 else SAW_RADIUS
            if radius <= 0 or speed < 0:
                raise ValueError("radio y velocidad deben ser positivos")
        except ValueError as error:
            print(f"Aviso: sierra ignorada ({value!r}): {error}")
            return
        self.saw_specs.append((col * TILE + TILE / 2, row * TILE + TILE / 2, radius, dx * TILE, dy * TILE, speed))

    def _set_param(self, key, value):
        if key == "gravity":
            self.gravity = float(value)
        elif key == "grip":
            self.grip = float(value)
        elif key == "sierra":
            self._add_saw(value)
        elif key == "modo":
            self.test_mode = value == "pruebas"
        elif key == "nombre":
            self.name = value

    def draw(self, surface, camera):
        sw, sh = surface.get_size()
        for r in self.solids:
            x, y = r.x - camera.x, r.y - camera.y
            if x + r.w < 0 or x > sw or y + r.h < 0 or y > sh:
                continue  # fuera de pantalla
            pygame.draw.rect(surface, INK, (int(x), int(y), r.w, r.h))
