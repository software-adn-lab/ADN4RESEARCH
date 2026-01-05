from dataclasses import dataclass


@dataclass
class DesignTimelineStageDTO:
    key: str
    label: str
    status: str
