"""
Deduplicator service for removing duplicate studies with intelligent merging.

ESTRATEGIA (2-Pass + Fusion):
1. Primera pasada: Indexar por DOI (más confiable)
2. Segunda pasada: Indexar por título normalizado
3. Fusión inteligente: Si mismo título pero uno tiene DOI y otro no,
   enriquece el registro sin DOI con el DOI encontrado

EDGE CASE RESUELTO (Record Linkage):
Si el estudio A tiene DOI y el estudio B (mismo paper) no tiene DOI:
- A -> DOI: "10.1234/abc", Title: "Machine Learning"
- B -> DOI: None, Title: "Machine Learning"
→ Resultado: 1 estudio con DOI="10.1234/abc" (fusionado)

La fusión permite:
- Enriquecer datos automáticamente
- Evitar duplicados cross-source (Scopus con DOI + IEEE sin DOI)
- Maximizar calidad de metadatos

MEJORAS FUTURAS (si es necesario):
- Fuzzy matching de títulos para variaciones menores (Levenshtein distance)
- Clustering jerárquico de registros
- Fusión de otros campos (autores, abstract, etc.)
"""

from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.normalizers import normalize_title, normalize_doi


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
        Remove duplicate studies from the list with intelligent merging.

        Estrategia de 2 pasadas + fusión:
        1. Primera pasada: agrupa por DOI (más confiable)
        2. Segunda pasada: agrupa por título normalizado
        3. Fusión: si encontramos mismo título pero uno tiene DOI y otro no,
           enriquece el registro sin DOI con el DOI encontrado

        Esto resuelve el edge case:
        - Scopus: "Machine Learning" DOI=10.1234/abc
        - IEEE:   "Machine Learning" DOI=None
        → Resultado: 1 estudio con DOI=10.1234/abc (fusionado)

        Args:
            studies: List of studies to deduplicate

        Returns:
            List of unique studies (mantiene orden, enriquecidos con fusión)

        Ejemplos:
            >>> s1 = Study(title="Machine Learning", link="url1", source="Scopus", doi="10.1234/abc")
            >>> s2 = Study(title="Machine Learning", link="url2", source="IEEE", doi=None)
            >>> dedup = Deduplicator()
            >>> result = dedup.deduplicate([s1, s2])
            >>> len(result)
            1
            >>> result[0].doi.value
            '10.1234/abc'
        """
        if not studies:
            return []

        # Paso 1: Indexar por DOI (los que tienen)
        by_doi: dict[str, Study] = {}
        by_title: dict[str, Study] = {}
        result: list[Study] = []

        for study in studies:
            # Si tiene DOI, indexar por DOI
            if study.doi:
                doi_key = normalize_doi(study.doi.value)
                if doi_key not in by_doi:
                    by_doi[doi_key] = study
                    result.append(study)
                # else: duplicado por DOI, ignorar
            else:
                # Si no tiene DOI, indexar por título
                title_key = normalize_title(study.title)
                if title_key not in by_title:
                    by_title[title_key] = study
                    result.append(study)
                # else: duplicado por título, ignorar

        # Paso 2: Fusión inteligente
        # Para cada estudio sin DOI, verificar si existe uno con DOI y mismo título
        for title_key, study_without_doi in list(by_title.items()):
            # Buscar en by_doi si hay alguno con el mismo título
            for study_with_doi in by_doi.values():
                if normalize_title(study_with_doi.title) == title_key:
                    # ¡Encontramos el mismo paper!
                    # Enriquecer el estudio sin DOI con el DOI del otro
                    from apps.acquisition.shared.domain.value_objects import DOI
                    study_without_doi.doi = DOI(study_with_doi.doi.value)

                    # Remover de resultado para evitar duplicado
                    # (el que tiene DOI ya está en resultado)
                    if study_without_doi in result:
                        result.remove(study_without_doi)

                    break  # Ya encontramos match, salir del loop

        return result
