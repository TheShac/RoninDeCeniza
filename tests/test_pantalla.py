"""Pruebas del tamaño de la ventana (config.py) y de la galería de animaciones (scroll y zoom)."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tools"))

import config
import settings as S
import ver_animaciones as galeria


class TestTamanoDeVentana(unittest.TestCase):
    def test_auto_usa_la_pantalla_menos_el_margen(self):
        cfg = dict(config.DEFAULTS)
        self.assertEqual(config.window_size(cfg, (1920, 1080)),
                         (1920 - config.AUTO_MARGIN[0], 1080 - config.AUTO_MARGIN[1]))

    def test_ancho_y_alto_configurables_por_separado(self):
        self.assertEqual(config.window_size({"ancho": 1280, "alto": "auto"}, (1920, 1080)), (1280, 990))
        self.assertEqual(config.window_size({"ancho": "auto", "alto": 600}, (1920, 1080)), (1920, 600))
        self.assertEqual(config.window_size({"ancho": "1000", "alto": "700"}, (1920, 1080)), (1000, 700))

    def test_valores_invalidos_vuelven_a_auto(self):
        for malo in (0, -5, "abc", None, [], 12.0 - 12):
            self.assertEqual(config.window_size({"ancho": malo, "alto": malo}, (1600, 900)), (1600, 810), msg=repr(malo))

    def test_nunca_baja_del_minimo(self):
        self.assertEqual(config.window_size({"ancho": 100, "alto": 50}, (1920, 1080)), config.MIN_SIZE)

    def test_auto_en_pantalla_diminuta_respeta_el_minimo(self):
        w, h = config.window_size(dict(config.DEFAULTS), (400, 300))
        self.assertGreaterEqual(w, config.MIN_SIZE[0])
        self.assertGreaterEqual(h, config.MIN_SIZE[1])


class TestAjusteAlLienzo(unittest.TestCase):
    LOGICO = (S.WIDTH, S.HEIGHT)

    def test_misma_proporcion_llena_la_ventana(self):
        scale, size, offset = config.fit((1920, 1088), self.LOGICO)
        self.assertAlmostEqual(scale, 2.0)
        self.assertEqual(size, (1920, 1088))
        self.assertEqual(offset, (0, 0))

    def test_ventana_mas_ancha_deja_barras_a_los_lados(self):
        scale, size, offset = config.fit((2000, 544), self.LOGICO)
        self.assertAlmostEqual(scale, 1.0)
        self.assertEqual(size, (960, 544))
        self.assertEqual(offset, ((2000 - 960) // 2, 0))

    def test_ventana_mas_alta_deja_barras_arriba_y_abajo(self):
        scale, size, offset = config.fit((960, 1000), self.LOGICO)
        self.assertAlmostEqual(scale, 1.0)
        self.assertEqual(offset, (0, (1000 - 544) // 2))

    def test_nunca_deforma(self):
        for ventana in ((1366, 768), (800, 600), (2560, 1080), (700, 900)):
            scale, size, _ = config.fit(ventana, self.LOGICO)
            self.assertLessEqual(size[0], ventana[0])
            self.assertLessEqual(size[1], ventana[1])
            self.assertAlmostEqual(size[0] / size[1], self.LOGICO[0] / self.LOGICO[1], places=2)

    def test_el_mouse_vuelve_a_coordenadas_del_lienzo(self):
        scale, size, offset = config.fit((2000, 1088), self.LOGICO)
        centro = (offset[0] + size[0] / 2, offset[1] + size[1] / 2)
        x, y = config.to_logical(centro, scale, offset)
        self.assertAlmostEqual(x, self.LOGICO[0] / 2, delta=0.6)
        self.assertAlmostEqual(y, self.LOGICO[1] / 2, delta=0.6)
        self.assertEqual(config.to_logical(offset, scale, offset), (0.0, 0.0))

    def test_esquina_inferior_derecha_del_lienzo(self):
        scale, size, offset = config.fit((1000, 900), self.LOGICO)
        x, y = config.to_logical((offset[0] + size[0], offset[1] + size[1]), scale, offset)
        self.assertAlmostEqual(x, self.LOGICO[0], delta=1.0)
        self.assertAlmostEqual(y, self.LOGICO[1], delta=1.0)


class TestLeerConfig(unittest.TestCase):
    def leer(self, texto):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "config.json"
            if texto is not None:
                ruta.write_text(texto, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):          # silencia el aviso de archivo roto
                return config.load_config(ruta)

    def test_sin_archivo_usa_los_valores_por_defecto(self):
        self.assertEqual(self.leer(None), config.DEFAULTS)

    def test_lee_ancho_alto_y_pantalla_completa(self):
        cfg = self.leer('{"ancho": 1280, "alto": 720, "pantalla_completa": true}')
        self.assertEqual((cfg["ancho"], cfg["alto"], cfg["pantalla_completa"]), (1280, 720, True))

    def test_lo_que_falta_se_completa_y_lo_desconocido_se_ignora(self):
        cfg = self.leer('{"ancho": 800, "otra_cosa": 1}')
        self.assertEqual(cfg["ancho"], 800)
        self.assertEqual(cfg["alto"], "auto")
        self.assertNotIn("otra_cosa", cfg)

    def test_archivo_roto_no_rompe_el_juego(self):
        for malo in ("{ esto no es json", "[1, 2, 3]", ""):
            self.assertEqual(self.leer(malo), config.DEFAULTS, msg=repr(malo))

    def test_el_config_json_del_proyecto_es_valido(self):
        cfg = config.load_config(S.BASE_DIR / "config.json")
        self.assertEqual(set(cfg), set(config.DEFAULTS))


def fila(*tamanos):
    return [("v", f"a{i}", SimpleNamespace(frames=[SimpleNamespace(get_width=lambda w=w: w, get_height=lambda h=h: h)],
                                           fps=5, loop=True)) for i, (w, h) in enumerate(tamanos)]


class TestGaleria(unittest.TestCase):
    def test_zoom_maximo_si_caben(self):
        m = galeria.medidas([fila((96, 96)) * 1], (1920, 1080))
        self.assertEqual(m["zoom"], galeria.MAX_ZOOM)
        self.assertEqual(m["cell_w"], 192)

    def test_el_zoom_baja_si_no_caben_a_lo_ancho(self):
        rows = [fila((160, 128), (160, 128), (160, 128), (160, 128), (160, 128))]      # 5 cuadros del hinchado
        m = galeria.medidas(rows, (1280, 720))
        self.assertLess(m["zoom"], galeria.MAX_ZOOM)
        self.assertLessEqual(m["win"][0], 1280 - galeria.MARGIN[0])

    def test_la_ventana_no_supera_la_pantalla_en_alto(self):
        rows = [fila((96, 96), (96, 96))] * 12                                        # muchas filas
        m = galeria.medidas(rows, (1920, 1080))
        self.assertGreater(m["content_h"], 1080)
        self.assertLessEqual(m["win"][1], 1080 - galeria.MARGIN[1])

    def test_si_cabe_todo_la_ventana_es_justa(self):
        rows = [fila((96, 96))]
        m = galeria.medidas(rows, (1920, 1080))
        self.assertEqual(m["win"][1], max(200, m["content_h"]))

    def test_celda_usa_el_cuadro_mas_grande(self):
        rows = [fila((96, 96), (160, 128))]
        m = galeria.medidas(rows, (1920, 1080))
        self.assertEqual((m["cell_w"], m["cell_h"]), (320, 256))

    def test_scroll_se_mantiene_en_rango(self):
        self.assertEqual(galeria.clamp_scroll(-50, 1000, 400), 0)
        self.assertEqual(galeria.clamp_scroll(250, 1000, 400), 250)
        self.assertEqual(galeria.clamp_scroll(9999, 1000, 400), 600)
        self.assertEqual(galeria.clamp_scroll(80, 300, 400), 0)         # todo cabe: no hay scroll


if __name__ == "__main__":
    unittest.main()
