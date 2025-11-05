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
      "id_estrategia": "slr_ml_software_2024",
      "terminos_principales": [
        {
          "termino": "machine learning",
          "sinonimos": ["deep learning", "ML", "artificial intelligence"]
        },
        {
          "termino": "software engineering",
          "sinonimos": ["software development", "software quality"]
        },
        {
          "termino": "bug prediction",
          "sinonimos": ["defect prediction", "fault prediction"]
        }
      ],
      "exclusiones": [
        "hardware testing",
        "gaming",
        "mobile applications"
      ],
      "filtros": {
        "año": {
          "desde": 2020,
          "hasta": 2024
        }
      }
    }
    """

  Escenario: Traducción para Scopus 
    Cuando solicito traducir mi estrategia de búsqueda para "Scopus"
    Entonces obtengo una consulta traducida compatible con la sintaxis de Scopus
    Y la consulta traducida preserva la lógica de mi estrategia original
    Y el estado de la traducción es "lista"
    Y se registra la trazabilidad de la traducción

  Escenario: Traducción para IEEE Xplore 
    Cuando solicito traducir mi estrategia de búsqueda para "IEEE Xplore"
    Entonces obtengo una consulta traducida compatible con la sintaxis de IEEE Xplore
    Y la consulta traducida preserva la lógica de mi estrategia original
    Y el estado de la traducción es "lista"
    Y se registra la trazabilidad de la traducción

