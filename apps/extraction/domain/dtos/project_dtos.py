from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(frozen=True)
class ProjectDTO:
    id: int
    name: str
    description: str
    owner_id: int
    # framework_id? Solo si extraction necesita saber sobre el framework

@dataclass(frozen=True)
class ProjectMemberDTO:
    user_id: int
    role: str  # 'OWNER', 'RESEARCHER'
    joined_at: datetime

@dataclass(frozen=True)
class StageDTO:
    name: str
    status: str # 'OPENED', 'CLOSED', 'INACTIVE'