import logging
import os

import pygame

import config as cfg
from guardado import AlmacenPartida, ErrorGuardado
from interfaz import Interfaz
from logic import manejar_evento_juego
from mundo import proyectar_vector
from partida import Partida
from performance import PerformanceMonitor
from render import dibujar_escena
from resources import cargar_recursos, crear_fondo
from tienda import comprar
from utils import apply_bloom

logger = logging.getLogger('Naves')


class Aplicacion:
    def __init__(self, almacen: AlmacenPartida | None = None) -> None:
        os.environ.setdefault('SDL_VIDEO_CENTERED', '1')
        pygame.display.init()
        pygame.font.init()
        self._iniciar_audio()
        self.pantalla = pygame.display.set_mode((cfg.ANCHO, cfg.ALTO), pygame.DOUBLEBUF)
        pygame.display.set_caption('Yugen-Noumeno')
        self.escena = pygame.Surface((cfg.ANCHO, cfg.ALTO))
        self.reloj = pygame.time.Clock()
        self.monitor = PerformanceMonitor()
        self.recursos = cargar_recursos()
        self.fondo = crear_fondo(self.recursos)
        self.interfaz = Interfaz()
        self.almacen = almacen if almacen is not None else AlmacenPartida()
        self.partida: Partida | None = None
        self.estado = 'inicio'
        self.estado_anterior = 'inicio'
        self.mensaje = ''
        self.en_ejecucion = True

    def _iniciar_audio(self) -> None:
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except pygame.error as error:
            logger.warning('Audio no disponible: %s', error)

    def ejecutar(self) -> None:
        try:
            while self.en_ejecucion:
                dt = min(self.reloj.tick(cfg.FPS) / 1000.0, cfg.PASO_MAXIMO_SEGUNDOS)
                for evento in pygame.event.get():
                    self.procesar_evento(evento)
                    if not self.en_ejecucion:
                        break
                if self.en_ejecucion:
                    self.actualizar(dt)
                    self.dibujar()
        finally:
            pygame.quit()

    def procesar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.QUIT:
            self._salir()
            return
        if self.estado == 'jugando':
            accion = manejar_evento_juego(evento, self.partida)
            if accion:
                self.accion(accion)
            return
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
            self._volver()
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self._pulsar_boton(evento.pos)

    def _pulsar_boton(self, posicion: tuple[int, int]) -> None:
        botones = self.interfaz.botones(self.estado, self.partida, self.almacen.ruta.exists())
        for boton in botones:
            if boton.habilitado and boton.rectangulo.collidepoint(posicion):
                self.accion(boton.accion)
                return

    def accion(self, accion: str) -> None:
        self.mensaje = ''
        if accion.startswith('comprar_'):
            self.mensaje = comprar(self.partida, accion.removeprefix('comprar_'))
            return
        acciones = {
            'nueva': self._pedir_nueva, 'confirmar': self._nueva,
            'cancelar': self._volver, 'cargar': self._cargar,
            'guardar': self._guardar, 'salir': self._salir,
            'reanudar': self._reanudar, 'pausa': self._pausar,
            'tienda': self._abrir_tienda, 'cancelar_salida': self._volver,
            'salir_sin_guardar': self._salir_sin_guardar,
        }
        acciones[accion]()

    def _pedir_nueva(self) -> None:
        if self.almacen.ruta.exists() or self.partida is not None:
            self.estado_anterior = self.estado
            self.estado = 'confirmar_nueva'
        else:
            self._nueva()

    def _nueva(self) -> None:
        self.partida = Partida()
        self.partida.mundo.actualizar(self.partida.nave.pos, 0.0)
        self.estado = 'jugando'

    def _cargar(self) -> None:
        try:
            partida = self.almacen.cargar()
        except ErrorGuardado as error:
            logger.warning('Carga rechazada: %s', error)
            self.mensaje = str(error)
            return
        self.partida = partida
        self.estado = 'jugando' if partida.nave.viva else 'derrota'

    def _guardar(self) -> bool:
        if self.partida is None:
            return True
        try:
            self.almacen.guardar(self.partida)
        except ErrorGuardado as error:
            logger.warning('Guardado rechazado: %s', error)
            self.mensaje = str(error)
            return False
        self.mensaje = 'Partida guardada.'
        return True

    def _salir(self) -> None:
        if self._guardar():
            self.en_ejecucion = False
        else:
            if self.estado != 'error_salida':
                self.estado_anterior = self.estado
            self.estado = 'error_salida'
            if self.partida is not None:
                self.partida.nave.detener_disparo()

    def _salir_sin_guardar(self) -> None:
        self.en_ejecucion = False

    def _pausar(self) -> None:
        self.partida.nave.detener_disparo()
        if pygame.mixer.get_init():
            pygame.mixer.stop()
        self.estado = 'pausa'

    def _abrir_tienda(self) -> None:
        self.partida.preparar_base()
        self.partida.nave.destino = self.partida.nave.pos.copy()
        self.estado = 'tienda'

    def _reanudar(self) -> None:
        self.estado = 'jugando' if self.partida.nave.viva else 'derrota'

    def _volver(self) -> None:
        if self.estado in ('pausa', 'tienda'):
            self._reanudar()
        elif self.estado in ('confirmar_nueva', 'error_salida'):
            self.estado = self.estado_anterior
        self.mensaje = ''

    def actualizar(self, dt: float) -> None:
        self.monitor.update()
        if self.estado == 'derrota':
            self.partida.actualizar_visuales(dt)
            return
        if self.estado != 'jugando':
            return
        self.partida.actualizar(dt)
        for grupo in self.fondo.values():
            for elemento in grupo:
                elemento.actualizar(dt, proyectar_vector(self.partida.nave.vel))
        self._reproducir_audio()
        if not self.partida.nave.viva:
            self.estado = 'derrota'

    def _reproducir_audio(self) -> None:
        for nombre in set(self.partida.eventos_audio):
            sonido = self.recursos.get(nombre)
            if sonido is not None:
                try:
                    sonido.play()
                except pygame.error as error:
                    logger.warning('No se pudo reproducir %s: %s', nombre, error)
        self.partida.eventos_audio.clear()

    def dibujar(self) -> None:
        if self.partida is None:
            self.escena.fill(cfg.COLOR_FONDO_BASE)
            for estrella in self.fondo['stars']:
                estrella.dibujar(self.escena)
        else:
            dibujar_escena(self.escena, self.partida, self.fondo, self.recursos)
        self.pantalla.blit(self.escena, (0, 0))
        self.pantalla.blit(apply_bloom(self.escena), (0, 0), special_flags=pygame.BLEND_ADD)
        if self.partida is not None:
            self.interfaz.dibujar_hud(self.pantalla, self.partida, self.reloj.get_fps())
        if self.estado != 'jugando':
            self.interfaz.dibujar_menu(self.pantalla, self.estado, self.partida,
                                       self.almacen.ruta.exists(), self.mensaje)
        pygame.display.flip()


def ejecutar() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    Aplicacion().ejecutar()


if __name__ == '__main__':
    ejecutar()
