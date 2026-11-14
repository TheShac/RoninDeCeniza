"""Bucle principal: eventos -> actualizar (con dt) -> dibujar."""
import pygame

import settings as S
from animation import Animator, load_ronin_animations
from camera import Camera
from level import Level
from player import Player, InputState


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        pygame.display.set_caption("Ronin de Ceniza")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.running = True
        self.debug = False
        self.ronin_animations = load_ronin_animations()
        self.load_level(S.LEVELS_DIR / "nivel1.txt")

    def load_level(self, path):
        self.level = Level(path)
        self.player = Player(*self.level.spawn)
        self.projectiles = []
        if self.ronin_animations:
            self.player.animator = Animator(self.ronin_animations)
        self.camera = Camera(self.level.width, self.level.height)

    # ------------------------------------------------------------------ bucle
    def run(self):
        while self.running:
            dt = min(self.clock.tick(S.FPS) / 1000.0, S.MAX_DT)   # delta time en segundos
            pressed = self.handle_events()
            self.update(dt, self.read_input(pressed))
            self.draw()
        pygame.quit()

    def handle_events(self):
        """Devuelve el conjunto de acciones pulsadas en este frame (salto, ataque, etc.)."""
        pressed = set()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False          # más adelante: menú de pausa
                elif event.key == pygame.K_F1:
                    self.debug = not self.debug
                elif event.key == pygame.K_F2 and self.debug:
                    self.player.hurt()            # probar la animación de daño
                elif event.key == pygame.K_F3 and self.debug:
                    self.player.die()             # probar la animación de muerte
                elif event.key == pygame.K_r:
                    self.load_level(S.LEVELS_DIR / "nivel1.txt")
                elif event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    pressed.add("jump")
                elif event.key == pygame.K_j:
                    pressed.add("attack")
                elif event.key == pygame.K_k:
                    pressed.add("parry")
                elif event.key == pygame.K_e:
                    pressed.add("throw")
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    pressed.add("dash")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    pressed.add("attack")
                elif event.button == 3:
                    pressed.add("parry")
        return pressed

    def read_input(self, pressed):
        keys = pygame.key.get_pressed()
        move_x = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        return InputState(
            move_x=int(move_x), jump_pressed="jump" in pressed, jump_held=bool(jump_held),
            crouch=bool(keys[pygame.K_s] or keys[pygame.K_DOWN]),
            attack_pressed="attack" in pressed, parry_pressed="parry" in pressed,
            throw_pressed="throw" in pressed, dash_pressed="dash" in pressed)

    def update(self, dt, inp):
        self.player.update(dt, inp, self.level)
        self.projectiles.extend(self.player.new_projectiles)
        self.player.new_projectiles.clear()
        for shot in self.projectiles:
            shot.update(dt, self.level)
        self.projectiles = [s for s in self.projectiles if s.alive]
        cx, cy = self.player.center
        self.camera.update(cx, cy, dt)

    # ----------------------------------------------------------------- dibujo
    def draw(self):
        self.screen.fill(S.PAPER)
        self.level.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        for shot in self.projectiles:
            shot.draw(self.screen, self.camera)
        self.draw_hud()
        if self.debug:
            self.draw_debug()
        pygame.display.flip()

    def draw_text(self, text, x, y, color=S.GREY):
        self.screen.blit(self.font.render(text, True, color), (x, y))

    def draw_hud(self):
        self.draw_text("A/D mover | W saltar | S agacharse | Shift dash | Esc salir", 10, 8)
        self.draw_text("Clic izq o J tajo | Clic der o K desvio | E shuriken | F1 debug | R reiniciar", 10, 26)

    def draw_debug(self):
        p, cam = self.player, self.camera
        x, y, w, h = p.rect
        # hitbox y vector de velocidad
        pygame.draw.rect(self.screen, S.GREEN, (int(x - cam.x), int(y - cam.y), w, h), 1)
        cx, cy = p.center
        start = (cx - cam.x, cy - cam.y)
        end = (start[0] + p.vel.x * 0.2, start[1] + p.vel.y * 0.2)
        pygame.draw.line(self.screen, S.RED, start, end, 2)
        lines = [
            f"FPS {self.clock.get_fps():.0f}",
            f"pos ({p.pos.x:.0f}, {p.pos.y:.0f})",
            f"vel ({p.vel.x:.0f}, {p.vel.y:.0f}) px/s",
            f"estado: {p.state}   en suelo: {p.on_ground}   agachado: {p.crouching}   shurikens: {len(self.projectiles)}",
            f"g = {self.level.gravity:.0f}   grip = {self.level.grip}   (F2 dano, F3 muerte)",
        ]
        for i, line in enumerate(lines):
            self.draw_text(line, 10, 52 + i * 18, S.INK)
