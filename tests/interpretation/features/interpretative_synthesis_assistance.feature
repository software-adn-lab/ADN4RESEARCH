Feature: Asistencia Inteligente para la Síntesis Interpretativa
    Como un Investigador de SLR en Ingeniería de Software
    Quiero utilizar generar un borrador de Proposición Interpretativa (Conclusión) y su narrativa de soporte
    Para asegurar que la interpretación de los datos cualitativos responda directamente a las Preguntas de Investigación.

Background:
    Given que el Investigador ha definido la Pregunta de Investigación: "¿Cuáles son los desafíos técnicos y organizacionales reportados al implementar DevOps en equipos distribuidos?"
    And se tiene el tema "Antipatrones en el desarrollo de software" como foco de la interpretación actual
    And el Investigador selecciona el "Subtema B: Retos Culturales y de Comunicación" como objeto de la interpretación
        | Tema Seleccionado | Códigos Centrales | Citas Clave de Estudios |
        | Retos Culturales y de Comunicación | Dependencia de zonas horarias, Retraso en feedback, Falta de confianza. | Fragmentos de texto específicos. |

Scenario: Inicio de la Asistencia Contextual de Interpretación

    Given que el Módulo de Interpretación está disponible para la Síntesis de Datos y las "extracciones" del "tema B" son parte del contexto activo
    
    When el Investigador **inicia de la asistencia conversacional** sobre el "Subtema B"
        And **Establece la RQ, el subtema B y los códigos/citas de soporte como contexto activo** para la interacción.
    
    Then se genera un texto con la estructura:
        | Title | Body | Tags |
        | Apertura conversacional del Copilot | Texto que reconoce el Tema y la RQ (p. ej., "Asistiendo en la interpretación del Subtema B... ¿Cuál es la proposición preliminar o enfoque deseado?") | tema_b, retos_culturales, comunicacion |

# Scenario: Refinamiento Iterativo y Persistencia del Hallazgo Final

#     Given que la Asistencia Interpretativa Conversacional está activa y contextualizada con el Tema B
#     And el Investigador ha mantenido la siguiente interacción con el Copilot:
#         | Instrucción Investigador | Respuesta Copilot (Borrador) |
#         | Genera una proposición fuerte sobre zonas horarias y feedback. | Proposición Borrador: "La principal barrera organizacional es la disrupción de la colaboración..." |
    
#     When el Investigador **proporciona la instrucción de refinamiento final**: "Reformula el borrador para enfatizar 'comunicación asíncrona' y acepta el resultado final."
    
#     Then el sistema (Copilot) debería:
#         And Generar una **Proposición Refinada** que incorpore el concepto de "comunicación asíncrona".
#         And El Módulo de Interpretación debería **persistir** la Proposición Refinada y su narrativa de soporte como 'Hallazgo Final de la SLR'.
#         And **Guardar la traza completa de la interacción conversacional** para fines de **Reflexividad metodológica**.
#         And Marcar el Tema B como **'Interpretación Finalizada'**.