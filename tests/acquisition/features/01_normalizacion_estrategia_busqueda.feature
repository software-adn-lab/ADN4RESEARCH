# language: es
@modulo:busqueda @componente:traduccion @mvp
Característica: Traducción automática de estrategias de búsqueda según la base de datos académica
  Como investigador 
  Quiero que mi estrategia de búsqueda se adapte automáticamente a la sintaxis de cada base de datos
  Para poder buscar en múltiples fuentes sin tener que reescribir manualmente cada consulta

  Antecedentes:
    Dada una estrategia de búsqueda normalizada estructurada
    """json
    {
      "strategy_id": "slr_ml_software_2024",
      "main_terms": [
      {
        "term": "machine learning",
        "synonyms": ["deep learning", "ML", "artificial intelligence"]
      },
      {
        "term": "software engineering",
        "synonyms": ["software development", "software quality"]
      },
      {
        "term": "bug prediction",
        "synonyms": ["defect prediction", "fault prediction"]
      }
      ],
      "exclusions": [
      "hardware testing",
      "gaming",
      "mobile applications"
      ],
      "filters": {
      "year": {
        "from": 2020,
        "to": 2024
      }
      }
    }
    """

  Esquema del escenario: Traducción de estrategia para diferentes bases de datos académicas
    Cuando solicito traducir mi estrategia de búsqueda para "<base_datos>"
    Entonces obtengo una consulta traducida compatible con la sintaxis de <base_datos>
    """
    <consulta_traducida>
    """
    Y la consulta traducida preserva la lógica de mi estrategia original
    Y el estado de la traducción es "Done"
    Y se registra la trazabilidad de la traducción
    Y <advertencias>

    Ejemplos:
      | base_datos   | consulta_traducida                                                                                                                                                                                                                                                                                                  | advertencias                                                                                   |
      | Scopus       | TITLE-ABS-KEY((("machine learning" OR "deep learning" OR "ML" OR "artificial intelligence") AND ("software engineering" OR "software development" OR "software quality") AND ("bug prediction" OR "defect prediction" OR "fault prediction")) AND NOT ("hardware testing" OR "gaming" OR "mobile applications")) AND PUBYEAR > 2019 AND PUBYEAR < 2025 | no se emiten advertencias                                                                      |
      | IEEE Xplore  | ((("machine learning" OR "deep learning" OR "ML" OR "artificial intelligence") AND ("software engineering" OR "software development" OR "software quality") AND ("bug prediction" OR "defect prediction" OR "fault prediction")) NOT ("hardware testing" OR "gaming" OR "mobile applications"))                    | se emite una advertencia indicando aplicar el filtro de año 2020-2024 manualmente en la interfaz |





