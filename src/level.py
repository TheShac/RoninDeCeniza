"""Nivel cargado desde un archivo de texto.

Formato de levels/*.txt:
  - Líneas que empiezan con ';' son parámetros: ;clave=valor  (gravity, grip, nombre, modo=pruebas)
  - '#' bloque sólido, 'P' posición inicial del jugador, '.' vacío
  - Zombis (aparecen apoyados en el suelo de esa casilla): 'Z' caminante aldeano, 'X' caminante samurai,
    'R' corredor campesino, 'A' corredor ashigaru, 'C' arquero cazador, 'Y' arquero kyudoka, 'H' hinchado (sumo)
  - '=' bloque de lodo (sólido y pegajoso: al pisarlo se camina a MUD_SPEED_MULT y se salta con MUD_JUMP_MULT)
  - '~' bloque de hielo (sólido y resbaladizo: el agarre se multiplica por ICE_GRIP al pisarlo)
  - Plataformas móviles (sólidas, llevan encima a quien las pisa; 'fila' es la fila de su cara superior):
      ;plataforma=lineal,col,fila,ancho,recorrido_x,recorrido_y[,velocidad]     (ida y vuelta; recorrido en casillas)
      ;plataforma=circular,col,fila,ancho,radio[,omega]                         (gira alrededor del centro de la casilla;
                                                                               radio en casillas, omega en rad/s)
  - ;letrero=col,fila,texto  rótulo de ayuda que se dibuja en el mundo (solo en el modo pruebas)
  - 'O' sierra giratoria fija (centrada en la casilla). Una sierra con riel: ;sierra=col,fila,recorrido_x,recorrido_y[,velocidad[,radio]]
Agregar un nivel nuevo = agregar un .txt, sin tocar el código.
"""
import pygame

from moving_platform import MovingPlatform, step as platform_step
from settings import (TILE, GRAVITY, PLAYER_SIZE, PAPER, INK, SAW_RADIUS, SAW_PATH_SPEED, ICE_GRIP, ICE, ICE_LINE, MUD, MUD_DARK,
                      PLATFORM_H, PLATFORM_SPEED, PLATFORM_OMEGA)


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
        self.ice = []             # bloques de hielo (subconjunto de solids)
        self.mud = []             # bloques de lodo (subconjunto de solids)
        self.signs = []           # (x, y, texto): rótulos del modo pruebas
        self.platform_specs = []  # kwargs de MovingPlatform
        self.platforms = []

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
                elif ch == "=":
                    block = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                    self.solids.append(block)
                    self.mud.append(block)
                elif ch == "~":
                    block = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                    self.solids.append(block)
                    self.ice.append(block)
                elif ch == "P":
                    self.spawn = (c * TILE + (TILE - pw) / 2, (r + 1) * TILE - ph)
                elif ch == "O":
                    self.saw_specs.append((c * TILE + TILE / 2, r * TILE + TILE / 2, SAW_RADIUS, 0.0, 0.0, SAW_PATH_SPEED))
                elif ch in ENEMY_CHARS:
                    self.enemy_spawns.append((*ENEMY_CHARS[ch], c * TILE + TILE / 2, (r + 1) * TILE))

        self.width = max((len(row) for row in rows), default=0) * TILE
        self.height = len(rows) * TILE
        # Las plataformas móviles comparten la lista `solids` (sus rectángulos se mueven en el lugar), así toda la
        # física (jugador, enemigos, proyectiles) las trata como bloques. `static_count` separa los bloques fijos.
        self.static_count = len(self.solids)
        self.platforms = [MovingPlatform(**spec) for spec in self.platform_specs]
        self.solids.extend(p.rect for p in self.platforms)

    @property
    def static_solids(self):
        """Bloques fijos (sin las plataformas móviles)."""
        return self.solids[:self.static_count]

    @staticmethod
    def _foot_on(blocks, rect):
        """True si alguno de los dos pies de la caja (x, y, w, h) pisa uno de `blocks`."""
        x, y, w, h = rect
        py = y + h + 1
        return any(r.left <= px < r.right and r.top <= py < r.bottom for px in (x + 2, x + w - 2) for r in blocks)

    def grip_under(self, rect):
        """Agarre del suelo bajo los pies de la caja (x, y, w, h): el del nivel, o más bajo si pisa hielo."""
        return self.grip * ICE_GRIP if self._foot_on(self.ice, rect) else self.grip

    def on_mud(self, rect):
        """True si pisa lodo (basta un pie)."""
        return self._foot_on(self.mud, rect)

    def update_platforms(self, dt, entities):
        """Mueve las plataformas y arrastra / empuja a las entidades (con pos, size, on_ground)."""
        for e in entities:
            e.ride_vel = (0.0, 0.0)
        for p in self.platforms:
            platform_step(p, dt, entities, self.static_solids)

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

    def _add_platform(self, value):
        """;plataforma=lineal,col,fila,ancho,recorrido_x,recorrido_y[,velocidad]
           ;plataforma=circular,col,fila,ancho,radio[,omega]   (todo en casillas, excepto velocidad px/s y omega rad/s)"""
        try:
            kind, *rest = [v.strip() for v in value.split(",")]
            nums = [float(v) for v in rest]
            if kind == "lineal":
                if not 5 <= len(nums) <= 6:
                    raise ValueError("lineal: col,fila,ancho,recorrido_x,recorrido_y[,velocidad]")
                col, row, width, dx, dy = nums[:5]
                speed = nums[5] if len(nums) > 5 else PLATFORM_SPEED
                if width <= 0 or speed < 0:
                    raise ValueError("ancho positivo y velocidad no negativa")
                spec = dict(x=col * TILE, y=row * TILE, w=width * TILE, h=PLATFORM_H, kind="linear",
                            path=(dx * TILE, dy * TILE), speed=speed)
            elif kind == "circular":
                if not 4 <= len(nums) <= 5:
                    raise ValueError("circular: col,fila,ancho,radio[,omega]")
                col, row, width, radius = nums[:4]
                omega = nums[4] if len(nums) > 4 else PLATFORM_OMEGA
                if width <= 0 or radius <= 0:
                    raise ValueError("ancho y radio positivos")
                cx, cy = col * TILE + TILE / 2, row * TILE + TILE / 2
                # esquina de la plataforma con θ = 0: a la derecha del centro
                spec = dict(x=cx + radius * TILE - width * TILE / 2, y=cy - PLATFORM_H / 2, w=width * TILE, h=PLATFORM_H,
                            kind="circular", radius=radius * TILE, omega=omega)
            else:
                raise ValueError("el tipo debe ser lineal o circular")
        except ValueError as error:
            print(f"Aviso: plataforma ignorada ({value!r}): {error}")
            return
        self.platform_specs.append(spec)

    def _set_param(self, key, value):
        if key == "gravity":
            self.gravity = float(value)
        elif key == "grip":
            self.grip = float(value)
        elif key == "sierra":
            self._add_saw(value)
        elif key == "plataforma":
            self._add_platform(value)
        elif key == "letrero":
            col, _, rest = value.partition(",")
            row, _, text = rest.partition(",")
            try:
                self.signs.append((float(col) * TILE, float(row) * TILE, text.strip()))
            except ValueError:
                print(f"Aviso: letrero ignorado ({value!r})")
        elif key == "modo":
            self.test_mode = value == "pruebas"
        elif key == "nombre":
            self.name = value

    def draw(self, surface, camera, debug=False):
        sw, sh = surface.get_size()
        ice_ids = {id(b) for b in self.ice}
        mud_ids = {id(b) for b in self.mud}
        for r in self.static_solids:
            x, y = r.x - camera.x, r.y - camera.y
            if x + r.w < 0 or x > sw or y + r.h < 0 or y > sh:
                continue  # fuera de pantalla
            if id(r) in ice_ids:                      # hielo: celeste con un brillo, para distinguirlo del suelo normal
                pygame.draw.rect(surface, ICE, (int(x), int(y), r.w, r.h))
                pygame.draw.line(surface, ICE_LINE, (int(x) + 4, int(y) + 5), (int(x) + r.w - 12, int(y) + 5), 2)
                pygame.draw.rect(surface, INK, (int(x), int(y), r.w, r.h), 2)
            elif id(r) in mud_ids:                    # lodo: marrón con ondas oscuras
                pygame.draw.rect(surface, MUD, (int(x), int(y), r.w, r.h))
                for k, off in enumerate((6, 15)):
                    pygame.draw.line(surface, MUD_DARK, (int(x) + 3 + 6 * k, int(y) + off), (int(x) + r.w - 5 - 4 * k, int(y) + off), 2)
                pygame.draw.rect(surface, INK, (int(x), int(y), r.w, r.h), 2)
            else:
                pygame.draw.rect(surface, INK, (int(x), int(y), r.w, r.h))
        for p in self.platforms:
            p.draw(surface, camera, debug)
