"""Pruebas de la física (python -m unittest discover -s tests). Usan pygame.math.Vector2 y pygame.Rect."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from level import Level
from player import Player, InputState

DT = 1 / 60


def nuevo_jugador():
    nivel = Level(S.LEVELS_DIR / "nivel1.txt")
    return nivel, Player(*nivel.spawn)


def simular(jugador, nivel, segundos, **kw):
    for _ in range(int(segundos / DT)):
        jugador.update(DT, InputState(**kw), nivel)


class TestFisica(unittest.TestCase):
    def test_nivel_carga(self):
        nivel = Level(S.LEVELS_DIR / "nivel1.txt")
        self.assertEqual(nivel.width, 80 * S.TILE)
        self.assertEqual(nivel.height, 17 * S.TILE)
        self.assertGreater(len(nivel.solids), 100)

    def test_cae_y_se_apoya_en_el_suelo(self):
        nivel, p = nuevo_jugador()
        simular(p, nivel, 1.0)
        self.assertTrue(p.on_ground)
        self.assertAlmostEqual(p.pos.y + p.size[1], 15 * S.TILE, places=3)

    def test_altura_del_salto(self):
        nivel, p = nuevo_jugador()
        simular(p, nivel, 1.0)
        y0 = p.pos.y
        p.update(DT, InputState(jump_pressed=True, jump_held=True), nivel)
        minimo = p.pos.y
        for _ in range(90):
            p.update(DT, InputState(jump_held=True), nivel)
            minimo = min(minimo, p.pos.y)
        altura = y0 - minimo
        esperada = S.JUMP_SPEED ** 2 / (2 * S.GRAVITY)       # v^2 / 2g
        self.assertAlmostEqual(altura, esperada, delta=12)

    def test_salto_corto_al_soltar(self):
        nivel, p = nuevo_jugador()
        simular(p, nivel, 1.0)
        y0 = p.pos.y
        p.update(DT, InputState(jump_pressed=True, jump_held=True), nivel)
        minimo = p.pos.y
        for _ in range(90):
            p.update(DT, InputState(jump_held=False), nivel)
            minimo = min(minimo, p.pos.y)
        self.assertLess(y0 - minimo, 0.5 * S.JUMP_SPEED ** 2 / (2 * S.GRAVITY))

    def test_velocidad_maxima_y_frenado(self):
        nivel, p = nuevo_jugador()
        simular(p, nivel, 0.5)
        simular(p, nivel, 0.8, move_x=1)
        self.assertAlmostEqual(p.vel.x, S.RUN_SPEED, places=3)
        simular(p, nivel, 0.5)
        self.assertEqual(p.vel.x, 0.0)

    def test_hielo_frena_mas_lento(self):
        nivel, p = nuevo_jugador()
        simular(p, nivel, 0.5)
        simular(p, nivel, 0.5, move_x=1)
        nivel.grip = 0.15
        p.vel.x = S.RUN_SPEED
        simular(p, nivel, 0.2)
        self.assertGreater(p.vel.x, 0.0)          # con hielo todavía se desliza

    def test_no_atraviesa_pared_a_gran_velocidad(self):
        nivel, p = nuevo_jugador()
        p.pos.update(40 * S.TILE, 15 * S.TILE - p.size[1] - 1)
        simular(p, nivel, 0.3)
        for _ in range(30):
            p.vel.x = 3000.0                      # muy por encima de lo normal
            p.update(DT, InputState(move_x=1), nivel)
        self.assertLessEqual(p.pos.x + p.size[0], 45 * S.TILE + 1e-6)   # se detiene en el primer obstáculo (escalón)

    def test_coyote_time(self):
        nivel, p = nuevo_jugador()
        simular(p, nivel, 0.5)
        p.pos.x = 33 * S.TILE - p.size[0] + 4     # justo en el borde del foso
        p.update(DT, InputState(move_x=1), nivel)
        for _ in range(40):
            p.update(DT, InputState(move_x=1), nivel)
            if not p.on_ground:
                break
        self.assertFalse(p.on_ground)
        p.update(DT, InputState(move_x=1, jump_pressed=True, jump_held=True), nivel)
        self.assertLess(p.vel.y, 0)               # saltó aunque ya no estaba en el suelo

    def test_caida_al_foso_reaparece(self):
        nivel, p = nuevo_jugador()
        p.pos.update(35 * S.TILE, 10 * S.TILE)
        simular(p, nivel, 3.0)
        self.assertLess(p.pos.x, 10 * S.TILE)     # volvió al punto de inicio


if __name__ == "__main__":
    unittest.main()
