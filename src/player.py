# src/player.py
# Player com movimento (WASD / setas) e animação suave de "virar" (yaw) em torno do eixo vertical.
# - ao mover para a direita: sprite "vira" (compressão horizontal + leve rotação) para a direita
# - ao mover para cima: sprite alinha a proa para cima (com efeito diferente)
# - interpolação suave entre estados para evitar saltos bruscos
#
# Ajuste os parâmetros de TUNING no topo deste arquivo para calibrar a sensação.

import os
import pygame
import time
import math

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
PLAYER_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "player.png")

# ---------- PARÂMETROS DE TUNING ----------
SPRITE_DRAW_SIZE = (64, 64)     # tamanho final do sprite desenhado (px)
DEFAULT_SPEED = 300.0           # px/s
DEFAULT_SHOOT_COOLDOWN = 0.25   # s entre tiros
DEFAULT_BULLET_SPEED = 700.0    # px/s

# Quanto compressão horizontal máxima aplicar ao virar 90° (0..1).
# 1.0 = sem compressão, 0.5 = largura reduzida a metade quando virar totalmente.
MAX_HORIZ_SCALE = 0.72

# Ângulo 2D máximo (graus) de rotação visual quando vira lateralmente
MAX_YAW_ROT_DEG = 14.0

# Ângulo adicional (graus) quando move para cima (aponta a proa para cima)
PITCH_UP_ROT_DEG = -12.0  # negativo = rotaciona pra "norte" no plano 2D

# Velocidade da interpolação (quanto maior, mais rápido a sprite "vira" para o alvo)
TILT_SPEED = 10.0  # unidades por segundo (usa lerp com fator dt * TILT_SPEED)

# -----------------------------------------

class Player(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700)):
        super().__init__()
        self.speed = DEFAULT_SPEED

        # Carrega sprite (ou fallback)
        self.original_image = None
        if os.path.isfile(PLAYER_IMAGE_PATH):
            try:
                img = pygame.image.load(PLAYER_IMAGE_PATH).convert_alpha()
                # redimensiona a imagem-fonte para o tamanho de desenho desejado (mantém proporção)
                img = pygame.transform.smoothscale(img, SPRITE_DRAW_SIZE)
                self.original_image = img
            except Exception as e:
                print(f"Aviso: falha ao carregar player.png: {e}")
                self.original_image = self._make_placeholder()
        else:
            self.original_image = self._make_placeholder()

        # A image corrente desenhada (modificada por tilt)
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=pos)

        # Mantemos pos float para movimento suave
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.screen_rect = pygame.Rect(0, 0, 480, 800)

        # Disparo cooldown
        self.shoot_cooldown = DEFAULT_SHOOT_COOLDOWN
        self._last_shot_time = -999.0

        # Estado visual para animação (valores continuam entre frames)
        # yaw_value varia de -1 (virar totalmente à esquerda) a +1 (virar totalmente à direita)
        self.yaw_value = 0.0          # valor atual
        self.target_yaw_value = 0.0   # valor alvo (calculado a cada update)

        # pitch_value para ajustar quando mover para cima (0..1)
        self.pitch_value = 0.0
        self.target_pitch_value = 0.0

    def _make_placeholder(self):
        surf = pygame.Surface(SPRITE_DRAW_SIZE, pygame.SRCALPHA)
        w,h = SPRITE_DRAW_SIZE
        pygame.draw.polygon(surf, (200,160,80), [(w//2,0),(w-6,h//2),(w//2,h-2),(6,h//2)])
        pygame.draw.rect(surf, (100,60,20), (w//2-8,h//2,16,10))
        return surf

    def update(self, dt):
        """
        Chamado a cada frame: atualiza movimento e estado visual alvo.
        dt: delta time em segundos.
        """
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

        # Normaliza diagonal (para manter velocidade constante)
        if dx != 0 and dy != 0:
            inv = math.sqrt(0.5)
            dx *= inv
            dy *= inv

        # Aplica movimento com dt (pos é top-left, rect.center usa pos + half)
        self.pos.x += dx * self.speed * dt
        self.pos.y += dy * self.speed * dt

        # Mantém dentro da tela
        # atualiza rect temporariamente para clamping
        tmp_rect = self.rect.copy()
        tmp_rect.x = int(self.pos.x)
        tmp_rect.y = int(self.pos.y)
        tmp_rect.clamp_ip(self.screen_rect)
        # atualiza pos com os limites aplicados
        self.pos.x = tmp_rect.x
        self.pos.y = tmp_rect.y
        # sincroniza rect
        self.rect.x = int(self.pos.x)
        self.rect.y = int(self.pos.y)

        # --- cálculo do estado visual alvo (target_yaw_value / target_pitch_value) ---
        # Usamos dx,dy (direção do movimento) como entrada.
        # yaw alvo = dx (direção horizontal) -> mapeamos dx (-1..1) diretamente para -1..1
        self.target_yaw_value = float(max(-1.0, min(1.0, dx)))

        # pitch é maior quando se move para cima; mapeamos dy (-1 para subir) para 0..1
        # queremos pitch positivo (apontar para cima) quando dy < 0
        if dy < 0:
            # dy == -1 -> pitch 1.0 ; dy == 0 -> pitch 0
            self.target_pitch_value = float(min(1.0, -dy))
        else:
            self.target_pitch_value = 0.0

        # Interpolamos suavemente os valores (lerp)
        interp = min(1.0, TILT_SPEED * dt)  # fator em [0,1]
        self.yaw_value += (self.target_yaw_value - self.yaw_value) * interp
        self.pitch_value += (self.target_pitch_value - self.pitch_value) * interp

        # Após atualizar valores, geramos a imagem transformada para desenhar
        self._update_transformed_image()

    def _update_transformed_image(self):
        """
        Aplica as transformações visuais à self.original_image para simular yaw/pitch.
        Estratégia:
         - escala horizontal = lerp(1.0, MAX_HORIZ_SCALE, abs(yaw_value))
         - rotação 2D = yaw_sign * MAX_YAW_ROT_DEG * abs(yaw_value) + pitch_contrib
         - combinamos escala e rotação com rotozoom/smoothscale
        """
        # compressão horizontal baseada em yaw
        yaw = self.yaw_value  # -1..1
        abs_yaw = abs(yaw)
        horiz_scale = 1.0 - (1.0 - MAX_HORIZ_SCALE) * abs_yaw  # de 1.0 (frente) a MAX_HORIZ_SCALE (de lado)

        # rotacao lateral (2D), direita -> negativo rotation (dependendo do feel)
        yaw_rot = -yaw * MAX_YAW_ROT_DEG

        # rotacao por pitch (ao mover para cima)
        pitch_rot = self.pitch_value * PITCH_UP_ROT_DEG  # pitch_value 0..1

        total_rot = yaw_rot + pitch_rot

        # aplica escala horizontal via smoothscale: primeiro escala a largura, mantendo altura
        w0,h0 = SPRITE_DRAW_SIZE
        new_w = max(2, int(w0 * horiz_scale))
        # scaling intermediate image to apply shear-like effect
        scaled = pygame.transform.smoothscale(self.original_image, (new_w, h0))

        # para manter o sprite centrado, criamos uma surface com tamanho original e blitamos scaled no centro
        canvas = pygame.Surface((w0, h0), pygame.SRCALPHA)
        x_offset = (w0 - new_w) // 2
        canvas.blit(scaled, (x_offset, 0))

        # agora aplicamos rotação 2D leve (rotozoom)
        # rotação com rotozoom preserva qualidade (anti-aliasing interno)
        try:
            rotated = pygame.transform.rotozoom(canvas, total_rot, 1.0)
        except Exception:
            # fallback: sem rotozoom
            rotated = pygame.transform.rotate(canvas, total_rot)

        # por fim, guardamos a imagem e atualizamos rect mantendo o center
        old_center = self.rect.center
        self.image = rotated
        self.rect = self.image.get_rect()
        self.rect.center = old_center
        # também atualiza pos (topleft) para manter consistência interna
        self.pos.x = self.rect.x
        self.pos.y = self.rect.y

    # ---------- método de disparo (permanece compatível com as versões anteriores) ----------
    def shoot(self, target_pos=None):
        now = time.perf_counter()
        if now - self._last_shot_time < self.shoot_cooldown:
            return None
        self._last_shot_time = now

        # import dinâmico
        try:
            from src.bullet import Bullet
        except Exception as e:
            print(f"Aviso: não foi possível importar Bullet: {e}")
            return None

        sx = self.rect.centerx
        sy = self.rect.top - 8

        if target_pos is None:
            try:
                target_pos = pygame.mouse.get_pos()
            except Exception:
                target_pos = None

        if target_pos is None:
            try:
                b = Bullet(pos=(sx,sy), vx=0.0, vy=-DEFAULT_BULLET_SPEED, owner="player")
                return b
            except Exception:
                return None

        tx, ty = target_pos
        dx = tx - sx
        dy = ty - sy
        dist = math.hypot(dx, dy) or 1.0
        vx = dx / dist * DEFAULT_BULLET_SPEED
        vy = dy / dist * DEFAULT_BULLET_SPEED

        try:
            b = Bullet(pos=(sx,sy), vx=vx, vy=vy, owner="player")
            return b
        except TypeError:
            try:
                b = Bullet((sx,sy), -DEFAULT_BULLET_SPEED)
                return b
            except Exception:
                return None
