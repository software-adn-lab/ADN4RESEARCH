"""
Deduplicator service for removing duplicate studies.

ESTRATEGIA:
1. DOI normalizado tiene prioridad sobre título
2. Si un estudio tiene DOI, se usa como clave de deduplicación
3. Si no tiene DOI, se usa el título normalizado
4. Se mantiene la primera ocurrencia de cada duplicado
"""
from typing import List, Dict

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

    def deduplicate(self, studies: List[Study]) -> List[Study]:
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

        seen_keys: Dict[str, bool] = {}
        unique_studies: List[Study] = []

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
