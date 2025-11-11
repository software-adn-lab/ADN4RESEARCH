"""
Deduplicator service for removing duplicate studies.

ESTRATEGIA:
1. DOI normalizado tiene prioridad sobre título
2. Si un estudio tiene DOI, se usa como clave de deduplicación
3. Si no tiene DOI, se usa el título normalizado
4. Se mantiene la primera ocurrencia de cada duplicado

EDGE CASE CONOCIDO (Record Linkage):
Si el estudio A tiene DOI y el estudio B (mismo paper) no tiene DOI:
- A -> key: "doi::10.1234/abc"
- B -> key: "title::machine learning"
- NO se detectarán como duplicados (diferentes claves)

Esto es una limitación conocida de la estrategia de "single-pass deduplication".
Para MVP es aceptable. Para producción avanzada, considerar:
- Estrategia de doble pasada (agrupar por DOI, luego por título, luego cruzar)
- Fuzzy matching de títulos para variaciones menores
- Clustering jerárquico de registros

Documentado para: Revisión técnica pre-producción
"""

from apps.acquisition.domain.entities.study import Study
from .normalizers import normalize_title, normalize_doi


class Deduplicator:
    """
    Service for deduplicating studies based on title and DOI.

    Usa las funciones de normalización del dominio (única fuente de verdad).

    Estrategia de deduplicación:
    - DOI tiene prioridad sobre título (más confiable)
    - Primera ocurrencia se mantiene (preserva orden de descubrimiento)
    - Normalización case-insensitive y sin acentos
    """

    def deduplicate(self, studies: list[Study]) -> list[Study]:
        """
        Remove duplicate studies from the list.

        Reglas:
        1. Si estudio tiene DOI: clave = "doi::{normalize_doi(doi)}"
        2. Si no tiene DOI: clave = "title::{normalize_title(title)}"
        3. Primera ocurrencia se mantiene, siguientes se descartan

        Args:
            studies: List of studies to deduplicate

        Returns:
            List of unique studies (mantiene orden de entrada)

        Ejemplos:
            >>> s1 = Study(title="Machine Learning", link="url1", source="Scopus", doi="10.1234/abc")
            >>> s2 = Study(title="Machine Learning", link="url2", source="IEEE", doi="10.1234/abc")
            >>> dedup = Deduplicator()
            >>> result = dedup.deduplicate([s1, s2])
            >>> len(result)
            1
            >>> result[0].source
            'Scopus'
        """
        if not studies:
            return []

        seen_keys: dict[str, bool] = {}
        unique_studies: list[Study] = []

        for study in studies:
            # Determinar clave de deduplicación
            if study.doi:
                # DOI tiene prioridad
                key = f"doi::{normalize_doi(study.doi)}"
            else:
                # Fallback a título
                key = f"title::{normalize_title(study.title)}"

            # Si no hemos visto esta clave, mantener el estudio
            if key not in seen_keys:
                seen_keys[key] = True
                unique_studies.append(study)
            # else: duplicado, se descarta silenciosamente

        return unique_studies
