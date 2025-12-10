
class CreationError(Exception):
    """Exception raised when there is an error creating an eligibility criterion."""
    pass

class NotFoundError(Exception):
    """Exception raised when an eligibility criterion is not found."""
    pass

class UpdateError(Exception):
    """Exception raised when there is an error updating an eligibility criterion."""
    pass

class DeletionError(Exception):
    """Exception raised when there is an error deleting an eligibility criterion."""
    pass

class InvalidCriterionTypeError(Exception):
    """Exception raised when an invalid criteria type is provided."""
    pass

class ConsolidationError(Exception):
    """Exception raised when there is an error consolidating the eligibility criteria stage."""
    pass