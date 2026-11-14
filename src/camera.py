"""Cámara con seguimiento suave. Dibujar = posición del mundo - posición de la cámara."""
from settings import WIDTH, HEIGHT


class Camera:
    def __init__(self, level_w, level_h):
        self.level_w, self.level_h = level_w, level_h
        self.x = 0.0
        self.y = 0.0

    def update(self, target_x, target_y, dt):
        goal_x = target_x - WIDTH / 2
        goal_y = target_y - HEIGHT / 2
        k = min(1.0, 8.0 * dt)                  # suavizado: se acerca una fracción por frame
        self.x += (goal_x - self.x) * k
        self.y += (goal_y - self.y) * k
        self.x = max(0.0, min(self.x, max(0.0, self.level_w - WIDTH)))
        self.y = max(0.0, min(self.y, max(0.0, self.level_h - HEIGHT)))
