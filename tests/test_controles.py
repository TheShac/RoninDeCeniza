"""Pruebas de los controles: dirección del desvío, ataques en movimiento y dirección del tajo."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from combat import resolve_combat
from controls import jump_pressed, keyboard_aim, mouse_aim
from enemy import Walker
from level import Level
from player import Player, InputState
from projectile import Arrow

DT = 1 / 60
SUELO = 15 * S.TILE


def nuevo():
    lv = Level(S.LEVELS_DIR / "nivel1.txt")
    p = Player(300, SUELO - S.PLAYER_SIZE[1])
    for _ in range(30):
        p.update(DT, InputState(), lv)
    return lv, p


def angulo(v):
    return math.degrees(math.atan2(v[1], v[0]))


class TestDireccionConTeclado(unittest.TestCase):
    def test_sin_teclas_no_hay_direccion(self):
        self.assertIsNone(keyboard_aim(0, False, False))

    def test_ocho_direcciones(self):
        casos = {
            (1, False, False): 0, (1, False, True): 45, (0, False, True): 90, (-1, False, True): 135,
            (-1, False, False): 180, (-1, True, False): -135, (0, True, False): -90, (1, True, False): -45,
        }
        for (mx, up, down), esperado in casos.items():
            a = keyboard_aim(mx, up, down)
            self.assertAlmostEqual(math.hypot(*a), 1.0, places=9)
            diff = (angulo(a) - esperado + 180) % 360 - 180
            self.assertAlmostEqual(diff, 0, places=6, msg=f"{(mx, up, down)}")

    def test_arriba_y_abajo_juntas_se_anulan(self):
        self.assertIsNone(keyboard_aim(0, True, True))

    def test_mouse_apunta_al_cursor(self):
        a = mouse_aim((100, 100), (100, 40))
        self.assertAlmostEqual(a[0], 0, places=9)
        self.assertAlmostEqual(a[1], -1, places=9)
        self.assertIsNone(mouse_aim((5, 5), (5, 5)))

    def test_w_con_k_no_salta_pero_sola_si(self):
        self.assertTrue(jump_pressed({"up"}))
        self.assertFalse(jump_pressed({"up", "parry"}))
        self.assertTrue(jump_pressed({"jump", "parry"}))      # Espacio siempre salta


class TestDesvioConTeclado(unittest.TestCase):
    def devolver(self, aim):
        lv, p = nuevo()
        p.facing = 1
        flechas = [Arrow(300 + 90, p.center[1], -420, 0)]
        p.update(DT, InputState(parry_pressed=True, aim=aim, move_x=0), lv)
        for _ in range(40):
            p.update(DT, InputState(), lv)
            resolve_combat(p, [], flechas)
            if flechas[0].friendly:
                break
            flechas[0].update(DT, lv)
        self.assertTrue(flechas[0].friendly)
        return p, flechas[0].vel

    def test_sin_direccion_vuelve_hacia_donde_mira(self):
        _, v = self.devolver(None)
        self.assertAlmostEqual(angulo((v.x, v.y)), 0, delta=0.5)

    def test_las_direcciones_cambian_hacia_donde_sale(self):
        for mx, up, down, esperado in ((1, True, False, -45), (0, True, False, -90), (1, False, True, 45)):
            _, v = self.devolver(keyboard_aim(mx, up, down))
            self.assertAlmostEqual(angulo((v.x, v.y)), esperado, delta=0.5, msg=f"{(mx, up, down)}")
            self.assertAlmostEqual(math.hypot(v.x, v.y), 525.0, places=3)

    def test_el_desvio_con_direccion_no_gira_al_ronin(self):
        p, _ = self.devolver(keyboard_aim(-1, False, False))   # apunta a la izquierda, pero él mira a la derecha
        self.assertEqual(p.facing, 1)


class TestElTajoSigueHaciaDondeMira(unittest.TestCase):
    def test_el_tajo_ignora_el_aim_y_golpea_al_frente(self):
        lv, p = nuevo()
        p.facing = 1
        delante = Walker("aldeano", 300 + 12 + 45, SUELO)
        detras = Walker("aldeano", 300 + 12 - 45, SUELO)
        p.update(DT, InputState(attack_pressed=True, aim=(-1.0, 0.0)), lv)   # aunque el "mouse" apunte a la izquierda
        for _ in range(int(0.3 / DT)):
            p.update(DT, InputState(), lv)
            resolve_combat(p, [delante, detras], [])
        self.assertTrue(delante.dead)
        self.assertFalse(detras.dead)
        self.assertEqual(p.facing, 1)

    def test_el_tajo_mirando_a_la_izquierda_golpea_a_la_izquierda(self):
        lv, p = nuevo()
        p.facing = -1
        delante = Walker("aldeano", 300 + 12 - 45, SUELO)
        detras = Walker("aldeano", 300 + 12 + 45, SUELO)
        p.update(DT, InputState(attack_pressed=True), lv)
        for _ in range(int(0.3 / DT)):
            p.update(DT, InputState(), lv)
            resolve_combat(p, [delante, detras], [])
        self.assertTrue(delante.dead)
        self.assertFalse(detras.dead)

    def test_el_shuriken_sale_hacia_donde_mira(self):
        lv, p = nuevo()
        p.facing = -1
        p.update(DT, InputState(throw_pressed=True, aim=(1.0, 0.0)), lv)
        for _ in range(int(0.3 / DT)):
            p.update(DT, InputState(), lv)
        self.assertLess(p.new_projectiles[0].vel.x, 0)


class TestAccionesEnMovimiento(unittest.TestCase):
    """J, E y K funcionan mientras se camina, se salta, se cae o se va agachado."""

    def situaciones(self):
        def correr(lv, p):
            for _ in range(30):
                p.update(DT, InputState(move_x=1), lv)
            return dict(move_x=1)

        def agachado(lv, p):
            for _ in range(30):
                p.update(DT, InputState(move_x=1, crouch=True), lv)
            return dict(move_x=1, crouch=True)

        def saltando(lv, p):
            p.update(DT, InputState(move_x=1, jump_pressed=True, jump_held=True), lv)
            for _ in range(5):
                p.update(DT, InputState(move_x=1, jump_held=True), lv)
            return dict(move_x=1, jump_held=True)

        def cayendo(lv, p):
            saltando(lv, p)
            for _ in range(40):
                p.update(DT, InputState(move_x=1), lv)
            return dict(move_x=1)

        return {"corriendo": correr, "agachado": agachado, "saltando": saltando, "cayendo": cayendo}

    def test_todas_las_acciones_en_todas_las_situaciones(self):
        for nombre, preparar in self.situaciones().items():
            for tecla, accion in (("attack_pressed", "attack"), ("throw_pressed", "throw"), ("parry_pressed", "parry")):
                lv, p = nuevo()
                mantener = preparar(lv, p)
                p.update(DT, InputState(**mantener, **{tecla: True}), lv)
                self.assertEqual(p.action, accion, msg=f"{nombre} + {tecla}")

    def test_sigue_avanzando_mientras_ataca(self):
        for tecla in ("attack_pressed", "throw_pressed", "parry_pressed"):
            lv, p = nuevo()
            for _ in range(30):
                p.update(DT, InputState(move_x=1), lv)
            x0 = p.pos.x
            p.update(DT, InputState(move_x=1, **{tecla: True}), lv)
            for _ in range(12):
                p.update(DT, InputState(move_x=1), lv)
            self.assertGreater(p.pos.x - x0, 20, msg=tecla)


if __name__ == "__main__":
    unittest.main()
