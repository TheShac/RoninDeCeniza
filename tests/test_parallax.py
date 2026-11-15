"""Pruebas del fondo con parallax: fórmula de desplazamiento, repetición en bucle y capas generadas."""
import contextlib, io, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import settings as S
from level import Level
from parallax import FONDOS, FONDOS_DIR, Layer, Parallax, layer_offset, tile_positions


class Imagen:
    def __init__(self, w): self.w = w
    def get_width(self): return self.w


class Superficie:
    def __init__(self, w=960): self.w, self.blits, self.fills = w, [], []
    def get_width(self): return self.w
    def blit(self, img, pos): self.blits.append((img, pos))
    def fill(self, color): self.fills.append(color)


class TestFormula(unittest.TestCase):
    def test_factor_cero_es_fijo_y_uno_sigue_a_la_camara(self):
        self.assertEqual(layer_offset(1234, 0.0) + 0, 0)
        self.assertEqual(layer_offset(1234, 1.0), -1234)

    def test_proporcional_al_factor(self):
        self.assertAlmostEqual(layer_offset(1000, 0.25), -250)
        self.assertAlmostEqual(layer_offset(1000, 0.5) / layer_offset(1000, 0.25), 2.0)

    def test_lo_lejano_se_mueve_menos(self):
        factores = [f for _, f, _, _ in FONDOS["aldea"]]
        self.assertEqual(factores, sorted(factores))
        self.assertTrue(all(0.0 <= f < 1.0 for f in factores))
        self.assertEqual(factores[0], 0.0)


class TestBucle(unittest.TestCase):
    def test_cubre_toda_la_pantalla_sin_huecos(self):
        for w in (500, 960, 1280, 1536):
            for off in range(-5000, 400, 37):
                xs = tile_positions(off, w, 960)
                self.assertLessEqual(xs[0], 0)
                self.assertGreater(xs[-1] + w, 960 - 1e-9)
                self.assertTrue(all(b - a == w for a, b in zip(xs, xs[1:])))

    def test_dar_una_vuelta_completa_no_cambia_nada(self):
        self.assertEqual(tile_positions(-300, 1280, 960), tile_positions(-300 - 1280 * 3, 1280, 960))

    def test_ejemplo_concreto(self):
        self.assertEqual(tile_positions(-300, 1280, 960), [-300])
        self.assertEqual(tile_positions(-1000, 1280, 960), [-1000, 280])
        self.assertEqual(tile_positions(0, 1280, 960), [0])
        self.assertEqual(tile_positions(100, 1280, 960), [-1180, 100])

    def test_ancho_invalido(self):
        self.assertEqual(tile_positions(0, 0, 960), [])


class TestCapa(unittest.TestCase):
    def test_dibuja_en_bucle_con_el_desplazamiento_del_factor(self):
        s = Superficie()
        Layer(Imagen(1280), 0.5, y=100, loop=True).draw(s, 2000, 0)       # offset = -1000
        self.assertEqual([p for _, p in s.blits], [(-1000 + 0, 100), (280, 100)])

    def test_sin_bucle_una_sola_copia(self):
        s = Superficie()
        Layer(Imagen(960), 0.0, 0, loop=False).draw(s, 5000, 0)
        self.assertEqual([p for _, p in s.blits], [(0, 0)])
        s = Superficie()
        Layer(Imagen(960), 0.1, 0, loop=False).draw(s, 500, 0)
        self.assertEqual([p for _, p in s.blits], [(-50, 0)])

    def test_tambien_se_desplaza_en_vertical(self):
        s = Superficie()
        Layer(Imagen(2000), 0.5, y=200).draw(s, 0, 40)
        self.assertEqual(s.blits[0][1][1], 180)

    def test_parallax_desactivado_solo_pinta_el_papel(self):
        s = Superficie()
        p = Parallax([Layer(Imagen(960), 0.5)])
        p.enabled = False
        p.draw(s, 100, 0)
        self.assertEqual(s.fills, [S.PAPER])
        self.assertEqual(s.blits, [])
        p.enabled = True
        p.draw(s, 100, 0)
        self.assertTrue(s.blits)

    def test_capas_en_orden_de_atras_hacia_delante(self):
        s = Superficie()
        a, b = Imagen(960), Imagen(960)
        Parallax([Layer(a, 0.1), Layer(b, 0.5)]).draw(s, 0, 0)
        self.assertEqual([img for img, _ in s.blits], [a, b])

    def test_fondo_desconocido_o_sin_archivos_no_rompe(self):
        self.assertEqual(Parallax.load("no_existe").layers, [])


class TestNivel(unittest.TestCase):
    def test_parametro_fondo(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d) / "n.txt"
            r.write_text(";fondo=aldea\n#..#\n####\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(Level(r).background, "aldea")
            r.write_text("#..#\n####\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(Level(r).background)

    def test_el_nivel_1_usa_el_fondo_aldea(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(Level(S.LEVELS_DIR / "nivel1.txt").background, "aldea")


class TestCapasGeneradas(unittest.TestCase):
    def setUp(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow no está instalado")
        self.Image = Image

    def test_existen_todos_los_archivos(self):
        for file, _, _, _ in FONDOS["aldea"]:
            self.assertTrue((FONDOS_DIR / f"aldea_{file}.png").exists(), msg=file)

    def test_las_capas_en_bucle_enlazan_por_los_bordes(self):
        for file, _, _, loop in FONDOS["aldea"]:
            img = self.Image.open(FONDOS_DIR / f"aldea_{file}.png").convert("RGBA")
            w, h = img.size
            if not loop:
                continue
            self.assertGreaterEqual(w, S.WIDTH, msg=file)
            izq = [img.getpixel((0, y)) for y in range(h)]
            der = [img.getpixel((w - 1, y)) for y in range(h)]
            dif = sum(abs(a - b) for p, q in zip(izq, der) for a, b in zip(p, q)) / (h * 4)
            self.assertLess(dif, 6.0, msg=f"{file}: borde con salto ({dif:.1f})")


if __name__ == "__main__":
    unittest.main()
