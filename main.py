
# Ponto de entrada do jogo
# Mantemos esse arquivo mínimo para separar inicialização da lógica do jogo em src/game.py.

from src.game import Game

if __name__ == "__main__":
    # Criamos a instância do jogo e chamamos run(), que contém o loop principal.
    # Isso permite importar Game em outros testes sem disparar o loop automaticamente.
    game = Game()
    game.run()
