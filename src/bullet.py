# src/bullet.py
# Implementa a bala disparada pelo jogador. Move-se verticalmente e se autodestrói
# quando sai da tela.

import os
import pygame

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
BULLET_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "bullet.png")

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700), dy=-500):
        """
        pos: posição inicial (x,y) da bala
        dy: velocidade vertical em pixels por segundo (negativo = sobe)
        """
        super().__init__()
        self.dy = dy

        # Carrega imagem da bala, se existir; senão gera placeholder (círculo)
        if os.path.isfile(BULLET_IMAGE_PATH):
            img = pygame.image.load(BULLET_IMAGE_PATH).convert_alpha()
            self.image = pygame.transform.smoothscale(img, (8, 16))
        else:
            surf = pygame.Surface((8, 16), pygame.SRCALPHA)
            pygame.draw.rect(surf, (255, 220, 60), (0, 0, 8, 16))
            self.image = surf

        self.rect = self.image.get_rect(center=pos)

        # Mantemos também uma posição em float, se desejarmos movimento fino.
        self.pos = pygame.math.Vector2(self.rect.topleft)

    def update(self, dt):
        """Move a bala verticalmente e se mata ao sair da tela."""
        # Atualiza posição (dy em px/s)
        self.pos.y += self.dy * dt
        # Sincroniza rect (inteiro) com a posição float
        self.rect.y = int(self.pos.y)

        # Se a bala sair da tela (acima ou abaixo), remove-se
        if self.rect.bottom < 0 or self.rect.top > 800:
            self.kill()
