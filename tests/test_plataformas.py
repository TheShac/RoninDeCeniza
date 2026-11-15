"""Pruebas de las plataformas móviles, el hielo y los rótulos del nivel de pruebas."""
import contextlib
import io
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from enemy import Walker
from level import Level
from player import Player, InputState

DT = 1 / 60
T = S.TILE
SALA = ["#..............#"] * 11 + ["################"]          # 16x12 casillas, el suelo está en y = 352
SUELO = 11 * T


def nivel(params="", filas=SALA):
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "n.txt"
        ruta.write_text(";modo=pruebas\n" + params + "\n" + "\n".join(filas) + "\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            lv = Level(ruta)
    return lv, salida.getvalue()


def avanzar(lv, entidades, segundos, inp=None):
    for _ in range(int(round(segundos / DT))):
        lv.update_platforms(DT, entidades)
        for e in entidades:
            if isinstance(e, Player):
                e.update(DT, inp or InputState(), lv)


def sobre(lv, plat, dx=8):
    """Un Ronin de pie sobre la plataforma `plat` (asentado)."""
    p = Player(plat.rect.x + dx, plat.rect.top - S.PLAYER_SIZE[1])
    avanzar(lv, [p], 0.25)
    assert p.on_ground
    return p


class TestLecturaDelNivel(unittest.TestCase):
    def test_plataforma_lineal(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,6,0,60")
        self.assertEqual(len(lv.platforms), 1)
        p = lv.platforms[0]
        self.assertEqual((p.kind, p.rect.x, p.rect.y, p.rect.w, p.rect.h), ("linear", 3 * T, 8 * T, 3 * T, S.PLATFORM_H))
        self.assertEqual((p.path, p.speed), ((6 * T, 0.0), 60.0))

    def test_valores_por_defecto(self):
        lv, _ = nivel(";plataforma=lineal,3,8,2,0,4\n;plataforma=circular,8,6,2,3")
        a, b = lv.platforms
        self.assertEqual(a.speed, S.PLATFORM_SPEED)
        self.assertEqual(b.omega, S.PLATFORM_OMEGA)

    def test_plataforma_circular_parte_a_la_derecha_del_centro(self):
        lv, _ = nivel(";plataforma=circular,8,6,2,3,1.0")
        p = lv.platforms[0]
        self.assertEqual(p.kind, "circular")
        self.assertEqual(p.radius, 3 * T)
        cx, cy = 8 * T + T / 2, 6 * T + T / 2
        self.assertEqual(p.rect.center, (round(cx + 3 * T), round(cy)))

    def test_la_plataforma_comparte_la_lista_de_solidos(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,6,0")
        p = lv.platforms[0]
        self.assertTrue(any(r is p.rect for r in lv.solids))
        self.assertFalse(any(r is p.rect for r in lv.static_solids))
        self.assertEqual(len(lv.static_solids), len(lv.solids) - 1)

    def test_lineas_mal_escritas_se_ignoran_con_aviso(self):
        for malo in (";plataforma=rara,1,2,3", ";plataforma=lineal,1,2", ";plataforma=lineal,a,b,c,d,e",
                     ";plataforma=lineal,1,2,0,3,0", ";plataforma=circular,1,2,2,0", ";plataforma=circular,1,2,2",
                     ";plataforma=lineal,1,2,2,3,0,-5"):
            lv, salida = nivel(malo)
            self.assertEqual(lv.platforms, [], msg=malo)
            self.assertIn("Aviso", salida, msg=malo)

    def test_rotulos(self):
        lv, _ = nivel(";letrero=5,2,ZONA 1: zombis, y mas")
        self.assertEqual(lv.signs, [(5 * T, 2 * T, "ZONA 1: zombis, y mas")])
        lv2, salida = nivel(";letrero=x,2,hola")
        self.assertEqual(lv2.signs, [])
        self.assertIn("Aviso", salida)


class TestMovimiento(unittest.TestCase):
    def test_lineal_va_y_viene(self):
        lv, _ = nivel(";plataforma=lineal,3,8,2,4,0,64")          # 128 px a 64 px/s: 2 s de ida
        p = lv.platforms[0]
        xs = []
        for _ in range(int(5 / DT)):
            lv.update_platforms(DT, [])
            xs.append(p.rect.x)
        self.assertGreaterEqual(min(xs), 3 * T - 1)
        self.assertLessEqual(max(xs), 3 * T + 128 + 1)
        self.assertAlmostEqual(max(xs), 3 * T + 128, delta=2)
        self.assertAlmostEqual(min(xs[130:]), 3 * T, delta=2)

    def test_velocidad_de_la_plataforma(self):
        lv, _ = nivel(";plataforma=lineal,3,8,2,6,0,90")
        lv.update_platforms(DT, [])
        for _ in range(20):
            lv.update_platforms(DT, [])
        self.assertAlmostEqual(lv.platforms[0].vel.x, 90.0, delta=0.01)     # velocidad exacta, no la del rect entero
        self.assertEqual(lv.platforms[0].linear_speed, 90.0)

    def test_circular_mantiene_el_radio_y_gira_con_omega(self):
        lv, _ = nivel(";plataforma=circular,8,6,2,3,1.5")
        p = lv.platforms[0]
        cx, cy = 8 * T + T / 2, 6 * T + T / 2
        angulos = []
        for _ in range(int(2 / DT)):
            lv.update_platforms(DT, [])
            x, y = p.rect.center
            self.assertAlmostEqual(math.hypot(x - cx, y - cy), 3 * T, delta=1.5)
            angulos.append(math.atan2(y - cy, x - cx))
        # a los 2 s lleva 1,5 * 2 = 3 rad
        self.assertAlmostEqual(angulos[-1] % (2 * math.pi), 3.0, delta=0.05)
        self.assertEqual(p.linear_speed, 1.5 * 3 * T)

    def test_circular_da_la_vuelta_completa(self):
        lv, _ = nivel(";plataforma=circular,8,6,2,3,2.0")
        p = lv.platforms[0]
        inicio = p.rect.center
        for _ in range(int((2 * math.pi / 2.0) / DT)):
            lv.update_platforms(DT, [])
        self.assertAlmostEqual(p.rect.centerx, inicio[0], delta=4)
        self.assertAlmostEqual(p.rect.centery, inicio[1], delta=4)

    def test_sin_recorrido_queda_quieta(self):
        lv, _ = nivel(";plataforma=lineal,3,8,2,0,0")
        pos = lv.platforms[0].rect.topleft
        for _ in range(60):
            lv.update_platforms(DT, [])
        self.assertEqual(lv.platforms[0].rect.topleft, pos)


class TestLlevarEncima(unittest.TestCase):
    def test_es_solida_y_se_puede_pisar(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,0,0")
        p = Player(3 * T + 20, 5 * T)                                       # cae sobre ella
        avanzar(lv, [p], 1.0)
        self.assertTrue(p.on_ground)
        self.assertAlmostEqual(p.pos.y + p.size[1], 8 * T, delta=0.01)

    def test_la_lleva_hacia_los_lados(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,6,0,60")
        plat = lv.platforms[0]
        p = sobre(lv, plat)
        x0, px0 = p.pos.x, plat.rect.x
        avanzar(lv, [p], 1.5)
        self.assertGreater(plat.rect.x - px0, 80)
        self.assertAlmostEqual(p.pos.x - x0, plat.rect.x - px0, delta=2)
        self.assertTrue(p.on_ground)
        self.assertAlmostEqual(p.pos.y + p.size[1], plat.rect.top, delta=0.01)

    def test_en_vertical_sube_y_baja_pegado_a_la_plataforma(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,0,-4,60")                   # sube 4 casillas y vuelve
        plat = lv.platforms[0]
        p = sobre(lv, plat)
        for _ in range(int(5 / DT)):
            avanzar(lv, [p], DT)
            self.assertAlmostEqual(p.pos.y + p.size[1], plat.rect.top, delta=1.01)
            self.assertTrue(p.on_ground)
        self.assertLess(min(plat.rect.y for _ in [0]), 8 * T + 1)

    def test_baja_con_la_plataforma(self):
        lv, _ = nivel(";plataforma=lineal,3,3,3,0,4,60")
        plat = lv.platforms[0]
        p = sobre(lv, plat)
        y0 = p.pos.y
        avanzar(lv, [p], 1.5)
        self.assertGreater(p.pos.y - y0, 60)
        self.assertAlmostEqual(p.pos.y + p.size[1], plat.rect.top, delta=1.01)

    def test_sobre_la_circular(self):
        lv, _ = nivel(";plataforma=circular,8,6,2,2,1.0")
        plat = lv.platforms[0]
        p = sobre(lv, plat, dx=24)
        for _ in range(int(4 / DT)):
            avanzar(lv, [p], DT)
            self.assertTrue(p.on_ground)
            self.assertAlmostEqual(p.pos.y + p.size[1], plat.rect.top, delta=1.6)

    def test_quien_esta_al_lado_no_es_llevado(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,0,-4,60")
        p = Player(8 * T, SUELO - S.PLAYER_SIZE[1])                          # en el suelo, lejos de la plataforma
        avanzar(lv, [p], 0.3)
        y0 = p.pos.y
        avanzar(lv, [p], 1.5)
        self.assertAlmostEqual(p.pos.y, y0, places=3)

    def test_un_zombi_tambien_va_encima(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,6,0,60")
        plat = lv.platforms[0]
        z = Walker("aldeano", plat.rect.centerx, plat.rect.top)
        for _ in range(30):
            lv.update_platforms(DT, [z])
            z.update(DT, lv, Player(1500, 0))
        z.vel.x = 0.0
        self.assertTrue(z.on_ground)
        x0, px0 = z.pos.x, plat.rect.x
        for _ in range(60):                               # solo la plataforma: el zombi no se mueve por su cuenta
            lv.update_platforms(DT, [z])
        self.assertAlmostEqual(z.pos.x - x0, plat.rect.x - px0, delta=3)
        self.assertTrue(z.on_ground)

    def test_la_pared_detiene_a_quien_va_encima(self):
        filas = list(SALA)
        filas[7] = "#.........#....#"                                        # pared en la columna 10, filas 6 a 8
        filas[6] = "#.........#....#"
        filas[8] = "#.........#....#"
        lv, _ = nivel(";plataforma=lineal,3,8,4,8,0,100", filas)
        plat = lv.platforms[0]
        p = sobre(lv, plat, dx=60)
        avanzar(lv, [p], 3.0)
        self.assertLessEqual(p.pos.x + p.size[0], 10 * T + 0.01)             # no atraviesa la pared


class TestMomentum(unittest.TestCase):
    def test_saltar_de_una_plataforma_conserva_su_velocidad(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,6,0,60")
        plat = lv.platforms[0]
        p = sobre(lv, plat)
        avanzar(lv, [p], 0.5)
        lv.update_platforms(DT, [p])
        self.assertGreater(p.ride_vel[0], 40)
        p.update(DT, InputState(jump_pressed=True, jump_held=True), lv)
        self.assertAlmostEqual(p.vel.x, p.ride_vel[0], delta=1.0)
        self.assertLess(p.vel.y, -S.JUMP_SPEED + 100)

    def test_en_el_suelo_no_hereda_nada(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,6,0,60")
        p = Player(10 * T, SUELO - S.PLAYER_SIZE[1])
        avanzar(lv, [p], 0.3)
        self.assertEqual(p.ride_vel, (0.0, 0.0))
        p.update(DT, InputState(jump_pressed=True, jump_held=True), lv)
        self.assertEqual(p.vel.x, 0.0)

    def test_al_bajarse_se_reinicia_la_velocidad_heredada(self):
        lv, _ = nivel(";plataforma=lineal,3,8,3,6,0,60")
        plat = lv.platforms[0]
        p = sobre(lv, plat)
        avanzar(lv, [p], 0.3)
        self.assertNotEqual(p.ride_vel, (0.0, 0.0))
        p.pos.update(10 * T, SUELO - p.size[1])                             # lo pasamos al suelo
        avanzar(lv, [p], 0.3)
        self.assertEqual(p.ride_vel, (0.0, 0.0))


class TestEmpujeYAplastamiento(unittest.TestCase):
    def test_la_plataforma_empuja_a_quien_se_cruza(self):
        lv, _ = nivel(";plataforma=lineal,2,9,3,6,0,90")                    # cara superior en y = 288
        plat = lv.platforms[0]
        p = Player(6 * T, SUELO - S.PLAYER_SIZE[1])                         # en el suelo, a la altura de la plataforma
        avanzar(lv, [p], 0.3)
        self.assertGreater(p.pos.y + p.size[1], plat.rect.top)
        inicio = p.pos.x
        avanzar(lv, [p], 1.2)
        self.assertGreater(p.pos.x, inicio + 10)                           # lo empujó hacia delante
        self.assertFalse(plat.rect.colliderect(pygame_rect(p)))

    def test_aplastado_contra_una_pared_recibe_dano_y_queda_encima(self):
        filas = list(SALA)
        for r in (7, 8, 9, 10):
            filas[r] = "#........#.....#"                                   # pared en la columna 9
        lv, _ = nivel(";plataforma=lineal,2,9,3,6,0,120", filas)
        plat = lv.platforms[0]
        p = Player(8 * T, SUELO - S.PLAYER_SIZE[1])
        avanzar(lv, [p], 0.3)
        vida = p.health
        avanzar(lv, [p], 1.5)
        self.assertEqual(p.health, vida - 1)
        self.assertFalse(plat.rect.colliderect(pygame_rect(p)))

    def test_nunca_queda_atrapado_dentro_de_la_plataforma(self):
        lv, _ = nivel(";plataforma=lineal,2,9,3,10,0,200")
        p = Player(8 * T, SUELO - S.PLAYER_SIZE[1])
        for _ in range(int(4 / DT)):
            avanzar(lv, [p], DT)
            self.assertFalse(lv.platforms[0].rect.colliderect(pygame_rect(p)) and
                             abs(p.pos.y + p.size[1] - lv.platforms[0].rect.top) > 1.01)


def pygame_rect(p):
    import pygame
    return pygame.Rect(round(p.pos.x), round(p.pos.y), p.size[0], p.size[1])


HIELO = ["#..............#"] * 10 + ["#..............#", "#~~~~~~~~~~~~~~#"][:1] + ["################"]
SALA_HIELO = ["#..............#"] * 10 + ["#~~~~~~~~~~~~~~#", "################"]


class TestHielo(unittest.TestCase):
    def jugador(self, lv, x=3 * T):
        p = Player(x, 10 * T - S.PLAYER_SIZE[1] + T)                         # sobre la fila 11
        p.pos.update(x, 11 * T - S.PLAYER_SIZE[1] - T)
        return p

    def test_el_hielo_es_solido_y_se_puede_pisar(self):
        lv, _ = nivel("", SALA_HIELO)
        self.assertEqual(len(lv.ice), 14)
        p = Player(5 * T, 3 * T)
        for _ in range(90):
            p.update(DT, InputState(), lv)
        self.assertTrue(p.on_ground)
        self.assertAlmostEqual(p.pos.y + p.size[1], 10 * T + T - T, delta=T + 0.01)

    def test_agarre_sobre_hielo_y_sobre_suelo_normal(self):
        lv, _ = nivel("", SALA_HIELO)
        suelo_hielo = (5 * T, 10 * T - 58, 24, 58)
        self.assertAlmostEqual(lv.grip_under(suelo_hielo), lv.grip * S.ICE_GRIP)
        lv2, _ = nivel("", SALA)
        self.assertEqual(lv2.grip_under((5 * T, SUELO - 58, 24, 58)), lv2.grip)

    def test_el_agarre_del_nivel_se_combina_con_el_hielo(self):
        lv, _ = nivel(";grip=0.5", SALA_HIELO)
        self.assertAlmostEqual(lv.grip_under((5 * T, 10 * T - 58, 24, 58)), 0.5 * S.ICE_GRIP)

    def test_basta_un_pie_sobre_hielo(self):
        filas = ["#..............#"] * 10 + ["#~~#############", "################"]
        lv, _ = nivel("", filas)
        # el pie izquierdo sobre el hielo (col. 1-2), el derecho fuera
        self.assertAlmostEqual(lv.grip_under((3 * T - 10, 10 * T - 58, 24, 58)), lv.grip * S.ICE_GRIP)
        self.assertEqual(lv.grip_under((5 * T, 10 * T - 58, 24, 58)), lv.grip)

    def test_en_el_aire_no_hay_hielo_bajo_los_pies(self):
        lv, _ = nivel("", SALA_HIELO)
        self.assertEqual(lv.grip_under((5 * T, 3 * T, 24, 58)), lv.grip)

    def test_cuesta_mas_arrancar_y_frenar_sobre_hielo(self):
        def correr_y_frenar(filas):
            lv, _ = nivel("", filas)
            p = Player(2 * T, 10 * T - 58)
            for _ in range(30):
                p.update(DT, InputState(), lv)
            x_ini = p.pos.x
            for _ in range(15):                                              # 0,25 s corriendo hacia la derecha
                p.update(DT, InputState(move_x=1), lv)
            v = p.vel.x
            x0 = p.pos.x
            for _ in range(120):                                             # suelta: ¿cuánto se desliza?
                p.update(DT, InputState(), lv)
            return v, p.pos.x - x0
        v_suelo, desliza_suelo = correr_y_frenar(["#..............#"] * 10 + ["################"] * 2)
        v_hielo, desliza_hielo = correr_y_frenar(["#..............#"] * 10 + ["#~~~~~~~~~~~~~~#", "################"])
        self.assertLess(v_hielo, v_suelo * 0.5)                              # arranca mucho más lento
        self.assertGreater(desliza_hielo / max(v_hielo, 1), desliza_suelo / max(v_suelo, 1))

    def test_un_zombi_tambien_resbala(self):
        def aceleracion(filas):
            lv, _ = nivel("", filas)
            z = Walker("aldeano", 6 * T, 10 * T)
            for _ in range(30):
                z.update(DT, lv, Player(1500, 0))
            z.vel.x = 0.0
            z.facing = 1
            z._dt = DT
            z._walk(lv, S.WALKER_PATROL_SPEED, False)
            return z.vel.x
        normal = aceleracion(["#..............#"] * 10 + ["################"] * 2)
        hielo = aceleracion(["#..............#"] * 10 + ["#~~~~~~~~~~~~~~#", "################"])
        self.assertAlmostEqual(hielo, normal * S.ICE_GRIP, places=6)

    def test_la_letra_tilde_no_rompe_a_los_demas_bloques(self):
        lv, _ = nivel("", ["#~.#", "####"])
        self.assertEqual(len(lv.solids), 7)
        self.assertEqual(len(lv.ice), 1)


if __name__ == "__main__":
    unittest.main()
