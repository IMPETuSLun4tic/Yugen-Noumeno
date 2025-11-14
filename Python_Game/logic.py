
import random
import math
import logging
import pygame
from pygame.math import Vector2

from config import (
    ALCANCE_BEAM,
    DANIO_BEAM_POR_SEG,
    DANIO_MISIL,
    RADIO_EXPLOSION,
    EXPLOSION_PARTICLES,
    SCREEN_SHAKE_INTENSITY,
    MAX_ENEMIGOS_EN_PANTALLA,
    VELOCIDAD_BASE_ENEMIGO,
    VELOCIDAD_MAXIMA_ENEMIGO,
    VELOCIDAD_INCREMENTO_POR_MUERTE,
    SPAWN_INTERVAL_BASE,
    SPAWN_INTERVAL_MINIMO,
    SPAWN_REDUCCION_POR_MUERTE,
)
from entities import LaserShot, Misil, Enemigo, Particle
from utils import colision_punto_circulo, colision_circulos

logger = logging.getLogger("Naves")


def manejar_eventos(nave):
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            return False
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_SPACE and nave.alive:
                nave.misiles_activos = not nave.misiles_activos
    return True

def procesar_inputs(nave, dt, mouse_pos, entidades, recursos, stats):
    if not nave.alive:
        return False

    nave.actualizar(dt, mouse_pos)
    botones = pygame.mouse.get_pressed(3)

    if botones[0] and nave.puede_disparar_laser():
        nave.disparar_laser()
        dir_vec = Vector2(mouse_pos) - nave.pos
        entidades['lasers'].append(LaserShot(nave.pos, dir_vec))
        if recursos.get('s_shot'):
            try:
                recursos['s_shot'].play()
            except Exception:
                logger.exception("Error reproduciendo s_shot")

    haz_activo = botones[2]
    beam_channel = None
    try:
        beam_channel = pygame.mixer.Channel(1)
    except Exception:
        logger.debug("No se pudo acceder al canal de audio 1")

    if haz_activo:
        if beam_channel and recursos.get('s_beam') and not beam_channel.get_busy():
            try:
                beam_channel.play(recursos['s_beam'], loops=-1, fade_ms=100)
            except Exception:
                logger.exception("Error iniciando sonido de beam")
    else:
        if beam_channel and beam_channel.get_busy():
            try:
                beam_channel.fadeout(100)
            except Exception:
                logger.exception("Error deteniendo sonido de beam")

    if nave.misiles_activos and nave.puede_disparar_misil():
        nave.disparar_misil()
        dir_vec = Vector2(mouse_pos) - nave.pos
        if dir_vec.length_squared() == 0:
            dir_vec = Vector2(1,0)
        entidades['misiles'].append(Misil(nave.pos, dir_vec))
        if recursos.get('s_missile'):
            try:
                recursos['s_missile'].play()
            except Exception:
                logger.exception("Error reproducir s_missile")

    return haz_activo

def actualizar_proyectiles(entidades, dt):
    for l in entidades['lasers']:
        l.actualizar(dt)
        entidades['particles'].append(
            Particle(l.pos + Vector2(random.uniform(-2,2), random.uniform(-2,2)),
                     Vector2(random.uniform(-40,40), random.uniform(-40,40)),
                     (255,200,200), 1.6, 0.12)
        )
    entidades['lasers'] = [l for l in entidades['lasers'] if l.vivo]

    for m in entidades['misiles']:
        m.actualizar(dt, entidades['particles'])
    entidades['misiles'] = [m for m in entidades['misiles'] if m.vivo]

def procesar_colisiones_laser(entidades, recursos, stats, shake_callback):
    for l in entidades['lasers']:
        for e in entidades['enemigos']:
            if colision_punto_circulo(l.pos, e.pos, e.radio):
                died = e.recibir_danio(l.danio)
                l.vivo = False
                for _ in range(6):
                    entidades['particles'].append(Particle(l.pos, Vector2(random.uniform(-120,120), random.uniform(-120,120)),
                                                          (255,200,40), random.uniform(2,4), 0.45))
                if died:
                    stats['muertes_totales'] += 1
                    actualizar_dificultad(stats)
                    shake_callback(SCREEN_SHAKE_INTENSITY, 0.25)
                    if recursos.get('s_explosion'):
                        try:
                            recursos['s_explosion'].play()
                        except Exception:
                            logger.exception("Error reproducir s_explosion")

def procesar_colisiones_misil(entidades, recursos, stats, shake_callback):
    for m in entidades['misiles']:
        for e in entidades['enemigos']:
            if colision_punto_circulo(m.pos, e.pos, e.radio):
                for e2 in entidades['enemigos']:
                    if (e2.pos - m.pos).length() <= RADIO_EXPLOSION:
                        died = e2.recibir_danio(DANIO_MISIL)
                        if died:
                            stats['muertes_totales'] += 1
                            actualizar_dificultad(stats)
                            shake_callback(SCREEN_SHAKE_INTENSITY, 0.25)
                            if recursos.get('s_explosion'):
                                try:
                                    recursos['s_explosion'].play()
                                except Exception:
                                    logger.exception("Error reproducir s_explosion")

                m.vivo = False
                for _ in range(EXPLOSION_PARTICLES):
                    ang = random.random() * math.pi * 2
                    speed = random.uniform(80,320)
                    vel = Vector2(math.cos(ang), math.sin(ang)) * speed
                    entidades['particles'].append(Particle(m.pos + vel*0.01, vel, (255,160,60), random.uniform(3,6), random.uniform(0.6,1.2)))
                if recursos.get('s_explosion'):
                    try:
                        recursos['s_explosion'].play()
                    except Exception:
                        logger.exception("Error reproducir s_explosion")
                break

def procesar_haz(haz_activo, entidades, recursos, stats, dt, shake_callback, nave, mouse_pos):
    if not haz_activo:
        return
    origen = nave.pos
    dir_beam = Vector2(mouse_pos) - origen
    dist = dir_beam.length()
    if dist == 0:
        dir_beam = Vector2(1,0)
        dist = 1
    dir_norm = dir_beam.normalize()
    for e in entidades['enemigos']:
        rel = e.pos - origen
        t = rel.dot(dir_norm)
        if 0 <= t <= min(ALCANCE_BEAM, dist):
            perpendicular = (rel - dir_norm * t).length()
            if perpendicular <= e.radio + 6:
                died = e.recibir_danio(DANIO_BEAM_POR_SEG * dt)
                for _ in range(2):
                    entidades['particles'].append(Particle(e.pos, Vector2(random.uniform(-80,80), random.uniform(-80,80)),
                                                         (255,50,200), random.uniform(2,4), 0.25))
                if died:
                    stats['muertes_totales'] += 1
                    actualizar_dificultad(stats)
                    shake_callback(SCREEN_SHAKE_INTENSITY, 0.25)
                    if recursos.get('s_explosion'):
                        try:
                            recursos['s_explosion'].play()
                        except Exception:
                            logger.exception("Error reproducir s_explosion")

def procesar_colisiones_nave(entidades, recursos, stats, shake_callback):
    nave = entidades['nave']
    if not nave.alive:
        return
    for e in entidades['enemigos']:
        if colision_circulos(nave.pos, nave.radio, e.pos, e.radio):
            nave.alive = False
            nave.health = 0
            for _ in range(60):
                ang = random.random() * math.pi * 2
                speed = random.uniform(100,400)
                vel = Vector2(math.cos(ang), math.sin(ang)) * speed
                entidades['particles'].append(Particle(nave.pos + vel*0.02, vel,
                                                       random.choice([(255,100,50),(255,200,80),(255,50,50)]),
                                                       random.uniform(4,8), random.uniform(0.8,1.5)))
            shake_callback(SCREEN_SHAKE_INTENSITY * 2, 0.5)
            if recursos.get('s_explosion'):
                try:
                    recursos['s_explosion'].play()
                except Exception:
                    logger.exception("Error reproducir s_explosion")
            break

def actualizar_dificultad(stats):
    stats['velocidad_enemigos'] = min(VELOCIDAD_MAXIMA_ENEMIGO,
                                     VELOCIDAD_BASE_ENEMIGO + stats['muertes_totales'] * VELOCIDAD_INCREMENTO_POR_MUERTE)
    stats['spawn_interval'] = max(SPAWN_INTERVAL_MINIMO,
                                  SPAWN_INTERVAL_BASE - stats['muertes_totales'] * SPAWN_REDUCCION_POR_MUERTE)

def actualizar_entidades(entidades, dt, parallax_velocity, stats):
    for e in entidades['enemigos']:
        e.actualizar(dt)
    entidades['enemigos'] = [e for e in entidades['enemigos'] if e.vivo]

    for p in entidades['particles']:
        p.actualizar(dt)
    entidades['particles'] = [p for p in entidades['particles'] if p.vivo]

    for n in entidades['nebulas']:
        n.actualizar(dt, parallax_velocity)
    for f in entidades['fogs']:
        f.actualizar(dt, parallax_velocity)
    for s in entidades['stars']:
        s.actualizar(dt, parallax_velocity)

    stats['tiempo_spawn'] += dt
    if stats['tiempo_spawn'] >= stats['spawn_interval']:
        stats['tiempo_spawn'] = 0
        if len(entidades['enemigos']) < MAX_ENEMIGOS_EN_PANTALLA:
            entidades['enemigos'].append(Enemigo(stats['velocidad_enemigos']))