# src/game.py
# Jogo principal atualizado:
# - Texto de vitória menor e centralizado
# - HUD: "Tempo para o Boss: Xs" abaixo do tempo
# - Hitbox do player reduzida em 50% (aplicado nas verificações de colisão)
#
import os
import random
import time
import pygame

from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy, BossEnemy
from src.background import ParallaxBackground

# ----------------- Configurações -----------------
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")
MENU_MUSIC_PATH = os.path.join(SOUNDS_DIR, "menu_music.mp3")
GAME_MUSIC_PATH = os.path.join(SOUNDS_DIR, "game_music.mp3")
BOSS_APPEAR_PATH = os.path.join(SOUNDS_DIR, "boss_appear.mp3")       # opcional
VICTORY_MUSIC_PATH = os.path.join(SOUNDS_DIR, "victory_music.mp3")  # opcional

OBST_IMAGE_PATH = os.path.join(IMAGES_DIR, "obst.png")               # imagem do drop
VICTORY_IMAGE_PATH = os.path.join(IMAGES_DIR, "victory_image.png")  # imagem mostrada na vitória

BOSS_HP_BAR_RECT = pygame.Rect(12, 12, 360, 18)
BOSS_NAME = "Boss final"
FONT_NAME = "arial"

# hitbox shrink factor (percentage to shrink width/height): 50% => 0.5
PLAYER_HITBOX_SHRINK_FACTOR = 0.5


# ----------------- Pickup (Obst) -----------------
class Pickup(pygame.sprite.Sprite):
    """Objeto colecionável deixado pelo boss ao morrer."""
    def __init__(self, pos=(240, 400)):
        super().__init__()
        self.image = None
        if os.path.isfile(OBST_IMAGE_PATH):
            try:
                img = pygame.image.load(OBST_IMAGE_PATH).convert_alpha()
                # escala moderada
                maxw, maxh = 96, 96
                w, h = img.get_size()
                scale = min(1.0, maxw / w if w > 0 else 1.0, maxh / h if h > 0 else 1.0)
                if scale < 1.0:
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                self.image = img
            except Exception as e:
                print(f"Aviso: falha ao carregar {OBST_IMAGE_PATH}: {e}")
                self.image = None

        if self.image is None:
            # placeholder circular
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 220, 50), (32, 32), 28)
            pygame.draw.circle(surf, (200, 150, 30), (32, 32), 20)
            self.image = surf

        self.rect = self.image.get_rect(center=pos)


# ----------------- util: colisão com hitbox reduzida -----------------
def collide_with_shrunken_player(a, b):
    """
    Função usada como 'collided' em groupcollide / spritecollide:
    - a: sprite A (ex: bullet or enemy)
    - b: sprite B (expected to be player)
    Compara a.rect com uma versão inflada negativamente (menor) de b.rect.
    A redução é definida por PLAYER_HITBOX_SHRINK_FACTOR.
    """
    if not (hasattr(a, "rect") and hasattr(b, "rect")):
        return False
    try:
        shrink_w = int(b.rect.width * PLAYER_HITBOX_SHRINK_FACTOR)
        shrink_h = int(b.rect.height * PLAYER_HITBOX_SHRINK_FACTOR)
        # inflate takes (dx, dy) added to width/height; to shrink, pass negative values
        infl_w = -(b.rect.width - shrink_w)
        infl_h = -(b.rect.height - shrink_h)
        shrunk = b.rect.inflate(infl_w, infl_h)
        return a.rect.colliderect(shrunk)
    except Exception:
        # fallback: rect collide
        return a.rect.colliderect(b.rect)


# ----------------- Game class -----------------
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

        # música
        self.menu_music = MENU_MUSIC_PATH if os.path.isfile(MENU_MUSIC_PATH) else None
        self.game_music = GAME_MUSIC_PATH if os.path.isfile(GAME_MUSIC_PATH) else None
        self.boss_appear_music = BOSS_APPEAR_PATH if os.path.isfile(BOSS_APPEAR_PATH) else None
        self.victory_music = VICTORY_MUSIC_PATH if os.path.isfile(VICTORY_MUSIC_PATH) else None

        # track boss sound object so we can stop it later
        self.boss_sound = None

        # --- menu assets & UI ---
        self.state = "menu"  # inicia no menu
        self.menu_playing = False

        # start button
        btn_w, btn_h = 220, 56
        self.start_button_rect = pygame.Rect((SCREEN_WIDTH // 2 - btn_w // 2,
                                              SCREEN_HEIGHT - 220, btn_w, btn_h))

        # title image (optional)
        self.title_image = None
        TITLE_IMAGE_PATH = os.path.join(IMAGES_DIR, "title_image.png")
        if os.path.isfile(TITLE_IMAGE_PATH):
            try:
                img = pygame.image.load(TITLE_IMAGE_PATH).convert_alpha()
                w, h = img.get_size()
                maxw, maxh = (360, 240)
                scale = min(1.0, maxw / w if w > 0 else 1.0, maxh / h if h > 0 else 1.0)
                if scale < 1.0:
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                self.title_image = img
            except Exception as e:
                print(f"Aviso: falha ao carregar title_image.png: {e}")
                self.title_image = None

        # fonts
        self.font_title = pygame.font.SysFont(FONT_NAME, 36, bold=True)
        self.font_button = pygame.font.SysFont(FONT_NAME, 28, bold=True)
        self.font_instruct = pygame.font.SysFont(FONT_NAME, 18)
        self.font = pygame.font.SysFont(FONT_NAME, 20)
        self.font_boss = pygame.font.SysFont(FONT_NAME, 18, bold=True)

        # instructions
        self.instructions = [
            "INSTRUÇÕES:",
            "- Clique com o botão esquerdo para atirar para o mouse",
            "- Use WASD ou setas para mover",
            "- Pressione SPACE para atirar (mira no cursor)",
            "- Pressione ESC para pausar"
        ]

        # ----------------- game state -----------------
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        # groups
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.pickups_group = pygame.sprite.Group()  # grupo para Obst

        self.player = None

        # spawn/difficulty
        self.spawn_interval = 1.0
        self.spawn_timer = 0.0
        self.difficulty_timer = 0.0
        self.difficulty_period = 12.0
        self.difficulty_reduction_factor = 0.92
        self.spawn_interval_min = 0.25

        # boss control
        self.boss_phase_started = False
        self.boss_spawned = False
        self.boss_ref = None

        # inicia música do menu (se tiver)
        self.menu_start()

    # ----------------- music control -----------------
    def menu_start(self):
        if self.menu_music:
            try:
                pygame.mixer.music.load(self.menu_music)
                pygame.mixer.music.play(-1)
                self.menu_playing = True
            except Exception as e:
                print(f"Aviso: falha ao tocar música do menu: {e}")
                self.menu_playing = False

    def menu_stop(self):
        try:
            if self.menu_playing:
                pygame.mixer.music.stop()
                self.menu_playing = False
        except Exception:
            pass

    # ----------------- game start -----------------
    def start_game(self):
        # stops menu music and starts gameplay music
        self.menu_stop()
        if self.game_music:
            try:
                pygame.mixer.music.load(self.game_music)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.65)
            except Exception as e:
                print(f"Aviso: falha ao tocar música de gameplay: {e}")

        # reset state
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        # recreate groups
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.pickups_group = pygame.sprite.Group()

        # player
        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        # reset boss flags and stop any leftover boss sound
        self.boss_phase_started = False
        self.boss_spawned = False
        self.boss_ref = None
        if self.boss_sound:
            try:
                self.boss_sound.stop()
            except Exception:
                pass
            self.boss_sound = None

        # change state
        self.state = "playing"

    # ----------------- main loop -----------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            # update background always for parallax
            if self.background:
                try:
                    self.background.update(dt)
                except Exception:
                    self.background = None

            # events
            self.handle_events()

            # game update
            if self.state == "playing" and not self.paused:
                self.total_time += dt
                self.update(dt)

            # draw current frame
            self.draw()

        self.quit()

    # ----------------- events -----------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # route events by state
            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "playing":
                self._handle_playing_event(event)

    def _handle_menu_event(self, event):
        # ENTER starts, click START starts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_ESCAPE:
                self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.start_button_rect.collidepoint(event.pos):
                self.start_game()

    def _handle_playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
                return
            if not self.paused and event.key == pygame.K_SPACE:
                # shoot toward current mouse position
                target = pygame.mouse.get_pos() if pygame.mouse.get_focused() else None
                self._attempt_player_shoot(target_pos=target)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.paused:
                self._attempt_player_shoot(target_pos=event.pos)

    def _attempt_player_shoot(self, target_pos=None):
        try:
            bullet = self.player.shoot(target_pos=target_pos)
        except Exception as e:
            print(f"Aviso: erro ao atirar: {e}")
            bullet = None

        if bullet is not None:
            self.all_sprites.add(bullet)
            self.bullets_group.add(bullet)
            if self.shot_sound:
                try:
                    self.shot_sound.play()
                except Exception:
                    pass

    # ----------------- update -----------------
    def update(self, dt):
        # update sprites
        try:
            self.all_sprites.update(dt)
        except Exception:
            pass

        # collect pending bullets from shooter enemies
        for enemy in list(self.enemies_group):
            if isinstance(enemy, ShooterEnemy):
                try:
                    b = enemy.pop_pending_bullet()
                except Exception:
                    b = None
                if b is not None:
                    self.all_sprites.add(b)
                    self.enemy_bullets_group.add(b)

        # boss phase trigger at 60s
        if not self.boss_phase_started and self.total_time >= 60.0:
            self.boss_phase_started = True
            print("Boss phase iniciado: spawn pausado. Limpe a tela!")

        # spawning (disabled during boss phase)
        if not self.boss_phase_started:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer -= self.spawn_interval
                self.spawn_enemy()

            # difficulty scaling
            self.difficulty_timer += dt
            if self.difficulty_timer >= self.difficulty_period:
                self.difficulty_timer -= self.difficulty_period
                self.spawn_interval = max(self.spawn_interval * self.difficulty_reduction_factor,
                                          self.spawn_interval_min)
        else:
            # when boss phase and no non-boss enemies remain -> spawn boss
            non_boss_enemies = [e for e in self.enemies_group if not isinstance(e, BossEnemy)]
            if not non_boss_enemies and not self.boss_spawned:
                bx = SCREEN_WIDTH // 2
                boss = BossEnemy(pos=(bx, -220), dy=60, start_y=100, hp=50, speed_x=140, player_ref=self.player)
                self.enemies_group.add(boss)
                self.all_sprites.add(boss)
                self.boss_spawned = True
                self.boss_ref = boss
                print("Boss spawnado!")
                # PARA música de gameplay (evita overlap)
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                # toca som de aparição do boss (se existir) e guarda referência para poder parar depois
                if self.boss_appear_music:
                    try:
                        self.boss_sound = pygame.mixer.Sound(self.boss_appear_music)
                        # tocar em loop até morrer (loop=-1). se preferir tocar só uma vez, remova o -1
                        self.boss_sound.play(-1)
                    except Exception as e:
                        print(f"Aviso: falha ao tocar boss_appear_music: {e}")
                        self.boss_sound = None

        # collisions: player bullets -> enemies (unchanged)
        collisions = pygame.sprite.groupcollide(self.bullets_group, self.enemies_group, True, False)
        if collisions:
            for bullet, enemies_hit in collisions.items():
                for enemy in enemies_hit:
                    try:
                        died = enemy.take_damage(1)
                    except Exception:
                        died = False
                    if died:
                        if isinstance(enemy, BossEnemy):
                            # boss morreu -> spawnar Obst no centro do boss
                            boss_center = enemy.rect.center
                            try:
                                pickup = Pickup(pos=boss_center)
                                self.pickups_group.add(pickup)
                                self.all_sprites.add(pickup)
                            except Exception as e:
                                print(f"Aviso: falha ao criar pickup: {e}")
                            # limpa referencia e marca que boss morreu (já kill() foi chamado)
                            if self.boss_ref is enemy:
                                self.boss_ref = None
                            print("Boss derrotado! Obst dropada.")
                            # pare imediatamente o som do boss, se estiver tocando
                            if self.boss_sound:
                                try:
                                    self.boss_sound.stop()
                                except Exception:
                                    pass
                                self.boss_sound = None
                        else:
                            self.score += 10

        # check player colliding with pickups (Obst)
        if pygame.sprite.spritecollideany(self.player, self.pickups_group, collided=collide_with_shrunken_player):
            # coletou a Obst: remove pickup(s) and trigger victory
            for p in list(self.pickups_group):
                try:
                    p.kill()
                except Exception:
                    pass
            try:
                # ensure any boss sound is stopped before victory sequence
                if self.boss_sound:
                    try:
                        self.boss_sound.stop()
                    except Exception:
                        pass
                    self.boss_sound = None
                self.trigger_victory()
                return  # trigger_victory handles music / menu return
            except Exception as e:
                print(f"Aviso: erro ao disparar trigger_victory(): {e}")

        # collisions: enemy bullets -> player (use shrunken hitbox)
        hits = pygame.sprite.groupcollide(self.enemy_bullets_group, self.player_group, True, False,
                                          collided=collide_with_shrunken_player)
        if hits:
            self.lives -= 1
            print(f"Player atingido! Vidas: {self.lives}")
            if self.lives <= 0:
                self.display_game_over()
                pygame.time.delay(1500)
                self.running = False
                return

        # collisions: enemy -> player (touch) using shrunken hitbox
        enemy_hits = pygame.sprite.spritecollide(self.player, self.enemies_group, dokill=False,
                                                 collided=collide_with_shrunken_player)
        if enemy_hits:
            for enemy in enemy_hits:
                try:
                    enemy.kill()
                except Exception:
                    pass
                self.lives -= 1
                print(f"Player colidiu! Vidas: {self.lives}")
                if self.lives <= 0:
                    self.display_game_over()
                    pygame.time.delay(1500)
                    self.running = False
                    return

        # remove enemies off-screen (no penalty)
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT + 120:
                enemy.kill()

    # ----------------- spawn -----------------
    def spawn_enemy(self):
        # don't spawn if boss phase started
        if self.boss_phase_started:
            return

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
            e = ShooterEnemy(pos=(x, y), dy=90, stop_distance=200, shoot_cooldown=1.6,
                             bullet_speed=200, player_ref=self.player, hp=3)
        else:
            e = BasicEnemy(pos=(x, y), player_ref=self.player)

        self.enemies_group.add(e)
        self.all_sprites.add(e)

    # ----------------- draw -----------------
    def draw(self):
        # background
        if self.background:
            try:
                self.background.draw(self.screen)
            except Exception:
                self.background = None
                self.screen.fill((30, 40, 80))
        else:
            self.screen.fill((30, 40, 80))

        # draw menu OR gameplay
        if self.state == "menu":
            # draw menu only (no HUD/sprites)
            try:
                self._draw_menu()
            except Exception as e:
                print(f"Aviso: erro em _draw_menu(): {e}")
        else:
            # playing: draw sprites then HUD and overlays
            try:
                self.all_sprites.draw(self.screen)
            except Exception:
                pass

            # draw pickups on top (if any) - already in all_sprites, but ensure visible
            for p in list(self.pickups_group):
                try:
                    self.screen.blit(p.image, p.rect)
                except Exception:
                    pass

            # boss hp bar top-left
            if self.boss_ref is not None and self.boss_ref.alive():
                try:
                    self._draw_boss_hp(self.boss_ref)
                except Exception:
                    pass

            # HUD
            try:
                self._draw_hud()
            except Exception:
                pass

            # pause overlay
            if self.paused:
                try:
                    self.draw_pause_overlay()
                except Exception:
                    pass

        pygame.display.flip()

    def _draw_menu(self):
        # subtle panel to highlight menu UI
        panel = pygame.Surface((SCREEN_WIDTH - 40, SCREEN_HEIGHT - 80), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 80))
        panel_rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(panel, panel_rect)

        # title text
        title_surf = self.font_title.render("Pirata — O Tesouro", True, (240, 240, 220))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 72))
        self.screen.blit(title_surf, title_rect)

        # title image (if available)
        if self.title_image is not None:
            ti_rect = self.title_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 70))
            self.screen.blit(self.title_image, ti_rect)
        else:
            # visible placeholder
            ph_w, ph_h = 300, 140
            ph = pygame.Surface((ph_w, ph_h))
            ph.fill((180, 160, 100))
            pygame.draw.rect(ph, (140, 120, 80), ph.get_rect(), 4)
            ph_rect = ph.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 70))
            self.screen.blit(ph, ph_rect)

        # start button with shadow, hover, border
        mx, my = pygame.mouse.get_pos()
        rect = self.start_button_rect
        # shadow
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 120))
        self.screen.blit(shadow, (rect.x + 4, rect.y + 6))
        # background color
        hover = rect.collidepoint(mx, my)
        color = (40, 200, 130) if hover else (28, 160, 100)
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=10)
        btn_text = self.font_button.render("START", True, (255, 255, 255))
        self.screen.blit(btn_text, btn_text.get_rect(center=rect.center))

        # instructions
        y0 = rect.bottom + 14
        for i, line in enumerate(self.instructions):
            surf = self.font_instruct.render(line, True, (230, 230, 230))
            rect_text = surf.get_rect(center=(SCREEN_WIDTH // 2, y0 + i * 22))
            self.screen.blit(surf, rect_text)

        # hint
        hint = self.font_instruct.render("Pressione ENTER ou clique START para iniciar", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)))

    def _draw_boss_hp(self, boss):
        # background rect
        pygame.draw.rect(self.screen, (30, 30, 30), BOSS_HP_BAR_RECT, border_radius=4)
        pygame.draw.rect(self.screen, (200, 200, 200), BOSS_HP_BAR_RECT, 2, border_radius=4)
        inner = BOSS_HP_BAR_RECT.inflate(-6, -6)
        hp_ratio = max(0.0, min(1.0, float(boss.hp) / float(boss.max_hp) if boss.max_hp else 0.0))
        fill_w = int(inner.width * hp_ratio)
        if hp_ratio > 0.5:
            color = (int(50 + (1 - hp_ratio) * 100), 200, 40)
        else:
            color = (220, int(50 + hp_ratio * 150), 40)
        pygame.draw.rect(self.screen, (40, 40, 40), inner, border_radius=3)
        pygame.draw.rect(self.screen, color, (inner.x, inner.y, fill_w, inner.height), border_radius=3)
        name_surf = self.font_boss.render(BOSS_NAME, True, (240, 240, 240))
        self.screen.blit(name_surf, (BOSS_HP_BAR_RECT.x, BOSS_HP_BAR_RECT.y - 20))

    def _draw_hud(self):
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        time_surf = self.font.render(f"Tempo: {int(self.total_time)}s", True, (255, 255, 255))
        # Tempo para o Boss (regressivo)
        boss_remaining = max(0, 60 - int(self.total_time))
        boss_time_surf = self.font.render(f"Tempo para o Boss: {boss_remaining}s", True, (200, 200, 255))

        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(time_surf, (SCREEN_WIDTH - 200, 10))
        # draw boss time under the time (small offset)
        self.screen.blit(boss_time_surf, (SCREEN_WIDTH - 200, 34))

        pygame.display.set_caption(f"Pirata — FPS: {int(self.clock.get_fps())}")

    # ----------------- victory sequence -----------------
    def trigger_victory(self):
        """Toca victory_music (se existir) e mostra mensagem + imagem; volta ao menu."""
        # stop any music playing (game music already stopped on boss spawn, but be safe)
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        # stop boss sound if playing
        if self.boss_sound:
            try:
                self.boss_sound.stop()
            except Exception:
                pass
            self.boss_sound = None

        # try to play victory music
        if self.victory_music:
            try:
                pygame.mixer.music.load(self.victory_music)
                pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"Aviso: falha ao tocar victory_music: {e}")

        # try to load victory image
        victory_surf = None
        if os.path.isfile(VICTORY_IMAGE_PATH):
            try:
                img = pygame.image.load(VICTORY_IMAGE_PATH).convert_alpha()
                # scale to fit
                maxw, maxh = SCREEN_WIDTH - 120, SCREEN_HEIGHT - 240
                w, h = img.get_size()
                scale = min(1.0, maxw / w if w > 0 else 1.0, maxh / h if h > 0 else 1.0)
                if scale < 1.0:
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                victory_surf = img
            except Exception as e:
                print(f"Aviso: falha ao carregar victory image: {e}")
                victory_surf = None

        if victory_surf is None:
            # fallback placeholder
            vs = pygame.Surface((360, 180))
            vs.fill((30, 30, 30))
            pygame.draw.rect(vs, (200, 200, 200), vs.get_rect(), 3)
            victory_surf = vs

        # fade to dark and display message + image for a few seconds
        fade_time = 1.2
        display_time = 4.0
        start = time.perf_counter()
        clock = pygame.time.Clock()

        # positions: image above center, text centered in middle (smaller)
        image_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80)
        text_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        msg = "Parabéns, você conquistou a Obst, a fruta sagrada dos sete mares!"
        # agora menor (fonte 18) e centralizado
        victory_font = pygame.font.SysFont(FONT_NAME, 18, bold=True)

        while True:
            now = time.perf_counter()
            elapsed = now - start
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                    return

            # draw background darkened
            if self.background:
                try:
                    self.background.draw(self.screen)
                except Exception:
                    self.screen.fill((10, 10, 10))
            else:
                self.screen.fill((10, 10, 10))

            # dark overlay (progressive)
            alpha = min(1.0, elapsed / fade_time)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(int(alpha * 220))
            self.screen.blit(overlay, (0, 0))

            # draw victory image (above center)
            rect = victory_surf.get_rect(center=image_center)
            self.screen.blit(victory_surf, rect)

            # draw message centered (menor e no meio da tela)
            text_surf = victory_font.render(msg, True, (255, 230, 120))
            text_rect = text_surf.get_rect(center=text_center)
            self.screen.blit(text_surf, text_rect)

            pygame.display.flip()

            if elapsed >= fade_time + display_time:
                break

            clock.tick(30)

        # stop victory music and return to menu
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        # return to menu and restart menu music
        self.state = "menu"
        self.menu_start()

        # cleanup entities
        self.all_sprites.empty()
        self.enemies_group.empty()
        self.enemy_bullets_group.empty()
        self.bullets_group.empty()
        self.pickups_group.empty()
        self.player = None
        self.boss_ref = None
        self.boss_phase_started = False
        self.boss_spawned = False

    # ----------------- game over and quit -----------------
    def display_game_over(self):
        self.screen.fill((10, 10, 10))
        go_font = pygame.font.SysFont(FONT_NAME, 48)
        text = go_font.render("GAME OVER", True, (200, 50, 50))
        sub = self.font.render(f"Score final: {self.score}", True, (255, 255, 255))
        self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))
        pygame.display.flip()

    def quit(self):
        try:
            # ensure boss sound stopped
            if self.boss_sound:
                try:
                    self.boss_sound.stop()
                except Exception:
                    pass
                self.boss_sound = None
            pygame.mixer.music.stop()
        except Exception:
            pass
        pygame.quit()
