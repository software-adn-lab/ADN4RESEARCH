# Feature: Descubrimiento y Generación Automática de Temas (AI-Driven Theme Discovery) 🧠

# Propósito: Utilizar la capacidad de LLM para asistir en la Codificación Avanzada y la Generación de Temas (Análisis Temático),
# proponiendo estructuras temáticas coherentes a partir de los códigos (tags) validados por el investigador.

Feature: Descubrimiento y Generación Automática de Temas
    Como un Investigador en el Módulo de Interpretación
    Quiero que la IA me asista en la limpieza y agrupación de códigos en temas de alto nivel
    Para acelerar la fase de análisis cualitativo y garantizar la coherencia de la síntesis interpretativa.

# ------------------------------------------------------------------------------------------------------------------------------------

Scenario: 1. Normalización de Códigos (Fusión de Tags Similares y División de Conceptos)

    Given que el Módulo de Interpretación ha cargado los Códigos iniciales (tags) desde el Módulo de Extracción
        | Código Inicial | Frecuencia |
        | #repository_mining | 3 |
        | #github | 2 |
        | #antipattern_detection | 4 |
        | #qualitative_method | 3 |
        | #thematic_analysis | 3 |
        | #time_pressure | 1 |
        | #client_server_architecture | 1 |
        | #vague_inheritance | 1 |
        | #inherited_debt | 1 |
        | #api_misuse | 1 |
    
    When el Investigador activa la función "Normalización Inteligente de Códigos" en el Study Quality Evaluator
    
    Then el sistema (IA) debería analizar los códigos y proponer las siguientes acciones para reducir la redundancia:
        And Proponer la fusión de [#repository_mining, #github] en un nuevo Código Normalizado: "#extracción_de_repositorios_SWH".
        And Proponer la fusión de [#qualitative_method, #thematic_analysis] en un nuevo Código Normalizado: "#análisis_temático_cualitativo".
        And Proponer la fusión de [#vague_inheritance, #inherited_debt] en un nuevo Código Normalizado: "#deuda_heredada_de_framework".
    
    When el Investigador acepta la lista de Códigos Normalizados propuestos
    
    Then el Módulo de Interpretación persiste el nuevo diccionario de códigos para su uso en la siguiente fase.

# ------------------------------------------------------------------------------------------------------------------------------------

Scenario: 2. Descubrimiento y Propuesta Automática de Temas (AI-Generated Themes)

    Given que el proceso de Normalización de Códigos ha sido completado
    And el Study Quality Evaluator dispone de los siguientes Códigos Finales (Axiomas) para la síntesis:
        | Código Final | Foco de Investigación |
        | #antipattern_detection | RQ1 (Identificación) |
        | #extracción_de_repositorios_SWH | RQ1 (Identificación) |
        | #análisis_temático_cualitativo | RQ1 (Identificación) |
        | #time_pressure | RQ2 (Causas) |
        | #client_server_architecture | RQ2 (Causas) |
        | #deuda_heredada_de_framework | RQ2 (Causas) |
        | #developer_skill | RQ2 (Causas) |
        | #api_misuse | RQ2 (Causas) |
    
    When el Investigador **solicita a la IA generar una estructura de temas de alto nivel** (emulando la Teoría Fundamentada)
    
    Then el sistema (IA/LLM) debería proponer una jerarquía de **Temas** que clasifiquen y sinteticen los códigos:
        And Proponer el Tema 1: "Métodos de Descubrimiento de Anti-Patrones" que agrupe códigos de RQ1.
        And Proponer el Tema 2: "Factores Determinantes de Anti-Patrones" con una sub-clasificación inicial:
            | Subtema 2.1: Factores Organizacionales (#time_pressure) | 
            | Subtema 2.2: Factores Arquitectónicos (#client_server_architecture, #deuda_heredada_de_framework) | 
            | Subtema 2.3: Factores Humanos/Cognitivos (#developer_skill, #api_misuse) |
    
    When el Investigador aplica **Reflexividad** y revisa las propuestas
        And El Investigador **edita** el Tema 2, renombrándolo a: "Modelos Teóricos de Inducción de APs (RQ2)".
    
    Then el Módulo de Interpretación persiste la estructura de Temas Finales validados
        And La **traza del análisis por IA** (propuesta inicial vs. estructura final) se registra para fines de rigor y trazabilidad metodológica.
