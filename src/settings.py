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
STEEL = (150, 154, 166)
ICE = (178, 208, 226)
ICE_LINE = (232, 244, 250)
WOOD = (150, 118, 74)

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
DASH_DIAGONAL_SPEED = 800.0       # px/s del dash en diagonal (W + A/D + Shift): llega más lejos que el horizontal
DASH_DIAGONAL_EXIT_KEEP = 0.35    # al terminar el dash diagonal conserva este % de la velocidad (evita planear lejos)
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

# --- Vida y combate del Ronin ---
PLAYER_MAX_HEALTH = 5        # corazones
PLAYER_IFRAMES = 1.0         # s de invulnerabilidad tras recibir daño
SLASH_REACH = 64.0           # px de alcance del tajo
SLASH_ARC = 120.0            # grados de apertura del tajo (60 a cada lado de la horizontal)
SLASH_WINDOW = (0.06, 0.22)  # s desde que empieza el ataque durante los que el arco hace daño
SLASH_ORIGIN_Y = 0.35        # altura del hombro como fracción del alto de la hitbox (desde arriba)
DEATH_RESTART = 1.5          # s tras morir antes de reiniciar el nivel

# --- Zombi caminante (variantes: aldeano y samurai) ---
WALKER_SIZE = (24, 50)
WALKER_HEALTH = 1
WALKER_PATROL_SPEED = 60.0
WALKER_CHASE_SPEED = 90.0
WALKER_ACCEL = 700.0
WALKER_SIGHT = 220.0         # px de visión (se compara el cuadrado de la distancia)
WALKER_SIGHT_DY = 90.0       # diferencia de altura máxima para verte
WALKER_ATTACK_RANGE = 30.0   # px de separación entre cajas para lanzar el zarpazo
WALKER_ATTACK_COOLDOWN = 1.0
ENEMY_ACTION_TIME = {"attack": 0.40, "hurt": 0.35, "death": 0.80}
ENEMY_HIT_WINDOW = (0.15, 0.30)   # s del ataque en los que el zarpazo hiere
ENEMY_CLAW = (36, 34)        # caja del zarpazo delante del enemigo
ENEMY_KNOCKBACK = (180.0, -200.0)
CORPSE_TIME = 2.0            # s que queda el cuerpo antes de desaparecer

# --- Zombi corredor (variantes: campesino y ashigaru) ---
RUNNER_SIZE = (26, 46)
RUNNER_HEALTH = 1
RUNNER_PATROL_SPEED = 80.0
RUNNER_SIGHT = 320.0         # px; al verte con el Ronin dentro de este radio, embiste
RUNNER_ACCEL = 900.0         # px/s^2 (movimiento uniformemente acelerado)
RUNNER_MAX_SPEED = 260.0     # px/s
RUNNER_BRAKE = 1400.0        # px/s^2 de frenado por fricción al terminar la embestida
RUNNER_CHARGE_DIST = 420.0   # px máximos que recorre una embestida
RUNNER_STUN = 0.8            # s aturdido si la embestida falla
RUNNER_COOLDOWN = 1.2        # s antes de poder embestir de nuevo

# --- Zombi hinchado (luchador de sumo): lento, se infla y explota ---
BLOATER_SIZE = (60, 62)         # cabe bajo una plataforma a 2 casillas del suelo (64 px)
BLOATER_FRAME = (160, 128)   # sus cuadros son más grandes que los 96x96 del resto
BLOATER_FEET_Y = 124         # fila del cuadro donde apoyan los pies
BLOATER_HEALTH = 3
BLOATER_PATROL_SPEED = 30.0
BLOATER_CHASE_SPEED = 48.0
BLOATER_SIGHT = 260.0        # px de visión
BLOATER_TRIGGER = 34.0       # px de separación entre cajas a los que empieza a inflarse
BLOATER_TRIGGER_DY = 50.0
BLOATER_FUSE = 1.0           # s inflándose antes de reventar
BLOATER_DEATH_FUSE = 0.45    # s que tarda en reventar si lo matan (da tiempo de alejarse)
BLOATER_EXPLODE_TIME = 0.6   # s de animación de la explosión
BLOATER_KNOCKBACK = 60.0     # px/s: pesa mucho, casi no retrocede

# --- Explosión (impulso radial) ---
BLAST_RADIUS = 110.0         # px
BLAST_IMPULSE = 560.0        # px/s de velocidad que recibe en el centro; baja linealmente hasta 0 en el borde
BLAST_LIFT = 0.6             # componente hacia arriba que se suma a la dirección radial
BLAST_PLAYER_DAMAGE = 2      # corazones que quita al Ronin
BLAST_ENEMY_DAMAGE = 3       # daño a otros zombis (mata a todos, incluso a otro hinchado: reacción en cadena)
BLAST_RING_TIME = 0.35       # s que dura el anillo visual

# --- Sierras giratorias (peligro del escenario) ---
SAW_RADIUS = 26.0            # px del dibujo (cabe en una casilla de 32 px con los dientes)
SAW_HIT_SCALE = 0.88         # la zona de golpe es un 88 % del radio dibujado: perdona un poco los dientes
SAW_OMEGA = 18.0             # rad/s (unas 2,9 vueltas por segundo)
SAW_TEETH = 12
SAW_PATH_SPEED = 90.0        # px/s por defecto cuando va y viene por un riel
SAW_DAMAGE = 1               # corazones por contacto

# --- Suelo de hielo y plataformas móviles ---
ICE_GRIP = 0.10              # el agarre del suelo se multiplica por esto sobre hielo (poca aceleración y poco frenado)
PLATFORM_H = 16              # px de alto de una plataforma móvil
PLATFORM_SPEED = 70.0        # px/s por defecto de una plataforma lineal
PLATFORM_OMEGA = 0.8         # rad/s por defecto de una plataforma circular (una vuelta cada 7,9 s)

# --- Desvío (parry) ---
PARRY_WINDOW = (0.05, 0.25)  # s del desvío durante los que la hoja devuelve proyectiles
PARRY_LOCKOUT = 0.6          # s inutilizable si el desvío no tocó ningún proyectil
PARRY_ZONE = (48, 56)        # caja delante del Ronin que cubre la hoja (ancho, alto)
PARRY_SPEED_BONUS = 1.25     # el proyectil devuelto sale un 25 % más rápido

# --- Flechas y zombi arquero (variantes: cazador y kyudoka) ---
ARROW_SPEED = 420.0
ARROW_LIFETIME = 3.0
REFLECTED_ARROW_DAMAGE = 2   # una flecha devuelta mata a un arquero (2 de vida)
ARCHER_SIZE = (24, 50)
ARCHER_HEALTH = 2
ARCHER_SIGHT = 450.0         # px a los que dispara
ARCHER_RETREAT_DIST = 150.0  # si el Ronin se acerca más que esto, retrocede
ARCHER_RETREAT_SPEED = 80.0
ARCHER_COOLDOWN = 2.0        # s entre disparos
ARCHER_SHOOT_TIME = 0.8      # duración de la animación de disparo
ARCHER_RELEASE = 0.48        # s desde que empieza a tensar hasta que suelta la flecha
ARCHER_BOW = (24, -35)       # salida de la flecha respecto a los pies (adelante, arriba)
ARCHER_MAX_SLOPE = 0.7       # inclinación máxima del disparo (|dy| <= 0.7 |dx|)
