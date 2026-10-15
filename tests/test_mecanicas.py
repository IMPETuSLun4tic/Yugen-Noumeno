import json
import os
from pathlib import Path
import sys
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Python_Game'))

import pygame
from pygame.math import Vector2

import config as cfg
from combate import actualizar_combate, fraccion_impacto
from entities import Enemigo, Nave, Proyectil
from guardado import AlmacenPartida, ErrorGuardado, MAX_BYTES_GUARDADO
from logic import RECTANGULO_MINIMAPA, manejar_evento_juego
from main import Aplicacion
from mundo import Camara, Mundo, en_base
from partida import Partida
from tienda import comprar


def crear_directorio_temporal(prueba: unittest.TestCase) -> Path:
    raiz = Path(__file__).resolve().parent
    ruta = raiz / ('temporal_' + uuid4().hex)
    ruta.mkdir()
    prueba.addCleanup(limpiar_directorio_temporal, ruta, raiz)
    return ruta


def limpiar_directorio_temporal(ruta: Path, raiz: Path) -> None:
    if ruta.resolve().parent != raiz or not ruta.name.startswith('temporal_'):
        raise ValueError('El directorio temporal debe estar dentro de tests')
    shutil.rmtree(ruta)


def crear_partida_combate() -> Partida:
    partida = Partida(nave=Nave(Vector2(1000, 1000)), mundo=Mundo(7))
    enemigo = Enemigo('1:1:0', Vector2(1100, 1000), Vector2(1100, 1000), tiempo_disparo=1)
    partida.mundo.sectores_generados.add((1, 1))
    partida.mundo.enemigos[enemigo.identificador] = enemigo
    partida.mundo.activos.append(enemigo)
    partida.objetivo_id = enemigo.identificador
    return partida


class PruebasDefensas(unittest.TestCase):
    def test_impacto_reparte_danio_ochenta_veinte(self) -> None:
        nave = Nave(Vector2(1000, 1000))
        resultado = nave.recibir_danio(20)
        self.assertEqual((resultado.escudo, resultado.vida), (16, 4))
        self.assertEqual((nave.escudo, nave.vida), (84, 96))
        self.assertGreater(nave.tiempo_impacto, 0)

    def test_escudo_insuficiente_transfiere_el_resto_a_vida(self) -> None:
        nave = Nave(Vector2(1000, 1000), escudo=5)
        nave.recibir_danio(20)
        self.assertEqual((nave.escudo, nave.vida), (0, 85))

    def test_sin_escudo_todo_el_danio_va_a_vida(self) -> None:
        nave = Nave(Vector2(1000, 1000), escudo=0)
        nave.recibir_danio(20)
        self.assertEqual(nave.vida, 80)

    def test_muerte_limita_vida_y_no_admite_mas_danio(self) -> None:
        nave = Nave(Vector2(1000, 1000), vida=3, escudo=0)
        nave.recibir_danio(20)
        self.assertFalse(nave.viva)
        self.assertEqual(nave.recibir_danio(20).vida, 0)
        self.assertEqual(nave.vida, 0)

    def test_regeneracion_empieza_despues_de_cinco_segundos(self) -> None:
        nave = Nave(Vector2(1000, 1000), vida=50, escudo=20)
        nave.regenerar(5)
        self.assertEqual((nave.vida, nave.escudo), (50, 20))
        nave.regenerar(1)
        self.assertEqual((nave.vida, nave.escudo), (55, 30))

    def test_regeneracion_calcula_fraccion_del_umbral(self) -> None:
        nave = Nave(Vector2(1000, 1000), vida=50, escudo=20, tiempo_sin_combate=4.8)
        nave.regenerar(0.4)
        self.assertAlmostEqual(nave.vida, 51)
        self.assertAlmostEqual(nave.escudo, 22)

    def test_regeneracion_no_supera_maximos_ni_resucita(self) -> None:
        nave = Nave(Vector2(1000, 1000), vida=99, escudo=99)
        nave.regenerar(100)
        self.assertEqual((nave.vida, nave.escudo), (100, 100))
        nave.vida = 0
        nave.regenerar(100)
        self.assertEqual(nave.vida, 0)

    def test_recibir_danio_reinicia_espera(self) -> None:
        nave = Nave(Vector2(1000, 1000), tiempo_sin_combate=10)
        nave.recibir_danio(20)
        nave.regenerar(1)
        self.assertEqual(nave.vida, 96)

    def test_danio_invalido_se_rechaza(self) -> None:
        for cantidad in (-1, float('nan'), float('inf')):
            with self.subTest(cantidad=cantidad), self.assertRaises(ValueError):
                Nave(Vector2(1000, 1000)).recibir_danio(cantidad)


class PruebasMovimiento(unittest.TestCase):
    def test_destino_no_produce_sobrepaso(self) -> None:
        nave = Nave(Vector2(1000, 1000))
        nave.mover_a(Vector2(1010, 1000))
        nave.actualizar(1)
        self.assertEqual(nave.pos, Vector2(1010, 1000))

    def test_destino_se_limita_al_mundo(self) -> None:
        nave = Nave(Vector2(1000, 1000))
        nave.mover_a(Vector2(-100, 7000))
        self.assertEqual(nave.destino, Vector2(18, 5982))

    def test_camara_centra_al_jugador_incluso_en_bordes(self) -> None:
        camara = Camara()
        for posicion in (Vector2(18, 18), Vector2(5982, 5982), Vector2(3000, 3000)):
            camara.seguir(posicion)
            self.assertEqual(camara.a_pantalla(posicion), Vector2(cfg.ANCHO / 2, cfg.ALTO / 2))
            self.assertEqual(camara.a_mundo(camara.a_pantalla(posicion)), posicion)

    def test_clic_en_enemigo_selecciona_sin_mover_destino(self) -> None:
        partida = crear_partida_combate()
        partida.objetivo_id = None
        posicion = partida.camara.a_pantalla(partida.mundo.activos[0].pos)
        partida.seleccionar(posicion)
        self.assertEqual(partida.objetivo_id, '1:1:0')
        self.assertEqual(partida.nave.destino, partida.nave.pos)

    def test_clic_vacio_convierte_coordenadas_y_fija_destino(self) -> None:
        partida = crear_partida_combate()
        partida.seleccionar((cfg.ANCHO // 2, cfg.ALTO // 2 + 100))
        self.assertAlmostEqual(partida.nave.destino.x, 1141.421356, places=5)
        self.assertAlmostEqual(partida.nave.destino.y, 1141.421356, places=5)

    def test_clic_en_minimapa_no_mueve_la_nave(self) -> None:
        partida = crear_partida_combate()
        evento = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=RECTANGULO_MINIMAPA.center)
        manejar_evento_juego(evento, partida)
        self.assertEqual(partida.nave.destino, partida.nave.pos)


class PruebasCombate(unittest.TestCase):
    def test_slots_seleccionan_y_repetir_alterna_disparo(self) -> None:
        nave = Nave(Vector2(1000, 1000))
        nave.seleccionar_arma(1)
        self.assertFalse(nave.disparo_activo)
        nave.seleccionar_arma(1)
        self.assertTrue(nave.disparo_activo)
        nave.seleccionar_arma(1)
        self.assertFalse(nave.disparo_activo)
        nave.seleccionar_arma(2)
        self.assertFalse(nave.disparo_activo)
        self.assertEqual(nave.arma, 2)

    def test_disparo_respeta_cadencia_y_reinicia_combate(self) -> None:
        partida = crear_partida_combate()
        partida.nave.arma, partida.nave.disparo_activo = 1, True
        actualizar_combate(partida, 0.01)
        actualizar_combate(partida, 0.01)
        self.assertEqual(len(partida.proyectiles), 1)
        self.assertTrue(partida.nave.hubo_combate)
        self.assertEqual(partida.nave.tiempo_sin_combate, 0)

    def test_disparo_espera_hasta_entrar_en_alcance(self) -> None:
        partida = crear_partida_combate()
        partida.objetivo.pos = Vector2(1900, 1000)
        partida.nave.arma, partida.nave.disparo_activo = 1, True
        actualizar_combate(partida, 0.01)
        self.assertFalse(partida.proyectiles)
        self.assertTrue(partida.nave.disparo_activo)
        partida.objetivo.pos = Vector2(1500, 1000)
        actualizar_combate(partida, 0.01)
        self.assertEqual(len(partida.proyectiles), 1)

    def test_proyectil_impacta_una_sola_vez_y_creditos_no_se_duplican(self) -> None:
        partida = crear_partida_combate()
        partida.proyectiles = [Proyectil(Vector2(1050, 1000), Vector2(1000, 0), 120, 'laser', 500)
                               for _ in range(2)]
        actualizar_combate(partida, 0.1)
        self.assertEqual((partida.bajas, partida.creditos), (1, cfg.CREDITOS_POR_BAJA))

    def test_proyectil_rapido_no_atraviesa_enemigos(self) -> None:
        self.assertIsNotNone(fraccion_impacto(Vector2(0, 0), Vector2(1000, 0), Vector2(500, 0), 18))
        self.assertIsNone(fraccion_impacto(Vector2(0, 0), Vector2(1000, 0), Vector2(500, 30), 18))

    def test_enemigos_disparan_veinte_con_cadencia(self) -> None:
        partida = crear_partida_combate()
        partida.objetivo.tiempo_disparo = 0
        actualizar_combate(partida, 0.001)
        proyectil = partida.proyectiles[0]
        self.assertEqual((proyectil.tipo, proyectil.danio), ('enemigo', 20))
        actualizar_combate(partida, 0.001)
        self.assertEqual(len(partida.proyectiles), 1)

    def test_impacto_en_burbuja_aplica_danio_y_marcadores(self) -> None:
        partida = crear_partida_combate()
        partida.proyectiles.append(Proyectil(Vector2(950, 1000), Vector2(1000, 0), 20, 'enemigo', 500))
        actualizar_combate(partida, 0.05)
        self.assertEqual((partida.nave.escudo, partida.nave.vida), (84, 96))
        self.assertEqual(len(partida.marcadores), 2)
        self.assertFalse(partida.proyectiles)

    def test_contacto_no_mata_de_un_golpe(self) -> None:
        partida = crear_partida_combate()
        partida.objetivo.pos = partida.nave.pos.copy()
        actualizar_combate(partida, 0.05)
        self.assertEqual(partida.nave.vida, 100)

    def test_misil_aplica_danio_en_area(self) -> None:
        partida = crear_partida_combate()
        segundo = Enemigo('1:1:1', Vector2(1150, 1000), Vector2(1150, 1000), tiempo_disparo=1)
        partida.mundo.enemigos[segundo.identificador] = segundo
        partida.mundo.activos.append(segundo)
        partida.proyectiles.append(Proyectil(Vector2(1000, 1000), Vector2(1000, 0), 120, 'misil', 500))
        actualizar_combate(partida, 0.1)
        self.assertEqual(partida.bajas, 2)

    def test_haz_causa_danio_continuo_y_pararlo_inicia_recarga(self) -> None:
        partida = crear_partida_combate()
        partida.nave.arma, partida.nave.disparo_activo = 3, True
        actualizar_combate(partida, 0.1)
        self.assertAlmostEqual(partida.objetivo.vida, 74)
        self.assertTrue(partida.haz_visible)
        partida.nave.seleccionar_arma(2)
        self.assertEqual(partida.nave.enfriamiento_haz, 3)

    def test_perder_objetivo_cancela_disparo(self) -> None:
        partida = crear_partida_combate()
        partida.nave.arma, partida.nave.disparo_activo = 1, True
        partida.mundo.activos.clear()
        actualizar_combate(partida, 0.1)
        self.assertFalse(partida.nave.disparo_activo)
        self.assertIsNone(partida.objetivo_id)

    def test_impacto_de_proyectil_en_vuelo_reinicia_combate(self) -> None:
        partida = crear_partida_combate()
        partida.nave.tiempo_sin_combate = 5
        partida.proyectiles.append(Proyectil(Vector2(1050, 1000), Vector2(1000, 0), 80, 'laser', 500))
        actualizar_combate(partida, 0.1)
        self.assertEqual(partida.nave.tiempo_sin_combate, 0)
        self.assertTrue(partida.nave.hubo_combate)


class PruebasMundoYTienda(unittest.TestCase):
    def test_solo_activa_enemigos_proximos_y_limita_cantidad(self) -> None:
        mundo = Mundo(7)
        posicion = Vector2(1500, 1500)
        mundo.actualizar(posicion, 0)
        self.assertLess(len(mundo.sectores_generados), 64)
        self.assertLessEqual(len(mundo.activos), 25)
        self.assertTrue(all(enemigo.pos.distance_to(posicion) <= cfg.RADIO_ACTIVACION for enemigo in mundo.activos))

    def test_alejarse_y_volver_no_restaura_vida_ni_enemigos_muertos(self) -> None:
        mundo = Mundo(7)
        posicion = Vector2(1500, 1500)
        mundo.actualizar(posicion, 0)
        herido, muerto = mundo.activos[:2]
        herido.recibir_danio(25)
        muerto.recibir_danio(100)
        mundo.actualizar(Vector2(5800, 5800), 1)
        mundo.actualizar(posicion, 0)
        self.assertEqual(herido.vida, 75)
        self.assertEqual(muerto.vida, 0)
        self.assertNotIn(muerto, mundo.activos)

    def test_enemigos_lejanos_conservan_posicion_y_temporizadores(self) -> None:
        partida = crear_partida_combate()
        enemigo = partida.objetivo
        posicion = enemigo.pos.copy()
        partida.mundo.actualizar(Vector2(5800, 5800), 1)
        self.assertEqual(enemigo.pos, posicion)
        self.assertEqual(enemigo.tiempo_disparo, 1)

    def test_base_no_genera_ni_admite_enemigos(self) -> None:
        mundo = Mundo(7)
        posicion = Vector2(cfg.POSICION_BASE)
        mundo.actualizar(posicion, 0)
        self.assertTrue(all(not en_base(enemigo.pos, enemigo.radio) for enemigo in mundo.enemigos.values()))
        enemigo = mundo.activos[0]
        enemigo.pos = posicion.copy()
        mundo.actualizar(posicion, 0)
        self.assertFalse(en_base(enemigo.pos, enemigo.radio))

    def test_base_bloquea_armas_y_proyectiles(self) -> None:
        partida = Partida()
        partida.nave.arma, partida.nave.disparo_activo = 1, True
        partida.proyectiles.append(Proyectil(partida.nave.pos.copy(), Vector2(1, 0), 20, 'enemigo', 50))
        actualizar_combate(partida, 0.1)
        self.assertEqual((partida.nave.vida, partida.nave.escudo), (100, 100))
        self.assertFalse(partida.proyectiles)
        self.assertFalse(partida.nave.disparo_activo)

    def test_base_intercepta_disparos_que_la_cruzan(self) -> None:
        partida = crear_partida_combate()
        partida.nave.pos = Vector2(2200, 3000)
        enemigo = partida.objetivo
        enemigo.pos = Vector2(3700, 3000)
        partida.proyectiles.append(Proyectil(Vector2(2300, 3000), Vector2(30000, 0), 100, 'laser', 2000))
        actualizar_combate(partida, 0.05)
        self.assertEqual(enemigo.vida, 100)
        self.assertFalse(partida.proyectiles)

    def test_comprar_descuenta_creditos_y_aumenta_maximo(self) -> None:
        partida = Partida(creditos=100)
        comprar(partida, 'escudo')
        self.assertEqual((partida.creditos, partida.mejoras.escudo), (25, 1))
        self.assertEqual((partida.nave.escudo, partida.nave.escudo_maximo), (100, 120))

    def test_comprar_requiere_creditos_base_y_nivel_disponible(self) -> None:
        partida = crear_partida_combate()
        partida.creditos = 10000
        comprar(partida, 'laser')
        self.assertEqual(partida.mejoras.laser, 0)
        partida.nave.pos = Vector2(cfg.POSICION_BASE)
        partida.creditos = 0
        comprar(partida, 'laser')
        self.assertEqual(partida.mejoras.laser, 0)
        partida.creditos = 10000
        for _ in range(6):
            comprar(partida, 'laser')
        self.assertEqual(partida.mejoras.laser, 5)
        self.assertEqual(partida.creditos, 10000 - sum(75 * nivel for nivel in range(1, 6)))


class PruebasGuardado(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = crear_directorio_temporal(self)
        self.almacen = AlmacenPartida(self.temporal / 'partidas' / 'partida.json')

    def test_guardar_y_cargar_restaura_progreso_y_enemigo_herido(self) -> None:
        partida = crear_partida_combate()
        partida.objetivo.recibir_danio(40)
        partida.nave.recibir_danio(20)
        partida.nave.mover_a(Vector2(1200, 1200))
        partida.creditos, partida.bajas = 250, 10
        self.almacen.guardar(partida)
        cargada = self.almacen.cargar()
        self.assertEqual((cargada.creditos, cargada.bajas), (250, 10))
        self.assertEqual(cargada.nave.destino, Vector2(1200, 1200))
        self.assertEqual((cargada.nave.vida, cargada.nave.escudo), (96, 84))
        self.assertEqual(cargada.mundo.enemigos['1:1:0'].vida, 60)
        self.assertEqual(cargada.mundo.semilla, 7)
        self.assertFalse(cargada.nave.disparo_activo)

    def test_mejoras_se_restauran_sin_recuperacion_gratuita(self) -> None:
        partida = Partida(creditos=300)
        comprar(partida, 'vida')
        partida.nave.vida = 70
        self.almacen.guardar(partida)
        cargada = self.almacen.cargar()
        self.assertEqual((cargada.mejoras.vida, cargada.nave.vida_maxima, cargada.nave.vida), (1, 120, 70))

    def test_haz_activo_se_carga_detenido_con_enfriamiento(self) -> None:
        partida = crear_partida_combate()
        partida.nave.arma, partida.nave.disparo_activo, partida.nave.tiempo_haz = 3, True, 2
        self.almacen.guardar(partida)
        cargada = self.almacen.cargar()
        self.assertFalse(cargada.nave.disparo_activo)
        self.assertEqual((cargada.nave.tiempo_haz, cargada.nave.enfriamiento_haz), (0, 3))

    def test_guardado_muerto_no_resucita(self) -> None:
        partida = Partida()
        partida.nave.vida = 0
        self.almacen.guardar(partida)
        self.assertFalse(self.almacen.cargar().nave.viva)

    def test_guardado_inexistente_o_roto_informa_error(self) -> None:
        with self.assertRaises(ErrorGuardado):
            self.almacen.cargar()
        self.almacen.ruta.parent.mkdir()
        self.almacen.ruta.write_text('{invalido', encoding='utf-8')
        with self.assertRaises(ErrorGuardado):
            self.almacen.cargar()

    def test_rechaza_version_incompatible_campos_ausentes_y_numeros_invalidos(self) -> None:
        self.almacen.guardar(Partida())
        original = json.loads(self.almacen.ruta.read_text(encoding='utf-8'))
        cambios = [('version', 99), ('creditos', True), ('bajas', -1), ('semilla', float('nan'))]
        for campo, valor in cambios:
            datos = dict(original, **{campo: valor})
            self.almacen.ruta.write_text(json.dumps(datos), encoding='utf-8')
            with self.subTest(campo=campo), self.assertRaises(ErrorGuardado):
                self.almacen.cargar()
        original.pop('nave')
        self.almacen.ruta.write_text(json.dumps(original), encoding='utf-8')
        with self.assertRaises(ErrorGuardado):
            self.almacen.cargar()

    def test_rechaza_enemigos_duplicados_o_dentro_de_base(self) -> None:
        self.almacen.guardar(crear_partida_combate())
        datos = json.loads(self.almacen.ruta.read_text(encoding='utf-8'))
        datos['enemigos'].append(dict(datos['enemigos'][0]))
        self.almacen.ruta.write_text(json.dumps(datos), encoding='utf-8')
        with self.assertRaises(ErrorGuardado):
            self.almacen.cargar()
        datos['enemigos'].pop()
        datos['enemigos'][0]['pos'] = list(cfg.POSICION_BASE)
        self.almacen.ruta.write_text(json.dumps(datos), encoding='utf-8')
        with self.assertRaises(ErrorGuardado):
            self.almacen.cargar()

    def test_archivo_demasiado_grande_se_rechaza(self) -> None:
        self.almacen.ruta.parent.mkdir()
        self.almacen.ruta.write_bytes(b' ' * (MAX_BYTES_GUARDADO + 1))
        with self.assertRaises(ErrorGuardado):
            self.almacen.cargar()

    def test_json_con_entero_excesivo_se_rechaza_sin_cerrar(self) -> None:
        self.almacen.ruta.parent.mkdir()
        self.almacen.ruta.write_text('{"version":' + '9' * 5000 + '}', encoding='utf-8')
        with self.assertRaises(ErrorGuardado):
            self.almacen.cargar()

    def test_escritura_fallida_conserva_guardado_anterior(self) -> None:
        self.almacen.guardar(Partida(creditos=25))
        with patch.object(Path, 'replace', side_effect=OSError('Fallo simulado')):
            with self.assertRaises(ErrorGuardado):
                self.almacen.guardar(Partida(creditos=50))
        self.assertEqual(self.almacen.cargar().creditos, 25)


class PruebasAplicacion(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = crear_directorio_temporal(self)
        self.addCleanup(pygame.quit)
        self.almacen = AlmacenPartida(self.temporal / 'partida.json')
        self.aplicacion = Aplicacion(self.almacen)

    def test_menu_nueva_pausa_guardar_y_cargar(self) -> None:
        aplicacion = self.aplicacion
        self.assertEqual(aplicacion.estado, 'inicio')
        aplicacion.accion('nueva')
        aplicacion.actualizar(0.05)
        aplicacion.partida.nave.mover_a(Vector2(3400, 3000))
        aplicacion.accion('pausa')
        posicion = aplicacion.partida.nave.pos.copy()
        aplicacion.actualizar(1)
        self.assertEqual(aplicacion.partida.nave.pos, posicion)
        aplicacion.accion('guardar')
        aplicacion.accion('cargar')
        self.assertEqual(aplicacion.estado, 'jugando')

    def test_cierre_autoguarda_y_puede_cargarse(self) -> None:
        self.aplicacion.accion('nueva')
        self.aplicacion.partida.creditos = 50
        self.aplicacion.procesar_evento(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.aplicacion.en_ejecucion)
        self.assertEqual(self.almacen.cargar().creditos, 50)

    def test_fallo_de_guardado_no_cierra_y_permite_decidir(self) -> None:
        self.aplicacion.accion('nueva')
        with patch.object(self.almacen, 'guardar', side_effect=ErrorGuardado('Fallo simulado')):
            self.aplicacion.accion('salir')
        self.assertTrue(self.aplicacion.en_ejecucion)
        self.assertEqual(self.aplicacion.estado, 'error_salida')
        self.aplicacion.accion('salir_sin_guardar')
        self.assertFalse(self.aplicacion.en_ejecucion)

    def test_nueva_con_guardado_pide_confirmacion_sin_borrarlo(self) -> None:
        self.almacen.guardar(Partida(creditos=50))
        self.aplicacion.accion('nueva')
        self.assertEqual(self.aplicacion.estado, 'confirmar_nueva')
        self.aplicacion.accion('confirmar')
        self.assertEqual(self.aplicacion.partida.creditos, 0)
        self.assertEqual(self.almacen.cargar().creditos, 50)

    def test_carga_invalida_no_reemplaza_partida_actual(self) -> None:
        self.aplicacion.accion('nueva')
        original = self.aplicacion.partida
        self.almacen.ruta.write_text('{}', encoding='utf-8')
        self.aplicacion.accion('cargar')
        self.assertIs(self.aplicacion.partida, original)
        self.assertIn('version', self.aplicacion.mensaje)

    def test_renderiza_todos_los_menus_y_escena(self) -> None:
        self.aplicacion.dibujar()
        self.aplicacion.accion('nueva')
        self.aplicacion.actualizar(0.05)
        for estado in ('jugando', 'pausa', 'tienda', 'derrota', 'confirmar_nueva', 'error_salida'):
            self.aplicacion.estado = estado
            self.aplicacion.dibujar()
        self.assertEqual(self.aplicacion.pantalla.get_size(), (cfg.ANCHO, cfg.ALTO))

    def test_bucle_real_procesa_menu_y_autoguarda_al_cerrar(self) -> None:
        nueva = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(683, 318))
        cerrar = pygame.event.Event(pygame.QUIT)
        with patch.object(pygame.event, 'get', side_effect=[[nueva], [], [cerrar]]):
            self.aplicacion.ejecutar()
        self.assertFalse(self.aplicacion.en_ejecucion)
        self.assertTrue(self.almacen.cargar().nave.viva)


if __name__ == '__main__':
    unittest.main()
