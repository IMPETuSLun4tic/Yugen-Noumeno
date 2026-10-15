import math
import random
from dataclasses import dataclass, field

import pygame
from pygame.math import Vector2

import config as cfg
from mundo import Camara, elipse_proyectada, proyectar_vector


@dataclass(frozen=True)
class PerfilParticulas:
    color: tuple[int, int, int]
    cantidad: int
    velocidad: float
    radio: float
    duracion: float
    fragmentos: bool = False


PERFIL_ESCUDO = PerfilParticulas((95, 205, 255), 10, 105, 2, 0.45)
PERFIL_CASCO = PerfilParticulas((255, 195, 100), 12, 145, 2, 0.55)
PERFIL_HAZ = PerfilParticulas((100, 225, 255), 3, 75, 1.5, 0.3)
PERFIL_MISIL = PerfilParticulas((255, 160, 70), 24, 180, 3, 0.8, True)
PERFIL_DESTRUCCION = PerfilParticulas((255, 175, 80), 40, 230, 3.5, 1.2, True)


@dataclass
class ParticulaImpacto:
    pos: Vector2
    vel: Vector2
    color: tuple[int, int, int]
    radio: float
    duracion: float
    velocidad_altura: float
    fragmento: bool = False
    altura: float = 0.0
    edad: float = 0.0

    def actualizar(self, dt: float) -> None:
        self.edad += dt
        self.pos += self.vel * dt
        self.vel *= math.exp(-2.8 * dt)
        self.altura = max(0.0, self.altura + self.velocidad_altura * dt)
        self.velocidad_altura -= 160 * dt


@dataclass
class PulsoImpacto:
    pos: Vector2
    color: tuple[int, int, int]
    radio: float
    duracion: float
    tipo: str = 'onda'
    direccion: Vector2 = field(default_factory=lambda: Vector2(1, 0))
    anclado_nave: bool = False
    edad: float = 0.0


@dataclass
class SistemaEfectos:
    particulas: list[ParticulaImpacto] = field(default_factory=list)
    pulsos: list[PulsoImpacto] = field(default_factory=list)
    espera_haz: float = 0.0
    _azar: random.Random = field(default_factory=random.Random, repr=False)
    _capa: pygame.Surface | None = field(default=None, init=False, repr=False)

    def actualizar(self, dt: float) -> None:
        self.espera_haz = max(0.0, self.espera_haz - dt)
        for particula in self.particulas:
            particula.actualizar(dt)
        for pulso in self.pulsos:
            pulso.edad += dt
        self.particulas = [particula for particula in self.particulas if particula.edad < particula.duracion]
        self.pulsos = [pulso for pulso in self.pulsos if pulso.edad < pulso.duracion]

    def impacto_escudo(self, posicion: Vector2, centro_nave: Vector2) -> None:
        normal = posicion - centro_nave
        normal = normal.normalize() if normal.length_squared() else Vector2(1, 0)
        self._agregar_pulso(PulsoImpacto(Vector2(), (125, 225, 255), 32, 0.35,
                                       'escudo', normal, True))
        self._agregar_pulso(PulsoImpacto(Vector2(posicion), (160, 235, 255), 15, 0.18, 'destello'))
        self._emitir(posicion, normal, PERFIL_ESCUDO)

    def impacto_casco(self, posicion: Vector2, direccion: Vector2) -> None:
        self._agregar_pulso(PulsoImpacto(Vector2(posicion), (255, 220, 150), 16, 0.16, 'destello'))
        self._emitir(posicion, -direccion, PERFIL_CASCO)

    def impacto_haz(self, posicion: Vector2, direccion: Vector2) -> None:
        if self.espera_haz > 0:
            return
        self.espera_haz = cfg.INTERVALO_EFECTO_HAZ_SEGUNDOS
        self._agregar_pulso(PulsoImpacto(Vector2(posicion), (140, 235, 255), 11, 0.12, 'destello'))
        self._emitir(posicion, -direccion, PERFIL_HAZ)

    def explosion_misil(self, posicion: Vector2) -> None:
        self._explosion(posicion, cfg.RADIO_EXPLOSION, PERFIL_MISIL)

    def destruccion(self, posicion: Vector2) -> None:
        self._explosion(posicion, 115, PERFIL_DESTRUCCION)

    def _explosion(self, posicion: Vector2, radio: float, perfil: PerfilParticulas) -> None:
        self._agregar_pulso(PulsoImpacto(Vector2(posicion), (255, 175, 75), radio, 0.65))
        self._agregar_pulso(PulsoImpacto(Vector2(posicion), (255, 110, 45), radio * 0.72, 0.45))
        self._agregar_pulso(PulsoImpacto(Vector2(posicion), (255, 235, 175), radio * 0.45, 0.28, 'destello'))
        self._emitir(posicion, Vector2(), perfil)

    def _agregar_pulso(self, pulso: PulsoImpacto) -> None:
        if len(self.pulsos) >= cfg.MAX_PULSOS_IMPACTO:
            self.pulsos.pop(0)
        self.pulsos.append(pulso)

    def _emitir(self, posicion: Vector2, direccion: Vector2, perfil: PerfilParticulas) -> None:
        cantidad = min(perfil.cantidad, cfg.MAX_PARTICULAS_IMPACTO - len(self.particulas))
        for _ in range(cantidad):
            velocidad = Vector2(1, 0).rotate(self._azar.uniform(0, 360))
            velocidad = velocidad * perfil.velocidad * self._azar.uniform(0.3, 1.0)
            if direccion.length_squared():
                velocidad += direccion.normalize() * perfil.velocidad * 0.4
            self.particulas.append(ParticulaImpacto(
                Vector2(posicion), velocidad, perfil.color,
                perfil.radio * self._azar.uniform(0.6, 1.3),
                perfil.duracion * self._azar.uniform(0.6, 1.0),
                self._azar.uniform(15, 60), perfil.fragmentos,
            ))

    def dibujar(self, superficie: pygame.Surface, camara: Camara, posicion_nave: Vector2) -> None:
        if not self.particulas and not self.pulsos:
            return
        if self._capa is None or self._capa.get_size() != superficie.get_size():
            self._capa = pygame.Surface(superficie.get_size(), pygame.SRCALPHA)
        self._capa.fill((0, 0, 0, 0))
        for pulso in self.pulsos:
            self._dibujar_pulso(pulso, camara, posicion_nave)
        for particula in self.particulas:
            self._dibujar_particula(particula, camara)
        superficie.blit(self._capa, (0, 0))

    def _dibujar_pulso(self, pulso: PulsoImpacto, camara: Camara, posicion_nave: Vector2) -> None:
        posicion = posicion_nave if pulso.anclado_nave else pulso.pos
        centro = camara.a_pantalla(posicion)
        progreso = min(1.0, pulso.edad / pulso.duracion)
        alpha = round(230 * (1 - progreso))
        if pulso.tipo == 'destello':
            self._dibujar_destello(centro, pulso, progreso, alpha)
        elif pulso.tipo == 'escudo':
            self._dibujar_arco_escudo(centro, pulso, progreso, alpha)
        else:
            radio = max(1, pulso.radio * (0.15 + progreso * 0.85))
            rectangulo = elipse_proyectada(centro, radio)
            pygame.draw.ellipse(self._capa, (*pulso.color, alpha), rectangulo, max(1, round(4 * (1 - progreso))))

    def _dibujar_destello(self, centro: Vector2, pulso: PulsoImpacto, progreso: float, alpha: int) -> None:
        radio = max(1, round(pulso.radio * (0.5 + progreso * 0.5)))
        pygame.draw.circle(self._capa, (*pulso.color, alpha // 4), centro, radio)
        pygame.draw.circle(self._capa, (*pulso.color, alpha // 2), centro, max(1, radio // 2))
        pygame.draw.circle(self._capa, (255, 250, 235, alpha), centro, max(1, round(radio * 0.25)))
        amplitud = Vector2(radio * (1 - progreso), 0)
        pygame.draw.line(self._capa, (*pulso.color, alpha), centro - amplitud, centro + amplitud, 1)

    def _dibujar_arco_escudo(self, centro: Vector2, pulso: PulsoImpacto, progreso: float, alpha: int) -> None:
        direccion = proyectar_vector(pulso.direccion)
        angulo = math.atan2(-direccion.y / cfg.COMPRESION_ISOMETRICA, direccion.x)
        rectangulo = elipse_proyectada(centro, pulso.radio + progreso * 6)
        apertura = 0.35 + progreso * 0.8
        pygame.draw.arc(self._capa, (*pulso.color, alpha), rectangulo,
                        angulo - apertura, angulo + apertura, 3)
        punto = centro + proyectar_vector(pulso.direccion * pulso.radio)
        pygame.draw.ellipse(self._capa, (*pulso.color, alpha), elipse_proyectada(punto, 2 + progreso * 15), 1)

    def _dibujar_particula(self, particula: ParticulaImpacto, camara: Camara) -> None:
        centro = camara.a_pantalla(particula.pos) - Vector2(0, particula.altura)
        if not self._capa.get_rect().inflate(30, 30).collidepoint(centro):
            return
        restante = max(0.0, 1 - particula.edad / particula.duracion)
        color = (*particula.color, round(255 * restante))
        radio = max(1, round(particula.radio * restante))
        if particula.fragmento:
            puntos = [centro + Vector2(-radio, 0), centro + Vector2(0, -radio),
                      centro + Vector2(radio, 0), centro + Vector2(0, radio)]
            pygame.draw.polygon(self._capa, color, puntos)
        else:
            cola = proyectar_vector(particula.vel * 0.025)
            pygame.draw.line(self._capa, color, centro - cola, centro, radio)
            pygame.draw.circle(self._capa, (255, 245, 220, color[3]), centro, 1)
