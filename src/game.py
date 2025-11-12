# src/game.py
# Jogo completo com:
# - Tela inicial (imagem PNG, botão START, instruções)
# - Parallax background
# - Música do menu e música do gameplay (diferentes)
# - Pausa, HUD e todas as funcionalidades anteriores

import os
import random
import pygame
from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy
from src.background import ParallaxBackground

# ------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ------------------------------------------------------------
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")
MENU_MUSIC_PATH = os.path.join(SOUNDS_DIR, "menu_music.mp3")      # música do menu
GAME_MUSIC_PATH = os.path.join(SOUNDS_DIR, "game_music.mp3")      # música do gameplay
TITLE_IMAGE_PATH = os.path.join(IMAGES_DIR, "title_image.png")    # imagem do menu

# UI do menu
MENU_BG_COLOR = (8, 30, 70)
BUTTON_COLOR = (28, 160, 100)
BUTTON_HOVER_COLOR = (40, 200, 130)
BUTTON_TEXT_COLOR = (255, 255, 255)
INSTRUCTIONS_COLOR = (230, 230, 230)
TITLE_IMAGE_MAX_SIZE = (360, 240)


# ------------------------------------------------------------
# CLASSE PRINCIPAL DO JOGO
# ------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer de áudio não pôde ser inicializado — sem som.")

        # janela e clock
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # estado do app
        self.state = "menu"

        # background parallax
        try:
            self.background = ParallaxBackground(screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
                                                 water_speed=90.0,
                                                 side_speed=45.0)
        except Exception as e:
            print(f"Aviso: falha ao criar ParallaxBackground: {e}")
            self.background = None

        # sons
        self.shot_sound = None
        if os.path.isfile(SHOT_SOUND_PATH):
            try:
                self.shot_sound = pygame.mixer.Sound(SHOT_SOUND_PATH)
            except Exception:
                self.shot_sound = None

        # músicas
        self.menu_music = MENU_MUSIC_PATH if os.path.isfile(MENU_MUSIC_PATH) else None
        self.game_music = GAME_MUSIC_PATH if os.path.isfile(GAME_MUSIC_PATH) else None

        # imagem do título
        self.title_image = None
        if os.path.isfile(TITLE_IMAGE_PATH):
            try:
                img = pygame.image.load(TITLE_IMAGE_PATH).convert_alpha()
                w, h = img.get_size()
                maxw, maxh = TITLE_IMAGE_MAX_SIZE
                scale = min(maxw / w if w > 0 else 1.0, maxh / h if h > 0 else 1.0, 1.0)
                if scale < 1.0:
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                self.title_image = img
            except Exception as e:
                print(f"Aviso: falha ao carregar {TITLE_IMAGE_PATH}: {e}")
                self.title_image = None

        # fontes e UI
        self.font_title = pygame.font.SysFont("arial", 36, bold=True)
        self.font_button = pygame.font.SysFont("arial", 28, bold=True)
        self.font_instruct = pygame.font.SysFont("arial", 18)

        btn_w, btn_h = 220, 56
        self.start_button_rect = pygame.Rect((SCREEN_WIDTH // 2 - btn_w // 2,
                                              SCREEN_HEIGHT - 220, btn_w, btn_h))

        self.instructions = [
            "INSTRUÇÕES:",
            "- Clique com o botão esquerdo para atirar para o mouse",
            "- Use WASD ou setas para mover",
            "- Pressione SPACE para atirar (mira no cursor)",
            "- Pressione ESC para pausar"
        ]

        # variáveis do jogo
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        # grupos
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()

        self.player = None
        self.font = pygame.font.SysFont("arial", 20)

        # spawn
        self.spawn_interval = 1.0
        self.spawn_timer = 0.0
        self.difficulty_timer = 0.0
        self.difficulty_period = 12.0
        self.difficulty_reduction_factor = 0.92
        self.spawn_interval_min = 0.25

        # música do menu
        self.menu_playing = False
        self.menu_start()

    # ------------------------------------------------------------
    # MÚSICA DO MENU E DO JOGO
    # ------------------------------------------------------------
    def menu_start(self):
        """Toca a música do menu em loop (se disponível)."""
        if self.menu_music:
            try:
                pygame.mixer.music.load(self.menu_music)
                pygame.mixer.music.play(-1)
                self.menu_playing = True
            except Exception as e:
                print(f"Aviso: falha ao tocar música do menu: {e}")

    def menu_stop(self):
        """Para a música do menu."""
        try:
            if self.menu_playing:
                pygame.mixer.music.stop()
                self.menu_playing = False
        except Exception:
            pass

    def start_game(self):
        """Inicializa tudo e inicia o gameplay."""
        self.menu_stop()

        # toca música de gameplay
        if self.game_music:
            try:
                pygame.mixer.music.load(self.game_music)
                pygame.mixer.music.play(-1)  # loop infinito
                pygame.mixer.music.set_volume(0.65)
            except Exception as e:
                print(f"Aviso: falha ao tocar música do gameplay: {e}")

        # reseta estado
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        # grupos
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()

        # player
        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        self.state = "playing"

    # ------------------------------------------------------------
    # LOOP PRINCIPAL
    # ------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            if self.background:
                try:
                    self.background.update(dt)
                except Exception:
                    self.background = None

            self.handle_events()

            if self.state == "playing" and not self.paused:
                self.total_time += dt
                self.update(dt)

            self.draw()

        self.quit()

    # ------------------------------------------------------------
    # EVENTOS
    # ------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "playing":
                self._handle_playing_event(event)

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_ESCAPE:
                self.running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.start_button_rect.collidepoint(event.pos):
                self.start_game()

    def _handle_playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
                return
            if not self.paused and event.key == pygame.K_SPACE:
                self._attempt_player_shoot(pygame.mouse.get_pos())

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.paused:
            self._attempt_player_shoot(event.pos)

    def _attempt_player_shoot(self, target_pos=None):
        try:
            bullet = self.player.shoot(target_pos=target_pos)
        except Exception as e:
            print(f"Aviso: erro em shoot(): {e}")
            bullet = None

        if bullet:
            self.all_sprites.add(bullet)
            self.bullets_group.add(bullet)
            if self.shot_sound:
                try:
                    self.shot_sound.play()
                except Exception:
                    pass

    # ------------------------------------------------------------
    # ATUALIZAÇÃO DO JOGO
    # ------------------------------------------------------------
    def update(self, dt):
        self.all_sprites.update(dt)

        # recolhe balas dos shooters
        for enemy in list(self.enemies_group):
            if isinstance(enemy, ShooterEnemy):
                b = enemy.pop_pending_bullet()
                if b:
                    self.all_sprites.add(b)
                    self.enemy_bullets_group.add(b)

        # spawn
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer -= self.spawn_interval
            self.spawn_enemy()

        # dificuldade dinâmica
        self.difficulty_timer += dt
        if self.difficulty_timer >= self.difficulty_period:
            self.difficulty_timer -= self.difficulty_period
            self.spawn_interval = max(self.spawn_interval * self.difficulty_reduction_factor,
                                      self.spawn_interval_min)

        # colisões tiros jogador vs inimigos
        collisions = pygame.sprite.groupcollide(self.bullets_group, self.enemies_group, True, False)
        for bullet, enemies_hit in collisions.items():
            for enemy in enemies_hit:
                if enemy.take_damage(1):
                    self.score += 10

        # colisões balas inimigas vs player
        if pygame.sprite.groupcollide(self.enemy_bullets_group, self.player_group, True, False):
            self.lives -= 1
            print(f"Player atingido! Vidas: {self.lives}")
            if self.lives <= 0:
                self.display_game_over()
                pygame.time.delay(2000)
                self.running = False
                return

        # colisões inimigo vs player
        if pygame.sprite.spritecollide(self.player, self.enemies_group, dokill=False):
            self.lives -= 1
            print(f"Player colidiu com inimigo! Vidas: {self.lives}")
            if self.lives <= 0:
                self.display_game_over()
                pygame.time.delay(2000)
                self.running = False
                return

        # remove inimigos fora da tela
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT:
                enemy.kill()

    # ------------------------------------------------------------
    # SPAWN DE INIMIGOS
    # ------------------------------------------------------------
    def spawn_enemy(self):
        base = {"basic": 0.6, "zigzag": 0.18, "fast": 0.12, "shooter": 0.10}
        t = self.total_time
        bonus = min(0.6, t / 120.0)
        base["basic"] = max(0.25, base["basic"] * (1.0 - bonus * 0.6))
        base["zigzag"] += bonus * 0.25
        base["fast"] += bonus * 0.20
        base["shooter"] += bonus * 0.15
        total = sum(base.values())
        for k in base:
            base[k] /= total

        r = random.random()
        acc = 0.0
        chosen = "basic"
        for k, p in base.items():
            acc += p
            if r <= acc:
                chosen = k
                break

        x = random.randint(30, SCREEN_WIDTH - 30)
        y = -50
        if chosen == "basic":
            e = BasicEnemy(pos=(x, y), player_ref=self.player)
        elif chosen == "zigzag":
            e = ZigZagEnemy(pos=(x, y), dy=120, amplitude=80, frequency=0.9, player_ref=self.player)
        elif chosen == "fast":
            e = FastEnemy(pos=(x, y), dy=240, player_ref=self.player)
        else:
            e = ShooterEnemy(pos=(x, y), dy=90, stop_distance=200, shoot_cooldown=1.6,
                             bullet_speed=200, player_ref=self.player, hp=3)

        self.enemies_group.add(e)
        self.all_sprites.add(e)

    # ------------------------------------------------------------
    # DESENHO
    # ------------------------------------------------------------
    def draw(self):
        if self.background:
            try:
                self.background.draw(self.screen)
            except Exception:
                self.background = None
                self.screen.fill((30, 40, 80))
        else:
            self.screen.fill((30, 40, 80))

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "playing":
            self.all_sprites.draw(self.screen)
            self._draw_hud()
            if self.paused:
                self.draw_pause_overlay()

        pygame.display.flip()

    def _draw_menu(self):
        # título
        title_surf = self.font_title.render("Pirata — O Tesouro", True, (240, 240, 220))
        self.screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 72)))

        # imagem
        if self.title_image:
            rect = self.title_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
            self.screen.blit(self.title_image, rect)
        else:
            ph = pygame.Surface((220, 120))
            ph.fill((180, 160, 100))
            self.screen.blit(ph, ph.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))

        # botão START
        mx, my = pygame.mouse.get_pos()
        hover = self.start_button_rect.collidepoint(mx, my)
        color = BUTTON_HOVER_COLOR if hover else BUTTON_COLOR
        pygame.draw.rect(self.screen, color, self.start_button_rect, border_radius=8)
        btn_text = self.font_button.render("START", True, BUTTON_TEXT_COLOR)
        self.screen.blit(btn_text, btn_text.get_rect(center=self.start_button_rect.center))

        # instruções
        y0 = self.start_button_rect.bottom + 16
        for i, line in enumerate(self.instructions):
            surf = self.font_instruct.render(line, True, INSTRUCTIONS_COLOR)
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, y0 + i * 22))
            self.screen.blit(surf, rect)

        hint = self.font_instruct.render("Pressione ENTER para iniciar", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)))

    def _draw_hud(self):
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        time_surf = self.font.render(f"Tempo: {int(self.total_time)}s", True, (255, 255, 255))
        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(time_surf, (SCREEN_WIDTH - 120, 10))
        pygame.display.set_caption(f"Pirata — FPS: {int(self.clock.get_fps())}")

    def draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        go_font = pygame.font.SysFont("arial", 56, bold=True)
        text = go_font.render("PAUSADO", True, (240, 240, 240))
        sub = self.font.render("Pressione ESC para continuar", True, (200, 200, 200))
        self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))

    def display_game_over(self):
        self.screen.fill((10, 10, 10))
        go_font = pygame.font.SysFont("arial", 48)
        text = go_font.render("GAME OVER", True, (200, 50, 50))
        sub = self.font.render(f"Score final: {self.score}", True, (255, 255, 255))
        self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))
        pygame.display.flip()

    def quit(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        pygame.quit()
