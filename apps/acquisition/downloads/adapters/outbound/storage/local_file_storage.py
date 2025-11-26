"""
LocalFileStorage - Adaptador simple para guardar archivos en el sistema de archivos.

Separa la lógica de escritura/lectura del resto de la aplicación para que,
en el futuro, pueda reemplazarse por un storage en la nube sin tocar la capa
de aplicación.
"""

import os
from pathlib import Path
from typing import BinaryIO


class LocalFileStorage:
    """
    Adaptador de almacenamiento basado en el sistema de archivos local.
    """

    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: Directorio raíz donde se guardarán los archivos.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_obj: BinaryIO, relative_path: str) -> str:
        """
        Guardar un archivo en disco.

        Args:
            file_obj: Objeto tipo archivo. Debe soportar .read() o .chunks().
            relative_path: Ruta relativa dentro del base_dir.

        Returns:
            Ruta absoluta donde se guardó el archivo.
        """
        destination = self.base_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Permitir objetos Django UploadedFile (tienen .chunks()) o binarios simples.
        if hasattr(file_obj, "chunks"):
            with open(destination, "wb") as dest:
                for chunk in file_obj.chunks():
                    dest.write(chunk)
        else:
            with open(destination, "wb") as dest:
                dest.write(file_obj.read())

        return str(destination)

    def delete(self, path: str) -> None:
        """
        Eliminar un archivo si existe.

        Args:
            path: Ruta absoluta al archivo.
        """
        try:
            os.remove(path)
        except OSError:
            # Silencioso: si no existe o no se puede borrar, no debe romper el flujo.
            pass
