# src/player.py
# Versão corrigida: cria Bullet usando vx/vy explicitamente (compatível com Bullet atual)
# e protege a chamada para evitar que um erro feche o jogo.

import os
import pygame
import time

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
PLAYER_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "player.png")

class Player(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700)):
        super().__init__()
        self.speed = 300  # pixels por segundo

        # Carrega sprite se existir, senão placeholder
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
        self._last_shot_time = -999.0  # timestamp do último tiro

    def update(self, dt):
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

        if dx != 0 and dy != 0:
            import math
            dx *= math.sqrt(0.5)
            dy *= math.sqrt(0.5)

        self.rect.x += int(dx * self.speed * dt)
        self.rect.y += int(dy * self.speed * dt)
        self.rect.clamp_ip(self.screen_rect)

    def shoot(self):
        """
        Cria e retorna uma Bullet se o cooldown já passou.
        Utiliza vx/vy e owner para compatibilidade com a implementação atual de Bullet.
        Retorna None se em cooldown ou em caso de erro.
        """
        now = time.perf_counter()
        if now - self._last_shot_time < self.shoot_cooldown:
            return None  # ainda em cooldown

        self._last_shot_time = now

        # Import dinâmico para evitar import circular no topo
        try:
            from src.bullet import Bullet
        except Exception as e:
            # Se por algum motivo não for possível importar Bullet, não fechar o jogo.
            print(f"Aviso: não foi possível importar Bullet: {e}")
            return None

        # Cria a bala explicitamente com vx=0 e vy negativo (sobe)
        bullet_pos = (self.rect.centerx, self.rect.top - 8)
        try:
            bullet = Bullet(pos=bullet_pos, vx=0.0, vy=-600.0, owner="player")
        except TypeError:
            # Caso a assinatura da Bullet seja diferente (defensivo), tenta criar de forma compatível
            try:
                # tentativa compatível com versões antigas que aceitam (pos, dy)
                bullet = Bullet(bullet_pos, -600.0)
            except Exception as e:
                print(f"Aviso: falha ao criar Bullet: {e}")
                return None

        return bullet
