"""Plataformas móviles. Se mueven en línea recta (ida y vuelta) o en círculo y llevan encima a quien las pisa.

Física que se ve:
  Lineal   (MRU de ida y vuelta, onda triangular):  s(t) = L - | (v t mod 2L) - L |      posición = origen + s * dirección
  Circular (movimiento circular uniforme):          centro + r (cos θ, sin θ)   con θ = θ0 + ω t
                                                    velocidad = ω r (tangente al círculo)
  Sistemas de referencia: quien va encima se mueve con la plataforma (se le suma su desplazamiento) y, si salta,
  conserva su velocidad (momentum): v_salto = v_propia + v_plataforma.
  Empuje: si la plataforma choca con alguien, lo empuja en la dirección en que se mueve; si no cabe (queda
  aplastado entre la plataforma y una pared), recibe daño y queda encima de la plataforma.
"""
import math

import pygame
from pygame.math import Vector2

import settings as S
from physics import move_and_collide, overlaps


class MovingPlatform:
    def __init__(self, x, y, w, h=S.PLATFORM_H, kind="linear", path=(0.0, 0.0), speed=S.PLATFORM_SPEED,
                 radius=0.0, omega=S.PLATFORM_OMEGA, phase=0.0):
        """`x, y`: esquina superior izquierda de partida (lineal) o ESQUINA de la plataforma cuando θ = 0 (circular:
        el centro del círculo se calcula como esa posición menos (radio, 0), así la plataforma parte a la derecha)."""
        self.kind = kind
        self.w, self.h = int(w), int(h)
        self.origin = (float(x), float(y))
        self.path = (float(path[0]), float(path[1]))
        self.length = math.hypot(*self.path)
        self.speed = float(speed)
        self.radius = float(radius)
        self.omega = float(omega)
        self.travel = phase * 2 * self.length
        self.angle = phase * 2 * math.pi
        self.center = (self.origin[0] + self.w / 2 - self.radius, self.origin[1] + self.h / 2)   # solo el circular
        self.rect = pygame.Rect(0, 0, self.w, self.h)
        self.vel = Vector2(0, 0)                          # px/s en el último paso
        self.exact = self._exact_topleft()
        self.rect.topleft = self._topleft()

    # ------------------------------------------------------------------ movimiento
    def _exact_topleft(self):
        """Posición exacta (decimales) de la esquina superior izquierda."""
        if self.kind == "circular":
            cx = self.center[0] + self.radius * math.cos(self.angle)
            cy = self.center[1] + self.radius * math.sin(self.angle)
            return (cx - self.w / 2, cy - self.h / 2)
        if self.length == 0:
            return self.origin
        s = self.length - abs((self.travel % (2 * self.length)) - self.length)
        return (self.origin[0] + self.path[0] * s / self.length,
                self.origin[1] + self.path[1] * s / self.length)

    def _topleft(self):
        x, y = self._exact_topleft()
        return (round(x), round(y))

    @property
    def linear_speed(self):
        """Rapidez de la plataforma: v (lineal) o ω·r (circular), en px/s."""
        return abs(self.omega) * self.radius if self.kind == "circular" else (self.speed if self.length else 0.0)

    def advance(self, dt):
        if self.kind == "circular":
            self.angle = (self.angle + self.omega * dt) % (2 * math.pi)
        else:
            self.travel += self.speed * dt
        old = self.exact
        self.exact = self._exact_topleft()
        if dt > 0:                                        # velocidad exacta (el rect entero daría 60/120 alternados)
            self.vel.update((self.exact[0] - old[0]) / dt, (self.exact[1] - old[1]) / dt)
        self.rect.topleft = self._topleft()

    # ------------------------------------------------------------------ dibujo
    def draw(self, surface, camera, debug=False):
        r = self.rect
        x, y = r.x - camera.x, r.y - camera.y
        sw, sh = surface.get_size()
        if self.kind == "circular":
            c = (round(self.center[0] - camera.x), round(self.center[1] - camera.y))
            pygame.draw.circle(surface, S.GREY, c, round(self.radius), 1)
            pygame.draw.circle(surface, S.GREY, c, 3)
        elif self.length > 0:
            a = (self.origin[0] + self.w / 2 - camera.x, self.origin[1] + self.h / 2 - camera.y)
            b = (a[0] + self.path[0], a[1] + self.path[1])
            pygame.draw.line(surface, S.GREY, a, b, 1)
            for end in (a, b):
                pygame.draw.circle(surface, S.GREY, (round(end[0]), round(end[1])), 3)
        if x + r.w < 0 or x > sw or y + r.h < 0 or y > sh:
            return
        pygame.draw.rect(surface, S.WOOD, (round(x), round(y), r.w, r.h))
        for px in range(16, r.w, 16):                     # junta entre tablas
            pygame.draw.line(surface, S.INK, (round(x + px), round(y)), (round(x + px), round(y + r.h - 1)), 1)
        pygame.draw.rect(surface, S.INK, (round(x), round(y), r.w, r.h), 2)
        if debug:
            pygame.draw.line(surface, S.GREEN, (round(x + r.w / 2), round(y)),
                             (round(x + r.w / 2 + self.vel.x * 0.3), round(y + self.vel.y * 0.3)), 2)


# ---------------------------------------------------------------------- interacción con quienes están cerca
def standing_on(entity, rect):
    """True si `entity` (con pos, size y on_ground) está de pie sobre la plataforma `rect`."""
    w, h = entity.size
    return (entity.on_ground and abs(entity.pos.y + h - rect.top) <= 1
            and entity.pos.x < rect.right and entity.pos.x + w > rect.left)


def _crush(entity, rect):
    """Aplastado entre la plataforma y una pared: recibe daño y se coloca encima de la plataforma."""
    if hasattr(entity, "take_damage"):
        entity.take_damage(rect.centerx)
    elif hasattr(entity, "damage"):
        entity.damage(1, rect.centerx)
    entity.pos.y = rect.top - entity.size[1]


def _push(entity, rect, dx, dy, static, dt):
    """Empuja a `entity` fuera de la plataforma en la dirección en que ésta se movió."""
    w, h = entity.size
    if abs(dx) >= abs(dy):
        need = (rect.right - entity.pos.x) if dx > 0 else (rect.left - w - entity.pos.x)
        move_and_collide(entity.pos, Vector2(need / dt, 0.0), entity.size, static, dt)
    else:
        need = (rect.bottom - entity.pos.y) if dy > 0 else (rect.top - h - entity.pos.y)
        move_and_collide(entity.pos, Vector2(0.0, need / dt), entity.size, static, dt)
    if overlaps(entity.pos.x, entity.pos.y, w, h, rect):
        _crush(entity, rect)


def step(platform, dt, entities, static_solids):
    """Mueve una plataforma un paso: arrastra a los que van encima y empuja a los que estorban."""
    r = platform.rect
    riders = [e for e in entities if standing_on(e, r)]
    others = [e for e in entities if e not in riders]
    old = (r.x, r.y)
    platform.advance(dt)
    dx, dy = r.x - old[0], r.y - old[1]
    vx, vy = (dx / dt, dy / dt) if dt > 0 else (0.0, 0.0)   # desplazamiento real del rect (entero)
    for e in riders:                                      # se mueven con la plataforma (respetando las paredes)
        move_and_collide(e.pos, Vector2(vx, vy), e.size, static_solids, dt)
        e.ride_vel = (platform.vel.x, platform.vel.y)     # velocidad exacta, para el momentum al saltar
    for e in others:
        if overlaps(e.pos.x, e.pos.y, e.size[0], e.size[1], r) and (dx or dy):
            _push(e, r, dx, dy, static_solids, dt)
