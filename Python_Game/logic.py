import pygame

from partida import Partida
from mundo import en_base


RECTANGULO_MINIMAPA = pygame.Rect(1146, 20, 200, 200)


def manejar_evento_juego(evento: pygame.event.Event, partida: Partida) -> str | None:
    if evento.type == pygame.KEYDOWN:
        return _manejar_tecla(evento.key, partida)
    if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
        if not RECTANGULO_MINIMAPA.collidepoint(evento.pos):
            partida.seleccionar(evento.pos)
    return None


def _manejar_tecla(tecla: int, partida: Partida) -> str | None:
    if tecla == pygame.K_ESCAPE:
        return 'pausa'
    if tecla == pygame.K_e and en_base(partida.nave.pos):
        return 'tienda'
    ranuras = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}
    if tecla in ranuras:
        partida.nave.seleccionar_arma(ranuras[tecla])
    return None
