# python
# render.py
import pygame
from pygame.math import Vector2

from config import ANCHO, ALTO, COLOR_FONDO_BASE, ALCANCE_BEAM, COLOR_BEAM


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