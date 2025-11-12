# src/game.py
# Loop principal do jogo com tela inicial (menu) contendo:
#  - imagem de título (assets/images/title_image.png)
#  - botão START clicável
#  - instruções em texto
#  - música de fundo do menu (assets/sounds/menu_music.mp3)
#
# Ao pressionar START (clique no botão ou ENTER), o menu pára a música
# e inicia o jogo (estado "playing").
#
# Proteções defensivas: se os assets estiverem ausentes, usa fallback.

import os
import random
import pygame
from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy
from src.background import ParallaxBackground

# tela / fps
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")
MENU_MUSIC_PATH = os.path.join(SOUNDS_DIR, "menu_music.mp3")      # música do menu (coloque aqui)
TITLE_IMAGE_PATH = os.path.join(IMAGES_DIR, "title_image.png")   # sua imagem PNG para o menu

# --- UI tuning (ajuste como preferir) ---
MENU_BG_COLOR = (8, 30, 70)
BUTTON_COLOR = (28, 160, 100)
BUTTON_HOVER_COLOR = (40, 200, 130)
BUTTON_TEXT_COLOR = (255, 255, 255)
INSTRUCTIONS_COLOR = (230, 230, 230)
TITLE_IMAGE_MAX_SIZE = (360, 240)  # max width,height para a imagem do título
# ----------------------------------------


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

        # estado do app: 'menu' ou 'playing'
        self.state = "menu"

        # background parallax
        try:
            self.background = ParallaxBackground(screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
                                                 water_speed=90.0, side_speed=45.0)
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

        # música do menu (loop)
        self.menu_music = None
        if os.path.isfile(MENU_MUSIC_PATH):
            try:
                # não carregamos com Sound se for mp3 grande; usamos mixer.music
                # guardamos o path e tocará no menu_start()
                self.menu_music = MENU_MUSIC_PATH
            except Exception:
                self.menu_music = None

        # carrega imagem do title (se houver)
        self.title_image = None
        if os.path.isfile(TITLE_IMAGE_PATH):
            try:
                img = pygame.image.load(TITLE_IMAGE_PATH).convert_alpha()
                # scale mantendo razão, limitando ao tamanho máximo
                w, h = img.get_size()
                maxw, maxh = TITLE_IMAGE_MAX_SIZE
                scale = min(maxw / w if w > 0 else 1.0, maxh / h if h > 0 else 1.0, 1.0)
                if scale < 1.0:
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                self.title_image = img
            except Exception as e:
                print(f"Aviso: falha ao carregar {TITLE_IMAGE_PATH}: {e}")
                self.title_image = None

        # --- Menu UI: botão START e textos ---
        self.font_title = pygame.font.SysFont("arial", 36, bold=True)
        self.font_button = pygame.font.SysFont("arial", 28, bold=True)
        self.font_instruct = pygame.font.SysFont("arial", 18)
        # botão: rect central
        btn_w, btn_h = 220, 56
        self.start_button_rect = pygame.Rect((SCREEN_WIDTH // 2 - btn_w // 2,
                                              SCREEN_HEIGHT - 220, btn_w, btn_h))

        # texto das instruções (você pode alterar)
        self.instructions = [
            "INSTRUÇÕES:",
            "- Clique com o botão esquerdo para atirar para o mouse",
            "- Use WASD ou setas para mover",
            "- Pressione SPACE para atirar também (mira no cursor)",
            "- Pressione ESC para pausar"
        ]

        # --- estado do jogo real (inicia quando entrar em "playing") ---
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        # grupos de sprites (serão inicializados no start_game())
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()

        # o player (criado no start_game)
        self.player = None

        # HUD font
        self.font = pygame.font.SysFont("arial", 20)

        # spawn/dificuldade
        self.spawn_interval = 1.0
        self.spawn_timer = 0.0
        self.difficulty_timer = 0.0
        self.difficulty_period = 12.0
        self.difficulty_reduction_factor = 0.92
        self.spawn_interval_min = 0.25

        # inicia música do menu automaticamente
        self.menu_playing = False
        self.menu_start()

    # ---------- MENU MUSIC ----------
    def menu_start(self):
        """Toca a música do menu em loop (se disponível)."""
        if self.menu_music:
            try:
                # usa mixer.music para loop contínuo
                pygame.mixer.music.load(self.menu_music)
                pygame.mixer.music.play(-1)
                self.menu_playing = True
            except Exception as e:
                print(f"Aviso: falha ao tocar música do menu: {e}")
                self.menu_playing = False

    def menu_stop(self):
        """Para a música do menu (se estiver tocando)."""
        try:
            if self.menu_playing:
                pygame.mixer.music.stop()
                self.menu_playing = False
        except Exception:
            pass

    # ---------- START DO JOGO ----------
    def start_game(self):
        """Inicializa entidades e grupos para começar a partida e muda o estado para 'playing'."""
        # para a música do menu
        self.menu_stop()

        # reseta estado
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        # limpa e recria grupos
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()

        # cria player e adiciona
        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        # define estado
        self.state = "playing"

    # ---------- EVENTOS / LOOP ----------
    def run(self):
        """Loop principal com menu integrado."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            # atualiza background SEMPRE (independente de pausa) para sensação de movimento
            if self.background is not None:
                try:
                    self.background.update(dt)
                except Exception as e:
                    print(f"Aviso: erro ao atualizar background: {e}")
                    self.background = None

            # eventos gerais
            self.handle_events()

            # atualiza dependendo do estado
            if self.state == "playing" and not self.paused:
                self.total_time += dt
                self.update(dt)

            # desenha (menu ou jogo)
            self.draw()

        self.quit()

    def handle_events(self):
        """Processa eventos do Pygame, delegando conforme estado."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "playing":
                self._handle_playing_event(event)

    # --- eventos do menu (click no botão, ENTER para iniciar) ---
    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                # Enter inicia
                self.start_game()
            if event.key == pygame.K_ESCAPE:
                self.running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.start_button_rect.collidepoint(mx, my):
                self.start_game()

    # --- eventos do jogo (reutiliza sua lógica anterior) ---
    def _handle_playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
                return
            if not self.paused and event.key == pygame.K_SPACE:
                target = pygame.mouse.get_pos() if pygame.mouse.get_focused() else None
                self._attempt_player_shoot(target_pos=target)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.paused and event.button == 1:
                self._attempt_player_shoot(target_pos=event.pos)

    def _attempt_player_shoot(self, target_pos=None):
        try:
            bullet = self.player.shoot(target_pos=target_pos)
        except Exception as e:
            print(f"Aviso: erro ao chamar player.shoot(): {e}")
            bullet = None

        if bullet is not None:
            try:
                self.all_sprites.add(bullet)
                self.bullets_group.add(bullet)
            except Exception as e:
                print(f"Aviso: falha ao adicionar bullet aos grupos: {e}")
            if self.shot_sound:
                try:
                    self.shot_sound.play()
                except Exception:
                    pass

    # ---------- LÓGICA DO JOGO (igual à anterior) ----------
    def update(self, dt):
        self.all_sprites.update(dt)

        # recolhe balas pendentes dos shooters
        for enemy in list(self.enemies_group):
            if isinstance(enemy, ShooterEnemy):
                try:
                    b = enemy.pop_pending_bullet()
                except Exception:
                    b = None
                if b is not None:
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
        if collisions:
            for bullet, enemies_hit in collisions.items():
                for enemy in enemies_hit:
                    try:
                        died = enemy.take_damage(1)
                    except Exception:
                        died = False
                    if died:
                        self.score += 10

        # colisões balas inimigas vs player
        hits = pygame.sprite.groupcollide(self.enemy_bullets_group, self.player_group, True, False)
        if hits:
            for bullet, players in hits.items():
                self.lives -= 1
                print(f"Player atingido por bala! Vidas: {self.lives}")
                if self.lives <= 0:
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return

        # colisões inimigo vs player
        enemy_hits = pygame.sprite.spritecollide(self.player, self.enemies_group, dokill=False)
        if enemy_hits:
            for enemy in enemy_hits:
                try:
                    enemy.kill()
                except Exception:
                    pass
                self.lives -= 1
                print(f"Player atingido por inimigo! Vidas: {self.lives}")
                if self.lives <= 0:
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return

        # remove inimigos que saem pelo fundo (não penaliza vidas)
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT:
                enemy.kill()

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
        elif chosen == "shooter":
            e = ShooterEnemy(pos=(x, y), dy=90, stop_distance=200, shoot_cooldown=1.6, bullet_speed=200, player_ref=self.player, hp=3)
        else:
            e = BasicEnemy(pos=(x, y), player_ref=self.player)

        self.enemies_group.add(e)
        self.all_sprites.add(e)

    # ---------- DESENHO (menu + jogo) ----------
    def draw(self):
        # primeiro desenha background (se existir)
        if self.background is not None:
            try:
                self.background.draw(self.screen)
            except Exception:
                self.screen.fill((30, 40, 80))
                self.background = None
        else:
            self.screen.fill((30, 40, 80))

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "playing":
            # desenha sprites por cima do background
            self.all_sprites.draw(self.screen)
            self._draw_hud()

        # overlay pausa
        if self.state == "playing" and self.paused:
            self.draw_pause_overlay()

        pygame.display.flip()

    def _draw_menu(self):
        """Desenha a tela inicial com título, imagem, botão START e instruções."""
        # fundo (se desejar usar cor sólida sobre o background)
        # Aqui mantemos o parallax por baixo e desenhamos elementos do menu por cima.

        # desenha título textual no topo
        title_surf = self.font_title.render("Pirata — O Tesouro", True, (240, 240, 220))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 72))
        self.screen.blit(title_surf, title_rect)

        # desenha sua imagem (se existir) centralizada um pouco acima do centro
        if self.title_image is not None:
            ti_rect = self.title_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
            self.screen.blit(self.title_image, ti_rect)
        else:
            # placeholder: desenha um sprite simples
            ph = pygame.Surface((220, 120), pygame.SRCALPHA)
            pygame.draw.rect(ph, (200, 160, 80), ph.get_rect(), border_radius=10)
            ph_rect = ph.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60))
            self.screen.blit(ph, ph_rect)

        # botão START (cor muda se hover)
        mx, my = pygame.mouse.get_pos()
        hover = self.start_button_rect.collidepoint(mx, my)
        color = BUTTON_HOVER_COLOR if hover else BUTTON_COLOR
        pygame.draw.rect(self.screen, color, self.start_button_rect, border_radius=8)
        # texto do botão
        btn_text = self.font_button.render("START", True, BUTTON_TEXT_COLOR)
        btn_rect = btn_text.get_rect(center=self.start_button_rect.center)
        self.screen.blit(btn_text, btn_rect)

        # instruções (linhas)
        y0 = self.start_button_rect.bottom + 16
        for i, line in enumerate(self.instructions):
            surf = self.font_instruct.render(line, True, INSTRUCTIONS_COLOR)
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, y0 + i * 22))
            self.screen.blit(surf, rect)

        # dica: ENTER para iniciar
        hint = self.font_instruct.render("Pressione ENTER para iniciar", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
        self.screen.blit(hint, hint_rect)

    def _draw_hud(self):
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        spawn_surf = self.font.render(f"Spawn: {self.spawn_interval:.2f}s", True, (255, 255, 255))
        time_surf = self.font.render(f"Tempo: {int(self.total_time)}s", True, (255, 255, 255))

        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(spawn_surf, (10, 58))
        self.screen.blit(time_surf, (SCREEN_WIDTH - 120, 10))

        fps = int(self.clock.get_fps())
        fps_surf = self.font.render(f"FPS: {fps}", True, (255, 255, 255))
        self.screen.blit(fps_surf, (SCREEN_WIDTH - 80, 34))
        pygame.display.set_caption(f"Pirata — FPS: {fps}")

    def draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        go_font = pygame.font.SysFont("arial", 56, bold=True)
        text = go_font.render("PAUSED", True, (240, 240, 240))
        sub = self.font.render("Pressione ESC para continuar", True, (200, 200, 200))
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        subrect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(text, rect)
        self.screen.blit(sub, subrect)

    def display_game_over(self):
        self.screen.fill((10, 10, 10))
        go_font = pygame.font.SysFont("arial", 48)
        text = go_font.render("GAME OVER", True, (200, 50, 50))
        sub = self.font.render(f"Score final: {self.score}", True, (255, 255, 255))
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        subrect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(text, rect)
        self.screen.blit(sub, subrect)
        pygame.display.flip()

    def quit(self):
        # garante que música do menu pare ao sair
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        pygame.quit()
