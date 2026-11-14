"""Pruebas de las acciones del Ronin: agacharse, dash, ataque, daño y muerte."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pygame

import settings as S
from animation import Animation, Animator
from level import Level
from player import Player, InputState
from projectile import Shuriken

DT = 1 / 60


def jugador_en_suelo():
    nivel = Level(S.LEVELS_DIR / "nivel1.txt")
    p = Player(*nivel.spawn)
    for _ in range(60):
        p.update(DT, InputState(), nivel)
    return nivel, p


def correr(p, nivel, segundos, **kw):
    for _ in range(int(segundos / DT)):
        p.update(DT, InputState(**kw), nivel)


class TestAgacharse(unittest.TestCase):
    def test_reduce_la_hitbox_y_mantiene_los_pies(self):
        nivel, p = jugador_en_suelo()
        suelo = p.pos.y + p.size[1]
        correr(p, nivel, 0.2, crouch=True)
        self.assertTrue(p.crouching)
        self.assertEqual(p.size[1], S.PLAYER_CROUCH_H)
        self.assertAlmostEqual(p.pos.y + p.size[1], suelo, places=3)
        self.assertEqual(p.state, "crouch")

    def test_se_levanta_al_soltar(self):
        nivel, p = jugador_en_suelo()
        correr(p, nivel, 0.2, crouch=True)
        correr(p, nivel, 0.2)
        self.assertFalse(p.crouching)
        self.assertEqual(p.size[1], S.PLAYER_SIZE[1])

    def test_no_se_levanta_bajo_un_techo_bajo(self):
        nivel, p = jugador_en_suelo()
        correr(p, nivel, 0.2, crouch=True)
        x, y = p.pos.x, p.pos.y
        nivel.solids.append(pygame.Rect(int(x) - 8, int(y) - 10, 60, 10))   # techo justo sobre la cabeza agachada
        correr(p, nivel, 0.3)
        self.assertTrue(p.crouching)

    def test_agachado_camina_mas_lento(self):
        nivel, p = jugador_en_suelo()
        correr(p, nivel, 0.5, crouch=True, move_x=1)
        self.assertAlmostEqual(p.vel.x, S.RUN_SPEED * S.CROUCH_SPEED_MULT, places=3)


class TestDash(unittest.TestCase):
    def test_impulso_y_duracion(self):
        nivel, p = jugador_en_suelo()
        x0 = p.pos.x
        p.update(DT, InputState(dash_pressed=True), nivel)
        self.assertEqual(p.state, "dash")
        self.assertAlmostEqual(p.vel.x, S.DASH_SPEED, places=3)
        correr(p, nivel, S.ACTION_TIME["dash"] + 0.05)
        self.assertIsNone(p.action)
        self.assertGreater(p.pos.x - x0, 70)           # recorrió unos 650 * 0.15 px

    def test_inercia_despues_del_dash(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(dash_pressed=True), nivel)
        correr(p, nivel, S.ACTION_TIME["dash"] + 0.05)
        self.assertGreater(p.vel.x, 0)                  # todavía se desliza
        correr(p, nivel, 0.6)
        self.assertEqual(p.vel.x, 0.0)

    def test_recarga(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(dash_pressed=True), nivel)
        correr(p, nivel, S.ACTION_TIME["dash"] + 0.05)
        p.update(DT, InputState(dash_pressed=True), nivel)
        self.assertIsNone(p.action)                      # aún en recarga
        correr(p, nivel, S.DASH_COOLDOWN)
        p.update(DT, InputState(dash_pressed=True), nivel)
        self.assertEqual(p.action, "dash")

    def test_sin_caida_durante_el_dash(self):
        nivel, p = jugador_en_suelo()
        p.pos.update(p.pos.x, p.pos.y - 40)
        p.update(DT, InputState(dash_pressed=True), nivel)
        y = p.pos.y
        correr(p, nivel, 0.1)
        self.assertAlmostEqual(p.pos.y, y, places=3)


class TestCombate(unittest.TestCase):
    def test_ataque_dura_lo_que_su_animacion(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(attack_pressed=True), nivel)
        self.assertEqual(p.state, "attack")
        correr(p, nivel, S.ACTION_TIME["attack"] - 0.05)
        self.assertEqual(p.state, "attack")
        correr(p, nivel, 0.1)
        self.assertIsNone(p.action)

    def test_no_se_empieza_otra_accion_a_mitad_de_una(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(attack_pressed=True), nivel)
        p.update(DT, InputState(parry_pressed=True), nivel)
        self.assertEqual(p.action, "attack")

    def test_desvio_y_lanzamiento(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(parry_pressed=True), nivel)
        self.assertEqual(p.state, "parry")
        correr(p, nivel, 0.5)
        p.update(DT, InputState(throw_pressed=True), nivel)
        self.assertEqual(p.state, "throw")

    def test_camina_mas_lento_mientras_ataca(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(attack_pressed=True, move_x=1), nivel)
        correr(p, nivel, 0.2, move_x=1)
        self.assertLessEqual(p.vel.x, S.RUN_SPEED * S.ACTION_SPEED_MULT + 1e-6)

    def test_golpe_empuja_hacia_atras_y_bloquea_el_control(self):
        nivel, p = jugador_en_suelo()
        p.facing = 1
        p.hurt()
        p.update(DT, InputState(move_x=1), nivel)
        self.assertEqual(p.state, "hurt")
        self.assertLess(p.vel.x, 0)                      # va hacia atrás aunque se pida avanzar
        self.assertLess(p.vel.y, 0)
        correr(p, nivel, S.ACTION_TIME["hurt"] + 0.1)
        self.assertIsNone(p.action)

    def test_muerte_es_permanente_hasta_reaparecer(self):
        nivel, p = jugador_en_suelo()
        p.die()
        correr(p, nivel, 2.0, move_x=1)
        self.assertEqual(p.state, "death")
        self.assertEqual(p.vel.x, 0.0)
        p.respawn(nivel.spawn)
        self.assertNotEqual(p.state, "death")


class TestAgachadoEnMovimiento(unittest.TestCase):
    def test_estado_crouch_walk_solo_si_se_mueve(self):
        nivel, p = jugador_en_suelo()
        correr(p, nivel, 0.3, crouch=True)
        self.assertEqual(p.state, "crouch")
        correr(p, nivel, 0.3, crouch=True, move_x=1)
        self.assertEqual(p.state, "crouch_walk")

    def test_agachado_avanza_mas_lento_que_de_pie(self):
        nivel, a = jugador_en_suelo()
        x0 = a.pos.x
        correr(a, nivel, 0.5, move_x=1)
        de_pie = a.pos.x - x0
        nivel, b = jugador_en_suelo()
        correr(b, nivel, 0.2, crouch=True)
        x0 = b.pos.x
        correr(b, nivel, 0.5, crouch=True, move_x=1)
        agachado = b.pos.x - x0
        self.assertGreater(agachado, 0)
        self.assertLess(agachado, de_pie * 0.6)

    def test_agachado_no_cambia_de_direccion_bloqueado_ni_salta(self):
        nivel, p = jugador_en_suelo()
        correr(p, nivel, 0.2, crouch=True)
        p.update(DT, InputState(crouch=True, jump_pressed=True, jump_held=True), nivel)
        self.assertLess(p.vel.y, 0.5 * S.JUMP_SPEED)   # al pulsar saltar se levanta, no sale disparado


class TestShuriken(unittest.TestCase):
    def test_sale_a_mitad_del_lanzamiento(self):
        nivel, p = jugador_en_suelo()
        p.update(DT, InputState(throw_pressed=True), nivel)
        self.assertEqual(p.new_projectiles, [])          # todavía lo tiene en la mano
        correr(p, nivel, S.THROW_RELEASE + 0.05)
        self.assertEqual(len(p.new_projectiles), 1)
        correr(p, nivel, 0.3)
        self.assertEqual(len(p.new_projectiles), 1)       # un solo shuriken por lanzamiento

    def test_sale_hacia_donde_mira(self):
        nivel, p = jugador_en_suelo()
        p.facing = -1
        p.update(DT, InputState(throw_pressed=True), nivel)
        correr(p, nivel, S.THROW_RELEASE + 0.05)
        self.assertLess(p.new_projectiles[0].vel.x, 0)

    def test_trayectoria_parabolica_y_rotacion(self):
        nivel, _ = jugador_en_suelo()
        s = Shuriken(100, 100, 1)
        y0 = s.vel.y
        for _ in range(30):
            s.update(DT, nivel)
        self.assertGreater(s.vel.y, y0)                   # la gravedad lo va curvando hacia abajo
        self.assertAlmostEqual(s.vel.x, S.SHURIKEN_SPEED, places=3)
        self.assertAlmostEqual(s.angle, (S.SHURIKEN_SPIN * 30 * DT) % 360, places=3)

    def test_se_clava_en_el_suelo(self):
        nivel, p = jugador_en_suelo()
        s = Shuriken(p.pos.x, nivel.height - 40, 1)
        s.vel.update(0, 400)
        for _ in range(60):
            s.update(DT, nivel)
        self.assertFalse(s.alive)

    def test_desaparece_por_tiempo(self):
        nivel, _ = jugador_en_suelo()
        s = Shuriken(100, 100, 1)
        s.vel.update(0, -S.SHURIKEN_GRAVITY * 0.5)
        s.pos.update(100, 100)
        s.age = S.SHURIKEN_LIFETIME
        s.update(DT, nivel)
        self.assertFalse(s.alive)


class TestAnimatorReinicio(unittest.TestCase):
    def test_restart_reinicia_la_misma_animacion(self):
        anim = Animator({"attack": Animation(["a0", "a1", "a2"], fps=10, loop=False)}, start="attack")
        anim.update(0.25)
        self.assertEqual(anim.frame, "a2")
        anim.play("attack")
        self.assertEqual(anim.frame, "a2")
        anim.play("attack", restart=True)
        self.assertEqual(anim.frame, "a0")


if __name__ == "__main__":
    unittest.main()
