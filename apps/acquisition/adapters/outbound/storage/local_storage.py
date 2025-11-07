from typing import BinaryIO, Optional
from pathlib import Path


class LocalStorage:
    """Simple file-system storage used in FASE 1-2."""

    def __init__(self, base_path: str):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def store(self, name: str, stream: BinaryIO) -> str:
        dest = self.base / name
        with open(dest, "wb") as f:
            f.write(stream.read())
        return str(dest)

    def get(self, path: str) -> Optional[BinaryIO]:
        p = Path(path)
        if not p.exists():
            return None
        return open(p, "rb")
