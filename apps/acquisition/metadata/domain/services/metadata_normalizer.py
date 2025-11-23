"""
MetadataNormalizer - Servicio de normalización de metadatos.

Responsabilidad única: Estandarizar formatos de datos para garantizar
consistencia en la base de datos y facilitar búsquedas/comparaciones.

Reglas de normalización:
- DOI: minúsculas, sin prefijos URL, sin espacios
- Autores: Title Case, formato "Apellido, Nombre"
- Año: entero válido
- Abstract: texto limpio sin espacios extras

NOTA: Este normalizador es diferente de shared/normalizers.py:
- shared/normalizers.py: Normalización AGRESIVA para deduplicación/comparación
  (remueve acentos, puntuación, etc.)
- Este servicio: Normalización CONSERVADORA para limpieza de datos
  (preserva estructura, solo limpia)
"""

import re
import unicodedata
from typing import List, Any, Optional
from apps.acquisition.shared.domain.entities.study import Study
from apps.acquisition.shared.domain.value_objects.doi import DOI
# Importar función de normalización compartida para DOI
from apps.acquisition.shared.domain.normalizers import normalize_doi as normalize_doi_basic


class MetadataNormalizer:
    """
    Servicio de dominio encargado de estandarizar los formatos de metadatos.

    Este servicio es idempotente: aplicarlo múltiples veces produce el mismo resultado.
    Es tolerante a fallos: si un campo no puede normalizarse, mantiene el valor original.

    DELEGACIÓN:
    - Normalización de DOI básica delegada a shared/normalizers.py
    - Luego aplica limpieza adicional específica de metadatos
    """

    def normalize(self, study: Study) -> Study:
        """
        Aplica todas las reglas de normalización a un estudio.

        Args:
            study: Estudio a normalizar

        Returns:
            El mismo estudio con campos normalizados (modificado in-place)

        Note:
            Esta operación es tolerante a fallos. Si un campo no puede
            normalizarse, se mantiene el valor original y se continúa.
        """
        # 1. Normalizar DOI
        if study.doi:
            try:
                normalized_doi_str = self.normalize_doi(study.doi.value)
                if normalized_doi_str:
                    study.doi = DOI(normalized_doi_str)
            except Exception:
                # Mantener DOI original si falla la normalización
                pass

        # 2. Normalizar Autores
        if study.authors:
            try:
                study.authors = self.normalize_authors(study.authors)
            except Exception:
                # Mantener autores originales si falla
                pass

        # 3. Normalizar Año
        if study.year is not None:
            try:
                normalized_year = self.normalize_year(study.year)
                if normalized_year is not None:
                    study.year = normalized_year
            except Exception:
                pass

        # 4. Normalizar Abstract
        if study.abstract:
            try:
                study.abstract = self.normalize_text(study.abstract)
            except Exception:
                pass

        # 5. Normalizar Título
        if study.title:
            try:
                study.title = self.normalize_text(study.title)
            except Exception:
                pass

        return study

    def normalize_doi(self, doi: str) -> str:
        """
        Normaliza un DOI según estándares.

        Delega a la función básica de shared/normalizers.py y luego
        aplica limpieza adicional de Unicode y caracteres de control.

        Reglas:
        - Minúsculas (delegado a shared)
        - Sin espacios al inicio/final (delegado a shared)
        - Sin prefijos de URL (delegado a shared)
        - Sin caracteres de control (adicional)
        - Normalización Unicode (adicional)

        Args:
            doi: DOI en cualquier formato

        Returns:
            DOI normalizado (ej: "10.1000/xyz.123")

        Examples:
            >>> normalizer.normalize_doi("HTTPS://DOI.ORG/10.1000/XYZ")
            "10.1000/xyz"
            >>> normalizer.normalize_doi("  doi:10.1234/ABC  ")
            "10.1234/abc"
        """
        if not doi:
            return ""

        # 1. Aplicar normalización básica (delegada a shared kernel)
        clean = normalize_doi_basic(doi)

        # 2. Aplicar limpieza adicional específica de metadata
        # Normalizar Unicode NFKC (compatibilidad)
        clean = unicodedata.normalize("NFKC", clean)

        # Remover caracteres de control
        clean = "".join(c for c in clean if not unicodedata.category(c).startswith("C"))

        # Trim final por si la limpieza Unicode generó espacios
        clean = clean.strip()

        return clean

    def normalize_authors(self, authors: List[str]) -> List[str]:
        """
        Normaliza lista de autores a formato consistente.

        Reglas:
        - Title Case (Primera letra mayúscula)
        - Preservar estructura "Apellido, Nombre"
        - Limpiar espacios extras
        - Remover autores vacíos

        Args:
            authors: Lista de nombres de autores

        Returns:
            Lista de autores normalizados

        Examples:
            >>> normalizer.normalize_authors(["LOPEZ, MARIA", "juan perez"])
            ["Lopez, Maria", "Juan Perez"]
        """
        if not authors:
            return []

        normalized = []
        for author in authors:
            if not author:
                continue

            # Limpiar espacios
            clean = " ".join(author.split())

            if not clean:
                continue

            # Aplicar Title Case inteligente
            # Preservar la coma si existe (formato Apellido, Nombre)
            if "," in clean:
                parts = clean.split(",", 1)
                formatted = ", ".join(part.strip().title() for part in parts)
            else:
                formatted = clean.title()

            # Corregir partículas comunes que no deberían capitalizarse
            # (de, del, von, van, etc.) - pero solo en medio del nombre
            formatted = self._fix_name_particles(formatted)

            normalized.append(formatted)

        return normalized

    def _fix_name_particles(self, name: str) -> str:
        """
        Corrige capitalización de partículas en nombres.

        Partículas como "de", "del", "von", "van" no deberían
        capitalizarse cuando están en medio del nombre.
        """
        particles = ["De", "Del", "Von", "Van", "Der", "Den", "La", "Las", "Los"]
        words = name.split()

        for i, word in enumerate(words):
            # No corregir la primera palabra
            if i > 0 and word in particles:
                words[i] = word.lower()

        return " ".join(words)

    def normalize_year(self, year: Any) -> Optional[int]:
        """
        Normaliza año a entero válido.

        Args:
            year: Año en cualquier formato (str, int, float)

        Returns:
            Año como entero o None si no es válido

        Examples:
            >>> normalizer.normalize_year("2023")
            2023
            >>> normalizer.normalize_year(2023.0)
            2023
            >>> normalizer.normalize_year("invalid")
            None
        """
        if year is None:
            return None

        try:
            year_int = int(float(str(year).strip()))

            # Validar rango razonable (1900-2100)
            if 1900 <= year_int <= 2100:
                return year_int
            else:
                return None

        except (ValueError, TypeError):
            return None

    def normalize_text(self, text: str) -> str:
        """
        Normaliza texto general (títulos, abstracts).

        Reglas:
        - Remover marcadores de IEEE [::Machine::], [::Automation::]
        - Remover espacios extras
        - Normalizar Unicode
        - Remover caracteres de control

        Args:
            text: Texto a normalizar

        Returns:
            Texto limpio
        """
        if not text:
            return ""

        # Remover marcadores de IEEE (ej: [::Machine::], [::Deep Learning::])
        clean = re.sub(r'\[::[^\]]*::\]', '', text)

        # Normalizar Unicode
        clean = unicodedata.normalize("NFKC", clean)

        # Remover caracteres de control excepto newlines
        clean = "".join(
            c for c in clean
            if not unicodedata.category(c).startswith("C") or c in "\n\r\t"
        )

        # Normalizar espacios (múltiples espacios a uno)
        clean = " ".join(clean.split())

        return clean.strip()
