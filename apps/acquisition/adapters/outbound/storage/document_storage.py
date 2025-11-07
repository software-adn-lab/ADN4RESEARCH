from typing import BinaryIO, Optional


class DocumentStorage:
    """Abstract base for document storage backends (scaffold)."""

    def store(self, name: str, stream: BinaryIO) -> str:
        raise NotImplementedError

    def get(self, path: str) -> Optional[BinaryIO]:
        raise NotImplementedError
