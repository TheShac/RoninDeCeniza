"""Galería de animaciones: muestra todas las animaciones en bucle, con scroll si no caben en la pantalla.

Uso:  python tools/ver_animaciones.py          (el Ronin: 6 animaciones por fila)
      python tools/ver_animaciones.py zombi    (todos los zombis: una fila por variante)
Controles: rueda del mouse, flechas arriba/abajo, RePág/AvPág, Inicio/Fin para desplazarse; Esc para salir.
La ventana nunca supera el tamaño de tu pantalla (se achican los cuadros si hace falta) y se puede cambiar de tamaño.
Sirve para revisar el arte sin tener que jugar. Las animaciones de acción se repiten con una pausa al final.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pygame

import settings as S
from animation import Animator, ENEMY_VARIANTS, load_enemy_animations, load_ronin_animations

MAX_ZOOM = 2.0
LABEL_H = 50
PAUSE = 0.6            # segundos de pausa al terminar una animación que no es cíclica
RONIN_COLS = 6
MARGIN = (40, 120)     # px que se dejan libres de la pantalla (barras de título y de tareas)
WHEEL_STEP = 60
ARROW_STEP = 40


def cargar(zombi):
    """Devuelve las filas de la galería: lista de filas, cada una una lista de (quién, nombre, animación).

    Zombis: una fila por variante (aldeano, samurai, ...). Ronin: filas de RONIN_COLS animaciones."""
    if zombi:
        rows = []
        for kind, variants in ENEMY_VARIANTS.items():
            for variant in variants:
                loaded = load_enemy_animations(kind, variant)
                if loaded:
                    rows.append([(variant, name, anim) for name, anim in loaded.items()])
        return rows
    items = [("ronin", name, anim) for name, anim in (load_ronin_animations() or {}).items()]
    return [items[i:i + RONIN_COLS] for i in range(0, len(items), RONIN_COLS)]


def medidas(rows, desktop):
    """Calcula el zoom, el tamaño de cada celda y el tamaño inicial de la ventana.

    El zoom baja de MAX_ZOOM si las columnas no caben a lo ancho de la pantalla; el alto de la ventana se
    recorta al de la pantalla (lo que no cabe se ve con scroll)."""
    base_w = max(a.frames[0].get_width() for row in rows for _, _, a in row)
    base_h = max(a.frames[0].get_height() for row in rows for _, _, a in row)
    cols = max(len(row) for row in rows)
    zoom = min(MAX_ZOOM, (desktop[0] - MARGIN[0]) / (cols * base_w))
    cell_w, cell_h = int(base_w * zoom), int(base_h * zoom)
    content_h = len(rows) * (cell_h + LABEL_H)
    win_w = cols * cell_w
    win_h = max(200, min(content_h, desktop[1] - MARGIN[1]))
    return dict(zoom=zoom, cell_w=cell_w, cell_h=cell_h, cols=cols, content_h=content_h, win=(win_w, win_h))


def clamp_scroll(scroll, content_h, view_h):
    """Mantiene el desplazamiento entre 0 y lo que sobra de contenido por debajo de la ventana."""
    return max(0, min(scroll, max(0, content_h - view_h)))


def main():
    zombi = "zombi" in sys.argv[1:]
    pygame.init()
    pygame.display.set_mode((400, 300))          # hace falta una ventana antes de cargar imágenes
    rows = cargar(zombi)
    if not rows:
        print("No se encontraron los sprites. Genera con: python tools/generar_sprites_ronin.py "
              "o python tools/generar_sprites_zombi.py")
        return
    try:
        desktop = pygame.display.get_desktop_sizes()[0]
    except (AttributeError, IndexError, pygame.error):
        desktop = (1280, 720)
    m = medidas(rows, desktop)
    screen = pygame.display.set_mode(m["win"], pygame.RESIZABLE)
    pygame.display.set_caption("Ronin de Ceniza - animaciones (rueda o flechas para desplazarse)")
    pygame.key.set_repeat(250, 30)
    animators = {(who, name): Animator({name: anim}, start=name) for row in rows for who, name, anim in row}
    title_font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()
    cache = {}
    scroll = 0
    zoom, cell_w, cell_h = m["zoom"], m["cell_w"], m["cell_h"]
    row_h = cell_h + LABEL_H

    running = True
    while running:
        view_w, view_h = screen.get_size()
        page = max(60, view_h - 60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                scroll -= event.y * WHEEL_STEP
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_DOWN:
                    scroll += ARROW_STEP
                elif event.key == pygame.K_UP:
                    scroll -= ARROW_STEP
                elif event.key == pygame.K_PAGEDOWN:
                    scroll += page
                elif event.key == pygame.K_PAGEUP:
                    scroll -= page
                elif event.key == pygame.K_HOME:
                    scroll = 0
                elif event.key == pygame.K_END:
                    scroll = m["content_h"]
        scroll = clamp_scroll(scroll, m["content_h"], view_h)

        now = pygame.time.get_ticks() / 1000.0
        screen.fill(S.PAPER)
        for r, row in enumerate(rows):
            y = r * row_h - scroll
            if y + row_h < 0 or y > view_h:
                continue                                     # fila fuera de la ventana
            for c, (who, name, anim) in enumerate(row):
                x = c * cell_w
                animator = animators[(who, name)]
                duration = len(anim.frames) / anim.fps
                animator.time = now if anim.loop else now % (duration + PAUSE)
                frame = animator.frame
                fw, fh = frame.get_size()
                feet = S.BLOATER_FEET_Y if (fw, fh) == S.BLOATER_FRAME else S.SPRITE_FEET_Y
                size = (int(fw * zoom), int(fh * zoom))
                top = y + cell_h - size[1]
                ground = top + feet * zoom
                pygame.draw.line(screen, S.GREY, (x + 8, ground), (x + cell_w - 8, ground), 1)
                key = (id(frame), size)
                if key not in cache:
                    cache[key] = pygame.transform.smoothscale(frame, size)
                screen.blit(cache[key], (x + (cell_w - size[0]) // 2, top))
                title = name if who == "ronin" else f"{who}: {name}"
                screen.blit(title_font.render(title, True, S.INK), (x + 10, y + cell_h))
                screen.blit(small_font.render(f"{len(anim.frames)} cuadros", True, S.GREY), (x + 10, y + cell_h + 24))
        if m["content_h"] > view_h:                          # barra de scroll
            bar_h = max(30, view_h * view_h // m["content_h"])
            bar_y = (view_h - bar_h) * scroll // max(1, m["content_h"] - view_h)
            pygame.draw.rect(screen, S.GREY, (view_w - 8, bar_y, 6, bar_h), border_radius=3)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
