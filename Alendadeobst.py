"""
Jogo de teste em Pygame - main.py
Controles:
  ← → ↑ ↓  : mover o personagem
  ESC      : sair
"""

import random
import pygame
import sys

# Configurações
WIDTH, HEIGHT = 640, 480
FPS = 60
PLAYER_SIZE = 32
PLAYER_SPEED = 5
COIN_RADIUS = 10

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jogo de Teste - Pygame")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)

# Estado do jogador
player = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
score = 0

# Função para criar uma moeda em posição válida
def spawn_coin():
    x = random.randint(COIN_RADIUS, WIDTH - COIN_RADIUS)
    y = random.randint(COIN_RADIUS, HEIGHT - COIN_RADIUS)
    return pygame.Vector2(x, y)

coin_pos = spawn_coin()

# Função para desenhar HUD (pontuação)
def draw_hud(surface, score):
    text = font.render(f"Pontuação: {score}", True, (255, 255, 255))
    surface.blit(text, (10, 10))

# Loop principal
running = True
while running:
    dt = clock.tick(FPS)  # limita o FPS

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # Entrada de teclado
    keys = pygame.key.get_pressed()
    dx = dy = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        dx = -PLAYER_SPEED
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        dx = PLAYER_SPEED
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        dy = -PLAYER_SPEED
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        dy = PLAYER_SPEED

    # Atualiza posição do jogador com limites da tela
    player.x += dx
    player.y += dy
    player.x = max(0, min(WIDTH - PLAYER_SIZE, player.x))
    player.y = max(0, min(HEIGHT - PLAYER_SIZE, player.y))

    # Verifica colisão com a moeda (distância entre centro e coin)
    player_center = pygame.Vector2(player.centerx, player.centery)
    if player_center.distance_to(coin_pos) <= COIN_RADIUS + PLAYER_SIZE / 2:
        score += 1
        coin_pos = spawn_coin()

    # Desenho
    screen.fill((30, 30, 40))  # fundo
    # desenha moeda
    pygame.draw.circle(screen, (255, 215, 0), (int(coin_pos.x), int(coin_pos.y)), COIN_RADIUS)
    # desenha jogador (quadrado)
    pygame.draw.rect(screen, (100, 200, 255), player)
    # desenha HUD
    draw_hud(screen, score)

    pygame.display.flip()

pygame.quit()
sys.exit()

