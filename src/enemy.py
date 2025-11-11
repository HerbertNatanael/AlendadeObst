# src/enemy.py
# Inimigos com imagens específicas por tipo (se existirem em assets/images).
# Arquivos esperados:
#   assets/images/enemy_basic.png
#   assets/images/enemy_zigzag.png
#   assets/images/enemy_fast.png
#   assets/images/enemy_shooter.png
#
# Tamanhos recomendados (pixels):
#   basic / zigzag / fast / shooter: 48x48 (ou 64x64 se preferir mais resolução)
#
# O código carrega cada imagem com convert_alpha() e aplica smoothscale para garantir o tamanho.

import os
import math
import time
import pygame
from src.bullet import Bullet

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
# caminhos esperados (nomes exatos)
ENEMY_BASIC_IMG = os.path.join(ASSETS_IMAGES, "enemy_basic.png")
ENEMY_ZIGZAG_IMG = os.path.join(ASSETS_IMAGES, "enemy_zigzag.png")
ENEMY_FAST_IMG = os.path.join(ASSETS_IMAGES, "enemy_fast.png")
ENEMY_SHOOTER_IMG = os.path.join(ASSETS_IMAGES, "enemy_shooter.png")

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800

# função utilitária para carregar imagem com fallback
def load_enemy_image(path, size=(48, 48), fallback_color=(180, 180, 220)):
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, size)
            return img
        except Exception as e:
            print(f"Aviso: falha ao carregar {path}: {e}")
    # fallback: cria placeholder
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    pygame.draw.rect(surf, fallback_color, (0, int(h*0.15), w, int(h*0.7)), border_radius=int(min(size)/8))
    pygame.draw.circle(surf, (110, 110, 160), (w//2, int(h*0.3)), int(min(size)/6))
    return surf


class Enemy(pygame.sprite.Sprite):
    """Classe base para inimigos — contém atributos comuns."""
    def __init__(self, pos=(240, -50), hp=1, image=None):
        super().__init__()
        self.hp = hp
        self.pos = pygame.math.Vector2(pos)
        # se image já fornecida, usa, senão fallback
        if image is not None:
            self.image = image
        else:
            self.image = load_enemy_image(ENEMY_BASIC_IMG, size=(48,48))
        self.rect = self.image.get_rect(center=pos)

    def take_damage(self, amount=1):
        """Aplica dano e mata se HP <= 0."""
        self.hp -= amount
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def update(self, dt):
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class BasicEnemy(Enemy):
    """Inimigo que desce em linha reta."""
    def __init__(self, pos=(240, -50), dy=120):
        # tenta carregar imagem específica
        img = load_enemy_image(ENEMY_BASIC_IMG, size=(48,48))
        super().__init__(pos=pos, hp=1, image=img)
        self.dy = dy

    def update(self, dt):
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class ZigZagEnemy(Enemy):
    """Inimigo que desce com movimento sinusoidal horizontal."""
    def __init__(self, pos=(240, -50), dy=110, amplitude=70, frequency=1.0):
        img = load_enemy_image(ENEMY_ZIGZAG_IMG, size=(48,48), fallback_color=(170,200,220))
        super().__init__(pos=pos, hp=1, image=img)
        self.dy = dy
        self.amplitude = amplitude
        self.frequency = frequency
        self._time = 0.0
        self.base_x = pos[0]

    def update(self, dt):
        self._time += dt
        self.pos.y += self.dy * dt
        self.pos.x = self.base_x + math.sin(2 * math.pi * self.frequency * self._time) * self.amplitude
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class FastEnemy(Enemy):
    """Inimigo rápido (desce mais rápido)."""
    def __init__(self, pos=(240, -50), dy=240):
        img = load_enemy_image(ENEMY_FAST_IMG, size=(48,48), fallback_color=(220,170,170))
        super().__init__(pos=pos, hp=1, image=img)
        self.dy = dy

    def update(self, dt):
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class ShooterEnemy(Enemy):
    """
    Inimigo que atira em direção ao jogador.
    Gera uma bala (Bullet) apontando para player_ref e disponibiliza via _pending_bullet.
    """
    def __init__(self, pos=(240, -50), dy=90, shoot_cooldown=1.6, bullet_speed=220, player_ref=None):
        img = load_enemy_image(ENEMY_SHOOTER_IMG, size=(48,48), fallback_color=(200,200,160))
        super().__init__(pos=pos, hp=2, image=img)
        self.dy = dy
        self.shoot_cooldown = shoot_cooldown
        self._last_shot = -999.0
        self.bullet_speed = bullet_speed
        self.player_ref = player_ref
        self._pending_bullet = None

    def update(self, dt):
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        if self.player_ref is None:
            return

        now = time.perf_counter()
        if now - self._last_shot >= self.shoot_cooldown:
            px, py = self.player_ref.rect.center
            sx, sy = self.rect.center
            dx = px - sx
            dy = py - sy
            dist = math.hypot(dx, dy)
            if dist == 0:
                dist = 1.0
            vx = dx / dist * self.bullet_speed
            vy = dy / dist * self.bullet_speed
            try:
                bullet = Bullet(pos=self.rect.center, vx=vx, vy=vy, owner="enemy")
                self._pending_bullet = bullet
            except Exception as e:
                print(f"Aviso: falha ao criar bala do ShooterEnemy: {e}")
                self._pending_bullet = None
            self._last_shot = now
        else:
            self._pending_bullet = None

    def pop_pending_bullet(self):
        b = self._pending_bullet
        self._pending_bullet = None
        return b
