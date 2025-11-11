# src/player.py
# Implementa a classe Player como um pygame.sprite.Sprite.
# Contém carregamento de imagem (se existir) ou desenho de placeholder,
# gerenciamento de movimento e limitação da área de jogo.

import os
import pygame

# Caminho para a pasta de imagens nos assets (relativo a este arquivo)
ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")

# Caminho esperado do sprite do jogador — se não existir, usamos placeholder
PLAYER_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "player.png")


class Player(pygame.sprite.Sprite):
    """
    Representa o navio controlado pelo jogador.
    - Herda de pygame.sprite.Sprite para integração com grupos.
    - Possui imagem (self.image) e retângulo de colisão/posicionamento (self.rect).
    - update(dt) aplica movimento com base em teclas pressionadas.
    """

    def __init__(self, pos=(240, 700)):
        super().__init__()

        # Velocidade em pixels por segundo; dt é usado para aplicar movimento corretamente.
        self.speed = 300

        # Tenta carregar imagem do jogador a partir de assets/images/player.png
        if os.path.isfile(PLAYER_IMAGE_PATH):
            # convert_alpha() mantém transparência e melhora performance na GPU/software.
            img = pygame.image.load(PLAYER_IMAGE_PATH).convert_alpha()
            # redimensionamos para um tamanho estável (64x64) para consistência visual.
            self.image = pygame.transform.smoothscale(img, (64, 64))
        else:
            # Se não houver imagem, criamos um placeholder desenhado dinamicamente.
            # Isso evita crashes quando você ainda não adicionou assets.
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            # Corpo do navio (polígono)
            pygame.draw.polygon(surf, (200, 160, 80), [(32, 0), (58, 24), (32, 56), (6, 24)])
            # Detalhe do convés
            pygame.draw.rect(surf, (100, 60, 20), (22, 30, 20, 15))
            self.image = surf

        # Obtém rect para posicionamento; center define posição inicial passada via pos.
        self.rect = self.image.get_rect(center=pos)

        # Retângulo da tela para manter o player dentro dos limites com clamp_ip()
        self.screen_rect = pygame.Rect(0, 0, 480, 800)

    def update(self, dt):
        """
        Atualiza posição do player.
        dt: delta time em segundos (float) — importante para movimento independente de FPS.
        """
        keys = pygame.key.get_pressed()

        # dx/dy serão -1, 0 ou 1 dependendo da tecla; depois multiplicamos pela velocidade.
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1

        # Normalização do movimento diagonal:
        # sem isso, mover diagonalmente seria ~1.414x (sqrt(2)) mais rápido.
        if dx != 0 and dy != 0:
            import math
            dx *= math.sqrt(0.5)
            dy *= math.sqrt(0.5)

        # Aplica movimento multiplicando por velocidade e por dt para suavidade
        self.rect.x += int(dx * self.speed * dt)
        self.rect.y += int(dy * self.speed * dt)

        # Mantém o jogador dentro dos limites da tela (clamp_ip ajusta rect in-place)
        self.rect.clamp_ip(self.screen_rect)

# src/player.py
# Player sprite com movimento (WASD / setas) e método de disparo (shoot).
import os
import pygame
import time

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
PLAYER_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "player.png")

class Player(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700)):
        super().__init__()
        self.speed = 300  # pixels por segundo

        # Tenta carregar sprite; senão, cria placeholder gráfico.
        if os.path.isfile(PLAYER_IMAGE_PATH):
            img = pygame.image.load(PLAYER_IMAGE_PATH).convert_alpha()
            self.image = pygame.transform.smoothscale(img, (64, 64))
        else:
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.polygon(surf, (200, 160, 80), [(32,0),(58,24),(32,56),(6,24)])
            pygame.draw.rect(surf, (100, 60, 20), (22, 30, 20, 15))
            self.image = surf

        self.rect = self.image.get_rect(center=pos)
        self.screen_rect = pygame.Rect(0, 0, 480, 800)

        # Disparo - cooldown
        self.shoot_cooldown = 0.25  # segundos entre tiros
        self._last_shot_time = -999.0  # timestamp do último tiro (inicial muito no passado)

    def update(self, dt):
        """Atualiza posição do player (chamado pelo game loop)."""
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1

        # Normaliza diagonal
        if dx != 0 and dy != 0:
            import math
            dx *= math.sqrt(0.5)
            dy *= math.sqrt(0.5)

        # Movimento aplicado com dt
        self.rect.x += int(dx * self.speed * dt)
        self.rect.y += int(dy * self.speed * dt)

        # Mantém dentro da tela
        self.rect.clamp_ip(self.screen_rect)

    def shoot(self):
        """
        Tenta criar e retornar uma Bullet se o cooldown já passou.
        Retorna:
            Bullet instance ou None (se ainda estiver em cooldown).
        Observação: o Game chama player.shoot() e, se não for None,
        adiciona a bala aos grupos apropriados.
        """
        now = time.perf_counter()
        if now - self._last_shot_time < self.shoot_cooldown:
            return None  # ainda em cooldown

        # atualiza o tempo do último disparo
        self._last_shot_time = now

        # Importamos aqui para evitar import circular (Game -> Player -> Bullet)
        from src.bullet import Bullet

        # Cria a bala na posição do topo do navio (ajuste visual)
        bullet_pos = (self.rect.centerx, self.rect.top - 8)
        bullet = Bullet(pos=bullet_pos, dy=-600)  # dy negativo -> sobem rápido
        return bullet

# src/player.py
# Player sprite com movimento (WASD / setas) e método de disparo (shoot).
import os
import pygame
import time

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
PLAYER_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "player.png")

class Player(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700)):
        super().__init__()
        self.speed = 300  # pixels por segundo

        # Tenta carregar sprite; senão, cria placeholder gráfico.
        if os.path.isfile(PLAYER_IMAGE_PATH):
            img = pygame.image.load(PLAYER_IMAGE_PATH).convert_alpha()
            self.image = pygame.transform.smoothscale(img, (64, 64))
        else:
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.polygon(surf, (200, 160, 80), [(32,0),(58,24),(32,56),(6,24)])
            pygame.draw.rect(surf, (100, 60, 20), (22, 30, 20, 15))
            self.image = surf

        self.rect = self.image.get_rect(center=pos)
        self.screen_rect = pygame.Rect(0, 0, 480, 800)

        # Disparo - cooldown
        self.shoot_cooldown = 0.25  # segundos entre tiros
        self._last_shot_time = -999.0  # timestamp do último tiro (inicial muito no passado)

    def update(self, dt):
        """Atualiza posição do player (chamado pelo game loop)."""
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1

        # Normaliza diagonal
        if dx != 0 and dy != 0:
            import math
            dx *= math.sqrt(0.5)
            dy *= math.sqrt(0.5)

        # Movimento aplicado com dt
        self.rect.x += int(dx * self.speed * dt)
        self.rect.y += int(dy * self.speed * dt)

        # Mantém dentro da tela
        self.rect.clamp_ip(self.screen_rect)

    def shoot(self):
        """
        Tenta criar e retornar uma Bullet se o cooldown já passou.
        Retorna:
            Bullet instance ou None (se ainda estiver em cooldown).
        Observação: o Game chama player.shoot() e, se não for None,
        adiciona a bala aos grupos apropriados e toca som.
        """
        now = time.perf_counter()
        if now - self._last_shot_time < self.shoot_cooldown:
            return None  # ainda em cooldown

        # atualiza o tempo do último disparo
        self._last_shot_time = now

        # Importamos aqui para evitar import circular (Game -> Player -> Bullet)
        from src.bullet import Bullet

        # Cria a bala na posição do topo do navio (ajuste visual)
        bullet_pos = (self.rect.centerx, self.rect.top - 8)
        bullet = Bullet(pos=bullet_pos, dy=-600)  # dy negativo -> sobem rápido
        return bullet
