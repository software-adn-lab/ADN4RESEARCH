from enum import Enum

class TagType(str, Enum):
    DEDUCTIVE = 'deductive'
    INDUCTIVE = 'inductive'
    PERSONAL = 'personal'

    def __str__(self):
        return self.value