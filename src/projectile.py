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
from physics import overlaps


class Shuriken:
    def __init__(self, x, y, direction):
        self.pos = Vector2(x, y)                                  # centro
        self.vel = Vector2(direction * S.SHURIKEN_SPEED, S.SHURIKEN_LIFT)
        self.angle = 0.0                                          # grados
        self.age = 0.0
        self.alive = True
        self.reflected = False                                    # lo usará el desvío del Ronin

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
