"""
ManualEditService - Servicio de aplicación para edición manual de metadatos.

Permite a los usuarios editar manualmente campos de metadatos cuando
la consolidación automática no logra completarlos o produce errores.

Responsabilidades:
- Aplicar ediciones manuales a estudios
- Registrar trazabilidad como "manual"
- Revalidar estado de consolidación tras edición
- Validar que las ediciones sean válidas
"""

from typing import Dict, Any, Optional, List
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.repositories.i_study_repository import IStudyRepository
from apps.acquisition.metadata.domain.services.completeness_validator import CompletenessValidator
from apps.acquisition.metadata.domain.services.metadata_normalizer import MetadataNormalizer
from apps.acquisition.metadata.domain.value_objects.consolidation_status import ConsolidationStatus
from apps.acquisition.shared.domain.value_objects.doi import DOI


class ManualEditService:
    """
    Servicio de Aplicación para edición manual de metadatos.

    Permite editar campos específicos de un estudio marcando
    la trazabilidad como "manual". Después de cada edición,
    revalida el estado de consolidación.

    Use cases:
    - Completar DOI que no se encontró automáticamente
    - Corregir autores mal formateados
    - Agregar abstract que no estaba disponible en APIs
    - Corregir cualquier error de la consolidación automática
    """

    # Campos que pueden editarse manualmente
    EDITABLE_FIELDS = {
        "doi", "authors", "abstract", "year",
        "journal", "keywords", "title"
    }

    def __init__(self, repository: Optional[IStudyRepository] = None):
        """
        Inicializa el servicio con validador y normalizador.

        Args:
            repository: Repositorio de estudios (opcional, para métodos con persistencia)
        """
        self.validator = CompletenessValidator()
        self.normalizer = MetadataNormalizer()
        self.repository = repository

    def edit(
        self,
        study_id: str,
        field_name: str,
        value: Any,
        normalize: bool = True
    ) -> Study:
        """
        Edita un campo específico de un estudio (CON PERSISTENCIA).

        Args:
            study_id: ID del estudio a editar
            field_name: Nombre del campo a editar
            value: Nuevo valor para el campo
            normalize: Si se debe normalizar el valor (default True)

        Returns:
            Study con el campo editado y persistido

        Raises:
            ValueError: Si el estudio no existe
            ValueError: Si el campo no es editable o el valor es inválido

        Ejemplo:
            >>> service = Container.get_manual_edit_service()
            >>> study = service.edit(
            ...     study_id="uuid-123",
            ...     field_name="doi",
            ...     value="10.1234/example"
            ... )
            >>> study.doi.value
            '10.1234/example'
            >>> study.field_origins["doi"]
            'manual'
        """
        # 1. Recuperar estudio
        study = self._get_study_or_raise(study_id)

        # 2. Aplicar edición (lógica pura)
        self._edit_in_place(study, field_name, value, normalize)

        # 3. Persistir cambios
        saved_study = self.repository.save(study)

        return saved_study

    def edit_multiple(
        self,
        study_id: str,
        edits: Dict[str, Any],
        normalize: bool = True
    ) -> Study:
        """
        Edita múltiples campos de un estudio (CON PERSISTENCIA).

        Args:
            study_id: ID del estudio a editar
            edits: Diccionario {campo: valor} con las ediciones
            normalize: Si se deben normalizar los valores

        Returns:
            Study con los campos editados y persistido

        Raises:
            ValueError: Si el estudio no existe
            ValueError: Si algún campo no es editable o valor inválido

        Ejemplo:
            >>> service = Container.get_manual_edit_service()
            >>> study = service.edit_multiple(
            ...     study_id="uuid-123",
            ...     edits={
            ...         "doi": "10.1234/example",
            ...         "year": 2023,
            ...         "authors": ["Smith, J.", "Doe, A."]
            ...     }
            ... )
            >>> study.field_origins["doi"]
            'manual'
        """
        # 1. Recuperar estudio
        study = self._get_study_or_raise(study_id)

        # 2. Aplicar ediciones múltiples (lógica pura)
        self._edit_multiple_in_place(study, edits, normalize)

        # 3. Persistir cambios
        saved_study = self.repository.save(study)

        return saved_study

    def _apply_field_value(self, study: Study, field_name: str, value: Any) -> None:
        """
        Aplica un valor a un campo específico del estudio.

        Args:
            study: Estudio a modificar
            field_name: Nombre del campo
            value: Valor a aplicar

        Raises:
            ValueError: Si el valor no es válido para el campo
        """
        if field_name == "doi":
            self._set_doi(study, value)
        elif field_name == "authors":
            self._set_authors(study, value)
        elif field_name == "abstract":
            self._set_abstract(study, value)
        elif field_name == "year":
            self._set_year(study, value)
        elif field_name == "journal":
            self._set_journal(study, value)
        elif field_name == "keywords":
            self._set_keywords(study, value)
        elif field_name == "title":
            self._set_title(study, value)

    def _set_doi(self, study: Study, value: Any) -> None:
        """Establece el DOI del estudio."""
        if value is None or value == "":
            study.doi = None
            return

        if not isinstance(value, str):
            raise ValueError("El DOI debe ser un string")

        try:
            study.doi = DOI(value)
        except Exception as e:
            raise ValueError(f"DOI inválido: {str(e)}")

    def _set_authors(self, study: Study, value: Any) -> None:
        """Establece los autores del estudio."""
        if value is None:
            study.authors = None
            return

        if isinstance(value, str):
            # Convertir string separado por comas a lista
            authors = [a.strip() for a in value.split(",") if a.strip()]
            if not authors:
                raise ValueError("La lista de autores no puede estar vacía")
            study.authors = authors
        elif isinstance(value, list):
            # Validar que todos los elementos sean strings no vacíos
            authors = [str(a).strip() for a in value if a and str(a).strip()]
            if not authors:
                raise ValueError("La lista de autores no puede estar vacía")
            study.authors = authors
        else:
            raise ValueError("Los autores deben ser un string o una lista")

    def _set_abstract(self, study: Study, value: Any) -> None:
        """Establece el abstract del estudio."""
        if value is None or value == "":
            study.abstract = None
            return

        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        if not value:
            raise ValueError("El abstract no puede estar vacío")

        study.abstract = value

    def _set_year(self, study: Study, value: Any) -> None:
        """Establece el año del estudio."""
        if value is None:
            study.year = None
            return

        try:
            year_int = int(value)
            if not (1900 <= year_int <= 2100):
                raise ValueError(f"Año fuera de rango válido (1900-2100): {year_int}")
            study.year = year_int
        except (ValueError, TypeError) as e:
            raise ValueError(f"Año inválido: {str(e)}")

    def _set_journal(self, study: Study, value: Any) -> None:
        """Establece el journal/conferencia del estudio."""
        if value is None or value == "":
            study.journal = None
            return

        if not isinstance(value, str):
            value = str(value)

        study.journal = value.strip()

    def _set_keywords(self, study: Study, value: Any) -> None:
        """Establece las keywords del estudio."""
        if value is None:
            study.keywords = None
            return

        if isinstance(value, str):
            # Convertir string separado por comas a lista
            keywords = [k.strip() for k in value.split(",") if k.strip()]
            study.keywords = keywords if keywords else None
        elif isinstance(value, list):
            keywords = [str(k).strip() for k in value if k and str(k).strip()]
            study.keywords = keywords if keywords else None
        else:
            raise ValueError("Las keywords deben ser un string o una lista")

    def _set_title(self, study: Study, value: Any) -> None:
        """Establece el título del estudio."""
        if value is None or value == "":
            raise ValueError("El título no puede estar vacío")

        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        if not value:
            raise ValueError("El título no puede estar vacío")

        study.title = value

    def _normalize_field(self, study: Study, field_name: str) -> None:
        """
        Normaliza un campo específico del estudio.

        Args:
            study: Estudio con el campo a normalizar
            field_name: Nombre del campo a normalizar
        """
        try:
            if field_name == "doi" and study.doi:
                normalized = self.normalizer.normalize_doi(study.doi.value)
                if normalized:
                    study.doi = DOI(normalized)
            elif field_name == "authors" and study.authors:
                study.authors = self.normalizer.normalize_authors(study.authors)
            elif field_name == "year" and study.year is not None:
                normalized = self.normalizer.normalize_year(study.year)
                if normalized is not None:
                    study.year = normalized
            elif field_name == "abstract" and study.abstract:
                study.abstract = self.normalizer.normalize_text(study.abstract)
            elif field_name == "title" and study.title:
                study.title = self.normalizer.normalize_text(study.title)
            # journal y keywords no requieren normalización especial
        except Exception:
            # Si falla la normalización, mantener el valor original
            pass

    def get_editable_fields(self) -> List[str]:
        """
        Retorna la lista de campos editables.

        Returns:
            Lista de nombres de campos que pueden editarse
        """
        return sorted(list(self.EDITABLE_FIELDS))

    def get_edit_summary(self, study_id: str) -> Dict[str, Any]:
        """
        Genera un resumen del estado de edición de un estudio.

        Args:
            study_id: ID del estudio a analizar

        Returns:
            Diccionario con información de campos editados manualmente

        Raises:
            ValueError: Si el estudio no existe
        """
        study = self._get_study_or_raise(study_id)
        return self._build_edit_summary(study)

    # ==========================================================================
    # HELPERS PRIVADOS (lógica pura en memoria)
    # ==========================================================================

    def _get_study_or_raise(self, study_id: str) -> Study:
        """Recupera estudio o lanza excepción."""
        study = self.repository.find_by_id(study_id)
        if study is None:
            raise ValueError(f"Estudio no encontrado: {study_id}")
        return study

    def _edit_in_place(
        self,
        study: Study,
        field_name: str,
        value: Any,
        normalize: bool
    ) -> None:
        """Aplica edición de un campo en el objeto Study (en memoria)."""
        # Validar que el campo sea editable
        if field_name not in self.EDITABLE_FIELDS:
            raise ValueError(
                f"El campo '{field_name}' no es editable. "
                f"Campos permitidos: {', '.join(sorted(self.EDITABLE_FIELDS))}"
            )

        # Validar y aplicar el valor
        self._apply_field_value(study, field_name, value)

        # Normalizar si está habilitado
        if normalize:
            self._normalize_field(study, field_name)

        # Registrar trazabilidad
        study.field_origins[field_name] = "manual"

        # Revalidar estado de consolidación
        new_status = self.validator.validate(study)
        study.consolidation_status = new_status.value

    def _edit_multiple_in_place(
        self,
        study: Study,
        edits: Dict[str, Any],
        normalize: bool
    ) -> None:
        """Aplica ediciones múltiples en el objeto Study (en memoria)."""
        if not edits:
            return

        # Validar todos los campos antes de aplicar
        invalid_fields = set(edits.keys()) - self.EDITABLE_FIELDS
        if invalid_fields:
            raise ValueError(
                f"Campos no editables: {', '.join(sorted(invalid_fields))}. "
                f"Campos permitidos: {', '.join(sorted(self.EDITABLE_FIELDS))}"
            )

        # Aplicar todas las ediciones
        for field_name, value in edits.items():
            self._apply_field_value(study, field_name, value)

            # Normalizar si está habilitado
            if normalize:
                self._normalize_field(study, field_name)

            # Registrar trazabilidad
            study.field_origins[field_name] = "manual"

        # Revalidar estado de consolidación (una sola vez)
        new_status = self.validator.validate(study)
        study.consolidation_status = new_status.value

    def _build_edit_summary(self, study: Study) -> Dict[str, Any]:
        """Construye resumen de edición de un estudio."""
        manual_fields = [
            field for field, origin in study.field_origins.items()
            if origin == "manual"
        ]

        automatic_fields = [
            field for field, origin in study.field_origins.items()
            if origin == "automatic"
        ]

        discovery_fields = [
            field for field, origin in study.field_origins.items()
            if origin == "discovery"
        ]

        return {
            "consolidation_status": study.consolidation_status,
            "total_fields": len(study.field_origins),
            "manual_count": len(manual_fields),
            "automatic_count": len(automatic_fields),
            "discovery_count": len(discovery_fields),
            "manual_fields": manual_fields,
            "automatic_fields": automatic_fields,
            "discovery_fields": discovery_fields,
            "missing_fields": self.validator.get_missing_fields(study),
        }

