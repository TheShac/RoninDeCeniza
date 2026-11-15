"""Reglas de combate: quién golpea a quién.

Tajo del Ronin: un sector circular delante de él (álgebra de vectores).
  Sea v el vector desde el hombro del Ronin hasta el punto del enemigo más cercano, y f = (facing, 0).
  Hay golpe si  |v| <= alcance   y   v . f >= |v| * cos(arco / 2)     (producto punto = ángulo entre vectores)
"""
import math

import settings as S


def rects_overlap(a, b):
    """Solape de dos cajas (x, y, w, h)."""
    return a[0] < b[0] + b[2] and a[0] + a[2] > b[0] and a[1] < b[1] + b[3] and a[1] + a[3] > b[1]


def slash_hits_rect(origin, facing, rect, reach=S.SLASH_REACH, arc=S.SLASH_ARC):
    """True si la caja `rect` (x, y, w, h) está dentro del sector del tajo."""
    rx, ry, rw, rh = rect
    nx = min(max(origin[0], rx), rx + rw)          # punto de la caja más cercano al origen
    ny = min(max(origin[1], ry), ry + rh)
    vx, vy = nx - origin[0], ny - origin[1]
    dist2 = vx * vx + vy * vy
    if dist2 > reach * reach:
        return False
    if dist2 == 0:
        return True                                # el origen está dentro de la caja
    return vx * facing >= math.sqrt(dist2) * math.cos(math.radians(arc / 2))


def blast_push(center, target, radius=S.BLAST_RADIUS, strength=S.BLAST_IMPULSE, lift=S.BLAST_LIFT):
    """Impulso radial de una explosión sobre un punto. Devuelve (vx, vy, falloff) o None si está fuera.

    Sea d = target - center (vector) y r = |d|. Dentro del radio:
      falloff = 1 - r / radius                      (1 en el centro, 0 en el borde)
      n = normalizar(d + (0, -lift * r))            (dirección radial con un empujón hacia arriba)
      delta_v = strength * falloff * n
    Es un impulso: cambia la velocidad de golpe, y después la fricción y la gravedad hacen el resto."""
    dx, dy = target[0] - center[0], target[1] - center[1]
    dist = math.hypot(dx, dy)
    if dist > radius:
        return None
    falloff = 1.0 - dist / radius
    if dist < 1e-6:
        nx, ny = 0.0, -1.0
    else:
        nx, ny = dx / dist, dy / dist - lift
        length = math.hypot(nx, ny)
        nx, ny = nx / length, ny / length
    return nx * strength * falloff, ny * strength * falloff, falloff


def apply_blast(blast, player, enemies):
    """Aplica una explosión {x, y, radius} al Ronin y a los zombis (menos el que explota: no está en `enemies`).

    Cada uno dentro del radio recibe daño (si puede) y el impulso radial de `blast_push`.
    El impulso se aplica aunque el Ronin sea invulnerable (el dash esquiva el daño, no la onda de choque)."""
    center = (blast["x"], blast["y"])
    radius = blast.get("radius", S.BLAST_RADIUS)
    if not player.dead:
        push = blast_push(center, player.center, radius)
        if push:
            player.take_damage(center[0], S.BLAST_PLAYER_DAMAGE)
            player.vel.x += push[0]
            player.vel.y += push[1]
    for enemy in enemies:
        if enemy.dead or not enemy.can_be_hit:
            continue
        push = blast_push(center, enemy.center, radius)
        if push:
            enemy.damage(S.BLAST_ENEMY_DAMAGE, center[0])
            enemy.vel.x += push[0]
            enemy.vel.y += push[1]


def resolve_combat(player, enemies, projectiles):
    """Aplica el combate de este frame y devuelve los eventos visuales [(tipo, (x, y))].

    - Tajo del Ronin: hiere a cada enemigo del arco una sola vez.
    - Proyectiles amistosos (shuriken, flechas devueltas): hieren al primer enemigo que tocan.
    - Proyectiles hostiles (flechas): el desvío los devuelve si están dentro de la hoja; si no, hieren al Ronin
      (salvo que sea invulnerable, p. ej. durante el dash: entonces lo atraviesan).
    """
    events = []
    if player.slash_active:
        for enemy in enemies:
            if enemy.can_be_hit and id(enemy) not in player.slash_hits \
                    and slash_hits_rect(player.slash_origin, player.facing, enemy.rect):
                player.slash_hits.add(id(enemy))
                enemy.damage(1, player.center[0])
    for shot in projectiles:
        if not shot.alive:
            continue
        if shot.friendly:
            for enemy in enemies:
                if enemy.can_be_hit and rects_overlap(shot.rect, enemy.rect):
                    enemy.damage(shot.damage, shot.pos.x)
                    shot.alive = False
                    break
        elif shot.reflectable and player.parry_active and rects_overlap(shot.rect, player.parry_zone):
            player.reflect_projectile(shot)
            events.append(("spark", (shot.pos.x, shot.pos.y)))
        elif rects_overlap(shot.rect, player.rect):
            if player.take_damage(shot.pos.x):
                shot.alive = False
    return events
