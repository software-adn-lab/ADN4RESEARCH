from typing import List, Optional, Dict


class DesignService:
    """
    Servicio público de la app Design.
    MOCK MODE: Retorna datos falsos para desarrollo.
    """

    @staticmethod
    def get_question_details(question_id: int) -> Optional[Dict]:
        if question_id == 999:
            return None

        return {
            "id": question_id,
            "text": "¿Cómo afecta el TDD a la productividad en equipos pequeños?",
            "project_id": 1,
            "created_at": datetime.now(),
        }

    @staticmethod
    def get_questions_by_project(project_id: int) -> List[Dict]:
        """Retorna 2 preguntas dummy siempre"""
        return [
            {
                "id": 101,
                "text": "¿Cuáles son los principales retos de la migración a microservicios?",
                "project_id": project_id,
            },
            {
                "id": 102,
                "text": "¿Qué métricas definen el éxito en Clean Architecture?",
                "project_id": project_id,
            }
        ]

    @staticmethod
    def question_exists(question_id: int) -> bool:
        return question_id != 999

from typing import Optional, Dict


class AcquisitionService:
    """
    Servicio público de la app Acquisition.
    MOCK MODE: Retorna datos falsos para desarrollo.
    """

    @staticmethod
    def get_study_details(study_id: int) -> Optional[Dict]:
        """API pública para obtener detalles de un estudio (MOCK)"""
        if study_id == 999:
            return None

        return {
            "id": study_id,
            "title": f"Estudio Simulado #{study_id}: Impacto de la IA en Legacy Code",
            "year": 2024,
            "project_id": 1,
            "authors": "Dr. House, John Doe",
        }

    @staticmethod
    def exists(study_id: int) -> bool:
        """Verifica existencia del estudio (MOCK)"""
        return study_id != 999

    @staticmethod
    def get_project_id(study_id: int) -> Optional[int]:
        """Obtiene el ID del proyecto al que pertenece el estudio (MOCK)"""
        if study_id == 999:
            return None
        return 1

from typing import List, Optional, Dict
from datetime import datetime


class ProjectService:
    """
    Servicio público de la app Projects.
    MOCK MODE: Retorna datos falsos para desarrollo.
    """

    @staticmethod
    def get_project_details(project_id: int) -> Optional[Dict]:
        if project_id == 999:
            return None

        return {
            "id": project_id,
            "name": "Proyecto SLR: Modernización de Sistemas",
            "description": "Revisión sistemática sobre patrones de modernización.",
            "owner_id": 1,
        }

    @staticmethod
    def exists(project_id: int) -> bool:
        return project_id != 999

    @staticmethod
    def is_member(project_id: int, user_id: int) -> bool:
        return user_id != -1

    @staticmethod
    def get_members(project_id: int) -> List[Dict]:
        return [
            {"user_id": 1, "role": "OWNER", "joined_at": datetime.now()},
            {"user_id": 2, "role": "COLLABORATOR", "joined_at": datetime.now()},
        ]

    @staticmethod
    def get_current_stage(project_id: int) -> Optional[Dict]:
        return {
            "name": "EXTRACTION",
            "status": "OPENED",
        }
