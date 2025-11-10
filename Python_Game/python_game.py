
"""
A space ship's shooter game with enemies, projectiles, particle effects, and performance monitoring.
Este es un juego de naves espaciales con enemigos, proyectiles, efectos de partículas y monitoreo de rendimiento.
"""

import os
import time
import math
import random
import logging

import pygame
import psutil
import numpy as np
from pygame.math import Vector2

# Configuración logging:
LOG_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("Naves")

# CONFIGURACIÓN / CONSTANTES:
ANCHO = 1366
ALTO = 768
FPS = 100

COLOR_FONDO_BASE = (6, 8, 20)
COLOR_NAVE = (80, 200, 255)
COLOR_LASER = (255, 70, 70)
COLOR_BEAM = (161, 255, 180)
COLOR_MISIL = (255, 190, 80)
COLOR_ENEMIGO = (120, 240, 140)

CANT_ENEMIGOS_INICIAL = 6
MAX_ENEMIGOS_EN_PANTALLA = 25
SPAWN_INTERVAL = 100.0

DANIO_LASER = 40
COOLDOWN_LASER = 0.12

DANIO_BEAM_POR_SEG = 260
ALCANCE_BEAM = 820

DANIO_MISIL = 120
VELOCIDAD_MISIL = 360
CADENCIA_MISIL = 1.2
RADIO_EXPLOSION = 70

VEL_NAVE = 260
ROTACION_SUAVIZADO = 0.18

VELOCIDAD_BASE_ENEMIGO = 250
VELOCIDAD_INCREMENTO_POR_MUERTE = 10
VELOCIDAD_MAXIMA_ENEMIGO = 480

SPAWN_INTERVAL_BASE = 2.5
SPAWN_REDUCCION_POR_MUERTE = 0.15
SPAWN_INTERVAL_MINIMO = 1.5

PARTICLE_LIFETIME = 0.7
EXPLOSION_PARTICLES = 40
SCREEN_SHAKE_INTENSITY = 14
STAR_COUNT = 120
NEBULA_COUNT = random.randint(2, 4)
FOG_COUNT = random.randint(10, 14)

BLOOM_DOWNSCALE = 4
BLOOM_INTENSITY = 180

# HELPERS:
def clamp(v, a, b):
    return max(a, min(b, v))

def create_sound_tone(frequency=440, duration=0.12, volume=0.2, sample_rate=44100):
    """Genera un tono simple (seno) y devuelve pygame.Sound, maneja errores internamente."""
    try:
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = 0.5 * np.sin(2 * np.pi * frequency * t)
        env = np.exp(-5 * t)
        sig = (wave * env * volume)
        audio = np.int16(sig * 32767)
        stereo = np.column_stack([audio, audio])
        sound = pygame.sndarray.make_sound(stereo.copy())
        return sound
    except Exception:
        logger.exception("Fallo al generar tono sintético")
        return None

# PERFORMANCE MONITOR:
class PerformanceMonitor:
    """Mide CPU, memoria y frame time (simple)."""
    def __init__(self):
        try:
            self.process = psutil.Process()
        except Exception:
            logger.exception("psutil no disponible; se deshabilitarán métricas avanzadas")
            self.process = None
        self.last_time = time.time()
        self.frame_times = []

    def update(self):
        current = time.time()
        frame_ms = (current - self.last_time) * 1000.0
        self.last_time = current
        self.frame_times.append(frame_ms)
        if len(self.frame_times) > 60:
            self.frame_times.pop(0)

    def get_stats(self):
        cpu_percent = self.process.cpu_percent() if self.process else 0.0
        memory_mb = self.process.memory_info().rss / 1024.0 / 1024.0 if self.process else 0.0
        avg_frame = sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0.0
        fps = 1000.0 / avg_frame if avg_frame > 0 else 0.0
        return {'cpu': cpu_percent, 'memory': memory_mb, 'avg_frame_ms': avg_frame, 'fps': fps}

# ENTIDADES:
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

class Nave:
    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.vel = Vector2(0,0)
        self.angle = 0.0
        self.radio = 18
        self.laser_timer = 0.0
        self.misil_timer = 0.0
        self.misiles_activos = False
        self.health = 200
        self.alive = True

    def actualizar(self, dt, mouse_pos):
        keys = pygame.key.get_pressed()
        direccion = Vector2(0,0)
        if keys[pygame.K_w]:
            direccion.y -= 1
        if keys[pygame.K_s]:
            direccion.y += 1
        if keys[pygame.K_a]:
            direccion.x -= 1
        if keys[pygame.K_d]:
            direccion.x += 1
        if direccion.length_squared() > 0:
            direccion = direccion.normalize()
        self.vel = direccion * VEL_NAVE
        self.pos += self.vel * dt
        self.pos.x %= ANCHO
        self.pos.y %= ALTO

        objetivo = Vector2(mouse_pos) - self.pos
        if objetivo.length_squared() > 0:
            ang_deseado = math.degrees(math.atan2(-objetivo.y, objetivo.x))
            diff = (ang_deseado - self.angle + 180) % 360 - 180
            self.angle += diff * ROTACION_SUAVIZADO

        self.laser_timer -= dt
        self.misil_timer -= dt

    def puede_disparar_laser(self):
        return self.laser_timer <= 0

    def disparar_laser(self):
        self.laser_timer = COOLDOWN_LASER

    def puede_disparar_misil(self):
        return self.misil_timer <= 0

    def disparar_misil(self):
        self.misil_timer = CADENCIA_MISIL

    def recibir_danio(self, cantidad):
        self.health -= cantidad
        if self.health <= 0 and self.alive:
            self.alive = False
            return True
        return False

    def dibujar(self, pantalla, offset, particles, img=None):
        ang_rad = math.radians(self.angle)
        punta = self.pos + Vector2(math.cos(ang_rad), -math.sin(ang_rad)) * self.radio
        izquierdo = self.pos + Vector2(math.cos(ang_rad + 2.5), -math.sin(ang_rad + 2.5)) * self.radio
        derecho = self.pos + Vector2(math.cos(ang_rad - 2.5), -math.sin(ang_rad - 2.5)) * self.radio

        if self.vel.length_squared() > 1:
            back = self.pos - Vector2(math.cos(ang_rad), -math.sin(ang_rad)) * (self.radio + 6)
            for _ in range(4):
                jitter = Vector2(random.uniform(-4,4), random.uniform(-4,4))
                p = Particle(back + jitter, Vector2(random.uniform(-80,-40), random.uniform(-10,10)), (255,160,60), random.uniform(2,4), 0.25)
                particles.append(p)

        if img:
            try:
                rotated = pygame.transform.rotate(img, self.angle)
                rect = rotated.get_rect(center=(self.pos.x + offset[0], self.pos.y + offset[1]))
                pantalla.blit(rotated, rect)
            except Exception:
                logger.exception("Error al dibujar sprite de jugador; usando fallback")
                self._dibujar_fallback(pantalla, offset, punta, izquierdo, derecho)
        else:
            self._dibujar_fallback(pantalla, offset, punta, izquierdo, derecho)

    def _dibujar_fallback(self, pantalla, offset, punta, izquierdo, derecho):
        surf = pygame.Surface((self.radio*4, self.radio*4), pygame.SRCALPHA)
        pts = []
        for v in (punta, izquierdo, derecho):
            pts.append((v.x - self.pos.x + self.radio*2, v.y - self.pos.y + self.radio*2))
        pygame.draw.polygon(surf, COLOR_NAVE, pts)
        pygame.draw.polygon(surf, (20,20,30), pts, 2)
        pantalla.blit(surf, (self.pos.x - self.radio*2 + offset[0], self.pos.y - self.radio*2 + offset[1]))

class LaserShot:
    def __init__(self, pos, dir_vec):
        self.pos = Vector2(pos)
        if dir_vec.length_squared() == 0:
            dir_vec = Vector2(1,0)
        self.vel = dir_vec.normalize() * 800
        self.radio = 4
        self.danio = DANIO_LASER
        self.vivo = True
        self.age = 0.0

    def actualizar(self, dt):
        self.age += dt
        self.pos += self.vel * dt
        if not (0 <= self.pos.x <= ANCHO and 0 <= self.pos.y <= ALTO):
            self.vivo = False

    def dibujar(self, pantalla, offset=(0,0)):
        surf = pygame.Surface((20,20), pygame.SRCALPHA)
        cx, cy = 10, 10
        pygame.draw.circle(surf, (*COLOR_LASER, 50), (cx,cy), 9)
        pygame.draw.circle(surf, (*COLOR_LASER, 140), (cx,cy), 5)
        pygame.draw.circle(surf, COLOR_LASER, (cx,cy), 2)
        pantalla.blit(surf, (self.pos.x - 10 + offset[0], self.pos.y - 10 + offset[1]))

class Misil:
    def __init__(self, pos, dir_vec):
        self.pos = Vector2(pos)
        if dir_vec.length_squared() == 0:
            dir_vec = Vector2(1,0)
        self.vel = dir_vec.normalize() * VELOCIDAD_MISIL
        self.radio = 8
        self.danio = DANIO_MISIL
        self.vivo = True
        self.tail_timer = 0.0

    def actualizar(self, dt, particles):
        self.pos += self.vel * dt
        self.tail_timer += dt
        if self.tail_timer > 0.03:
            self.tail_timer = 0.0
            back = self.pos - self.vel.normalize() * 8
            for _ in range(2):
                vel = Vector2(random.uniform(-30,-10), random.uniform(-10,10)) + -self.vel.normalize()*20
                particles.append(Particle(back + Vector2(random.uniform(-4,4), random.uniform(-4,4)), vel, (255,140,40), random.uniform(2,4), 0.5))
        if not (0 <= self.pos.x <= ANCHO and 0 <= self.pos.y <= ALTO):
            self.vivo = False

    def dibujar(self, pantalla, offset=(0,0)):
        pygame.draw.circle(pantalla, COLOR_MISIL, (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])), self.radio)
        surf = pygame.Surface((30,10), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (255,150,50,160), (0,0,30,10))
        ang = math.degrees(math.atan2(-self.vel.y, self.vel.x))
        surf_rot = pygame.transform.rotate(surf, ang)
        pantalla.blit(surf_rot, (self.pos.x - surf_rot.get_width()/2 + offset[0] - self.vel.normalize().x*6,
                                 self.pos.y - surf_rot.get_height()/2 + offset[1] - self.vel.normalize().y*6))

class Enemigo:
    def __init__(self, velocidad_nivel=VELOCIDAD_BASE_ENEMIGO):
        self.pos = Vector2(random.uniform(0,ANCHO), random.uniform(0,ALTO))
        self.vel = Vector2(random.uniform(-velocidad_nivel, velocidad_nivel),
                           random.uniform(-velocidad_nivel, velocidad_nivel))
        self.radio = 18
        self.vida = 200
        self.max_vida = 200
        self.vivo = True
        self.wobble = random.random() * 200

    def actualizar(self, dt):
        wob = math.sin(time.time() + self.wobble) * 40
        self.pos += (self.vel + Vector2(wob, -wob*0.3)) * dt
        if self.pos.x < 0 or self.pos.x > ANCHO:
            self.vel.x *= -1
        if self.pos.y < 0 or self.pos.y > ALTO:
            self.vel.y *= -1
        if self.vida <= 0:
            self.vivo = False

    def recibir_danio(self, cantidad):
        self.vida -= cantidad
        if self.vida <= 0 and self.vivo:
            self.vivo = False
            return True
        return False

    def dibujar(self, pantalla, offset=(0,0), img=None):
        if img:
            try:
                rect = img.get_rect(center=(self.pos.x + offset[0], self.pos.y + offset[1]))
                pantalla.blit(img, rect)
            except Exception:
                logger.exception("Error dibujando sprite enemigo; usando fallback")
                self._dibujar_fallback(pantalla, offset)
        else:
            self._dibujar_fallback(pantalla, offset)

        porc = clamp(self.vida / self.max_vida, 0, 1)
        w, h = 34, 6
        x = int(self.pos.x - w/2 + offset[0])
        y = int(self.pos.y - self.radio - 14 + offset[1])
        pygame.draw.rect(pantalla, (40,40,40), (x, y, w, h))
        pygame.draw.rect(pantalla, (0,200,0), (x, y, int(w * porc), h))

    def _dibujar_fallback(self, pantalla, offset):
        surf = pygame.Surface((self.radio*3, self.radio*3), pygame.SRCALPHA)
        cx = cy = self.radio * 1.5
        pygame.draw.circle(surf, (*COLOR_ENEMIGO, 90), (int(cx), int(cy)), int(self.radio+6))
        pygame.draw.circle(surf, COLOR_ENEMIGO, (int(cx), int(cy)), int(self.radio))
        pantalla.blit(surf, (self.pos.x - cx + offset[0], self.pos.y - cy + offset[1]))

# COLISIONES Y BLOOM:
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

# RECURSOS / INICIALIZACIÓN:
def cargar_recursos():
    recursos = {}
    try:
        img = pygame.image.load('jugador.png').convert_alpha()
        recursos['jugador'] = pygame.transform.rotate(pygame.transform.scale(img, (40,40)), 180)
    except Exception:
        logger.info("Sprite 'jugador.png' no encontrado o inválido; usando fallback")
        recursos['jugador'] = None

    try:
        img = pygame.image.load('enemigos.png').convert_alpha()
        recursos['enemigo'] = pygame.transform.scale(img, (36,36))
    except Exception:
        recursos['enemigo'] = None

    try:
        img = pygame.image.load('nebulosa.png').convert_alpha()
        recursos['nebulosa'] = pygame.transform.scale(img, (120,120))
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
        'nave': Nave((ANCHO/2, ALTO/2)),
        'lasers': [],
        'misiles': [],
        'enemigos': [Enemigo(VELOCIDAD_BASE_ENEMIGO) for _ in range(CANT_ENEMIGOS_INICIAL)],
        'particles': [],
        'stars': [Star() for _ in range(STAR_COUNT)],
        'nebulas': [Nebula(recursos['nebulosa']) for _ in range(NEBULA_COUNT)],
        'fogs': [Fog() for _ in range(FOG_COUNT)]
    }
    return entidades

# LÓGICA: PROCESAMIENTO / COLISIONES / ACTUALIZACIÓN:
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

# RENDER: UI + ESCENA
def dibujar_ui(scene, entidades, stats, nave, reloj, perf_monitor=None, fuente=None):
    if fuente is None:
        fuente = pygame.font.SysFont("consolas", 18)
    texto = f"Enemigos: {len(entidades['enemigos'])}  Misiles {'ON' if nave.misiles_activos else 'OFF'}  FPS:{int(reloj.get_fps())}"
    surf = fuente.render(texto, True, (200,200,200))
    scene.blit(surf, (10,10))

    instr = "Controles: WASD mover | Clic izq: ráfaga | Clic der: láser continuo | Espacio: toggle misiles"
    surf2 = fuente.render(instr, True, (160,160,160))
    scene.blit(surf2, (10, ALTO-28))

    stats_text = f"Muertes: {stats['muertes_totales']}  Vel: {int(stats['velocidad_enemigos'])}  Spawn: {stats['spawn_interval']:.1f}s"
    surf_stats = fuente.render(stats_text, True, (180,180,180))
    scene.blit(surf_stats, (10,35))

    if not nave.alive:
        fuente_grande = pygame.font.SysFont("consolas", 48, bold=True)
        game_over = fuente_grande.render("GAME OVER", True, (255,80,80))
        scene.blit(game_over, (ANCHO//2 - game_over.get_width()//2, ALTO//2 - 40))
        fuente_med = pygame.font.SysFont("consolas", 24)
        final_score = fuente_med.render(f"Enemigos eliminados: {stats['muertes_totales']}", True, (200,200,200))
        scene.blit(final_score, (ANCHO//2 - final_score.get_width()//2, ALTO//2 + 20))

    if perf_monitor:
        perf_stats = perf_monitor.get_stats()
        perf_text = f"CPU: {perf_stats['cpu']:.1f}%  RAM: {perf_stats['memory']:.0f}MB  Frame: {perf_stats['avg_frame_ms']:.1f}ms"
        surf_perf = fuente.render(perf_text, True, (180,180,255))
        scene.blit(surf_perf, (10,60))

def dibujar_escena(scene, entidades, recursos, haz_activo, nave, mouse_pos, stats, reloj, fuente_ui):
    scene.fill(COLOR_FONDO_BASE)
    for n in entidades['nebulas']:
        n.dibujar(scene)
    for s in entidades['stars']:
        s.dibujar(scene)
    for f in entidades['fogs']:
        f.dibujar(scene)
    for e in entidades['enemigos']:
        e.dibujar(scene, (0,0), recursos.get('enemigo'))
    for m in entidades['misiles']:
        m.dibujar(scene, (0,0))
    for l in entidades['lasers']:
        l.dibujar(scene, (0,0))
    if nave.alive:
        nave.dibujar(scene, (0,0), entidades['particles'], recursos.get('jugador'))
    for p in entidades['particles']:
        p.dibujar(scene, (0,0))

    if haz_activo:
        origen = nave.pos
        dir_norm = (Vector2(mouse_pos) - origen)
        dir_norm = dir_norm.normalize() if dir_norm.length_squared() != 0 else Vector2(1,0)
        destino = origen + dir_norm * ALCANCE_BEAM
        surf = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        pygame.draw.line(surf, (*COLOR_BEAM, 40), (origen.x, origen.y), (destino.x, destino.y), 40)
        pygame.draw.line(surf, (*COLOR_BEAM, 100), (origen.x, origen.y), (destino.x, destino.y), 12)
        pygame.draw.line(surf, (*COLOR_BEAM, 220), (origen.x, origen.y), (destino.x, destino.y), 4)
        scene.blit(surf, (0,0))

    dibujar_ui(scene, entidades, stats, nave, reloj, fuente=fuente_ui)

# UTIL / DIAGNÓSTICO:
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

# MAIN
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

    # Convertir surfaces cargadas
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
        'velocidad_enemigos': VELOCIDAD_BASE_ENEMIGO,
        'spawn_interval': SPAWN_INTERVAL_BASE,
        'tiempo_spawn': 0.0
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

        parallax_velocity = nave.vel if nave.alive else Vector2(0,0)
        actualizar_entidades(entidades, dt, parallax_velocity, stats)

        if shake_state['timer'] > 0:
            shake_state['timer'] -= dt
            offset = (random.uniform(-shake_state['amount'], shake_state['amount']) *
                      (shake_state['timer'] / 0.25 if shake_state['timer'] < 0.25 else 1),
                      random.uniform(-shake_state['amount'], shake_state['amount']) *
                      (shake_state['timer'] / 0.25 if shake_state['timer'] < 0.25 else 1))
        else:
            offset = (0,0)
            shake_state['amount'] = 0.0
            shake_state['timer'] = 0.0

        dibujar_escena(scene, entidades, recursos, haz_activo, nave, mouse_pos, stats, reloj, fuente_ui)

        bloom = apply_bloom(scene, intensity=BLOOM_INTENSITY, downscale=BLOOM_DOWNSCALE)
        pantalla.fill((0,0,0))
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
