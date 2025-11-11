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
