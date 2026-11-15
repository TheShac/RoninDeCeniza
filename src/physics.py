"""Física reutilizable: movimiento hacia un valor y colisiones AABB.

Para el informe:
- Integración (Euler semiimplícito): v += a*dt ; pos += v*dt
- Colisión AABB (Axis-Aligned Bounding Box): dos rectángulos se solapan si se solapan en X e Y a la vez.
- Resolución por eje: se mueve y se corrige primero en X y luego en Y, así se sabe contra qué lado se chocó.
- Subpasos: el desplazamiento por frame se divide en pasos de a lo más TILE/2 px para no atravesar paredes
  cuando la velocidad es alta (problema típico de "tunneling").
"""
import math

from settings import TILE

MAX_STEP = TILE / 2


def move_toward(value, target, max_delta):
    """Acerca `value` a `target` sin pasarse, avanzando a lo más `max_delta`."""
    if abs(target - value) <= max_delta:
        return target
    return value + math.copysign(max_delta, target - value)


def reflect(vx, vy, nx, ny):
    """Reflexión de un vector: v' = v - 2 (v . n) n, con n unitario (normal de la superficie)."""
    dot = vx * nx + vy * ny
    return vx - 2 * dot * nx, vy - 2 * dot * ny


def overlaps(x, y, w, h, rect):
    """True si la caja (x, y, w, h) se solapa con `rect` (los bordes que solo se tocan no cuentan)."""
    return x < rect.right and x + w > rect.left and y < rect.bottom and y + h > rect.top


def move_and_collide(pos, vel, size, solids, dt):
    """Mueve `pos` según `vel*dt` resolviendo colisiones con `solids`.

    Modifica `pos` y `vel` en el lugar. Devuelve (en_suelo, choco_pared, choco_techo).
    """
    w, h = size
    on_ground = hit_wall = hit_ceiling = False

    # --- Eje X ---
    dx = vel.x * dt
    if dx != 0:
        steps = max(1, math.ceil(abs(dx) / MAX_STEP))
        step = dx / steps
        for _ in range(steps):
            pos.x += step
            collided = False
            for r in solids:
                if overlaps(pos.x, pos.y, w, h, r):
                    pos.x = r.left - w if step > 0 else r.right
                    vel.x = 0.0
                    hit_wall = collided = True
            if collided:
                break

    # --- Eje Y ---
    dy = vel.y * dt
    if dy != 0:
        steps = max(1, math.ceil(abs(dy) / MAX_STEP))
        step = dy / steps
        for _ in range(steps):
            pos.y += step
            collided = False
            for r in solids:
                if overlaps(pos.x, pos.y, w, h, r):
                    if step > 0:
                        pos.y = r.top - h
                        on_ground = True
                    else:
                        pos.y = r.bottom
                        hit_ceiling = True
                    vel.y = 0.0
                    collided = True
            if collided:
                break

    return on_ground, hit_wall, hit_ceiling
