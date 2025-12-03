"""
Circuit Breaker Pattern - Implementación simple para tolerancia a fallos.

Evita saturar servicios externos que están caídos o lentos.

Estados:
- CLOSED: Funcionando normal, peticiones pasan.
- OPEN: Servicio marcado como caído, peticiones NO pasan (fail fast).
- HALF_OPEN: Probando si el servicio volvió (permite 1 petición de prueba).

Uso:
    breaker = CircuitBreaker(fail_max=5, timeout_duration=300)

    try:
        result = breaker.call(funcion_riesgosa, arg1, arg2)
    except CircuitBreakerOpenError:
        # El servicio está caído, no intentar más
        handle_fallback()
"""
import time
import logging
from typing import Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados del Circuit Breaker."""
    CLOSED = "closed"  # Funcionando normal
    OPEN = "open"  # Servicio caído, bloqueando peticiones
    HALF_OPEN = "half_open"  # Probando si el servicio volvió


class CircuitBreakerOpenError(Exception):
    """Excepción lanzada cuando el Circuit Breaker está abierto (servicio caído)."""
    pass


class CircuitBreaker:
    """
    Implementación del patrón Circuit Breaker.

    Protege llamadas a servicios externos fallidos.
    """

    def __init__(
        self,
        fail_max: int = 5,
        timeout_duration: int = 300,
        name: str = "CircuitBreaker"
    ):
        """
        Args:
            fail_max: Número máximo de fallos antes de abrir el circuito
            timeout_duration: Segundos que el circuito permanece abierto
            name: Nombre del breaker (para logs)
        """
        self.fail_max = fail_max
        self.timeout_duration = timeout_duration
        self.name = name

        self.fail_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función protegida por el circuit breaker.

        Args:
            func: Función a ejecutar
            *args, **kwargs: Argumentos para la función

        Returns:
            Resultado de la función

        Raises:
            CircuitBreakerOpenError: Si el circuito está abierto
            Exception: Si la función falla (y el circuito se cierra o abre)
        """
        # Si el circuito está abierto
        if self.state == CircuitState.OPEN:
            # Verificar si ya pasó el timeout
            if self._should_attempt_reset():
                logger.info(f"🔄 [{self.name}] Circuito en HALF_OPEN. Probando reconexión...")
                self.state = CircuitState.HALF_OPEN
            else:
                # Todavía no pasó el timeout, rechazar petición
                raise CircuitBreakerOpenError(
                    f"Circuit Breaker [{self.name}] ABIERTO. "
                    f"Servicio no disponible. Reintento en {self._time_until_reset():.0f}s"
                )

        # Intentar ejecutar la función
        try:
            result = func(*args, **kwargs)
            # Éxito: resetear contadores
            self._on_success()
            return result

        except Exception as e:
            # Fallo: incrementar contador
            self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Verificar si ya pasó el timeout para intentar reconectar."""
        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.timeout_duration

    def _time_until_reset(self) -> float:
        """Calcular segundos faltantes hasta el próximo intento."""
        if self.last_failure_time is None:
            return 0

        time_since_failure = time.time() - self.last_failure_time
        return max(0, self.timeout_duration - time_since_failure)

    def _on_success(self):
        """Registrar éxito: resetear contadores y cerrar circuito."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"✅ [{self.name}] Servicio restaurado. Circuito CERRADO.")

        self.fail_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self, exception: Exception):
        """Registrar fallo: incrementar contador y posiblemente abrir circuito."""
        self.fail_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"⚠️ [{self.name}] Fallo {self.fail_count}/{self.fail_max}: {type(exception).__name__}"
        )

        # Si alcanzamos el límite, abrir el circuito
        if self.fail_count >= self.fail_max:
            self.state = CircuitState.OPEN
            logger.error(
                f"❌ [{self.name}] Circuit Breaker ABIERTO. "
                f"Servicio marcado como caído por {self.timeout_duration}s."
            )

    def reset(self):
        """Resetear manualmente el circuit breaker (para testing)."""
        self.fail_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info(f"🔄 [{self.name}] Circuit Breaker reseteado manualmente.")
