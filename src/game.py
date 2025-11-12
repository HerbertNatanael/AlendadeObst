# src/game.py
# Versão atualizada com Boss final e sequência de vitória.
# Dependências: src/background.py, src/player.py, src/enemy.py, src/bullet.py
# Assets opcionais:
#   assets/images/victory.gif      (se Pillow instalado, será animado)
#   assets/images/victory_image.png (fallback)
#   assets/sounds/victory_music.mp3 (opcional)
#
import os
import random
import pygame
import time

from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy, BossEnemy
from src.background import ParallaxBackground

# constantes e paths
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")
MENU_MUSIC_PATH = os.path.join(SOUNDS_DIR, "menu_music.mp3")
GAME_MUSIC_PATH = os.path.join(SOUNDS_DIR, "game_music.mp3")
VICTORY_MUSIC_PATH = os.path.join(SOUNDS_DIR, "victory_music.mp3")

VICTORY_GIF_PATH = os.path.join(IMAGES_DIR, "victory.gif")
VICTORY_IMAGE_PATH = os.path.join(IMAGES_DIR, "victory_image.png")
BOSS_IMAGE_PATH = os.path.join(IMAGES_DIR, "boss.png")

# HUD / boss UI tuning
BOSS_HP_BAR_RECT = pygame.Rect(12, 12, 360, 18)  # onde o HP do boss aparece (canto superior esquerdo)
BOSS_NAME = "Boss final"
FONT_NAME = "arial"


class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer nao inicializado — sem som")

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # background
        try:
            self.background = ParallaxBackground(screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
                                                 water_speed=90.0, side_speed=45.0)
        except Exception as e:
            print(f"Aviso: falha ao criar ParallaxBackground: {e}")
            self.background = None

        # sounds
        self.shot_sound = None
        if os.path.isfile(SHOT_SOUND_PATH):
            try:
                self.shot_sound = pygame.mixer.Sound(SHOT_SOUND_PATH)
            except Exception:
                self.shot_sound = None

        self.menu_music = MENU_MUSIC_PATH if os.path.isfile(MENU_MUSIC_PATH) else None
        self.game_music = GAME_MUSIC_PATH if os.path.isfile(GAME_MUSIC_PATH) else None
        self.victory_music = VICTORY_MUSIC_PATH if os.path.isfile(VICTORY_MUSIC_PATH) else None

        # victory animation assets
        self.victory_gif = VICTORY_GIF_PATH if os.path.isfile(VICTORY_GIF_PATH) else None
        self.victory_image = VICTORY_IMAGE_PATH if os.path.isfile(VICTORY_IMAGE_PATH) else None

        # UI fonts
        self.font = pygame.font.SysFont(FONT_NAME, 20)
        self.font_boss = pygame.font.SysFont(FONT_NAME, 18, bold=True)

        # game state
        self.state = "menu"
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

        self.player = None

        # spawn/difficulty
        self.spawn_interval = 1.0
        self.spawn_timer = 0.0
        self.difficulty_timer = 0.0
        self.difficulty_period = 12.0
        self.difficulty_reduction_factor = 0.92
        self.spawn_interval_min = 0.25

        # boss control
        self.boss_phase_started = False     # true when we stop spawning (time >= 60)
        self.boss_spawned = False
        self.boss_ref = None

        # menu -> start music
        self.menu_playing = False
        self.menu_music_start()

    # ---- music control ----
    def menu_music_start(self):
        if self.menu_music:
            try:
                pygame.mixer.music.load(self.menu_music)
                pygame.mixer.music.play(-1)
                self.menu_playing = True
            except Exception:
                self.menu_playing = False

    def menu_music_stop(self):
        try:
            if self.menu_playing:
                pygame.mixer.music.stop()
                self.menu_playing = False
        except Exception:
            pass

    # ---- starting gameplay ----
    def start_game(self):
        # stop menu and start game music
        self.menu_music_stop()
        if self.game_music:
            try:
                pygame.mixer.music.load(self.game_music)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.65)
            except Exception:
                pass

        # reset
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()

        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        # reset boss flags
        self.boss_phase_started = False
        self.boss_spawned = False
        self.boss_ref = None

        self.state = "playing"

    # ---- main loop ----
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            # update background always
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

    # ---- events ----
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "playing":
                self._handle_play_event(event)

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_game()
            if event.key == pygame.K_ESCAPE:
                self.running = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # simple menu: start area center bottom
            mx, my = event.pos
            # reuse same start button region as before (approx)
            btn_rect = pygame.Rect((SCREEN_WIDTH//2 - 110, SCREEN_HEIGHT - 220, 220, 56))
            if btn_rect.collidepoint(mx, my):
                self.start_game()

    def _handle_play_event(self, event):
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
        except Exception:
            bullet = None
        if bullet:
            self.all_sprites.add(bullet)
            self.bullets_group.add(bullet)
            if self.shot_sound:
                try:
                    self.shot_sound.play()
                except Exception:
                    pass

    # ---- update loop ----
    def update(self, dt):
        self.all_sprites.update(dt)

        # collect shooter bullets
        for enemy in list(self.enemies_group):
            if isinstance(enemy, ShooterEnemy):
                b = enemy.pop_pending_bullet()
                if b:
                    self.all_sprites.add(b)
                    self.enemy_bullets_group.add(b)

        # boss phase trigger: at 60s stop spawning and wait for clear
        if not self.boss_phase_started and self.total_time >= 60.0:
            self.boss_phase_started = True
            # effectively stop spawning by setting a flag; spawn_enemy checks this
            # keep existing enemies until they die
            print("Boss phase iniciado: spawn de inimigos pausado. Limpe a tela!")

        # spawn (only if not in boss_phase_started)
        if not self.boss_phase_started:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer -= self.spawn_interval
                self.spawn_enemy()
            # difficulty timer
            self.difficulty_timer += dt
            if self.difficulty_timer >= self.difficulty_period:
                self.difficulty_timer -= self.difficulty_period
                self.spawn_interval = max(self.spawn_interval * self.difficulty_reduction_factor,
                                          self.spawn_interval_min)
        else:
            # when boss phase started and there are no regular enemies and boss not yet spawned => spawn boss
            non_boss_enemies = [e for e in self.enemies_group if not isinstance(e, BossEnemy)]
            if not non_boss_enemies and not self.boss_spawned:
                # spawn boss
                bx = SCREEN_WIDTH // 2
                boss = BossEnemy(pos=(bx, -220), dy=60, start_y=100, hp=50, speed_x=140, player_ref=self.player)
                self.enemies_group.add(boss)
                self.all_sprites.add(boss)
                self.boss_spawned = True
                self.boss_ref = boss
                print("Boss spawnado!")

        # collisions: player bullets -> enemies
        collisions = pygame.sprite.groupcollide(self.bullets_group, self.enemies_group, True, False)
        if collisions:
            for bullet, enemies_hit in collisions.items():
                for enemy in enemies_hit:
                    died = enemy.take_damage(1)
                    if died:
                        # if died and was boss => trigger victory
                        if isinstance(enemy, BossEnemy):
                            # ensure boss reference cleared
                            if enemy is self.boss_ref:
                                self.boss_ref = None
                            # run victory sequence
                            self.trigger_victory()
                            return
                        else:
                            self.score += 10

        # enemy bullets -> player
        hits = pygame.sprite.groupcollide(self.enemy_bullets_group, self.player_group, True, False)
        if hits:
            self.lives -= 1
            print(f"Player atingido por bala! Vidas: {self.lives}")
            if self.lives <= 0:
                self.display_game_over()
                pygame.time.delay(2000)
                self.running = False
                return

        # enemy collisions with player
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

        # remove enemies off-screen (no penalty)
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT + 100:
                enemy.kill()

    # ---- spawn logic ----
    def spawn_enemy(self):
        # do not spawn if boss phase started
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

    # ---- draw ----
    def draw(self):
        if self.background:
            try:
                self.background.draw(self.screen)
            except Exception:
                self.screen.fill((30, 40, 80))
                self.background = None
        else:
            self.screen.fill((30, 40, 80))

        # draw sprites
        self.all_sprites.draw(self.screen)

        # if boss present, draw boss hp bar top-left with name
        if self.boss_ref is not None and self.boss_ref.alive():
            self._draw_boss_hp(self.boss_ref)

        # HUD
        self._draw_hud()

        # paused overlay
        if self.paused:
            self.draw_pause_overlay()

        pygame.display.flip()

    def _draw_boss_hp(self, boss):
        # background rect
        pygame.draw.rect(self.screen, (30, 30, 30), BOSS_HP_BAR_RECT, border_radius=4)
        # border
        pygame.draw.rect(self.screen, (200, 200, 200), BOSS_HP_BAR_RECT, 2, border_radius=4)
        # fill based on hp
        inner = BOSS_HP_BAR_RECT.inflate(-6, -6)
        hp_ratio = max(0.0, min(1.0, float(boss.hp) / float(boss.max_hp) if boss.max_hp else 0.0))
        fill_w = int(inner.width * hp_ratio)
        # color gradient (green->red)
        if hp_ratio > 0.5:
            color = (int(50 + (1-hp_ratio)*100), 200, 40)
        else:
            color = (220, int(50 + hp_ratio*150), 40)
        pygame.draw.rect(self.screen, (40, 40, 40), inner, border_radius=3)
        pygame.draw.rect(self.screen, color, (inner.x, inner.y, fill_w, inner.height), border_radius=3)
        # name text
        name_surf = self.font_boss.render(BOSS_NAME, True, (240, 240, 240))
        self.screen.blit(name_surf, (BOSS_HP_BAR_RECT.x, BOSS_HP_BAR_RECT.y - 20))

    def _draw_hud(self):
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        time_surf = self.font.render(f"Tempo: {int(self.total_time)}s", True, (255, 255, 255))
        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(time_surf, (SCREEN_WIDTH - 120, 10))
        pygame.display.set_caption(f"Pirata — FPS: {int(self.clock.get_fps())}")

    # ---- victory sequence ----
    def trigger_victory(self):
        # stop music
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        # try to load victory gif frames via PIL (optional)
        frames = []
        fps = 12
        try:
            from PIL import Image
            if self.victory_gif:
                try:
                    pil_img = Image.open(self.victory_gif)
                    for frame in range(0, getattr(pil_img, "n_frames", 1)):
                        pil_img.seek(frame)
                        mode = pil_img.mode
                        if mode != "RGBA":
                            frame_img = pil_img.convert("RGBA")
                        else:
                            frame_img = pil_img.copy()
                        raw_str = frame_img.tobytes()
                        size = frame_img.size
                        surf = pygame.image.fromstring(frame_img.tobytes(), size, "RGBA")
                        frames.append(surf)
                except Exception as e:
                    print(f"Aviso: não foi possível ler GIF com PIL: {e}")
                    frames = []
        except Exception:
            # PIL não disponível
            frames = []

        # fallback: try single image
        if not frames and self.victory_image:
            try:
                img = pygame.image.load(self.victory_image).convert_alpha()
                frames = [img]
            except Exception:
                frames = []

        # if victory music exists, play it
        if self.victory_music:
            try:
                pygame.mixer.music.load(self.victory_music)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

        # fade to dark while showing animation / image and message
        fade_time = 2.0  # seconds to full dark
        display_time = 4.0  # seconds to display frames after fade (per frame loop if multiple)
        start = time.perf_counter()
        clock = pygame.time.Clock()

        # center image area
        center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)
        frame_index = 0
        n_frames = max(1, len(frames))

        while True:
            now = time.perf_counter()
            elapsed = now - start
            # handle events to allow quit
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                    return

            # draw current game screen darkened underneath (we'll just draw background + black overlay)
            if self.background:
                try:
                    self.background.draw(self.screen)
                except Exception:
                    self.screen.fill((10, 10, 10))
            else:
                self.screen.fill((10, 10, 10))

            # draw overlay (fade)
            alpha = min(1.0, elapsed / fade_time)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(int(alpha * 230))
            self.screen.blit(overlay, (0, 0))

            # draw current frame (if any) with scaling to fit
            if frames:
                surf = frames[frame_index % len(frames)]
                # scale down if too big
                fw, fh = surf.get_size()
                maxw, maxh = SCREEN_WIDTH - 120, SCREEN_HEIGHT - 220
                scale = min(1.0, maxw / fw if fw>0 else 1.0, maxh / fh if fh>0 else 1.0)
                if scale < 1.0:
                    draw_surf = pygame.transform.smoothscale(surf, (int(fw*scale), int(fh*scale)))
                else:
                    draw_surf = surf
                rect = draw_surf.get_rect(center=center)
                self.screen.blit(draw_surf, rect)
            else:
                # no frames: draw a fallback message box / image placeholder
                placeholder = pygame.Surface((380, 200))
                placeholder.fill((40, 40, 40))
                rect = placeholder.get_rect(center=center)
                self.screen.blit(placeholder, rect)

            # draw victory message text centered below image
            big_font = pygame.font.SysFont(FONT_NAME, 30, bold=True)
            msg = "Parabéns, você conquistou o Obst, o tesouro sagrado"
            text_surf = big_font.render(msg, True, (255, 230, 120))
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 100))
            self.screen.blit(text_surf, text_rect)

            pygame.display.flip()

            # advance frames after fade
            if elapsed >= fade_time:
                # show frames for display_time seconds total, advance frame every (display_time / n_frames)
                per_frame = max(0.033, display_time / n_frames)
                if now - start - fade_time >= per_frame * (frame_index + 1):
                    frame_index += 1
                # end after one loop of frames + some hold
                if now - start >= fade_time + display_time + 1.0:
                    break

            clock.tick(30)

        # after victory sequence, stop music and return to menu (or quit)
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        # return to menu
        self.state = "menu"
        self.menu_music_start()
        # clear entities
        self.all_sprites.empty()
        self.enemies_group.empty()
        self.enemy_bullets_group.empty()
        self.bullets_group.empty()
        self.player = None
        self.boss_ref = None
        self.boss_phase_started = False
        self.boss_spawned = False

    # ---- game over and quit ----
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
