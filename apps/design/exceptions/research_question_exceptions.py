class QuestionSubmissionError(Exception):
    """Raised when a question cannot be submitted for review."""
    pass


class QuestionNotFoundError(Exception):
    """Raised when a question does not exist."""
    pass