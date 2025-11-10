import pygame 
pygame.init() #inicializa o pygame
surf = pygame.display.set_mode(400,400) #cria a janela do jogo
surf.fill(0,0,0) #pinta a janela de preto
pygame.display.update() #atualiza a janela do jogo

while True: 
    eventos = pygame.event.get()
    if eventos:
        print(eventos)


# colocar comentários das origens dos códigos (gpt, youtube, etc)