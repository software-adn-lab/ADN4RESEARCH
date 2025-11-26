from dataclasses import dataclass

@dataclass(frozen=True)
class ResearchQuestionDTO:
    id: int
    text: str
    project_id: int