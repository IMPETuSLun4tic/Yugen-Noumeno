import random
import logging
import pygame

from pygame.math import Vector2
from config import (
    ANCHO, ALTO,
    CANT_ENEMIGOS_INICIAL,
    STAR_COUNT,
    NEBULA_COUNT_MIN, NEBULA_COUNT_MAX,
    FOG_COUNT_MIN, FOG_COUNT_MAX,
    VELOCIDAD_BASE_ENEMIGO,
)
from utils import create_sound_tone
from entities import Nave, Enemigo, Star, Nebula, Fog

logger = logging.getLogger("Naves")


def cargar_recursos():
    recursos = {}
    try:
        img = pygame.image.load('jugador.png').convert_alpha()
        recursos['jugador'] = pygame.transform.rotate(
            pygame.transform.scale(img, (40, 40)), 180
        )
    except Exception:
        logger.info("Sprite `jugador.png` no encontrado o inválido; usando fallback")
        recursos['jugador'] = None

    try:
        img = pygame.image.load('enemigos.png').convert_alpha()
        recursos['enemigo'] = pygame.transform.scale(img, (36, 36))
    except Exception:
        recursos['enemigo'] = None

    try:
        img = pygame.image.load('nebulosa.png').convert_alpha()
        recursos['nebulosa'] = pygame.transform.scale(img, (120, 120))
    except Exception:
        recursos['nebulosa'] = None

    try:
        recursos['s_shot'] = pygame.mixer.Sound('laser.wav')
        recursos['s_missile'] = pygame.mixer.Sound('missile.wav')
        recursos['s_explosion'] = pygame.mixer.Sound('explosion.wav')
        recursos['s_beam'] = pygame.mixer.Sound('beam.wav')
    except Exception:
        logger.info("SFX faltantes; usando tonos sintetizados o None")
        recursos['s_shot'] = create_sound_tone(1200, 0.07, 0.12)
        recursos['s_missile'] = create_sound_tone(420, 0.12, 0.16)
        recursos['s_explosion'] = create_sound_tone(160, 0.5, 0.18)
        recursos['s_beam'] = create_sound_tone(720, 0.3, 0.06)

    return recursos


def inicializar_entidades(recursos):
    entidades = {
        'nave': Nave((ANCHO / 2, ALTO / 2)),
        'lasers': [],
        'misiles': [],
        'enemigos': [Enemigo(VELOCIDAD_BASE_ENEMIGO) for _ in range(CANT_ENEMIGOS_INICIAL)],
        'particles': [],
        'stars': [Star() for _ in range(STAR_COUNT)],
        'nebulas': [
            Nebula(recursos['nebulosa'])
            for _ in range(random.randint(NEBULA_COUNT_MIN, NEBULA_COUNT_MAX))
        ],
        'fogs': [
            Fog()
            for _ in range(random.randint(FOG_COUNT_MIN, FOG_COUNT_MAX))
        ],
    }
    return entidades
