from dataclasses import dataclass
from typing import TYPE_CHECKING

import config as cfg
from mundo import en_base

if TYPE_CHECKING:
    from partida import Partida


@dataclass
class Mejoras:
    laser: int = 0
    vida: int = 0
    escudo: int = 0

    def nivel(self, tipo: str) -> int:
        if tipo not in ('laser', 'vida', 'escudo'):
            raise ValueError('Mejora desconocida')
        return getattr(self, tipo)

    def precio(self, tipo: str) -> int:
        return cfg.PRECIO_BASE_MEJORA * (self.nivel(tipo) + 1)


def aplicar_mejoras(partida: 'Partida') -> None:
    partida.nave.vida_maxima = cfg.VIDA_NAVE + partida.mejoras.vida * cfg.VIDA_POR_MEJORA
    partida.nave.escudo_maximo = cfg.ESCUDO_NAVE + partida.mejoras.escudo * cfg.ESCUDO_POR_MEJORA


def comprar(partida: 'Partida', tipo: str) -> str:
    nivel = partida.mejoras.nivel(tipo)
    if not partida.nave.viva or not en_base(partida.nave.pos):
        return 'La tienda solo esta disponible dentro de la base.'
    if nivel >= cfg.MAX_NIVEL_MEJORA:
        return 'Esta mejora ya alcanzo el nivel maximo.'
    precio = partida.mejoras.precio(tipo)
    if partida.creditos < precio:
        return f'Necesitas {precio} creditos.'
    partida.creditos -= precio
    setattr(partida.mejoras, tipo, nivel + 1)
    aplicar_mejoras(partida)
    if tipo == 'laser':
        return 'Mejora de laser adquirida: +10 de danio por disparo.'
    return f'Mejora de {tipo} adquirida. La regeneracion recupera la capacidad nueva.'
