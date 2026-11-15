"""Enemigos: zombi caminante (Walker) y zombi corredor (Runner). Cada tipo tiene dos variantes de apariencia.

Inteligencia: máquina de estados finita (FSM)
  Walker: patrol --(Ronin a menos de WALKER_SIGHT)--> chase --(a distancia de zarpazo y recargado)--> attack
  Runner: patrol --(Ronin a menos de RUNNER_SIGHT)--> charge --(pared, borde o distancia máxima)--> brake
          brake --(falló la embestida)--> stun (aturdido, sin moverse) --> patrol
  Archer: idle --(Ronin a la vista y recargado)--> shoot --(suelta la flecha y termina)--> idle
          idle --(Ronin a menos de ARCHER_RETREAT_DIST y hay suelo atrás)--> retreat
  cualquier estado --(daño)--> hurt o dead
Física: la misma que el jugador (gravedad + colisión AABB por ejes con subpasos).
Detección: se compara el CUADRADO de la distancia con el cuadrado del rango, así no hace falta calcular la raíz.
"""
import math

import pygame
from pygame.math import Vector2

import settings as S
from combat import rects_overlap
from physics import move_toward, move_and_collide, overlaps
from projectile import Arrow


class Walker:
    """Zombi caminante: lento y constante (movimiento rectilíneo uniforme)."""
    SIZE = S.WALKER_SIZE
    HEALTH = S.WALKER_HEALTH
    ANIM_FOR_STATE = {"patrol": "walk", "chase": "walk", "attack": "attack", "hurt": "hurt", "dead": "death"}
    RESTART_STATES = ("attack", "hurt", "dead")
    AFTER_HURT = "patrol"                 # estado al que vuelve tras quedar herido sin morir
    FRAME = (S.SPRITE_FRAME, S.SPRITE_FRAME)   # tamaño del cuadro de sprite
    FEET_Y = S.SPRITE_FEET_Y                   # fila del cuadro donde apoyan los pies
    FLIP = True                                # se voltea al mirar a la izquierda
    blast = None                               # explosión pendiente {x, y, radius}; Game la recoge

    def __init__(self, variant, feet_x, feet_y, animations=None):
        self.variant = variant
        self.size = self.SIZE
        self.pos = Vector2(feet_x - self.size[0] / 2, feet_y - self.size[1])
        self.vel = Vector2(0, 0)
        self.facing = -1
        self.health = self.HEALTH
        self.on_ground = False
        self.hit_wall = False
        self.state = "patrol"
        self.state_time = 0.0
        self.cooldown = 0.0
        self.hit_done = False
        self.removable = False
        self.new_projectiles = []             # proyectiles recién lanzados; Game los recoge cada frame
        self._dt = 0.0
        self.animator = None
        if animations:
            from animation import Animator
            self.animator = Animator(animations, start="walk")

    # ------------------------------------------------------------------ consultas
    @property
    def rect(self):
        return (self.pos.x, self.pos.y, self.size[0], self.size[1])

    @property
    def center(self):
        return (self.pos.x + self.size[0] / 2, self.pos.y + self.size[1] / 2)

    @property
    def dead(self):
        return self.state == "dead"

    @property
    def can_be_hit(self):
        return self.state != "dead"

    @property
    def claw_rect(self):
        cw, ch = S.ENEMY_CLAW
        x = self.pos.x + self.size[0] if self.facing > 0 else self.pos.x - cw
        return (x, self.pos.y + self.size[1] - ch, cw, ch)

    # ------------------------------------------------------------------ estados
    def _set_state(self, name):
        self.state = name
        self.state_time = 0.0
        if self.animator:
            anim = self.ANIM_FOR_STATE[name]
            self.animator.play(anim, restart=name in self.RESTART_STATES)

    def damage(self, amount, from_x):
        """Recibe daño desde la posición x `from_x`. Devuelve True si el golpe contó."""
        if self.dead:
            return False
        self.health -= amount
        away = 1 if self.center[0] >= from_x else -1
        self.vel.update(away * S.ENEMY_KNOCKBACK[0], S.ENEMY_KNOCKBACK[1])
        self.hit_done = True
        self._set_state("dead" if self.health <= 0 else "hurt")
        return True

    def _ground_ahead(self, level, extra=0.0):
        """Hay suelo justo delante de los pies? `extra` mira más lejos (para los que van rápido)."""
        px = self.pos.x + self.size[0] / 2 + self.facing * (self.size[0] / 2 + 4 + extra)
        py = self.pos.y + self.size[1] + 4
        return any(overlaps(px, py, 1, 1, r) for r in level.solids)

    def _walk(self, level, speed, sees):
        """Avanza hacia donde mira; en un borde, da la vuelta (patrulla) o se detiene (si persigue)."""
        if self.on_ground and not self._ground_ahead(level):
            if sees:
                speed = 0.0
            else:
                self.facing = -self.facing
                self.vel.x = 0.0
        if level.on_mud(self.rect):
            speed *= S.MUD_SPEED_MULT                      # el lodo frena también a los zombis
        self.vel.x = move_toward(self.vel.x, self.facing * speed, S.WALKER_ACCEL * level.grip_under(self.rect) * self._dt)

    def _think(self, player, level):
        ex, ey = self.center
        px, py = player.center
        dx, dy = px - ex, py - ey
        sees = (not player.dead and dx * dx + dy * dy <= S.WALKER_SIGHT ** 2 and abs(dy) <= S.WALKER_SIGHT_DY)
        if sees:
            if self.state != "chase":
                self._set_state("chase")
            if dx != 0:
                self.facing = 1 if dx > 0 else -1
            gap = abs(dx) - (self.size[0] + player.size[0]) / 2
            if gap <= S.WALKER_ATTACK_RANGE and abs(dy) <= 40 and self.cooldown <= 0:
                self.cooldown = S.WALKER_ATTACK_COOLDOWN
                self.hit_done = False
                self.vel.x = 0.0
                self._set_state("attack")
                return
            self._walk(level, S.WALKER_CHASE_SPEED, True)
        else:
            if self.state != "patrol":
                self._set_state("patrol")
            self._walk(level, S.WALKER_PATROL_SPEED, False)

    def _anim_speed(self):
        if self.state in ("patrol", "chase"):
            return max(0.3, abs(self.vel.x) / S.WALKER_PATROL_SPEED)
        return 1.0

    # ------------------------------------------------------------------ actualización
    def update(self, dt, level, player):
        self._dt = dt
        self.state_time += dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self._state_logic(level, player)

        self.vel.y = min(self.vel.y + level.gravity * dt, S.MAX_FALL_SPEED)
        self.on_ground, self.hit_wall, _ = move_and_collide(self.pos, self.vel, self.size, level.solids, dt)
        if self.hit_wall and self.state == "patrol":
            self.facing = -self.facing
            self.vel.x = 0.0
        if self.pos.y > level.height + 300:
            self.removable = True               # cayó al vacío

        if self.animator:
            self.animator.update(dt, self._anim_speed())
            self._sync_animation()

    def _sync_animation(self):
        """Gancho: algunos enemigos fijan el cuadro a mano (el hinchado, según su mecha)."""

    def _state_logic(self, level, player):
        """Un paso de la máquina de estados (velocidades, ataques, cambios de estado)."""
        dt = self._dt
        if self.state == "dead":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * dt)
            if self.state_time > S.ENEMY_ACTION_TIME["death"] + S.CORPSE_TIME:
                self.removable = True
        elif self.state == "hurt":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * 0.5 * dt)
            if self.state_time >= S.ENEMY_ACTION_TIME["hurt"]:
                self._set_state(self.AFTER_HURT)
        elif self.state == "attack":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * dt)
            lo, hi = S.ENEMY_HIT_WINDOW
            if not self.hit_done and lo <= self.state_time <= hi and not player.dead \
                    and rects_overlap(self.claw_rect, player.rect):
                self.hit_done = True
                player.take_damage(self.center[0])
            if self.state_time >= S.ENEMY_ACTION_TIME["attack"]:
                self._set_state("chase")
        else:
            self._think(player, level)

    # ------------------------------------------------------------------ dibujo
    def draw(self, surface, camera):
        if self.animator is None:
            x, y = int(self.pos.x - camera.x), int(self.pos.y - camera.y)
            pygame.draw.rect(surface, (70, 90, 70), (x, y, self.size[0], self.size[1]))
            return
        frame = self.animator.frame
        if self.facing < 0 and self.FLIP:
            frame = pygame.transform.flip(frame, True, False)
        x = self.pos.x + self.size[0] / 2 - self.FRAME[0] / 2 - camera.x
        y = self.pos.y + self.size[1] - self.FEET_Y - camera.y
        surface.blit(frame, (round(x), round(y)))


class Runner(Walker):
    """Zombi corredor: patrulla y, al ver al Ronin, embiste en línea recta con aceleración constante.

    Embestida (MRUA):  v = v + a * dt  hasta RUNNER_MAX_SPEED  (a = 900 px/s^2)
    Al terminar frena por fricción (a = 1400 px/s^2). Si falló, queda aturdido: es la ventana para atacarlo.
    El dash del Ronin lo atraviesa sin daño (es invulnerable), y entonces la embestida cuenta como fallida.
    """
    SIZE = S.RUNNER_SIZE
    HEALTH = S.RUNNER_HEALTH
    ANIM_FOR_STATE = {"patrol": "walk", "charge": "run", "brake": "run", "stun": "stun", "dead": "death",
                      "hurt": "stun"}

    def __init__(self, variant, feet_x, feet_y, animations=None):
        super().__init__(variant, feet_x, feet_y, animations)
        self.charge_start_x = 0.0

    def _start_charge(self, dx):
        if dx != 0:
            self.facing = 1 if dx > 0 else -1
        self.charge_start_x = self.pos.x
        self.hit_wall = False
        self.hit_done = False
        self._set_state("charge")

    def _think(self, player, level):
        px, py = player.center
        ex, ey = self.center
        dx, dy = px - ex, py - ey
        dt = self._dt

        if self.state == "patrol":
            sees = (not player.dead and self.cooldown <= 0 and self.on_ground
                    and dx * dx + dy * dy <= S.RUNNER_SIGHT ** 2 and abs(dy) <= S.WALKER_SIGHT_DY)
            if sees:
                self._start_charge(dx)
            else:
                self._walk(level, S.RUNNER_PATROL_SPEED, False)
                return

        if self.state == "charge":
            self.vel.x = move_toward(self.vel.x, self.facing * S.RUNNER_MAX_SPEED * (S.MUD_SPEED_MULT if level.on_mud(self.rect) else 1.0), S.RUNNER_ACCEL * dt)
            if not self.hit_done and not player.dead and rects_overlap(self.rect, player.rect):
                if player.take_damage(self.center[0]):      # con dash no cuenta: el Ronin es invulnerable
                    self.hit_done = True
            braking = self.vel.x ** 2 / (2 * S.RUNNER_BRAKE) + 6.0
            end = (self.hit_wall
                   or abs(self.pos.x - self.charge_start_x) >= S.RUNNER_CHARGE_DIST
                   or (self.on_ground and not self._ground_ahead(level, braking)))
            if end:
                self._set_state("brake")
        elif self.state == "brake":
            self.vel.x = move_toward(self.vel.x, 0.0, S.RUNNER_BRAKE * dt)
            if self.vel.x == 0.0:
                self.cooldown = S.RUNNER_COOLDOWN
                self._set_state("patrol" if self.hit_done else "stun")
        elif self.state == "stun":
            self.vel.x = 0.0
            if self.state_time >= S.RUNNER_STUN:
                self._set_state("patrol")

    def _anim_speed(self):
        if self.state == "patrol":
            return max(0.3, abs(self.vel.x) / S.RUNNER_PATROL_SPEED)
        if self.state in ("charge", "brake"):
            return max(0.4, abs(self.vel.x) / S.RUNNER_MAX_SPEED)
        return 1.0


class Archer(Walker):
    """Zombi arquero: casi estático. Dispara flechas rectas cada 2 s si ve al Ronin; si se acerca, retrocede.

    Tiene 2 de vida. Las flechas se pueden devolver con el desvío: una flecha devuelta lo mata de un golpe.
    """
    SIZE = S.ARCHER_SIZE
    HEALTH = S.ARCHER_HEALTH
    ANIM_FOR_STATE = {"idle": "idle", "retreat": "walk", "shoot": "shoot", "hurt": "hurt", "dead": "death",
                      "patrol": "idle"}
    RESTART_STATES = ("shoot", "hurt", "dead")
    AFTER_HURT = "idle"

    def __init__(self, variant, feet_x, feet_y, animations=None):
        super().__init__(variant, feet_x, feet_y, animations)
        self.state = "idle"
        self.released = False
        if self.animator:
            self.animator.play("idle", restart=True)

    def _bow_point(self):
        return (self.center[0] + self.facing * S.ARCHER_BOW[0], self.pos.y + self.size[1] + S.ARCHER_BOW[1])

    def _line_of_sight(self, level, target):
        """True si no hay bloques entre el arco y el objetivo (se muestrea el segmento cada 12 px)."""
        ox, oy = self._bow_point()
        dx, dy = target[0] - ox, target[1] - oy
        steps = max(1, int(math.hypot(dx, dy) // 12))
        for i in range(1, steps + 1):
            px, py = ox + dx * i / steps, oy + dy * i / steps
            if any(overlaps(px, py, 1, 1, r) for r in level.solids):
                return False
        return True

    def _ground_behind(self, level):
        px = self.center[0] - self.facing * (self.size[0] / 2 + 6)
        py = self.pos.y + self.size[1] + 4
        return any(overlaps(px, py, 1, 1, r) for r in level.solids)

    def _release(self, player):
        """Suelta la flecha hacia donde está el Ronin en ese instante (la velocidad es ARROW_SPEED)."""
        ox, oy = self._bow_point()
        tx, ty = player.center
        dx, dy = tx - ox, ty - oy
        if dx * self.facing <= 0:                       # el Ronin pasó por detrás: dispara recto hacia adelante
            dx, dy = float(self.facing), 0.0
        length = math.hypot(dx, dy)
        self.new_projectiles.append(Arrow(ox, oy, dx / length * S.ARROW_SPEED, dy / length * S.ARROW_SPEED))
        self.released = True

    def _think(self, player, level):
        dt = self._dt
        if self.state == "shoot":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * dt)
            if not self.released and self.state_time >= S.ARCHER_RELEASE:
                self._release(player)
            if self.state_time >= S.ARCHER_SHOOT_TIME:
                self._set_state("idle")
            return
        dx, dy = player.center[0] - self.center[0], player.center[1] - self.center[1]
        dist2 = dx * dx + dy * dy
        sees = (not player.dead and dist2 <= S.ARCHER_SIGHT ** 2 and self._line_of_sight(level, player.center))
        if sees and dx != 0:
            self.facing = 1 if dx > 0 else -1
        cornered = self.hit_wall and self.state == "retreat"
        if sees and dist2 < S.ARCHER_RETREAT_DIST ** 2 and self._ground_behind(level) and not cornered:
            if self.state != "retreat":
                self._set_state("retreat")
            self.vel.x = move_toward(self.vel.x, -self.facing * S.ARCHER_RETREAT_SPEED, S.WALKER_ACCEL * dt)
            return
        if self.state != "idle":
            self._set_state("idle")
        self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * dt)
        if sees and self.cooldown <= 0 and abs(dy) <= S.ARCHER_MAX_SLOPE * abs(dx) + 30:
            self.cooldown = S.ARCHER_COOLDOWN
            self.released = False
            self._set_state("shoot")

    def _anim_speed(self):
        if self.state == "retreat":
            return max(0.3, abs(self.vel.x) / S.ARCHER_RETREAT_SPEED)
        return 1.0


class Bloater(Walker):
    """Zombi hinchado: un luchador de sumo enorme, lento y con mucha vida. No ataca: EXPLOTA.

    patrol --(Ronin a la vista)--> chase --(Ronin a menos de BLOATER_TRIGGER)--> inflate --(mecha 1 s)--> dead (explota)
    Si lo matan, se infla igual pero con una mecha corta (BLOATER_DEATH_FUSE): hay que alejarse, o matarlo de lejos
    con shurikens. La explosión (ver combat.apply_blast) empuja con un impulso radial y daña a todo el que esté cerca,
    incluidos otros zombis: sirve de arma. Los sprites son de frente, así que no se voltean.
    """
    SIZE = S.BLOATER_SIZE
    HEALTH = S.BLOATER_HEALTH
    FRAME = S.BLOATER_FRAME
    FEET_Y = S.BLOATER_FEET_Y
    FLIP = False
    ANIM_FOR_STATE = {"patrol": "walk", "chase": "walk", "inflate": "inflate", "hurt": "hurt", "dead": "explode"}
    RESTART_STATES = ("inflate", "hurt", "dead")

    def __init__(self, variant, feet_x, feet_y, animations=None):
        super().__init__(variant, feet_x, feet_y, animations)
        self.fuse = 0.0                       # s que faltan para reventar (solo en "inflate")
        self.doomed = False                   # ya no tiene vida: va a reventar sí o sí
        self.blast = None

    @property
    def fuse_progress(self):
        """0 recién encendido, 1 a punto de reventar."""
        return 0.0 if self.state != "inflate" else max(0.0, min(1.0, 1.0 - self.fuse / S.BLOATER_FUSE))

    def _ignite(self, fuse):
        """Empieza a inflarse (o acorta la mecha si ya lo hacía)."""
        if self.state != "inflate":
            self._set_state("inflate")
            self.fuse = S.BLOATER_FUSE
        self.fuse = min(self.fuse, fuse)

    def damage(self, amount, from_x):
        if self.dead:
            return False
        self.health -= amount
        away = 1 if self.center[0] >= from_x else -1
        self.vel.x += away * S.BLOATER_KNOCKBACK
        if self.health <= 0:
            self.doomed = True
            self._ignite(S.BLOATER_DEATH_FUSE)
        elif self.state != "inflate":
            self._set_state("hurt")
        return True

    def _explode(self):
        self._set_state("dead")
        self.vel.x = 0.0
        self.blast = {"x": self.center[0], "y": self.center[1], "radius": S.BLAST_RADIUS}

    def _state_logic(self, level, player):
        dt = self._dt
        if self.state == "dead":
            self.vel.x = 0.0
            if self.state_time >= S.BLOATER_EXPLODE_TIME:
                self.removable = True
        elif self.state == "inflate":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * dt)
            self.fuse -= dt
            if self.fuse <= 0:
                self._explode()
        elif self.state == "hurt":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * 0.5 * dt)
            if self.state_time >= S.ENEMY_ACTION_TIME["hurt"]:
                self._set_state(self.AFTER_HURT)
        else:
            self._think(player, level)

    def _think(self, player, level):
        dx, dy = player.center[0] - self.center[0], player.center[1] - self.center[1]
        sees = (not player.dead and dx * dx + dy * dy <= S.BLOATER_SIGHT ** 2 and abs(dy) <= S.WALKER_SIGHT_DY)
        if not sees:
            if self.state != "patrol":
                self._set_state("patrol")
            self._walk(level, S.BLOATER_PATROL_SPEED, False)
            return
        if self.state != "chase":
            self._set_state("chase")
        if dx != 0:
            self.facing = 1 if dx > 0 else -1
        gap = abs(dx) - (self.size[0] + player.size[0]) / 2
        if gap <= S.BLOATER_TRIGGER and abs(dy) <= S.BLOATER_TRIGGER_DY:
            self._ignite(S.BLOATER_FUSE)
            return
        self._walk(level, S.BLOATER_CHASE_SPEED, True)

    def _anim_speed(self):
        if self.state in ("patrol", "chase"):
            return max(0.3, abs(self.vel.x) / S.BLOATER_PATROL_SPEED)
        return 1.0

    def _sync_animation(self):
        if self.state == "inflate":                      # el cuadro sigue a la mecha, no al reloj
            anim = self.animator.animations["inflate"]
            self.animator.time = self.fuse_progress * 0.999 * len(anim.frames) / anim.fps


ENEMY_CLASSES = {"caminante": Walker, "corredor": Runner, "arquero": Archer, "hinchado": Bloater}
