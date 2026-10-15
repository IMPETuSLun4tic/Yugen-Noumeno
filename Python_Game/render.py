import math

import pygame
from pygame.math import Vector2

import config as cfg
from entities import Enemigo, Nave, Proyectil
from mundo import elipse_proyectada, proyectar_vector
from partida import Partida


def dibujar_escena(superficie: pygame.Surface, partida: Partida, fondo: dict, recursos: dict) -> None:
    superficie.fill(cfg.COLOR_FONDO_BASE)
    for grupo in ('nebulas', 'stars', 'fogs'):
        for elemento in fondo[grupo]:
            elemento.dibujar(superficie)
    _dibujar_mapa(superficie, partida)
    _dibujar_destino(superficie, partida)
    entidades = [enemigo for enemigo in partida.mundo.activos if enemigo.vivo]
    if partida.nave.viva:
        entidades.append(partida.nave)
    for entidad in sorted(entidades, key=lambda entidad: proyectar_vector(entidad.pos).y):
        if isinstance(entidad, Nave):
            _dibujar_nave(superficie, partida, recursos.get('jugador'))
        else:
            _dibujar_enemigo(superficie, partida, entidad, recursos.get('enemigo'))
    for proyectil in partida.proyectiles:
        _dibujar_proyectil(superficie, partida, proyectil)
    if partida.haz_visible and partida.objetivo is not None:
        _dibujar_haz(superficie, partida)
    partida.efectos.dibujar(superficie, partida.camara, partida.nave.pos)


def dibujar_marcadores(superficie: pygame.Surface, partida: Partida, fuente: pygame.font.Font) -> None:
    for marcador in partida.marcadores:
        posicion = partida.camara.a_pantalla(marcador.pos)
        posicion.y += marcador.desplazamiento_pantalla
        texto = fuente.render(marcador.texto, True, marcador.color)
        texto.set_alpha(int(255 * min(1.0, marcador.tiempo / 0.3)))
        superficie.blit(texto, texto.get_rect(center=posicion))


def _dibujar_mapa(superficie: pygame.Surface, partida: Partida) -> None:
    camara = partida.camara
    esquinas = (Vector2(0, 0), Vector2(cfg.ANCHO_MUNDO, 0),
                Vector2(cfg.ANCHO_MUNDO, cfg.ALTO_MUNDO), Vector2(0, cfg.ALTO_MUNDO))
    pygame.draw.polygon(superficie, (32, 60, 85), [camara.a_pantalla(punto) for punto in esquinas], 3)
    for x in range(0, cfg.ANCHO_MUNDO + 1, cfg.TAMANIO_SECTOR):
        a, b = camara.a_pantalla(Vector2(x, 0)), camara.a_pantalla(Vector2(x, cfg.ALTO_MUNDO))
        pygame.draw.line(superficie, (15, 29, 44), a, b)
    for y in range(0, cfg.ALTO_MUNDO + 1, cfg.TAMANIO_SECTOR):
        a, b = camara.a_pantalla(Vector2(0, y)), camara.a_pantalla(Vector2(cfg.ANCHO_MUNDO, y))
        pygame.draw.line(superficie, (15, 29, 44), a, b)
    centro = camara.a_pantalla(Vector2(cfg.POSICION_BASE))
    if superficie.get_rect().colliderect(elipse_proyectada(centro, cfg.RADIO_BASE)):
        _dibujar_base(superficie, centro)


def _dibujar_base(superficie: pygame.Surface, centro: Vector2) -> None:
    radio = cfg.RADIO_BASE
    tamanio = (radio * 2 + 4, round(radio * 2 * cfg.COMPRESION_ISOMETRICA) + 4)
    capa = pygame.Surface(tamanio, pygame.SRCALPHA)
    centro_local = Vector2(tamanio) / 2
    pygame.draw.ellipse(capa, (30, 180, 160, 14), elipse_proyectada(centro_local, radio))
    pygame.draw.ellipse(capa, (55, 200, 190, 110), elipse_proyectada(centro_local, radio), 2)
    superficie.blit(capa, centro - centro_local)
    _dibujar_plataforma(superficie, centro)
    _dibujar_luces_base(superficie, centro)


def _dibujar_plataforma(superficie: pygame.Surface, centro: Vector2) -> None:
    pygame.draw.ellipse(superficie, (4, 11, 21), elipse_proyectada(centro + Vector2(6, 30), 112))
    inferior = centro + Vector2(0, 20)
    pygame.draw.ellipse(superficie, (10, 30, 45), elipse_proyectada(inferior, 90))
    pygame.draw.rect(superficie, (10, 30, 45), (centro.x - 90, centro.y, 180, 20))
    pygame.draw.ellipse(superficie, (35, 125, 150), elipse_proyectada(inferior, 90), 2)
    pygame.draw.ellipse(superficie, (22, 50, 68), elipse_proyectada(centro, 90))
    pygame.draw.ellipse(superficie, (95, 215, 225), elipse_proyectada(centro, 90), 2)
    pygame.draw.ellipse(superficie, (45, 110, 140), elipse_proyectada(centro, 70), 2)
    pygame.draw.ellipse(superficie, (115, 205, 215), elipse_proyectada(centro, 36), 1)
    for desplazamiento in (-55, 55):
        pygame.draw.line(superficie, (25, 80, 100), centro + Vector2(desplazamiento, -27),
                         centro + Vector2(desplazamiento, 27), 2)


def _dibujar_luces_base(superficie: pygame.Surface, centro: Vector2) -> None:
    for angulo in range(0, 360, 90):
        direccion = proyectar_vector(Vector2(1, 0).rotate(angulo))
        inicio, fin = centro + direccion * 70, centro + direccion * 110
        pygame.draw.line(superficie, (6, 20, 32), inicio + Vector2(0, 7), fin + Vector2(0, 7), 9)
        pygame.draw.line(superficie, (45, 110, 130), inicio, fin, 7)
        pygame.draw.line(superficie, (145, 235, 230), inicio, fin, 2)
        pygame.draw.ellipse(superficie, (110, 220, 225), elipse_proyectada(fin, 8))
    for x in (-70, -35, 0, 35, 70):
        pygame.draw.circle(superficie, (90, 200, 230), centro + Vector2(x, 35), 2)


def _dibujar_destino(superficie: pygame.Surface, partida: Partida) -> None:
    if partida.nave.pos.distance_to(partida.nave.destino) < 3:
        return
    posicion = partida.camara.a_pantalla(partida.nave.destino)
    pygame.draw.ellipse(superficie, (75, 140, 175), elipse_proyectada(posicion, 12), 1)
    for vector in (Vector2(1, 0), Vector2(0, 1)):
        direccion = proyectar_vector(vector) * 18
        pygame.draw.line(superficie, (75, 140, 175), posicion - direccion, posicion + direccion, 1)


def _dibujar_enemigo(superficie: pygame.Surface, partida: Partida, enemigo: Enemigo, imagen: pygame.Surface | None) -> None:
    posicion = partida.camara.a_pantalla(enemigo.pos)
    if not superficie.get_rect().inflate(120, 120).collidepoint(posicion):
        return
    direccion = partida.nave.pos - enemigo.pos
    angulo = math.degrees(math.atan2(-direccion.y, direccion.x))
    _dibujar_sombra(superficie, posicion)
    if imagen is not None:
        _dibujar_sprite(superficie, imagen, posicion, angulo + 180)
    else:
        _dibujar_casco(superficie, posicion, angulo, cfg.COLOR_ENEMIGO)
    if enemigo is partida.objetivo:
        pygame.draw.ellipse(superficie, (255, 185, 80), elipse_proyectada(posicion, 30), 2)
    barra = pygame.Rect(posicion.x - 23, posicion.y - 27, 46, 4)
    pygame.draw.rect(superficie, (38, 47, 58), barra)
    pygame.draw.rect(superficie, (130, 225, 160), (*barra.topleft, barra.width * enemigo.vida / cfg.VIDA_ENEMIGO, 4))


def _dibujar_nave(superficie: pygame.Surface, partida: Partida, imagen: pygame.Surface | None) -> None:
    nave = partida.nave
    centro = partida.camara.a_pantalla(nave.pos)
    direccion = proyectar_vector(Vector2(math.cos(math.radians(nave.angulo)), -math.sin(math.radians(nave.angulo))))
    _dibujar_sombra(superficie, centro)
    if nave.vel.length_squared() > 1:
        escape = centro - direccion * 24
        pygame.draw.circle(superficie, (40, 110, 185), escape, 6)
        pygame.draw.circle(superficie, (170, 235, 255), escape, 3)
    if nave.escudo > 0:
        _dibujar_escudo(superficie, nave, centro)
    if imagen is not None:
        _dibujar_sprite(superficie, imagen, centro, nave.angulo)
    else:
        _dibujar_casco(superficie, centro, nave.angulo, cfg.COLOR_NAVE)


def proyectar_sprite(imagen: pygame.Surface, angulo: float) -> pygame.Surface:
    rotada = pygame.transform.rotate(imagen, angulo - 45)
    ancho = max(1, round(rotada.get_width() * cfg.ESCALA_SPRITE_ISOMETRICO))
    alto = max(1, round(rotada.get_height() * cfg.ESCALA_SPRITE_ISOMETRICO * cfg.COMPRESION_ISOMETRICA))
    return pygame.transform.smoothscale(rotada, (ancho, alto))


def _dibujar_sprite(superficie: pygame.Surface, imagen: pygame.Surface, centro: Vector2, angulo: float) -> None:
    rotada = proyectar_sprite(imagen, angulo)
    lateral = rotada.copy()
    lateral.fill((65, 95, 120, 210), special_flags=pygame.BLEND_RGBA_MULT)
    superficie.blit(lateral, lateral.get_rect(center=centro + Vector2(0, 3)))
    superficie.blit(rotada, rotada.get_rect(center=centro))


def _dibujar_casco(superficie: pygame.Surface, centro: Vector2, angulo: float, color: tuple) -> None:
    direccion = Vector2(math.cos(math.radians(angulo)), -math.sin(math.radians(angulo)))
    lateral = direccion.rotate(90)
    vectores = (direccion * 21, -direccion * 15 + lateral * 14,
                -direccion * 10, -direccion * 15 - lateral * 14)
    puntos = [centro + proyectar_vector(vector) for vector in vectores]
    pygame.draw.polygon(superficie, (20, 45, 65), [punto + Vector2(0, 4) for punto in puntos])
    pygame.draw.polygon(superficie, color, puntos)
    pygame.draw.lines(superficie, (195, 235, 245), False, puntos[:3], 1)


def _dibujar_sombra(superficie: pygame.Surface, centro: Vector2) -> None:
    capa = pygame.Surface((64, 30), pygame.SRCALPHA)
    pygame.draw.ellipse(capa, (0, 3, 10, 95), (6, 9, 50, 15))
    pygame.draw.ellipse(capa, (0, 3, 10, 65), (13, 12, 36, 9))
    superficie.blit(capa, centro - Vector2(28, 3))


def _dibujar_escudo(superficie: pygame.Surface, nave: Nave, centro: Vector2) -> None:
    capa = pygame.Surface((80, 44), pygame.SRCALPHA)
    centro_local = Vector2(40, 22)
    alpha = round(35 + 40 * nave.escudo / nave.escudo_maximo)
    pygame.draw.ellipse(capa, (70, 175, 255, 15), elipse_proyectada(centro_local, 32))
    pygame.draw.ellipse(capa, (95, 205, 255, alpha), elipse_proyectada(centro_local, 32), 2)
    pygame.draw.arc(capa, (160, 230, 255, alpha), elipse_proyectada(centro_local, 30), 0.4, 2.7, 1)
    superficie.blit(capa, centro - centro_local)


def _dibujar_proyectil(superficie: pygame.Surface, partida: Partida, proyectil: Proyectil) -> None:
    posicion = partida.camara.a_pantalla(proyectil.pos)
    if not superficie.get_rect().inflate(50, 50).collidepoint(posicion):
        return
    color = {'laser': cfg.COLOR_LASER, 'misil': cfg.COLOR_MISIL, 'enemigo': (255, 105, 105)}[proyectil.tipo]
    direccion = proyectar_vector(proyectil.vel.normalize()) if proyectil.vel.length_squared() else Vector2(1, 0)
    pygame.draw.line(superficie, color, posicion - direccion * 18, posicion, 4)
    pygame.draw.line(superficie, (255, 250, 235), posicion - direccion * 12, posicion, 1)


def _dibujar_haz(superficie: pygame.Surface, partida: Partida) -> None:
    objetivo = partida.objetivo
    direccion = objetivo.pos - partida.nave.pos
    direccion = direccion.normalize() if direccion.length_squared() else Vector2(1, 0)
    inicio = partida.camara.a_pantalla(partida.nave.pos + direccion * 22)
    fin = partida.camara.a_pantalla(objetivo.pos - direccion * objetivo.radio)
    pygame.draw.line(superficie, (25, 90, 155), inicio, fin, 8)
    pygame.draw.line(superficie, cfg.COLOR_BEAM, inicio, fin, 4)
    pygame.draw.line(superficie, (235, 250, 255), inicio, fin, 1)
