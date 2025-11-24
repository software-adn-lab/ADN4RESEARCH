"""
MetadataMatcher - Servicio compartido para validación de coincidencia de metadatos.

Este servicio proporciona algoritmos de matching reutilizables para validar
que los resultados de búsqueda (Crossref, Scopus, etc.) correspondan
al estudio que estamos buscando.

Evita falsos positivos mediante validación multi-criterio:
- Similitud de título (Jaccard)
- Coincidencia de autores (apellidos)
- Coincidencia de año (con tolerancia)
"""

import re
import unicodedata
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MatchResult:
    """Resultado del matching con score y detalles."""
    is_match: bool
    score: float
    title_score: float
    author_adjustment: float
    year_adjustment: float
    candidate: Optional[Dict[str, Any]] = None


class MetadataMatcher:
    """
    Servicio para validar coincidencia entre metadatos buscados y encontrados.

    Usa sistema de scoring multi-criterio:
    - Título: 0.0 - 1.0 (similitud Jaccard)
    - Autores: +0.3 bonus o -0.2 penalización
    - Año: +0.2 bonus o -0.15 penalización

    Uso:
        matcher = MetadataMatcher()
        result = matcher.find_best_match(
            candidates=crossref_results,
            search_title="Deep Learning for Testing",
            search_authors=["Smith", "Doe"],
            search_year=2020
        )

        if result.is_match:
            print(f"Match encontrado con score {result.score}")
    """

    # Umbrales de matching
    MIN_TITLE_SIMILARITY = 0.6   # Mínimo para considerar el título
    MIN_COMBINED_SCORE = 0.7     # Mínimo para aceptar un match

    def find_best_match(
        self,
        candidates: List[Dict[str, Any]],
        search_title: str,
        search_authors: Optional[List[str]] = None,
        search_year: Optional[int] = None,
        title_key: str = "title",
        authors_key: str = "authors",
        year_key: str = "year"
    ) -> MatchResult:
        """
        Evalúa candidatos y encuentra el mejor match.

        Args:
            candidates: Lista de candidatos (dicts con metadatos)
            search_title: Título que buscamos
            search_authors: Autores para validación cruzada (opcional)
            search_year: Año para validación cruzada (opcional)
            title_key: Key del título en los candidatos
            authors_key: Key de autores en los candidatos
            year_key: Key del año en los candidatos

        Returns:
            MatchResult con el mejor candidato o is_match=False
        """
        best_candidate = None
        best_score = 0.0
        best_title_score = 0.0
        best_author_adj = 0.0
        best_year_adj = 0.0

        for item in candidates:
            found_title = item.get(title_key)
            found_authors = item.get(authors_key)
            found_year = item.get(year_key)

            # 1. Calcular similitud de título (base)
            title_score = self.calculate_title_similarity(search_title, found_title)

            if title_score < self.MIN_TITLE_SIMILARITY:
                continue  # Título muy diferente, descartar

            # 2. Calcular ajuste por autores
            author_adjustment = 0.0
            if search_authors and found_authors:
                author_sim = self.calculate_author_similarity(search_authors, found_authors)
                if author_sim >= 0.5:
                    author_adjustment = author_sim * 0.3  # Bonus si coinciden
                else:
                    author_adjustment = -0.2  # Penalizar si NO coinciden

            # 3. Calcular ajuste por año
            year_adjustment = 0.0
            if search_year and found_year:
                try:
                    year_int = int(found_year) if not isinstance(found_year, int) else found_year
                    if search_year == year_int:
                        year_adjustment = 0.2  # Bonus año exacto
                    elif abs(search_year - year_int) <= 1:
                        year_adjustment = 0.1  # Tolerancia de 1 año
                    else:
                        year_adjustment = -0.15  # Penalizar si difiere mucho
                except (ValueError, TypeError):
                    pass

            # Score combinado
            combined_score = title_score + author_adjustment + year_adjustment

            if combined_score > best_score:
                best_score = combined_score
                best_candidate = item
                best_title_score = title_score
                best_author_adj = author_adjustment
                best_year_adj = year_adjustment

        # Verificar umbral mínimo
        is_match = best_candidate is not None and best_score >= self.MIN_COMBINED_SCORE

        return MatchResult(
            is_match=is_match,
            score=round(best_score, 3),
            title_score=round(best_title_score, 3),
            author_adjustment=round(best_author_adj, 3),
            year_adjustment=round(best_year_adj, 3),
            candidate=best_candidate if is_match else None
        )

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calcula similitud entre dos títulos usando Jaccard.

        Args:
            title1: Primer título
            title2: Segundo título

        Returns:
            Score entre 0.0 y 1.0
        """
        if not title1 or not title2:
            return 0.0

        t1 = self._normalize_for_comparison(title1)
        t2 = self._normalize_for_comparison(title2)

        words1 = set(t1.split())
        words2 = set(t2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def calculate_author_similarity(
        self,
        authors1: List[str],
        authors2: List[str]
    ) -> float:
        """
        Calcula similitud entre dos listas de autores.

        Compara apellidos normalizados.

        Args:
            authors1: Primera lista de autores
            authors2: Segunda lista de autores

        Returns:
            Score entre 0.0 y 1.0
        """
        if not authors1 or not authors2:
            return 0.0

        # Extraer apellidos y normalizar
        surnames1 = set()
        for author in authors1:
            surname = self._extract_surname(author)
            if surname:
                surnames1.add(surname)

        surnames2 = set()
        for author in authors2:
            surname = self._extract_surname(author)
            if surname:
                surnames2.add(surname)

        if not surnames1 or not surnames2:
            return 0.0

        # Contar cuántos apellidos coinciden
        matches = len(surnames1 & surnames2)
        total = max(len(surnames1), len(surnames2))

        return matches / total if total > 0 else 0.0

    def _extract_surname(self, author: str) -> Optional[str]:
        """
        Extrae el apellido de un autor.

        Maneja formatos:
        - "Apellido, Nombre"
        - "Nombre Apellido"
        """
        if not author:
            return None

        author = self._normalize_for_comparison(author)

        # Si tiene coma, el apellido está primero
        if "," in author:
            parts = author.split(",")
            return parts[0].strip()

        # Si no, asumir que el último es el apellido
        parts = author.split()
        if parts:
            return parts[-1].strip()

        return None

    def _normalize_for_comparison(self, text: str) -> str:
        """
        Normaliza texto para comparación.

        Remueve acentos, puntuación, convierte a minúsculas.
        """
        if not text:
            return ""

        # Remover acentos
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')

        # Minúsculas
        text = text.lower()

        # Remover puntuación y caracteres especiales
        text = re.sub(r'[^\w\s]', ' ', text)

        # Remover espacios múltiples
        text = re.sub(r'\s+', ' ', text)

        return text.strip()
