from dataclasses import dataclass, field

import config as cfg
from entities import Enemigo, MarcadorDanio, Nave, Proyectil
from efectos import SistemaEfectos
from mundo import Camara, Mundo, en_base
from tienda import Mejoras


@dataclass
class Partida:
    nave: Nave = field(default_factory=lambda: Nave(cfg.POSICION_BASE))
    mundo: Mundo = field(default_factory=Mundo)
    mejoras: Mejoras = field(default_factory=Mejoras)
    camara: Camara = field(default_factory=Camara)
    creditos: int = 0
    bajas: int = 0
    objetivo_id: str | None = None
    proyectiles: list[Proyectil] = field(default_factory=list)
    marcadores: list[MarcadorDanio] = field(default_factory=list)
    eventos_audio: list[str] = field(default_factory=list)
    haz_visible: bool = False
    efectos: SistemaEfectos = field(default_factory=SistemaEfectos)

    def __post_init__(self) -> None:
        self.camara.seguir(self.nave.pos)

    @property
    def objetivo(self) -> Enemigo | None:
        enemigo = self.mundo.enemigos.get(self.objetivo_id)
        if enemigo is None or not enemigo.vivo or enemigo not in self.mundo.activos:
            return None
        return enemigo

    def actualizar(self, dt: float) -> None:
        from combate import actualizar_combate

        if not self.nave.viva:
            return
        self.nave.hubo_combate = False
        objetivo = self.objetivo
        self.nave.actualizar(dt, objetivo.pos if objetivo is not None else None)
        self.mundo.actualizar(self.nave.pos, dt)
        if self.objetivo is None:
            self.objetivo_id = None
            self.nave.detener_disparo()
        actualizar_combate(self, dt)
        if not self.nave.hubo_combate:
            self.nave.regenerar(dt)
        self.camara.seguir(self.nave.pos)
        self.actualizar_visuales(dt)

    def actualizar_visuales(self, dt: float) -> None:
        self.efectos.actualizar(dt)
        for marcador in self.marcadores:
            marcador.actualizar(dt)
        self.marcadores = [marcador for marcador in self.marcadores if marcador.tiempo > 0]

    def seleccionar(self, posicion: tuple[int, int]) -> None:
        punto = self.camara.a_mundo(posicion)
        candidatos = [enemigo for enemigo in self.mundo.activos
                      if enemigo.vivo and enemigo.pos.distance_to(punto) <= enemigo.radio + 10]
        if candidatos:
            self.objetivo_id = min(candidatos, key=lambda enemigo: enemigo.pos.distance_to(punto)).identificador
            return
        self.nave.mover_a(punto)

    def preparar_base(self) -> None:
        if en_base(self.nave.pos):
            self.nave.detener_disparo()
            self.proyectiles.clear()
