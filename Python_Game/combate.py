from typing import TYPE_CHECKING

from pygame.math import Vector2

import config as cfg
from entities import Enemigo, MarcadorDanio, Proyectil, ResultadoDanio
from mundo import en_base

if TYPE_CHECKING:
    from partida import Partida


def fraccion_impacto(inicio: Vector2, fin: Vector2, centro: Vector2, radio: float) -> float | None:
    direccion = fin - inicio
    relativo = inicio - centro
    if relativo.length_squared() <= radio * radio:
        return 0.0
    longitud = direccion.length_squared()
    if longitud == 0:
        return None
    producto = relativo.dot(direccion)
    discriminante = producto * producto - longitud * (relativo.length_squared() - radio * radio)
    if discriminante < 0:
        return None
    fraccion = (-producto - discriminante ** 0.5) / longitud
    return fraccion if 0 <= fraccion <= 1 else None


def actualizar_combate(partida: 'Partida', dt: float) -> None:
    partida.haz_visible = False
    partida.preparar_base()
    if not en_base(partida.nave.pos):
        _disparar_jugador(partida, dt)
        _disparar_enemigos(partida)
        _actualizar_proyectiles(partida, dt)
    partida.proyectiles = [proyectil for proyectil in partida.proyectiles
                          if proyectil.vivo and proyectil.distancia_restante > 0]
    if partida.objetivo is None:
        partida.objetivo_id = None
        partida.nave.detener_disparo()


def _disparar_jugador(partida: 'Partida', dt: float) -> None:
    nave, objetivo = partida.nave, partida.objetivo
    if not nave.disparo_activo or objetivo is None:
        return
    alcance = {1: cfg.ALCANCE_LASER, 2: cfg.ALCANCE_MISIL, 3: cfg.ALCANCE_BEAM}[nave.arma]
    if en_base(objetivo.pos) or nave.pos.distance_to(objetivo.pos) > alcance:
        nave.interrumpir_haz()
        return
    if nave.arma == 3:
        _disparar_haz(partida, dt)
    elif nave.arma == 1 and nave.tiempo_laser <= 0:
        danio = cfg.DANIO_LASER + partida.mejoras.laser * cfg.DANIO_POR_MEJORA_LASER
        _crear_proyectil(partida, objetivo.pos, danio, 'laser')
        nave.tiempo_laser = cfg.COOLDOWN_LASER
    elif nave.arma == 2 and nave.tiempo_misil <= 0:
        _crear_proyectil(partida, objetivo.pos, cfg.DANIO_MISIL, 'misil')
        nave.tiempo_misil = cfg.CADENCIA_MISIL


def _registrar_ataque(partida: 'Partida', sonido: str) -> None:
    partida.nave.tiempo_sin_combate = 0.0
    partida.nave.hubo_combate = True
    partida.eventos_audio.append(sonido)


def _crear_proyectil(partida: 'Partida', destino: Vector2, danio: float, tipo: str) -> None:
    direccion = destino - partida.nave.pos
    if direccion.length_squared() == 0:
        direccion = Vector2(1, 0)
    velocidad = cfg.VELOCIDAD_MISIL if tipo == 'misil' else 800
    alcance = cfg.ALCANCE_MISIL if tipo == 'misil' else cfg.ALCANCE_LASER
    posicion = partida.nave.pos + direccion.normalize() * 24
    partida.proyectiles.append(Proyectil(posicion, direccion.normalize() * velocidad, danio, tipo, alcance))
    _registrar_ataque(partida, 's_missile' if tipo == 'misil' else 's_shot')


def _disparar_haz(partida: 'Partida', dt: float) -> None:
    nave = partida.nave
    if nave.enfriamiento_haz > 0:
        return
    if nave.tiempo_haz <= 0:
        nave.tiempo_haz = cfg.DURACION_HAZ_SEGUNDOS
        _registrar_ataque(partida, 's_beam')
    intervalo = min(dt, nave.tiempo_haz)
    nave.tiempo_haz = max(0.0, nave.tiempo_haz - intervalo)
    nave.tiempo_sin_combate = 0.0
    nave.hubo_combate = True
    partida.haz_visible = True
    _mostrar_impacto_haz(partida)
    _danio_enemigo(partida, partida.objetivo, cfg.DANIO_BEAM_POR_SEG * intervalo)
    if nave.tiempo_haz <= 0:
        nave.enfriamiento_haz = cfg.ENFRIAMIENTO_HAZ_SEGUNDOS


def _mostrar_impacto_haz(partida: 'Partida') -> None:
    objetivo = partida.objetivo
    direccion = objetivo.pos - partida.nave.pos
    direccion = direccion.normalize() if direccion.length_squared() else Vector2(1, 0)
    partida.efectos.impacto_haz(objetivo.pos - direccion * objetivo.radio, direccion)


def _disparar_enemigos(partida: 'Partida') -> None:
    for enemigo in partida.mundo.activos:
        direccion = partida.nave.pos - enemigo.pos
        if not enemigo.vivo or enemigo.tiempo_disparo > 0 or en_base(enemigo.pos):
            continue
        if not 0 < direccion.length() <= cfg.ALCANCE_ENEMIGO:
            continue
        partida.proyectiles.append(Proyectil(
            enemigo.pos.copy(), direccion.normalize() * 520,
            cfg.DANIO_ENEMIGO, 'enemigo', cfg.ALCANCE_ENEMIGO + 80,
        ))
        enemigo.tiempo_disparo = cfg.CADENCIA_ENEMIGO_SEGUNDOS


def _actualizar_proyectiles(partida: 'Partida', dt: float) -> None:
    for proyectil in partida.proyectiles:
        if not partida.nave.viva:
            break
        proyectil.actualizar(dt)
        impacto_base = fraccion_impacto(
            proyectil.anterior, proyectil.pos, Vector2(cfg.POSICION_BASE), cfg.RADIO_BASE,
        )
        if proyectil.tipo == 'enemigo':
            _impactar_nave(partida, proyectil, impacto_base)
        else:
            _impactar_enemigos(partida, proyectil, impacto_base)


def _impactar_nave(partida: 'Partida', proyectil: Proyectil, barrera: float | None) -> None:
    radio = 32 if partida.nave.escudo > 0 else partida.nave.radio
    impacto = fraccion_impacto(proyectil.anterior, proyectil.pos, partida.nave.pos, radio)
    if barrera is not None and (impacto is None or barrera <= impacto):
        proyectil.vivo = False
        return
    if impacto is None:
        return
    proyectil.vivo = False
    resultado = partida.nave.recibir_danio(proyectil.danio)
    _mostrar_impacto_nave(partida, proyectil, impacto, resultado)


def _mostrar_impacto_nave(partida: 'Partida', proyectil: Proyectil,
                          fraccion: float, resultado: ResultadoDanio) -> None:
    contacto = proyectil.anterior.lerp(proyectil.pos, fraccion)
    if resultado.escudo:
        partida.efectos.impacto_escudo(contacto, partida.nave.pos)
        _marcar(partida, partida.nave.pos + Vector2(-25, -20), resultado.escudo, (80, 190, 255))
    if resultado.vida:
        direccion = proyectil.vel.normalize() if proyectil.vel.length_squared() else Vector2(1, 0)
        contacto_casco = partida.nave.pos - direccion * partida.nave.radio
        partida.efectos.impacto_casco(contacto_casco, proyectil.vel)
        _marcar(partida, partida.nave.pos + Vector2(25, -5), resultado.vida, (255, 110, 100))
    if not partida.nave.viva:
        partida.haz_visible = False
        partida.efectos.destruccion(partida.nave.pos)
        partida.eventos_audio.append('s_explosion')


def _impactar_enemigos(partida: 'Partida', proyectil: Proyectil, barrera: float | None) -> None:
    candidatos = []
    for enemigo in partida.mundo.activos:
        if not enemigo.vivo or en_base(enemigo.pos):
            continue
        fraccion = fraccion_impacto(proyectil.anterior, proyectil.pos, enemigo.pos, enemigo.radio)
        if fraccion is not None and (barrera is None or fraccion < barrera):
            candidatos.append((fraccion, enemigo))
    if not candidatos:
        if barrera is not None:
            proyectil.vivo = False
        return
    fraccion, objetivo = min(candidatos, key=lambda candidato: candidato[0])
    proyectil.vivo = False
    posicion = proyectil.anterior.lerp(proyectil.pos, fraccion)
    if proyectil.tipo == 'misil':
        _explotar_misil(partida, posicion, proyectil.danio)
    else:
        partida.efectos.impacto_casco(posicion, proyectil.vel)
        _danio_enemigo(partida, objetivo, proyectil.danio)


def _explotar_misil(partida: 'Partida', posicion: Vector2, danio: float) -> None:
    partida.efectos.explosion_misil(posicion)
    partida.eventos_audio.append('s_explosion')
    for enemigo in partida.mundo.activos:
        if enemigo.vivo and not en_base(enemigo.pos) and enemigo.pos.distance_to(posicion) <= cfg.RADIO_EXPLOSION:
            _danio_enemigo(partida, enemigo, danio)


def _danio_enemigo(partida: 'Partida', enemigo: Enemigo, danio: float) -> None:
    if not enemigo.vivo:
        return
    perdido = enemigo.recibir_danio(danio)
    if perdido > 0:
        partida.nave.tiempo_sin_combate = 0.0
        partida.nave.hubo_combate = True
    _marcar(partida, enemigo.pos, perdido, (255, 216, 110))
    if not enemigo.vivo:
        partida.efectos.destruccion(enemigo.pos)
        partida.creditos += cfg.CREDITOS_POR_BAJA
        partida.bajas += 1
        partida.eventos_audio.append('s_explosion')


def _marcar(partida: 'Partida', posicion: Vector2, cantidad: float, color: tuple[int, int, int]) -> None:
    partida.marcadores.append(MarcadorDanio(Vector2(posicion), f'-{cantidad:g}', color))
