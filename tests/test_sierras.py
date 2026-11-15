"""Pruebas de la sierra giratoria: rotación, riel, colisión círculo-caja, daño y lectura desde el nivel."""
import contextlib
import io
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from combat import resolve_hazards
from hazard import Saw
from level import Level
from player import Player, InputState

DT = 1 / 60
FIXTURE = S.BASE_DIR / "tests" / "niveles" / "pruebas.txt"
SUELO = 15 * S.TILE


def nivel_con(texto):
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "n.txt"
        ruta.write_text(texto, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            lv = Level(ruta)
    return lv, salida.getvalue()


def ronin(x=300):
    lv = Level(FIXTURE)
    p = Player(x, SUELO - S.PLAYER_SIZE[1])
    for _ in range(30):
        p.update(DT, InputState(), lv)
    return lv, p


class TestRotacion(unittest.TestCase):
    def test_el_angulo_avanza_omega_por_dt(self):
        s = Saw(100, 100, omega=10.0)
        s.update(0.1)
        self.assertAlmostEqual(s.angle, 1.0, places=9)

    def test_el_angulo_se_mantiene_entre_0_y_2pi(self):
        s = Saw(100, 100, omega=S.SAW_OMEGA)
        for _ in range(600):
            s.update(DT)
            self.assertTrue(0 <= s.angle < 2 * math.pi)

    def test_una_vuelta_completa_tarda_2pi_sobre_omega(self):
        s = Saw(100, 100, omega=math.pi)               # media vuelta por segundo
        for _ in range(120):                           # 2 s = una vuelta
            s.update(DT)
        self.assertTrue(s.angle < 1e-6 or abs(s.angle - 2 * math.pi) < 1e-6)

    def test_velocidad_tangencial(self):
        s = Saw(0, 0, radius=26.0, omega=18.0)
        self.assertAlmostEqual(s.tangential_speed, 468.0, places=6)

    def test_gira_en_su_sitio_si_no_tiene_riel(self):
        s = Saw(120, 90)
        for _ in range(100):
            s.update(DT)
        self.assertEqual((s.pos.x, s.pos.y), (120, 90))

    def test_los_dientes_giran_con_el_disco(self):
        s = Saw(100, 100)
        antes = s.blade_points()
        s.update(0.05)
        self.assertNotEqual(antes, s.blade_points())
        self.assertEqual(len(antes), 2 * S.SAW_TEETH)
        for x, y in antes:                             # todos los puntos quedan dentro del radio dibujado
            self.assertLessEqual(math.hypot(x - 100, y - 100), s.radius + 1e-9)


class TestRiel(unittest.TestCase):
    def test_va_y_viene_por_el_riel(self):
        s = Saw(100, 200, path=(200, 0), speed=100.0)
        xs = []
        for _ in range(int(5 / DT)):
            s.update(DT)
            xs.append(s.pos.x)
        self.assertGreaterEqual(min(xs), 100 - 1e-6)
        self.assertLessEqual(max(xs), 300 + 1e-6)
        self.assertAlmostEqual(max(xs), 300, delta=2)          # llega al final (a los 2 s)
        self.assertAlmostEqual(min(xs[130:]), 100, delta=2)    # y vuelve al principio (a los 4 s)

    def test_velocidad_constante_entre_los_extremos(self):
        s = Saw(0, 0, path=(300, 0), speed=120.0)
        s.update(DT)
        x1 = s.pos.x
        s.update(DT)
        self.assertAlmostEqual(s.pos.x - x1, 120.0 * DT, places=6)

    def test_riel_diagonal_y_vertical(self):
        s = Saw(50, 50, path=(0, 120), speed=60.0)
        for _ in range(60):                                   # 1 s
            s.update(DT)
        self.assertEqual(s.pos.x, 50)
        self.assertAlmostEqual(s.pos.y, 110, places=5)
        d = Saw(0, 0, path=(60, 80), speed=50.0)               # largo 100
        for _ in range(60):
            d.update(DT)
        self.assertAlmostEqual(math.hypot(d.pos.x, d.pos.y), 50.0, places=4)
        self.assertAlmostEqual(d.pos.y / d.pos.x, 80 / 60, places=6)

    def test_la_fase_desplaza_el_inicio(self):
        s = Saw(0, 0, path=(100, 0), speed=10.0, phase=0.5)    # mitad del ciclo: en el extremo
        self.assertAlmostEqual(s.pos.x, 100, places=6)

    def test_un_paso_de_tiempo_enorme_no_se_sale_del_riel(self):
        s = Saw(0, 0, path=(100, 0), speed=100.0)
        s.update(37.3)
        self.assertTrue(0 <= s.pos.x <= 100)


class TestColision(unittest.TestCase):
    def test_caja_dentro_del_circulo(self):
        s = Saw(100, 100, radius=20)
        self.assertTrue(s.hits_rect((95, 95, 10, 10)))

    def test_caja_lejos_no_golpea(self):
        s = Saw(100, 100, radius=20)
        self.assertFalse(s.hits_rect((200, 100, 10, 10)))

    def test_la_esquina_cuenta_con_distancia_euclidiana(self):
        s = Saw(100, 100, radius=20)                           # radio de golpe = 17,6
        # la esquina de la caja está a (14, 14) del centro: distancia 19,8 > 17,6 aunque las cajas se solapen
        self.assertFalse(s.hits_rect((114, 114, 30, 30)))
        # a (11, 11): distancia 15,6 < 17,6
        self.assertTrue(s.hits_rect((111, 111, 30, 30)))

    def test_la_zona_de_golpe_es_menor_que_el_dibujo(self):
        s = Saw(100, 100, radius=20)
        casi = 20 * (S.SAW_HIT_SCALE + 1) / 2                  # entre el radio de golpe y el dibujado
        self.assertFalse(s.hits_rect((100 + casi, 95, 10, 10)))
        self.assertTrue(s.hits_rect((100 + s.hit_radius - 0.5, 95, 10, 10)))

    def test_tocar_justo_el_borde_cuenta(self):
        s = Saw(0, 0, radius=10)
        self.assertTrue(s.hits_rect((s.hit_radius, -5, 10, 10)))

    def test_el_punto_de_contacto_esta_en_la_caja(self):
        s = Saw(0, 50, radius=20)
        self.assertEqual(s.contact_point((10, 0, 20, 100)), (10, 50))


class TestDano(unittest.TestCase):
    def test_la_sierra_quita_un_corazon_y_empuja(self):
        lv, p = ronin()
        x, y = p.center
        sierra = Saw(x - 12, y)                                # pegada al lado izquierdo del Ronin
        eventos = resolve_hazards(p, [sierra])
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - S.SAW_DAMAGE)
        self.assertEqual(p.action, "hurt")
        self.assertGreater(p.vel.x, 0)                         # lo empuja hacia la derecha, lejos de la sierra
        self.assertEqual(eventos[0][0], "spark")

    def test_no_quita_corazones_cada_frame_por_la_invulnerabilidad(self):
        lv, p = ronin()
        sierra = Saw(p.center[0], p.center[1])
        for _ in range(30):                                    # medio segundo encima de la sierra
            resolve_hazards(p, [sierra])
            p.update(DT, InputState(), lv)
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 1)

    def test_si_se_queda_encima_vuelve_a_dolerle_al_acabar_la_invulnerabilidad(self):
        lv, p = ronin()
        sierra = Saw(p.center[0], p.center[1])
        resolve_hazards(p, [sierra])
        for _ in range(int((S.PLAYER_IFRAMES + 0.2) / DT)):
            p.pos.update(p.pos.x, p.pos.y)
            p.vel.update(0, 0)
            p.update(DT, InputState(), lv)
        sierra.pos.update(p.center[0], p.center[1])
        resolve_hazards(p, [sierra])
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 2)

    def test_el_dash_atraviesa_la_sierra(self):
        lv, p = ronin()
        p.update(DT, InputState(dash_pressed=True), lv)
        sierra = Saw(p.center[0] + 20, p.center[1])
        resolve_hazards(p, [sierra])
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH)

    def test_una_sierra_lejana_no_hace_nada(self):
        lv, p = ronin()
        resolve_hazards(p, [Saw(p.center[0] + 300, p.center[1])])
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH)

    def test_con_varias_sierras_solo_cuenta_un_golpe_a_la_vez(self):
        lv, p = ronin()
        a, b = Saw(p.center[0] - 5, p.center[1]), Saw(p.center[0] + 5, p.center[1])
        resolve_hazards(p, [a, b])
        self.assertEqual(p.health, S.PLAYER_MAX_HEALTH - 1)

    def test_un_ronin_muerto_no_recibe_dano(self):
        lv, p = ronin()
        p.die()
        h = p.health
        self.assertEqual(resolve_hazards(p, [Saw(p.center[0], p.center[1])]), [])
        self.assertEqual(p.health, h)

    def test_la_sierra_en_movimiento_alcanza_al_ronin_parado(self):
        lv, p = ronin(400)
        sierra = Saw(p.center[0] - 150, p.center[1], path=(300, 0), speed=150.0)
        golpe = None
        for i in range(int(3 / DT)):
            sierra.update(DT)
            if resolve_hazards(p, [sierra]):
                golpe = i * DT
                break
        self.assertIsNotNone(golpe)
        self.assertAlmostEqual(golpe, (150 - 12 - sierra.hit_radius) / 150, delta=0.12)


class TestNivel(unittest.TestCase):
    def test_la_letra_O_pone_una_sierra_fija_centrada_en_la_casilla(self):
        lv, _ = nivel_con("#....#\n#..O.#\n######\n")
        self.assertEqual(len(lv.saw_specs), 1)
        cx, cy, r, dx, dy, v = lv.saw_specs[0]
        self.assertEqual((cx, cy), (3 * S.TILE + S.TILE / 2, 1 * S.TILE + S.TILE / 2))
        self.assertEqual((dx, dy, r), (0.0, 0.0, S.SAW_RADIUS))

    def test_la_O_no_es_un_bloque_solido(self):
        lv, _ = nivel_con("#....#\n#..O.#\n######\n")
        self.assertFalse(any(r.x == 3 * S.TILE and r.y == S.TILE for r in lv.solids))

    def test_sierra_con_riel_y_parametros(self):
        lv, _ = nivel_con(";sierra=10,4,6,0,120,30\n#..#\n")
        cx, cy, r, dx, dy, v = lv.saw_specs[0]
        self.assertEqual((cx, cy), (10 * S.TILE + 16, 4 * S.TILE + 16))
        self.assertEqual((dx, dy, v, r), (6 * S.TILE, 0.0, 120.0, 30.0))

    def test_valores_por_defecto_de_velocidad_y_radio(self):
        lv, _ = nivel_con(";sierra=2,3,4,0\n#..#\n")
        _, _, r, _, _, v = lv.saw_specs[0]
        self.assertEqual((r, v), (S.SAW_RADIUS, S.SAW_PATH_SPEED))

    def test_lineas_mal_escritas_se_ignoran_con_aviso(self):
        for malo in (";sierra=1,2\n", ";sierra=a,b,c,d\n", ";sierra=1,2,3,4,5,6,7\n", ";sierra=1,2,3,4,-5\n",
                     ";sierra=1,2,3,4,5,0\n"):
            lv, salida = nivel_con(malo + "#..#\n")
            self.assertEqual(lv.saw_specs, [], msg=malo)
            self.assertIn("Aviso", salida, msg=malo)

    def test_varias_sierras(self):
        lv, _ = nivel_con(";sierra=2,2,0,0\n;sierra=5,2,3,0\n#.O.#\n")
        self.assertEqual(len(lv.saw_specs), 3)

    def test_se_puede_construir_el_Saw_desde_la_especificacion(self):
        lv, _ = nivel_con(";sierra=2,3,4,0,100\n#..#\n")
        cx, cy, r, dx, dy, v = lv.saw_specs[0]
        s = Saw(cx, cy, r, (dx, dy), v)
        for _ in range(int(1 / DT)):
            s.update(DT)
        self.assertAlmostEqual(s.pos.x, cx + 100, delta=2)


if __name__ == "__main__":
    unittest.main()
