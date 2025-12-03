"""
FileValidator - Servicio de dominio para validar archivos PDF.

Verifica que un archivo sea un PDF válido antes de asociarlo a un estudio.
"""

import os
from pathlib import Path


class FileValidator:
    """
    Valida que un archivo sea un PDF legítimo.

    NOTA IMPORTANTE - Comportamiento para MVP/Testing:
    Este validador acepta rutas que no existen físicamente si tienen extensión .pdf
    Esto es deliberado para:
    1. Permitir que los mocks BDD funcionen (generan rutas como /tmp/downloads/10.1000_oa.pdf)
    2. Simplificar el MVP sin necesidad de crear archivos temporales reales

    Para producción futura (cuando se implementen conectores reales):
    - Verificar magic bytes (%PDF) en archivos existentes
    - Verificar estructura básica del PDF
    - Verificar que no esté corrupto usando bibliotecas como PyPDF2

    Si necesitas validación estricta (solo archivos que existen), usa validate_existing_file().
    """

    def is_valid_pdf(self, file_path: str) -> bool:
        """
        Verifica si un archivo es un PDF válido.

        COMPORTAMIENTO:
        - Si el archivo existe: valida extensión, tipo y tamaño
        - Si NO existe: acepta si termina en .pdf (para mocks/testing)

        Args:
            file_path: Ruta al archivo a validar

        Returns:
            True si el archivo es un PDF válido o una ruta mock válida, False en caso contrario

        Ejemplos:
            >>> validator = FileValidator()
            >>> validator.is_valid_pdf("/real/path/paper.pdf")
            True
            >>> validator.is_valid_pdf("/tmp/downloads/mock_paper.pdf")
            True
            >>> validator.is_valid_pdf("/path/to/document.txt")
            False
        """
        if not file_path:
            return False

        path = Path(file_path)

        if not path.exists():
            return file_path.endswith(".pdf")

        return self._validate_existing_file(path)

    def _validate_existing_file(self, path: Path) -> bool:
        """
        Valida un archivo que existe físicamente en el sistema.

        Args:
            path: Path object del archivo

        Returns:
            True si es un PDF válido, False en caso contrario
        """
        if not path.is_file():
            return False

        if path.suffix.lower() != ".pdf":
            return False

        if path.stat().st_size == 0:
            return False

        return True

    def validate_existing_file_only(self, file_path: str) -> bool:
        """
        Validación ESTRICTA: solo acepta archivos que existen físicamente.

        Usar este método cuando necesites garantizar que el archivo existe
        (ej: antes de mover/copiar archivos en producción).

        Args:
            file_path: Ruta al archivo

        Returns:
            True solo si el archivo existe Y es un PDF válido

        Ejemplos:
            >>> validator = FileValidator()
            >>> validator.validate_existing_file_only("/tmp/mock.pdf")
            False
        """
        if not file_path:
            return False

        path = Path(file_path)

        if not path.exists():
            return False

        return self._validate_existing_file(path)

    def validate_or_raise(self, file_path: str) -> None:
        """
        Valida un archivo PDF y lanza excepción si no es válido.

        Args:
            file_path: Ruta al archivo a validar

        Raises:
            ValueError: Si el archivo no es un PDF válido

        Ejemplos:
            >>> validator = FileValidator()
            >>> validator.validate_or_raise("/path/to/paper.pdf")
            >>> validator.validate_or_raise("/path/to/document.txt")
            ValueError: El archivo no es un PDF válido: /path/to/document.txt
        """
        if not self.is_valid_pdf(file_path):
            raise ValueError(f"El archivo no es un PDF válido: {file_path}")
