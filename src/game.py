# src/game.py
# Responsável pelo loop principal do jogo, inicialização do Pygame, criação de grupos
# de sprites e desenho do HUD mínimo (FPS).
#
# Comentários detalhados ao longo do código explicam decisões e pontos de atenção.

import os
import pygame
from src.player import Player

# Configurações globais do jogo (fáceis de ajustar)
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

# Caminho base para pastas de assets (imagens, sons, fontes)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")


class Game:
    """
    Classe principal que gerencia o estado do jogo.
    - Inicializa Pygame e o mixer de áudio.
    - Cria a janela, o clock e os grupos de sprites.
    - Contém o loop principal: handle_events -> update -> draw.
    """

    def __init__(self):
        # Inicialização do Pygame — necessário antes de usar qualquer funcionalidade
        pygame.init()

        # Inicializa o mixer de áudio; se houver erro em ambientes sem áudio, pode lançar.
        # Em caso de problema, podemos envolver em try/except (ver observação ao final).
        pygame.mixer.init()

        # Cria janela com a resolução definida
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Clock para controlar FPS e calcular delta time (dt)
        self.clock = pygame.time.Clock()

        # Flag para manter o loop em execução; será setada para False ao fechar a janela
        self.running = True

        # Grupos de sprites (usamos pygame.sprite.Group para facilitar draw/update/colisões)
        self.all_sprites = pygame.sprite.Group()    # todos os sprites desenhados/atualizados
        self.player_group = pygame.sprite.Group()   # grupo específico para o player (útil para colisões)

        # Cria o player em posição inicial (centro horizontal, um pouco acima do final da tela)
        player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.player = player
        self.all_sprites.add(player)
        self.player_group.add(player)

        # Fonte simples para desenhar FPS e debug. SysFont evita necessidade de arquivo de fonte.
        self.font = pygame.font.SysFont("arial", 18)

    def run(self):
        """Loop principal do jogo.

        Estrutura padrão:
        - dt: tempo em segundos desde o último frame (útil para movimento consistente)
        - handle_events: processa eventos do Pygame (teclado, fechamento)
        - update: atualiza lógica do jogo (chama update nos sprites)
        - draw: desenha tudo na tela e realiza flip
        """
        while self.running:
            # clock.tick limita a taxa de frames e retorna milissegundos desde o último tick.
            # Dividimos por 1000 para ter dt em segundos (float).
            dt = self.clock.tick(FPS) / 1000.0

            self.handle_events()
            self.update(dt)
            self.draw()

        # Ao sair do loop, chama quit para desalocar recursos
        self.quit()

    def handle_events(self):
        """Trata eventos do Pygame (entrada do usuário)."""
        for event in pygame.event.get():
            # Quando o usuário clica no X da janela, recebemos um QUIT: fechamos o loop.
            if event.type == pygame.QUIT:
                self.running = False

            # (Aqui é onde, futuramente, trataríamos teclas PRESS/RELEASE específicas,
            # menus, pausa, etc.)

    def update(self, dt):
        """Atualiza todos os sprites e a lógica do jogo."""
        # O grupo all_sprites chama update(dt) em cada sprite que implementar esse método.
        # Usar dt permite que o movimento seja consistente independentemente de FPS.
        self.all_sprites.update(dt)

        # (Quando adicionarmos inimigos/balas/powerups, atualizaremos grupos específicos
        # e checaremos colisões aqui.)

    def draw(self):
        """Desenha o frame atual na tela."""
        # Preenche o fundo com um azul escuro — substituiremos por background gráfico depois.
        self.screen.fill((30, 40, 80))  # cor RGB

        # Desenha todos os sprites na ordem de adição (podemos controlar com layers mais tarde).
        self.all_sprites.draw(self.screen)

        # Renderiza FPS no canto superior esquerdo — útil para debug de performance.
        fps = int(self.clock.get_fps())
        fps_surf = self.font.render(f"FPS: {fps}", True, (255, 255, 255))
        self.screen.blit(fps_surf, (8, 8))

        # Também colocamos FPS no título da janela (útil quando a janela estiver em segundo plano)
        pygame.display.set_caption(f"Pirata — FPS: {fps}")

        # Atualiza o display com o que foi desenhado neste frame
        pygame.display.flip()

    def quit(self):
        """Finaliza Pygame de forma limpa."""
        pygame.quit()

# src/game.py
# Gerencia loop principal, grupos de sprites, spawn de inimigos, colisões e HUD.
# Comentários explicativos incluídos para facilitar entendimento.

import os
import random
import pygame
from src.player import Player
from src.bullet import Bullet
from src.enemy import Enemy

# Configurações globais do jogo
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")


class Game:
    def __init__(self):
        # Inicializa pygame
        pygame.init()

        # Inicializa mixer de áudio, mas protegemos com try/except
        # para evitar crashes em ambientes sem som.
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer de áudio não pôde ser inicializado — continuando sem som.")

        # Cria janela e clock
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # Estado do jogo
        self.score = 0
        self.lives = 3
        self.game_over_displayed = False  # controla a exibição do Game Over

        # Grupos de sprites
        self.all_sprites = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()

        # Cria o player e adiciona aos grupos
        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        # Fonte para HUD/debug
        self.font = pygame.font.SysFont("arial", 20)

        # Spawn de inimigos: configuráveis
        self.spawn_interval = 1.0  # segundos entre spawns (pode diminuir com dificuldade)
        self.spawn_timer = 0.0     # contador incremental (em segundos)

    def run(self):
        """Loop principal do jogo."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # delta time em segundos
            self.handle_events()
            self.update(dt)
            self.draw()
        self.quit()

    def handle_events(self):
        """Trata eventos do Pygame — teclado, fechar janela."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Tratamos teclas pressionadas: disparo no KEYDOWN para evitar auto-fire instantâneo
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Ao pressionar SPACE, pedimos que o player tente atirar.
                    # Passamos os grupos de destino para que o jogador crie a bala
                    # e nós a registremos nos grupos do jogo.
                    bullet = self.player.shoot()
                    if bullet is not None:
                        # adiciona nas coleções do jogo
                        self.all_sprites.add(bullet)
                        self.bullets_group.add(bullet)

    def update(self, dt):
        """Atualiza lógica do jogo e gerencia spawn/collisions."""
        # Atualiza todos os sprites (cada sprite usa dt para movimento suave)
        self.all_sprites.update(dt)

        # Spawn de inimigos baseado no timer
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer -= self.spawn_interval
            self.spawn_enemy()

        # Colisões: balas que acertam inimigos
        # groupcollide retorna dict {bullet: [enemy, ...], ...}
        collisions = pygame.sprite.groupcollide(self.bullets_group, self.enemies_group,
                                                True, True)
        if collisions:
            # Para cada bullet que colidiu, listamos enemies e incrementamos score
            for bullet, enemies_hit in collisions.items():
                # cada inimigo vale 10 pontos (ajustável)
                self.score += 10 * len(enemies_hit)
                # (Opcional: tocar som de explosão aqui)

        # Checa inimigos que alcançaram o fundo da tela
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT:
                # inimigo escapou — penaliza o jogador
                enemy.kill()
                self.lives -= 1
                print(f"Inimigo escapou! Vidas restantes: {self.lives}")

                # Se vidas chegaram a zero, exiba Game Over e encerre após pequeno delay
                if self.lives <= 0:
                    # desenhar a tela final por 2 segundos antes de fechar
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return  # sai do update imediatamente

        # (Futuro) aqui podemos aumentar dificuldade ao longo do tempo,
        # por exemplo diminuindo self.spawn_interval ou aumentando velocidade.

    def spawn_enemy(self):
        """Cria um inimigo em uma posição x aleatória no topo da tela."""
        x = random.randint(30, SCREEN_WIDTH - 30)
        y = -50  # começa um pouco acima da tela para aparecer "descendo"
        enemy = Enemy(pos=(x, y))
        self.enemies_group.add(enemy)
        self.all_sprites.add(enemy)

    def draw(self):
        """Desenha background, sprites e HUD."""
        # Fundo simples — podemos trocar por imagem depois.
        self.screen.fill((30, 40, 80))

        # Desenha sprites
        self.all_sprites.draw(self.screen)

        # HUD (score e vidas)
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))

        # FPS para debug (opcional)
        fps = int(self.clock.get_fps())
        fps_surf = self.font.render(f"FPS: {fps}", True, (255, 255, 255))
        self.screen.blit(fps_surf, (SCREEN_WIDTH - 80, 10))
        pygame.display.set_caption(f"Pirata — FPS: {fps}")

        pygame.display.flip()

    def display_game_over(self):
        """Desenha uma única tela de Game Over (chamada antes de encerrar)."""
        # Desenha fundo escuro e mensagem central
        self.screen.fill((10, 10, 10))
        go_font = pygame.font.SysFont("arial", 48)
        text = go_font.render("GAME OVER", True, (200, 50, 50))
        sub = self.font.render(f"Score final: {self.score}", True, (255, 255, 255))
        # centraliza
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        subrect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(text, rect)
        self.screen.blit(sub, subrect)
        pygame.display.flip()

    def quit(self):
        """Encerra Pygame."""
        pygame.quit()

# src/game.py
# Gerencia o loop principal, grupos de sprites, spawn de inimigos, colisões e HUD.
# Agora com:
# - Som de tiro (assets/sounds/shot.wav) — opcional, tratado com gracefulness.
# - Tela de pausa (toggle com ESC) — pausa updates, spawn e disparo.
# - Dificuldade dinâmica: spawn_interval diminui gradualmente com o tempo.
#
# Comentários explicativos incluídos para facilitar entendimento.

import os
import random
import pygame
from src.player import Player
from src.bullet import Bullet
from src.enemy import Enemy

# Configurações globais do jogo
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
FPS = 60

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
SHOT_SOUND_PATH = os.path.join(SOUNDS_DIR, "shot.wav")  # caminho esperado do som do tiro


class Game:
    def __init__(self):
        # Inicializa pygame
        pygame.init()

        # Inicializa mixer de áudio, protegido para evitar crash em sistemas sem som.
        try:
            pygame.mixer.init()
        except Exception:
            print("Aviso: mixer de áudio não pôde ser inicializado — continuando sem som.")

        # Carrega som de tiro se existir (se não existir, None)
        self.shot_sound = None
        if os.path.isfile(SHOT_SOUND_PATH):
            try:
                self.shot_sound = pygame.mixer.Sound(SHOT_SOUND_PATH)
            except Exception as e:
                print(f"Aviso: não foi possível carregar o som de tiro: {e}")
                self.shot_sound = None

        # Cria janela e clock
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # Estado do jogo
        self.score = 0
        self.lives = 3
        self.game_over_displayed = False  # controla a exibição do Game Over

        # Pausa
        self.paused = False  # se True, o jogo não atualiza lógica nem spawns

        # Grupos de sprites
        self.all_sprites = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()

        # Cria o player e adiciona aos grupos
        self.player = Player(pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
        self.all_sprites.add(self.player)
        self.player_group.add(self.player)

        # Fonte para HUD/debug
        self.font = pygame.font.SysFont("arial", 20)

        # Spawn de inimigos: configuráveis
        self.spawn_interval = 1.0  # segundos entre spawns (valor inicial)
        self.spawn_timer = 0.0     # contador incremental (em segundos)

        # Dificuldade dinâmica: diminuir spawn_interval ao longo do tempo
        self.difficulty_timer = 0.0            # contador para acionar redução
        self.difficulty_period = 12.0          # a cada 12s, aplicamos redução
        self.difficulty_reduction_factor = 0.92  # diminuímos spawn_interval em 8% (por exemplo)
        self.spawn_interval_min = 0.25         # limite mínimo para o intervalo

    def run(self):
        """Loop principal do jogo."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # delta time em segundos
            self.handle_events()
            # Se pausado, não atualizamos lógica de jogo (sprites, spawn, timers)
            if not self.paused:
                self.update(dt)
            self.draw()
        self.quit()

    def handle_events(self):
        """Trata eventos do Pygame — teclado, fechar janela.

        Observações:
        - ESC toggles pause.
        - Enquanto paused == True, SPACE não dispara.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Toggle de pausa (KEYDOWN para detectar apenas uma vez)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Alterna estado de pausa
                    self.paused = not self.paused
                    if self.paused:
                        print("Jogo pausado.")
                    else:
                        print("Jogo retomado.")
                    # Não processamos outras teclas deste evento (evita disparo instantâneo ao despausar)
                    continue

                # Se não estiver pausado, processa KEYDOWN de outras ações (ex.: disparo)
                if not self.paused:
                    if event.key == pygame.K_SPACE:
                        bullet = self.player.shoot()
                        if bullet is not None:
                            # adiciona nas coleções do jogo
                            self.all_sprites.add(bullet)
                            self.bullets_group.add(bullet)
                            # Toca som de tiro se disponível — não bloqueante.
                            if self.shot_sound:
                                try:
                                    self.shot_sound.play()
                                except Exception:
                                    # Se tocar falhar por algum motivo, apenas ignoramos
                                    pass

    def update(self, dt):
        """Atualiza lógica do jogo e gerencia spawn/collisions."""
        # Atualiza todos os sprites (cada sprite usa dt para movimento suave)
        self.all_sprites.update(dt)

        # Spawn de inimigos baseado no timer
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer -= self.spawn_interval
            self.spawn_enemy()

        # Dificuldade dinâmica: decrementa spawn_interval a cada período definido
        self.difficulty_timer += dt
        if self.difficulty_timer >= self.difficulty_period:
            self.difficulty_timer -= self.difficulty_period
            # Aplica redução multiplicativa, respeitando o mínimo
            new_interval = max(self.spawn_interval * self.difficulty_reduction_factor,
                               self.spawn_interval_min)
            if new_interval < self.spawn_interval:
                print(f"Aumentando dificuldade: spawn_interval {self.spawn_interval:.3f} -> {new_interval:.3f}")
            self.spawn_interval = new_interval

        # Colisões: balas que acertam inimigos
        collisions = pygame.sprite.groupcollide(self.bullets_group, self.enemies_group,
                                                True, True)
        if collisions:
            # Para cada bullet que colidiu, listamos enemies e incrementamos score
            for bullet, enemies_hit in collisions.items():
                # cada inimigo vale 10 pontos (ajustável)
                self.score += 10 * len(enemies_hit)
                # (Opcional: tocar som de explosão aqui)

        # Checa inimigos que alcançaram o fundo da tela
        for enemy in list(self.enemies_group):
            if enemy.rect.top > SCREEN_HEIGHT:
                # inimigo escapou — penaliza o jogador
                enemy.kill()
                self.lives -= 1
                print(f"Inimigo escapou! Vidas restantes: {self.lives}")

                # Se vidas chegaram a zero, exiba Game Over e encerre após pequeno delay
                if self.lives <= 0:
                    # desenhar a tela final por 2 segundos antes de fechar
                    self.display_game_over()
                    pygame.time.delay(2000)
                    self.running = False
                    return  # sai do update imediatamente

    def spawn_enemy(self):
        """Cria um inimigo em uma posição x aleatória no topo da tela."""
        x = random.randint(30, SCREEN_WIDTH - 30)
        y = -50  # começa um pouco acima da tela para aparecer "descendo"
        enemy = Enemy(pos=(x, y))
        self.enemies_group.add(enemy)
        self.all_sprites.add(enemy)

    def draw(self):
        """Desenha background, sprites, HUD e (se necessário) overlay de pausa."""
        # Fundo simples — podemos trocar por imagem depois.
        self.screen.fill((30, 40, 80))

        # Desenha sprites
        self.all_sprites.draw(self.screen)

        # HUD (score e vidas e spawn interval atual)
        score_surf = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_surf = self.font.render(f"Vidas: {self.lives}", True, (255, 255, 255))
        spawn_surf = self.font.render(f"Spawn: {self.spawn_interval:.2f}s", True, (255, 255, 255))
        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (10, 34))
        self.screen.blit(spawn_surf, (10, 58))

        # FPS para debug (opcional)
        fps = int(self.clock.get_fps())
        fps_surf = self.font.render(f"FPS: {fps}", True, (255, 255, 255))
        self.screen.blit(fps_surf, (SCREEN_WIDTH - 80, 10))
        pygame.display.set_caption(f"Pirata — FPS: {fps}")

        # Se o jogo estiver pausado, desenha overlay (sem atualizar lógica)
        if self.paused:
            self.draw_pause_overlay()

        pygame.display.flip()

    def draw_pause_overlay(self):
        """Desenha um overlay semitransparente com a palavra PAUSED no centro."""
        # Surface semitransparente do mesmo tamanho da tela
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))  # preta com alpha 160/255 (transparente)
        self.screen.blit(overlay, (0, 0))

        # Texto central de PAUSE
        go_font = pygame.font.SysFont("arial", 56, bold=True)
        text = go_font.render("PAUSED", True, (240, 240, 240))
        sub = self.font.render("Pressione ESC para continuar", True, (200, 200, 200))
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        subrect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(text, rect)
        self.screen.blit(sub, subrect)

    def display_game_over(self):
        """Desenha uma única tela de Game Over (chamada antes de encerrar)."""
        # Desenha fundo escuro e mensagem central
        self.screen.fill((10, 10, 10))
        go_font = pygame.font.SysFont("arial", 48)
        text = go_font.render("GAME OVER", True, (200, 50, 50))
        sub = self.font.render(f"Score final: {self.score}", True, (255, 255, 255))
        # centraliza
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        subrect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(text, rect)
        self.screen.blit(sub, subrect)
        pygame.display.flip()

    def quit(self):
        """Encerra Pygame."""
        pygame.quit()
