import os
from pathlib import Path
import random
import sys
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Python_Game'))

import pygame
from pygame.math import Vector2

import config as cfg
from combate import actualizar_combate
from efectos import SistemaEfectos
from entities import MarcadorDanio, Proyectil
from guardado import AlmacenPartida
from interfaz import Interfaz
from main import Aplicacion
from mundo import Camara, desproyectar_vector, elipse_proyectada, proyectar_vector
from render import proyectar_sprite
from test_mecanicas import crear_directorio_temporal, crear_partida_combate


class PruebasProyeccion(unittest.TestCase):
    def test_ejes_forman_diagonales_con_proporcion_dos_a_uno(self) -> None:
        horizontal = proyectar_vector(Vector2(100, 0))
        vertical = proyectar_vector(Vector2(0, 100))
        self.assertAlmostEqual(horizontal.x, 70.710678, places=5)
        self.assertAlmostEqual(horizontal.y, 35.355339, places=5)
        self.assertAlmostEqual(vertical.x, -70.710678, places=5)
        self.assertAlmostEqual(vertical.y, 35.355339, places=5)

    def test_proyeccion_inversa_recupera_vectores_y_coordenadas(self) -> None:
        camara = Camara(Vector2(2380, 4200))
        for x in (-100, 0, 18, 3000, 5982, 6200):
            for y in (-100, 0, 18, 3000, 5982, 6200):
                punto = Vector2(x, y)
                self.assertLess(desproyectar_vector(proyectar_vector(punto)).distance_to(punto), 1e-9)
                self.assertLess(camara.a_mundo(camara.a_pantalla(punto)).distance_to(punto), 1e-9)

    def test_clic_hacia_derecha_mueve_en_los_dos_ejes_logicos(self) -> None:
        partida = crear_partida_combate()
        partida.seleccionar((cfg.ANCHO // 2 + 100, cfg.ALTO // 2))
        self.assertAlmostEqual(partida.nave.destino.x, 1070.710678, places=5)
        self.assertAlmostEqual(partida.nave.destino.y, 929.289322, places=5)
        partida.actualizar(0.05)
        self.assertEqual(partida.camara.a_pantalla(partida.nave.pos), Vector2(683, 384))

    def test_selecciona_enemigos_en_cuatro_direcciones_proyectadas(self) -> None:
        partida = crear_partida_combate()
        enemigo = partida.objetivo
        for desplazamiento in ((100, 0), (0, 100), (-100, 0), (0, -100)):
            enemigo.pos = partida.nave.pos + Vector2(desplazamiento)
            partida.objetivo_id = None
            partida.seleccionar(partida.camara.a_pantalla(enemigo.pos))
            self.assertEqual(partida.objetivo_id, enemigo.identificador)

    def test_circulo_proyectado_es_una_elipse_centrada(self) -> None:
        rectangulo = elipse_proyectada(Vector2(100, 100), 32)
        self.assertEqual((rectangulo.width, rectangulo.height), (64, 32))
        self.assertEqual(rectangulo.center, (100, 100))

    def test_sprite_apunta_hacia_la_direccion_proyectada(self) -> None:
        imagen = pygame.Surface((30, 10), pygame.SRCALPHA)
        pygame.draw.rect(imagen, (255, 0, 0), (24, 2, 6, 6))
        for angulo, vector in ((0, (1, 0)), (90, (0, -1)), (180, (-1, 0)), (270, (0, 1))):
            sprite = proyectar_sprite(imagen, angulo)
            mascara = pygame.mask.from_threshold(sprite, (255, 0, 0, 255), (25, 25, 25, 255))
            punta = Vector2(mascara.centroid()) - Vector2(sprite.get_size()) / 2
            esperado = proyectar_vector(Vector2(vector))
            self.assertGreater(punta.dot(esperado), 0)
            self.assertLess(abs(punta.normalize().cross(esperado.normalize())), 0.15)

    def test_marcadores_suben_en_pantalla_sin_mover_punto_de_impacto(self) -> None:
        marcador = MarcadorDanio(Vector2(1000, 1000), '-20', (255, 0, 0))
        marcador.actualizar(0.2)
        self.assertEqual(marcador.pos, Vector2(1000, 1000))
        self.assertAlmostEqual(marcador.desplazamiento_pantalla, -7)


class PruebasEfectos(unittest.TestCase):
    def test_escudo_registra_contacto_y_normal_del_lado_golpeado(self) -> None:
        partida = crear_partida_combate()
        partida.proyectiles.append(Proyectil(Vector2(950, 1000), Vector2(1000, 0), 20, 'enemigo', 500))
        actualizar_combate(partida, 0.05)
        arco = next(pulso for pulso in partida.efectos.pulsos if pulso.tipo == 'escudo')
        self.assertEqual(arco.direccion, Vector2(-1, 0))
        self.assertTrue(arco.anclado_nave)
        self.assertTrue(any(pulso.pos == Vector2(968, 1000) for pulso in partida.efectos.pulsos))
        self.assertTrue(any(pulso.pos == Vector2(982, 1000) for pulso in partida.efectos.pulsos))
        self.assertEqual((partida.nave.vida, partida.nave.escudo), (96, 84))

    def test_sin_escudo_emite_chispas_de_casco_sin_arco(self) -> None:
        partida = crear_partida_combate()
        partida.nave.escudo = 0
        partida.proyectiles.append(Proyectil(Vector2(950, 1000), Vector2(1000, 0), 20, 'enemigo', 500))
        actualizar_combate(partida, 0.05)
        self.assertTrue(partida.efectos.particulas)
        self.assertFalse(any(pulso.tipo == 'escudo' for pulso in partida.efectos.pulsos))
        self.assertEqual(partida.efectos.pulsos[0].pos, Vector2(982, 1000))

    def test_laser_emite_efecto_en_interseccion_y_no_en_centro_del_enemigo(self) -> None:
        partida = crear_partida_combate()
        partida.proyectiles.append(Proyectil(Vector2(1050, 1000), Vector2(1000, 0), 80, 'laser', 500))
        actualizar_combate(partida, 0.1)
        self.assertEqual(partida.efectos.pulsos[0].pos, Vector2(1082, 1000))
        self.assertEqual(partida.objetivo.vida, 20)

    def test_misil_crea_ondas_fragmentos_y_recompensa_unica(self) -> None:
        partida = crear_partida_combate()
        partida.proyectiles.append(Proyectil(Vector2(1050, 1000), Vector2(1000, 0), 120, 'misil', 500))
        actualizar_combate(partida, 0.1)
        self.assertTrue(any(pulso.tipo == 'onda' and pulso.radio == cfg.RADIO_EXPLOSION
                            for pulso in partida.efectos.pulsos))
        self.assertTrue(any(particula.fragmento for particula in partida.efectos.particulas))
        self.assertEqual((partida.bajas, partida.creditos), (1, 25))

    def test_haz_limita_emisiones_por_tiempo(self) -> None:
        efectos = SistemaEfectos()
        for _ in range(50):
            efectos.impacto_haz(Vector2(1000, 1000), Vector2(1, 0))
        self.assertEqual(len(efectos.particulas), 3)
        efectos.actualizar(cfg.INTERVALO_EFECTO_HAZ_SEGUNDOS)
        efectos.impacto_haz(Vector2(1000, 1000), Vector2(1, 0))
        self.assertEqual(len(efectos.particulas), 6)

    def test_todos_los_efectos_caducan(self) -> None:
        efectos = SistemaEfectos()
        efectos.destruccion(Vector2(1000, 1000))
        efectos.impacto_escudo(Vector2(968, 1000), Vector2(1000, 1000))
        efectos.actualizar(2)
        self.assertFalse(efectos.particulas)
        self.assertFalse(efectos.pulsos)

    def test_explosiones_acumuladas_respetan_limites(self) -> None:
        efectos = SistemaEfectos()
        for _ in range(200):
            efectos.destruccion(Vector2(1000, 1000))
        self.assertEqual(len(efectos.particulas), cfg.MAX_PARTICULAS_IMPACTO)
        self.assertEqual(len(efectos.pulsos), cfg.MAX_PULSOS_IMPACTO)

    def test_efectos_no_alteran_azar_de_la_simulacion(self) -> None:
        estado = random.getstate()
        efectos = SistemaEfectos()
        efectos.destruccion(Vector2(1000, 1000))
        self.assertEqual(random.getstate(), estado)

    def test_emisiones_copian_posicion_sin_modificarla(self) -> None:
        posicion = Vector2(1000, 1000)
        efectos = SistemaEfectos()
        efectos.impacto_casco(posicion, Vector2(1, 0))
        posicion.x = 2000
        self.assertEqual(efectos.pulsos[0].pos, Vector2(1000, 1000))
        self.assertTrue(all(particula.pos == Vector2(1000, 1000) for particula in efectos.particulas))

    def test_dibujar_no_avanza_el_tiempo_ni_acumula_fantasmas(self) -> None:
        efectos = SistemaEfectos()
        efectos.destruccion(Vector2(1000, 1000))
        camara = Camara(Vector2(1000, 1000))
        primera, segunda = pygame.Surface((1366, 768)), pygame.Surface((1366, 768))
        efectos.dibujar(primera, camara, Vector2(1000, 1000))
        efectos.dibujar(segunda, camara, Vector2(1000, 1000))
        self.assertEqual(pygame.image.tobytes(primera, 'RGB'), pygame.image.tobytes(segunda, 'RGB'))
        self.assertTrue(all(particula.edad == 0 for particula in efectos.particulas))
        efectos.actualizar(2)
        segunda.fill((0, 0, 0))
        efectos.dibujar(segunda, camara, Vector2(1000, 1000))
        self.assertFalse(pygame.mask.from_threshold(segunda, (255, 255, 255), (254, 254, 254)).count())

    def test_efectos_no_cambian_formato_ni_datos_guardados(self) -> None:
        temporal = crear_directorio_temporal(self)
        almacen = AlmacenPartida(temporal / 'partida.json')
        partida = crear_partida_combate()
        almacen.guardar(partida)
        anterior = almacen.ruta.read_bytes()
        partida.efectos.destruccion(partida.nave.pos)
        almacen.guardar(partida)
        self.assertEqual(almacen.ruta.read_bytes(), anterior)
        self.assertFalse(almacen.cargar().efectos.particulas)

    def test_muerte_apaga_haz_del_mismo_fotograma(self) -> None:
        partida = crear_partida_combate()
        partida.nave.vida, partida.nave.escudo = 1, 0
        partida.nave.arma, partida.nave.disparo_activo = 3, True
        partida.proyectiles.append(Proyectil(Vector2(950, 1000), Vector2(1000, 0), 20, 'enemigo', 500))
        actualizar_combate(partida, 0.05)
        self.assertFalse(partida.nave.viva)
        self.assertFalse(partida.haz_visible)


class PruebasIntegracionVisual(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = crear_directorio_temporal(self)
        self.addCleanup(pygame.quit)
        self.aplicacion = Aplicacion(AlmacenPartida(self.temporal / 'partida.json'))

    def test_derrota_anima_restos_sin_actualizar_enemigos_ni_regenerar(self) -> None:
        partida = crear_partida_combate()
        partida.nave.vida, partida.nave.escudo = 1, 0
        partida.proyectiles.append(Proyectil(Vector2(950, 1000), Vector2(1000, 0), 20, 'enemigo', 500))
        self.aplicacion.partida, self.aplicacion.estado = partida, 'jugando'
        self.aplicacion.actualizar(0.05)
        self.assertEqual(self.aplicacion.estado, 'derrota')
        self.assertTrue(partida.efectos.particulas)
        enemigo = partida.mundo.enemigos['1:1:0']
        posicion = enemigo.pos.copy()
        self.aplicacion.actualizar(2)
        self.assertEqual(enemigo.pos, posicion)
        self.assertFalse(partida.efectos.particulas)
        self.assertEqual(partida.nave.vida, 0)

    def test_pausa_congela_particulas(self) -> None:
        self.aplicacion.accion('nueva')
        efectos = self.aplicacion.partida.efectos
        efectos.destruccion(self.aplicacion.partida.nave.pos)
        self.aplicacion.accion('pausa')
        self.aplicacion.actualizar(0.5)
        self.assertTrue(all(particula.edad == 0 for particula in efectos.particulas))

    def test_minimapa_restaura_el_recorte_de_la_superficie(self) -> None:
        interfaz = Interfaz()
        superficie = pygame.Surface((cfg.ANCHO, cfg.ALTO))
        recorte = pygame.Rect(100, 100, 1200, 600)
        superficie.set_clip(recorte)
        interfaz._dibujar_vista_minimapa(superficie, crear_partida_combate())
        self.assertEqual(superficie.get_clip(), recorte)

    def test_render_con_efectos_y_figuras_de_respaldo(self) -> None:
        self.aplicacion.accion('nueva')
        self.aplicacion.recursos['jugador'] = None
        self.aplicacion.recursos['enemigo'] = None
        partida = self.aplicacion.partida
        partida.efectos.explosion_misil(partida.nave.pos + Vector2(100, 0))
        partida.efectos.impacto_escudo(partida.nave.pos - Vector2(32, 0), partida.nave.pos)
        self.aplicacion.dibujar()
        self.assertEqual(self.aplicacion.pantalla.get_size(), (1366, 768))


if __name__ == '__main__':
    unittest.main()
