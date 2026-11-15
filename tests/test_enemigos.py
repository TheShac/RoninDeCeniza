"""Pruebas del combate y del zombi caminante."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from combat import resolve_combat, slash_hits_rect
from enemy import Runner, Walker
from level import Level
from player import Player, InputState
from projectile import Shuriken

DT = 1 / 60
SUELO = 15 * S.TILE          # y de la superficie del suelo en nivel1


def nivel():
    return Level(S.LEVELS_DIR / "nivel1.txt")


def jugador_en(x_pies, lv):
    p = Player(x_pies - S.PLAYER_SIZE[0] / 2, SUELO - S.PLAYER_SIZE[1])
    for _ in range(30):
        p.update(DT, InputState(), lv)
    return p


def avanzar(lv, player, enemies, segundos, inp=None):
    for _ in range(int(segundos / DT)):
        player.update(DT, inp or InputState(), lv)
        resolve_combat(player, enemies, [])
        for e in enemies:
            e.update(DT, lv, player)


class TestGeometriaDelTajo(unittest.TestCase):
    ORIGEN = (100, 100)

    def test_enfrente_dentro_del_alcance(self):
        self.assertTrue(slash_hits_rect(self.ORIGEN, 1, (130, 90, 24, 50)))

    def test_detras_no(self):
        self.assertFalse(slash_hits_rect(self.ORIGEN, 1, (40, 90, 24, 50)))
        self.assertTrue(slash_hits_rect(self.ORIGEN, -1, (40, 90, 24, 50)))   # mirando a la izquierda sí

    def test_fuera_de_alcance(self):
        self.assertFalse(slash_hits_rect(self.ORIGEN, 1, (200, 90, 24, 50)))

    def test_arco_de_120_grados(self):
        self.assertTrue(slash_hits_rect(self.ORIGEN, 1, (130, 60, 24, 20)))     # unos 34 grados arriba: dentro
        self.assertFalse(slash_hits_rect(self.ORIGEN, 1, (88, 20, 24, 40)))     # justo encima: fuera del arco

    def test_origen_dentro_de_la_caja(self):
        self.assertTrue(slash_hits_rect(self.ORIGEN, 1, (90, 90, 24, 50)))


class TestVentanaDelTajo(unittest.TestCase):
    def test_solo_hiere_en_su_ventana(self):
        lv = nivel()
        p = jugador_en(200, lv)
        p.update(DT, InputState(attack_pressed=True), lv)
        self.assertFalse(p.slash_active)                     # al empezar todavía no
        for _ in range(int(0.10 / DT)):
            p.update(DT, InputState(), lv)
        self.assertTrue(p.slash_active)
        for _ in range(int(0.15 / DT)):
            p.update(DT, InputState(), lv)
        self.assertFalse(p.slash_active)                     # ya pasó el arco

    def test_un_tajo_hiere_una_sola_vez(self):
        lv = nivel()
        p = jugador_en(200, lv)
        z = Walker("aldeano", 200 + 40, SUELO)
        z.health = 3
        z.facing = -1
        p.facing = 1
        avanzar(lv, p, [z], 0.02, InputState(attack_pressed=True))
        avanzar(lv, p, [z], 0.4)
        self.assertEqual(z.health, 2)


class TestZombi(unittest.TestCase):
    def test_patrulla_a_su_velocidad(self):
        lv = nivel()
        p = jugador_en(100, lv)
        z = Walker("aldeano", 22 * S.TILE, SUELO)
        avanzar(lv, p, [z], 1.5)
        self.assertEqual(z.state, "patrol")
        self.assertAlmostEqual(abs(z.vel.x), S.WALKER_PATROL_SPEED, places=3)

    def test_da_la_vuelta_en_una_pared(self):
        lv = nivel()
        p = jugador_en(100, lv)
        z = Walker("samurai", 42 * S.TILE, SUELO)
        z.facing = 1                                      # hacia el escalón de las columnas 45-46
        giro = False
        for _ in range(int(8 / DT)):
            p.update(DT, InputState(), lv)
            z.update(DT, lv, p)
            giro = giro or z.facing == -1
        self.assertTrue(giro)

    def test_no_se_cae_por_el_pozo(self):
        lv = nivel()
        p = jugador_en(100, lv)
        z = Walker("aldeano", 31 * S.TILE, SUELO)          # el pozo está en las columnas 34-37
        z.facing = 1
        for _ in range(int(20 / DT)):
            p.update(DT, InputState(), lv)
            z.update(DT, lv, p)
            self.assertLessEqual(z.pos.y + z.size[1], SUELO + 1)
        self.assertFalse(z.removable)

    def test_persigue_al_ronin_que_ve(self):
        lv = nivel()
        z = Walker("aldeano", 20 * S.TILE, SUELO)
        p = jugador_en(20 * S.TILE + 150, lv)
        avanzar(lv, p, [z], 0.5)
        self.assertEqual(z.facing, 1)
        self.assertGreater(z.vel.x, S.WALKER_PATROL_SPEED)

    def test_no_ve_al_ronin_lejano(self):
        lv = nivel()
        z = Walker("aldeano", 20 * S.TILE, SUELO)
        p = jugador_en(20 * S.TILE + 400, lv)
        avanzar(lv, p, [z], 0.5)
        self.assertEqual(z.state, "patrol")

    def test_el_zarpazo_quita_un_corazon_una_vez(self):
        lv = nivel()
        z = Walker("aldeano", 20 * S.TILE, SUELO)
        p = jugador_en(20 * S.TILE + 60, lv)
        avanzar(lv, p, [z], 0.9)
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 1)
        self.assertGreater(p.iframes, 0)

    def test_la_invulnerabilidad_evita_golpes_seguidos(self):
        lv = nivel()
        p = jugador_en(200, lv)
        self.assertTrue(p.take_damage(100))
        self.assertFalse(p.take_damage(100))
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 1)

    def test_el_golpe_empuja_al_ronin_lejos_del_zombi(self):
        lv = nivel()
        p = jugador_en(200, lv)
        p.take_damage(150)                                  # el golpe viene desde la izquierda
        self.assertGreater(p.vel.x, 0)

    def test_sin_corazones_muere(self):
        lv = nivel()
        p = jugador_en(200, lv)
        for _ in range(S.PLAYER_MAX_HEALTH):
            p.iframes = 0.0
            p.action = None
            p.take_damage(100)
        self.assertTrue(p.dead)
        self.assertEqual(p.health, 0)

    def test_un_tajo_lo_mata_y_queda_el_cuerpo(self):
        lv = nivel()
        p = jugador_en(200, lv)
        p.facing = 1
        z = Walker("samurai", 200 + 45, SUELO)
        avanzar(lv, p, [z], 0.02, InputState(attack_pressed=True))
        avanzar(lv, p, [z], 0.3)
        self.assertTrue(z.dead)
        self.assertFalse(z.removable)
        avanzar(lv, p, [z], S.ENEMY_ACTION_TIME["death"] + S.CORPSE_TIME + 0.3)
        self.assertTrue(z.removable)

    def test_un_muerto_no_ataca(self):
        lv = nivel()
        z = Walker("aldeano", 20 * S.TILE, SUELO)
        p = jugador_en(20 * S.TILE + 20, lv)
        z.damage(1, p.center[0])
        avanzar(lv, p, [z], 1.5)
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH)

    def test_el_shuriken_lo_mata(self):
        lv = nivel()
        p = jugador_en(100, lv)
        z = Walker("aldeano", 400, SUELO)
        shot = Shuriken(z.center[0], z.center[1], 1)
        resolve_combat(p, [z], [shot])
        self.assertTrue(z.dead)
        self.assertFalse(shot.alive)

    def test_empuja_hacia_atras_al_morir(self):
        z = Walker("aldeano", 400, SUELO)
        z.damage(1, 300)                                    # golpe desde la izquierda
        self.assertGreater(z.vel.x, 0)

    def test_nivel_de_pruebas_tiene_enemigos_de_ambas_variantes(self):
        variantes = {(k, v) for k, v, _, _ in nivel().enemy_spawns}
        self.assertEqual(variantes, {("caminante", "aldeano"), ("caminante", "samurai"),
                                     ("corredor", "campesino"), ("corredor", "ashigaru")})

    def test_nivel_de_pruebas_esta_marcado_como_tal(self):
        self.assertTrue(nivel().test_mode)


class TestCorredor(unittest.TestCase):
    def nuevo(self, x_corredor=20 * S.TILE, x_ronin=None, variante="campesino"):
        lv = nivel()
        r = Runner(variante, x_corredor, SUELO)
        p = jugador_en(x_ronin if x_ronin is not None else x_corredor + 250, lv)
        return lv, p, r

    def correr(self, lv, p, r, segundos, inp=None):
        for _ in range(int(segundos / DT)):
            p.update(DT, inp or InputState(), lv)
            resolve_combat(p, [r], [])
            r.update(DT, lv, p)

    def test_patrulla_mas_rapido_que_el_caminante(self):
        lv, p, r = self.nuevo(x_ronin=100)
        self.correr(lv, p, r, 1.5)
        self.assertEqual(r.state, "patrol")
        self.assertAlmostEqual(abs(r.vel.x), S.RUNNER_PATROL_SPEED, places=3)

    def test_la_embestida_acelera_de_forma_constante_y_tiene_tope(self):
        lv, p, r = self.nuevo()
        r.facing = 1
        self.correr(lv, p, r, 0.05)                         # ve al Ronin: empieza a embestir
        self.assertEqual(r.state, "charge")
        v0 = r.vel.x
        self.correr(lv, p, r, 0.10)
        self.assertAlmostEqual(r.vel.x - v0, S.RUNNER_ACCEL * 0.10, delta=S.RUNNER_ACCEL * DT * 1.5)
        self.correr(lv, p, r, 0.20)
        self.assertLessEqual(r.vel.x, S.RUNNER_MAX_SPEED + 1e-6)

    def test_embiste_hacia_el_ronin_aunque_mire_para_otro_lado(self):
        lv, p, r = self.nuevo(x_ronin=20 * S.TILE - 200)
        r.facing = 1
        self.correr(lv, p, r, 0.1)
        self.assertEqual(r.facing, -1)
        self.assertLess(r.vel.x, 0)

    def test_no_embiste_si_el_ronin_esta_lejos(self):
        lv, p, r = self.nuevo(x_ronin=20 * S.TILE + 500)
        self.correr(lv, p, r, 0.5)
        self.assertEqual(r.state, "patrol")

    def test_la_embestida_hiere_una_vez(self):
        lv, p, r = self.nuevo(x_ronin=20 * S.TILE + 200)
        self.correr(lv, p, r, 1.2)
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 1)

    def test_si_falla_frena_y_queda_aturdido(self):
        lv, p, r = self.nuevo(x_ronin=20 * S.TILE + 200)
        p.take_damage(0)                                    # el Ronin ya es invulnerable: la embestida "falla"
        p.iframes = 10.0
        estados = []
        for _ in range(int(3.0 / DT)):
            p.update(DT, InputState(), lv)
            r.update(DT, lv, p)
            if not estados or estados[-1] != r.state:
                estados.append(r.state)
        self.assertEqual(estados[:4], ["patrol", "charge", "brake", "stun"])

    def test_el_dash_atraviesa_la_embestida_sin_dano(self):
        lv, p, r = self.nuevo(x_corredor=20 * S.TILE, x_ronin=20 * S.TILE + 200)
        p.facing = -1                                        # mira al corredor, que llega desde la izquierda
        estados = []
        for _ in range(int(3 / DT)):
            cerca = abs(p.center[0] - r.center[0]) < 75
            p.update(DT, InputState(dash_pressed=cerca), lv)
            r.update(DT, lv, p)
            if not estados or estados[-1] != r.state:
                estados.append(r.state)
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH)      # el dash lo hizo invulnerable
        self.assertIn("stun", estados)                       # la embestida falló y quedó aturdido
        self.assertLess(p.pos.x, r.pos.x)                    # el Ronin quedó detrás

    def test_aturdido_tarda_lo_indicado_y_luego_patrulla(self):
        lv, p, r = self.nuevo(x_ronin=20 * S.TILE + 100)
        p.iframes = 100.0
        while r.state != "stun":
            p.update(DT, InputState(), lv)
            r.update(DT, lv, p)
        t = 0.0
        while r.state == "stun":
            p.update(DT, InputState(), lv)
            r.update(DT, lv, p)
            t += DT
        self.assertAlmostEqual(t, S.RUNNER_STUN, delta=3 * DT)
        self.assertEqual(r.state, "patrol")

    def test_aturdido_es_vulnerable(self):
        lv, p, r = self.nuevo(x_ronin=20 * S.TILE + 100)
        p.iframes = 100.0
        while r.state != "stun":
            p.update(DT, InputState(), lv)
            r.update(DT, lv, p)
        self.assertTrue(r.damage(1, p.center[0]))
        self.assertTrue(r.dead)

    def _con_ronin_quieto(self, x_corredor, x_ronin, segundos):
        """El Ronin se queda fijo en el suelo; devuelve los estados por los que pasa el corredor."""
        lv = nivel()
        r = Runner("ashigaru", x_corredor, SUELO)
        p = jugador_en(x_ronin, lv)
        fijo = p.pos.x
        estados, y_max = [], 0.0
        for _ in range(int(segundos / DT)):
            p.pos.update(fijo, SUELO - S.PLAYER_SIZE[1])
            p.vel.update(0, 0)
            p.iframes = max(p.iframes, 1.0)
            r.update(DT, lv, p)
            y_max = max(y_max, r.pos.y + r.size[1])
            if not estados or estados[-1] != r.state:
                estados.append(r.state)
        return r, estados, y_max

    def test_se_detiene_en_el_borde_del_pozo_al_embestir(self):
        r, estados, y_max = self._con_ronin_quieto(31 * S.TILE, 39 * S.TILE, 4.0)   # pozo en las columnas 34-37
        self.assertIn("charge", estados)
        self.assertLessEqual(y_max, SUELO + 1)               # nunca bajó del suelo: no cayó
        self.assertLess(r.pos.x + r.size[0], 34 * S.TILE)    # se quedó antes del pozo

    def test_se_detiene_ante_la_pared_y_queda_aturdido(self):
        r, estados, _ = self._con_ronin_quieto(42 * S.TILE, 48 * S.TILE, 1.5)       # escalón en las columnas 45-46
        self.assertEqual(estados[:4], ["patrol", "charge", "brake", "stun"])
        self.assertLessEqual(r.pos.x + r.size[0], 45 * S.TILE + 1)

    def test_un_tajo_o_shuriken_lo_mata(self):
        lv, p, r = self.nuevo()
        shot = Shuriken(r.center[0], r.center[1], 1)
        resolve_combat(p, [r], [shot])
        self.assertTrue(r.dead)


def rects_overlap_player(r, p):
    from combat import rects_overlap
    return rects_overlap(r.rect, p.rect)


class TestInvulnerabilidadDelRonin(unittest.TestCase):
    def test_los_golpes_durante_la_invulnerabilidad_no_hacen_nada(self):
        lv = nivel()
        p = jugador_en(200, lv)
        self.assertTrue(p.take_damage(150))
        vida, vel_x = p.health, p.vel.x
        for _ in range(int(S.PLAYER_IFRAMES / DT) - 2):
            p.update(DT, InputState(), lv)
            self.assertFalse(p.take_damage(150))
        self.assertEqual(p.health, vida)

    def test_un_golpe_en_curso_no_reinicia_la_animacion(self):
        lv = nivel()
        p = jugador_en(200, lv)
        p.take_damage(150)
        for _ in range(10):
            p.update(DT, InputState(), lv)
        restante = p.action_time
        p.hurt(150)                                        # lo que hacía la tecla de prueba antes
        self.assertEqual(p.action_time, restante)

    def test_recupera_el_control_al_terminar_la_animacion_aunque_siga_invulnerable(self):
        lv = nivel()
        p = jugador_en(200, lv)
        p.take_damage(150)
        for _ in range(int((S.ACTION_TIME["hurt"] + 0.1) / DT)):
            p.update(DT, InputState(move_x=1), lv)
        self.assertIsNone(p.action)
        self.assertGreater(p.iframes, 0)                   # sigue invulnerable...
        x = p.pos.x
        for _ in range(30):
            p.update(DT, InputState(move_x=1), lv)
        self.assertGreater(p.pos.x, x + 10)                # ...pero ya se puede mover
        self.assertEqual(p.state, "run")

    def test_un_zombi_muerto_ya_no_recibe_golpes(self):
        lv = nivel()
        p = jugador_en(200, lv)
        p.facing = 1
        z = Walker("samurai", 245, SUELO)
        self.assertTrue(z.damage(1, 200))
        self.assertFalse(z.damage(1, 200))
        shot = Shuriken(z.center[0], z.center[1], 1)
        resolve_combat(p, [z], [shot])
        self.assertTrue(shot.alive)                        # el shuriken atraviesa el cuerpo


if __name__ == "__main__":
    unittest.main()
