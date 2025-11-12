# src/background.py
# Parallax background simples para o jogo.
# - Camada "water" (faz o efeito principal vertical contínuo).
# - Camadas "side" (left e right) que deslocam também (padrão vertical, mas você pode adaptar).
# - Suporta imagens em assets/images/ (nomes padrão abaixo). Se faltarem, usa fallback procedural.
#
# Uso:
#   bg = ParallaxBackground(screen_size=(480,800))
#   no loop principal (sempre, independente do movimento do player):
#       bg.update(dt)
#       bg.draw(screen)
#
import os
import math
import pygame
import random

ASSETS_IMAGES = os.path.join(os.path.dirname(__file__), "..", "assets", "images")
# nomes de arquivo opcionais (se estiverem presentes, serão usados)
WATER_IMG = os.path.join(ASSETS_IMAGES, "bg_water.png")
SIDE_LEFT_IMG = os.path.join(ASSETS_IMAGES, "bg_side_left.png")
SIDE_RIGHT_IMG = os.path.join(ASSETS_IMAGES, "bg_side_right.png")


class ParallaxLayer:
    """Uma camada que pode ser uma imagem (tiled) ou um gerador procedural fallback."""
    def __init__(self, screen_size, image_path=None, speed=(0.0, 0.0), tile_vertical=True, horizontal_wrap=False):
        """
        screen_size: (w,h)
        image_path: caminho (opcional). Se None ou não existir, usa fallback procedural.
        speed: (vx, vy) em px/s — movimento da camada (positivo vy = move para baixo)
        tile_vertical: se True, usa tiling vertical (coloca 2 cópias e faz loop)
        horizontal_wrap: se True, permite movimento horizontal contínuo com wrap
        """
        self.screen_w, self.screen_h = screen_size
        self.image_path = image_path
        self.speed = pygame.math.Vector2(speed)
        self.tile_vertical = tile_vertical
        self.horizontal_wrap = horizontal_wrap

        self.offset = pygame.math.Vector2(0.0, 0.0)  # deslocamento corrente

        # carrega imagem se existir
        self.image = None
        if image_path and os.path.isfile(image_path):
            try:
                img = pygame.image.load(image_path).convert_alpha()
                # não redimensionamos aqui: a camada lida com tiling/scale no draw
                self.image = img
            except Exception:
                self.image = None

    def update(self, dt):
        # atualiza offset com base na velocidade (px/s)
        self.offset.x += self.speed.x * dt
        self.offset.y += self.speed.y * dt

        # modularizamos offsets para evitar crescimento infinito
        # se tile_vertical, fazemos modulo pela altura da imagem (ou tela)
        if self.image:
            iw, ih = self.image.get_size()
            if ih > 0 and self.tile_vertical:
                self.offset.y = self.offset.y % ih
            if iw > 0 and self.horizontal_wrap:
                self.offset.x = self.offset.x % iw
        else:
            # fallback: constrain offset simples por valores arbitrários
            self.offset.y = self.offset.y % max(1, self.screen_h)
            self.offset.x = self.offset.x % max(1, self.screen_w)

    def draw(self, surface):
        """Desenha a camada sobre a surface (deve cobrir toda a tela)."""
        if self.image:
            iw, ih = self.image.get_size()
            # escala horizontal para largura da tela se imagem de fundo for estreita (opcional)
            # desenhamos cópias tiling para cobrir a tela verticalmente/horizontalmente
            # calculamos o primeiro y a desenhar
            start_y = - (self.offset.y % ih)
            x_scale = 1.0
            # se imagem menor que tela width, vamos esticar na largura (mantemos aspecto)
            if iw < self.screen_w:
                x_scale = self.screen_w / iw
            # cria versão escalada se necessário
            if x_scale != 1.0:
                img_draw = pygame.transform.smoothscale(self.image, (int(iw * x_scale), ih))
                iw_draw, ih_draw = img_draw.get_size()
            else:
                img_draw = self.image
                iw_draw, ih_draw = iw, ih

            # horizontal tiling - vamos cobrir toda largura
            x = 0
            while x < self.screen_w:
                y = start_y
                # desenha cópias verticais suficientes para cobrir a tela
                while y < self.screen_h:
                    surface.blit(img_draw, (x + self.offset.x % iw_draw if self.horizontal_wrap else x, int(y)))
                    y += ih_draw
                x += iw_draw
        else:
            # procedural fallback (água simples: ondulações horizontais)
            self._draw_fallback(surface)

    def _draw_fallback(self, surface):
        """Desenho procedural simples se não houver imagem (água ou terreno)."""
        # se a camada mover-se rápido verticalmente consideramos água (ondas)
        vy = self.speed.y
        if abs(vy) > 30:
            # água: desenhos de faixas horizontais onduladas que se movem
            t_offset = self.offset.y
            for i in range(0, self.screen_h, 24):
                wave = int(6.0 * math.sin((i * 0.12) + t_offset * 0.04))
                color = (10, 60 + (i % 40), 140 + (i % 40))
                pygame.draw.rect(surface, color, (0, i + wave, self.screen_w, 12))
        else:
            # terreno lateral fallback: linhas verticais com variação de tom
            # desenhar retângulos nas laterais (20% da largura cada)
            side_w = int(self.screen_w * 0.22)
            left_x = 0
            right_x = self.screen_w - side_w
            # movimento vertical das faixas
            t = int(self.offset.y) % 60
            for j in range(-60, self.screen_h + 60, 30):
                shade = 80 + ((j + t) % 120)
                pygame.draw.rect(surface, (shade, shade-20, shade-40), (left_x, j, side_w, 24))
                pygame.draw.rect(surface, (shade, shade-20, shade-40), (right_x, j, side_w, 24))


class ParallaxBackground:
    """
    Combina camadas: water center + side left/right.
    Instancie e chame update(dt) e draw(surface) do loop principal.
    """
    def __init__(self, screen_size=(480,800),
                 water_speed=100.0,
                 side_speed=60.0,
                 water_image_path=WATER_IMG,
                 left_image_path=SIDE_LEFT_IMG,
                 right_image_path=SIDE_RIGHT_IMG):
        self.screen_size = screen_size
        w,h = screen_size

        # water: velocidade vertical (move para baixo)
        # Ajuste water_speed para sensacao de velocidade
        self.water_layer = ParallaxLayer(screen_size, image_path=water_image_path,
                                         speed=(0.0, water_speed), tile_vertical=True, horizontal_wrap=False)

        # sides: deslocamento vertical mais lento, podem usar imagens verticais
        # colocamos duas camadas para as laterais (left / right)
        # Se houver imagens, elas serão usadas; se não, fallback procedural desenhará barras
        self.left_layer = ParallaxLayer(screen_size, image_path=left_image_path,
                                        speed=(0.0, side_speed * 0.9), tile_vertical=True, horizontal_wrap=False)
        self.right_layer = ParallaxLayer(screen_size, image_path=right_image_path,
                                         speed=(0.0, side_speed * 0.9), tile_vertical=True, horizontal_wrap=False)

        # parâmetros de posicionamento das camadas laterais (porcentagem da tela)
        self.side_width_frac = 0.22  # largura da area lateral (22% esquerda/direita)
        # cores de fallback (quando não há imagem)
        self._fallback_water_color = (10, 70, 150)
        self._fallback_side_color = (90, 110, 70)

    def update(self, dt):
        # atualizamos todas as camadas sempre (independente do movimento do player)
        self.water_layer.update(dt)
        self.left_layer.update(dt)
        self.right_layer.update(dt)

    def draw(self, surface):
        # desenha água cobrindo toda a tela
        # se houver imagem de água, desenhamos primeiro ela; se não, desenhamos um preenchimento e fallback
        if self.water_layer.image:
            # desenha a layer full-screen first
            self.water_layer.draw(surface)
        else:
            surface.fill(self._fallback_water_color)
            self.water_layer.draw(surface)

        # desenha as laterais (com imagens ou fallback) por cima da água
        sw, sh = self.screen_size
        side_w = int(sw * self.side_width_frac)

        # left: produz uma surface auxiliar só com a área lateral e manda layer desenhar nela
        left_surf = pygame.Surface((side_w, sh), pygame.SRCALPHA)
        # se layer tiver imagem, seu draw cobrirá a left_surf verticalmente; se não, draw fallback desenha faixas
        self.left_layer.draw(left_surf)
        surface.blit(left_surf, (0, 0))

        # right:
        right_surf = pygame.Surface((side_w, sh), pygame.SRCALPHA)
        self.right_layer.draw(right_surf)
        surface.blit(right_surf, (sw - side_w, 0))