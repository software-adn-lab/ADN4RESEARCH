"""
Study Entity - Entidad principal del dominio de Acquisition.

Esta es la ÚNICA entidad Study del módulo (Shared Kernel).
Todos los componentes (discovery, metadata, downloads) operan sobre esta entidad.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from ..value_objects.doi import DOI
from ..value_objects.study_status import StudyStatus
from ..value_objects.source import Source


@dataclass
class Study:
    """
    Representa un estudio académico en el proceso de revisión sistemática.

    El Study es el Agregado principal del módulo de Acquisition.
    Evoluciona a través del workflow: DISCOVERED → ENRICHED → DOWNLOADED

    Attributes:
        # Identificación
        id: Identificador único del estudio (UUID)
        title: Título del estudio
        link: URL al estudio en la fuente original
        source: Fuente académica de donde proviene
        doi: Digital Object Identifier (opcional)
        status: Estado actual del estudio en el workflow

        # Metadata (se completan en fase ENRICHED)
        authors: Lista de autores
        abstract: Resumen del estudio
        year: Año de publicación
        journal: Nombre de la revista/conferencia
        keywords: Palabras clave del estudio

        # Texto completo (se completa en fase DOWNLOADED)
        pdf_path: Ruta al archivo PDF descargado
        pdf_source: Fuente desde donde se obtuvo el PDF (puede diferir de source)

        # Auditoria
        discovered_at: Timestamp de cuándo se descubrió el estudio
        enriched_at: Timestamp de cuándo se enriquecieron los metadatos
        downloaded_at: Timestamp de cuándo se descargó el PDF
        failure_reason: Razón de fallo si status=FAILED

    Invariantes:
        - title no puede estar vacío
        - link debe ser una URL válida
        - Las transiciones de estado deben seguir el workflow válido
        - Si status=ENRICHED, authors y abstract deben estar presentes
        - Si status=DOWNLOADED, pdf_path debe estar presente
    """

    # Identificación y datos básicos (DISCOVERED)
    title: str
    link: str
    source: Source
    doi: Optional[DOI] = None
    status: StudyStatus = StudyStatus.DISCOVERED
    id: str = field(default_factory=lambda: str(uuid4()))

    # Metadata (ENRICHED)
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    keywords: Optional[List[str]] = None

    # Texto completo (DOWNLOADED)
    pdf_path: Optional[str] = None
    pdf_source: Optional[str] = None

    # Auditoría
    discovered_at: datetime = field(default_factory=datetime.now)
    enriched_at: Optional[datetime] = None
    downloaded_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    def __post_init__(self):
        """Validar invariantes básicas."""
        if not self.title or not self.title.strip():
            raise ValueError("El título del estudio no puede estar vacío")

        if not self.link or not self.link.strip():
            raise ValueError("El link del estudio no puede estar vacío")

    # ============================================================================
    # MÉTODOS DE TRANSICIÓN DE ESTADO
    # ============================================================================

    def enrich_metadata(
        self,
        authors: List[str],
        abstract: str,
        year: Optional[int] = None,
        journal: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> None:
        """
        Enriquecer el estudio con metadatos completos.

        Transición: DISCOVERED → ENRICHED

        Args:
            authors: Lista de autores del estudio
            abstract: Resumen del estudio
            year: Año de publicación (opcional)
            journal: Nombre de la revista/conferencia (opcional)
            keywords: Palabras clave (opcional)

        Raises:
            ValueError: Si la transición de estado no es válida
            ValueError: Si authors o abstract están vacíos
        """
        # Validar transición de estado
        if not self.status.can_transition_to(StudyStatus.ENRICHED):
            raise ValueError(
                f"No se puede enriquecer un estudio en estado {self.status}. "
                f"Estado actual debe ser {StudyStatus.DISCOVERED}"
            )

        # Validar datos requeridos
        if not authors or len(authors) == 0:
            raise ValueError("La lista de autores no puede estar vacía")

        if not abstract or not abstract.strip():
            raise ValueError("El abstract no puede estar vacío")

        # Actualizar metadata
        self.authors = authors
        self.abstract = abstract
        self.year = year
        self.journal = journal
        self.keywords = keywords if keywords else []

        # Transicionar estado
        self.status = StudyStatus.ENRICHED
        self.enriched_at = datetime.now()

    def attach_pdf(
        self,
        pdf_path: str,
        pdf_source: Optional[str] = None,
    ) -> None:
        """
        Adjuntar el texto completo (PDF) al estudio.

        Transición: ENRICHED → DOWNLOADED

        Args:
            pdf_path: Ruta al archivo PDF descargado
            pdf_source: Fuente desde donde se obtuvo (puede diferir de source original)

        Raises:
            ValueError: Si la transición de estado no es válida
            ValueError: Si pdf_path está vacío
        """
        # Validar transición de estado
        if not self.status.can_transition_to(StudyStatus.DOWNLOADED):
            raise ValueError(
                f"No se puede adjuntar PDF a un estudio en estado {self.status}. "
                f"Estado actual debe ser {StudyStatus.ENRICHED}"
            )

        # Validar datos requeridos
        if not pdf_path or not pdf_path.strip():
            raise ValueError("La ruta del PDF no puede estar vacía")

        # Actualizar datos del PDF
        self.pdf_path = pdf_path
        self.pdf_source = pdf_source if pdf_source else self.source.name

        # Transicionar estado
        self.status = StudyStatus.DOWNLOADED
        self.downloaded_at = datetime.now()

    def mark_as_failed(self, reason: str) -> None:
        """
        Marcar el estudio como fallido.

        Transición: ANY → FAILED

        Args:
            reason: Descripción de por qué falló el procesamiento

        Raises:
            ValueError: Si reason está vacío
            ValueError: Si el estudio ya está en estado final
        """
        # Validar que no esté en estado final
        if self.status.is_final():
            raise ValueError(
                f"No se puede marcar como fallido un estudio en estado final {self.status}"
            )

        # Validar reason
        if not reason or not reason.strip():
            raise ValueError("La razón de fallo no puede estar vacía")

        # Transicionar estado
        self.status = StudyStatus.FAILED
        self.failure_reason = reason

    # ============================================================================
    # MÉTODOS DE CONSULTA
    # ============================================================================

    def is_discovered(self) -> bool:
        """Verificar si el estudio está en estado DISCOVERED."""
        return self.status == StudyStatus.DISCOVERED

    def is_enriched(self) -> bool:
        """Verificar si el estudio está en estado ENRICHED."""
        return self.status == StudyStatus.ENRICHED

    def is_downloaded(self) -> bool:
        """Verificar si el estudio está en estado DOWNLOADED."""
        return self.status == StudyStatus.DOWNLOADED

    def is_failed(self) -> bool:
        """Verificar si el estudio está en estado FAILED."""
        return self.status == StudyStatus.FAILED

    def has_metadata(self) -> bool:
        """Verificar si el estudio tiene metadatos completos."""
        return self.authors is not None and self.abstract is not None

    def has_pdf(self) -> bool:
        """Verificar si el estudio tiene PDF adjunto."""
        return self.pdf_path is not None

    def get_doi_url(self) -> Optional[str]:
        """
        Obtener la URL del DOI si está disponible.

        Returns:
            URL del DOI o None si no tiene DOI
        """
        return self.doi.url() if self.doi else None

    # ============================================================================
    # SERIALIZACIÓN
    # ============================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializar el estudio a diccionario.

        Returns:
            Diccionario con todos los campos del estudio
        """
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "source": self.source.name,
            "doi": self.doi.value if self.doi else None,
            "status": self.status.value,
            "authors": self.authors,
            "abstract": self.abstract,
            "year": self.year,
            "journal": self.journal,
            "keywords": self.keywords,
            "pdf_path": self.pdf_path,
            "pdf_source": self.pdf_source,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "enriched_at": self.enriched_at.isoformat() if self.enriched_at else None,
            "downloaded_at": self.downloaded_at.isoformat() if self.downloaded_at else None,
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def create_discovered(
        cls,
        title: str,
        link: str,
        source: str,
        doi: Optional[str] = None,
    ) -> "Study":
        """
        Factory method para crear un Study en estado DISCOVERED con strings simples.

        Este método es el punto de entrada recomendado para crear estudios desde
        los componentes de discovery. Convierte automáticamente strings a value objects.

        Args:
            title: Título del estudio
            link: URL del estudio
            source: Nombre de la fuente académica (ej: "Scopus", "IEEE Xplore")
            doi: DOI opcional (string)

        Returns:
            Study en estado DISCOVERED

        Raises:
            ValueError: Si los parámetros no son válidos

        Ejemplos:
            >>> study = Study.create_discovered(
            ...     title="Machine Learning in Software Engineering",
            ...     link="https://scopus.com/study1",
            ...     source="Scopus",
            ...     doi="10.1109/TSE.2023.123"
            ... )
            >>> study.status
            StudyStatus.DISCOVERED
        """
        return cls(
            title=title,
            link=link,
            source=Source(source),
            doi=DOI.from_optional_string(doi),
            status=StudyStatus.DISCOVERED,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Study":
        """
        Crear un Study desde un diccionario.

        Args:
            data: Diccionario con los campos del estudio

        Returns:
            Instancia de Study

        Raises:
            ValueError: Si faltan campos requeridos o son inválidos
        """
        # Campos requeridos
        required_fields = ["title", "link", "source"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Campo requerido faltante: {field_name}")

        # Crear value objects
        source = Source(data["source"])
        doi = DOI.from_optional_string(data.get("doi"))
        status = StudyStatus(data.get("status", "discovered"))

        # Parsear timestamps
        discovered_at = (
            datetime.fromisoformat(data["discovered_at"])
            if data.get("discovered_at")
            else datetime.now()
        )
        enriched_at = (
            datetime.fromisoformat(data["enriched_at"])
            if data.get("enriched_at")
            else None
        )
        downloaded_at = (
            datetime.fromisoformat(data["downloaded_at"])
            if data.get("downloaded_at")
            else None
        )

        return cls(
            id=data.get("id", str(uuid4())),
            title=data["title"],
            link=data["link"],
            source=source,
            doi=doi,
            status=status,
            authors=data.get("authors"),
            abstract=data.get("abstract"),
            year=data.get("year"),
            journal=data.get("journal"),
            keywords=data.get("keywords"),
            pdf_path=data.get("pdf_path"),
            pdf_source=data.get("pdf_source"),
            discovered_at=discovered_at,
            enriched_at=enriched_at,
            downloaded_at=downloaded_at,
            failure_reason=data.get("failure_reason"),
        )

    def __repr__(self) -> str:
        """Representación del estudio para debugging."""
        return (
            f"Study(id={self.id[:8]}..., "
            f"title='{self.title[:50]}...', "
            f"status={self.status.value})"
        )
