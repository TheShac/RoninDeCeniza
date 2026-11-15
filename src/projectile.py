"""Shuriken: proyectil con tiro parabólico y rotación.

Física (por frame, con dt en segundos):
  v.y += SHURIKEN_GRAVITY * dt        (cae poco: el shuriken es liviano)
  pos += v * dt                        (movimiento parabólico, mismo integrador que el jugador)
  ángulo += SHURIKEN_SPIN * dt         (movimiento rotacional: 720 grados por segundo)
La colisión usa el mismo choque rectángulo-contra-mapa (AABB) que el resto del juego.
"""
import math

import pygame
from pygame.math import Vector2

import settings as S
from physics import overlaps, reflect


class Shuriken:
    def __init__(self, x, y, direction):
        self.pos = Vector2(x, y)                                  # centro
        self.vel = Vector2(direction * S.SHURIKEN_SPEED, S.SHURIKEN_LIFT)
        self.angle = 0.0                                          # grados
        self.age = 0.0
        self.alive = True
        self.friendly = True          # daña a los enemigos (las flechas enemigas dañan al Ronin)
        self.damage = 1
        self.reflectable = False

    @property
    def rect(self):
        r = S.SHURIKEN_RADIUS
        return (self.pos.x - r, self.pos.y - r, 2 * r, 2 * r)

    def update(self, dt, level):
        if not self.alive:
            return
        self.age += dt
        self.vel.y += S.SHURIKEN_GRAVITY * dt
        self.pos += self.vel * dt
        self.angle = (self.angle + S.SHURIKEN_SPIN * dt) % 360.0
        x, y, w, h = self.rect
        if self.age > S.SHURIKEN_LIFETIME or self.pos.y > level.height + 100 or not (-100 < self.pos.x < level.width + 100):
            self.alive = False
        elif any(overlaps(x, y, w, h, r) for r in level.solids):
            self.alive = False                                    # se clava en la pared o el suelo

    def points(self, camera):
        """Estrella de 4 puntas: se rota cada vértice con (x cos a - y sin a, x sin a + y cos a)."""
        a = math.radians(self.angle)
        cos_a, sin_a = math.cos(a), math.sin(a)
        r, inner = S.SHURIKEN_RADIUS, S.SHURIKEN_RADIUS * 0.35
        pts = []
        for k in range(8):
            rad = r if k % 2 == 0 else inner
            t = k * math.pi / 4
            px, py = rad * math.cos(t), rad * math.sin(t)
            pts.append((self.pos.x - camera.x + px * cos_a - py * sin_a,
                        self.pos.y - camera.y + px * sin_a + py * cos_a))
        return pts

    def draw(self, surface, camera):
        pts = self.points(camera)
        pygame.draw.polygon(surface, S.INK, pts)
        pygame.draw.circle(surface, S.PAPER, (round(self.pos.x - camera.x), round(self.pos.y - camera.y)), 2)


class Arrow:
    """Flecha: vuela en línea recta (sin gravedad) y se puede devolver con el desvío del Ronin.

    Desvío: v' = v - 2 (v . n) n, con la normal n de la hoja, y luego se multiplica por 1,25.
    Una flecha devuelta deja de herir al Ronin y hiere a los enemigos que toque.
    """

    def __init__(self, x, y, vx, vy):
        self.pos = Vector2(x, y)                                  # punta de la flecha
        self.vel = Vector2(vx, vy)
        self.age = 0.0
        self.alive = True
        self.friendly = False         # al nacer hiere al Ronin
        self.damage = 1
        self.reflectable = True
        self.reflected = False

    @property
    def rect(self):
        return (self.pos.x - 6, self.pos.y - 3, 12, 6)

    def reflect(self, nx, ny):
        """Devuelve la flecha: refleja la velocidad con la normal (nx, ny) y la acelera un 25 %."""
        vx, vy = reflect(self.vel.x, self.vel.y, nx, ny)
        self.vel.update(vx * S.PARRY_SPEED_BONUS, vy * S.PARRY_SPEED_BONUS)
        self.friendly = True
        self.reflectable = False
        self.reflected = True
        self.damage = S.REFLECTED_ARROW_DAMAGE
        self.age = 0.0

    def update(self, dt, level):
        if not self.alive:
            return
        self.age += dt
        self.pos += self.vel * dt
        if self.age > S.ARROW_LIFETIME or not (-100 < self.pos.x < level.width + 100) \
                or not (-300 < self.pos.y < level.height + 300):
            self.alive = False
        elif any(overlaps(self.pos.x, self.pos.y, 1, 1, r) for r in level.solids):
            self.alive = False                                    # se clava en el mapa

    def draw(self, surface, camera):
        speed = self.vel.length()
        if speed == 0:
            return
        dx, dy = self.vel.x / speed, self.vel.y / speed           # dirección de vuelo: la flecha apunta hacia donde va
        tip = (self.pos.x - camera.x, self.pos.y - camera.y)
        tail = (tip[0] - dx * 22, tip[1] - dy * 22)
        color = S.RED if self.reflected else S.INK
        pygame.draw.line(surface, color, tail, tip, 2)
        px, py = -dy, dx                                          # perpendicular, para la punta y las plumas
        pygame.draw.polygon(surface, S.GREY if not self.reflected else S.RED,
                            [(tip[0] + dx * 5, tip[1] + dy * 5), (tip[0] - dx * 3 + px * 3, tip[1] - dy * 3 + py * 3),
                             (tip[0] - dx * 3 - px * 3, tip[1] - dy * 3 - py * 3)])
        for sign in (-1, 1):
            pygame.draw.line(surface, S.RED, (tail[0] + dx * 4, tail[1] + dy * 4),
                             (tail[0] - dx * 2 + px * 3 * sign, tail[1] - dy * 2 + py * 3 * sign), 1)
