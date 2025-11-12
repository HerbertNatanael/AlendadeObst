# src/enemy.py
# Inimigos com comportamento baseado na posição do player:
# - BasicEnemy / FastEnemy / ZigZagEnemy: descem e ajustam X para se dirigir ao player;
#   ao colidir com o player, causam dano (e são removidos).
# - ShooterEnemy: desce até uma distância alvo e para; dispara periodicamente ao player.
#
# Arquivos de imagem (opcionais):
#  assets/images/enemy_basic.png
#  assets/images/enemy_zigzag.png
#  assets/images/enemy_fast.png
#  assets/images/enemy_shooter.png

import os
import math
import time
import pygame
from src.bullet import Bullet

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
ENEMY_BASIC_IMG = os.path.join(ASSETS_IMAGES, "enemy_basic.png")
ENEMY_ZIGZAG_IMG = os.path.join(ASSETS_IMAGES, "enemy_zigzag.png")
ENEMY_FAST_IMG = os.path.join(ASSETS_IMAGES, "enemy_fast.png")
ENEMY_SHOOTER_IMG = os.path.join(ASSETS_IMAGES, "enemy_shooter.png")

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800

def load_enemy_image(path, size=(48,48), fallback_color=(180,180,220)):
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, size)
            return img
        except Exception as e:
            print(f"Aviso: falha ao carregar {path}: {e}")
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w,h = size
    pygame.draw.rect(surf, fallback_color, (0, int(h*0.15), w, int(h*0.7)), border_radius=int(min(size)/8))
    pygame.draw.circle(surf, (110,110,160), (w//2, int(h*0.3)), int(min(size)/6))
    return surf


class Enemy(pygame.sprite.Sprite):
    """Base class para inimigos."""
    def __init__(self, pos=(240,-50), hp=1, image=None, player_ref=None):
        super().__init__()
        self.hp = hp
        self.pos = pygame.math.Vector2(pos)
        self.player_ref = player_ref  # referência ao player (pode ser None)
        self.image = image if image is not None else load_enemy_image(ENEMY_BASIC_IMG)
        self.rect = self.image.get_rect(center=pos)

    def take_damage(self, amount=1):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def update(self, dt):
        # subclasses atualizam self.pos; aqui mantemos rect sincronizado.
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class BasicEnemy(Enemy):
    """Desce e ajusta X para mirar o jogador (seguimento horizontal simples)."""
    def __init__(self, pos=(240,-50), dy=120, steer_speed=80, player_ref=None):
        img = load_enemy_image(ENEMY_BASIC_IMG, size=(48,48))
        super().__init__(pos=pos, hp=1, image=img, player_ref=player_ref)
        self.dy = dy
        # velocidade horizontal máxima para "se aproximar" do jogador
        self.steer_speed = steer_speed  # px/s de ajuste horizontal

    def update(self, dt):
        # segue horizontalmente o player (apenas se player_ref fornecido)
        if self.player_ref is not None:
            target_x = self.player_ref.rect.centerx
            dx = target_x - self.pos.x
            # move horizontalmente na direção do player, respeitando velocidade steer_speed
            if abs(dx) > 2:  # tolerância para evitar jitter
                sign = 1 if dx > 0 else -1
                self.pos.x += sign * min(abs(dx), self.steer_speed * dt)
        # sempre desce
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class ZigZagEnemy(Enemy):
    """Desce e faz Z (sinusoidal) enquanto também se aproxima do player horizontalmente."""
    def __init__(self, pos=(240,-50), dy=110, amplitude=70, frequency=1.0, steer_speed=60, player_ref=None):
        img = load_enemy_image(ENEMY_ZIGZAG_IMG, size=(48,48), fallback_color=(170,200,220))
        super().__init__(pos=pos, hp=1, image=img, player_ref=player_ref)
        self.dy = dy
        self.amplitude = amplitude
        self.frequency = frequency
        self._time = 0.0
        self.base_x = pos[0]
        self.steer_speed = steer_speed

    def update(self, dt):
        self._time += dt
        # componente zigzag horizontal baseado no tempo
        zig_x = math.sin(2*math.pi*self.frequency*self._time) * self.amplitude
        # base_x tenta seguir o player lentamente
        if self.player_ref is not None:
            target_x = self.player_ref.rect.centerx
            dx = target_x - self.base_x
            if abs(dx) > 2:
                sign = 1 if dx > 0 else -1
                self.base_x += sign * min(abs(dx), self.steer_speed * dt)
        self.pos.x = self.base_x + zig_x
        # descida
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class FastEnemy(Enemy):
    """Inimigo rápido que desce e também ajusta X para atingir o player mais agressivamente."""
    def __init__(self, pos=(240,-50), dy=240, steer_speed=140, player_ref=None):
        img = load_enemy_image(ENEMY_FAST_IMG, size=(48,48), fallback_color=(220,170,170))
        super().__init__(pos=pos, hp=1, image=img, player_ref=player_ref)
        self.dy = dy
        self.steer_speed = steer_speed

    def update(self, dt):
        if self.player_ref is not None:
            target_x = self.player_ref.rect.centerx
            dx = target_x - self.pos.x
            if abs(dx) > 2:
                sign = 1 if dx > 0 else -1
                self.pos.x += sign * min(abs(dx), self.steer_speed * dt)
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)


class ShooterEnemy(Enemy):
    """
    Inimigo que desce até uma distância alvo em relação ao player e para,
    permanecendo parado e atirando periodicamente em direção ao player.
    """
    def __init__(self, pos=(240,-50), dy=90, stop_distance=200, shoot_cooldown=1.6, bullet_speed=220, player_ref=None):
        img = load_enemy_image(ENEMY_SHOOTER_IMG, size=(48,48), fallback_color=(200,200,160))
        super().__init__(pos=pos, hp=2, image=img, player_ref=player_ref)
        self.dy = dy
        self.stop_distance = stop_distance  # distância vertical ao player para parar (px)
        self.shoot_cooldown = shoot_cooldown
        self._last_shot = -999.0
        self.bullet_speed = bullet_speed
        self._pending_bullet = None
        self.stopped = False  # se True, não desce mais

    def update(self, dt):
        # se já está parado, não desce; apenas atira periodicamente
        if not self.stopped:
            # se houver player_ref, compare posição vertical
            if self.player_ref is not None:
                player_y = self.player_ref.rect.centery
                # queremos ficar acima do player por 'stop_distance' pixels
                desired_y = player_y - self.stop_distance
                # se ainda não alcançou desired_y, desce; se passar, para
                if self.pos.y < desired_y:
                    self.pos.y += self.dy * dt
                else:
                    # alcançou posição de parada
                    self.pos.y = desired_y
                    # sincroniza X com player no momento da parada (pode ser mais interessante manter X atual)
                    # vamos deixar o X como está ao alcançar (evita movimento brusco)
                    self.stopped = True
            else:
                # sem player_ref, continua descendo
                self.pos.y += self.dy * dt
        # Se parado, permanece e tenta atirar
        # Sincroniza rect antes da lógica de tiro
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # tiro: apenas se tivermos referência ao jogador
        if self.player_ref is None:
            self._pending_bullet = None
            return

        now = time.perf_counter()
        if now - self._last_shot >= self.shoot_cooldown:
            px, py = self.player_ref.rect.center
            sx, sy = self.rect.center
            dx = px - sx
            dy = py - sy
            dist = math.hypot(dx, dy) or 1.0
            vx = dx / dist * self.bullet_speed
            vy = dy / dist * self.bullet_speed
            # cria bala inimiga apontando para player
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
