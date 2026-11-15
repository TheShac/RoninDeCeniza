"""Enemigos: zombi caminante (Walker) y zombi corredor (Runner). Cada tipo tiene dos variantes de apariencia.

Inteligencia: máquina de estados finita (FSM)
  Walker: patrol --(Ronin a menos de WALKER_SIGHT)--> chase --(a distancia de zarpazo y recargado)--> attack
  Runner: patrol --(Ronin a menos de RUNNER_SIGHT)--> charge --(pared, borde o distancia máxima)--> brake
          brake --(falló la embestida)--> stun (aturdido, sin moverse) --> patrol
  cualquier estado --(daño)--> hurt o dead
Física: la misma que el jugador (gravedad + colisión AABB por ejes con subpasos).
Detección: se compara el CUADRADO de la distancia con el cuadrado del rango, así no hace falta calcular la raíz.
"""
import pygame
from pygame.math import Vector2

import settings as S
from combat import rects_overlap
from physics import move_toward, move_and_collide, overlaps


class Walker:
    """Zombi caminante: lento y constante (movimiento rectilíneo uniforme)."""
    SIZE = S.WALKER_SIZE
    HEALTH = S.WALKER_HEALTH
    ANIM_FOR_STATE = {"patrol": "walk", "chase": "walk", "attack": "attack", "hurt": "hurt", "dead": "death"}
    RESTART_STATES = ("attack", "hurt", "dead")

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
        self.vel.x = move_toward(self.vel.x, self.facing * speed, S.WALKER_ACCEL * level.grip * self._dt)

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

        if self.state == "dead":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * dt)
            if self.state_time > S.ENEMY_ACTION_TIME["death"] + S.CORPSE_TIME:
                self.removable = True
        elif self.state == "hurt":
            self.vel.x = move_toward(self.vel.x, 0.0, S.GROUND_FRICTION * 0.5 * dt)
            if self.state_time >= S.ENEMY_ACTION_TIME["hurt"]:
                self._set_state("patrol")
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

        self.vel.y = min(self.vel.y + level.gravity * dt, S.MAX_FALL_SPEED)
        self.on_ground, self.hit_wall, _ = move_and_collide(self.pos, self.vel, self.size, level.solids, dt)
        if self.hit_wall and self.state == "patrol":
            self.facing = -self.facing
            self.vel.x = 0.0
        if self.pos.y > level.height + 300:
            self.removable = True               # cayó al vacío

        if self.animator:
            self.animator.update(dt, self._anim_speed())

    # ------------------------------------------------------------------ dibujo
    def draw(self, surface, camera):
        if self.animator is None:
            x, y = int(self.pos.x - camera.x), int(self.pos.y - camera.y)
            pygame.draw.rect(surface, (70, 90, 70), (x, y, self.size[0], self.size[1]))
            return
        frame = self.animator.frame
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        x = self.pos.x + self.size[0] / 2 - S.SPRITE_FRAME / 2 - camera.x
        y = self.pos.y + self.size[1] - S.SPRITE_FEET_Y - camera.y
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
            self.vel.x = move_toward(self.vel.x, self.facing * S.RUNNER_MAX_SPEED, S.RUNNER_ACCEL * dt)
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


ENEMY_CLASSES = {"caminante": Walker, "corredor": Runner}
