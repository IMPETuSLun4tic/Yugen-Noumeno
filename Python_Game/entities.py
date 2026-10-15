import math
import random
from dataclasses import dataclass, field

import pygame
from pygame.math import Vector2

import config as cfg
from config import ANCHO, ALTO
from utils import clamp


class Particle:
    def __init__(self, pos, vel, color, size, lifetime):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.age = 0.0
        self.vivo = True

    def actualizar(self, dt):
        self.age += dt
        if self.age >= self.lifetime:
            self.vivo = False
            return
        self.pos += self.vel * dt
        self.vel *= (1 - dt * 1.2)

    def dibujar(self, pantalla, offset=(0,0)):
        alpha = int(255 * (1 - (self.age / self.lifetime)))
        surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.size, self.size), int(self.size))
        pantalla.blit(surf, (self.pos.x - self.size + offset[0], self.pos.y - self.size + offset[1]))

class Star:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.random() * ANCHO
        self.y = random.random() * ALTO
        self.z = random.uniform(0.2, 1.0)
        self.size = clamp(int(3 * (1 - self.z)), 1, 3)
        self.speed = 20 + (1 - self.z) * 80

    def actualizar(self, dt, parallax_vel=Vector2(0, 0)):
        self.x -= self.speed * dt * (1 - self.z) * 0.3
        parallax_factor = (1 - self.z) * 0.5
        self.x -= parallax_vel.x * parallax_factor * dt
        self.y -= parallax_vel.y * parallax_factor * dt

        if self.x < -10:
            self.x = ANCHO + 10
            self.y = random.random() * ALTO
        elif self.x > ANCHO + 10:
            self.x = -10
            self.y = random.random() * ALTO
        if self.y < -10:
            self.y = ALTO + 10
        elif self.y > ALTO + 10:
            self.y = -10

    def dibujar(self, pantalla):
        col = int(200 + (1 - self.z) * 55)
        pygame.draw.rect(pantalla, (col, col, col), (int(self.x), int(self.y), self.size, self.size))

class Nebula:
    def __init__(self, img=None):
        self.x = random.random() * ANCHO
        self.y = random.random() * ALTO
        self.z = random.uniform(0.6, 0.9)
        self.size = int(420 * (1 - self.z))
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-5, 5)
        self.color = random.choice([(40,20,60),(20,40,60),(60,20,40)])
        self.img = img

    def actualizar(self, dt, parallax_vel):
        parallax_factor = (1 - self.z) * 0.2
        self.x -= parallax_vel.x * parallax_factor * dt
        self.y -= parallax_vel.y * parallax_factor * dt
        self.rotation += self.rotation_speed * dt

        if self.x < -self.size:
            self.x = ANCHO + self.size
        elif self.x > ANCHO + self.size:
            self.x = -self.size
        if self.y < -self.size:
            self.y = ALTO + self.size
        elif self.y > ALTO + self.size:
            self.y = -self.size

    def dibujar(self, pantalla):
        if self.img:
            scaled = pygame.transform.scale(self.img, (self.size * 2, self.size * 2))
            rotated = pygame.transform.rotate(scaled, self.rotation)
            alpha = int(180 * (1 - self.z))
            rotated.set_alpha(alpha)
            rect = rotated.get_rect(center=(int(self.x), int(self.y)))
            pantalla.blit(rotated, rect)
        else:
            surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, 30), (self.size, self.size), self.size)
            pantalla.blit(surf, (int(self.x - self.size), int(self.y - self.size)))

class Fog:
    def __init__(self):
        self.x = random.random() * ANCHO
        self.y = random.random() * ALTO
        self.z = random.uniform(0.3, 0.7)
        self.size = int(200 * (1 - self.z))
        self.speed = 10 + (1 - self.z) * 30
        self.offset_x = random.uniform(-100, 100)
        self.offset_y = random.uniform(-100, 100)
        colores_base = [
            (180, 220, 200),
            (200, 180, 220),
            (220, 220, 180),
            (200, 210, 220)
        ]
        self.color_base = random.choice(colores_base)

    def actualizar(self, dt, parallax_vel):
        self.x -= self.speed * dt * (1 - self.z) * 0.15
        parallax_factor = (1 - self.z) * 0.3
        self.x -= parallax_vel.x * parallax_factor * dt
        self.y -= parallax_vel.y * parallax_factor * dt

        if self.x < -self.size:
            self.x = ANCHO + self.size
            self.y = random.random() * ALTO
        elif self.x > ANCHO + self.size:
            self.x = -self.size
            self.y = random.random() * ALTO
        if self.y < -self.size:
            self.y = ALTO + self.size
        elif self.y > ALTO + self.size:
            self.y = -self.size

    def dibujar(self, pantalla):
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        alpha_base = int(10 * (1 - self.z))
        for i in range(5, 0, -1):
            radius = int(self.size * (i / 5))
            alpha = int(alpha_base * (i / 5))
            color = (*self.color_base, alpha)
            pygame.draw.circle(surf, color, (self.size, self.size), radius)
        pantalla.blit(surf, (int(self.x - self.size), int(self.y - self.size)))

@dataclass(frozen=True)
class ResultadoDanio:
    vida: float
    escudo: float


@dataclass
class Nave:
    pos: Vector2
    destino: Vector2 | None = None
    vel: Vector2 = field(default_factory=Vector2)
    angulo: float = 0.0
    radio: float = 18.0
    vida: float = cfg.VIDA_NAVE
    escudo: float = cfg.ESCUDO_NAVE
    vida_maxima: float = cfg.VIDA_NAVE
    escudo_maximo: float = cfg.ESCUDO_NAVE
    tiempo_sin_combate: float = 0.0
    tiempo_impacto: float = 0.0
    arma: int = 0
    disparo_activo: bool = False
    tiempo_laser: float = 0.0
    tiempo_misil: float = 0.0
    tiempo_haz: float = 0.0
    enfriamiento_haz: float = 0.0
    hubo_combate: bool = False

    def __post_init__(self) -> None:
        self.pos = Vector2(self.pos)
        self.destino = Vector2(self.pos if self.destino is None else self.destino)

    @property
    def viva(self) -> bool:
        return self.vida > 0

    def mover_a(self, posicion: Vector2) -> None:
        self.destino = Vector2(
            clamp(posicion.x, self.radio, cfg.ANCHO_MUNDO - self.radio),
            clamp(posicion.y, self.radio, cfg.ALTO_MUNDO - self.radio),
        )

    def actualizar(self, dt: float, objetivo: Vector2 | None = None) -> None:
        if not self.viva:
            self.vel.update(0, 0)
            return
        self._mover(dt)
        self._orientar(objetivo if objetivo is not None else self.destino, dt)
        self.tiempo_laser = max(0.0, self.tiempo_laser - dt)
        self.tiempo_misil = max(0.0, self.tiempo_misil - dt)
        self.enfriamiento_haz = max(0.0, self.enfriamiento_haz - dt)
        self.tiempo_impacto = max(0.0, self.tiempo_impacto - dt)

    def regenerar(self, dt: float) -> None:
        if not self.viva:
            return
        self.tiempo_sin_combate += dt
        intervalo = min(dt, max(0.0, self.tiempo_sin_combate - cfg.ESPERA_REGENERACION_SEGUNDOS))
        self.vida = min(self.vida_maxima, self.vida + intervalo * cfg.REGENERACION_VIDA_POR_SEGUNDO)
        self.escudo = min(self.escudo_maximo, self.escudo + intervalo * cfg.REGENERACION_ESCUDO_POR_SEGUNDO)

    def _mover(self, dt: float) -> None:
        direccion = self.destino - self.pos
        distancia = direccion.length()
        if distancia < 0.01 or dt <= 0:
            self.vel.update(0, 0)
            return
        paso = min(distancia, cfg.VEL_NAVE * dt)
        self.vel = direccion * (paso / distancia / dt)
        self.pos += direccion * (paso / distancia)

    def _orientar(self, objetivo: Vector2, dt: float) -> None:
        direccion = objetivo - self.pos
        if direccion.length_squared() == 0:
            return
        deseado = math.degrees(math.atan2(-direccion.y, direccion.x))
        diferencia = (deseado - self.angulo + 180) % 360 - 180
        self.angulo += diferencia * (1 - math.exp(-18 * dt))

    def recibir_danio(self, cantidad: float) -> ResultadoDanio:
        if not math.isfinite(cantidad) or cantidad < 0:
            raise ValueError('El danio debe ser finito y no negativo')
        if not self.viva:
            return ResultadoDanio(0.0, 0.0)
        absorbido = min(self.escudo, cantidad * cfg.PROPORCION_ESCUDO)
        perdido = min(self.vida, cantidad - absorbido)
        self.escudo -= absorbido
        self.vida -= perdido
        self.tiempo_sin_combate = 0.0
        self.hubo_combate = True
        self.tiempo_impacto = 0.3 if absorbido else 0.0
        if not self.viva:
            self.detener_disparo()
        return ResultadoDanio(perdido, absorbido)

    def seleccionar_arma(self, ranura: int) -> None:
        if ranura not in (1, 2, 3):
            raise ValueError('La ranura debe ser 1, 2 o 3')
        if self.arma == ranura:
            self.disparo_activo = not self.disparo_activo
            if not self.disparo_activo:
                self.detener_disparo()
            return
        self.detener_disparo()
        self.arma = ranura

    def detener_disparo(self) -> None:
        self.disparo_activo = False
        self.interrumpir_haz()

    def interrumpir_haz(self) -> None:
        if self.tiempo_haz > 0:
            self.enfriamiento_haz = cfg.ENFRIAMIENTO_HAZ_SEGUNDOS
            self.tiempo_haz = 0.0


@dataclass
class Enemigo:
    identificador: str
    pos: Vector2
    origen: Vector2
    vida: float = cfg.VIDA_ENEMIGO
    tiempo_disparo: float = 0.0
    radio: float = 18.0

    def __post_init__(self) -> None:
        self.pos = Vector2(self.pos)
        self.origen = Vector2(self.origen)

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    def actualizar(self, dt: float, destino: Vector2) -> None:
        self.tiempo_disparo = max(0.0, self.tiempo_disparo - dt)
        direccion = destino - self.pos
        distancia = direccion.length()
        if distancia > 2:
            self.pos += direccion * (min(cfg.VELOCIDAD_ENEMIGO * dt, distancia) / distancia)

    def recibir_danio(self, cantidad: float) -> float:
        perdido = min(self.vida, max(0.0, cantidad))
        self.vida -= perdido
        return perdido


@dataclass
class Proyectil:
    pos: Vector2
    vel: Vector2
    danio: float
    tipo: str
    distancia_restante: float
    anterior: Vector2 = field(init=False)
    vivo: bool = True

    def __post_init__(self) -> None:
        self.pos = Vector2(self.pos)
        self.vel = Vector2(self.vel)
        self.anterior = self.pos.copy()

    def actualizar(self, dt: float) -> None:
        self.anterior = self.pos.copy()
        distancia = min(self.vel.length() * dt, self.distancia_restante)
        if self.vel.length_squared() > 0:
            self.pos += self.vel.normalize() * distancia
        self.distancia_restante = max(0.0, self.distancia_restante - distancia)


@dataclass
class MarcadorDanio:
    pos: Vector2
    texto: str
    color: tuple[int, int, int]
    tiempo: float = 0.9
    desplazamiento_pantalla: float = 0.0

    def actualizar(self, dt: float) -> None:
        self.tiempo -= dt
        self.desplazamiento_pantalla -= 35 * dt
