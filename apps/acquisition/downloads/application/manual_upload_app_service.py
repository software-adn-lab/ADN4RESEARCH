"""
ManualUploadAppService - Servicio de aplicación para carga manual de PDFs.

Orquesta:
- Repositorio de estudios (persistencia)
- Almacenamiento físico de archivos
- ManualUploadService (valida PDF y actualiza el estudio)
"""

import os
from typing import Protocol, BinaryIO

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.repositories.i_study_repository import IStudyRepository
from apps.acquisition.downloads.application.manual_upload_service import ManualUploadService
from apps.acquisition.downloads.adapters.outbound.storage.local_file_storage import LocalFileStorage
from apps.acquisition.downloads.domain.value_objects.pdf_source import PdfSource
from apps.acquisition.downloads.domain.value_objects.download_status import DownloadStatus


class IUploadedFile(Protocol):
    """
    Protocolo mínimo para representar un archivo subido (Django UploadedFile compatible).
    """

    @property
    def name(self) -> str:  # noqa: D401 - simple passthrough
        ...

    def chunks(self, chunk_size: int = ...) -> BinaryIO:  # noqa: D401
        ...


class ManualUploadAppService:
    """
    Servicio de aplicación de alto nivel para carga manual de PDFs.
    """

    def __init__(
        self,
        repository: IStudyRepository,
        manual_upload_service: ManualUploadService,
        storage: LocalFileStorage,
    ):
        self.repository = repository
        self.manual_upload_service = manual_upload_service
        self.storage = storage

    def upload_pdf_for_study(self, study_id: str, uploaded_file: IUploadedFile) -> Study:
        """
        Procesa la carga manual de un PDF para un estudio existente.

        Flujo:
        1) Buscar el estudio por ID
        2) Guardar el archivo en disco en una ruta estable
        3) Validar y adjuntar el PDF usando ManualUploadService
        4) Persistir cambios en el repositorio
        """
        study = self.repository.find_by_id(study_id)
        if study is None:
            raise ValueError(f"Estudio no encontrado: {study_id}")

        raw_name = uploaded_file.name or "uploaded.pdf"
        safe_name = os.path.basename(raw_name) or "uploaded.pdf"
        relative_path = f"{study.id}/manual/{safe_name}"

        saved_path = self.storage.save(uploaded_file, relative_path)

        try:
            # Usar attach_file del servicio de dominio para validar y marcar estado
            updated = self.manual_upload_service.attach_file(study=study, file_path=saved_path)

            # Garantizar estado consistente (status de workflow + download_status)
            updated.attach_pdf(pdf_path=saved_path, pdf_source=PdfSource.MANUAL.value)
            updated.download_status = DownloadStatus.DISPONIBLE.value

            self.repository.save(updated)
            return updated
        except Exception:
            # Rollback físico si la validación falla
            self.storage.delete(saved_path)
            raise
