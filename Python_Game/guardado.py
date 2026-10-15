import json
import math
import os
from dataclasses import asdict
from pathlib import Path

from pygame.math import Vector2

import config as cfg
from entities import Enemigo
from mundo import Mundo, en_base
from partida import Partida
from tienda import Mejoras, aplicar_mejoras

VERSION_GUARDADO = 1
RUTA_PARTIDA = Path(__file__).resolve().parent.parent / 'partidas' / 'partida.json'
MAX_BYTES_GUARDADO = 2 * 1024 * 1024


class ErrorGuardado(ValueError):
    pass


class AlmacenPartida:
    def __init__(self, ruta: Path = RUTA_PARTIDA) -> None:
        self.ruta = Path(ruta)

    def guardar(self, partida: Partida) -> None:
        datos = _serializar(partida)
        _reconstruir(datos)
        temporal = self.ruta.with_suffix('.json.tmp')
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            with temporal.open('w', encoding='utf-8') as archivo:
                json.dump(datos, archivo, ensure_ascii=False, allow_nan=False, indent=2)
                archivo.flush()
                os.fsync(archivo.fileno())
            temporal.replace(self.ruta)
        except OSError as error:
            raise ErrorGuardado(f'No se pudo guardar la partida: {error}') from error

    def cargar(self) -> Partida:
        try:
            with self.ruta.open('rb') as archivo:
                contenido = archivo.read(MAX_BYTES_GUARDADO + 1)
            if len(contenido) > MAX_BYTES_GUARDADO:
                raise ErrorGuardado('El guardado supera el tamanio permitido.')
            datos = json.loads(contenido.decode('utf-8'))
            return _reconstruir(datos)
        except (OSError, UnicodeDecodeError, ValueError, RecursionError) as error:
            raise ErrorGuardado(f'No se pudo leer la partida: {error}') from error


def _serializar(partida: Partida) -> dict:
    return {
        'version': VERSION_GUARDADO,
        'nave': _serializar_nave(partida),
        'creditos': partida.creditos,
        'bajas': partida.bajas,
        'mejoras': asdict(partida.mejoras),
        'semilla': partida.mundo.semilla,
        'sectores': [list(sector) for sector in sorted(partida.mundo.sectores_generados)],
        'enemigos': [_serializar_enemigo(enemigo) for enemigo in partida.mundo.enemigos.values()],
    }


def _serializar_nave(partida: Partida) -> dict:
    nave = partida.nave
    return {
        'pos': list(nave.pos), 'destino': list(nave.destino), 'angulo': nave.angulo % 360,
        'vida': nave.vida, 'escudo': nave.escudo, 'arma': nave.arma,
        'tiempo_sin_combate': min(nave.tiempo_sin_combate, cfg.ESPERA_REGENERACION_SEGUNDOS),
        'tiempo_laser': nave.tiempo_laser, 'tiempo_misil': nave.tiempo_misil,
        'enfriamiento_haz': max(nave.enfriamiento_haz,
                               cfg.ENFRIAMIENTO_HAZ_SEGUNDOS if nave.tiempo_haz > 0 else 0),
    }


def _serializar_enemigo(enemigo: Enemigo) -> dict:
    return {
        'id': enemigo.identificador, 'pos': list(enemigo.pos),
        'origen': list(enemigo.origen), 'vida': enemigo.vida,
        'tiempo_disparo': enemigo.tiempo_disparo,
    }


def _objeto(datos: object, nombre: str) -> dict:
    if not isinstance(datos, dict):
        raise ErrorGuardado(f'{nombre} debe ser un objeto.')
    return datos


def _campo(datos: dict, nombre: str) -> object:
    if nombre not in datos:
        raise ErrorGuardado(f'Falta el campo {nombre}.')
    return datos[nombre]


def _numero(datos: dict, nombre: str, minimo: float, maximo: float) -> float:
    valor = _campo(datos, nombre)
    if type(valor) not in (int, float):
        raise ErrorGuardado(f'{nombre} debe ser numerico.')
    if not minimo <= valor <= maximo or not math.isfinite(valor):
        raise ErrorGuardado(f'{nombre} esta fuera de rango.')
    return float(valor)


def _entero(datos: dict, nombre: str, minimo: int, maximo: int) -> int:
    valor = _campo(datos, nombre)
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ErrorGuardado(f'{nombre} debe ser un entero entre {minimo} y {maximo}.')
    return valor


def _vector(datos: dict, nombre: str, margen: float = 0) -> Vector2:
    valor = _campo(datos, nombre)
    if not isinstance(valor, list) or len(valor) != 2:
        raise ErrorGuardado(f'{nombre} debe contener dos coordenadas.')
    coordenadas = {'x': valor[0], 'y': valor[1]}
    return Vector2(_numero(coordenadas, 'x', margen, cfg.ANCHO_MUNDO - margen),
                   _numero(coordenadas, 'y', margen, cfg.ALTO_MUNDO - margen))


def _lista(datos: dict, nombre: str, maximo: int) -> list:
    valor = _campo(datos, nombre)
    if not isinstance(valor, list) or len(valor) > maximo:
        raise ErrorGuardado(f'{nombre} debe ser una lista con un maximo de {maximo} elementos.')
    return valor


def _reconstruir(datos: object) -> Partida:
    datos = _objeto(datos, 'partida')
    if _entero(datos, 'version', 1, 2**31) != VERSION_GUARDADO:
        raise ErrorGuardado('Version de guardado incompatible.')
    partida = Partida()
    mejoras = _objeto(_campo(datos, 'mejoras'), 'mejoras')
    partida.mejoras = Mejoras(*[_entero(mejoras, tipo, 0, cfg.MAX_NIVEL_MEJORA)
                               for tipo in ('laser', 'vida', 'escudo')])
    aplicar_mejoras(partida)
    _restaurar_nave(partida, _objeto(_campo(datos, 'nave'), 'nave'))
    partida.creditos = _entero(datos, 'creditos', 0, 10**9)
    partida.bajas = _entero(datos, 'bajas', 0, 10**9)
    partida.mundo = Mundo(_entero(datos, 'semilla', 0, 2**31 - 1))
    partida.mundo.sectores_generados = _restaurar_sectores(datos)
    for registro in _lista(datos, 'enemigos', 128):
        _restaurar_enemigo(partida.mundo, _objeto(registro, 'enemigo'))
    partida.camara.seguir(partida.nave.pos)
    partida.mundo.activar_cercanos(partida.nave.pos)
    return partida


def _restaurar_nave(partida: Partida, datos: dict) -> None:
    nave = partida.nave
    nave.pos = _vector(datos, 'pos', nave.radio)
    nave.destino = _vector(datos, 'destino', nave.radio)
    nave.angulo = _numero(datos, 'angulo', 0, 360)
    nave.vida = _numero(datos, 'vida', 0, nave.vida_maxima)
    nave.escudo = _numero(datos, 'escudo', 0, nave.escudo_maximo)
    nave.arma = _entero(datos, 'arma', 0, 3)
    nave.tiempo_sin_combate = _numero(datos, 'tiempo_sin_combate', 0, cfg.ESPERA_REGENERACION_SEGUNDOS)
    nave.tiempo_laser = _numero(datos, 'tiempo_laser', 0, cfg.COOLDOWN_LASER)
    nave.tiempo_misil = _numero(datos, 'tiempo_misil', 0, cfg.CADENCIA_MISIL)
    nave.enfriamiento_haz = _numero(datos, 'enfriamiento_haz', 0, cfg.ENFRIAMIENTO_HAZ_SEGUNDOS)


def _restaurar_sectores(datos: dict) -> set[tuple[int, int]]:
    sectores = set()
    for sector in _lista(datos, 'sectores', 64):
        if not isinstance(sector, list) or len(sector) != 2:
            raise ErrorGuardado('Sector invalido.')
        coordenadas = {'x': sector[0], 'y': sector[1]}
        clave = (_entero(coordenadas, 'x', 0, 7), _entero(coordenadas, 'y', 0, 7))
        if clave in sectores:
            raise ErrorGuardado('Sector duplicado.')
        sectores.add(clave)
    return sectores


def _restaurar_enemigo(mundo: Mundo, datos: dict) -> None:
    identificador = _campo(datos, 'id')
    if not isinstance(identificador, str) or len(identificador) > 16:
        raise ErrorGuardado('Identificador de enemigo invalido.')
    partes = identificador.split(':')
    if len(partes) != 3 or any(parte not in tuple(str(i) for i in range(8)) for parte in partes):
        raise ErrorGuardado('Identificador de enemigo invalido.')
    x, y, indice = map(int, partes)
    if indice >= cfg.ENEMIGOS_POR_SECTOR or (x, y) not in mundo.sectores_generados:
        raise ErrorGuardado('El enemigo no pertenece a un sector generado.')
    if identificador in mundo.enemigos:
        raise ErrorGuardado('Enemigo duplicado.')
    posicion, origen = _vector(datos, 'pos', 18), _vector(datos, 'origen', 18)
    if (int(origen.x // cfg.TAMANIO_SECTOR), int(origen.y // cfg.TAMANIO_SECTOR)) != (x, y):
        raise ErrorGuardado('El origen del enemigo no coincide con su sector.')
    if en_base(posicion, 18) or en_base(origen, 18):
        raise ErrorGuardado('Un enemigo esta dentro de la base.')
    mundo.enemigos[identificador] = Enemigo(
        identificador, posicion, origen, _numero(datos, 'vida', 0, cfg.VIDA_ENEMIGO),
        _numero(datos, 'tiempo_disparo', 0, cfg.CADENCIA_ENEMIGO_SEGUNDOS),
    )
