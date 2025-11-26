class QuestionSubmissionError(Exception):
    """Raised when a question cannot be submitted for review."""
    pass

class QuestionNotFoundError(Exception):
    """Raised when a question does not exist."""
    pass

class ResearchQuestionError(Exception):
    """Excepción base para el módulo de preguntas de investigación."""
    pass

class ProjectNotFoundError(ResearchQuestionError):
    """Se lanza cuando el proyecto asociado no existe."""
    pass

class InvalidFrameworkFieldsError(ResearchQuestionError):
    """Se lanza cuando la estructura o datos del framework son inválidos."""
    pass