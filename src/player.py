"""El Ronin: movimiento, salto, agacharse, dash, acciones de combate y animación.

Ecuaciones usadas (por frame, con dt en segundos):
  v.x  -> se acerca a (dirección * RUN_SPEED) con aceleración; sin input, frena con fricción
  v.y += g * dt                 (gravedad, con velocidad terminal)
  pos  += v * dt                (en move_and_collide, por ejes y con subpasos)
  dash -> v.x = dirección * DASH_SPEED durante 0,15 s; después la inercia se disipa con la fricción

Las acciones (attack, parry, throw, dash, hurt, death) duran lo mismo que su animación (S.ACTION_TIME).
- attack: el arco del tajo hiere a los enemigos durante una ventana corta (ver combat.py).
- throw: suelta un shuriken a mitad de la animación.
- parry: durante una ventana corta devuelve las flechas que tocan la hoja hacia el cursor (ley de reflexión);
  si no toca ninguna, queda inutilizable un tiempo.
"""
from dataclasses import dataclass

import math

import pygame
from pygame.math import Vector2

import settings as S
from physics import move_toward, move_and_collide, overlaps
from projectile import Shuriken


@dataclass
class InputState:
    """Intención del jugador en este frame (separada del teclado para poder probar la física)."""
    move_x: int = 0              # -1 izquierda, 0 quieto, 1 derecha
    jump_pressed: bool = False   # se pulsó saltar en este frame
    jump_held: bool = False      # el botón de salto sigue presionado
    crouch: bool = False         # agacharse (mantener)
    attack_pressed: bool = False
    parry_pressed: bool = False
    throw_pressed: bool = False
    dash_pressed: bool = False
    aim: tuple = None            # dirección del desvío (mouse o WASD con K); None = hacia donde mira. No gira al Ronin


class Player:
    def __init__(self, x, y):
        self.size = S.PLAYER_SIZE
        self.pos = Vector2(x, y)      # esquina superior izquierda de la hitbox
        self.vel = Vector2(0, 0)
        self.on_ground = False
        self.facing = 1
        self.jumping = False
        self.crouching = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.action = None            # None, attack, parry, throw, dash, hurt o death
        self.action_time = 0.0
        self.dash_cooldown = 0.0
        self.animator = None          # lo asigna Game cuando están cargados los sprites
        self._restart_anim = False
        self.health = S.PLAYER_MAX_HEALTH
        self.iframes = 0.0            # invulnerabilidad tras un golpe
        self.slash_hits = set()       # enemigos ya golpeados por el tajo en curso
        self.parry_aim = (1.0, 0.0)   # hacia dónde se devuelven los proyectiles
        self.parry_reflected = False
        self.parry_lock = 0.0         # s que queda inutilizable el desvío tras fallar
        self.new_projectiles = []     # shurikens recién lanzados; Game los recoge cada frame
        self._thrown = False

    # ------------------------------------------------------------------ consultas
    @property
    def state(self):
        """Nombre de la animación a mostrar."""
        if self.action:
            return self.action
        if self.crouching:
            return "crouch_walk" if abs(self.vel.x) > 20 else "crouch"
        if not self.on_ground:
            return "jump" if self.vel.y < 0 else "fall"
        if abs(self.vel.x) > 20:
            return "run"
        return "idle"

    @property
    def invulnerable(self):
        return self.action in ("dash", "hurt", "death")

    @property
    def dead(self):
        return self.action == "death"

    @property
    def rect(self):
        return (self.pos.x, self.pos.y, self.size[0], self.size[1])

    @property
    def center(self):
        return (self.pos.x + self.size[0] / 2, self.pos.y + self.size[1] / 2)

    # ------------------------------------------------------------------ acciones
    def start_action(self, name):
        self.action = name
        self.action_time = S.ACTION_TIME[name]
        self._restart_anim = True
        self._thrown = False
        self.slash_hits = set()
        self.parry_reflected = False

    def hurt(self, source_x=None):
        """Animación de golpe con knockback: se aleja de `source_x` (o hacia atrás si no se indica)."""
        if self.dead or self.action == "hurt":
            return                                   # un golpe en curso no se reinicia ni se encadena
        self.start_action("hurt")
        away = -self.facing if source_x is None else (1 if self.center[0] >= source_x else -1)
        self.vel.update(away * S.HURT_KNOCKBACK[0], S.HURT_KNOCKBACK[1])

    def take_damage(self, source_x=None):
        """Pierde 1 corazón (si no es invulnerable). Devuelve True si el golpe contó."""
        if self.dead or self.invulnerable or self.iframes > 0:
            return False
        self.health -= 1
        self.iframes = S.PLAYER_IFRAMES
        if self.health <= 0:
            self.health = 0
            self.die()
        else:
            self.hurt(source_x)
        return True

    @property
    def slash_active(self):
        """El arco del tajo hiere solo durante una ventana corta del ataque."""
        if self.action != "attack":
            return False
        t = S.ACTION_TIME["attack"] - self.action_time
        return S.SLASH_WINDOW[0] <= t <= S.SLASH_WINDOW[1]

    @property
    def parry_active(self):
        """La hoja devuelve proyectiles solo durante una ventana corta del desvío."""
        if self.action != "parry":
            return False
        t = S.ACTION_TIME["parry"] - self.action_time
        return S.PARRY_WINDOW[0] <= t <= S.PARRY_WINDOW[1]

    @property
    def parry_zone(self):
        w, h = S.PARRY_ZONE
        x = self.pos.x + self.size[0] if self.facing > 0 else self.pos.x - w
        return (x, self.pos.y + self.size[1] - h, w, h)

    def reflect_projectile(self, shot):
        """Devuelve el proyectil hacia donde se apunta.

        Ley de reflexión: para que v' tenga la dirección apuntada `a` (y el mismo módulo que v), la hoja debe tener
        la normal n = (|v| a - v) / ||...||. Luego se aplica v' = v - 2 (v . n) n y se acelera un 25 %.
        """
        speed = math.hypot(shot.vel.x, shot.vel.y)
        ax, ay = self.parry_aim
        nx, ny = ax * speed - shot.vel.x, ay * speed - shot.vel.y
        length = math.hypot(nx, ny)
        if length < 1e-6:                          # ya viaja hacia donde se apunta: la hoja queda de canto
            nx, ny = -shot.vel.y / speed, shot.vel.x / speed
        else:
            nx, ny = nx / length, ny / length
        shot.reflect(nx, ny)
        self.parry_reflected = True

    @property
    def slash_origin(self):
        return (self.pos.x + self.size[0] / 2, self.pos.y + self.size[1] * S.SLASH_ORIGIN_Y)

    def die(self):
        if not self.dead:
            self.start_action("death")

    def respawn(self, spawn):
        self.size = S.PLAYER_SIZE
        self.crouching = False
        self.action = None
        self.dash_cooldown = 0.0
        self.iframes = S.PLAYER_IFRAMES
        self.pos.update(*spawn)
        self.vel.update(0, 0)

    def _tick_action(self, dt):
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.iframes = max(0.0, self.iframes - dt)
        self.parry_lock = max(0.0, self.parry_lock - dt)
        if self.action == "throw" and not self._thrown and S.ACTION_TIME["throw"] - self.action_time >= S.THROW_RELEASE:
            self._thrown = True
            hx, hy = S.SHURIKEN_HAND
            self.new_projectiles.append(
                Shuriken(self.pos.x + self.size[0] / 2 + self.facing * hx, self.pos.y + self.size[1] + hy, self.facing))
        if self.action and not self.dead:
            self.action_time -= dt
            if self.action_time <= 0:
                if self.action == "parry" and not self.parry_reflected:
                    self.parry_lock = S.PARRY_LOCKOUT      # el desvío no tocó nada: queda inutilizable un rato
                self.action = None

    def _begin_actions(self, inp):
        if self.action is not None:
            return
        if inp.dash_pressed and self.dash_cooldown <= 0:
            self.start_action("dash")
            self.dash_cooldown = S.DASH_COOLDOWN
            self.vel.x = self.facing * S.DASH_SPEED
        elif inp.attack_pressed:
            self.start_action("attack")
        elif inp.parry_pressed and self.parry_lock <= 0:
            self.start_action("parry")
            aim = inp.aim
            if aim and (aim[0] or aim[1]):
                length = math.hypot(*aim)
                self.parry_aim = (aim[0] / length, aim[1] / length)   # solo cambia hacia dónde sale la flecha
            else:
                self.parry_aim = (float(self.facing), 0.0)
        elif inp.throw_pressed:
            self.start_action("throw")

    # ------------------------------------------------------------------ agacharse
    def _resize(self, new_h):
        """Cambia el alto de la hitbox manteniendo fijos los pies."""
        self.pos.y += self.size[1] - new_h
        self.size = (self.size[0], new_h)

    def _can_stand(self, level):
        new_y = self.pos.y + self.size[1] - S.PLAYER_SIZE[1]
        return not any(overlaps(self.pos.x, new_y, self.size[0], S.PLAYER_SIZE[1], r) for r in level.solids)

    def _update_crouch(self, inp, level):
        want = inp.crouch and self.on_ground and self.action is None and not inp.jump_pressed
        if want and not self.crouching:
            self._resize(S.PLAYER_CROUCH_H)
            self.crouching = True
        elif not want and self.crouching and self._can_stand(level):
            self._resize(S.PLAYER_SIZE[1])
            self.crouching = False

    # ------------------------------------------------------------------ actualización
    def update(self, dt, inp, level):
        self._tick_action(dt)
        self._begin_actions(inp)
        self._update_crouch(inp, level)

        # --- Temporizadores de "perdón" para que el salto se sienta consistente ---
        self.coyote = S.COYOTE_TIME if self.on_ground else max(0.0, self.coyote - dt)
        self.jump_buffer = S.JUMP_BUFFER if inp.jump_pressed else max(0.0, self.jump_buffer - dt)

        # --- Horizontal: aceleración / fricción ---
        locked = self.action in ("dash", "hurt", "death")
        if self.action == "dash":
            self.vel.x = self.facing * S.DASH_SPEED          # velocidad constante durante el impulso
        else:
            if self.on_ground:
                accel = S.GROUND_ACCEL * level.grip
                friction = S.GROUND_FRICTION * level.grip
            else:
                accel, friction = S.AIR_ACCEL, S.AIR_DRAG
            if inp.move_x != 0 and not locked:
                mult = S.CROUCH_SPEED_MULT if self.crouching else (S.ACTION_SPEED_MULT if self.action else 1.0)
                self.vel.x = move_toward(self.vel.x, inp.move_x * S.RUN_SPEED * mult, accel * dt)
                if self.action is None:
                    self.facing = inp.move_x
            else:
                self.vel.x = move_toward(self.vel.x, 0.0, friction * dt)

        # --- Salto ---
        can_jump = not locked and not self.crouching
        if can_jump and self.jump_buffer > 0 and self.coyote > 0:
            self.vel.y = -S.JUMP_SPEED
            self.jumping = True
            self.jump_buffer = self.coyote = 0.0
        if self.jumping and not inp.jump_held and self.vel.y < 0:
            self.vel.y *= S.JUMP_CUT       # soltar antes = salto más corto
            self.jumping = False

        # --- Gravedad (el dash es un impulso horizontal sin caída) ---
        if self.action == "dash":
            self.vel.y = 0.0
        else:
            self.vel.y = min(self.vel.y + level.gravity * dt, S.MAX_FALL_SPEED)

        # --- Mover y resolver colisiones ---
        self.on_ground, _, _ = move_and_collide(self.pos, self.vel, self.size, level.solids, dt)
        if self.on_ground:
            self.jumping = False

        # --- Caída al vacío ---
        if self.pos.y > level.height + 300:
            self.respawn(level.spawn)

        # --- Animación (la velocidad del ciclo de carrera sigue a la velocidad real) ---
        if self.animator:
            self.animator.play(self.state, restart=self._restart_anim)
            self._restart_anim = False
            if self.state == "run":
                run_speed = max(0.6, abs(self.vel.x) / S.RUN_SPEED)
            elif self.state == "crouch_walk":      # el paso agachado sigue a la velocidad real (más lenta)
                run_speed = max(0.5, abs(self.vel.x) / (S.RUN_SPEED * S.CROUCH_SPEED_MULT))
            else:
                run_speed = 1.0
            self.animator.update(dt, run_speed)

    # ------------------------------------------------------------------ dibujo
    def draw(self, surface, camera):
        if self.iframes > 0 and not self.dead and int(self.iframes * 20) % 2 == 0:
            return                       # parpadea mientras es invulnerable
        if self.animator is None:
            self._draw_placeholder(surface, camera)
            return
        frame = self.animator.frame
        if self.facing < 0:
            frame = pygame.transform.flip(frame, True, False)
        x = self.pos.x + self.size[0] / 2 - S.SPRITE_FRAME / 2 - camera.x
        y = self.pos.y + self.size[1] - S.SPRITE_FEET_Y - camera.y
        surface.blit(frame, (round(x), round(y)))

    def _draw_placeholder(self, surface, camera):
        """Dibujo provisional con rectángulos, por si faltan los sprites."""
        x = int(self.pos.x - camera.x)
        y = int(self.pos.y - camera.y)
        w, h = self.size
        pygame.draw.rect(surface, S.INK, (x, y, w, h))
        pygame.draw.rect(surface, S.RED, (x, y + 6, w, 6))
