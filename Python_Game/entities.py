import math
import random
import time
import logging
import pygame
from pygame.math import Vector2

from config import (
    ANCHO, ALTO,
    COLOR_NAVE, COLOR_LASER, COLOR_MISIL, COLOR_ENEMIGO,
    VEL_NAVE, ROTACION_SUAVIZADO,
    VELOCIDAD_MISIL, DANIO_MISIL,
    DANIO_LASER,
    VELOCIDAD_BASE_ENEMIGO,
    COOLDOWN_LASER,
    CADENCIA_MISIL,
)
from utils import clamp

logger = logging.getLogger("Naves")


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

    def dibujar(self, pantalla, offset=(0, 0)):
        # Parámetros del láser mejorado
        largo = 30
        ancho_core = 4
        ancho_glow = 6
        separacion = 16

        # Superficie más grande para acomodar el brillo
        surf = pygame.Surface((largo + 30, largo + 30), pygame.SRCALPHA)
        centro = (largo + 30) // 2

        # Calcular ángulo de rotación
        angulo = math.degrees(math.atan2(-self.vel.y, self.vel.x)) - 90

        # Función auxiliar para dibujar un láser individual
        def dibujar_laser(x_centro):
            # Capa 1: Brillo exterior más difuso
            for i in range(4, 0, -1):
                alpha = int(15 * i)
                ancho_actual = ancho_glow + (i * 2)
                rect = pygame.Rect(
                    x_centro - ancho_actual // 2,
                    centro - largo // 2 - 4,
                    ancho_actual,
                    largo + 8
                )
                pygame.draw.rect(surf, (*COLOR_LASER, alpha), rect)

            # Capa 2: Brillo medio
            for i in range(3, 0, -1):
                alpha = int(40 * i)
                ancho_actual = ancho_glow - (i * 1)
                rect = pygame.Rect(
                    x_centro - ancho_actual // 2,
                    centro - largo // 2 - 2,
                    ancho_actual,
                    largo + 4
                )
                pygame.draw.rect(surf, (*COLOR_LASER, alpha), rect)

            # Capa 3: Núcleo brillante con gradiente
            pygame.draw.rect(
                surf,
                (255, 255, 255, 220),
                (x_centro - ancho_core // 2, centro - largo // 2, ancho_core, largo)
            )

            # Capa 4: Centro ultra brillante
            pygame.draw.rect(
                surf,
                (255, 255, 255, 255),
                (x_centro - ancho_core // 2 + 1, centro - largo // 2 + 2, ancho_core - 2, largo - 4)
            )



        # Dibujar ambos láseres
        x1 = centro - separacion // 2
        x2 = centro + separacion // 2

        dibujar_laser(x1)
        dibujar_laser(x2)

        # Rotar y dibujar
        surf_rotada = pygame.transform.rotate(surf, angulo)
        rect = surf_rotada.get_rect(center=(self.pos.x + offset[0], self.pos.y + offset[1]))
        pantalla.blit(surf_rotada, rect)


class Misil:
    def __init__(self, pos, dir_vec):
        self.pos = Vector2(pos)
        if dir_vec.length_squared() == 0:
            dir_vec = Vector2(1, 0)
        self.vel = dir_vec.normalize() * VELOCIDAD_MISIL
        self.radio = 8
        self.danio = DANIO_MISIL
        self.vivo = True
        self.tail_timer = 0.0

    def actualizar(self, dt, particles):
        self.pos += self.vel * dt
        self.tail_timer += dt

        if self.tail_timer > 0.015:
            self.tail_timer = 0.0
            back = self.pos - self.vel.normalize() * 8

            for _ in range(6):
                vel = Vector2(random.uniform(-40, -5), random.uniform(-15, 15)) + -self.vel.normalize() * 30
                particles.append(Particle(
                    back + Vector2(random.uniform(-6, 6), random.uniform(-6, 6)),
                    vel,
                    random.choice([(255, 140, 40), (255, 180, 60), (255, 100, 20)]),
                    random.uniform(1.5, 3), # Ancho
                    random.uniform(0.5, 0.8)
                ))
        if not (0 <= self.pos.x <= ANCHO and 0 <= self.pos.y <= ALTO):
            self.vivo = False

    def dibujar(self, pantalla, offset=(0, 0)):
        # Calcular puntos de inicio y fin de la línea
        dir_norm = self.vel.normalize()
        largo = 20
        end_pos = self.pos + dir_norm * largo

        # Capa 1: Brillo exterior
        for i in range(4, 0, -1):
            alpha = int(30 * i)
            width = 2 + (i * 2)
            pygame.draw.line(
                pantalla,
                (*COLOR_MISIL, alpha),
                (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])),
                (int(end_pos.x + offset[0]), int(end_pos.y + offset[1])),
                width
            )

        # Capa 2: Brillo medio
        for i in range(3, 0, -1):
            alpha = int(80 * i)
            width = 1 + (i * 1)
            pygame.draw.line(
                pantalla,
                (*COLOR_MISIL, alpha),
                (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])),
                (int(end_pos.x + offset[0]), int(end_pos.y + offset[1])),
                width
            )

        # Capa 3: Núcleo brillante
        pygame.draw.line(
            pantalla,
            (255, 255, 255, 200),
            (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])),
            (int(end_pos.x + offset[0]), int(end_pos.y + offset[1])),
            4
        )

        # Capa 4: Centro ultra brillante
        pygame.draw.line(
            pantalla,
            (255, 255, 255, 255),
            (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])),
            (int(end_pos.x + offset[0]), int(end_pos.y + offset[1])),
            2
        )


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

