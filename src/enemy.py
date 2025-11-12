# src/enemy.py
# Inimigos com animação yaw/pitch e BossEnemy (movimento horizontal + HP alto)
#
# Opcional: assets/images/boss.png (se presente será usado)
#
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
BOSS_IMG = os.path.join(ASSETS_IMAGES, "boss.png")

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800

# visual tuning
SPRITE_DRAW_SIZE = (48, 48)
MAX_HORIZ_SCALE = 0.72
MAX_YAW_ROT_DEG = 12.0
PITCH_UP_ROT_DEG = -8.0
TILT_SPEED = 8.0
HEALTH_BAR_HEIGHT = 6
HEALTH_BAR_MARGIN = 4


def load_enemy_image(path, size=SPRITE_DRAW_SIZE, fallback_color=(180, 180, 220)):
    """Tenta carregar e escalar imagem; se não existir cria placeholder."""
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, size)
            return img
        except Exception as e:
            print(f"Aviso: falha ao carregar {path}: {e}")
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, fallback_color, (0, int(h*0.15), w, int(h*0.7)), border_radius=int(min(size)/8))
    pygame.draw.circle(surf, (110, 110, 160), (w//2, int(h*0.3)), int(min(size)/6))
    return surf


class Enemy(pygame.sprite.Sprite):
    """Base para inimigos com animação visual (yaw/pitch)."""
    def __init__(self, pos=(240, -50), hp=1, image=None, player_ref=None, size=SPRITE_DRAW_SIZE):
        super().__init__()
        self.hp = hp
        self.max_hp = hp
        self.pos = pygame.math.Vector2(pos)
        self.player_ref = player_ref
        self.size = size

        if image is not None:
            self.original_image = image
        else:
            self.original_image = load_enemy_image(ENEMY_BASIC_IMG, size=self.size)

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=pos)

        # visual state
        self.yaw_value = 0.0
        self.target_yaw_value = 0.0
        self.pitch_value = 0.0
        self.target_pitch_value = 0.0

        # velocities for visual
        self.vx = 0.0
        self.vy = 0.0

    def take_damage(self, amount=1):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def _update_visual_targets(self, dt):
        """Define target yaw/pitch a partir de vx/vy e interpola suavemente."""
        if abs(self.vx) < 0.01:
            desired_yaw = 0.0
        else:
            normalizer = max(1.0, abs(self.vx))
            desired_yaw = max(-1.0, min(1.0, self.vx / normalizer))
        self.target_yaw_value = desired_yaw

        if self.vy < -1.0:
            pv = min(1.0, -self.vy / max(100.0, abs(self.vy)))
            self.target_pitch_value = pv
        else:
            self.target_pitch_value = 0.0

        interp = min(1.0, TILT_SPEED * dt)
        self.yaw_value += (self.target_yaw_value - self.yaw_value) * interp
        self.pitch_value += (self.target_pitch_value - self.pitch_value) * interp

    def _apply_visual_transform(self, include_health_bar=False):
        """Aplica compressão horizontal + rotação 2D baseada em yaw/pitch e opcionalmente desenha barra."""
        yaw = self.yaw_value
        abs_yaw = abs(yaw)
        horiz_scale = 1.0 - (1.0 - MAX_HORIZ_SCALE) * abs_yaw
        yaw_rot = -yaw * MAX_YAW_ROT_DEG
        pitch_rot = self.pitch_value * PITCH_UP_ROT_DEG
        total_rot = yaw_rot + pitch_rot

        w0, h0 = self.size
        new_w = max(2, int(w0 * horiz_scale))
        scaled = pygame.transform.smoothscale(self.original_image, (new_w, h0))
        canvas = pygame.Surface((w0, h0), pygame.SRCALPHA)
        x_offset = (w0 - new_w) // 2
        canvas.blit(scaled, (x_offset, 0))

        try:
            rotated = pygame.transform.rotozoom(canvas, total_rot, 1.0)
        except Exception:
            rotated = pygame.transform.rotate(canvas, total_rot)

        if include_health_bar:
            bar_h = HEALTH_BAR_HEIGHT + HEALTH_BAR_MARGIN
            combined_w = rotated.get_width()
            combined_h = rotated.get_height() + bar_h
            combined = pygame.Surface((combined_w, combined_h), pygame.SRCALPHA)
            combined.blit(rotated, (0, bar_h))
            bar_w = int(combined_w * 0.9)
            bar_x = (combined_w - bar_w) // 2
            bar_y = HEALTH_BAR_MARGIN // 2
            pygame.draw.rect(combined, (60, 60, 60), (bar_x, bar_y, bar_w, HEALTH_BAR_HEIGHT), border_radius=2)
            hp_ratio = max(0.0, min(1.0, float(self.hp) / float(self.max_hp) if self.max_hp else 0.0))
            if hp_ratio > 0.5:
                g = int(255 * (hp_ratio - 0.5) * 2)
                r = int(255 * (1 - (hp_ratio - 0.5) * 2) * 0.2)
                color = (max(50, r), min(255, 200 + g//2), 40)
            else:
                r = int(200 + (1.0 - hp_ratio) * 55)
                g = int(200 * hp_ratio)
                color = (min(255, r), max(30, g), 30)
            fill_w = max(1, int(bar_w * hp_ratio))
            pygame.draw.rect(combined, color, (bar_x, bar_y, fill_w, HEALTH_BAR_HEIGHT), border_radius=2)
            old_center = self.rect.center
            self.image = combined
            self.rect = self.image.get_rect()
            self.rect.center = old_center
            self.pos.x = self.rect.x
            self.pos.y = self.rect.y
        else:
            old_center = self.rect.center
            self.image = rotated
            self.rect = self.image.get_rect()
            self.rect.center = old_center
            self.pos.x = self.rect.x
            self.pos.y = self.rect.y


class BasicEnemy(Enemy):
    def __init__(self, pos=(240, -50), dy=120, steer_speed=80, player_ref=None):
        img = load_enemy_image(ENEMY_BASIC_IMG, size=SPRITE_DRAW_SIZE)
        super().__init__(pos=pos, hp=1, image=img, player_ref=player_ref, size=SPRITE_DRAW_SIZE)
        self.dy = dy
        self.steer_speed = steer_speed

    def update(self, dt):
        if self.player_ref is not None:
            target_x = self.player_ref.rect.centerx
            dx = target_x - self.pos.x
            if abs(dx) > 2:
                sign = 1 if dx > 0 else -1
                self.pos.x += sign * min(abs(dx), self.steer_speed * dt)
        self.vx = (self.pos.x - self.rect.x) / max(1e-6, dt)
        self.vy = self.dy
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)
        self._update_visual_targets(dt)
        self._apply_visual_transform(include_health_bar=False)


class ZigZagEnemy(Enemy):
    def __init__(self, pos=(240, -50), dy=110, amplitude=70, frequency=1.0, steer_speed=60, player_ref=None):
        img = load_enemy_image(ENEMY_ZIGZAG_IMG, size=SPRITE_DRAW_SIZE, fallback_color=(170, 200, 220))
        super().__init__(pos=pos, hp=1, image=img, player_ref=player_ref, size=SPRITE_DRAW_SIZE)
        self.dy = dy
        self.amplitude = amplitude
        self.frequency = frequency
        self._time = 0.0
        self.base_x = pos[0]
        self.steer_speed = steer_speed

    def update(self, dt):
        self._time += dt
        zig_x = math.sin(2 * math.pi * self.frequency * self._time) * self.amplitude
        if self.player_ref is not None:
            target_x = self.player_ref.rect.centerx
            dx = target_x - self.base_x
            if abs(dx) > 2:
                sign = 1 if dx > 0 else -1
                self.base_x += sign * min(abs(dx), self.steer_speed * dt)
        self.pos.x = self.base_x + zig_x
        self.pos.y += self.dy * dt
        self.vx = (self.pos.x - self.rect.x) / max(1e-6, dt)
        self.vy = self.dy
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)
        self._update_visual_targets(dt)
        self._apply_visual_transform(include_health_bar=False)


class FastEnemy(Enemy):
    def __init__(self, pos=(240, -50), dy=240, steer_speed=140, player_ref=None):
        img = load_enemy_image(ENEMY_FAST_IMG, size=SPRITE_DRAW_SIZE, fallback_color=(220, 170, 170))
        super().__init__(pos=pos, hp=1, image=img, player_ref=player_ref, size=SPRITE_DRAW_SIZE)
        self.dy = dy
        self.steer_speed = steer_speed

    def update(self, dt):
        if self.player_ref is not None:
            target_x = self.player_ref.rect.centerx
            dx = target_x - self.pos.x
            if abs(dx) > 2:
                sign = 1 if dx > 0 else -1
                self.pos.x += sign * min(abs(dx), self.steer_speed * dt)
        self.vx = (self.pos.x - self.rect.x) / max(1e-6, dt)
        self.vy = self.dy
        self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)
        self._update_visual_targets(dt)
        self._apply_visual_transform(include_health_bar=False)


class ShooterEnemy(Enemy):
    def __init__(self, pos=(240, -50), dy=90, stop_distance=200, shoot_cooldown=1.6,
                 bullet_speed=220, player_ref=None, hp=3):
        img = load_enemy_image(ENEMY_SHOOTER_IMG, size=SPRITE_DRAW_SIZE, fallback_color=(200, 200, 160))
        super().__init__(pos=pos, hp=hp, image=img, player_ref=player_ref, size=SPRITE_DRAW_SIZE)
        self.max_hp = hp
        self.dy = dy
        self.stop_distance = stop_distance
        self.shoot_cooldown = shoot_cooldown
        self._last_shot = -999.0
        self.bullet_speed = bullet_speed
        self._pending_bullet = None
        self.stopped = False

    def update(self, dt):
        if not self.stopped:
            if self.player_ref is not None:
                player_y = self.player_ref.rect.centery
                desired_y = player_y - self.stop_distance
                if self.pos.y < desired_y:
                    self.pos.y += self.dy * dt
                else:
                    self.pos.y = desired_y
                    self.stopped = True
            else:
                self.pos.y += self.dy * dt
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        if self.player_ref is None:
            self._pending_bullet = None
        else:
            now = time.perf_counter()
            if now - self._last_shot >= self.shoot_cooldown:
                px, py = self.player_ref.rect.center
                sx, sy = self.rect.center
                dx = px - sx
                dy = py - sy
                dist = math.hypot(dx, dy) or 1.0
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

        if self.player_ref is not None:
            dx_vis = (self.player_ref.rect.centerx - self.pos.x)
            self.vx = dx_vis / max(1.0, abs(dx_vis))
            self.vy = 0.0
        else:
            self.vx = 0.0
            self.vy = 0.0

        self._update_visual_targets(dt)
        self._apply_visual_transform(include_health_bar=True)

    def pop_pending_bullet(self):
        b = self._pending_bullet
        self._pending_bullet = None
        return b


class BossEnemy(Enemy):
    """
    Boss final:
    - aparece centralizado, desce lentamente até posição inicial (start_y)
    - depois move-se apenas na horizontal (bounce entre limites)
    - maior tamanho que inimigos normais; tem hp alto.
    """
    def __init__(self, pos=(SCREEN_WIDTH//2, -220), dy=60, start_y=120, hp=40, speed_x=140, player_ref=None):
        boss_size = (120, 80)  # maior que inimigos
        # tenta carregar boss.png se existir
        if os.path.isfile(BOSS_IMG):
            try:
                img = pygame.image.load(BOSS_IMG).convert_alpha()
                img = pygame.transform.smoothscale(img, boss_size)
            except Exception:
                img = load_enemy_image(ENEMY_BASIC_IMG, size=boss_size, fallback_color=(180, 60, 60))
        else:
            img = load_enemy_image(ENEMY_BASIC_IMG, size=boss_size, fallback_color=(180, 60, 60))

        super().__init__(pos=pos, hp=hp, image=img, player_ref=player_ref, size=boss_size)
        self.max_hp = hp
        self.dy = dy
        self.start_y = start_y
        self.descended = False
        self.speed_x = speed_x
        self.vx = 0.0
        self.vy = 0.0
        margin = 40
        self.min_x = margin
        self.max_x = SCREEN_WIDTH - margin - boss_size[0]
        # pos is provided as center x; convert to topleft pos.x
        self.pos.x = pos[0] - boss_size[0] // 2
        self.pos.y = pos[1]
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)
        self._prev_rect_x = self.rect.x

    def update(self, dt):
        # descend first
        if not self.descended:
            if self.pos.y < self.start_y:
                self.pos.y += self.dy * dt
                self.vy = self.dy
            else:
                self.pos.y = self.start_y
                self.descended = True
                # start horizontal movement to the right
                self.vx = abs(self.speed_x)
        else:
            # horizontal movement with bounce
            self.pos.x += self.vx * dt
            if self.pos.x < self.min_x:
                self.pos.x = self.min_x
                self.vx = abs(self.vx)
            elif self.pos.x > self.max_x:
                self.pos.x = self.max_x
                self.vx = -abs(self.vx)

        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # compute approximate visual vx for yaw
        self.vx = (self.rect.x - getattr(self, "_prev_rect_x", self.rect.x)) / max(1e-6, dt)
        self.vy = 0.0
        self._prev_rect_x = self.rect.x

        self._update_visual_targets(dt)
        # Boss shows HP via Game.draw; still apply transform for visuals
        self._apply_visual_transform(include_health_bar=False)
