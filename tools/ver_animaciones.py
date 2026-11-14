"""Galería de animaciones del Ronin: muestra todas las animaciones en bucle.

Uso:  python tools/ver_animaciones.py      (Esc para salir)
Sirve para revisar el arte sin tener que jugar. Cada animación de acción se repite con una pausa al final.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pygame

import settings as S
from animation import Animator, RONIN_ANIMATIONS, load_ronin_animations

ZOOM = 2
COLS = 6
LABEL_H = 28
PAUSE = 0.6      # segundos de pausa al terminar una animación que no es cíclica


def main():
    pygame.init()
    cell = S.SPRITE_FRAME * ZOOM
    rows = math.ceil(len(RONIN_ANIMATIONS) / COLS)
    screen = pygame.display.set_mode((COLS * cell, rows * (cell + LABEL_H)))
    pygame.display.set_caption("Ronin de Ceniza - animaciones")
    animations = load_ronin_animations()
    if animations is None:
        print("No se encontraron los sprites. Ejecuta primero: python tools/generar_sprites_ronin.py")
        return
    animators = {name: Animator({name: anim}, start=name) for name, anim in animations.items()}
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
        now = pygame.time.get_ticks() / 1000.0
        screen.fill(S.PAPER)
        for i, (name, anim) in enumerate(animations.items()):
            x, y = (i % COLS) * cell, (i // COLS) * (cell + LABEL_H)
            animator = animators[name]
            duration = len(anim.frames) / anim.fps
            animator.time = now if anim.loop else now % (duration + PAUSE)
            ground = y + S.SPRITE_FEET_Y * ZOOM
            pygame.draw.line(screen, S.GREY, (x + 8, ground), (x + cell - 8, ground), 1)
            screen.blit(pygame.transform.scale(animator.frame, (cell, cell)), (x, y))
            label = f"{name} ({len(anim.frames)} cuadros)"
            screen.blit(font.render(label, True, S.INK), (x + 8, y + cell))
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
