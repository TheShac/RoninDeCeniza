"""Pruebas del zombi hinchado: estados, mecha, explosión con impulso radial y reacción en cadena."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from combat import apply_blast, blast_push
from enemy import Bloater, ENEMY_CLASSES, Walker
from level import Level
from player import Player, InputState

DT = 1 / 60
SUELO = 15 * S.TILE


def nivel():
    return Level(S.BASE_DIR / "tests" / "niveles" / "pruebas.txt")


def ronin(x, lv):
    p = Player(x, SUELO - S.PLAYER_SIZE[1])
    for _ in range(30):
        p.update(DT, InputState(), lv)
    return p


def hinchado(x, lv):
    b = Bloater("sumo", x, SUELO)
    for _ in range(30):
        b.update(DT, lv, Player(1500, 0))
    b.pos.x, b.vel.x = x - b.size[0] / 2, 0.0           # durante el asentamiento patrulla: lo devolvemos a su sitio
    return b


def correr(b, lv, p, seg):
    for _ in range(int(seg / DT)):
        b.update(DT, lv, p)


class TestImpulsoRadial(unittest.TestCase):
    def test_fuera_del_radio_no_hay_impulso(self):
        self.assertIsNone(blast_push((0, 0), (S.BLAST_RADIUS + 1, 0)))

    def test_el_impulso_baja_linealmente_con_la_distancia(self):
        mitad = blast_push((0, 0), (S.BLAST_RADIUS / 2, 0))
        self.assertAlmostEqual(mitad[2], 0.5, places=9)
        cerca = blast_push((0, 0), (S.BLAST_RADIUS / 10, 0))
        self.assertGreater(math.hypot(cerca[0], cerca[1]), math.hypot(mitad[0], mitad[1]))
        # magnitud exacta: strength * falloff
        self.assertAlmostEqual(math.hypot(mitad[0], mitad[1]), S.BLAST_IMPULSE * 0.5, places=6)

    def test_empuja_hacia_afuera_y_un_poco_hacia_arriba(self):
        der = blast_push((100, 100), (160, 100))
        izq = blast_push((100, 100), (40, 100))
        self.assertGreater(der[0], 0)
        self.assertLess(izq[0], 0)
        self.assertLess(der[1], 0)                      # y negativa = hacia arriba
        self.assertAlmostEqual(der[0], -izq[0], places=6)

    def test_en_el_centro_exacto_empuja_hacia_arriba(self):
        vx, vy, f = blast_push((50, 50), (50, 50))
        self.assertEqual(vx, 0.0)
        self.assertAlmostEqual(vy, -S.BLAST_IMPULSE, places=6)
        self.assertAlmostEqual(f, 1.0)

    def test_desde_abajo_empuja_hacia_arriba_mas_que_desde_arriba(self):
        debajo = blast_push((0, 0), (0, 50))          # el objetivo está debajo del centro
        encima = blast_push((0, 0), (0, -50))
        self.assertLess(encima[1], debajo[1])         # el de arriba sale disparado más hacia arriba


class TestEstados(unittest.TestCase):
    def test_esta_registrado(self):
        self.assertIs(ENEMY_CLASSES["hinchado"], Bloater)

    def test_camina_lento_hacia_el_ronin_y_se_infla_al_llegar(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 200, lv)
        estados = set()
        for _ in range(int(6 / DT)):
            b.update(DT, lv, p)
            estados.add(b.state)
            if b.state == "inflate":
                break
        self.assertIn("chase", estados)
        self.assertEqual(b.state, "inflate")
        self.assertLessEqual(abs(p.center[0] - b.center[0]) - (b.size[0] + p.size[0]) / 2, S.BLOATER_TRIGGER + 2)

    def test_velocidad_de_persecucion_es_48(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 220, lv)
        correr(b, lv, p, 0.6)
        self.assertEqual(b.state, "chase")
        self.assertAlmostEqual(abs(b.vel.x), 48.0, places=3)

    def test_inflado_se_queda_quieto_y_revienta_a_la_mecha(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 60, lv)
        correr(b, lv, p, 0.1)
        self.assertEqual(b.state, "inflate")
        x0 = b.pos.x
        correr(b, lv, p, S.BLOATER_FUSE - 0.2)
        self.assertEqual(b.state, "inflate")
        self.assertIsNone(b.blast)
        self.assertAlmostEqual(b.pos.x, x0, delta=1.0)
        correr(b, lv, p, 0.3)
        self.assertEqual(b.state, "dead")
        self.assertIsNotNone(b.blast)
        self.assertEqual(b.blast["radius"], S.BLAST_RADIUS)

    def test_la_mecha_sigue_aunque_el_ronin_se_aleje(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 60, lv)
        correr(b, lv, p, 0.1)
        p.pos.x += 600
        correr(b, lv, p, S.BLOATER_FUSE + 0.1)
        self.assertEqual(b.state, "dead")

    def test_tres_golpes_lo_matan_y_revienta_con_mecha_corta(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = Player(1500, 0)                                   # lejos: no se activa solo
        b.damage(1, 250)
        self.assertEqual(b.state, "hurt")
        self.assertFalse(b.doomed)
        correr(b, lv, p, S.ENEMY_ACTION_TIME["hurt"] + 0.05)
        b.damage(1, 250)
        correr(b, lv, p, S.ENEMY_ACTION_TIME["hurt"] + 0.05)
        b.damage(1, 250)
        self.assertTrue(b.doomed)
        self.assertEqual(b.state, "inflate")
        correr(b, lv, p, S.BLOATER_DEATH_FUSE - 0.1)
        self.assertEqual(b.state, "inflate")
        correr(b, lv, p, 0.2)
        self.assertEqual(b.state, "dead")
        self.assertIsNotNone(b.blast)

    def test_herido_mientras_se_infla_no_cancela_la_mecha(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 60, lv)
        correr(b, lv, p, 0.1)
        b.damage(1, 250)
        self.assertEqual(b.state, "inflate")
        correr(b, lv, p, S.BLOATER_FUSE)
        self.assertEqual(b.state, "dead")

    def test_matarlo_a_mitad_de_mecha_la_acorta(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 60, lv)
        correr(b, lv, p, 0.1)
        b.health = 1
        b.damage(1, 250)
        self.assertLessEqual(b.fuse, S.BLOATER_DEATH_FUSE)

    def test_matarlo_con_la_mecha_casi_gastada_no_la_alarga(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 60, lv)
        correr(b, lv, p, S.BLOATER_FUSE - 0.1)
        restante = b.fuse
        self.assertLess(restante, S.BLOATER_DEATH_FUSE)
        b.health = 1
        b.damage(1, 250)
        self.assertEqual(b.fuse, restante)

    def test_no_se_puede_golpear_mientras_explota_y_desaparece_despues(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 60, lv)
        correr(b, lv, p, S.BLOATER_FUSE + 0.2)
        self.assertEqual(b.state, "dead")
        self.assertFalse(b.can_be_hit)
        self.assertFalse(b.damage(1, 250))
        self.assertFalse(b.removable)
        correr(b, lv, p, S.BLOATER_EXPLODE_TIME)
        self.assertTrue(b.removable)

    def test_cuadro_de_inflado_sigue_a_la_mecha(self):
        lv = nivel()
        b = Bloater("sumo", 300, SUELO)
        from animation import Animation, Animator
        frames = [object() for _ in range(5)]
        b.animator = Animator({"walk": Animation(frames, 5), "inflate": Animation(frames, 5, loop=False),
                               "hurt": Animation(frames, 5, loop=False), "explode": Animation(frames, 5, loop=False)},
                              start="walk")
        for _ in range(30):
            b.update(DT, lv, Player(1500, 0))
        b.pos.x, b.vel.x = 300 - b.size[0] / 2, 0.0
        p = ronin(300 + 60, lv)
        indices = []
        for _ in range(int((S.BLOATER_FUSE - 0.05) / DT)):
            b.update(DT, lv, p)
            if b.state == "inflate":
                indices.append(frames.index(b.animator.frame))
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 4)
        self.assertEqual(indices, sorted(indices))


class TestExplosion(unittest.TestCase):
    def explotar(self, lv, b, p, otros=()):
        correr(b, lv, p, S.BLOATER_FUSE + 0.1)
        self.assertIsNotNone(b.blast)
        apply_blast(b.blast, p, list(otros))

    def test_el_ronin_cercano_pierde_dos_corazones_y_sale_empujado(self):
        lv = nivel()
        b = hinchado(300, lv)
        p = ronin(300 + 60, lv)
        p.facing = -1
        h0, x0 = p.health, p.vel.x
        self.explotar(lv, b, p)
        self.assertEqual(p.health, h0 - S.BLAST_PLAYER_DAMAGE)
        self.assertGreater(p.vel.x, 100)                       # empujado hacia la derecha (lejos del hinchado)
        self.assertLess(p.vel.y, 0)                            # y un poco hacia arriba

    def test_el_ronin_lejos_no_recibe_nada(self):
        lv = nivel()
        b = hinchado(300, lv)
        correr(b, lv, Player(300, 0), 0)
        b.blast = {"x": b.center[0], "y": b.center[1], "radius": S.BLAST_RADIUS}
        p = ronin(300 + S.BLAST_RADIUS + 120, lv)
        h0 = p.health
        apply_blast(b.blast, p, [])
        self.assertEqual(p.health, h0)
        self.assertEqual(p.vel.x, 0.0)

    def test_mas_cerca_empuja_mas_fuerte(self):
        lv = nivel()
        blast = {"x": 500.0, "y": SUELO - 34.0, "radius": S.BLAST_RADIUS}
        cerca, lejos = ronin(500 + 40, lv), ronin(500 + 90, lv)
        apply_blast(blast, cerca, [])
        apply_blast(blast, lejos, [])
        self.assertGreater(math.hypot(cerca.vel.x, cerca.vel.y), math.hypot(lejos.vel.x, lejos.vel.y))

    def test_el_dash_esquiva_el_dano_pero_no_el_empuje(self):
        lv = nivel()
        p = ronin(500 + 50, lv)
        p.update(DT, InputState(dash_pressed=True), lv)
        self.assertTrue(p.invulnerable)
        h0 = p.health
        apply_blast({"x": 500.0, "y": SUELO - 34.0, "radius": S.BLAST_RADIUS}, p, [])
        self.assertEqual(p.health, h0)
        self.assertNotEqual((p.vel.x, p.vel.y), (S.DASH_SPEED * p.facing, 0.0))

    def test_mata_a_los_zombis_cercanos_y_los_empuja(self):
        lv = nivel()
        b = hinchado(300, lv)
        vecino = Walker("aldeano", 300 + 70, SUELO)
        lejano = Walker("aldeano", 300 + 400, SUELO)
        p = Player(1500, 0)
        b._ignite(S.BLOATER_FUSE)
        correr(b, lv, p, S.BLOATER_FUSE + 0.1)
        apply_blast(b.blast, p, [vecino, lejano])
        self.assertTrue(vecino.dead)
        self.assertGreater(vecino.vel.x, 0)
        self.assertFalse(lejano.dead)

    def test_reaccion_en_cadena_entre_dos_hinchados(self):
        lv = nivel()
        a, b = hinchado(300, lv), hinchado(300 + 90, lv)
        p = Player(1500, 0)
        a._ignite(S.BLOATER_FUSE)
        correr(a, lv, p, S.BLOATER_FUSE + 0.1)
        apply_blast(a.blast, p, [b])
        self.assertTrue(b.doomed)
        self.assertEqual(b.state, "inflate")
        correr(b, lv, p, S.BLOATER_DEATH_FUSE + 0.1)
        self.assertEqual(b.state, "dead")
        self.assertIsNotNone(b.blast)

    def test_no_se_hiere_a_si_mismo_ni_a_otro_ya_explotando(self):
        lv = nivel()
        a, b = hinchado(300, lv), hinchado(300 + 90, lv)
        p = Player(1500, 0)
        a._ignite(S.BLOATER_FUSE)
        correr(a, lv, p, S.BLOATER_FUSE + 0.1)
        b._explode()
        h = b.health
        apply_blast(a.blast, p, [b])
        self.assertEqual(b.health, h)

    def test_ronin_muerto_no_recibe_impulso(self):
        lv = nivel()
        p = ronin(500, lv)
        p.die()
        apply_blast({"x": 500.0, "y": SUELO - 34.0, "radius": S.BLAST_RADIUS}, p, [])
        self.assertEqual(p.vel.x, 0.0)


class TestPlayerTakeDamage(unittest.TestCase):
    def test_cantidad_de_dano(self):
        lv = nivel()
        p = ronin(300, lv)
        self.assertTrue(p.take_damage(200, 3))
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 3)

    def test_mucho_dano_mata_sin_vida_negativa(self):
        lv = nivel()
        p = ronin(300, lv)
        p.take_damage(200, 99)
        self.assertEqual(p.health, 0)
        self.assertTrue(p.dead)


if __name__ == "__main__":
    unittest.main()
