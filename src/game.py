# src/game.py
# Jogo principal (com desenho de barras de vida para inimigos e logs claros)
#
import os
import random
import time
import pygame

from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy, BossEnemy, BossBullet
from src.background import ParallaxBackground

# ----------------- Configurações -----------------
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets"))
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")

SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")
MENU_MUSIC_PATH = os.path.join(SOUNDS_DIR, "menu_music.mp3")
GAME_MUSIC_PATH = os.path.join(SOUNDS_DIR, "game_music.mp3")
BOSS_APPEAR_PATH = os.path.join(SOUNDS_DIR, "boss_appear.mp3")
VICTORY_MUSIC_PATH = os.path.join(SOUNDS_DIR, "victory_music.mp3")

OBST_IMAGE_PATH = os.path.join(IMAGES_DIR, "obst.png")
VICTORY_IMAGE_PATH = os.path.join(IMAGES_DIR, "victory_image.png")

BOSS_HP_BAR_RECT = pygame.Rect(12, 12, 360, 18)
BOSS_NAME = "Boss final"
FONT_NAME = "arial"

PLAYER_HITBOX_SHRINK_FACTOR = 0.5


class Pickup(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 400)):
        super().__init__()
        self.image = None
        if os.path.isfile(OBST_IMAGE_PATH):
            try:
                img = pygame.image.load(OBST_IMAGE_PATH).convert_alpha()
                maxw, maxh = 96, 96
                w, h = img.get_size()
                scale = min(1.0, maxw / w if w > 0 else 1.0, maxh / h if h > 0 else 1.0)
                if scale < 1.0:
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                self.image = img
            except Exception as e:
                print(f"Aviso: falha ao carregar OBST image: {e}")

        if self.image is None:
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 220, 50), (32, 32), 28)
            pygame.draw.circle(surf, (200, 150, 30), (32, 32), 20)
            self.image = surf

        self.rect = self.image.get_rect(center=pos)


def collide_with_shrunken_player(a, b):
    if not (hasattr(a, "rect") and hasattr(b, "rect")):
        return False
    try:
        shrink_w = int(b.rect.width * PLAYER_HITBOX_SHRINK_FACTOR)
        shrink_h = int(b.rect.height * PLAYER_HITBOX_SHRINK_FACTOR)
        infl_w = -(b.rect.width - shrink_w)
        infl_h = -(b.rect.height - shrink_h)
        shrunk = b.rect.inflate(infl_w, infl_h)
        return a.rect.colliderect(shrunk)
    except Exception:
        return a.rect.colliderect(b.rect)


class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer de áudio não pôde ser inicializado — sem som.")

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        try:
            self.background = ParallaxBackground(screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
                                                 water_speed=90.0, side_speed=45.0)
        except Exception as e:
            print(f"Aviso: falha ao criar ParallaxBackground: {e}")
            self.background = None

        self.shot_sound = None
        if os.path.isfile(SHOT_SOUND_PATH):
            try:
                self.shot_sound = pygame.mixer.Sound(SHOT_SOUND_PATH)
            except Exception:
                self.shot_sound = None

        self.menu_music = MENU_MUSIC_PATH if os.path.isfile(MENU_MUSIC_PATH) else None
        self.game_music = GAME_MUSIC_PATH if os.path.isfile(GAME_MUSIC_PATH) else None
        self.boss_appear_music = BOSS_APPEAR_PATH if os.path.isfile(BOSS_APPEAR_PATH) else None
        self.victory_music = VICTORY_MUSIC_PATH if os.path.isfile(VICTORY_MUSIC_PATH) else None

        self.boss_sound = None
        self.state = "menu"
        self.menu_playing = False

        btn_w, btn_h = 220, 56
        self.start_button_rect = pygame.Rect((SCREEN_WIDTH // 2 - btn_w // 2,
                                              SCREEN_HEIGHT - 220, btn_w, btn_h))

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
            except Exception:
                self.title_image = None

        self.font_title = pygame.font.SysFont(FONT_NAME, 36, bold=True)
        self.font_button = pygame.font.SysFont(FONT_NAME, 28, bold=True)
        self.font_instruct = pygame.font.SysFont(FONT_NAME, 18)
        self.font = pygame.font.SysFont(FONT_NAME, 20)
        self.font_boss = pygame.font.SysFont(FONT_NAME, 18, bold=True)

        self.instructions = [
            "INSTRUÇÕES:",
            "- Clique com o botão esquerdo para atirar para o mouse",
            "- Use WASD ou setas para mover",
            "- Pressione SPACE para atirar (mira no cursor)",
            "- Pressione ESC para pausar"
        ]

        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.pickups_group = pygame.sprite.Group()

        self.player = None

        self.spawn_interval = 1.0
        self.spawn_timer = 0.0
        self.difficulty_timer = 0.0
        self.difficulty_period = 12.0
        self.difficulty_reduction_factor = 0.92
        self.spawn_interval_min = 0.25

        self.boss_phase_started = False
        self.boss_spawned = False
        self.boss_ref = None

        self.menu_start()

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

    def start_game(self):
        self.menu_stop()
        if self.game_music:
            try:
                pygame.mixer.music.load(self.game_music)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.65)
            except Exception as e:
                print(f"Aviso: falha ao tocar música de gameplay: {e}")

        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.pickups_group = pygame.sprite.Group()

        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        self.boss_phase_started = False
        self.boss_spawned = False
        self.boss_ref = None
        if self.boss_sound:
            try:
                self.boss_sound.stop()
            except Exception:
                pass
            self.boss_sound = None

        self.state = "playing"

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

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "playing":
                self._handle_playing_event(event)

    def _handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.start_game()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.start_button_rect.collidepoint(event.pos):
                self.start_game()

    def _handle_playing_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
            elif not self.paused and event.key == pygame.K_SPACE:
                self._attempt_player_shoot(pygame.mouse.get_pos())
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.paused:
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

    def update(self, dt):
        try:
            self.all_sprites.update(dt)
        except Exception:
            pass

        # adiciona tiros recém-criados do boss e shooters
        for enemy in list(self.enemies_group):
            if isinstance(enemy, BossEnemy) and getattr(enemy, "new_bullets", None):
                for b in enemy.new_bullets:
                    self.all_sprites.add(b)
                    self.enemy_bullets_group.add(b)
                enemy.new_bullets.clear()
            if isinstance(enemy, ShooterEnemy) and getattr(enemy, "new_bullets", None):
                for b in enemy.new_bullets:
                    self.all_sprites.add(b)
                    self.enemy_bullets_group.add(b)
                enemy.new_bullets.clear()

        # também tenta pop_pending_bullet (compatibilidade)
        for enemy in list(self.enemies_group):
            if isinstance(enemy, ShooterEnemy):
                try:
                    b = enemy.pop_pending_bullet()
                except Exception:
                    b = None
                if b is not None:
                    self.all_sprites.add(b)
                    self.enemy_bullets_group.add(b)

        if not self.boss_phase_started and self.total_time >= 60.0:
            self.boss_phase_started = True
            print("Boss phase iniciado!")

        if not self.boss_phase_started:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer -= self.spawn_interval
                self.spawn_enemy()

            self.difficulty_timer += dt
            if self.difficulty_timer >= self.difficulty_period:
                self.difficulty_timer -= self.difficulty_period
                self.spawn_interval = max(self.spawn_interval * self.difficulty_reduction_factor,
                                          self.spawn_interval_min)
        else:
            non_boss = [e for e in self.enemies_group if not isinstance(e, BossEnemy)]
            if not non_boss and not self.boss_spawned:
                boss = BossEnemy(pos=(SCREEN_WIDTH // 2, -220), dy=60, start_y=100, hp=50, speed_x=140, player_ref=self.player)
                self.enemies_group.add(boss)
                self.all_sprites.add(boss)
                self.boss_spawned = True
                self.boss_ref = boss
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                if self.boss_appear_music:
                    try:
                        self.boss_sound = pygame.mixer.Sound(self.boss_appear_music)
                        self.boss_sound.play(-1)
                    except Exception:
                        pass

        collisions = pygame.sprite.groupcollide(self.bullets_group, self.enemies_group, True, False)
        for bullet, enemies_hit in collisions.items():
            for enemy in enemies_hit:
                if enemy.take_damage(1):
                    if isinstance(enemy, BossEnemy):
                        obst = Pickup(enemy.rect.center)
                        self.pickups_group.add(obst)
                        self.all_sprites.add(obst)
                        if self.boss_ref is enemy:
                            self.boss_ref = None
                        if self.boss_sound:
                            try:
                                self.boss_sound.stop()
                            except Exception:
                                pass
                            self.boss_sound = None
                    else:
                        self.score += 10

        if pygame.sprite.spritecollideany(self.player, self.pickups_group, collided=collide_with_shrunken_player):
            for p in list(self.pickups_group):
                p.kill()
            if self.boss_sound:
                try:
                    self.boss_sound.stop()
                except Exception:
                    pass
            self.trigger_victory()
            return

        if pygame.sprite.groupcollide(self.enemy_bullets_group, self.player_group, True, False, collided=collide_with_shrunken_player):
            self.lives -= 1
            if self.lives <= 0:
                self.display_game_over()
                pygame.time.delay(1500)
                self.running = False
                return

        if pygame.sprite.spritecollide(self.player, self.enemies_group, dokill=False, collided=collide_with_shrunken_player):
            self.lives -= 1
            if self.lives <= 0:
                self.display_game_over()
                pygame.time.delay(1500)
                self.running = False

        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT + 120:
                enemy.kill()

    def spawn_enemy(self):
        if self.boss_phase_started:
            return
        x = random.randint(30, SCREEN_WIDTH - 30)
        y = -50
        e = random.choices(
            [BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy],
            weights=[0.5, 0.2, 0.15, 0.15],
            k=1
        )[0](pos=(x, y), player_ref=self.player)
        self.enemies_group.add(e)
        self.all_sprites.add(e)

    def draw(self):
        if self.background:
            try:
                self.background.draw(self.screen)
            except Exception:
                self.screen.fill((30, 40, 80))
        else:
            self.screen.fill((30, 40, 80))

        if self.state == "menu":
            self._draw_menu()
        else:
            self.all_sprites.draw(self.screen)
            for p in self.pickups_group:
                self.screen.blit(p.image, p.rect)

            # desenhar barras de vida para inimigos:
            for enemy in self.enemies_group:
                try:
                    # desenha barra se o inimigo tem hp>0 e (max_hp>1) OU se é ShooterEnemy/BossEnemy
                    should_draw = False
                    try:
                        if hasattr(enemy, "hp") and hasattr(enemy, "max_hp") and enemy.max_hp > 1:
                            should_draw = True
                    except Exception:
                        should_draw = False
                    # forçar desenho para ShooterEnemy e BossEnemy (caso você tenha setado hp=1)
                    if isinstance(enemy, (ShooterEnemy, BossEnemy)):
                        should_draw = True

                    if should_draw:
                        bar_w = enemy.rect.width
                        bar_h = 6
                        bar_x = enemy.rect.centerx - bar_w // 2
                        bar_y = enemy.rect.top - 10

                        back_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
                        pygame.draw.rect(self.screen, (40, 40, 40), back_rect, border_radius=3)
                        pygame.draw.rect(self.screen, (100, 100, 100), back_rect, 1, border_radius=3)

                        try:
                            ratio = max(0.0, min(1.0, float(enemy.hp) / float(getattr(enemy, "max_hp", max(1, getattr(enemy, "hp", 1))))))
                        except Exception:
                            ratio = 0.0
                        fill_w = int(bar_w * ratio)
                        fill_rect = pygame.Rect(bar_x, bar_y, fill_w, bar_h)
                        if ratio > 0.6:
                            color = (80, 200, 60)
                        elif ratio > 0.3:
                            color = (220, 180, 40)
                        else:
                            color = (200, 60, 60)
                        pygame.draw.rect(self.screen, color, fill_rect, border_radius=3)
                except Exception:
                    pass

            if self.boss_ref and self.boss_ref.alive():
                try:
                    self._draw_boss_hp(self.boss_ref)
                except Exception:
                    pass

            try:
                self._draw_hud()
            except Exception:
                pass

            if self.paused:
                try:
                    self.draw_pause_overlay()
                except Exception:
                    pass

        pygame.display.flip()

    def _draw_menu(self):
        panel = pygame.Surface((SCREEN_WIDTH - 40, SCREEN_HEIGHT - 80), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 80))
        panel_rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(panel, panel_rect)

        title_surf = self.font_title.render("Pirata — O Tesouro", True, (240, 240, 220))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 72))
        self.screen.blit(title_surf, title_rect)

        if self.title_image is not None:
            ti_rect = self.title_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 70))
            self.screen.blit(self.title_image, ti_rect)
        else:
            ph_w, ph_h = 300, 140
            ph = pygame.Surface((ph_w, ph_h))
            ph.fill((180, 160, 100))
            pygame.draw.rect(ph, (140, 120, 80), ph.get_rect(), 4)
            ph_rect = ph.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 70))
            self.screen.blit(ph, ph_rect)

        mx, my = pygame.mouse.get_pos()
        rect = self.start_button_rect
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 120))
        self.screen.blit(shadow, (rect.x + 4, rect.y + 6))
        hover = rect.collidepoint(mx, my)
        color = (40, 200, 130) if hover else (28, 160, 100)
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=10)
        btn_text = self.font_button.render("START", True, (255, 255, 255))
        self.screen.blit(btn_text, btn_text.get_rect(center=rect.center))

        y0 = rect.bottom + 14
        for i, line in enumerate(self.instructions):
            surf = self.font_instruct.render(line, True, (230, 230, 230))
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, y0 + i * 22)))

        hint = self.font_instruct.render("Pressione ENTER ou clique START para iniciar", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)))

    def _draw_boss_hp(self, boss):
        pygame.draw.rect(self.screen, (30, 30, 30), BOSS_HP_BAR_RECT, border_radius=4)
        pygame.draw.rect(self.screen, (200, 200, 200), BOSS_HP_BAR_RECT, 2, border_radius=4)
        inner = BOSS_HP_BAR_RECT.inflate(-6, -6)
        hp_ratio = max(0.0, min(1.0, boss.hp / boss.max_hp))
        fill_w = int(inner.width * hp_ratio)
        color = (int(50 + (1 - hp_ratio) * 100), 200, 40) if hp_ratio > 0.5 else (220, int(50 + hp_ratio * 150), 40)
        pygame.draw.rect(self.screen, (40, 40, 40), inner, border_radius=3)
        pygame.draw.rect(self.screen, color, (inner.x, inner.y, fill_w, inner.height), border_radius=3)
        name_surf = self.font_boss.render(BOSS_NAME, True, (240, 240, 240))
        self.screen.blit(name_surf, (BOSS_HP_BAR_RECT.x, BOSS_HP_BAR_RECT.y - 20))

    def _draw_hud(self):
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        time_surf = self.font.render(f"Tempo: {int(self.total_time)}s", True, (255, 255, 255))
        boss_remaining = max(0, 60 - int(self.total_time))
        boss_time_surf = self.font.render(f"Tempo para o Boss: {boss_remaining}s", True, (200, 200, 255))

        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(time_surf, (SCREEN_WIDTH - 200, 10))
        self.screen.blit(boss_time_surf, (SCREEN_WIDTH - 200, 34))

        pygame.display.set_caption(f"Pirata — FPS: {int(self.clock.get_fps())}")

    def trigger_victory(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        if self.boss_sound:
            try:
                self.boss_sound.stop()
            except Exception:
                pass
            self.boss_sound = None

        if self.victory_music:
            try:
                pygame.mixer.music.load(self.victory_music)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

        obst_surf = None
        if os.path.isfile(OBST_IMAGE_PATH):
            try:
                img = pygame.image.load(OBST_IMAGE_PATH).convert_alpha()
                maxw, maxh = 160, 160
                w, h = img.get_size()
                scale = min(1.0, maxw / w if w > 0 else 1.0, maxh / h if h > 0 else 1.0)
                if scale < 1.0:
                    img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
                obst_surf = img
            except Exception:
                obst_surf = None
        if obst_surf is None:
            vs = pygame.Surface((96, 96))
            vs.fill((200, 180, 60))
            pygame.draw.rect(vs, (140, 110, 20), vs.get_rect(), 4)
            obst_surf = vs

        message_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)
        obst_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)
        instr_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120)

        msg = "Parabéns, você conquistou a Obst, a fruta sagrada dos sete mares!"
        victory_font = pygame.font.SysFont(FONT_NAME, 14, bold=True)
        instr_font = pygame.font.SysFont(FONT_NAME, 16)

        waiting = True
        while waiting and self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                    break
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                    waiting = False
                    break

            if self.background:
                try:
                    self.background.draw(self.screen)
                except Exception:
                    self.screen.fill((10, 10, 10))
            else:
                self.screen.fill((10, 10, 10))

            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(200)
            self.screen.blit(overlay, (0, 0))

            text_surf = victory_font.render(msg, True, (255, 230, 120))
            text_rect = text_surf.get_rect(center=message_center)
            self.screen.blit(text_surf, text_rect)

            obst_rect = obst_surf.get_rect(center=obst_center)
            self.screen.blit(obst_surf, obst_rect)

            instr = "Pressione R para voltar ao menu inicial"
            instr_surf = instr_font.render(instr, True, (220, 220, 220))
            instr_rect = instr_surf.get_rect(center=instr_center)
            self.screen.blit(instr_surf, instr_rect)

            pygame.display.flip()
            self.clock.tick(30)

        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        self.state = "menu"
        self.menu_start()
        self.all_sprites.empty()
        self.enemies_group.empty()
        self.enemy_bullets_group.empty()
        self.bullets_group.empty()
        self.pickups_group.empty()
        self.player = None
        self.boss_ref = None
        self.boss_phase_started = False
        self.boss_spawned = False

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
