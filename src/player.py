# src/player.py
# Player com movimento, animação yaw/pitch e hitbox reduzida em 45%.
# A aparência do sprite não muda, mas o retângulo de colisão (hitbox)
# é 55% do tamanho do sprite e centralizado.
#
# Isso deixa as colisões (balas e inimigos) mais justas e menos frustrantes.

import os
import pygame
import time
import math

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
PLAYER_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "player.png")

# ---------- PARÂMETROS DE TUNING ----------
SPRITE_DRAW_SIZE = (64, 64)
DEFAULT_SPEED = 300.0
DEFAULT_SHOOT_COOLDOWN = 0.25
DEFAULT_BULLET_SPEED = 700.0

MAX_HORIZ_SCALE = 0.72
MAX_YAW_ROT_DEG = 14.0
PITCH_UP_ROT_DEG = -12.0
TILT_SPEED = 10.0
HITBOX_SCALE = 0.55  # 55% do tamanho original (reduz ~45%)
# -----------------------------------------

class Player(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700)):
        super().__init__()
        self.speed = DEFAULT_SPEED

        # Carrega sprite (ou placeholder)
        if os.path.isfile(PLAYER_IMAGE_PATH):
            try:
                img = pygame.image.load(PLAYER_IMAGE_PATH).convert_alpha()
                img = pygame.transform.smoothscale(img, SPRITE_DRAW_SIZE)
                self.original_image = img
            except Exception as e:
                print(f"Aviso: falha ao carregar player.png: {e}")
                self.original_image = self._make_placeholder()
        else:
            self.original_image = self._make_placeholder()

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.screen_rect = pygame.Rect(0, 0, 480, 800)

        # Hitbox reduzida
        self._update_hitbox()

        # Disparo cooldown
        self.shoot_cooldown = DEFAULT_SHOOT_COOLDOWN
        self._last_shot_time = -999.0

        # Estados visuais (yaw/pitch)
        self.yaw_value = 0.0
        self.target_yaw_value = 0.0
        self.pitch_value = 0.0
        self.target_pitch_value = 0.0

    def _make_placeholder(self):
        surf = pygame.Surface(SPRITE_DRAW_SIZE, pygame.SRCALPHA)
        w,h = SPRITE_DRAW_SIZE
        pygame.draw.polygon(surf, (200,160,80), [(w//2,0),(w-6,h//2),(w//2,h-2),(6,h//2)])
        pygame.draw.rect(surf, (100,60,20), (w//2-8,h//2,16,10))
        return surf

    def _update_hitbox(self):
        """Atualiza o retângulo de colisão reduzido (hitbox)."""
        w, h = self.rect.size
        reduced_w = int(w * HITBOX_SCALE)
        reduced_h = int(h * HITBOX_SCALE)
        cx, cy = self.rect.center
        self.hitbox_rect = pygame.Rect(0, 0, reduced_w, reduced_h)
        self.hitbox_rect.center = (cx, cy)

    def get_hitbox(self):
        """Retorna o retângulo de colisão reduzido."""
        return self.hitbox_rect

    def update(self, dt):
        """Movimento + animação + hitbox update."""
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
            inv = math.sqrt(0.5)
            dx *= inv
            dy *= inv

        self.pos.x += dx * self.speed * dt
        self.pos.y += dy * self.speed * dt

        tmp_rect = self.rect.copy()
        tmp_rect.x = int(self.pos.x)
        tmp_rect.y = int(self.pos.y)
        tmp_rect.clamp_ip(self.screen_rect)
        self.pos.x = tmp_rect.x
        self.pos.y = tmp_rect.y
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # --- controle visual ---
        self.target_yaw_value = float(max(-1.0, min(1.0, dx)))
        if dy < 0:
            self.target_pitch_value = float(min(1.0, -dy))
        else:
            self.target_pitch_value = 0.0
        interp = min(1.0, TILT_SPEED * dt)
        self.yaw_value += (self.target_yaw_value - self.yaw_value) * interp
        self.pitch_value += (self.target_pitch_value - self.pitch_value) * interp
        self._update_transformed_image()

        # Atualiza hitbox com base na nova posição e rotação
        self._update_hitbox()

    def _update_transformed_image(self):
        """Aplica compressão horizontal + rotação para simular virada."""
        yaw = self.yaw_value
        abs_yaw = abs(yaw)
        horiz_scale = 1.0 - (1.0 - MAX_HORIZ_SCALE) * abs_yaw
        yaw_rot = -yaw * MAX_YAW_ROT_DEG
        pitch_rot = self.pitch_value * PITCH_UP_ROT_DEG
        total_rot = yaw_rot + pitch_rot

        w0,h0 = SPRITE_DRAW_SIZE
        new_w = max(2, int(w0 * horiz_scale))
        scaled = pygame.transform.smoothscale(self.original_image, (new_w, h0))
        canvas = pygame.Surface((w0, h0), pygame.SRCALPHA)
        x_offset = (w0 - new_w) // 2
        canvas.blit(scaled, (x_offset, 0))
        rotated = pygame.transform.rotozoom(canvas, total_rot, 1.0)

        old_center = self.rect.center
        self.image = rotated
        self.rect = self.image.get_rect()
        self.rect.center = old_center

    def shoot(self, target_pos=None):
        """Atira em direção ao cursor (mantido igual)."""
        now = time.perf_counter()
        if now - self._last_shot_time < self.shoot_cooldown:
            return None
        self._last_shot_time = now

        try:
            from src.bullet import Bullet
        except Exception as e:
            print(f"Aviso: não foi possível importar Bullet: {e}")
            return None

        sx, sy = self.rect.centerx, self.rect.top - 8
        if target_pos is None:
            try:
                target_pos = pygame.mouse.get_pos()
            except Exception:
                target_pos = None

        if target_pos is None:
            try:
                return Bullet(pos=(sx, sy), vx=0.0, vy=-DEFAULT_BULLET_SPEED, owner="player")
            except Exception:
                return None

        tx, ty = target_pos
        dx = tx - sx
        dy = ty - sy
        dist = math.hypot(dx, dy) or 1.0
        vx = dx / dist * DEFAULT_BULLET_SPEED
        vy = dy / dist * DEFAULT_BULLET_SPEED

        try:
            return Bullet(pos=(sx, sy), vx=vx, vy=vy, owner="player")
        except Exception:
            return None
