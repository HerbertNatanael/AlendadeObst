# src/game.py
# Gerencia loop principal, eventos, spawn, colisões e desenho.
# Agora com suporte a:
# - disparo com clique do mouse (MOUSEBUTTONDOWN, botão esquerdo)
# - disparo com tecla SPACE mirando no cursor atual
# - proteção para evitar crashes caso a criação da bala falhe
#
# Comentários em Português explicam trechos importantes.

import os
import random
import pygame
from src.player import Player
from src.bullet import Bullet
from src.enemy import BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy

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
        # tentar inicializar mixer (pode falhar em ambientes sem som)
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer de áudio não pôde ser inicializado — sem som.")

        # tenta carregar som do tiro (opcional)
        self.shot_sound = None
        if os.path.isfile(SHOT_SOUND_PATH):
            try:
                self.shot_sound = pygame.mixer.Sound(SHOT_SOUND_PATH)
            except Exception as e:
                print(f"Aviso: falha ao carregar som de tiro: {e}")
                self.shot_sound = None

        # janela e clock
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # estado do jogo
        self.score = 0
        self.lives = 3
        self.total_time = 0.0

        # pausa
        self.paused = False

        # grupos de sprites
        self.all_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()       # balas do jogador
        self.enemy_bullets_group = pygame.sprite.Group() # balas disparadas por inimigos
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
                    # evita que o ESC gere outro efeito no mesmo evento (ex.: atirar)
                    continue

                # SPACE: disparo mirando no cursor atual (se não estiver pausado)
                if not self.paused and event.key == pygame.K_SPACE:
                    # mira no cursor atual (get_pos em vez de event porque queremos posição do mouse)
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
        Tenta fazer o player atirar. Encapsula em try/except para evitar que
        um erro em player.shoot() feche o jogo.
        - Recebe target_pos (tupla) ou None (usa cursor atual).
        - Se a bala for criada, a adiciona aos grupos e toca som (se houver).
        """
        try:
            bullet = self.player.shoot(target_pos=target_pos)
        except Exception as e:
            # Erro defensivo: não permitimos que o jogo feche por causa de um erro na criação da bala.
            print(f"Aviso: erro ao chamar player.shoot(): {e}")
            bullet = None

        if bullet is not None:
            # Adiciona a bala nos grupos responsáveis
            try:
                self.all_sprites.add(bullet)
                self.bullets_group.add(bullet)
            except Exception as e:
                # Se houver problema ao adicionar (ex.: objeto inválido), apenas reportamos.
                print(f"Aviso: falha ao adicionar bullet aos grupos: {e}")

            # Tocar som de tiro (não bloqueante); protegido por try/except
            if self.shot_sound:
                try:
                    self.shot_sound.play()
                except Exception:
                    pass

    def update(self, dt):
        """Atualiza lógica do jogo: sprites, spawns, colisões e balas inimigas pendentes."""
        # atualiza todos os sprites
        self.all_sprites.update(dt)

        # alguns inimigos (ShooterEnemy) podem ter _pending_bullet: coletamos e adicionamos
        for enemy in list(self.enemies_group):
            if isinstance(enemy, ShooterEnemy):
                try:
                    b = enemy.pop_pending_bullet()
                except Exception:
                    b = None
                if b is not None:
                    self.all_sprites.add(b)
                    self.enemy_bullets_group.add(b)

        # spawn de inimigos por timer
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer -= self.spawn_interval
            self.spawn_enemy()

        # dificuldade dinâmica (diminui spawn_interval periodicamente)
        self.difficulty_timer += dt
        if self.difficulty_timer >= self.difficulty_period:
            self.difficulty_timer -= self.difficulty_period
            new_interval = max(self.spawn_interval * self.difficulty_reduction_factor,
                               self.spawn_interval_min)
            if new_interval < self.spawn_interval:
                print(f"Aumentando dificuldade: spawn_interval {self.spawn_interval:.3f} -> {new_interval:.3f}")
            self.spawn_interval = new_interval

        # colisões: balas do jogador vs inimigos
        # Não removemos o inimigo imediatamente (passamos kill via take_damage)
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

        # colisões: balas inimigas vs player
        hits = pygame.sprite.groupcollide(self.enemy_bullets_group, self.player_group, True, False)
        if hits:
            for bullet, players in hits.items():
                # reduz vida por bala que acertou (ajustar lógica se quiser invencibilidade temporária)
                self.lives -= 1
                print(f"Player atingido! Vidas restantes: {self.lives}")
                if self.lives <= 0:
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return

        # inimigos que passam pelo fundo da tela
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT:
                enemy.kill()
                self.lives -= 1
                print(f"Inimigo escapou! Vidas restantes: {self.lives}")
                if self.lives <= 0:
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return

    def spawn_enemy(self):
        """Cria um inimigo com probabilidade ajustada ao tempo total de jogo."""
        base = {
            "basic": 0.6,
            "zigzag": 0.18,
            "fast": 0.12,
            "shooter": 0.10
        }

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
        """Desenha background, sprites, HUD e overlay de pausa se necessário."""
        self.screen.fill((30, 40, 80))
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
