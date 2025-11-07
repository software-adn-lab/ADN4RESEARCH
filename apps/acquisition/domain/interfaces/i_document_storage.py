from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class IDocumentStorage(ABC):
    """Contract for storing downloaded documents (PDFs, etc.)."""

    @abstractmethod
    def store(self, name: str, stream: BinaryIO) -> str:
        """Store the binary stream and return a URL or path."""

    @abstractmethod
    def get(self, path: str) -> Optional[BinaryIO]:
        """Retrieve a previously stored document by path."""
