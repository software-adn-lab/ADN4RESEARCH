"""
ManualUploadService - Servicio de aplicación para carga manual de PDFs.

Permite al usuario adjuntar manualmente archivos PDF a estudios cuando
la descarga automática no es posible.
"""

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.downloads.domain.services.file_validator import FileValidator
from apps.acquisition.downloads.domain.value_objects.download_status import DownloadStatus
from apps.acquisition.downloads.domain.value_objects.pdf_source import PdfSource


class ManualUploadService:
    """
    Servicio de aplicación para carga manual de textos completos.

    Responsabilidades:
    1. Validar que el archivo sea un PDF válido
    2. Vincular el archivo al estudio
    3. Actualizar el estado de descarga
    4. Registrar trazabilidad (origen = manual)

    Este servicio NO descarga archivos. Solo valida y vincula
    archivos que el usuario ya subió al sistema.
    """

    def __init__(self, file_validator: FileValidator):
        """
        Inicializar el servicio con sus dependencias.

        Args:
            file_validator: Validador de archivos PDF
        """
        self.file_validator = file_validator

    def attach_file(self, study: Study, file_path: str, force: bool = False) -> Study:
        """
        Adjuntar un archivo PDF manualmente a un estudio.

        Args:
            study: Estudio al que se va a adjuntar el archivo
            file_path: Ruta al archivo PDF subido por el usuario
            force: Si True, permite reemplazar un PDF existente

        Returns:
            Study con el archivo adjunto y metadatos actualizados

        Raises:
            ValueError: Si el archivo no es un PDF válido
            ValueError: Si el estudio ya tiene un PDF adjunto y force=False

        Ejemplos:
            >>> service = ManualUploadService(file_validator=FileValidator())
            >>> study = Study.create_discovered(...)
            >>> updated_study = service.attach_file(study, "/uploads/paper.pdf")
            >>> updated_study.pdf_path
            '/uploads/paper.pdf'
            >>> updated_study.pdf_source
            'manual'
            >>> updated_study.download_status
            'texto_completo_disponible'
            
            # Reemplazar un PDF existente:
            >>> updated_study = service.attach_file(study, "/uploads/new.pdf", force=True)
        """
        # 1. Validar precondiciones
        if study.pdf_path is not None and not force:
            raise ValueError(
                f"El estudio '{study.title}' ya tiene un PDF adjunto: {study.pdf_path}. "
                f"Usa force=True para reemplazarlo."
            )

        # 2. Validar que el archivo sea un PDF válido
        if not self.file_validator.is_valid_pdf(file_path):
            raise ValueError(f"El archivo no es un PDF válido: {file_path}")

        # 3. Vincular el archivo al estudio
        study.pdf_path = file_path
        study.pdf_source = PdfSource.MANUAL.value
        
        # Count pages
        study.page_count = self._count_pages(file_path)
        
        study.download_status = DownloadStatus.DISPONIBLE.value

        # 4. Retornar el estudio actualizado
        return study

    def _count_pages(self, pdf_path: str) -> int | None:
        """Count pages of the uploaded PDF."""
        try:
            from pypdf import PdfReader
            import os
            
            if os.path.exists(pdf_path):
                reader = PdfReader(pdf_path)
                return len(reader.pages)
            return None
        except Exception:
            return None
