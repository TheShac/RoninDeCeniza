"""Pruebas del suelo de lodo (`=`): se camina más lento y se salta menos."""
import contextlib, io, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from enemy import Walker, Runner
from level import Level
from player import Player, InputState

DT = 1 / 60
T = S.TILE


def nivel(fila_suelo):
    filas = ["#" + "." * 30 + "#"] * 10 + [fila_suelo, "#" * 32]
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "n.txt"
        ruta.write_text(";modo=pruebas\n" + "\n".join(filas) + "\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            return Level(ruta)


NORMAL = "#" * 32
LODO = "#" + "=" * 30 + "#"
SUELO_Y = 10 * T          # cara superior de la fila 10 (suelo)


def jugador(lv, x=3 * T):
    p = Player(x, SUELO_Y - S.PLAYER_SIZE[1])
    for _ in range(20):
        p.update(DT, InputState(), lv)
    return p


def correr(lv, frames=60):
    p = jugador(lv)
    for _ in range(frames):
        p.update(DT, InputState(move_x=1), lv)
    return p.vel.x


def altura_salto(lv):
    p = jugador(lv, 10 * T)
    y0 = p.pos.y
    p.update(DT, InputState(jump_pressed=True, jump_held=True), lv)
    top = p.pos.y
    for _ in range(90):
        p.update(DT, InputState(jump_held=True), lv)
        top = min(top, p.pos.y)
    return y0 - top


class TestLodo(unittest.TestCase):
    def test_se_lee_como_bloque_solido(self):
        lv = nivel(LODO)
        self.assertEqual(len(lv.mud), 30)
        self.assertTrue(all(any(r is m for r in lv.solids) for m in lv.mud))

    def test_on_mud_solo_con_los_pies_encima(self):
        lv = nivel(LODO)
        self.assertTrue(lv.on_mud((5 * T, SUELO_Y - 58, 24, 58)))
        self.assertFalse(lv.on_mud((5 * T, 3 * T, 24, 58)))                 # en el aire
        self.assertFalse(nivel(NORMAL).on_mud((5 * T, SUELO_Y - 58, 24, 58)))

    def test_velocidad_maxima_reducida(self):
        v_n, v_l = correr(nivel(NORMAL)), correr(nivel(LODO))
        self.assertAlmostEqual(v_n, S.RUN_SPEED, delta=1)
        self.assertAlmostEqual(v_l, S.RUN_SPEED * S.MUD_SPEED_MULT, delta=1)

    def test_salto_mas_bajo_en_lodo(self):
        h_n, h_l = altura_salto(nivel(NORMAL)), altura_salto(nivel(LODO))
        esperado = (S.JUMP_SPEED * S.MUD_JUMP_MULT) ** 2 / (2 * S.GRAVITY)
        self.assertLess(h_l, h_n * 0.7)
        self.assertAlmostEqual(h_l, esperado, delta=esperado * 0.12)

    def test_el_lodo_no_cambia_el_salto_fuera_de_el(self):
        lv = nivel("#" + "=" * 5 + "#" * 26)
        self.assertAlmostEqual(altura_salto(lv), altura_salto(nivel(NORMAL)), delta=1)   # en x = 10 casillas ya es suelo normal

    def test_zombi_camina_mas_lento_en_lodo(self):
        def vmax(lv):
            z = Walker("aldeano", 10 * T, SUELO_Y)
            lejos = Player(30 * T, 0)
            for _ in range(60):
                z.update(DT, lv, lejos)
            return max(abs(z.vel.x), 0)
        self.assertLessEqual(vmax(nivel(LODO)), S.WALKER_PATROL_SPEED * S.MUD_SPEED_MULT + 0.5)
        self.assertGreater(vmax(nivel(NORMAL)), S.WALKER_PATROL_SPEED * 0.9)

    def test_corredor_embiste_mas_lento_en_lodo(self):
        def vmax(lv):
            r = Runner("campesino", 10 * T, SUELO_Y)
            j = Player(14 * T, SUELO_Y - 58)
            m = 0.0
            for _ in range(60):
                r.update(DT, lv, j)
                m = max(m, abs(r.vel.x))
            return m
        self.assertLessEqual(vmax(nivel(LODO)), S.RUNNER_MAX_SPEED * S.MUD_SPEED_MULT + 1)
        self.assertGreater(vmax(nivel(NORMAL)), S.RUNNER_MAX_SPEED * 0.8)


if __name__ == "__main__":
    unittest.main()
