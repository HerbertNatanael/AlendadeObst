# src/game.py
# Atualizado para:
# - suportar inimigos variados (Basic/ZigZag/Fast/Shooter)
# - gerenciar enemy_bullets_group (balas disparadas por inimigos)
# - checar colisões entre balas inimigas e player
# - spawn probabilístico dependente do tempo total de jogo

import os
import random
import pygame
from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy

# constantes
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")

class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer falhou")

        # tenta carregar som de tiro do jogador (opcional)
        self.shot_sound = None
        if os.path.isfile(SHOT_SOUND_PATH):
            try:
                self.shot_sound = pygame.mixer.Sound(SHOT_SOUND_PATH)
            except Exception:
                self.shot_sound = None

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # Estado do jogo
        self.score = 0
        self.lives = 3

        # Tempo total de jogo (usa para escalonamento de inimigos)
        self.total_time = 0.0

        # Pausa
        self.paused = False

        # Grupos
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()       # balas do jogador
        self.enemy_bullets_group = pygame.sprite.Group() # balas dos inimigos
        self.enemies_group = pygame.sprite.Group()

        # player
        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        # HUD font
        self.font = pygame.font.SysFont("arial", 20)

        # spawn config
        self.spawn_interval = 1.0
        self.spawn_timer = 0.0

        # difficulty scaling
        self.difficulty_timer = 0.0
        self.difficulty_period = 12.0
        self.difficulty_reduction_factor = 0.92
        self.spawn_interval_min = 0.25

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if not self.paused:
                self.total_time += dt
                self.update(dt)
            self.draw()
        self.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.paused = not self.paused
                    continue
                if not self.paused:
                    if event.key == pygame.K_SPACE:
                        bullet = self.player.shoot()
                        if bullet is not None:
                            self.all_sprites.add(bullet)
                            self.bullets_group.add(bullet)
                            if self.shot_sound:
                                try:
                                    self.shot_sound.play()
                                except Exception:
                                    pass

    def update(self, dt):
        # atualiza sprites
        self.all_sprites.update(dt)

        # --- special: alguns inimigos (ShooterEnemy) podem ter _pending_bullet ---
        # recolhe essas balas e adiciona aos grupos adequados
        for enemy in list(self.enemies_group):
            if isinstance(enemy, ShooterEnemy):
                b = enemy.pop_pending_bullet()
                if b is not None:
                    # b é Bullet com owner='enemy'
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

        # colisões: balas do jogador vs inimigos
        collisions = pygame.sprite.groupcollide(self.bullets_group, self.enemies_group, True, False)
        if collisions:
            # cada entry: bullet -> [enemy, ...]
            for bullet, enemies_hit in collisions.items():
                for enemy in enemies_hit:
                    died = enemy.take_damage(1)
                    if died:
                        # pontuação por inimigo morto
                        self.score += 10

        # colisões: balas inimigas vs player
        # Usamos spritecollide para saber quais bullets acertaram o player
        hits = pygame.sprite.groupcollide(self.enemy_bullets_group, self.player_group, True, False)
        if hits:
            # cada bullet que colidiu com o player -> decrementa vida
            for bullet, players in hits.items():
                # players normalmente tem um elemento: o player
                self.lives -= 1
                print(f"Player atingido! Vidas: {self.lives}")
                if self.lives <= 0:
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return

        # inimigos que passam pelo fundo -> penalidade
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT:
                enemy.kill()
                self.lives -= 1
                print(f"Inimigo escapou! Vidas: {self.lives}")
                if self.lives <= 0:
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return

    def spawn_enemy(self):
        """
        Spawn probabilístico em que as chances de cada tipo variam com o tempo.
        A ideia: no início mais Basic; com o tempo mais ZigZag, Shooter e Fast.
        """
        # base weights (podem ser ajustados)
        base = {
            "basic": 0.6,
            "zigzag": 0.18,
            "fast": 0.12,
            "shooter": 0.10
        }

        # Aumenta chance de inimigos mais difíceis conforme total_time cresce
        t = self.total_time
        # exemplo simples: a cada 30s, aumentamos peso de hard enemies um pouco
        bonus = min(0.6, t / 120.0)  # até +0.6 ao longo de 2 minutos
        # re-balance: tiramos um pouco do basic proporcionalmente
        base["basic"] = max(0.25, base["basic"] * (1.0 - bonus * 0.6))

        # ajusta pesos aumentando os outros
        base["zigzag"] += bonus * 0.25
        base["fast"] += bonus * 0.20
        base["shooter"] += bonus * 0.15

        # normaliza
        total = sum(base.values())
        for k in base:
            base[k] /= total

        r = random.random()
        # escolhe tipo por faixa acumulada
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
            e = BasicEnemy(pos=(x, y))
        elif chosen == "zigzag":
            e = ZigZagEnemy(pos=(x, y), dy=120, amplitude=80, frequency=0.9)
        elif chosen == "fast":
            e = FastEnemy(pos=(x, y), dy=240)
        elif chosen == "shooter":
            e = ShooterEnemy(pos=(x, y), dy=90, shoot_cooldown=1.6, bullet_speed=200, player_ref=self.player)
        else:
            e = BasicEnemy(pos=(x, y))

        self.enemies_group.add(e)
        self.all_sprites.add(e)

    def draw(self):
        self.screen.fill((30, 40, 80))
        self.all_sprites.draw(self.screen)

        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        spawn_surf = self.font.render(f"Spawn: {self.spawn_interval:.2f}s", True, (255, 255, 255))
        time_surf = self.font.render(f"Tempo: {int(self.total_time)}s", True, (255,255,255))

        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(spawn_surf, (10, 58))
        self.screen.blit(time_surf, (SCREEN_WIDTH - 120, 10))

        fps = int(self.clock.get_fps())
        fps_surf = self.font.render(f"FPS: {fps}", True, (255, 255, 255))
        self.screen.blit(fps_surf, (SCREEN_WIDTH - 80, 34))
        pygame.display.set_caption(f"Pirata — FPS: {fps}")

        if self.paused:
            self.draw_pause_overlay()

        pygame.display.flip()

    def draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        self.screen.blit(overlay, (0,0))

        go_font = pygame.font.SysFont("arial", 56, bold=True)
        text = go_font.render("PAUSED", True, (240,240,240))
        sub = self.font.render("Pressione ESC para continuar", True, (200,200,200))
        rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20))
        subrect = sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30))
        self.screen.blit(text, rect)
        self.screen.blit(sub, subrect)

    def display_game_over(self):
        self.screen.fill((10,10,10))
        go_font = pygame.font.SysFont("arial", 48)
        text = go_font.render("GAME OVER", True, (200,50,50))
        sub = self.font.render(f"Score final: {self.score}", True, (255,255,255))
        rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20))
        subrect = sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30))
        self.screen.blit(text, rect)
        self.screen.blit(sub, subrect)
        pygame.display.flip()

    def quit(self):
        pygame.quit()
