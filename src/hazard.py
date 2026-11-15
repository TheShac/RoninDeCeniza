"""Peligros del escenario. Por ahora: la sierra giratoria (Saw).

Física que se ve en la sierra:
  Movimiento rotacional:  theta = theta + omega * dt        (omega en rad/s; se mantiene entre 0 y 2*pi)
                          velocidad tangencial de un diente:  v = omega * r
  Movimiento en el riel (MRU de ida y vuelta, onda triangular):
                          s(t) = L - | (v * t mod 2L) - L |   con L = largo del riel
  Colisión círculo contra caja: se toma el punto de la caja más cercano al centro (clamp) y hay golpe si
                          distancia^2 <= (radio * SAW_HIT_SCALE)^2   (la caja de golpe es un poco más chica que el dibujo)
"""
import math

import pygame

import settings as S


class Saw:
    def __init__(self, cx, cy, radius=S.SAW_RADIUS, path=(0.0, 0.0), speed=S.SAW_PATH_SPEED, omega=S.SAW_OMEGA, phase=0.0):
        self.origin = (float(cx), float(cy))
        self.radius = float(radius)
        self.path = (float(path[0]), float(path[1]))          # desplazamiento total del riel en px (dx, dy)
        self.length = math.hypot(*self.path)
        self.speed = float(speed)
        self.omega = float(omega)
        self.angle = 0.0
        self.travel = phase * 2 * self.length                 # distancia recorrida (la onda triangular sale de aquí)
        self.pos = self._position()

    # ------------------------------------------------------------------ física
    def _position(self):
        if self.length == 0:
            return pygame.math.Vector2(*self.origin)
        s = self.length - abs((self.travel % (2 * self.length)) - self.length)     # 0 -> L -> 0 -> L ...
        return pygame.math.Vector2(self.origin[0] + self.path[0] * s / self.length,
                                   self.origin[1] + self.path[1] * s / self.length)

    @property
    def tangential_speed(self):
        """Velocidad lineal de la punta de un diente: v = omega * r (px/s)."""
        return abs(self.omega) * self.radius

    @property
    def hit_radius(self):
        return self.radius * S.SAW_HIT_SCALE

    def update(self, dt):
        self.angle = (self.angle + self.omega * dt) % (2 * math.pi)
        if self.length > 0:
            self.travel += self.speed * dt
            self.pos = self._position()

    def hits_rect(self, rect):
        """True si el círculo de golpe toca la caja (x, y, w, h)."""
        x, y, w, h = rect
        nx = min(max(self.pos.x, x), x + w)                   # punto de la caja más cercano al centro
        ny = min(max(self.pos.y, y), y + h)
        dx, dy = self.pos.x - nx, self.pos.y - ny
        return dx * dx + dy * dy <= self.hit_radius ** 2

    def contact_point(self, rect):
        x, y, w, h = rect
        return (min(max(self.pos.x, x), x + w), min(max(self.pos.y, y), y + h))

    # ------------------------------------------------------------------ dibujo
    def blade_points(self):
        """Contorno del disco: dientes de sierra (raíz -> punta inclinada -> raíz siguiente)."""
        n = S.SAW_TEETH
        step = 2 * math.pi / n
        pts = []
        for k in range(n):
            a = self.angle + k * step
            pts.append((self.pos.x + self.radius * 0.78 * math.cos(a), self.pos.y + self.radius * 0.78 * math.sin(a)))
            b = a + step * 0.8
            pts.append((self.pos.x + self.radius * math.cos(b), self.pos.y + self.radius * math.sin(b)))
        return pts

    def draw(self, surface, camera, debug=False):
        cx, cy = self.pos.x - camera.x, self.pos.y - camera.y
        sw, sh = surface.get_size()
        if cx + self.radius < 0 or cx - self.radius > sw or cy + self.radius < 0 or cy - self.radius > sh:
            return
        if self.length > 0:                                   # riel por el que va y viene
            a = (self.origin[0] - camera.x, self.origin[1] - camera.y)
            b = (self.origin[0] + self.path[0] - camera.x, self.origin[1] + self.path[1] - camera.y)
            pygame.draw.line(surface, S.GREY, a, b, 2)
            for end in (a, b):
                pygame.draw.circle(surface, S.GREY, (round(end[0]), round(end[1])), 4)
        pts = [(x - camera.x, y - camera.y) for x, y in self.blade_points()]
        pygame.draw.polygon(surface, S.STEEL, pts)
        pygame.draw.polygon(surface, S.INK, pts, 2)
        for k in range(3):                                    # tres agujeros que giran con el disco
            a = self.angle * 1.0 + k * 2 * math.pi / 3
            pygame.draw.circle(surface, S.PAPER, (round(cx + self.radius * 0.42 * math.cos(a)),
                                                  round(cy + self.radius * 0.42 * math.sin(a))), round(self.radius * 0.13))
        pygame.draw.circle(surface, S.INK, (round(cx), round(cy)), round(self.radius * 0.18))
        pygame.draw.circle(surface, S.RED, (round(cx + self.radius * 0.55 * math.cos(self.angle + 0.5)),
                                            round(cy + self.radius * 0.55 * math.sin(self.angle + 0.5))), 3)   # sangre
        if debug:
            pygame.draw.circle(surface, S.RED, (round(cx), round(cy)), round(self.hit_radius), 1)
