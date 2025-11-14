# python
# main.py
import os
import logging
import random
import pygame
from pygame.math import Vector2

from config import ANCHO, ALTO, FPS, BLOOM_INTENSITY, BLOOM_DOWNSCALE, SCREEN_SHAKE_INTENSITY
from utils import apply_bloom
from resources import cargar_recursos, inicializar_entidades
from performance import PerformanceMonitor
from logic import (
    manejar_eventos,
    procesar_inputs,
    actualizar_proyectiles,
    procesar_colisiones_laser,
    procesar_colisiones_misil,
    procesar_haz,
    procesar_colisiones_nave,
    actualizar_entidades,
)
from render import dibujar_escena

LOG_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("Naves")


def verificar_aceleracion_gpu():
    try:
        pygame.init()
        driver = pygame.display.get_driver()
        logger.info(f"Driver de video activo: {driver}")
        info = pygame.display.Info()
        logger.info(f"Aceleración por hardware: {info.hw}")
        logger.info(f"Blits acelerados: {info.blit_hw}")
        logger.info(f"Version SDL: {pygame.get_sdl_version()}")
        logger.info(f"Version Pygame: {pygame.version.ver}")
        return info.hw
    except Exception:
        logger.exception("Fallo al verificar aceleración GPU")
        return False


def ejecutar():
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    logger.info("Iniciando juego")
    verificar_aceleracion_gpu()

    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
    except Exception:
        logger.exception("No se pudo inicializar pygame.mixer; audio puede fallar")

    pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.DOUBLEBUF)
    pygame.display.set_caption("Naves Espaciales - Bloom & Shake (modular)")
    reloj = pygame.time.Clock()

    scene = pygame.Surface((ANCHO, ALTO))
    perf_monitor = PerformanceMonitor()
    recursos = cargar_recursos()

    for k, v in list(recursos.items()):
        if isinstance(v, pygame.Surface):
            try:
                recursos[k] = v.convert_alpha()
            except Exception:
                logger.exception(f"Error convert_alpha en recurso {k}")

    entidades = inicializar_entidades(recursos)
    nave = entidades['nave']

    stats = {
        'muertes_totales': 0,
        'velocidad_enemigos': 250.0,
        'spawn_interval': 2.5,
        'tiempo_spawn': 0.0,
    }

    shake_state = {'timer': 0.0, 'amount': 0.0}

    def trigger_shake(amount, duration=0.25):
        shake_state['timer'] = max(shake_state['timer'], duration)
        shake_state['amount'] = max(shake_state['amount'], amount)

    fuente_ui = pygame.font.SysFont("consolas", 18)

    running = True
    while running:
        dt = reloj.tick(FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        perf_monitor.update()

        running = manejar_eventos(nave)
        if not running:
            break

        haz_activo = procesar_inputs(nave, dt, mouse_pos, entidades, recursos, stats)
        actualizar_proyectiles(entidades, dt)
        procesar_colisiones_laser(entidades, recursos, stats, trigger_shake)
        procesar_colisiones_misil(entidades, recursos, stats, trigger_shake)
        procesar_haz(haz_activo, entidades, recursos, stats, dt, trigger_shake, nave, mouse_pos)
        procesar_colisiones_nave(entidades, recursos, stats, trigger_shake)

        parallax_velocity = nave.vel if nave.alive else Vector2(0, 0)
        actualizar_entidades(entidades, dt, parallax_velocity, stats)

        if shake_state['timer'] > 0:
            shake_state['timer'] -= dt
            factor = shake_state['timer'] / 0.25 if shake_state['timer'] < 0.25 else 1
            offset = (
                random.uniform(-shake_state['amount'], shake_state['amount']) * factor,
                random.uniform(-shake_state['amount'], shake_state['amount']) * factor,
            )
        else:
            offset = (0, 0)
            shake_state['amount'] = 0.0
            shake_state['timer'] = 0.0

        dibujar_escena(scene, entidades, recursos, haz_activo, nave, mouse_pos, stats, reloj, fuente_ui)

        bloom = apply_bloom(scene, intensity=BLOOM_INTENSITY, downscale=BLOOM_DOWNSCALE)
        pantalla.fill((0, 0, 0))
        pantalla.blit(scene, offset)
        pantalla.blit(bloom, offset, special_flags=pygame.BLEND_ADD)
        pygame.display.flip()

    try:
        pygame.mixer.quit()
    except Exception:
        logger.debug("Error al cerrar mixer (puede que no estuviera inicializado)")

    pygame.quit()
    logger.info("Juego finalizado")


if __name__ == "__main__":
    ejecutar()
