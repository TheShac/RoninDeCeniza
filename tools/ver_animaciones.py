"""Galería de animaciones: muestra todas las animaciones en bucle.

Uso:  python tools/ver_animaciones.py          (el Ronin: 6 animaciones por fila)
      python tools/ver_animaciones.py zombi    (todos los zombis: una fila por variante, 5 animaciones por fila)
(Esc para salir)
Sirve para revisar el arte sin tener que jugar. Las animaciones de acción se repiten con una pausa al final.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pygame

import settings as S
from animation import Animator, ENEMY_VARIANTS, load_enemy_animations, load_ronin_animations

ZOOM = 2
LABEL_H = 50
PAUSE = 0.6      # segundos de pausa al terminar una animación que no es cíclica


def cargar(zombi):
    """Devuelve una lista de (título, subtítulo, animación) en el orden en que se dibujan."""
    items = []
    if zombi:
        for kind, variants in ENEMY_VARIANTS.items():
            for variant in variants:
                loaded = load_enemy_animations(kind, variant)
                for name, anim in (loaded or {}).items():
                    items.append((variant, name, anim))
    else:
        for name, anim in (load_ronin_animations() or {}).items():
            items.append(("ronin", name, anim))
    return items


def main():
    zombi = "zombi" in sys.argv[1:]
    cols = 5 if zombi else 6
    pygame.init()
    pygame.display.set_mode((400, 300))          # hace falta una ventana antes de cargar imágenes
    items = cargar(zombi)
    if not items:
        print("No se encontraron los sprites. Genera con: python tools/generar_sprites_ronin.py "
              "o python tools/generar_sprites_zombi.py")
        return
    cell = S.SPRITE_FRAME * ZOOM
    rows = math.ceil(len(items) / cols)
    screen = pygame.display.set_mode((cols * cell, rows * (cell + LABEL_H)))
    pygame.display.set_caption("Ronin de Ceniza - animaciones")
    animators = {(who, name): Animator({name: anim}, start=name) for who, name, anim in items}
    title_font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
        now = pygame.time.get_ticks() / 1000.0
        screen.fill(S.PAPER)
        for i, (who, name, anim) in enumerate(items):
            x, y = (i % cols) * cell, (i // cols) * (cell + LABEL_H)
            animator = animators[(who, name)]
            duration = len(anim.frames) / anim.fps
            animator.time = now if anim.loop else now % (duration + PAUSE)
            ground = y + S.SPRITE_FEET_Y * ZOOM
            pygame.draw.line(screen, S.GREY, (x + 8, ground), (x + cell - 8, ground), 1)
            screen.blit(pygame.transform.scale(animator.frame, (cell, cell)), (x, y))
            title = name if who == "ronin" else f"{who}: {name}"
            screen.blit(title_font.render(title, True, S.INK), (x + 10, y + cell))
            screen.blit(small_font.render(f"{len(anim.frames)} cuadros", True, S.GREY), (x + 10, y + cell + 24))
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
