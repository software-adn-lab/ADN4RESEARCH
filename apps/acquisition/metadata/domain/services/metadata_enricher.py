"""
MetadataEnricher - Servicio de enriquecimiento de metadatos.

Responsabilidad única: Buscar y completar metadatos faltantes consultando
fuentes académicas externas (Scopus, IEEE, etc.).

Este servicio es el "detective" que:
1. Identifica qué campos faltan en un estudio
2. Consulta las APIs de las fuentes académicas
3. Completa los campos faltantes con los datos encontrados
4. Registra la trazabilidad (origen de cada dato)
"""

from typing import Dict, Any, Optional, List
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.doi import DOI


class MetadataEnricher:
    """
    Servicio de dominio que busca y completa metadatos faltantes.

    Utiliza conectores externos (inyectados) para consultar APIs de
    fuentes académicas y recuperar información que falta en los estudios.

    Attributes:
        connectors: Diccionario de conectores por fuente
                   {"Scopus": ScopusConnector, "IEEE Xplore": IeeeConnector}
    """

    # Campos que se pueden enriquecer automáticamente
    ENRICHABLE_FIELDS = {"doi", "abstract", "authors", "year", "journal", "keywords"}

    def __init__(self, connectors: Dict[str, Any] = None):
        """
        Inicializa el enricher con conectores.

        Args:
            connectors: Diccionario de conectores por nombre de fuente
        """
        self.connectors = connectors or {}

    def enrich(self, study: Study) -> Study:
        """
        Intenta completar los metadatos faltantes de un estudio.

        Proceso:
        1. Identifica campos faltantes
        2. Busca en la fuente original del estudio
        3. Si no encuentra, busca en otras fuentes
        4. Actualiza el estudio y registra trazabilidad

        Args:
            study: Estudio a enriquecer

        Returns:
            El mismo estudio con metadatos completados (modificado in-place)

        Note:
            Es tolerante a fallos. Si una fuente falla, continúa con las otras.
            Nunca sobrescribe datos existentes.
        """
        missing_fields = self._get_missing_enrichable_fields(study)

        if not missing_fields:
            # No hay nada que enriquecer
            return study

        # 1. Intentar con la fuente original del estudio
        primary_source = study.source.name if study.source else None
        if primary_source and primary_source in self.connectors:
            metadata = self._fetch_metadata(primary_source, study)
            if metadata:
                self._apply_metadata(study, metadata, source="automatic")
                # Actualizar lista de campos faltantes
                missing_fields = self._get_missing_enrichable_fields(study)

        # 2. Si aún faltan campos, intentar con otras fuentes
        if missing_fields:
            for source_name, connector in self.connectors.items():
                if source_name == primary_source:
                    continue  # Ya probamos esta

                metadata = self._fetch_metadata(source_name, study)
                if metadata:
                    self._apply_metadata(study, metadata, source="automatic")
                    missing_fields = self._get_missing_enrichable_fields(study)

                    if not missing_fields:
                        break  # Ya completamos todo

        return study

    def _get_missing_enrichable_fields(self, study: Study) -> List[str]:
        """
        Identifica qué campos enriquecibles están faltantes.

        Args:
            study: Estudio a analizar

        Returns:
            Lista de nombres de campos faltantes que se pueden enriquecer
        """
        missing = []

        if not study.doi or not study.doi.value:
            missing.append("doi")
        if not study.abstract:
            missing.append("abstract")
        if not study.authors:
            missing.append("authors")
        if not study.year:
            missing.append("year")
        if not study.journal:
            missing.append("journal")
        if not study.keywords:
            missing.append("keywords")

        return [f for f in missing if f in self.ENRICHABLE_FIELDS]

    def _fetch_metadata(self, source_name: str, study: Study) -> Optional[Dict[str, Any]]:
        """
        Consulta una fuente para obtener metadatos.

        Args:
            source_name: Nombre de la fuente (ej: "Scopus")
            study: Estudio del que buscar metadatos

        Returns:
            Diccionario con metadatos encontrados o None si falla
        """
        connector = self.connectors.get(source_name)
        if not connector:
            return None

        try:
            # El conector debe tener método find_metadata(title) -> dict
            if hasattr(connector, "find_metadata"):
                return connector.find_metadata(study.title)
            else:
                return None

        except Exception:
            # Tolerancia a fallos: si el conector falla, continuamos
            return None

    def _apply_metadata(
        self,
        study: Study,
        metadata: Dict[str, Any],
        source: str = "automatic"
    ) -> None:
        """
        Aplica metadatos encontrados al estudio.

        Solo completa campos que están vacíos (no sobrescribe).
        Registra la trazabilidad de cada campo actualizado.

        Args:
            study: Estudio a actualizar
            metadata: Diccionario con metadatos
            source: Origen de los datos ("automatic", "manual", "discovery")
        """
        if not metadata:
            return

        # DOI
        if "doi" in metadata and metadata["doi"]:
            if not study.doi or not study.doi.value:
                try:
                    study.doi = DOI(metadata["doi"])
                    study.field_origins["doi"] = source
                except Exception:
                    pass

        # Abstract
        if "abstract" in metadata and metadata["abstract"]:
            if not study.abstract:
                study.abstract = str(metadata["abstract"])
                study.field_origins["abstract"] = source

        # Authors
        if "authors" in metadata and metadata["authors"]:
            if not study.authors:
                authors = metadata["authors"]
                if isinstance(authors, list):
                    study.authors = authors
                elif isinstance(authors, str):
                    # Separar por coma si viene como string
                    study.authors = [a.strip() for a in authors.split(",")]
                study.field_origins["authors"] = source

        # Year
        if "year" in metadata and metadata["year"]:
            if not study.year:
                try:
                    study.year = int(metadata["year"])
                    study.field_origins["year"] = source
                except (ValueError, TypeError):
                    pass

        # Journal
        if "journal" in metadata and metadata["journal"]:
            if not study.journal:
                study.journal = str(metadata["journal"])
                study.field_origins["journal"] = source

        # Keywords
        if "keywords" in metadata and metadata["keywords"]:
            if not study.keywords:
                keywords = metadata["keywords"]
                if isinstance(keywords, list):
                    study.keywords = keywords
                elif isinstance(keywords, str):
                    study.keywords = [k.strip() for k in keywords.split(",")]
                study.field_origins["keywords"] = source

    def get_enrichment_summary(self, study: Study) -> Dict[str, Any]:
        """
        Genera un resumen del estado de enriquecimiento de un estudio.

        Args:
            study: Estudio a analizar

        Returns:
            Diccionario con información del enriquecimiento
        """
        missing = self._get_missing_enrichable_fields(study)
        enriched = [
            field for field in self.ENRICHABLE_FIELDS
            if field not in missing
        ]

        return {
            "total_enrichable": len(self.ENRICHABLE_FIELDS),
            "enriched_count": len(enriched),
            "missing_count": len(missing),
            "enriched_fields": enriched,
            "missing_fields": missing,
            "field_origins": study.field_origins.copy(),
        }
