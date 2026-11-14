"""El Ronin: movimiento horizontal con aceleración y fricción, gravedad, salto variable y animación.

Ecuaciones usadas (por frame, con dt en segundos):
  v.x  -> se acerca a (dirección * RUN_SPEED) con aceleración; sin input, frena con fricción
  v.y += g * dt                 (gravedad, con velocidad terminal)
  pos  += v * dt                (en move_and_collide, por ejes y con subpasos)
"""
from dataclasses import dataclass

import pygame
from pygame.math import Vector2

import settings as S
from physics import move_toward, move_and_collide


@dataclass
class InputState:
    """Intención del jugador en este frame (separada del teclado para poder probar la física)."""
    move_x: int = 0              # -1 izquierda, 0 quieto, 1 derecha
    jump_pressed: bool = False   # se pulsó saltar en este frame
    jump_held: bool = False      # el botón de salto sigue presionado


class Player:
    def __init__(self, x, y):
        self.size = S.PLAYER_SIZE
        self.pos = Vector2(x, y)      # esquina superior izquierda
        self.vel = Vector2(0, 0)
        self.on_ground = False
        self.facing = 1
        self.jumping = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.animator = None          # lo asigna Game cuando están cargados los sprites

    @property
    def state(self):
        """Estado para elegir la animación: idle, run, jump o fall."""
        if not self.on_ground:
            return "jump" if self.vel.y < 0 else "fall"
        if abs(self.vel.x) > 20:
            return "run"
        return "idle"

    @property
    def rect(self):
        return (self.pos.x, self.pos.y, self.size[0], self.size[1])

    @property
    def center(self):
        return (self.pos.x + self.size[0] / 2, self.pos.y + self.size[1] / 2)

    def respawn(self, spawn):
        self.pos.update(*spawn)
        self.vel.update(0, 0)

    def update(self, dt, inp, level):
        # --- Temporizadores de "perdón" para que el salto se sienta consistente ---
        self.coyote = S.COYOTE_TIME if self.on_ground else max(0.0, self.coyote - dt)
        self.jump_buffer = S.JUMP_BUFFER if inp.jump_pressed else max(0.0, self.jump_buffer - dt)

        # --- Horizontal: aceleración / fricción ---
        if self.on_ground:
            accel = S.GROUND_ACCEL * level.grip
            friction = S.GROUND_FRICTION * level.grip
        else:
            accel, friction = S.AIR_ACCEL, S.AIR_DRAG
        if inp.move_x != 0:
            self.vel.x = move_toward(self.vel.x, inp.move_x * S.RUN_SPEED, accel * dt)
            self.facing = inp.move_x
        else:
            self.vel.x = move_toward(self.vel.x, 0.0, friction * dt)

        # --- Salto ---
        if self.jump_buffer > 0 and self.coyote > 0:
            self.vel.y = -S.JUMP_SPEED
            self.jumping = True
            self.jump_buffer = self.coyote = 0.0
        if self.jumping and not inp.jump_held and self.vel.y < 0:
            self.vel.y *= S.JUMP_CUT       # soltar antes = salto más corto
            self.jumping = False

        # --- Gravedad ---
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
            self.animator.play(self.state)
            self.animator.update(dt, max(0.6, abs(self.vel.x) / S.RUN_SPEED) if self.state == "run" else 1.0)

    def draw(self, surface, camera):
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
