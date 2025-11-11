# src/enemy.py
# Inimigo básico que desce em linha reta. Se sair da tela pelo fundo, será
# tratado pelo Game como fuga (penalidade para o jogador).

import os
import pygame

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
ENEMY_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "enemy_basic.png")


class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos=(240, -50), dy=150):
        """
        pos: posição inicial (x,y) - geralmente topo
        dy: velocidade vertical (positivo = desce)
        """
        super().__init__()
        self.dy = dy
        self.hp = 1

        # Tenta carregar sprite de inimigo; senão, placeholder
        if os.path.isfile(ENEMY_IMAGE_PATH):
            img = pygame.image.load(ENEMY_IMAGE_PATH).convert_alpha()
            self.image = pygame.transform.smoothscale(img, (48, 48))
        else:
            surf = pygame.Surface((48, 48), pygame.SRCALPHA)
            # desenho simples: um retângulo com "capuz" para lembrar marinheiro/cartoon
            pygame.draw.rect(surf, (180, 180, 220), (0, 8, 48, 32), border_radius=6)
            pygame.draw.circle(surf, (110, 110, 160), (24, 14), 10)
            self.image = surf

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(self.rect.topleft)

    def update(self, dt):
        """Move o inimigo para baixo."""
        self.pos.y += self.dy * dt
        self.rect.y = int(self.pos.y)

        # (Futuro) lógica de IA/padrões pode ser adicionada aqui
