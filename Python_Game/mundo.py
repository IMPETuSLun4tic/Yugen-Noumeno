import random
import math
from dataclasses import dataclass, field

from pygame.math import Vector2
from pygame import Rect

import config as cfg
from entities import Enemigo
from utils import clamp


def proyectar_vector(vector: Vector2) -> Vector2:
    diagonal = math.sqrt(0.5)
    return Vector2((vector.x - vector.y) * diagonal,
                   (vector.x + vector.y) * diagonal * cfg.COMPRESION_ISOMETRICA)


def desproyectar_vector(vector: Vector2) -> Vector2:
    diagonal = math.sqrt(0.5)
    profundidad = vector.y / cfg.COMPRESION_ISOMETRICA
    return Vector2((vector.x + profundidad) * diagonal,
                   (profundidad - vector.x) * diagonal)


def elipse_proyectada(centro: Vector2, radio: float) -> Rect:
    ancho = max(2, round(radio * 2))
    alto = max(2, round(ancho * cfg.COMPRESION_ISOMETRICA))
    return Rect(round(centro.x - ancho / 2), round(centro.y - alto / 2), ancho, alto)


@dataclass
class Camara:
    centro: Vector2 = field(default_factory=Vector2)

    def seguir(self, posicion: Vector2) -> None:
        self.centro = Vector2(posicion)

    def a_pantalla(self, posicion: Vector2) -> Vector2:
        return proyectar_vector(Vector2(posicion) - self.centro) + Vector2(cfg.ANCHO / 2, cfg.ALTO / 2)

    def a_mundo(self, posicion: tuple[int, int]) -> Vector2:
        relativo = Vector2(posicion) - Vector2(cfg.ANCHO / 2, cfg.ALTO / 2)
        return self.centro + desproyectar_vector(relativo)


def en_base(posicion: Vector2, margen: float = 0.0) -> bool:
    return Vector2(posicion).distance_to(cfg.POSICION_BASE) <= cfg.RADIO_BASE + margen


@dataclass
class Mundo:
    semilla: int = field(default_factory=lambda: random.randrange(2**31))
    sectores_generados: set[tuple[int, int]] = field(default_factory=set)
    enemigos: dict[str, Enemigo] = field(default_factory=dict)
    activos: list[Enemigo] = field(default_factory=list)

    def actualizar(self, posicion: Vector2, dt: float) -> None:
        for sector in self._sectores_cercanos(posicion):
            if sector not in self.sectores_generados:
                self._generar_sector(sector)
        self.activar_cercanos(posicion)
        for enemigo in self.activos:
            enemigo.actualizar(dt, self._destino_enemigo(enemigo, posicion))
            self._excluir_de_base(enemigo)

    def activar_cercanos(self, posicion: Vector2) -> None:
        self.activos = self._enemigos_cercanos(posicion)[:cfg.MAX_ENEMIGOS_EN_PANTALLA]

    def _sectores_cercanos(self, posicion: Vector2) -> list[tuple[int, int]]:
        radio = cfg.RADIO_ACTIVACION
        minimo_x = int(max(0, posicion.x - radio) // cfg.TAMANIO_SECTOR)
        minimo_y = int(max(0, posicion.y - radio) // cfg.TAMANIO_SECTOR)
        maximo_x = int(min(cfg.ANCHO_MUNDO - 1, posicion.x + radio) // cfg.TAMANIO_SECTOR)
        maximo_y = int(min(cfg.ALTO_MUNDO - 1, posicion.y + radio) // cfg.TAMANIO_SECTOR)
        return [(x, y) for x in range(minimo_x, maximo_x + 1)
                for y in range(minimo_y, maximo_y + 1)]

    def _generar_sector(self, sector: tuple[int, int]) -> None:
        self.sectores_generados.add(sector)
        x, y = sector
        azar = random.Random(self.semilla ^ (x * 73856093) ^ (y * 19349663))
        for indice in range(cfg.ENEMIGOS_POR_SECTOR):
            posicion = Vector2(
                (x + azar.uniform(0.08, 0.92)) * cfg.TAMANIO_SECTOR,
                (y + azar.uniform(0.08, 0.92)) * cfg.TAMANIO_SECTOR,
            )
            if en_base(posicion, 100):
                continue
            identificador = f'{x}:{y}:{indice}'
            self.enemigos[identificador] = Enemigo(identificador, posicion, posicion)

    def _enemigos_cercanos(self, posicion: Vector2) -> list[Enemigo]:
        cercanos = [enemigo for enemigo in self.enemigos.values()
                    if enemigo.vivo and enemigo.pos.distance_squared_to(posicion)
                    <= cfg.RADIO_ACTIVACION ** 2]
        return sorted(cercanos, key=lambda enemigo: enemigo.pos.distance_squared_to(posicion))

    def _destino_enemigo(self, enemigo: Enemigo, posicion: Vector2) -> Vector2:
        distancia = enemigo.pos.distance_to(posicion)
        if distancia > cfg.RADIO_DETECCION_ENEMIGO or en_base(posicion):
            return enemigo.origen
        if distancia <= cfg.ALCANCE_ENEMIGO * 0.65:
            return enemigo.pos
        return posicion

    def _excluir_de_base(self, enemigo: Enemigo) -> None:
        if en_base(enemigo.pos, enemigo.radio):
            direccion = enemigo.pos - Vector2(cfg.POSICION_BASE)
            if direccion.length_squared() == 0:
                direccion = Vector2(1, 0)
            enemigo.pos = Vector2(cfg.POSICION_BASE) + direccion.normalize() * (
                cfg.RADIO_BASE + enemigo.radio + 1
            )
        enemigo.pos.x = clamp(enemigo.pos.x, enemigo.radio, cfg.ANCHO_MUNDO - enemigo.radio)
        enemigo.pos.y = clamp(enemigo.pos.y, enemigo.radio, cfg.ALTO_MUNDO - enemigo.radio)
