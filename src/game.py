# src/game.py
# Gerencia loop principal, eventos, spawn, colisões e desenho.
# Agora com integração do ParallaxBackground:
#  - background.update(dt) é chamado sempre (independente de pausa/movimento do player)
#  - background.draw(self.screen) desenhado antes dos sprites (fundo)
#
# Mantém: disparo por clique/SPACE, som de tiro, pausa com ESC, inimigos variados,
# balas inimigas, HUD, e lógica de não penalizar quando inimigo sai pelo fundo.

import os
import random
import pygame
from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy
from src.background import ParallaxBackground

# constantes de tela e fps
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")


class Game:
    def __init__(self):
        pygame.init()
        # tentar inicializar mixer (pode falhar em alguns ambientes)
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer de áudio não pôde ser inicializado — sem som.")

        # janela e clock
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # background parallax (instanciado aqui)
        try:
            self.background = ParallaxBackground(screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
                                                 water_speed=90.0,
                                                 side_speed=45.0)
        except Exception as e:
            print(f"Aviso: falha ao criar ParallaxBackground: {e}")
            self.background = None

        # tenta carregar som do tiro (opcional)
        self.shot_sound = None
        if os.path.isfile(SHOT_SOUND_PATH):
            try:
                self.shot_sound = pygame.mixer.Sound(SHOT_SOUND_PATH)
            except Exception as e:
                print(f"Aviso: falha ao carregar som de tiro: {e}")
                self.shot_sound = None

        # estado do jogo
        self.score = 0
        self.lives = 3
        self.total_time = 0.0
        self.paused = False

        # grupos de sprites
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()       # balas do jogador
        self.enemy_bullets_group = pygame.sprite.Group() # balas dos inimigos
        self.enemies_group = pygame.sprite.Group()

        # player
        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        # fonte para HUD
        self.font = pygame.font.SysFont("arial", 20)

        # spawn/dificuldade
        self.spawn_interval = 1.0
        self.spawn_timer = 0.0
        self.difficulty_timer = 0.0
        self.difficulty_period = 12.0
        self.difficulty_reduction_factor = 0.92
        self.spawn_interval_min = 0.25

    def run(self):
        """Loop principal do jogo."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            # atualiza background SEMPRE (independente de pausa). Se background for None, ignora.
            try:
                if self.background is not None:
                    self.background.update(dt)
            except Exception as e:
                # falha no background não deve fechar o jogo
                print(f"Aviso: erro ao atualizar background: {e}")
                self.background = None

            self.handle_events()
            if not self.paused:
                self.total_time += dt
                self.update(dt)
            self.draw()
        self.quit()

    def handle_events(self):
        """
        Processa eventos do Pygame:
        - ESC: toggle de pausa
        - SPACE: dispara mirando no cursor atual
        - MOUSEBUTTONDOWN (botão esquerdo): dispara para a posição do clique
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                # Toggle de pause com ESC
                if event.key == pygame.K_ESCAPE:
                    self.paused = not self.paused
                    continue

                # SPACE: disparo mirando no cursor atual (se não estiver pausado)
                if not self.paused and event.key == pygame.K_SPACE:
                    try:
                        target = pygame.mouse.get_pos()
                    except Exception:
                        target = None
                    self._attempt_player_shoot(target_pos=target)

            # Mouse click: botão esquerdo dispara para event.pos
            if event.type == pygame.MOUSEBUTTONDOWN:
                # button == 1 -> left click
                if not self.paused and event.button == 1:
                    mouse_pos = event.pos
                    self._attempt_player_shoot(target_pos=mouse_pos)

    def _attempt_player_shoot(self, target_pos=None):
        """
        Tenta fazer o player atirar (encapsula exceções).
        Se a bullet for criada, adiciona aos grupos e toca som (se existir).
        """
        try:
            bullet = self.player.shoot(target_pos=target_pos)
        except Exception as e:
            print(f"Aviso: erro ao chamar player.shoot(): {e}")
            bullet = None

        if bullet is not None:
            try:
                self.all_sprites.add(bullet)
                # assegura que bullet tem atributo owner se necessário (compatibilidade)
                self.bullets_group.add(bullet)
            except Exception as e:
                print(f"Aviso: falha ao adicionar bullet aos grupos: {e}")
            if self.shot_sound:
                try:
                    self.shot_sound.play()
                except Exception:
                    pass

    def update(self, dt):
        """Atualiza lógica do jogo: sprites, spawns, colisões e balas inimigas pendentes."""
        # atualiza todos os sprites
        self.all_sprites.update(dt)

        # recolhe balas pendentes dos shooters e adiciona aos grupos
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
            new_interval = max(self.spawn_interval * self.difficulty_reduction_factor,
                               self.spawn_interval_min)
            if new_interval < self.spawn_interval:
                print(f"Aumentando dificuldade: spawn_interval {self.spawn_interval:.3f} -> {new_interval:.3f}")
            self.spawn_interval = new_interval

        # colisões: balas do jogador vs inimigos
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

        # colisões: balas inimigas vs player (penaliza vida)
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

        # colisões entre inimigos e player — causam dano e removem o inimigo
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

        # inimigos que passam pelo fundo da tela: removemos para não acumular,
        # mas NÃO penalizamos o jogador conforme sua solicitação.
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT:
                enemy.kill()
                # intencionalmente não decrementamos self.lives

    def spawn_enemy(self):
        """Cria um inimigo com probabilidade ajustada ao tempo total de jogo.
           Passa player_ref=self.player para que inimigos reajam ao player."""
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
        # passamos player_ref=self.player para que inimigos possam reagir ao player
        if chosen == "basic":
            e = BasicEnemy(pos=(x, y), player_ref=self.player)
        elif chosen == "zigzag":
            e = ZigZagEnemy(pos=(x, y), dy=120, amplitude=80, frequency=0.9, player_ref=self.player)
        elif chosen == "fast":
            e = FastEnemy(pos=(x, y), dy=240, player_ref=self.player)
        elif chosen == "shooter":
            # Shooter com hp aumentado e barra é tratado em src/enemy.py
            e = ShooterEnemy(pos=(x, y), dy=90, stop_distance=200, shoot_cooldown=1.6, bullet_speed=200, player_ref=self.player, hp=3)
        else:
            e = BasicEnemy(pos=(x, y), player_ref=self.player)

        self.enemies_group.add(e)
        self.all_sprites.add(e)

    def draw(self):
        """Desenha background, sprites, HUD e overlay de pausa se necessário."""
        # desenha background parallax (se existir)
        if self.background is not None:
            try:
                self.background.draw(self.screen)
            except Exception as e:
                print(f"Aviso: erro ao desenhar background: {e}")
                # fallback: limpa tela com cor sólida
                self.screen.fill((30, 40, 80))
                self.background = None
        else:
            # se não há background, preenche com cor padrão
            self.screen.fill((30, 40, 80))

        # desenha sprites por cima do background
        self.all_sprites.draw(self.screen)

        # HUD: score, vidas, spawn interval, tempo
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        spawn_surf = self.font.render(f"Spawn: {self.spawn_interval:.2f}s", True, (255, 255, 255))
        time_surf = self.font.render(f"Tempo: {int(self.total_time)}s", True, (255, 255, 255))

        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(spawn_surf, (10, 58))
        self.screen.blit(time_surf, (SCREEN_WIDTH - 120, 10))

        # FPS (debug)
        fps = int(self.clock.get_fps())
        fps_surf = self.font.render(f"FPS: {fps}", True, (255, 255, 255))
        self.screen.blit(fps_surf, (SCREEN_WIDTH - 80, 34))
        pygame.display.set_caption(f"Pirata — FPS: {fps}")

        # overlay de pausa
        if self.paused:
            self.draw_pause_overlay()

        pygame.display.flip()

    def draw_pause_overlay(self):
        """Overlay semitransparente com texto PAUSED."""
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
        """Mostra tela de GAME OVER antes de encerrar."""
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
        """Encerra Pygame de forma limpa."""
        pygame.quit()
