"""
Normalization functions for deduplication.

PRINCIPIOS:
- Una sola fuente de verdad para normalización
- Usadas tanto por Deduplicator como por steps de validación
- Funciones puras sin efectos secundarios
- Lógica determinista y reproducible
"""

import re
import unicodedata


def normalize_title(title: str) -> str:
    """
    Normalize a study title for deduplication.

    Aplica las siguientes transformaciones:
    1. Convierte a minúsculas
    2. Remueve acentos y diacríticos (normalización Unicode NFD)
    3. Elimina puntuación y caracteres especiales
    4. Normaliza espacios múltiples a uno solo
    5. Trim inicial y final

    Args:
        title: The raw title to normalize

    Returns:
        The normalized title for comparison

    Ejemplos:
        >>> normalize_title("Machine Learning: A Survey")
        'machine learning a survey'

        >>> normalize_title("  Deep   Learning   ")
        'deep learning'

        >>> normalize_title("Café, Niño & Señor")
        'cafe nino senor'
    """
    if not title:
        return ""

    # 1. Normalización Unicode: descomponer caracteres acentuados (NFD)
    # Ejemplo: 'é' -> 'e' + acento
    normalized = unicodedata.normalize('NFD', title)

    # 2. Remover marcas diacríticas (categoría Mn = Nonspacing_Mark)
    # Esto elimina los acentos separados en el paso anterior
    no_accents = ''.join(
        char for char in normalized
        if unicodedata.category(char) != 'Mn'
    )

    # 3. Convertir a minúsculas
    lowercased = no_accents.lower()

    # 4. Remover puntuación y caracteres especiales (mantener solo alfanuméricos y espacios)
    # Esto maneja casos como "Machine Learning: A Survey" -> "machine learning a survey"
    alphanumeric_only = re.sub(r'[^a-z0-9\s]', ' ', lowercased)

    # 5. Normalizar espacios múltiples a uno solo
    single_spaced = re.sub(r'\s+', ' ', alphanumeric_only)

    # 6. Trim
    result = single_spaced.strip()

    return result


def normalize_doi(raw: str) -> str:
    """
    Normalize a DOI string for deduplication.

    Aplica las siguientes transformaciones:
    1. Convierte a minúsculas
    2. Remueve prefijos comunes: "doi:", "https://doi.org/", "http://dx.doi.org/"
    3. Trim

    Args:
        raw: The raw DOI string (e.g., "DOI:10.1234/example", "https://doi.org/10.1234/example")

    Returns:
        The normalized DOI for comparison (e.g., "10.1234/example")

    Ejemplos:
        >>> normalize_doi("DOI:10.1234/example")
        '10.1234/example'

        >>> normalize_doi("https://doi.org/10.1234/example")
        '10.1234/example'

        >>> normalize_doi("  10.1234/EXAMPLE  ")
        '10.1234/example'

        >>> normalize_doi("http://dx.doi.org/10.1234/example")
        '10.1234/example'
    """
    if not raw:
        return ""

    # 1. Trim inicial
    normalized = raw.strip()

    # 2. Convertir a minúsculas
    normalized = normalized.lower()

    # 3. Remover prefijos comunes (en orden de más específico a menos específico)
    prefixes = [
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi.org/",
        "dx.doi.org/",
        "doi:",
    ]

    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break  # Solo remover el primer prefijo encontrado

    # 4. Trim final (por si había espacios después del prefijo)
    normalized = normalized.strip()

    return normalized
