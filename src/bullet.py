# src/bullet.py
# Bala genérica que pode ser usada por jogador e inimigos.
# Agora aceita velocidade vetorial (vx, vy) em pixels/segundo e um campo `owner`
# para distinguir colisões (por exemplo: 'player' ou 'enemy').
#
# A bala se autodestrói ao sair da tela (top/bottom/side).

import os
import pygame

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
BULLET_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "bullet.png")

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700), vx=0.0, vy=-500.0, owner="player"):
        """
        pos: tupla (x, y) posição inicial da bala (center)
        vx, vy: velocidade em px/s (float). Por exemplo vy = -600 faz bala subir.
        owner: 'player' ou 'enemy' (usado para lógica de colisão)
        """
        super().__init__()
        self.vx = float(vx)
        self.vy = float(vy)
        self.owner = owner

        # Carrega imagem da bala se houver; senão gera placeholder amarelo
        if os.path.isfile(BULLET_IMAGE_PATH):
            img = pygame.image.load(BULLET_IMAGE_PATH).convert_alpha()
            # escala automática para tamanho razoável
            self.image = pygame.transform.smoothscale(img, (8, 16))
        else:
            # Placeholder retangular (8x16)
            surf = pygame.Surface((8, 16), pygame.SRCALPHA)
            if owner == "player":
                pygame.draw.rect(surf, (255, 220, 60), (0, 0, 8, 16))
            else:
                pygame.draw.rect(surf, (220, 80, 80), (0, 0, 8, 16))
            self.image = surf

        # Rect centralizado na posição inicial
        self.rect = self.image.get_rect(center=pos)
        # Posição em float para movimento suave
        self.pos = pygame.math.Vector2(self.rect.topleft)

    def update(self, dt):
        """Move a bala segundo (vx, vy) e mata quando sai da tela."""
        # Atualiza posição
        self.pos.x += self.vx * dt
        self.pos.y += self.vy * dt
        # Sincroniza rect
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # Mata a bala quando sair da área de jogo (alguma margem)
        if (self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT
                or self.rect.right < 0 or self.rect.left > SCREEN_WIDTH):
            self.kill()

