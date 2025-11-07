from typing import Callable, List


class DownloadManager:
    """Simple download manager scaffold with an in-memory queue.

    In later phases this will integrate retry policies and asynchronous workers.
    """

    def __init__(self) -> None:
        self._queue: List[Callable[[], None]] = []

    def enqueue(self, job: Callable[[], None]) -> None:
        self._queue.append(job)

    def run_next(self) -> None:
        if self._queue:
            job = self._queue.pop(0)
            job()
