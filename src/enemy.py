# src/enemy.py
# Enemies module (com loading robusto de imagens e avisos detalhados)
#
import os
import math
import random
import pygame

# ---------------- paths ----------------
BASE_DIR = os.path.dirname(__file__)
ASSETS_IMAGES = os.path.normpath(os.path.join(BASE_DIR, "..", "assets", "images"))

# padrão de nomes que o jogo usa; você pode renomear suas imagens para um desses nomes
EXPECTED_IMAGES = {
    "boss": "boss.png",
    "boss_bullet": "boss_bullet.png",
    "enemy": "enemy.png",
    "enemy_bullet": "enemy_bullet.png",
    "shooter": "shooter.png",
    "zigzag": "zigzag.png",
    "fast": "fast.png",
}

# paths construídos (usados pelas funções, mas loader tentará alternativas)
BOSS_IMG = os.path.join(ASSETS_IMAGES, EXPECTED_IMAGES["boss"])
BOSS_BULLET_IMG = os.path.join(ASSETS_IMAGES, EXPECTED_IMAGES["boss_bullet"])
ENEMY_IMG = os.path.join(ASSETS_IMAGES, EXPECTED_IMAGES["enemy"])
ENEMY_BULLET_IMG = os.path.join(ASSETS_IMAGES, EXPECTED_IMAGES["enemy_bullet"])
SHOOTER_IMG = os.path.join(ASSETS_IMAGES, EXPECTED_IMAGES["shooter"])
ZIGZAG_IMG = os.path.join(ASSETS_IMAGES, EXPECTED_IMAGES["zigzag"])
FAST_IMG = os.path.join(ASSETS_IMAGES, EXPECTED_IMAGES["fast"])

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800

_missing_warned = set()


def _try_variants(filename):
    """
    Gera uma lista de candidate paths para filename.
    - Se filename já for caminho absoluto/relativo existente, tenta direto.
    - Caso contrário, tenta basename com diferentes extensões dentro ASSETS_IMAGES.
    """
    candidates = []

    # se veio um path absoluto/relativo que contenha separadores, tenta direto primeiro
    if os.path.sep in filename or "/" in filename:
        candidates.append(os.path.normpath(filename))

    # tenta direto como dado (pode ser relativo)
    candidates.append(os.path.normpath(os.path.join(BASE_DIR, filename)))
    # tenta na pasta assets/images com o nome dado
    candidates.append(os.path.join(ASSETS_IMAGES, filename))

    # se o filename possui extensão, tente variantes de maiúscula/minúscula
    name, ext = os.path.splitext(filename)
    exts = [ext] if ext else [".png", ".PNG", ".jpg", ".jpeg"]
    # se não tinha ext, tente várias
    if not ext:
        exts = [".png", ".PNG", ".jpg", ".jpeg"]

    # se filename foi apenas nome sem ext, tente várias combinações dentro ASSETS_IMAGES
    base_only = os.path.basename(name)
    for e in exts:
        candidates.append(os.path.join(ASSETS_IMAGES, base_only + e))
        candidates.append(os.path.join(BASE_DIR, base_only + e))

    # dedupe e retorne
    seen = set()
    out = []
    for c in candidates:
        cn = os.path.normpath(c)
        if cn not in seen:
            out.append(cn)
            seen.add(cn)
    return out


def load_image_safe(path, size=None, fallback_color=(180, 60, 60)):
    """
    Carrega a imagem tentando várias alternativas.
    - path pode ser um caminho completo ou somente o nome do arquivo esperado.
    - se não encontrar nada, retorna um fallback contendo o nome do arquivo como texto (útil para debug).
    """
    tried = []
    for candidate in _try_variants(path):
        tried.append(candidate)
        if os.path.isfile(candidate):
            try:
                img = pygame.image.load(candidate).convert_alpha()
                if size is not None:
                    try:
                        img = pygame.transform.smoothscale(img, size)
                    except Exception:
                        img = pygame.transform.scale(img, size)
                return img
            except Exception as e:
                # caso falhe no carregamento (arquivo corrompido etc.)
                if candidate not in _missing_warned:
                    print(f"Aviso: falha ao carregar imagem '{candidate}': {e}")
                    _missing_warned.add(candidate)
                # continue tentando outros candidatos

    # se não achou nada, log detalhado (apenas uma vez por conjunto de tentativas)
    key = "|".join(tried)
    if key not in _missing_warned:
        print("Aviso: não foi possível localizar a imagem. Tente colocar um arquivo com um destes nomes/paths:")
        for t in tried:
            print("  ->", t)
        _missing_warned.add(key)

    # fallback visual: surface com texto do nome base (útil para identificar qual asset falta)
    w, h = size if size else (48, 48)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((fallback_color[0], fallback_color[1], fallback_color[2], 220))
    pygame.draw.rect(surf, (30, 30, 30), surf.get_rect(), 3, border_radius=6)

    # desenha uma sigla/label do arquivo esperado (basename) para debug
    try:
        basename = os.path.basename(path)
        font = pygame.font.SysFont("arial", max(10, min(20, w // 6)))
        txt = basename.replace(".png", "").replace(".PNG", "")
        label = font.render(txt, True, (20, 20, 20))
        rect = label.get_rect(center=(w // 2, h // 2))
        surf.blit(label, rect)
    except Exception:
        pass

    return surf


# ---------------- Enemy projectiles ----------------
class EnemyBullet(pygame.sprite.Sprite):
    """Projétil simples usado por inimigos (shooter enemies)."""
    def __init__(self, pos, vx, vy, speed=200, image_path=ENEMY_BULLET_IMG):
        super().__init__()
        self.image = load_image_safe(image_path, (14, 14), (240, 120, 60))
        self.rect = self.image.get_rect(center=pos)
        self.vx = vx
        self.vy = vy
        self.speed = speed

    def update(self, dt):
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)
        if (self.rect.top > SCREEN_HEIGHT + 50 or
                self.rect.bottom < -50 or
                self.rect.right < -60 or
                self.rect.left > SCREEN_WIDTH + 60):
            self.kill()


class BossBullet(pygame.sprite.Sprite):
    """Projétil do boss com imagem própria."""
    def __init__(self, pos, vx, vy, speed=280, image_path=BOSS_BULLET_IMG):
        super().__init__()
        self.image = load_image_safe(image_path, (20, 20), (255, 90, 90))
        self.rect = self.image.get_rect(center=pos)
        self.vx = vx
        self.vy = vy
        self.speed = speed

    def update(self, dt):
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)
        if (self.rect.top > SCREEN_HEIGHT + 60 or
                self.rect.bottom < -60 or
                self.rect.right < -60 or
                self.rect.left > SCREEN_WIDTH + 60):
            self.kill()


# ---------------- Base Enemy ----------------
class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos=(240, -50), hp=1, image=None, size=(48, 48), player_ref=None):
        super().__init__()
        self.hp = hp
        self.max_hp = hp
        self.player_ref = player_ref
        self.pos = pygame.math.Vector2(pos)
        self.size = size
        self.original_image = image if image is not None else load_image_safe(ENEMY_IMG, size)
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=pos)
        self.vx = 0.0
        self.vy = 0.0

    def take_damage(self, amount=1):
        self.hp -= amount
        if self.hp <= 0:
            try:
                self.kill()
            except Exception:
                pass
            return True
        return False

    def update(self, dt):
        self.pos.x += self.vx * dt
        self.pos.y += self.vy * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))


# ---------------- BasicEnemy ----------------
class BasicEnemy(Enemy):
    def __init__(self, pos=(240, -40), hp=1, speed=80, player_ref=None):
        img = load_image_safe(ENEMY_IMG, (48, 48), (200, 80, 80))
        super().__init__(pos=pos, hp=hp, image=img, size=(48, 48), player_ref=player_ref)
        self.speed = speed
        self.vy = speed

    def update(self, dt):
        if self.player_ref is not None and hasattr(self.player_ref, "rect"):
            px = self.player_ref.rect.centerx
            dx = px - self.pos.x
            if abs(dx) > 6:
                steer = 0.5 * math.copysign(1, dx)
                self.vx = steer * 60
            else:
                self.vx = 0
        else:
            self.vx = 0
        self.vy = self.speed
        super().update(dt)


# ---------------- ZigZagEnemy ----------------
class ZigZagEnemy(Enemy):
    def __init__(self, pos=(240, -40), hp=1, dy=120, amplitude=60, frequency=1.0, player_ref=None):
        img = load_image_safe(ZIGZAG_IMG, (48, 48), (180, 110, 80))
        super().__init__(pos=pos, hp=hp, image=img, size=(48, 48), player_ref=player_ref)
        self.base_y = pos[1]
        self.dy = dy
        self.amplitude = amplitude
        self.frequency = frequency
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        self.vy = self.dy
        self.pos.x += math.sin(self.t * self.frequency * 2.0 * math.pi) * self.amplitude * dt
        self.pos.y += self.vy * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))


# ---------------- FastEnemy ----------------
class FastEnemy(Enemy):
    def __init__(self, pos=(240, -40), hp=1, dy=240, player_ref=None):
        img = load_image_safe(FAST_IMG, (40, 40), (240, 140, 60))
        super().__init__(pos=pos, hp=hp, image=img, size=(40, 40), player_ref=player_ref)
        self.vy = dy

    def update(self, dt):
        super().update(dt)


# ---------------- ShooterEnemy ----------------
class ShooterEnemy(Enemy):
    def __init__(self, pos=(240, -40), hp=2, dy=90, stop_distance=200, shoot_cooldown=1.6,
                 bullet_speed=180, player_ref=None):
        img = load_image_safe(SHOOTER_IMG, (56, 56), (200, 50, 120))
        super().__init__(pos=pos, hp=hp, image=img, size=(56, 56), player_ref=player_ref)
        self.vy = dy
        self.stop_y = stop_distance
        self.stopped = False
        self.shoot_cooldown = shoot_cooldown
        self.shoot_timer = 0.0
        self.bullet_speed = bullet_speed
        self.new_bullets = []

    def update(self, dt):
        if not self.stopped:
            if self.pos.y < self.stop_y:
                self.pos.y += self.vy * dt
            else:
                self.pos.y = self.stop_y
                self.stopped = True
                self.shoot_timer = 0.2
        else:
            self.shoot_timer += dt
            if self.shoot_timer >= self.shoot_cooldown:
                self.shoot_timer = 0.0
                if self.player_ref is not None and hasattr(self.player_ref, "rect"):
                    px, py = self.player_ref.rect.center
                    cx, cy = self.rect.center
                    dx = px - cx
                    dy = py - cy
                    dist = math.hypot(dx, dy) or 1.0
                    vx = dx / dist * self.bullet_speed
                    vy = dy / dist * self.bullet_speed
                    b = EnemyBullet((cx, cy + 10), vx, vy, speed=self.bullet_speed)
                    self.new_bullets.append(b)
                else:
                    b = EnemyBullet(self.rect.center, 0, self.bullet_speed, speed=self.bullet_speed)
                    self.new_bullets.append(b)

        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def pop_pending_bullet(self):
        if self.new_bullets:
            return self.new_bullets.pop(0)
        return None


# ---------------- BossEnemy ----------------
class BossEnemy(Enemy):
    def __init__(self, pos=(SCREEN_WIDTH // 2, -220), dy=60, start_y=100, hp=50, speed_x=120, player_ref=None):
        size = (120, 80)
        img = load_image_safe(BOSS_IMG, size, (150, 50, 60))
        super().__init__(pos=pos, hp=hp, image=img, size=size, player_ref=player_ref)
        self.dy = dy
        self.start_y = start_y
        self.descended = False
        self.speed_x = speed_x
        self.vx = 0.0
        self.min_x = 40
        self.max_x = SCREEN_WIDTH - size[0] - 40
        self.pos = pygame.math.Vector2(pos)
        self.shoot_timer = 0.0
        self.shoot_cooldown = 2.5
        self.pattern_index = 0
        self.new_bullets = []

    def update(self, dt):
        if not self.descended:
            if self.pos.y < self.start_y:
                self.pos.y += self.dy * dt
            else:
                self.pos.y = self.start_y
                self.descended = True
                self.vx = self.speed_x
        else:
            self.pos.x += self.vx * dt
            if self.pos.x < self.min_x:
                self.pos.x = self.min_x
                self.vx = abs(self.vx)
            elif self.pos.x > self.max_x:
                self.pos.x = self.max_x
                self.vx = -abs(self.vx)

            self.shoot_timer += dt
            if self.shoot_timer >= self.shoot_cooldown:
                self.shoot_timer = 0.0
                self._fire_pattern()

        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def _fire_pattern(self):
        self.pattern_index = (self.pattern_index + 1) % 4
        cx, cy = self.rect.center

        if self.pattern_index == 0:
            gap = 40
            angles = [-45, -30, -15, 0, 15, 30, 45]
            filtered = [a for a in angles if not (-gap/2 < a < gap/2)]
            for a in filtered:
                rad = math.radians(a)
                vx = math.sin(rad) * 300
                vy = math.cos(rad) * 300
                self.new_bullets.append(BossBullet((cx, cy + 20), vx, vy, speed=300))

        elif self.pattern_index == 1:
            left_x = 60
            right_x = SCREEN_WIDTH - 60
            for i in range(5):
                angle = -20 - i * 5
                rad = math.radians(angle)
                vx = math.sin(rad) * 260
                vy = math.cos(rad) * 260
                self.new_bullets.append(BossBullet((left_x, cy + 20), vx, vy, speed=260))
                rad2 = math.radians(-angle)
                vx2 = math.sin(rad2) * 260
                vy2 = math.cos(rad2) * 260
                self.new_bullets.append(BossBullet((right_x, cy + 20), vx2, vy2, speed=260))

        elif self.pattern_index == 2:
            gap_center = random.randint(120, SCREEN_WIDTH - 120)
            gap_width = random.randint(60, 120)
            step = 60
            for x in range(40, SCREEN_WIDTH, step):
                if gap_center - gap_width // 2 <= x <= gap_center + gap_width // 2:
                    continue
                self.new_bullets.append(BossBullet((x, cy + 20), 0, 300, speed=300))

        else:
            base = random.randint(0, 60)
            for i in range(10):
                a = base + i * 18
                rad = math.radians(a)
                vx = math.sin(rad) * 240
                vy = math.cos(rad) * 240
                if i == 4:
                    continue
                self.new_bullets.append(BossBullet((cx, cy + 20), vx, vy, speed=240))
