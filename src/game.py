"""Bucle principal: eventos -> actualizar (con dt) -> dibujar."""
import pygame

import settings as S
from animation import Animator, ENEMY_VARIANTS, load_ronin_animations, load_enemy_animations
from camera import Camera
from combat import resolve_combat
from enemy import ENEMY_CLASSES
from level import Level
from physics import overlaps
from player import Player, InputState


# Modo pruebas: tecla -> (tipo, variante)
SPAWN_KEYS = {
    pygame.K_1: ("caminante", "aldeano"),
    pygame.K_2: ("caminante", "samurai"),
    pygame.K_3: ("corredor", "campesino"),
    pygame.K_4: ("corredor", "ashigaru"),
}


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
        self.enemy_animations = {(k, v): load_enemy_animations(k, v) for k, vs in ENEMY_VARIANTS.items() for v in vs}
        self.level_path = S.LEVELS_DIR / "nivel1.txt"
        self.death_timer = 0.0
        self.load_level(self.level_path)

    def load_level(self, path):
        self.level_path = path
        self.level = Level(path)
        self.player = Player(*self.level.spawn)
        self.projectiles = []
        self.death_timer = 0.0
        self.enemies = [ENEMY_CLASSES[k](v, x, y, self.enemy_animations.get((k, v))) for k, v, x, y in self.level.enemy_spawns]
        if self.ronin_animations:
            self.player.animator = Animator(self.ronin_animations)
        self.camera = Camera(self.level.width, self.level.height)

    def spawn_enemy(self, kind, variant):
        """Modo pruebas: genera un zombi delante del Ronin (o detrás si delante no hay sitio ni suelo)."""
        p = self.player
        cls = ENEMY_CLASSES[kind]
        w, h = cls.SIZE
        for dx in (260, 180, 340):
            for side in (p.facing, -p.facing):
                x = p.center[0] + side * dx
                ground = None                                   # primer suelo que haya debajo del Ronin
                for y in range(int(p.pos.y + p.size[1]), int(p.pos.y + p.size[1]) + 240, 4):
                    ground = next((r for r in self.level.solids if overlaps(x, y, 1, 1, r)), None)
                    if ground:
                        break
                if ground is None:
                    continue
                feet_y = ground.top
                if not any(overlaps(x - w / 2, feet_y - h, w, h, r) for r in self.level.solids):
                    self.enemies.append(cls(variant, x, feet_y, self.enemy_animations.get((kind, variant))))
                    return

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
                    # golpe de prueba: pasa por take_damage, así respeta la invulnerabilidad como uno real
                    self.player.take_damage(self.player.center[0] + self.player.facing * 40)
                elif event.key == pygame.K_F3 and self.debug:
                    self.player.die()             # probar la animación de muerte
                elif event.key in SPAWN_KEYS and self.level.test_mode:
                    self.spawn_enemy(*SPAWN_KEYS[event.key])
                elif event.key == pygame.K_r:
                    self.load_level(self.level_path)
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
        resolve_combat(self.player, self.enemies, self.projectiles)
        for enemy in self.enemies:
            enemy.update(dt, self.level, self.player)
        self.enemies = [e for e in self.enemies if not e.removable]
        self.projectiles = [s for s in self.projectiles if s.alive]
        if self.player.dead:                      # reinicia el nivel poco después de morir
            self.death_timer += dt
            if self.death_timer >= S.DEATH_RESTART:
                self.load_level(self.level_path)
        cx, cy = self.player.center
        self.camera.update(cx, cy, dt)

    # ----------------------------------------------------------------- dibujo
    def draw(self):
        self.screen.fill(S.PAPER)
        self.level.draw(self.screen, self.camera)
        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        for shot in self.projectiles:
            shot.draw(self.screen, self.camera)
        self.draw_hud()
        if self.debug:
            self.draw_debug()
        pygame.display.flip()

    def draw_text(self, text, x, y, color=S.GREY):
        self.screen.blit(self.font.render(text, True, color), (x, y))

    def draw_hearts(self):
        size = 22
        for i in range(S.PLAYER_MAX_HEALTH):
            x = S.WIDTH - 14 - (S.PLAYER_MAX_HEALTH - i) * (size + 4)
            full = i < self.player.health
            color = S.RED if full else (206, 198, 182)
            pygame.draw.circle(self.screen, color, (x + size * 0.28, 16 + size * 0.3), size * 0.28)
            pygame.draw.circle(self.screen, color, (x + size * 0.72, 16 + size * 0.3), size * 0.28)
            pygame.draw.polygon(self.screen, color, [(x + 1, 16 + size * 0.4), (x + size - 1, 16 + size * 0.4),
                                                     (x + size * 0.5, 16 + size * 0.95)])

    def draw_hud(self):
        self.draw_hearts()
        self.draw_text("A/D mover | W saltar | S agacharse | Shift dash | Esc salir", 10, 8)
        if self.player.dead:
            self.draw_text("Has caido... reiniciando", S.WIDTH // 2 - 90, S.HEIGHT // 2, S.RED)
        self.draw_text("Clic izq o J tajo | Clic der o K desvio | E shuriken | F1 debug | R reiniciar", 10, 26)
        if self.level.test_mode:
            self.draw_text("MODO PRUEBAS: 1 aldeano, 2 samurai (caminantes) | 3 campesino, 4 ashigaru (corredores)", 10, 44, S.RED)

    def draw_debug(self):
        p, cam = self.player, self.camera
        x, y, w, h = p.rect
        # hitbox y vector de velocidad
        pygame.draw.rect(self.screen, S.GREEN, (int(x - cam.x), int(y - cam.y), w, h), 1)
        cx, cy = p.center
        start = (cx - cam.x, cy - cam.y)
        end = (start[0] + p.vel.x * 0.2, start[1] + p.vel.y * 0.2)
        pygame.draw.line(self.screen, S.RED, start, end, 2)
        for e in self.enemies:                       # hitbox y estado de cada enemigo
            ex, ey, ew, eh = e.rect
            pygame.draw.rect(self.screen, S.RED, (int(ex - cam.x), int(ey - cam.y), ew, eh), 1)
            self.draw_text(e.state, int(ex - cam.x), int(ey - cam.y) - 14, S.RED)
        lines = [
            f"FPS {self.clock.get_fps():.0f}",
            f"pos ({p.pos.x:.0f}, {p.pos.y:.0f})",
            f"vel ({p.vel.x:.0f}, {p.vel.y:.0f}) px/s",
            f"estado: {p.state}   vida: {p.health}   suelo: {p.on_ground}   agachado: {p.crouching}   shurikens: {len(self.projectiles)}   enemigos: {len(self.enemies)}",
            f"g = {self.level.gravity:.0f}   grip = {self.level.grip}   (F2 golpe de prueba, F3 muerte)",
        ]
        for i, line in enumerate(lines):
            self.draw_text(line, 10, 70 + i * 18, S.INK)
