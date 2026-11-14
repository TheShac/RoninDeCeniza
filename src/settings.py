"""Constantes globales del juego (unidades: píxeles y segundos)."""
from pathlib import Path

# --- Rutas ---
BASE_DIR = Path(__file__).resolve().parent.parent
LEVELS_DIR = BASE_DIR / "levels"
SPRITES_DIR = BASE_DIR / "assets" / "images"

# --- Ventana ---
WIDTH, HEIGHT = 960, 544
FPS = 60
TILE = 32                 # tamaño de cada bloque del mapa
MAX_DT = 1 / 30           # tope del delta time (evita saltos enormes si el juego se congela)

# --- Paleta: tinta sobre papel ---
PAPER = (238, 232, 218)
INK = (24, 24, 28)
RED = (190, 40, 40)
GREY = (120, 120, 126)
GREEN = (40, 150, 70)

# --- Física del jugador ---
GRAVITY = 2200.0          # px/s^2 (se puede cambiar por nivel)
MAX_FALL_SPEED = 1400.0   # velocidad terminal
RUN_SPEED = 300.0         # px/s
GROUND_ACCEL = 2600.0     # px/s^2 al acelerar en el suelo
GROUND_FRICTION = 2200.0  # px/s^2 al soltar las teclas en el suelo
AIR_ACCEL = 1500.0        # control en el aire
AIR_DRAG = 300.0          # frenado leve en el aire sin input
JUMP_SPEED = 780.0        # velocidad inicial del salto (altura = v^2 / 2g, unos 138 px)
JUMP_CUT = 0.45           # al soltar el botón en ascenso, la velocidad vertical se multiplica por esto
COYOTE_TIME = 0.10        # s de gracia para saltar justo después de dejar el borde
JUMP_BUFFER = 0.12        # s en que se recuerda un salto pedido un poco antes de aterrizar

PLAYER_SIZE = (24, 58)   # hitbox (ancho, alto); el dibujo es un poco más ancho que la hitbox
SPRITE_FRAME = 96        # tamaño de cada cuadro de animación
SPRITE_FEET_Y = 90       # fila del cuadro donde apoyan los pies

PLAYER_CROUCH_H = 40      # alto de la hitbox al agacharse (el ancho no cambia)
CROUCH_SPEED_MULT = 0.4   # agachado se camina más lento
ACTION_SPEED_MULT = 0.5   # mientras ataca, desvía o lanza, se camina a la mitad

# --- Acciones del Ronin (duración en segundos; coinciden con la animación) ---
ACTION_TIME = {"attack": 0.30, "parry": 0.35, "throw": 0.30, "dash": 0.15, "hurt": 0.40, "death": 0.80}
DASH_SPEED = 650.0        # px/s durante el dash
DASH_COOLDOWN = 1.0       # s entre dashes
HURT_KNOCKBACK = (200.0, -280.0)   # impulso al recibir un golpe (hacia atrás y arriba)

# --- Shuriken (tiro parabólico + rotación) ---
SHURIKEN_SPEED = 700.0       # px/s horizontal
SHURIKEN_LIFT = -60.0        # px/s vertical inicial (sale levemente hacia arriba)
SHURIKEN_GRAVITY = 600.0     # px/s^2 (mucho menor que la del jugador)
SHURIKEN_SPIN = 720.0        # grados/s
SHURIKEN_RADIUS = 9
SHURIKEN_LIFETIME = 2.0      # s
THROW_RELEASE = 0.15         # s desde que empieza el lanzamiento hasta que la estrella sale de la mano
SHURIKEN_HAND = (22, -26)    # posición de salida respecto a los pies (x hacia donde mira, y hacia arriba)
