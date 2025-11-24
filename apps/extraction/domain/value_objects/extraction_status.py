from enum import Enum

class ExtractionStatus(str, Enum):
    PENDING = 'Pending'
    IN_PROGRESS = 'InProgress'
    DONE = 'Done'

    def __str__(self):
        return self.value