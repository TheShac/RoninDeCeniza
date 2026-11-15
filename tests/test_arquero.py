"""Pruebas de las flechas, el desvío (reflexión de vectores) y el zombi arquero."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pygame

import settings as S
from combat import resolve_combat
from enemy import Archer, Walker
from level import Level
from physics import reflect
from player import Player, InputState
from projectile import Arrow

DT = 1 / 60
SUELO = 15 * S.TILE


def nivel():
    return Level(S.BASE_DIR / "tests" / "niveles" / "pruebas.txt")


def jugador_en(x_pies, lv, facing=1):
    p = Player(x_pies - S.PLAYER_SIZE[0] / 2, SUELO - S.PLAYER_SIZE[1])
    p.facing = facing
    for _ in range(30):
        p.update(DT, InputState(), lv)
    return p


def paso(lv, p, enemigos, flechas, inp=None, fijo=None):
    """Un frame completo: Ronin, combate, enemigos y proyectiles. Devuelve los eventos."""
    p.update(DT, inp or InputState(), lv)
    if fijo is not None:
        p.pos.update(fijo, SUELO - S.PLAYER_SIZE[1])
        p.vel.update(0, 0)
    eventos = resolve_combat(p, enemigos, flechas)
    for e in enemigos:
        e.update(DT, lv, p)
        flechas.extend(e.new_projectiles)
        e.new_projectiles.clear()
    for f in flechas:
        f.update(DT, lv)
    flechas[:] = [f for f in flechas if f.alive]
    return eventos


class TestReflexion(unittest.TestCase):
    def test_pared_vertical_invierte_vx(self):
        self.assertEqual(reflect(-420, 0, 1, 0), (420, 0))

    def test_pared_horizontal_invierte_vy(self):
        vx, vy = reflect(100, 200, 0, -1)
        self.assertEqual((vx, vy), (100, -200))

    def test_normal_a_45_grados(self):
        n = (math.sqrt(0.5), math.sqrt(0.5))
        vx, vy = reflect(-420, 0, *n)
        self.assertAlmostEqual(vx, 0, places=6)
        self.assertAlmostEqual(vy, 420, places=6)

    def test_conserva_el_modulo(self):
        n = (math.cos(0.7), math.sin(0.7))
        vx, vy = reflect(-300, 150, *n)
        self.assertAlmostEqual(math.hypot(vx, vy), math.hypot(-300, 150), places=6)


class TestFlecha(unittest.TestCase):
    def test_vuela_recta_sin_gravedad(self):
        lv = nivel()
        f = Arrow(100, 100, 420, 0)
        for _ in range(30):
            f.update(DT, lv)
        self.assertAlmostEqual(f.vel.y, 0, places=6)
        self.assertAlmostEqual(f.pos.y, 100, places=6)
        self.assertAlmostEqual(f.pos.x, 100 + 420 * 30 * DT, places=3)

    def test_se_clava_en_la_pared(self):
        lv = nivel()
        f = Arrow(40 * S.TILE, SUELO - 40, 420, 0)           # el escalón de las columnas 45-46 está delante
        f.pos.update(44 * S.TILE, SUELO - 20)
        for _ in range(30):
            f.update(DT, lv)
        self.assertFalse(f.alive)

    def test_desaparece_por_tiempo(self):
        lv = nivel()
        f = Arrow(100, 100, 1, 0)
        f.age = S.ARROW_LIFETIME
        f.update(DT, lv)
        self.assertFalse(f.alive)

    def test_hiere_al_ronin_una_vez(self):
        lv = nivel()
        p = jugador_en(300, lv)
        f = Arrow(300 + 100, p.center[1], -420, 0)
        flechas = [f]
        for _ in range(40):
            paso(lv, p, [], flechas)
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 1)
        self.assertFalse(f.alive)

    def test_el_dash_la_atraviesa(self):
        lv = nivel()
        p = jugador_en(300, lv)
        flechas = [Arrow(300 + 60, p.center[1], -420, 0)]
        paso(lv, p, [], flechas, InputState(dash_pressed=True))
        for _ in range(8):
            paso(lv, p, [], flechas)
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH)


class TestDesvio(unittest.TestCase):
    def preparar(self, aim=None, vy=0.0):
        lv = nivel()
        p = jugador_en(300, lv, facing=1)
        flechas = [Arrow(300 + 90, p.center[1], -420, vy)]
        p.update(DT, InputState(parry_pressed=True, aim=aim), lv)
        return lv, p, flechas

    def avanzar_hasta_ventana(self, lv, p):
        while not p.parry_active:
            p.update(DT, InputState(), lv)

    def test_ventana_de_desvio(self):
        lv, p, _ = self.preparar()
        self.assertFalse(p.parry_active)                      # al empezar todavía no
        self.avanzar_hasta_ventana(lv, p)
        self.assertTrue(p.parry_active)
        for _ in range(int(0.3 / DT)):
            p.update(DT, InputState(), lv)
        self.assertFalse(p.parry_active)

    def test_devuelve_la_flecha_hacia_donde_mira_por_defecto(self):
        lv, p, flechas = self.preparar()
        self.avanzar_hasta_ventana(lv, p)
        for _ in range(30):
            paso(lv, p, [], flechas)
            if flechas and flechas[0].friendly:
                break
        f = flechas[0]
        self.assertTrue(f.friendly)
        self.assertGreater(f.vel.x, 0)                        # vuelve hacia el arquero (a la derecha)
        self.assertAlmostEqual(f.vel.length(), 525.0, places=3)        # 420 px/s * 1,25
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH)

    def test_la_direccion_de_salida_es_la_apuntada(self):
        aim = (math.cos(math.radians(-40)), math.sin(math.radians(-40)))      # hacia arriba y adelante
        lv, p, flechas = self.preparar(aim=aim)
        self.avanzar_hasta_ventana(lv, p)
        for _ in range(30):
            paso(lv, p, [], flechas)
            if flechas[0].friendly:
                break
        v = flechas[0].vel
        ang = math.degrees(math.atan2(v.y, v.x))
        self.assertAlmostEqual(ang, -40, delta=0.5)
        self.assertAlmostEqual(v.length(), 525.0, places=3)

    def test_con_la_flecha_inclinada_tambien_cumple_la_ley_de_reflexion(self):
        aim = (1.0, 0.0)
        lv, p, flechas = self.preparar(aim=aim, vy=120.0)     # la flecha baja un poco
        self.avanzar_hasta_ventana(lv, p)
        for _ in range(30):
            paso(lv, p, [], flechas)
            if flechas[0].friendly:
                break
        v = flechas[0].vel
        self.assertAlmostEqual(math.degrees(math.atan2(v.y, v.x)), 0.0, delta=0.5)

    def test_flecha_fuera_de_la_hoja_no_se_devuelve(self):
        lv = nivel()
        p = jugador_en(300, lv, facing=1)
        flechas = [Arrow(300 - 90, p.center[1], 420, 0)]      # viene por la espalda
        p.update(DT, InputState(parry_pressed=True), lv)
        self.avanzar_hasta_ventana(lv, p)
        for _ in range(30):
            paso(lv, p, [], flechas)
        self.assertLess(p.health, S.PLAYER_MAX_HEALTH)

    def test_fuera_de_la_ventana_la_flecha_hiere(self):
        lv = nivel()
        p = jugador_en(300, lv, facing=1)
        flechas = [Arrow(300 + 400, p.center[1], -420, 0)]    # llega cuando el desvío ya terminó
        p.update(DT, InputState(parry_pressed=True), lv)
        for _ in range(60):
            paso(lv, p, [], flechas)
        self.assertLess(p.health, S.PLAYER_MAX_HEALTH)

    def test_desvio_fallido_se_bloquea_y_luego_vuelve(self):
        lv = nivel()
        p = jugador_en(300, lv)
        p.update(DT, InputState(parry_pressed=True), lv)
        for _ in range(int((S.ACTION_TIME["parry"] + 0.05) / DT)):
            p.update(DT, InputState(), lv)
        self.assertIsNone(p.action)
        self.assertGreater(p.parry_lock, 0)
        p.update(DT, InputState(parry_pressed=True), lv)
        self.assertIsNone(p.action)                           # bloqueado
        for _ in range(int(S.PARRY_LOCKOUT / DT) + 2):
            p.update(DT, InputState(), lv)
        p.update(DT, InputState(parry_pressed=True), lv)
        self.assertEqual(p.action, "parry")

    def test_desvio_exitoso_no_se_bloquea(self):
        lv, p, flechas = self.preparar()
        for _ in range(int((S.ACTION_TIME["parry"] + 0.1) / DT)):
            paso(lv, p, [], flechas)
        self.assertEqual(p.parry_lock, 0.0)

    def test_el_mouse_solo_cambia_la_direccion_de_salida_no_gira_al_ronin(self):
        lv = nivel()
        p = jugador_en(300, lv, facing=1)
        p.update(DT, InputState(parry_pressed=True, aim=(-0.6, -0.8)), lv)
        self.assertEqual(p.facing, 1)                         # sigue mirando hacia donde se movía
        self.assertAlmostEqual(p.parry_aim[0], -0.6, places=6)
        self.assertAlmostEqual(p.parry_aim[1], -0.8, places=6)

    def test_flecha_devuelta_mata_al_arquero_y_hiere_a_otros(self):
        lv = nivel()
        p = jugador_en(100, lv)
        a = Archer("cazador", 500, SUELO)
        w = Walker("aldeano", 700, SUELO)
        f1 = Arrow(a.center[0], a.center[1], 0, 0)
        f1.reflect(1, 0)
        f2 = Arrow(w.center[0], w.center[1], 0, 0)
        f2.reflect(1, 0)
        resolve_combat(p, [a, w], [f1, f2])
        self.assertTrue(a.dead)                               # 2 de daño contra 2 de vida
        self.assertTrue(w.dead)

    def test_flecha_devuelta_ya_no_hiere_al_ronin(self):
        lv = nivel()
        p = jugador_en(300, lv)
        f = Arrow(p.center[0], p.center[1], -100, 0)
        f.reflect(1, 0)
        resolve_combat(p, [], [f])
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH)


class TestArquero(unittest.TestCase):
    def escena(self, x_arquero=10 * S.TILE, dx=300, variante="cazador"):
        lv = nivel()
        a = Archer(variante, x_arquero, SUELO)
        p = jugador_en(x_arquero + dx, lv)
        return lv, a, p, [], p.pos.x

    def correr(self, lv, a, p, flechas, fijo, segundos):
        for _ in range(int(segundos / DT)):
            paso(lv, p, [a], flechas, fijo=fijo)

    def test_suelta_la_flecha_a_mitad_del_disparo(self):
        lv, a, p, flechas, fijo = self.escena()
        t = 0.0
        while not flechas and t < 2:
            paso(lv, p, [a], flechas, fijo=fijo)
            t += DT
        self.assertAlmostEqual(t, S.ARCHER_RELEASE, delta=3 * DT)
        self.assertAlmostEqual(flechas[0].vel.length(), S.ARROW_SPEED, places=3)
        self.assertGreater(flechas[0].vel.x, 0)               # el Ronin está a la derecha

    def test_dispara_cada_dos_segundos(self):
        lv, a, p, flechas, fijo = self.escena()
        p.iframes = 100.0                                     # para que las flechas no lo maten
        tiempos, vistas = [], []                              # se guardan las flechas para que no se reutilicen ids
        for i in range(int(6.7 / DT)):
            paso(lv, p, [a], flechas, fijo=fijo)
            for f in flechas:
                if not any(f is v for v in vistas):
                    vistas.append(f)
                    tiempos.append(i * DT)
        self.assertEqual(len(tiempos), 4)
        for a_, b_ in zip(tiempos, tiempos[1:]):
            self.assertAlmostEqual(b_ - a_, S.ARCHER_COOLDOWN, delta=3 * DT)

    def test_no_dispara_si_hay_una_pared_en_medio(self):
        lv, a, p, flechas, fijo = self.escena()
        lv.solids.append(pygame.Rect(int(10 * S.TILE + 150), SUELO - 200, 20, 200))
        estados = set()
        for _ in range(int(3.0 / DT)):
            paso(lv, p, [a], flechas, fijo=fijo)
            estados.add(a.state)
        self.assertNotIn("shoot", estados)                    # ni siquiera apunta
        self.assertEqual(flechas, [])

    def test_no_dispara_si_esta_lejos(self):
        lv, a, p, flechas, fijo = self.escena(dx=600)
        estados = set()
        for _ in range(int(3.0 / DT)):
            paso(lv, p, [a], flechas, fijo=fijo)
            estados.add(a.state)
        self.assertNotIn("shoot", estados)
        self.assertEqual(flechas, [])

    def test_retrocede_si_el_ronin_se_acerca(self):
        lv, a, p, flechas, fijo = self.escena(dx=100)
        x0 = a.pos.x
        self.correr(lv, a, p, flechas, fijo, 0.5)
        self.assertEqual(a.state, "retreat")
        self.assertLess(a.pos.x, x0)                          # se aleja del Ronin
        self.assertEqual(a.facing, 1)                         # sin darle la espalda

    def test_acorralado_en_un_borde_dispara_a_quemarropa(self):
        lv = nivel()
        a = Archer("kyudoka", 33 * S.TILE + 16, SUELO)        # el pozo está justo detrás (columnas 34-37)
        p = jugador_en(33 * S.TILE + 16 - 100, lv)
        flechas = []
        fijo = p.pos.x
        p.iframes = 100.0
        self.correr(lv, a, p, flechas, fijo, 1.5)
        self.assertNotEqual(a.state, "retreat")
        self.assertLessEqual(a.pos.y + a.size[1], SUELO + 1)  # no se cayó
        self.assertTrue(flechas or a.state == "shoot" or a.cooldown > 0)

    def test_tiene_dos_de_vida(self):
        lv, a, p, flechas, fijo = self.escena(dx=100)
        self.assertTrue(a.damage(1, p.center[0]))
        self.assertEqual(a.state, "hurt")
        self.assertFalse(a.dead)
        for _ in range(int(0.5 / DT)):
            a.update(DT, lv, p)
        self.assertNotEqual(a.state, "hurt")                  # se recupera (y vuelve a retroceder o a apuntar)
        a.damage(1, p.center[0])
        self.assertTrue(a.dead)

    def test_herido_antes_de_soltar_no_dispara(self):
        lv, a, p, flechas, fijo = self.escena()
        for _ in range(int(0.3 / DT)):
            paso(lv, p, [a], flechas, fijo=fijo)
        self.assertEqual(a.state, "shoot")
        a.damage(1, p.center[0])
        self.correr(lv, a, p, flechas, fijo, 0.6)
        self.assertEqual(flechas, [])

    def test_no_dispara_a_un_ronin_muerto(self):
        lv, a, p, flechas, fijo = self.escena()
        p.die()
        self.correr(lv, a, p, flechas, fijo, 2.0)
        self.assertEqual(flechas, [])

    def test_el_tajo_y_el_shuriken_tambien_lo_hieren(self):
        from projectile import Shuriken
        lv, a, p, flechas, fijo = self.escena(dx=100)
        shot = Shuriken(a.center[0], a.center[1], 1)
        resolve_combat(p, [a], [shot])
        self.assertEqual(a.health, S.ARCHER_HEALTH - 1)


if __name__ == "__main__":
    unittest.main()
