"""Configuración de la ventana (config.json en la carpeta del proyecto). Funciones puras, fáciles de probar.

El juego se dibuja siempre en un lienzo lógico de WIDTH x HEIGHT (960x544) y se escala a la ventana
manteniendo la proporción (con barras si sobra espacio). Así la jugabilidad es la misma en cualquier tamaño.

config.json:
  {"ancho": "auto", "alto": "auto", "pantalla_completa": false}
  - ancho / alto: píxeles de la ventana, o "auto" para ocupar la pantalla (menos el espacio de las barras
    de título y de tareas).
  - pantalla_completa: true para abrir a pantalla completa (F11 lo alterna en el juego).
"""
import json

DEFAULTS = {"ancho": "auto", "alto": "auto", "pantalla_completa": False}
MIN_SIZE = (480, 270)          # la ventana nunca baja de esto
AUTO_MARGIN = (0, 90)          # px que "auto" deja libres: barra de título y barra de tareas


def load_config(path):
    """Lee config.json. Si falta o está mal escrito, usa los valores por defecto (y avisa)."""
    cfg = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("debe ser un objeto { ... }")
        cfg.update({k: data[k] for k in DEFAULTS if k in data})
    except FileNotFoundError:
        pass
    except (ValueError, OSError) as error:
        print(f"Aviso: no se pudo leer {path} ({error}); se usa la configuración por defecto.")
    return cfg


def _dimension(value, auto, minimum):
    if isinstance(value, str) and value.strip().lower() == "auto":
        number = auto
    else:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = auto
        if number <= 0:
            number = auto
    return max(minimum, number)


def window_size(cfg, desktop):
    """Tamaño de la ventana en px según la configuración y el tamaño del escritorio (ancho, alto)."""
    auto_w, auto_h = desktop[0] - AUTO_MARGIN[0], desktop[1] - AUTO_MARGIN[1]
    return (_dimension(cfg.get("ancho"), auto_w, MIN_SIZE[0]), _dimension(cfg.get("alto"), auto_h, MIN_SIZE[1]))


def fit(window, logical):
    """Escala el lienzo lógico para que quepa en la ventana sin deformarse.

    scale = min(ancho_ventana / ancho_lógico, alto_ventana / alto_lógico)
    Devuelve (scale, (ancho, alto) escalado, (x, y) de la esquina para centrarlo)."""
    scale = min(window[0] / logical[0], window[1] / logical[1])
    size = (max(1, round(logical[0] * scale)), max(1, round(logical[1] * scale)))
    return scale, size, ((window[0] - size[0]) // 2, (window[1] - size[1]) // 2)


def to_logical(pos, scale, offset):
    """Convierte un punto de la ventana (p. ej. el mouse) a coordenadas del lienzo lógico."""
    return ((pos[0] - offset[0]) / scale, (pos[1] - offset[1]) / scale)
