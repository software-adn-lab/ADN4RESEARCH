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
from apps.acquisition.downloads.domain.interfaces import IStorage


class IUploadedFile(Protocol):
    """
    Protocolo mínimo para representar un archivo subido (Django UploadedFile compatible).
    """

    @property
    def name(self) -> str:
        ...

    def chunks(self, chunk_size: int = ...) -> BinaryIO:
        ...


class ManualUploadAppService:
    """
    Servicio de aplicación de alto nivel para carga manual de PDFs.
    
    Usa IStorage (Port) en lugar de implementación concreta,
    permitiendo cambiar entre LocalFileStorage, DjangoStorage (MinIO/S3),
    o cualquier otro backend sin modificar este servicio.
    """

    def __init__(
        self,
        repository: IStudyRepository,
        manual_upload_service: ManualUploadService,
        storage: IStorage,
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
            # attach_file ya actualiza pdf_path, pdf_source y download_status
            updated = self.manual_upload_service.attach_file(study=study, file_path=saved_path)

            self.repository.save(updated)
            return updated
        except Exception:
            self.storage.delete(saved_path)
            raise
