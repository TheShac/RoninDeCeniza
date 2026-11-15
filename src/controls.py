"""Traducción de las entradas (teclado y mouse) a intenciones del Ronin. Funciones puras, fáciles de probar.

Reglas:
- El Ronin SIEMPRE mira hacia donde se mueve (A/D). El mouse nunca lo gira: el tajo y el shuriken salen hacia
  donde mira.
- Solo el desvío tiene dirección propia: indica hacia dónde se devuelve la flecha.
    * Clic derecho: hacia el cursor.
    * Tecla K: hacia la dirección de las teclas WASD que se mantengan (8 direcciones); sin ninguna, hacia donde mira.
"""
import math


def _unit(x, y):
    length = math.hypot(x, y)
    if length < 1e-9:
        return None
    return (x / length, y / length)


def mouse_aim(origin, target):
    """Dirección unitaria desde `origin` (el hombro del Ronin) hasta `target` (el cursor en el mundo)."""
    return _unit(target[0] - origin[0], target[1] - origin[1])


def keyboard_aim(move_x, up, down):
    """Dirección unitaria según las teclas mantenidas: x = D - A, y = S - W (en pantalla, y crece hacia abajo).

    Devuelve None si no hay ninguna (el desvío usa entonces la dirección en que mira el Ronin)."""
    return _unit(float(move_x), float(int(bool(down)) - int(bool(up))))


def jump_pressed(pressed):
    """Salto de este frame. Espacio siempre salta; W/flecha arriba saltan salvo que se pulsen junto con K
    (en ese caso W es la dirección del desvío, no un salto)."""
    return "jump" in pressed or ("up" in pressed and "parry" not in pressed)
