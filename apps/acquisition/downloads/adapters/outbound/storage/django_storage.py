"""
DjangoStorage - Adapter que implementa IStorage usando el storage de Django.

Este adapter sigue el patrón Port/Adapter (Hexagonal Architecture):
- Port: IStorage (interfaz en domain/interfaces.py)
- Adapter: DjangoStorage (implementación usando Django storage backend)

Soporta tanto FileSystemStorage como S3Boto3Storage según la configuración
USE_S3 en settings.py. Esto permite cambiar entre local y S3/MinIO sin
modificar código de aplicación.

La instanciación dinámica del storage (_get_storage) evita problemas de
caching del singleton default_storage de Django.
"""

from typing import BinaryIO
from django.core.files.base import ContentFile


def _get_storage():
    """
    Obtener storage dinámicamente según configuración USE_S3.
    """
    from django.conf import settings
    
    if settings.USE_S3:
        # Instanciar S3Boto3Storage directamente
        from storages.backends.s3boto3 import S3Boto3Storage
        return S3Boto3Storage()
    else:
        # Usar FileSystemStorage local
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()


class DjangoStorage:
    """
    Adaptador de almacenamiento que usa el default_storage de Django.
    
    Respeta la configuración USE_S3 en settings.py:
    - Si USE_S3=True: Usa S3Boto3Storage (AWS S3 o MinIO)
    - Si USE_S3=False: Usa FileSystemStorage (local)
    """

    def save(self, file_obj: BinaryIO, relative_path: str) -> str:
        """
        Guardar un archivo usando el backend configurado en Django.

        Args:
            file_obj: Objeto tipo archivo. Debe soportar .read() o .chunks().
            relative_path: Ruta relativa dentro del storage.

        Returns:
            Ruta donde se guardó el archivo (puede ser local o S3 URL).
        """
        storage = _get_storage()
        
        # Resetear puntero si es posible
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        
        # Django UploadedFile tiene .chunks(), archivos binarios tienen .read()
        if hasattr(file_obj, 'chunks'):
            # Leer todo el contenido en chunks
            content = b''.join(chunk for chunk in file_obj.chunks())
        else:
            content = file_obj.read()
        
        # Guardar usando storage dinámico (S3/MinIO o FileSystem según USE_S3)
        saved_path = storage.save(relative_path, ContentFile(content))
        
        return saved_path

    def delete(self, path: str) -> None:
        """
        Eliminar un archivo si existe.

        Args:
            path: Ruta al archivo (relativa o absoluta según backend).
        """
        storage = _get_storage()
        try:
            if storage.exists(path):
                storage.delete(path)
        except Exception:
            # Silencioso: si no existe o no se puede borrar, no rompe el flujo
            pass

    def exists(self, path: str) -> bool:
        """
        Verificar si un archivo existe.

        Args:
            path: Ruta al archivo.

        Returns:
            True si existe, False si no.
        """
        return _get_storage().exists(path)

    def url(self, path: str) -> str:
        """
        Obtener URL pública del archivo.

        Args:
            path: Ruta al archivo.

        Returns:
            URL completa (para S3) o ruta relativa (para local).
        """
        return _get_storage().url(path)

    def size(self, path: str) -> int:
        """
        Obtener el tamaño del archivo.

        Args:
            path: Ruta al archivo.

        Returns:
            Tamaño del archivo en bytes.
        """
        return _get_storage().size(path)
