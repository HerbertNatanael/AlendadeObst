# src/enemy.py
# Inimigos e projéteis: BasicEnemy, ZigZagEnemy, FastEnemy, ShooterEnemy, BossEnemy
# Inclui EnemyBullet e BossBullet. load_image_safe registra avisos quando assets faltam.
#
import os
import math
import random
import pygame

# ---------------- paths ----------------
ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
BOSS_IMG = os.path.join(ASSETS_IMAGES, "boss.png")
BOSS_BULLET_IMG = os.path.join(ASSETS_IMAGES, "boss_bullet.png")
ENEMY_IMG = os.path.join(ASSETS_IMAGES, "enemy.png")
ENEMY_BULLET_IMG = os.path.join(ASSETS_IMAGES, "enemy_bullet.png")
SHOOTER_IMG = os.path.join(ASSETS_IMAGES, "shooter.png")
ZIGZAG_IMG = os.path.join(ASSETS_IMAGES, "zigzag.png")
FAST_IMG = os.path.join(ASSETS_IMAGES, "fast.png")

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800

_missing_warned = set()

def load_image_safe(path, size=None, fallback_color=(180, 60, 60)):
    """
    Tenta carregar a imagem em `path`. Se não existir, retorna um fallback visível.
    Registra um aviso no console apenas uma vez por path ausente.
    Se `size` for provido, escala a imagem mantendo alpha.
    """
    try:
        if os.path.isfile(path):
            img = pygame.image.load(path).convert_alpha()
            if size is not None:
                try:
                    img = pygame.transform.smoothscale(img, size)
                except Exception:
                    img = pygame.transform.scale(img, size)
            return img
        else:
            # log uma única vez para evitar spam
            if path not in _missing_warned:
                print(f"Aviso: asset não encontrado: {path}")
                _missing_warned.add(path)
    except Exception as e:
        if path not in _missing_warned:
            print(f"Aviso: falha ao carregar {path}: {e}")
            _missing_warned.add(path)

    # fallback visual: retângulo com borda (mais legível que um quadrado simples)
    w, h = size if size else (48, 48)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((fallback_color[0], fallback_color[1], fallback_color[2], 220))
    pygame.draw.rect(surf, (30, 30, 30), surf.get_rect(), 3, border_radius=6)
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
        # vx/vy interpreted as per-second velocity
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)
        # remove if outside reasonable bounds
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
        # override in subclasses
        self.pos.x += self.vx * dt
        self.pos.y += self.vy * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))


# ---------------- BasicEnemy ----------------
class BasicEnemy(Enemy):
    """Inimigo básico: move em direção ao jogador (com componente descendente)."""
    def __init__(self, pos=(240, -40), hp=1, speed=80, player_ref=None):
        img = load_image_safe(ENEMY_IMG, (48, 48), (200, 80, 80))
        super().__init__(pos=pos, hp=hp, image=img, size=(48, 48), player_ref=player_ref)
        self.speed = speed
        self.vy = speed

    def update(self, dt):
        # se temos referência do player, tente mover levemente em sua direção X
        if self.player_ref is not None and hasattr(self.player_ref, "rect"):
            px = self.player_ref.rect.centerx
            dx = px - self.pos.x
            # normalize horizontal component and scale small so enemy generally goes down
            if abs(dx) > 6:
                steer = 0.5 * math.copysign(1, dx)
                self.vx = steer * 60
            else:
                self.vx = 0
        else:
            self.vx = 0

        # sempre descer
        self.vy = self.speed
        super().update(dt)


# ---------------- ZigZagEnemy ----------------
class ZigZagEnemy(Enemy):
    """Inimigo que faz zigzag horizontal enquanto desce."""
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
        # sinusoidal x motion
        self.pos.x += math.sin(self.t * self.frequency * 2.0 * math.pi) * self.amplitude * dt
        self.pos.y += self.vy * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))


# ---------------- FastEnemy ----------------
class FastEnemy(Enemy):
    """Inimigo rápido que vai direto pra baixo."""
    def __init__(self, pos=(240, -40), hp=1, dy=240, player_ref=None):
        img = load_image_safe(FAST_IMG, (40, 40), (240, 140, 60))
        super().__init__(pos=pos, hp=hp, image=img, size=(40, 40), player_ref=player_ref)
        self.vy = dy

    def update(self, dt):
        super().update(dt)


# ---------------- ShooterEnemy ----------------
class ShooterEnemy(Enemy):
    """
    Inimigo que desce até certa distância (stop_distance) e para, então atira para o jogador.
    Produz projéteis e os armazena em .new_bullets (lista) que o game.py deverá pegar.
    """
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
        self.new_bullets = []  # bullets will be appended here for game.py to collect

    def update(self, dt):
        if not self.stopped:
            # move down until reach stop_y
            if self.pos.y < self.stop_y:
                self.pos.y += self.vy * dt
            else:
                self.pos.y = self.stop_y
                self.stopped = True
                self.shoot_timer = 0.2  # pequeno delay antes de atirar
        else:
            # atira periodicamente
            self.shoot_timer += dt
            if self.shoot_timer >= self.shoot_cooldown:
                self.shoot_timer = 0.0
                # cria 1 projétil em direção ao jogador (ou em leque)
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
                    # fallback: shoot straight down
                    b = EnemyBullet(self.rect.center, 0, self.bullet_speed, speed=self.bullet_speed)
                    self.new_bullets.append(b)

        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def pop_pending_bullet(self):
        """Returna próximo projétil pendente (ou None). usado por game.py."""
        if self.new_bullets:
            return self.new_bullets.pop(0)
        return None


# ---------------- BossEnemy (mais completo) ----------------
class BossEnemy(Enemy):
    """
    Boss final:
    - desce até start_y
    - move horizontalmente (vaivém)
    - dispara padrões variados (usa BossBullet)
    - guarda balas em new_bullets para game.py coletar
    """
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
        # descer inicialmente
        if not self.descended:
            if self.pos.y < self.start_y:
                self.pos.y += self.dy * dt
            else:
                self.pos.y = self.start_y
                self.descended = True
                self.vx = self.speed_x
        else:
            # mover horizontalmente e ricochetear nas bordas
            self.pos.x += self.vx * dt
            if self.pos.x < self.min_x:
                self.pos.x = self.min_x
                self.vx = abs(self.vx)
            elif self.pos.x > self.max_x:
                self.pos.x = self.max_x
                self.vx = -abs(self.vx)

            # timer de rajadas
            self.shoot_timer += dt
            if self.shoot_timer >= self.shoot_cooldown:
                self.shoot_timer = 0.0
                self._fire_pattern()

        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def _fire_pattern(self):
        """Alterna entre padrões de disparo; adiciona BossBullet(s) em self.new_bullets."""
        self.pattern_index = (self.pattern_index + 1) % 4
        cx, cy = self.rect.center

        if self.pattern_index == 0:
            # leque frontal (com gap no centro para passagem)
            gap = 40  # pixels; leave central gap by skipping some angles
            angles = [-45, -30, -15, 0, 15, 30, 45]
            # make a central gap by removing some angles around 0
            filtered = [a for a in angles if not (-gap/2 < a < gap/2)]
            for a in filtered:
                rad = math.radians(a)
                vx = math.sin(rad) * 300
                vy = math.cos(rad) * 300
                b = BossBullet((cx, cy + 20), vx, vy, speed=300)
                self.new_bullets.append(b)

        elif self.pattern_index == 1:
            # diagonais alternadas: curtinhas, vindo dos lados deixando ranhura no meio
            left_x = 60
            right_x = SCREEN_WIDTH - 60
            for i in range(5):
                angle = -20 - i * 5
                rad = math.radians(angle)
                vx = math.sin(rad) * 260
                vy = math.cos(rad) * 260
                self.new_bullets.append(BossBullet((left_x, cy + 20), vx, vy, speed=260))
                # mirrored angle from right
                rad2 = math.radians(-angle)
                vx2 = math.sin(rad2) * 260
                vy2 = math.cos(rad2) * 260
                self.new_bullets.append(BossBullet((right_x, cy + 20), vx2, vy2, speed=260))

        elif self.pattern_index == 2:
            # linhas verticais com um gap aleatório para passagem
            gap_center = random.randint(120, SCREEN_WIDTH - 120)
            gap_width = random.randint(60, 120)
            step = 60
            for x in range(40, SCREEN_WIDTH, step):
                # se x dentro do gap, pule (deixe canal)
                if gap_center - gap_width // 2 <= x <= gap_center + gap_width // 2:
                    continue
                b = BossBullet((x, cy + 20), 0, 300, speed=300)
                self.new_bullets.append(b)

        else:
            # padrão 4: meia-espiral (vários ângulos em sequência) deixando espaço
            base = random.randint(0, 60)
            for i in range(10):
                a = base + i * 18
                rad = math.radians(a)
                vx = math.sin(rad) * 240
                vy = math.cos(rad) * 240
                # skip one bullet to make a corridor
                if i == 4:
                    continue
                self.new_bullets.append(BossBullet((cx, cy + 20), vx, vy, speed=240))
