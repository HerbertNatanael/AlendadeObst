# src/player.py
# Implementação do Player com movimento (WASD / setas) e tiro direcionado ao cursor.
# - shoot(target_pos=None): cria uma Bullet que segue em direção a target_pos.
# - Se target_pos for None, usa pygame.mouse.get_pos().
# - Proteções para evitar crashes caso falhe a importação/criação da Bullet.
#
# Observações:
# - Ajuste `bullet_speed` para deixar o tiro mais rápido/lento.
# - Ajuste `shoot_cooldown` para controlar a cadência de tiro.

import os
import pygame
import time

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
PLAYER_IMAGE_PATH = os.path.join(ASSETS_IMAGES, "player.png")

# Configurações do jogador (fáceis de alterar)
DEFAULT_SPEED = 300.0        # px/s
DEFAULT_SHOOT_COOLDOWN = 0.25  # segundos entre tiros
DEFAULT_BULLET_SPEED = 700.0  # px/s (velocidade das balas do jogador)

class Player(pygame.sprite.Sprite):
    def __init__(self, pos=(240, 700)):
        super().__init__()
        self.speed = DEFAULT_SPEED  # pixels por segundo

        # Carrega sprite do jogador (se existir), senão desenha um placeholder
        if os.path.isfile(PLAYER_IMAGE_PATH):
            try:
                img = pygame.image.load(PLAYER_IMAGE_PATH).convert_alpha()
                # escala para tamanho consistente
                self.image = pygame.transform.smoothscale(img, (64, 64))
            except Exception as e:
                print(f"Aviso: falha ao carregar {PLAYER_IMAGE_PATH}: {e}")
                self.image = self._make_placeholder()
        else:
            self.image = self._make_placeholder()

        self.rect = self.image.get_rect(center=pos)
        self.screen_rect = pygame.Rect(0, 0, 480, 800)

        # Disparo - cooldown
        self.shoot_cooldown = DEFAULT_SHOOT_COOLDOWN
        self._last_shot_time = -999.0  # timestamp do último tiro

    def _make_placeholder(self):
        """Cria um placeholder simples (um navio estilizado) caso não haja imagem."""
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (200, 160, 80), [(32,0),(58,24),(32,56),(6,24)])
        pygame.draw.rect(surf, (100, 60, 20), (22, 30, 20, 15))
        return surf

    def update(self, dt):
        """Atualiza posição do player com base nas teclas pressionadas."""
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

        # Normaliza velocidade diagonal para manter velocidade constante
        if dx != 0 and dy != 0:
            import math
            dx *= math.sqrt(0.5)
            dy *= math.sqrt(0.5)

        # Aplica movimento com delta time
        self.rect.x += int(dx * self.speed * dt)
        self.rect.y += int(dy * self.speed * dt)

        # Mantém dentro dos limites da tela
        self.rect.clamp_ip(self.screen_rect)

    def shoot(self, target_pos=None):
        """
        Cria e retorna uma Bullet apontando para target_pos.
        - target_pos: (x, y) em coordenadas de tela. Se None, usa a posição atual do mouse.
        - Retorna: Bullet instance ou None (se em cooldown ou se ocorrer erro).
        - A velocidade da bala é determinada por DEFAULT_BULLET_SPEED.
        """
        now = time.perf_counter()
        if now - self._last_shot_time < self.shoot_cooldown:
            return None  # ainda em cooldown

        self._last_shot_time = now

        # Import dinâmico para evitar import circular
        try:
            from src.bullet import Bullet
        except Exception as e:
            print(f"Aviso: não foi possível importar Bullet: {e}")
            return None

        # Origem da bala (centro horizontal, um pouco acima do navio)
        sx = self.rect.centerx
        sy = self.rect.top - 8

        # Determina o alvo: parâmetro ou posição atual do mouse
        if target_pos is None:
            try:
                target_pos = pygame.mouse.get_pos()
            except Exception:
                target_pos = None

        # Se não houver alvo, dispara reto para cima como fallback
        if target_pos is None:
            try:
                bullet = Bullet(pos=(sx, sy), vx=0.0, vy=-DEFAULT_BULLET_SPEED, owner="player")
                return bullet
            except Exception as e:
                # Tentativa de fallback compatível com versões antigas
                try:
                    bullet = Bullet((sx, sy), -DEFAULT_BULLET_SPEED)
                    return bullet
                except Exception as e2:
                    print(f"Aviso: falha ao criar Bullet (fallback): {e} / {e2}")
                    return None

        # Calcula vetor direção do tiro
        tx, ty = target_pos
        dx = tx - sx
        dy = ty - sy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist == 0:
            dist = 1.0  # evita divisão por zero

        # Normaliza e aplica velocidade desejada
        bullet_speed = DEFAULT_BULLET_SPEED
        vx = dx / dist * bullet_speed
        vy = dy / dist * bullet_speed

        # Cria a Bullet com vx/vy e owner="player"
        try:
            bullet = Bullet(pos=(sx, sy), vx=vx, vy=vy, owner="player")
            return bullet
        except TypeError:
            # Caso a assinatura da Bullet seja diferente (defensivo), tenta formas alternativas
            try:
                bullet = Bullet((sx, sy), -bullet_speed)
                return bullet
            except Exception as e:
                print(f"Aviso: não foi possível criar Bullet: {e}")
                return None
        except Exception as e:
            print(f"Aviso: erro ao criar Bullet: {e}")
            return None
