import logging
import random
from pathlib import Path

import pygame

import config as cfg
from entities import Fog, Nebula, Star
from utils import create_sound_tone

logger = logging.getLogger("Naves")
DIRECTORIO_RECURSOS = Path(__file__).resolve().parent


def _cargar_imagen(nombre: str, tamanio: tuple[int, int], rotacion: int = 0) -> pygame.Surface | None:
    try:
        imagen = pygame.image.load(str(DIRECTORIO_RECURSOS / nombre)).convert_alpha()
        return pygame.transform.rotate(pygame.transform.scale(imagen, tamanio), rotacion)
    except (pygame.error, OSError) as error:
        logger.info("Imagen %s no disponible; usando figura: %s", nombre, error)
        return None


def _cargar_sonido(nombre: str, frecuencia: int, duracion: float) -> pygame.mixer.Sound | None:
    if pygame.mixer.get_init() is None:
        return None
    try:
        sonido = pygame.mixer.Sound(str(DIRECTORIO_RECURSOS / nombre))
        if nombre == 'laser.wav':
            sonido.set_volume(0.5)
        return sonido
    except (pygame.error, OSError) as error:
        logger.info("Sonido %s no disponible; usando tono: %s", nombre, error)
        return create_sound_tone(frecuencia, duracion, 0.12)


def cargar_recursos() -> dict:
    return {
        'jugador': _cargar_imagen('jugador.png', (40, 40), 180),
        'enemigo': _cargar_imagen('enemigos.png', (36, 36)),
        'nebulosa': _cargar_imagen('nebulosa.png', (120, 120)),
        's_shot': _cargar_sonido('laser.wav', 1200, 0.07),
        's_missile': _cargar_sonido('missile.wav', 420, 0.12),
        's_explosion': _cargar_sonido('explosion.wav', 160, 0.5),
        's_beam': _cargar_sonido('beam.wav', 720, 0.3),
    }


def crear_fondo(recursos: dict) -> dict:
    return {
        'stars': [Star() for _ in range(cfg.STAR_COUNT)],
        'nebulas': [Nebula(recursos['nebulosa']) for _ in range(
            random.randint(cfg.NEBULA_COUNT_MIN, cfg.NEBULA_COUNT_MAX))],
        'fogs': [Fog() for _ in range(random.randint(cfg.FOG_COUNT_MIN, cfg.FOG_COUNT_MAX))],
    }
