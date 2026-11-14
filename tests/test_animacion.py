"""Pruebas del sistema de animación y de los estados del Ronin."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from animation import Animation, Animator
from level import Level
from player import Player, InputState

DT = 1 / 60


def jugador_en_suelo():
    nivel = Level(S.LEVELS_DIR / "nivel1.txt")
    p = Player(*nivel.spawn)
    for _ in range(60):
        p.update(DT, InputState(), nivel)
    return nivel, p


class TestAnimator(unittest.TestCase):
    def setUp(self):
        self.anim = Animator({
            "idle": Animation(["i0", "i1"], fps=2, loop=True),
            "jump": Animation(["j0", "j1"], fps=2, loop=False),
        })

    def test_avanza_con_el_tiempo(self):
        self.assertEqual(self.anim.frame, "i0")
        self.anim.update(0.5)
        self.assertEqual(self.anim.frame, "i1")

    def test_cicla(self):
        self.anim.update(1.0)
        self.assertEqual(self.anim.frame, "i0")

    def test_sin_ciclo_se_queda_en_el_ultimo(self):
        self.anim.play("jump")
        self.anim.update(10.0)
        self.assertEqual(self.anim.frame, "j1")

    def test_play_no_reinicia_la_misma_animacion(self):
        self.anim.update(0.5)
        self.anim.play("idle")
        self.assertEqual(self.anim.frame, "i1")

    def test_cambiar_de_animacion_reinicia(self):
        self.anim.update(0.5)
        self.anim.play("jump")
        self.assertEqual(self.anim.frame, "j0")

    def test_velocidad_acelera_la_animacion(self):
        self.anim.update(0.25, speed=2.0)
        self.assertEqual(self.anim.frame, "i1")


class TestEstados(unittest.TestCase):
    def test_idle_en_el_suelo(self):
        _, p = jugador_en_suelo()
        self.assertEqual(p.state, "idle")

    def test_run_al_moverse(self):
        nivel, p = jugador_en_suelo()
        for _ in range(20):
            p.update(DT, InputState(move_x=1), nivel)
        self.assertEqual(p.state, "run")

    def test_jump_y_fall(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(jump_pressed=True, jump_held=True), nivel)
        self.assertEqual(p.state, "jump")
        for _ in range(40):
            p.update(DT, InputState(jump_held=True), nivel)
            if p.vel.y > 0 and not p.on_ground:
                break
        self.assertEqual(p.state, "fall")


if __name__ == "__main__":
    unittest.main()
