# src/enemy.py
# Diferentes tipos de inimigos com padrões simples:
# - BasicEnemy: desce reto (HP = 1)
# - ZigZagEnemy: desce com movimento sinusoidal (para os lados)
# - FastEnemy: desce rápido (HP ainda 1)
# - ShooterEnemy: desce e periodicamente dispara balas em direção ao player
#
# Cada inimigo mantém `pos` (Vector2) para atualização suave.

import os
import math
import time
import pygame
from src.bullet import Bullet

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
ENEMY_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "enemy_basic.png")

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800


class Enemy(pygame.sprite.Sprite):
    """Classe base para inimigos — contém atributos comuns."""
    def __init__(self, pos=(240, -50), hp=1):
        super().__init__()
        self.hp = hp
        self.pos = pygame.math.Vector2(pos)
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (180, 180, 220), (0, 8, 48, 32), border_radius=6)
        pygame.draw.circle(self.image, (110, 110, 160), (24, 14), 10)
        self.rect = self.image.get_rect(center=pos)

    def take_damage(self, amount=1):
        """Aplica dano e mata se HP <= 0."""
        self.hp -= amount
        if self.hp <= 0:
            self.kill()  # remove o sprite (Game lida com pontuação)
            return True
        return False

    def update(self, dt):
        """Placeholder — subclasses implementam comportamento."""
        # Atualizam rect a partir de pos (subclasses devem alterar pos)
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class BasicEnemy(Enemy):
    """Inimigo que desce em linha reta."""
    def __init__(self, pos=(240, -50), dy=120):
        super().__init__(pos=pos, hp=1)
        self.dy = dy
        # Se existir sprite customizado, poderíamos carregar aqui (mantivemos placeholder)
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class ZigZagEnemy(Enemy):
    """Inimigo que desce e faz movimento horizontal sinusoidal."""
    def __init__(self, pos=(240, -50), dy=110, amplitude=70, frequency=1.2):
        super().__init__(pos=pos, hp=1)
        self.dy = dy
        self.amplitude = amplitude
        self.frequency = frequency  # oscilações por segundo
        self._time = 0.0
        self.base_x = pos[0]
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self._time += dt
        # movimento vertical
        self.pos.y += self.dy * dt
        # movimento horizontal sin/cos baseado em tempo
        self.pos.x = self.base_x + math.sin(2 * math.pi * self.frequency * self._time) * self.amplitude
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class FastEnemy(Enemy):
    """Inimigo rápido, pouca resistência — pressiona o jogador a reagir."""
    def __init__(self, pos=(240, -50), dy=220):
        super().__init__(pos=pos, hp=1)
        self.dy = dy
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class ShooterEnemy(Enemy):
    """
    Inimigo que atira em direção ao jogador.
    Recebe referência ao player para mirar corretamente.
    """
    def __init__(self, pos=(240, -50), dy=90, shoot_cooldown=1.6, bullet_speed=220, player_ref=None):
        super().__init__(pos=pos, hp=2)  # dá um pouco mais de HP
        self.dy = dy
        self.shoot_cooldown = shoot_cooldown
        self._last_shot = -999.0
        self.bullet_speed = bullet_speed
        self.player_ref = player_ref
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        # movimento vertical similar ao basic
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # tenta atirar se houver player e cooldown estiver pronto
        if self.player_ref is None:
            return

        now = time.perf_counter()
        if now - self._last_shot >= self.shoot_cooldown:
            # mira na posição atual do player
            px, py = self.player_ref.rect.center
            sx, sy = self.rect.center
            dx = px - sx
            dy = py - sy
            dist = math.hypot(dx, dy)
            if dist == 0:
                dist = 1.0
            # normaliza e aplica velocidade
            vx = dx / dist * self.bullet_speed
            vy = dy / dist * self.bullet_speed
            # cria bala inimiga (owner='enemy')
            bullet = Bullet(pos=self.rect.center, vx=vx, vy=vy, owner="enemy")
            # Para evitar import circular, a adição das balas ao grupo será feita
            # pelo Game: ShooterEnemy retornará a bala, e o Game adiciona onde for necessário.
            # Aqui vamos guardar a última bala criada no objeto para que o Game possa buscar
            # ou o Game chamará um método para obter la bala. Para simplificar, salvamos
            # em self._pending_bullet e atualizamos _last_shot.
            self._pending_bullet = bullet
            self._last_shot = now
        else:
            self._pending_bullet = None

    def pop_pending_bullet(self):
        """Retorna (e limpa) a última bala criada pelo inimigo, ou None."""
        b = getattr(self, "_pending_bullet", None)
        self._pending_bullet = None
        return b
