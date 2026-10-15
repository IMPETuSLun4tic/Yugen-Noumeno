from dataclasses import dataclass

import pygame
from pygame.math import Vector2

import config as cfg
from logic import RECTANGULO_MINIMAPA
from mundo import en_base
from partida import Partida
from render import dibujar_marcadores


@dataclass(frozen=True)
class Boton:
    accion: str
    texto: str
    rectangulo: pygame.Rect
    habilitado: bool = True


class Interfaz:
    def __init__(self) -> None:
        self.fuentes = {
            'pequena': pygame.font.SysFont('segoeui', 16),
            'normal': pygame.font.SysFont('segoeui', 20),
            'titulo': pygame.font.SysFont('segoeui', 46, bold=True),
        }

    def texto(self, superficie: pygame.Surface, texto: str, posicion: tuple,
              color: tuple = (210, 230, 240), fuente: str = 'normal') -> None:
        superficie.blit(self.fuentes[fuente].render(texto, True, color), posicion)

    def dibujar_hud(self, superficie: pygame.Surface, partida: Partida, fps: float) -> None:
        self._dibujar_defensas(superficie, partida)
        self._dibujar_minimapa(superficie, partida)
        self._dibujar_armas(superficie, partida)
        self._dibujar_objetivo(superficie, partida)
        dibujar_marcadores(superficie, partida, self.fuentes['normal'])
        self.texto(superficie, f'{fps:.0f} FPS  |  {partida.nave.pos.x:.0f}, {partida.nave.pos.y:.0f}',
                   (cfg.ANCHO - 220, cfg.ALTO - 30), fuente='pequena')

    def _dibujar_defensas(self, superficie: pygame.Surface, partida: Partida) -> None:
        nave = partida.nave
        _panel(superficie, pygame.Rect(20, 20, 305, 156))
        self.texto(superficie, 'NAVE / EXPLORACION', (36, 30), (95, 215, 235), 'pequena')
        self._barra(superficie, 'VIDA', nave.vida, nave.vida_maxima, 61, (110, 225, 155))
        self._barra(superficie, 'ESCUDO', nave.escudo, nave.escudo_maximo, 96, (90, 175, 255))
        self.texto(superficie, f'{partida.creditos} creditos  |  {partida.bajas} bajas', (36, 139), fuente='pequena')

    def _barra(self, superficie: pygame.Surface, nombre: str, valor: float,
               maximo: float, y: int, color: tuple) -> None:
        self.texto(superficie, f'{nombre}  {valor:.0f} / {maximo:.0f}', (36, y - 1), color, 'pequena')
        pygame.draw.rect(superficie, (25, 43, 60), (36, y + 21, 272, 5), border_radius=2)
        pygame.draw.rect(superficie, color, (36, y + 21, 272 * max(0, valor) / maximo, 5), border_radius=2)

    def _dibujar_minimapa(self, superficie: pygame.Surface, partida: Partida) -> None:
        rectangulo = RECTANGULO_MINIMAPA
        _panel(superficie, rectangulo)
        base = self._punto_minimapa(Vector2(cfg.POSICION_BASE))
        radio = max(1, round(cfg.RADIO_BASE / cfg.ANCHO_MUNDO * rectangulo.width))
        pygame.draw.circle(superficie, (35, 100, 100), base, radio)
        pygame.draw.circle(superficie, (110, 240, 210), base, 4)
        for enemigo in partida.mundo.activos:
            if enemigo.vivo:
                pygame.draw.circle(superficie, (250, 115, 110), self._punto_minimapa(enemigo.pos), 2)
        pygame.draw.circle(superficie, (220, 245, 255), self._punto_minimapa(partida.nave.pos), 4)
        self._dibujar_vista_minimapa(superficie, partida)
        self.texto(superficie, 'MAPA  /  6000 x 6000', (rectangulo.x, rectangulo.bottom + 5), fuente='pequena')

    def _punto_minimapa(self, posicion: Vector2) -> tuple[int, int]:
        rectangulo = RECTANGULO_MINIMAPA.inflate(-8, -8)
        return (round(rectangulo.x + posicion.x / cfg.ANCHO_MUNDO * rectangulo.width),
                round(rectangulo.y + posicion.y / cfg.ALTO_MUNDO * rectangulo.height))

    def _dibujar_vista_minimapa(self, superficie: pygame.Surface, partida: Partida) -> None:
        esquinas = ((0, 0), (cfg.ANCHO, 0), (cfg.ANCHO, cfg.ALTO), (0, cfg.ALTO))
        puntos = [self._punto_minimapa(partida.camara.a_mundo(esquina)) for esquina in esquinas]
        recorte_anterior = superficie.get_clip()
        superficie.set_clip(RECTANGULO_MINIMAPA.inflate(-8, -8).clip(recorte_anterior))
        pygame.draw.polygon(superficie, (90, 135, 165), puntos, 1)
        superficie.set_clip(recorte_anterior)

    def _dibujar_armas(self, superficie: pygame.Surface, partida: Partida) -> None:
        nave = partida.nave
        nombres = ('LASER', 'MISILES', 'HAZ')
        for indice, nombre in enumerate(nombres, 1):
            rectangulo = pygame.Rect(398 + (indice - 1) * 192, cfg.ALTO - 112, 178, 54)
            seleccionado = nave.arma == indice
            _panel(superficie, rectangulo, (80, 190, 215) if seleccionado else (35, 65, 85))
            self.texto(superficie, f'{indice}  {nombre}', (rectangulo.x + 12, rectangulo.y + 5))
            estado = self._estado_arma(partida, indice)
            self.texto(superficie, estado, (rectangulo.x + 12, rectangulo.y + 31), fuente='pequena')
        self.texto(superficie, 'Clic: destino / enemigo   |   Repetir slot: disparar / parar   |   Esc: pausa',
                   (360, cfg.ALTO - 42), fuente='pequena')

    def _estado_arma(self, partida: Partida, indice: int) -> str:
        nave = partida.nave
        if indice == 3 and nave.enfriamiento_haz > 0:
            return f'RECARGA {nave.enfriamiento_haz:.1f}s'
        if indice == 3 and nave.tiempo_haz > 0:
            return f'ACTIVO {nave.tiempo_haz:.1f}s'
        if nave.arma == indice:
            alcance = {1: cfg.ALCANCE_LASER, 2: cfg.ALCANCE_MISIL, 3: cfg.ALCANCE_BEAM}[indice]
            if nave.disparo_activo and partida.objetivo is not None:
                if nave.pos.distance_to(partida.objetivo.pos) > alcance:
                    return 'ESPERANDO ALCANCE'
            return 'DISPARANDO' if nave.disparo_activo else 'SELECCIONADO'
        return 'DISPONIBLE'

    def _dibujar_objetivo(self, superficie: pygame.Surface, partida: Partida) -> None:
        objetivo = partida.objetivo
        if objetivo is not None:
            distancia = partida.nave.pos.distance_to(objetivo.pos)
            self.texto(superficie, f'Objetivo {objetivo.identificador} / {objetivo.vida:.0f} vida / {distancia:.0f} px',
                       (36, 190), (255, 210, 130), 'pequena')
        if en_base(partida.nave.pos):
            self.texto(superficie, 'BASE SEGURA  /  E: tienda  /  Armas bloqueadas',
                       (470, 24), (120, 235, 205))
        elif partida.nave.tiempo_sin_combate < cfg.ESPERA_REGENERACION_SEGUNDOS:
            self.texto(superficie, 'EN COMBATE', (36, 218), (245, 145, 120), 'pequena')

    def botones(self, estado: str, partida: Partida | None, existe_guardado: bool) -> list[Boton]:
        opciones = self._opciones(estado, partida, existe_guardado)
        return [Boton(accion, texto, pygame.Rect(cfg.ANCHO // 2 - 250, 292 + indice * 64, 500, 52), habilitado)
                for indice, (accion, texto, habilitado) in enumerate(opciones)]

    def _opciones(self, estado: str, partida: Partida | None, existe: bool) -> list[tuple[str, str, bool]]:
        if estado in ('inicio', 'derrota'):
            return [('nueva', 'Nueva partida', True), ('cargar', 'Cargar partida', existe), ('salir', 'Salir', True)]
        if estado == 'pausa':
            return [('reanudar', 'Reanudar', True), ('guardar', 'Guardar partida', True), ('salir', 'Guardar y salir', True)]
        if estado == 'confirmar_nueva':
            return [('confirmar', 'Comenzar nueva partida', True), ('cancelar', 'Volver', True)]
        if estado == 'error_salida':
            return [('salir', 'Reintentar guardado y salida', True), ('cancelar_salida', 'Volver', True),
                    ('salir_sin_guardar', 'Salir sin guardar', True)]
        if estado == 'tienda':
            return self._opciones_tienda(partida)
        return []

    def _opciones_tienda(self, partida: Partida) -> list[tuple[str, str, bool]]:
        opciones = []
        for tipo in ('laser', 'vida', 'escudo'):
            nivel = partida.mejoras.nivel(tipo)
            precio = partida.mejoras.precio(tipo)
            disponible = nivel < cfg.MAX_NIVEL_MEJORA and partida.creditos >= precio
            texto = f'{tipo.upper()} / nivel {nivel} / {precio} creditos' if nivel < cfg.MAX_NIVEL_MEJORA else f'{tipo.upper()} / MAXIMO'
            opciones.append((f'comprar_{tipo}', texto, disponible))
        return opciones + [('reanudar', 'Volver al espacio', True)]

    def dibujar_menu(self, superficie: pygame.Surface, estado: str, partida: Partida | None,
                     existe: bool, mensaje: str) -> None:
        velo = pygame.Surface((cfg.ANCHO, cfg.ALTO), pygame.SRCALPHA)
        velo.fill((3, 8, 18, 160 if estado == 'derrota' else 225))
        superficie.blit(velo, (0, 0))
        titulos = {'inicio': 'YUGEN / NOUMENO', 'pausa': 'PAUSA', 'derrota': 'NAVE DESTRUIDA',
                   'tienda': 'BASE / SUMINISTROS', 'confirmar_nueva': 'NUEVA PARTIDA', 'error_salida': 'GUARDADO FALLIDO'}
        titulo = self.fuentes['titulo'].render(titulos[estado], True, (170, 235, 245))
        superficie.blit(titulo, titulo.get_rect(center=(cfg.ANCHO // 2, 192)))
        self._subtitulo(superficie, estado, partida)
        for boton in self.botones(estado, partida, existe):
            self._dibujar_boton(superficie, boton)
        if mensaje:
            self._dibujar_mensaje(superficie, mensaje)

    def _subtitulo(self, superficie: pygame.Surface, estado: str, partida: Partida | None) -> None:
        textos = {'inicio': 'Explora. Elige tu objetivo. Regresa a salvo.',
                  'pausa': 'La simulacion esta detenida.', 'derrota': 'Carga una partida o comienza otra.',
                  'tienda': f'{partida.creditos if partida else 0} creditos / Laser +10, vida +20, escudo +20 por nivel',
                  'confirmar_nueva': 'El proximo guardado reemplazara la partida anterior.',
                  'error_salida': 'La partida anterior se conserva. Puedes reintentar o salir sin guardar.'}
        texto = self.fuentes['pequena'].render(textos[estado], True, (135, 165, 185))
        superficie.blit(texto, texto.get_rect(center=(cfg.ANCHO // 2, 245)))

    def _dibujar_boton(self, superficie: pygame.Surface, boton: Boton) -> None:
        encima = boton.rectangulo.collidepoint(pygame.mouse.get_pos()) and boton.habilitado
        color = (85, 195, 215) if encima else (40, 75, 100)
        _panel(superficie, boton.rectangulo, color)
        texto = self.fuentes['normal'].render(boton.texto, True,
                                             (215, 240, 245) if boton.habilitado else (85, 105, 120))
        superficie.blit(texto, texto.get_rect(center=boton.rectangulo.center))

    def _dibujar_mensaje(self, superficie: pygame.Surface, mensaje: str) -> None:
        palabras, linea, lineas = mensaje.split(), '', []
        for palabra in palabras:
            candidato = f'{linea} {palabra}'.strip()
            if self.fuentes['pequena'].size(candidato)[0] > 1000:
                lineas.append(linea)
                linea = palabra
            else:
                linea = candidato
        lineas.append(linea)
        for indice, contenido in enumerate(lineas[:3]):
            texto = self.fuentes['pequena'].render(contenido, True, (255, 205, 135))
            superficie.blit(texto, texto.get_rect(center=(cfg.ANCHO // 2, 640 + indice * 24)))


def _panel(superficie: pygame.Surface, rectangulo: pygame.Rect,
           borde: tuple = (35, 65, 85)) -> None:
    pygame.draw.rect(superficie, (8, 19, 33), rectangulo, border_radius=8)
    pygame.draw.rect(superficie, borde, rectangulo, 1, border_radius=8)
