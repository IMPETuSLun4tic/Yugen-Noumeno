# python
# utils.py
import math
import logging
import numpy as np
import pygame

from config import BLOOM_DOWNSCALE, BLOOM_INTENSITY

logger = logging.getLogger("Naves")


def clamp(v, a, b):
    return max(a, min(b, v))


def create_sound_tone(frequency=440, duration=0.12, volume=0.2, sample_rate=44100):
    try:
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = 0.5 * np.sin(2 * np.pi * frequency * t)
        env = np.exp(-5 * t)
        sig = wave * env * volume
        audio = np.int16(sig * 32767)
        stereo = np.column_stack([audio, audio])
        return pygame.sndarray.make_sound(stereo.copy())
    except Exception:
        logger.exception("Fallo al generar tono sintético")
        return None


def colision_punto_circulo(punto, centro, radio):
    return (punto - centro).length_squared() <= radio * radio


def colision_circulos(c1, r1, c2, r2):
    return (c1 - c2).length_squared() <= (r1 + r2) ** 2


def apply_bloom(scene_surf, intensity=BLOOM_INTENSITY, downscale=BLOOM_DOWNSCALE):
    try:
        w, h = scene_surf.get_size()
        tw, th = max(1, w // downscale), max(1, h // downscale)
        small = pygame.transform.smoothscale(scene_surf, (tw, th))
        blur = pygame.transform.smoothscale(small, (w, h))
        bloom = blur.copy()
        bloom.set_alpha(intensity)
        return bloom
    except Exception:
        logger.exception("Error aplicando bloom")
        return scene_surf.copy()
