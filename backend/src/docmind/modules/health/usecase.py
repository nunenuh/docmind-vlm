"""docmind/modules/health/usecase.py"""

import time

from .schemas import ComponentHealth

_start_time = time.time()


class HealthUseCase:
    def get_basic_health(self) -> tuple[str, list[ComponentHealth], float]:
        components = [
            ComponentHealth(
                name="database", status="healthy", message="Stub — not connected"
            ),
            ComponentHealth(
                name="vlm_provider", status="healthy", message="Stub — not connected"
            ),
        ]
        overall = "healthy"
        uptime = time.time() - _start_time
        return overall, components, uptime
