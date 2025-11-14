import time
import logging
import psutil

logger = logging.getLogger("Naves")


class PerformanceMonitor:
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
        memory_mb = (
            self.process.memory_info().rss / 1024.0 / 1024.0
            if self.process
            else 0.0
        )
        avg_frame = sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0.0
        fps = 1000.0 / avg_frame if avg_frame > 0 else 0.0
        return {
            'cpu': cpu_percent,
            'memory': memory_mb,
            'avg_frame_ms': avg_frame,
            'fps': fps,
        }
